#!/usr/bin/env python3
"""Render stage1_marker_map.json with DUAL-GRID blended terrain (not flat tiles).

Replicates DualGridBuilder.cs in Python: flat base ground + 3 ascending edge layers
(road<dirt<grass), half-cell offset, 16 corner configs, border-clip variants. Marker
cells (H/T/K/P) are treated as grass for terrain, then drawn as solid color blocks +
a big letter per region on top (same as render_marker_map.py) so it's usable as a
Seedream layout ref.

30x30x64 = 1920x1920. Output -> art/experiments/stage1_marker_dualgrid_1920.png
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
MAP = json.loads((ROOT / "Assets/Art/Maps/stage1_marker_map.json").read_text(encoding="utf-8"))
CELL = MAP["cell_px"]
W, H = MAP["grid_w"], MAP["grid_h"]
base = MAP["base"]
TD = ROOT / "Assets/Art/Tiles"

MARKER = {"H": (74, 47, 27), "T": (28, 74, 38), "K": (130, 130, 130), "P": (150, 95, 50)}


def terr(c):
    return "G" if c in MARKER else c


def cell_letter(cx, cy):  # world cell (y up), clamped to edges
    cx = min(max(cx, 0), W - 1)
    cy = min(max(cy, 0), H - 1)
    return terr(base[H - 1 - cy][cx])


def prio(c):
    if c in ("W", "D"):
        return 0
    if c == "R":
        return 1
    if c == "I":
        return 2
    return 3


grass = Image.open(TD / "grass.png").convert("RGBA")
road = Image.open(TD / "road.png").convert("RGBA")
dirt = Image.open(TD / "dirt.png").convert("RGBA")
water = [Image.open(TD / f"water_base_{i}.png").convert("RGBA") for i in (1, 2, 3, 4)]
BASE = {"G": grass, "B": grass, "S": grass, "I": dirt, "R": road}

img = Image.new("RGBA", (W * CELL, H * CELL), (95, 140, 80, 255))

# 1) flat base ground (markers -> grass; water -> 2x2 blue set)
for r in range(H):
    for x in range(W):
        c = base[r][x]
        tc = terr(c)
        px, py = x * CELL, r * CELL
        if tc == "W":
            t = water[(x & 1) + ((r & 1) << 1)]
        else:
            t = BASE.get(tc, grass)
        pw, ph = t.size
        img.paste(t.crop((px % pw, py % ph, px % pw + CELL, py % ph + CELL)), (px, py))


def load_dual(name):
    d = {}
    for b in range(1, 15):
        p = TD / f"{name}_dual" / f"{b:02d}.png"
        if p.exists():
            d[f"{b:02d}"] = Image.open(p).convert("RGBA")
    for var in ("03L", "03R", "05B", "05T", "10B", "10T", "12L", "12R"):
        p = TD / f"{name}_dual" / f"{var}.png"
        if p.exists():
            d[var] = Image.open(p).convert("RGBA")
    return d


DUAL = {n: load_dual(n) for n in ("road", "dirt", "grass")}

# 2) dual-grid edge layers, ascending priority (higher drawn on top)
for name, pr in (("road", 1), ("dirt", 2), ("grass", 3)):
    tiles = DUAL[name]
    for y in range(-1, H):      # world y up
        for x in range(-1, W):
            def on(cx, cy):
                return prio(cell_letter(cx, cy)) >= pr
            bits = ((1 if on(x, y + 1) else 0) | (2 if on(x + 1, y + 1) else 0)
                    | (4 if on(x, y) else 0) | (8 if on(x + 1, y) else 0))
            if bits in (0, 15):
                continue
            key = f"{bits:02d}"
            clip = None
            if x == -1:
                clip = f"{key}L"
            elif x == W - 1:
                clip = f"{key}R"
            elif y == -1:
                clip = f"{key}B"
            elif y == H - 1:
                clip = f"{key}T"
            tile = (tiles.get(clip) if clip else None) or tiles.get(key)
            if tile is None:
                continue
            px = CELL * x + CELL // 2                 # corner between the 4 cells
            py = CELL * (H - y - 1) - CELL // 2
            img.paste(tile, (px, py), tile)

# 3) marker color blocks + one big letter per region (H/T/S/B)
draw = ImageDraw.Draw(img)
for r in range(H):
    for x in range(W):
        if base[r][x] in MARKER:
            draw.rectangle([x * CELL, r * CELL, (x + 1) * CELL - 1, (r + 1) * CELL - 1],
                           fill=MARKER[base[r][x]] + (255,))

DISPLAY = {"H": "H", "T": "T", "K": "S", "P": "B"}
FONTS = ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/Arial.ttf"]


def load_font(size):
    for p in FONTS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


grid = np.array([list(row) for row in base])
for internal, disp in DISPLAY.items():
    mask = grid == internal
    if not mask.any():
        continue
    lbl, n = ndimage.label(mask)
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        fs = max(30, min(int(min((xs.max() - xs.min() + 1), (ys.max() - ys.min() + 1)) * CELL * 0.8), 130))
        font = load_font(fs)
        sw = max(2, fs // 12)
        bb = draw.textbbox((0, 0), disp, font=font, stroke_width=sw)
        cx = (xs.mean() + 0.5) * CELL
        cy = (ys.mean() + 0.5) * CELL
        draw.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), disp,
                  font=font, fill=(255, 255, 255, 255), stroke_width=sw, stroke_fill=(0, 0, 0, 255))

out = ROOT / "art/experiments/stage1_marker_dualgrid_1920.png"
out.parent.mkdir(parents=True, exist_ok=True)
img.convert("RGB").save(out)
print(f"saved {out.relative_to(ROOT)}  {img.size}")
