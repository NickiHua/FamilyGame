#!/usr/bin/env python3
r"""gen_grass_dual_from_masks.py — build a seamless 16-tile grass dual-grid set
from 3 HAND-DRAWN masks (no procedural noise, no baked rim).

Hand-drawn masks (art/tiles/grass/, 64x64, alpha = grass silhouette; grass reaches
42px on every MIXED edge = a 10px overhang past the 32px midpoint, so all tiles
share the same edge crossing and tile seamlessly):
    grass_1_corner_mask.png    grass in the TOP-LEFT corner       (bit 1)
    grass_1_half_mask.png      grass in the TOP half              (bits 1+2 = 3)
    grass_1_3corners_mask.png  grass everywhere but a BR notch    (bits 1+2+4 = 7)

Bit layout (matches DualGridBuilder.BuildGrassEdges): 1=TL 2=TR 4=BL 8=BR.
Every 16 combo = one mask rotated, or (the 2 diagonals) two corner masks unioned.
The silhouette is filled with the tileable grass texture; NO dark outline — the
seam/rim is a separate hand-authored layer (design decision 2026-07-01).

Output: Assets/Art/Tiles/grass_dual/00.png .. 15.png (where DualGridBuilder reads
them) + a check grid art_undecided/tiles/grass_dual_new/_grid16.png. The previous
PNGs are backed up first.

Run (CWD = FamilyGame/):
    .\.venv\Scripts\python.exe scripts\tiles\gen_grass_dual_from_masks.py
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

from PIL import Image, ImageChops

TILE = 64
MASK_DIR = Path("art/tiles/grass")
GRASS_TEX = Path("Assets/Art/Tiles/grass.png")
OUT_DIR = Path("Assets/Art/Tiles/grass_dual")
REVIEW_DIR = Path("art_undecided/tiles/grass_dual_new")

R90 = Image.Transpose.ROTATE_90    # 90 CCW
R180 = Image.Transpose.ROTATE_180
R270 = Image.Transpose.ROTATE_270  # 90 CW


def load_alpha(name: str) -> Image.Image:
    im = Image.open(MASK_DIR / name).convert("RGBA")
    if im.size != (TILE, TILE):
        im = im.resize((TILE, TILE), Image.NEAREST)
    return im.split()[3]


def rot(a: Image.Image, t):
    return a if t is None else a.transpose(t)


def union(a: Image.Image, b: Image.Image):
    return ImageChops.lighter(a, b)


def main() -> None:
    corner = load_alpha("grass_1_corner_mask.png")    # bit 1  (TL)
    half = load_alpha("grass_1_half_mask.png")        # bit 3  (top)
    three = load_alpha("grass_1_3corners_mask.png")   # bit 7  (notch BR)

    full = Image.new("L", (TILE, TILE), 255)
    empty = Image.new("L", (TILE, TILE), 0)

    silh = {
        0: empty,
        1: rot(corner, None),   # TL
        4: rot(corner, R90),    # TL->BL
        8: rot(corner, R180),   # TL->BR
        2: rot(corner, R270),   # TL->TR
        3: rot(half, None),     # top
        5: rot(half, R90),      # left   (1+4)
        12: rot(half, R180),    # bottom (4+8)
        10: rot(half, R270),    # right  (2+8)
        7: rot(three, None),    # notch BR
        11: rot(three, R90),    # notch BL (1+2+8)
        14: rot(three, R180),   # notch TL (2+4+8)
        13: rot(three, R270),   # notch TR (1+4+8)
        6: union(rot(corner, R270), rot(corner, R90)),   # TR+BL
        9: union(rot(corner, None), rot(corner, R180)),  # TL+BR
        15: full,
    }

    grass = Image.open(GRASS_TEX).convert("RGBA")
    if grass.size != (TILE, TILE):
        tiled = Image.new("RGBA", (TILE, TILE))
        for y in range(0, TILE, grass.size[1]):
            for x in range(0, TILE, grass.size[0]):
                tiled.alpha_composite(grass, (x, y))
        grass = tiled

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(OUT_DIR.glob("[0-1][0-9].png"))
    if existing:
        bak = REVIEW_DIR.parent / f"grass_dual_backup_{time.strftime('%H%M%S')}"
        bak.mkdir(parents=True, exist_ok=True)
        for p in existing:
            shutil.copy2(p, bak / p.name)
        print(f"[backup] {len(existing)} old tiles -> {bak}")

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for b in range(16):
        tile = grass.copy()
        tile.putalpha(silh[b])
        tile.save(OUT_DIR / f"{b:02d}.png")
    print(f"[ok] wrote 16 tiles -> {OUT_DIR}")

    order = [1, 2, 4, 8, 3, 5, 10, 12, 6, 9, 7, 11, 13, 14]
    bg = Image.new("RGBA", (TILE * 8, TILE * 2), (120, 80, 45, 255))
    for i, b in enumerate(order):
        bg.alpha_composite(Image.open(OUT_DIR / f"{b:02d}.png"), ((i % 8) * TILE, (i // 8) * TILE))
    (REVIEW_DIR).mkdir(parents=True, exist_ok=True)
    bg.save(REVIEW_DIR / "_grid16.png")
    print(f"[ok] check grid -> {REVIEW_DIR / '_grid16.png'}")


if __name__ == "__main__":
    main()
