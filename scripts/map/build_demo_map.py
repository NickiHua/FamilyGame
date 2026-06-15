#!/usr/bin/env python3
"""Author the demo battlefield LAYOUT as grid data and export to JSON.

This script is the SINGLE SOURCE OF TRUTH for the map *layout*. It paints
features (river, forests, cliffs, roads, bridges, walls, houses) onto a
25x25 grid of terrain codes, then writes ``scripts/map/demo_map.json``.

The exported JSON drives BOTH:
  * ``render_map.py``  -> control images for ComfyUI / Flux ControlNet
  * Unity              -> walkable / move-cost logic grid (same source = no drift)

The layout approximates the "SRPG BATTLEFIELD" reference mock-up
(top-left panel): a meandering river crossed by two bridges, a village
cluster on each bank, forest belts, a short stone wall, and rocky cliffs
in the bottom corners. Tweak the data blocks below to reshape the map.

Run (CWD = FamilyGame/):
    python scripts/map/build_demo_map.py
"""
from __future__ import annotations

import json
from pathlib import Path

# --------------------------------------------------------------------------- #
# Grid constants
# --------------------------------------------------------------------------- #
GRID = 35            # cells per side
CELL_PX = 64         # pixels per cell  -> output image = 2240 x 2240

# Terrain codes (single char each, used in the base grid)
GRASS = "G"
ROAD = "R"
FOREST = "F"
WATER = "W"
CLIFF = "C"
BUILDING = "B"
WALL = "L"
BRIDGE = "D"

# Palette: code -> render + logic attributes.
#   rgb       : semantic-segmentation colour (matches reference legend)
#   walkable  : ground unit may ENTER and STOP here
#   move_cost : movement points consumed to enter (ignored if not walkable)
#   height    : 0..255 greyscale for the depth control image
PALETTE = {
    GRASS:    {"name": "Grass/Plains", "rgb": [124, 176, 76],  "walkable": True,  "move_cost": 1, "height": 110},
    ROAD:     {"name": "Road",         "rgb": [201, 178, 124], "walkable": True,  "move_cost": 1, "height": 100},
    FOREST:   {"name": "Forest",       "rgb": [47, 92, 47],    "walkable": False, "move_cost": 0, "height": 150},
    WATER:    {"name": "Water",        "rgb": [60, 120, 200],  "walkable": False, "move_cost": 0, "height": 30},
    CLIFF:    {"name": "Cliff/Rock",   "rgb": [120, 110, 130], "walkable": False, "move_cost": 0, "height": 240},
    BUILDING: {"name": "Building",     "rgb": [96, 60, 56],    "walkable": False, "move_cost": 0, "height": 210},
    WALL:     {"name": "Wall",         "rgb": [180, 180, 185], "walkable": False, "move_cost": 0, "height": 190},
    BRIDGE:   {"name": "Bridge",       "rgb": [150, 110, 70],  "walkable": True,  "move_cost": 1, "height": 90},
}


# --------------------------------------------------------------------------- #
# Rasterizer helpers
# --------------------------------------------------------------------------- #
def blank_grid() -> list[list[str]]:
    return [[GRASS] * GRID for _ in range(GRID)]


def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < GRID and 0 <= c < GRID


def paint_rect(grid, r0, c0, r1, c1, code) -> None:
    """Fill an inclusive rectangle [r0..r1] x [c0..c1] with ``code``."""
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if in_bounds(r, c):
                grid[r][c] = code


def paint_river(grid, centers, widths) -> None:
    """Paint WATER along a per-row centre column with a per-row width."""
    for r, (cc, w) in enumerate(zip(centers, widths)):
        if cc is None:
            continue
        half = w // 2
        for c in range(cc - half, cc - half + w):
            if in_bounds(r, c):
                grid[r][c] = WATER


def paint_road(grid, points) -> None:
    """Paint an L-shaped (orthogonal) ROAD through a list of (r, c) points.

    The road never overwrites WATER (a crossing needs a bridge instead),
    so paint roads BEFORE the river and add bridges on the crossings.
    """
    prev = None
    for r1, c1 in points:
        if prev is not None:
            r, c = prev
            while (r, c) != (r1, c1):
                if in_bounds(r, c) and grid[r][c] != WATER:
                    grid[r][c] = ROAD
                if r != r1:
                    r += 1 if r1 > r else -1
                elif c != c1:
                    c += 1 if c1 > c else -1
            if in_bounds(r1, c1) and grid[r1][c1] != WATER:
                grid[r1][c1] = ROAD
        prev = (r1, c1)


