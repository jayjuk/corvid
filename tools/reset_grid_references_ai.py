import sys
from collections import deque, defaultdict
from azurestoragemanager import AzureStorageManager
from dotenv import load_dotenv
import os
import argparse

# ---------- CLI ----------
parser = argparse.ArgumentParser(description="Recalculate room grid refs from exits and render a map.")
parser.add_argument("world", nargs="?", default="normchester", help="World name to map")
args = parser.parse_args()

# ---------- Env ----------
full_path = "../common/.env"
os.path.exists(full_path) or sys.exit(f"No .env file found at {full_path}")
load_dotenv(dotenv_path=full_path)

# ---------- Data fetch ----------
storage_manager = AzureStorageManager()

# Expecting each object like:
# {
#   "name": "Green Grocer",
#   "grid_reference": "-2,-6",   # ignored for recalculation
#   "exits": {"west": "Foo", "east": "Bar"}
# }
rooms = list(storage_manager.get_world_object_data(args.world, "Room"))

if not rooms:
    sys.exit(f"No rooms found for world '{args.world}'.")

# ---------- Build lookup ----------
rooms_by_name = {}
for r in rooms:
    name = r.get("name")
    if not name:
        # Skip nameless entries defensively
        continue
    rooms_by_name[name] = {
        "name": name,
        "exits": r.get("exits", {}) or {},
        "original_grid_reference": r.get("grid_reference"),
    }

# ---------- Direction deltas ----------
# Using conventional grid: +y = north, +x = east
DIR_DELTAS = {
    "north": (0, 1), "n": (0, 1),
    "south": (0, -1), "s": (0, -1),
    "east": (1, 0), "e": (1, 0),
    "west": (-1, 0), "w": (-1, 0),
    "northeast": (1, 1), "ne": (1, 1),
    "northwest": (-1, 1), "nw": (-1, 1),
    "southeast": (1, -1), "se": (1, -1),
    "southwest": (-1, -1), "sw": (-1, -1),
    "up": (0, 0),    # vertical/other dimensions: keep on same 2D tile for map, but track link
    "down": (0, 0),
    "in": (0, 0),
    "out": (0, 0),
}

# Reverse directions for consistency checks
REVERSE = {
    "north": "south", "n": "s",
    "south": "north", "s": "n",
    "east": "west", "e": "w",
    "west": "east", "w": "e",
    "northeast": "southwest", "ne": "sw",
    "southwest": "northeast", "sw": "ne",
    "northwest": "southeast", "nw": "se",
    "southeast": "northwest", "se": "nw",
    "up": "down",
    "down": "up",
    "in": "out",
    "out": "in",
}

# ---------- BFS over (possibly) multiple components ----------
assigned = {}                 # room_name -> (x, y)
by_coord = defaultdict(list)  # (x, y) -> [room_name, ...]
visited = set()

issues = {
    "missing_target_rooms": [],     # (room, direction, target_name)
    "unknown_directions": [],       # (room, direction, target_name)
    "coordinate_clashes": [],       # ((x,y), [rooms...])
    "room_reassigned": [],          # (room, old_xy, new_xy)
    "one_way_links": [],            # (from, dir, to)
    "inconsistent_backlinks": [],   # (from, dir, to, expected_back_dir)
}

def assign(room_name, xy):
    # If room already assigned a different xy, record reassignment issue
    if room_name in assigned and assigned[room_name] != xy:
        issues["room_reassigned"].append((room_name, assigned[room_name], xy))
    assigned[room_name] = xy
    by_coord[xy].append(room_name)

def traverse_component(start_room_name, origin_xy=(0, 0)):
    q = deque()
    assign(start_room_name, origin_xy)
    q.append(start_room_name)
    visited.add(start_room_name)

    while q:
        cur = q.popleft()
        cur_xy = assigned[cur]
        exits = rooms_by_name[cur].get("exits", {})

        for dir_raw, target in (exits or {}).items():
            if not target:
                continue
            dir_key = str(dir_raw).strip().lower()
            if dir_key not in DIR_DELTAS:
                issues["unknown_directions"].append((cur, dir_raw, target))
                continue
            dx, dy = DIR_DELTAS[dir_key]
            next_xy = (cur_xy[0] + dx, cur_xy[1] + dy)

            if target not in rooms_by_name:
                issues["missing_target_rooms"].append((cur, dir_raw, target))
                # still carry on, as graph can be partially broken
                continue

            # Backlink checks
            target_exits = rooms_by_name[target].get("exits", {}) or {}
            back_dir = REVERSE.get(dir_key)
            if back_dir:
                # If backlink exists but points elsewhere, flag
                if back_dir in target_exits and target_exits[back_dir] != cur:
                    issues["inconsistent_backlinks"].append((cur, dir_raw, target, back_dir))
                # If backlink missing entirely, note one-way
                if back_dir not in target_exits:
                    issues["one_way_links"].append((cur, dir_raw, target))

            if target not in assigned:
                assign(target, next_xy)
                if target not in visited:
                    visited.add(target)
                    q.append(target)
            else:
                # Already assigned; check for coordinate consistency
                if assigned[target] != next_xy:
                    # This manifests as two computed coords for same room; record reassignment
                    issues["room_reassigned"].append((target, assigned[target], next_xy))
                # else consistent, nothing to do

