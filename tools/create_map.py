import sys
from collections import deque, defaultdict
from azurestoragemanager import AzureStorageManager
from dotenv import load_dotenv
import os
import argparse
import math

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

# ---------- CLI ----------
parser = argparse.ArgumentParser(
    description="Recalculate room grid refs and render a graphical map with boxes and arrows."
)
parser.add_argument("world", nargs="?", default="normchester", help="World name to map")
parser.add_argument("--outdir", default=".", help="Directory to write outputs")
parser.add_argument("--dpi", type=int, default=200, help="Raster export DPI for PNG")
parser.add_argument("--scale", type=float, default=5.0,
                    help="Grid spacing in figure units (larger = more space between boxes)")
parser.add_argument("--boxw", type=float, default=5, help="Box width in figure units")
parser.add_argument("--boxh", type=float, default=2.0, help="Box height in figure units")
parser.add_argument("--font", default="DejaVu Sans", help="Matplotlib font family for labels")
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
    # 2D map keeps these on the same tile (still draw arrows if rooms are distinct and positioned)
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

# ---------- BFS layout (may have multiple components) ----------
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
    q = deque([start_room_name])
    assign(start_room_name, origin_xy)
    visited.add(start_room_name)

    while q:
        cur = q.popleft()
        cur_xy = assigned[cur]
        exits = rooms_by_name[cur].get("exits", {}) or {}

        for dir_raw, target in exits.items():
            if not target:
                continue
            d = str(dir_raw).strip().lower()
            if d not in DIR_DELTAS:
                issues["unknown_directions"].append((cur, dir_raw, target))
                continue

            dx, dy = DIR_DELTAS[d]
            next_xy = (cur_xy[0] + dx, cur_xy[1] + dy)

            if target not in rooms_by_name:
                issues["missing_target_rooms"].append((cur, dir_raw, target))
                continue

            # Backlink checks
            target_exits = rooms_by_name[target].get("exits", {}) or {}
            back_dir = REVERSE.get(d)
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

# For disconnected graphs, place each component at an offset to avoid overlap in the picture
component_offset_step = (1000, 0)  # big jump so components don’t overlap visually
comp_index = 0
for room_name in list(rooms_by_name.keys()):
    if room_name not in visited:
        base = (component_offset_step[0] * comp_index, component_offset_step[1] * comp_index)
        traverse_component(room_name, origin_xy=base)
        comp_index += 1

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

# ---------- Geometry helpers ----------
S = args.scale
BOX_W = args.boxw
BOX_H = args.boxh
HALF_W = BOX_W / 2.0
HALF_H = BOX_H / 2.0

def centre_for(xy):
    xg, yg = xy
    return (xg * S, yg * S)

def rect_for(xy):
    cx, cy = centre_for(xy)
    return (cx - HALF_W, cy - HALF_H, BOX_W, BOX_H)

def edge_point_between_boxes(src_xy, tgt_xy):
    """Return two points (p_src, p_tgt) on the edges of the source/target rectangles,
    so the arrow runs between rectangle borders rather than centre-to-centre."""
    sx, sy = centre_for(src_xy)
    tx, ty = centre_for(tgt_xy)
    dx, dy = tx - sx, ty - sy
    if dx == 0 and dy == 0:
        return (sx, sy), (tx, ty)

    # Compute intersection with source rectangle border
    def border_point(cx, cy, dx, dy):
        # parametric line from centre in direction (dx,dy) to rectangle border
        t_candidates = []
        if dx != 0:
            t_right = (HALF_W) / abs(dx)
            t_candidates.append(t_right)
        if dy != 0:
            t_top = (HALF_H) / abs(dy)
            t_candidates.append(t_top)
        t = min(t_candidates) if t_candidates else 0.0
        return (cx + dx * t, cy + dy * t)

    ps = border_point(sx, sy, dx, dy)
    pt = border_point(tx, ty, -dx, -dy)
    return ps, pt

