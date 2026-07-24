#!/usr/bin/env python3
"""Compose the 6 object/style refs into ONE labeled 'sample' sheet for Seedream.

Each cell has a colored label band matching its marker color so Seedream can bind
"this colored block in the layout" -> "draw it like this art". Feeding ONE sheet
(+ the marker layout) instead of 6 separate refs keeps Seedream from getting confused.

Output -> art/maps/map_raw/sample.png
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art/maps/map_raw"
FONT_PATH = ROOT / "Assets/Art/UI/fonts/NotoSansSC-Regular.ttf"

# (file, label, band color) — band color = the marker color it maps to
CELLS = [
    ("sample_edge_transision", "EDGE 接壤过渡 / 风格", (60, 60, 60)),
    ("sample_house_gpt",       "H = 房子 HOUSE",        (74, 47, 27)),
    ("sample_farmland",        "农田 FARMLAND (dirt 红棕块)", (110, 66, 43)),
    ("sample_tree_crop",       "T = 树 TREE",           (28, 74, 38)),
    ("sample_stone",           "S = 石头 STONE",         (130, 130, 130)),
    ("sample_bridge",          "B = 桥 BRIDGE",          (150, 95, 50)),
]

COLS = 2
IMG_W, IMG_H = 820, 720
BAND_H = 66
PAD = 18
font = ImageFont.truetype(str(FONT_PATH), 36)

rows = (len(CELLS) + COLS - 1) // COLS
cell_w = IMG_W
cell_h = BAND_H + IMG_H
sheet_w = PAD + COLS * (cell_w + PAD)
sheet_h = PAD + rows * (cell_h + PAD)

sheet = Image.new("RGB", (sheet_w, sheet_h), (245, 245, 245))
draw = ImageDraw.Draw(sheet)

for i, (name, label, band) in enumerate(CELLS):
    cx = PAD + (i % COLS) * (cell_w + PAD)
    cy = PAD + (i // COLS) * (cell_h + PAD)
    # label band
    draw.rectangle([cx, cy, cx + cell_w, cy + BAND_H], fill=band)
    bb = draw.textbbox((0, 0), label, font=font, stroke_width=2)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((cx + 16, cy + (BAND_H - th) / 2 - bb[1]), label, font=font,
              fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    # image (letterboxed, centered)
    im = Image.open(SRC / f"{name}.png").convert("RGB")
    im.thumbnail((IMG_W - 12, IMG_H - 12))
    ox = cx + (cell_w - im.width) // 2
    oy = cy + BAND_H + (IMG_H - im.height) // 2
    sheet.paste(im, (ox, oy))
    draw.rectangle([cx, cy, cx + cell_w, cy + cell_h], outline=(120, 120, 120), width=2)

out = SRC / "sample.png"
sheet.save(out)
print(f"saved {out.relative_to(ROOT)}  {sheet.size}")