# --------------------------------------------------------------------------- #
# Layout data (edit these to reshape the battlefield)
# --------------------------------------------------------------------------- #
# Reconciled to the CHOSEN art (art/maps/demo_map.png) on 2026-06-14 by reading
# the 1024 ControlNet source A_seg_str060_end080_00006. The art is a vertical
# river crossed by THREE horizontal bridges, a big house cluster top-right, a
# single house mid-left, a small hut on the right bank, and two rock clusters
# (right of the lower lake + bottom-right).
#
# River centre column per row (index 0 = top row) and its width per row.
# Vertical river that bulges into a lake between each pair of bridges.
RIVER_CENTERS = [17, 17, 17, 16, 16, 16, 16, 16, 16, 16,
                 16, 16, 16, 16, 16, 16, 16, 15, 15, 15,
                 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
                 15, 15, 15, 15, 15]
RIVER_WIDTHS = [6, 6, 7, 7, 8, 8, 10, 12, 13, 13,
                13, 13, 13, 13, 12, 12, 12, 11, 11, 11,
                11, 11, 11, 11, 11, 10, 10, 10, 10, 10,
                11, 11, 11, 12, 12]

# Forest belts (r0, c0, r1, c1) -- dark tree borders around the field
FORESTS = [
    (0, 0, 34, 4),     # left belt
    (0, 0, 6, 8),      # top-left extension
    (0, 32, 34, 34),   # right edge
    (0, 29, 3, 34),    # top-right corner above the houses
    (29, 0, 34, 9),    # bottom-left
    (30, 29, 34, 34),  # bottom-right
]

# Rocky cliffs (impassable terrain)
CLIFFS = [
    (19, 21, 23, 25),  # rock cluster right of the lower lake
    (28, 22, 33, 28),  # bottom-right rocks
]

# Roads (each entry = polyline of (r, c) waypoints, connected orthogonally)
# Sandy path down the right bank from the houses, plus a bridge-to-road link.
ROADS = [
    [(4, 30), (11, 31), (18, 29), (24, 26), (30, 23)],  # right-bank road
    [(17, 22), (18, 27)],                               # mid bridge east -> road
]

# Bridges (r0, c0, r1, c1) -- must span the river at each crossing
BRIDGES = [
    (4, 11, 5, 20),    # top bridge
    (16, 9, 17, 21),   # middle bridge
    (27, 10, 28, 20),  # bottom bridge
]

# Stone wall segments -- none in this map
WALLS = []

# Houses (large building footprints; r0, c0, r1, c1)
HOUSES = [
    (3, 24, 8, 29),    # top-right cluster, upper house
    (8, 23, 13, 28),   # top-right cluster, lower house (staggered)
    (15, 5, 18, 8),    # mid-left single house
    (15, 28, 16, 30),  # small hut on the right bank
]


def build_grid() -> list[list[str]]:
    """Paint every feature in z-order (later layers win)."""
    grid = blank_grid()

    for rect in FORESTS:
        paint_rect(grid, *rect, FOREST)
    for rect in CLIFFS:
        paint_rect(grid, *rect, CLIFF)
    for road in ROADS:
        paint_road(grid, road)
    paint_river(grid, RIVER_CENTERS, RIVER_WIDTHS)  # cuts roads -> needs bridges
    for rect in BRIDGES:
        paint_rect(grid, *rect, BRIDGE)
    for rect in WALLS:
        paint_rect(grid, *rect, WALL)
    for rect in HOUSES:
        paint_rect(grid, *rect, BUILDING)

    return grid


def main() -> None:
    grid = build_grid()
    out = {
        "name": "demo_village_battlefield",
        "grid_size": GRID,
        "cell_px": CELL_PX,
        "palette": PALETTE,
        "legend": "G=Grass R=Road F=Forest W=Water C=Cliff B=Building L=Wall D=Bridge",
        "base": ["".join(row) for row in grid],
    }

    dst = Path(__file__).resolve().parent / "demo_map.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # Console ASCII preview so you can eyeball the layout immediately.
    print(f"wrote {dst}  ({GRID}x{GRID}, {GRID * CELL_PX}px square)")
    print("legend:", out["legend"])
    print("+" + "-" * GRID + "+")
    for row in grid:
        print("|" + "".join(row) + "|")
    print("+" + "-" * GRID + "+")


if __name__ == "__main__":
    main()