# ---------- Build edges (collapse bidirectional into one <-> arrow) ----------
# key = frozenset({A,B}) -> {"pair": (A,B), "both": bool, "oneway": "A->B" or "B->A"}
edges = {}
for a_name, obj in rooms_by_name.items():
    for d_raw, b_name in (obj.get("exits", {}) or {}).items():
        if not b_name or b_name not in rooms_by_name:
            continue
        key = frozenset((a_name, b_name))
        existing = edges.get(key)
        a_to_b = (a_name, b_name)
        b_to_a = (b_name, a_name)
        if existing is None:
            edges[key] = {"pair": (a_name, b_name), "both": False, "oneway": a_to_b}
        else:
            # If the opposite direction already recorded as one-way, flip to both
            if existing["oneway"] == b_to_a:
                existing["both"] = True

# ---------- Figure setup ----------
plt.rcParams["font.family"] = args.font
fig, ax = plt.subplots(figsize=(10, 10), dpi=args.dpi)

# Expand axes based on bounds
pad = S * 2
min_fx = min_x * S - pad
max_fx = max_x * S + pad
min_fy = min_y * S - pad
max_fy = max_y * S + pad
ax.set_xlim(min_fx, max_fx)
ax.set_ylim(min_fy, max_fy)
ax.set_aspect("equal")
ax.axis("off")

# ---------- Draw boxes ----------
for xy, names in by_coord.items():
    cx, cy = centre_for(xy)
    if len(set(names)) == 1:
        # Normal single room
        name = names[0]
        x0, y0, w, h = rect_for(xy)
        rect = Rectangle((x0, y0), w, h, facecolor="#f4f4f4", edgecolor="#333333", linewidth=1.25)
        ax.add_patch(rect)
        ax.text(cx, cy, name, ha="center", va="center", fontsize=8, wrap=True)
    else:
        # Clash — show one red box with list of names
        x0, y0, w, h = rect_for(xy)
        rect = Rectangle((x0, y0), w, h, facecolor="#ffe6e6", edgecolor="#cc0000", linewidth=1.8, hatch="////")
        ax.add_patch(rect)
        # Show up to a few names; full list below the figure in a legend block
        label = "CLASH:\n" + "\n".join(names[:4]) + ("… (+{})".format(len(names)-4) if len(names) > 4 else "")
        ax.text(cx, cy, label, ha="center", va="center", fontsize=7, color="#990000", wrap=True)

# ---------- Draw arrows ----------
def draw_arrow(p0, p1, both=False):
    if both:
        style = "<->"
        lw = 1.4
        color = "#1f77b4"
    else:
        style = "->"
        lw = 1.4
        color = "#444444"
    # Slight shorten so arrowheads don’t cover box borders
    sx, sy = p0
    tx, ty = p1
    # Create the patch
    ap = FancyArrowPatch(
        p0, p1,
        arrowstyle=style,
        mutation_scale=10,
        linewidth=lw,
        color=color,
        shrinkA=6, shrinkB=6,
        connectionstyle="arc3"
    )
    ax.add_patch(ap)

for key, info in edges.items():
    a, b = info["pair"]
    # Skip arrows for rooms that ended up on the exact same coordinate (clash box covers it)
    if assigned.get(a) == assigned.get(b):
        continue
    ps, pt = edge_point_between_boxes(assigned[a], assigned[b])
    draw_arrow(ps, pt, both=info["both"])

# ---------- Title and export ----------
ax.set_title(f"World map: {args.world}", fontsize=12, pad=12)

os.makedirs(args.outdir, exist_ok=True)
png_path = os.path.join(args.outdir, f"{args.world}_map.png")
svg_path = os.path.join(args.outdir, f"{args.world}_map.svg")

fig.tight_layout(pad=0.5)
fig.savefig(png_path, dpi=args.dpi, bbox_inches="tight")
fig.savefig(svg_path, bbox_inches="tight")
plt.close(fig)

# ---------- Issues summary to console ----------
def print_section(title, items):
    print(f"\n{title} ({len(items)}):")
    if not items:
        print("  None")
        return
    for it in items:
        print(" ", it)

print(f"Wrote {png_path}")
print(f"Wrote {svg_path}")

print_section("Coordinate clashes (multiple rooms on same tile)", issues["coordinate_clashes"])
print_section("Rooms reassigned to conflicting coordinates", issues["room_reassigned"])
print_section("Unknown directions", issues["unknown_directions"])
print_section("Missing target rooms", issues["missing_target_rooms"])
print_section("One-way links (no backlink)", issues["one_way_links"])
print_section("Inconsistent backlinks (backlink exists but points elsewhere)", issues["inconsistent_backlinks"])
