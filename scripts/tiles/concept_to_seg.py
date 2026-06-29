"""Mechanical FIRST-DRAFT: turn a painterly concept map into a coarse SRPG segment.

Downsamples the concept to a GRID x GRID grid (averaging), classifies each cell
into a terrain code by colour heuristics, and writes a seg.png (GRID*64 px) using
render_seg's seg-colour palette so render_seg_dual.py can render it.

This is intentionally ROUGH (painterly greens overlap; coloured roofs may be
misread). It is a starting canvas to be hand-corrected, not a final map.

Run from repo root:
  python scripts/tiles/concept_to_seg.py [concept.png] [GRID]
"""

from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image

GRID = 35
CELL = 64

# terrain code -> seg colour (must match render_seg.COLOR_MAP keys)
SEG = {
    "grass": (124, 176, 76),
    "forest": (47, 92, 47),
    "water": (60, 120, 200),
    "road": (201, 178, 124),
    "house": (96, 60, 56),
    "rock": (180, 180, 185),
}


def classify(r: int, g: int, b: int) -> str:
    mx, mn = max(r, g, b), min(r, g, b)
    sat = mx - mn
    bright = (r + g + b) / 3
    # water: blue clearly dominant
    if b == mx and b > 95 and b - g > 8 and b - r > 20:
        return "water"
    # grey/light -> rock
    if sat < 26 and bright > 118:
        return "rock"
    # reddish/brown roof -> house
    if r == mx and r - g > 32 and r - b > 32 and bright < 160:
        return "house"
    # dark green -> forest
    if g >= r and g > b and bright < 100:
        return "forest"
    # tan / dirt road
    if r >= g >= b and r - b > 38 and bright > 110:
        return "road"
    # green -> grass (also catches yellow-green crop fields)
    if g >= b:
        return "grass"
    return "grass"


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        "art_undecided", "maps", "concept_village.png")
    grid = int(sys.argv[2]) if len(sys.argv) > 2 else GRID
    img = Image.open(src).convert("RGB").resize((grid, grid), Image.BILINEAR)
    arr = np.array(img)

    seg = np.empty((grid * CELL, grid * CELL, 3), dtype=np.uint8)
    codes = np.empty((grid, grid), dtype=object)
    for cy in range(grid):
        for cx in range(grid):
            r, g, b = (int(v) for v in arr[cy, cx])
            code = classify(r, g, b)
            codes[cy, cx] = code
            seg[cy * CELL:(cy + 1) * CELL, cx * CELL:(cx + 1) * CELL] = SEG[code]

    out_dir = os.path.join("art_undecided", "maps")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "concept_village_seg.png")
    Image.fromarray(seg, "RGB").save(out)
    # quick histogram so we can sanity-check the classification spread
    uniq, cnt = np.unique(codes.astype(str), return_counts=True)
    print("wrote", out, f"({grid}x{grid})")
    for u, c in sorted(zip(uniq, cnt), key=lambda t: -t[1]):
        print(f"  {u:7s} {c}")


if __name__ == "__main__":
    main()