# Kick off traversal for all components (choose any unvisited room as a new origin)
for room_name in rooms_by_name.keys():
    if room_name not in visited:
        traverse_component(room_name, origin_xy=(0, 0))

# ---------- Collisions (multiple rooms on same coord) ----------
for xy, names in by_coord.items():
    uniq = list(dict.fromkeys(names))
    if len(uniq) > 1:
        issues["coordinate_clashes"].append((xy, uniq))

# ---------- Build map ----------
if assigned:
    xs = [xy[0] for xy in assigned.values()]
    ys = [xy[1] for xy in assigned.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
else:
    min_x = max_x = min_y = max_y = 0

width = max_x - min_x + 1
height = max_y - min_y + 1

# Cell rendering rules:
# - "  ." empty
# - " XX" coordinate clash
# - number token if single room; enumerate legend
# Keep tokens width 3 for neat columns
coord_to_token = {}
legend = []
index_by_room = {}

counter = 1
for xy, names in sorted(by_coord.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    uniq = list(dict.fromkeys(names))
    if len(uniq) == 1:
        room = uniq[0]
        index_by_room[room] = counter
        coord_to_token[xy] = f"{counter:3d}"
        legend.append((counter, xy, room))
        counter += 1
    else:
        coord_to_token[xy] = " XX"  # clash

def cell(x, y):
    xy = (x, y)
    return coord_to_token.get(xy, "  .")

# Render with y descending (north at the top)
lines = []
lines.append("")
lines.append(f"World: {args.world}")
lines.append(f"Extent X[{min_x}..{max_x}] Y[{min_y}..{max_y}]  Rooms: {len(assigned)}  Components: {len({assigned[n] for n in assigned}) and 'var'}")
lines.append("Map key: '.' empty, number = room, 'XX' = coordinate clash\n")

header = "     " + " ".join(f"{x:3d}" for x in range(min_x, max_x + 1))
lines.append(header)
for y in range(max_y, min_y - 1, -1):
    row = [f"{y:4d}"]
    for x in range(min_x, max_x + 1):
        row.append(cell(x, y))
    lines.append(" ".join(row))

# ---------- Print map ----------
print("\n".join(lines))

# ---------- Legend ----------
print("\nLegend:")
for idx, xy, room in legend:
    print(f" {idx:3d} @ {xy[0]},{xy[1]}  {room}")

# ---------- Issues report ----------
def print_section(title, items):
    print(f"\n{title} ({len(items)}):")
    if not items:
        print("  None")
        return
    for it in items:
        print(" ", it)

print_section("Coordinate clashes (multiple rooms on same tile)", issues["coordinate_clashes"])
print_section("Rooms reassigned to conflicting coordinates", issues["room_reassigned"])
print_section("Unknown directions", issues["unknown_directions"])
print_section("Missing target rooms", issues["missing_target_rooms"])
print_section("One-way links (no backlink)", issues["one_way_links"])
print_section("Inconsistent backlinks (backlink exists but points elsewhere)", issues["inconsistent_backlinks"])

# ---------- Optional: compare with original stored grid refs ----------
mismatched_originals = []
for name, xy in assigned.items():
    orig = rooms_by_name[name].get("original_grid_reference")
    if isinstance(orig, str) and "," in orig:
        try:
            ox, oy = map(int, orig.split(",", 1))
            if (ox, oy) != xy:
                mismatched_originals.append((name, (ox, oy), xy))
        except ValueError:
            # Ignore unparsable originals
            pass

print_section("Rooms whose stored grid_reference differs from recalculated", mismatched_originals)
