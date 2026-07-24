#!/usr/bin/env python3
"""Render the MARKER layout (stage1_marker_map.json) to a flat 1920x1920 PNG.

Terrain cells use the flat tile textures (grass/road/dirt/sand/water); object markers
are filled as SOLID color blocks (NO letters) so the map is ready to feed Seedream as a
layout ref. Marker colors match scripts/tiles/gen_marker_tiles.py.

Grid is 30x30, cell 64px -> 1920x1920 exactly.
Output -> art/experiments/stage1_marker_render_1920.png
"""
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
MAP = json.loads((ROOT / "Assets/Art/Maps/stage1_marker_map.json").read_text(encoding="utf-8"))

CELL = MAP["cell_px"]
W, H = MAP["grid_w"], MAP["grid_h"]
base = MAP["base"]

TILE_DIR = ROOT / "Assets/Art/Tiles"
# terrain letter -> flat tile png
TERRAIN = {
    "G": "grass.png", "R": "road.png", "I": "dirt.png", "S": "sand.png", "D": "bridge.png",
}
# water uses the 2x2 blue set
WATER = [f"water_base_{i}.png" for i in (1, 2, 3, 4)]

# marker letter -> solid RGB (matches gen_marker_tiles.py)
MARKER = {
    "H": (74, 47, 27),    # house  深棕
    "T": (28, 74, 38),    # tree   深绿
    "K": (130, 130, 130),  # stone  灰
    "P": (150, 95, 50),   # bridge 棕
}

tiles = {k: Image.open(TILE_DIR / fn).convert("RGBA") for k, fn in TERRAIN.items()}
water = [Image.open(TILE_DIR / fn).convert("RGBA") for fn in WATER]

print("cell counts:", dict(Counter("".join(base))))

img = Image.new("RGBA", (W * CELL, H * CELL), (95, 140, 80, 255))
for r in range(H):
    for x in range(W):
        c = base[r][x]
        px, py = x * CELL, r * CELL
        if c in MARKER:
            img.paste(Image.new("RGBA", (CELL, CELL), MARKER[c] + (255,)), (px, py))
            continue
        if c == "W":
            t = water[(x & 1) + ((r & 1) << 1)]
        else:
            t = tiles.get(c, tiles["G"])
        pw, ph = t.size
        sxp, syp = px % pw, py % ph
        cell = t.crop((sxp, syp, sxp + CELL, syp + CELL))
        img.paste(cell, (px, py), cell)

# --- label each object region with a big letter (H house / T tree / S stone / B bridge) ---
# internal json letter -> displayed letter the user wants
DISPLAY = {"H": "H", "T": "T", "K": "S", "P": "B"}
FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def load_font(size):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


draw = ImageDraw.Draw(img)
grid = np.array([list(row) for row in base])  # (H, W), row 0 = top
for internal, disp in DISPLAY.items():
    mask = grid == internal
    if not mask.any():
        continue
    lbl, n = ndimage.label(mask)  # 4-connectivity
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        cw = (xs.max() - xs.min() + 1) * CELL
        ch = (ys.max() - ys.min() + 1) * CELL
        cx = (xs.mean() + 0.5) * CELL
        cy = (ys.mean() + 0.5) * CELL
        fs = int(min(cw, ch) * 0.8)
        fs = max(30, min(fs, 130))
        font = load_font(fs)
        sw = max(2, fs // 12)
        bb = draw.textbbox((0, 0), disp, font=font, stroke_width=sw)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        draw.text((cx - tw / 2 - bb[0], cy - th / 2 - bb[1]), disp, font=font,
                  fill=(255, 255, 255, 255), stroke_width=sw, stroke_fill=(0, 0, 0, 255))

out = ROOT / "art/experiments/stage1_marker_render_1920.png"
out.parent.mkdir(parents=True, exist_ok=True)
img.convert("RGB").save(out)
print(f"saved {out.relative_to(ROOT)}  {img.size}")
