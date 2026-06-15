#!/usr/bin/env python3
"""Composite the CURRENT logic grid (Assets/Art/Maps/demo_map.json) onto the
painted art so blocked vs walkable cells can be reconciled pixel-accurately.

Writes scripts/map/out/demo_blocked_overlay.png (+ a downscaled _view copy):
  - blocked cells (W/C/B/L) tinted by type, walkable bridge (D) tinted green
  - every cell labelled with its terrain letter
  - coordinate labels (c#, r#) every 5 cells; row 0 = TOP, col 0 = LEFT

Run (CWD = FamilyGame/):
    python scripts/map/overlay_blocked.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

JSON = Path("Assets/Art/Maps/demo_map.json")
SRC = Path("art/maps/demo_map.png")
OUT_FULL = Path("scripts/map/out/demo_blocked_overlay.png")
OUT_VIEW = Path("scripts/map/out/demo_blocked_overlay_view.png")
VIEW_WIDTH = 1600

WALKABLE = set("GRD")
TINT = {
    "W": (60, 120, 230, 120),   # water    - blue
    "C": (160, 160, 170, 130),  # cliff    - gray
    "B": (170, 60, 50, 130),    # building - red/brown
    "L": (245, 245, 250, 130),  # wall     - white
    "F": (20, 80, 20, 110),     # forest   - dark green (now blocked)
    "D": (40, 220, 90, 90),     # bridge   - green (walkable highlight)
}


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    data = json.loads(JSON.read_text(encoding="utf-8"))
    size = data["grid_size"]
    base = data["base"]

    img = Image.open(SRC).convert("RGBA")
    w, h = img.size
    cw, ch = w / size, h / size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    font = load_font(int(ch * 0.45))
    coord_font = load_font(int(ch * 0.7))

    for r in range(size):          # json row, 0 = top
        row = base[r]
        for x in range(size):
            t = row[x]
            x0, y0 = x * cw, r * ch
            if t in TINT:
                d.rectangle([x0, y0, x0 + cw, y0 + ch], fill=TINT[t])
            d.rectangle([x0, y0, x0 + cw, y0 + ch], outline=(0, 0, 0, 70))
            col = (255, 255, 0, 255) if t not in WALKABLE else (255, 255, 255, 180)
            d.text((x0 + cw * 0.30, y0 + ch * 0.22), t, fill=col, font=font)

    # Bold lines + coordinate labels every 5 cells.
    for i in range(0, size + 1, 5):
        x, y = round(i * cw), round(i * ch)
        d.line([(x, 0), (x, h)], fill=(255, 40, 40, 220), width=3)
        d.line([(0, y), (w, y)], fill=(255, 40, 40, 220), width=3)
    for i in range(0, size, 5):
        d.text((round(i * cw + 2), 2), f"c{i}", fill=(255, 255, 0, 255), font=coord_font)
        d.text((2, round(i * ch + 2)), f"r{i}", fill=(255, 255, 0, 255), font=coord_font)

    out = Image.alpha_composite(img, overlay).convert("RGB")
    OUT_FULL.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT_FULL)
    scale = VIEW_WIDTH / w
    out.resize((VIEW_WIDTH, round(h * scale)), Image.LANCZOS).save(OUT_VIEW)
    print(f"Wrote {OUT_FULL} ({w}x{h}) and {OUT_VIEW}")


if __name__ == "__main__":
    main()
