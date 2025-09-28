import sys
from collections import deque, defaultdict
from azurestoragemanager import AzureStorageManager
from dotenv import load_dotenv
import os
import argparse
import csv

# ---------- CLI ----------
parser = argparse.ArgumentParser(description="Recalculate room grid refs from exits and render CSV map with direction arrows.")
parser.add_argument("world", nargs="?", default="normchester", help="World name to map")
parser.add_argument("--outdir", default=".", help="Directory to write CSV outputs")
args = parser.parse_args()

# ---------- Env ----------
full_path = "../common/.env"
os.path.exists(full_path) or sys.exit(f"No .env file found at {full_path}")
load_dotenv(dotenv_path=full_path)

# ---------- Data fetch ----------
storage_manager = AzureStorageManager()
rooms = list(storage_manager.get_world_object_data(args.world, "Room"))
if not rooms:
    sys.exit(f"No rooms found for world '{args.world}'.")

# ---------- Build lookup ----------
rooms_by_name = {}
for r in rooms:
    name = r.get("name")
    if not name:
        continue
    rooms_by_name[name] = {
        "name": name,
        "exits": r.get("exits", {}) or {},
        "original_grid_reference": r.get("grid_reference"),
    }

# ---------- Direction tables ----------
DIR_DELTAS = {
    "north": (0, 1), "n": (0, 1),
    "south": (0, -1), "s": (0, -1),
    "east": (1, 0), "e": (1, 0),
    "west": (-1, 0), "w": (-1, 0),
    "northeast": (1, 1), "ne": (1, 1),
    "northwest": (-1, 1), "nw": (-1, 1),
    "southeast": (1, -1), "se": (1, -1),
    "southwest": (-1, -1), "sw": (-1, -1),
    "up": (0, 0), "down": (0, 0), "in": (0, 0), "out": (0, 0),
}

REVERSE = {
    "north": "south", "n": "s",
    "south": "north", "s": "n",
    "east": "west", "e": "w",
    "west": "east", "w": "e",
    "northeast": "southwest", "ne": "sw",
    "southwest": "northeast", "sw": "ne",
    "northwest": "southeast", "nw": "se",
    "southeast": "northwest", "se": "nw",
    "up": "down", "down": "up", "in": "out", "out": "in",
}

