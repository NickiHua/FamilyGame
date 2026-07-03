#!/usr/bin/env python3
r"""gen_dual_tiles.py — build seamless 16-tile dual-grid sets for MANY terrains
from the same 3 hand-drawn masks (grass corner/half/3corners), each filled with
that terrain's own texture. No baked rim (seam layer is separate).

Masks (art/tiles/grass/, 64x64 alpha silhouette, grass reaches 42px on every mixed
edge = 10px overhang past the 32px midpoint -> seamless):
    grass_1_corner_mask.png    (bit 1  = TL)
    grass_1_half_mask.png      (bit 3  = top)
    grass_1_3corners_mask.png  (bit 7  = notch BR)
Bits: 1=TL 2=TR 4=BL 8=BR (matches DualGridBuilder).

Terrains + their fill textures are in TERRAINS below. Output for each:
    Assets/Art/Tiles/<name>_dual/00.png .. 15.png  (+ old ones backed up)

Run (CWD = FamilyGame/):
    .\.venv\Scripts\python.exe scripts\tiles\gen_dual_tiles.py
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

TILE = 64
MASK_DIR = Path("art/tiles/grass")

# terrain name -> fill texture (any size; tiled if smaller, cropped if larger)
TERRAINS = {
    "grass": "Assets/Art/Tiles/grass.png",
    "road": "Assets/Art/Tiles/road.png",
    "dirt": "Assets/Art/Tiles/dirt.png",
    "water": "art/tiles/water/water_1_128.png",
}

R90 = Image.Transpose.ROTATE_90
R180 = Image.Transpose.ROTATE_180
R270 = Image.Transpose.ROTATE_270


def load_alpha(name: str) -> Image.Image:
    im = Image.open(MASK_DIR / name).convert("RGBA")
    if im.size != (TILE, TILE):
        im = im.resize((TILE, TILE), Image.NEAREST)
    return im.split()[3]


def rot(a, t):
    return a if t is None else a.transpose(t)


def clip_half(rgba, dirn):
    """Erase the OVERHANGING half of a border tile (alpha->0): L/R/T/B = which map edge it
    sits on (left edge overhangs left, etc.). Keeps the inner half so the border blend shows
    up to the map rectangle with no tile sticking out past it."""
    mask = Image.new("L", (TILE, TILE), 255)
    dr = ImageDraw.Draw(mask)
    if dirn == "L":   dr.rectangle([0, 0, TILE // 2 - 1, TILE - 1], fill=0)
    elif dirn == "R": dr.rectangle([TILE // 2, 0, TILE - 1, TILE - 1], fill=0)
    elif dirn == "T": dr.rectangle([0, 0, TILE - 1, TILE // 2 - 1], fill=0)
    elif dirn == "B": dr.rectangle([0, TILE // 2, TILE - 1, TILE - 1], fill=0)
    out = rgba.copy()
    out.putalpha(ImageChops.multiply(rgba.split()[3], mask))
    return out


def union(a, b):
    return ImageChops.lighter(a, b)


def fit_64(tex: Image.Image) -> Image.Image:
    """Return a 64x64 fill: tile up if smaller, crop top-left if larger."""
    if tex.size == (TILE, TILE):
        return tex
    if tex.size[0] < TILE or tex.size[1] < TILE:
        out = Image.new("RGBA", (TILE, TILE))
        for y in range(0, TILE, tex.size[1]):
            for x in range(0, TILE, tex.size[0]):
                out.alpha_composite(tex, (x, y))
        return out
    return tex.crop((0, 0, TILE, TILE))


def silhouettes():
    corner = load_alpha("grass_1_corner_mask.png")
    half = load_alpha("grass_1_half_mask.png")
    three = load_alpha("grass_1_3corners_mask.png")
    full = Image.new("L", (TILE, TILE), 255)
    empty = Image.new("L", (TILE, TILE), 0)
    return {
        0: empty,
        1: rot(corner, None), 4: rot(corner, R90), 8: rot(corner, R180), 2: rot(corner, R270),
        3: rot(half, None), 5: rot(half, R90), 12: rot(half, R180), 10: rot(half, R270),
        7: rot(three, None), 13: rot(three, R90), 14: rot(three, R180), 11: rot(three, R270),
        6: union(rot(corner, R270), rot(corner, R90)),
        9: union(rot(corner, None), rot(corner, R180)),
        15: full,
    }


def main() -> None:
    silh = silhouettes()
    stamp = time.strftime("%H%M%S")
    for name, tex_path in TERRAINS.items():
        p = Path(tex_path)
        if not p.is_file():
            print(f"[skip] {name}: texture not found {tex_path}")
            continue
        fill = fit_64(Image.open(p).convert("RGBA"))
        out_dir = Path(f"Assets/Art/Tiles/{name}_dual")
        out_dir.mkdir(parents=True, exist_ok=True)

        existing = list(out_dir.glob("[0-1][0-9].png"))
        if existing:
            bak = Path("art_undecided/tiles") / f"{name}_dual_backup_{stamp}"
            bak.mkdir(parents=True, exist_ok=True)
            for q in existing:
                shutil.copy2(q, bak / q.name)

        for b in range(16):
            t = fill.copy()
            t.putalpha(silh[b])
            t.save(out_dir / f"{b:02d}.png")
        # Half-clipped BORDER variants. After OOB-clamping, border-ring cells only ever use
        # bits 3/12 (vertical L/R edges) or 5/10 (horizontal T/B edges); clip the overhang half
        # so the map edge stays a clean rectangle. Named e.g. 03L.png / 05T.png.
        for b, dirs in ((3, "LR"), (12, "LR"), (5, "TB"), (10, "TB")):
            full = fill.copy()
            full.putalpha(silh[b])
            for dirn in dirs:
                clip_half(full, dirn).save(out_dir / f"{b:02d}{dirn}.png")
        print(f"[ok] {name}: 16 tiles + 8 border clips -> {out_dir}")


if __name__ == "__main__":
    main()