# Arrows only for the four cardinals (as requested)
DIR_TO_ARROW = {
    "north": "^", "n": "^",
    "south": "v", "s": "v",
    "east": ">", "e": ">",
    "west": "<", "w": "<",
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
    if room_name in assigned and assigned[room_name] != xy:
        issues["room_reassigned"].append((room_name, assigned[room_name], xy))
    assigned[room_name] = xy
    by_coord[xy].append(room_name)

def traverse_component(start_room_name, origin_xy=(0, 0)):
    from collections import deque
    q = deque()
    assign(start_room_name, origin_xy)
    q.append(start_room_name)
    visited.add(start_room_name)

    while q:
        cur = q.popleft()
        cur_xy = assigned[cur]
        exits = rooms_by_name[cur].get("exits", {}) or {}

        for dir_raw, target in exits.items():
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
                continue

            # Backlink checks
            target_exits = rooms_by_name[target].get("exits", {}) or {}
            back_dir = REVERSE.get(dir_key)
            if back_dir:
                if back_dir in target_exits and target_exits[back_dir] != cur:
                    issues["inconsistent_backlinks"].append((cur, dir_raw, target, back_dir))
                if back_dir not in target_exits:
                    issues["one_way_links"].append((cur, dir_raw, target))

            if target not in assigned:
                assign(target, next_xy)
                if target not in visited:
                    visited.add(target)
                    q.append(target)
            else:
                if assigned[target] != next_xy:
                    issues["room_reassigned"].append((target, assigned[target], next_xy))

# Kick off traversal for all components (each starts at origin)
for room_name in rooms_by_name.keys():
    if room_name not in visited:
        traverse_component(room_name, origin_xy=(0, 0))

# ---------- Collisions (multiple rooms on same coord) ----------
for xy, names in by_coord.items():
    uniq = list(dict.fromkeys(names))
    if len(uniq) > 1:
        issues["coordinate_clashes"].append((xy, uniq))

# ---------- Bounds ----------
if assigned:
    xs = [xy[0] for xy in assigned.values()]
    ys = [xy[1] for xy in assigned.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
else:
    min_x = max_x = min_y = max_y = 0

# ---------- Compute arrows per room (to/from) ----------
# Outgoing cardinals from this room
out_cardinals = {name: set() for name in rooms_by_name.keys()}
# Incoming cardinals from neighbours pointing at this room
in_cardinals = {name: set() for name in rooms_by_name.keys()}

for src_name, obj in rooms_by_name.items():
    exits = obj.get("exits", {}) or {}
    for dir_raw, tgt_name in exits.items():
        if not tgt_name or tgt_name not in rooms_by_name:
            continue
        d = str(dir_raw).strip().lower()
        # Outgoing arrow for src
        if d in DIR_TO_ARROW:
            out_cardinals[src_name].add(DIR_TO_ARROW[d])
        # Incoming arrow for target (reverse direction)
        rev = REVERSE.get(d)
        if rev in DIR_TO_ARROW:
            in_cardinals[tgt_name].add(DIR_TO_ARROW[rev])

def arrows_for(name: str) -> str:
    # Union of outgoing and incoming to satisfy "to/from"
    arrows = []
    # fixed order for readability
    order = ["<", "^", "v", ">"]
    present = set()
    present |= out_cardinals.get(name, set())
    present |= in_cardinals.get(name, set())
    for sym in order:
        if sym in present:
            arrows.append(sym)
    return "".join(arrows)

# ---------- Build CSV grid with names + arrows ----------
x_values = list(range(min_x, max_x + 1))
y_values = list(range(max_y, min_y - 1, -1))  # north at top

def formatted_name(name: str) -> str:
    arr = arrows_for(name)
    return f"{name} ({arr})" if arr else name

def cell_value(x, y):
    names = list(dict.fromkeys(by_coord.get((x, y), [])))
    if not names:
        return ""  # blank cell
    if len(names) == 1:
        return formatted_name(names[0])
    return "CLASH: " + " | ".join(formatted_name(n) for n in names)

rows = []
header_row = ["y\\x"] + [str(x) for x in x_values]
rows.append(header_row)

for y in y_values:
    row = [str(y)]
    for x in x_values:
        row.append(cell_value(x, y))
    rows.append(row)

# ---------- Write CSV files ----------
os.makedirs(args.outdir, exist_ok=True)
map_path = os.path.join(args.outdir, f"{args.world}_map.csv")
issues_path = os.path.join(args.outdir, f"{args.world}_issues.csv")

with open(map_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

with open(issues_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["IssueType", "Details"])
    for (xy, names) in issues["coordinate_clashes"]:
        writer.writerow(["coordinate_clash", f"{xy} :: {' | '.join(names)}"])
    for (room, old_xy, new_xy) in issues["room_reassigned"]:
        writer.writerow(["room_reassigned", f"{room} :: {old_xy} -> {new_xy}"])
    for (room, direction, target) in issues["unknown_directions"]:
        writer.writerow(["unknown_direction", f"{room} :: {direction} -> {target}"])
    for (room, direction, target) in issues["missing_target_rooms"]:
        writer.writerow(["missing_target_room", f"{room} :: {direction} -> {target}"])
    for (frm, direction, to) in issues["one_way_links"]:
        writer.writerow(["one_way_link", f"{frm} :: {direction} -> {to}"])
    for (frm, direction, to, expected_back) in issues["inconsistent_backlinks"]:
        writer.writerow(["inconsistent_backlink", f"{frm} :: {direction} -> {to} (expected {expected_back} back)"])

# ---------- Console report ----------
def print_section(title, items):
    print(f"\n{title} ({len(items)}):")
    if not items:
        print("  None")
        return
    for it in items:
        print(" ", it)

print(f"World: {args.world}")
print(f"Wrote CSV map: {map_path}")
print(f"Wrote CSV issues: {issues_path}")

print_section("Coordinate clashes (multiple rooms on same tile)", issues["coordinate_clashes"])
print_section("Rooms reassigned to conflicting coordinates", issues["room_reassigned"])
print_section("Unknown directions", issues["unknown_directions"])
print_section("Missing target rooms", issues["missing_target_rooms"])
print_section("One-way links (no backlink)", issues["one_way_links"])
print_section("Inconsistent backlinks (backlink exists but points elsewhere)", issues["inconsistent_backlinks"])
