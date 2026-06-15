#!/usr/bin/env python3
"""Render the demo map JSON into control images for ComfyUI / Flux ControlNet.

Reads ``scripts/map/demo_map.json`` (produced by ``build_demo_map.py``) and
writes, into ``scripts/map/out/``:

  seg.png       semantic segmentation (flat RGB per terrain) -- img2img init
                or a segmentation-ControlNet / reference image
  walkable.png  white = a ground unit may stand here, black = blocked
                (debug + feeds the Unity logic layer)
  depth.png     greyscale height map -- feeds a Flux **Depth** ControlNet
  canny.png     white structural edges on black -- feeds a **Canny** ControlNet
  preview.png   seg + grid lines + legend, for human eyeballing only

Deps: Pillow + numpy (already present in any ComfyUI environment).

Run (CWD = FamilyGame/):
    python scripts/map/render_map.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    sys.exit(
        "Missing deps. In your ComfyUI Python env run:\n"
        "    pip install pillow numpy"
    )

HERE = Path(__file__).resolve().parent
MAP_JSON = HERE / "demo_map.json"
OUT_DIR = HERE / "out"


def load_map() -> dict:
    if not MAP_JSON.exists():
        sys.exit(f"{MAP_JSON} not found -- run build_demo_map.py first.")
    return json.loads(MAP_JSON.read_text(encoding="utf-8"))


def cells(data: dict):
    """Yield (r, c, code) for every cell in the base grid."""
    for r, row in enumerate(data["base"]):
        for c, code in enumerate(row):
            yield r, c, code


def render_seg(data: dict) -> Image.Image:
    """Flat per-terrain RGB blocks at full resolution."""
    n, px = data["grid_size"], data["cell_px"]
    pal = data["palette"]
    img = np.zeros((n * px, n * px, 3), dtype=np.uint8)
    for r, c, code in cells(data):
        rgb = pal[code]["rgb"]
        img[r * px:(r + 1) * px, c * px:(c + 1) * px] = rgb
    return Image.fromarray(img, "RGB")


def render_walkable(data: dict) -> Image.Image:
    n, px = data["grid_size"], data["cell_px"]
    pal = data["palette"]
    img = np.zeros((n * px, n * px), dtype=np.uint8)
    for r, c, code in cells(data):
        if pal[code]["walkable"]:
            img[r * px:(r + 1) * px, c * px:(c + 1) * px] = 255
    return Image.fromarray(img, "L")


def render_depth(data: dict) -> Image.Image:
    n, px = data["grid_size"], data["cell_px"]
    pal = data["palette"]
    img = np.zeros((n * px, n * px), dtype=np.uint8)
    for r, c, code in cells(data):
        img[r * px:(r + 1) * px, c * px:(c + 1) * px] = pal[code]["height"]
    return Image.fromarray(img, "L")


def render_canny(data: dict) -> Image.Image:
    """White line wherever a cell differs from its right/down neighbour."""
    n, px = data["grid_size"], data["cell_px"]
    grid = data["base"]
    edges = np.zeros((n * px, n * px), dtype=np.uint8)
    for r in range(n):
        for c in range(n):
            code = grid[r][c]
            # vertical boundary (right neighbour)
            if c + 1 < n and grid[r][c + 1] != code:
                x = (c + 1) * px
                edges[r * px:(r + 1) * px, x - 1:x + 1] = 255
            # horizontal boundary (down neighbour)
            if r + 1 < n and grid[r + 1][c] != code:
                y = (r + 1) * px
                edges[y - 1:y + 1, c * px:(c + 1) * px] = 255
    return Image.fromarray(edges, "L")


def render_preview(data: dict, seg: Image.Image) -> Image.Image:
    """Seg image + thin grid lines + a legend strip on the right."""
    n, px = data["grid_size"], data["cell_px"]
    pal = data["palette"]
    legend_w = 320
    canvas = Image.new("RGB", (seg.width + legend_w, seg.height), (24, 24, 24))
    canvas.paste(seg, (0, 0))
    draw = ImageDraw.Draw(canvas)

    # grid lines every cell, bolder every 5 cells
    for i in range(n + 1):
        col = (255, 255, 255) if i % 5 == 0 else (0, 0, 0)
        w = 2 if i % 5 == 0 else 1
        draw.line([(i * px, 0), (i * px, seg.height)], fill=col, width=w)
        draw.line([(0, i * px), (seg.width, i * px)], fill=col, width=w)

    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()

    x0 = seg.width + 24
    draw.text((x0, 20), f"{data['name']}", fill=(255, 255, 255), font=font)
    draw.text((x0, 52), f"{n}x{n}  cell={px}px", fill=(200, 200, 200), font=font)
    y = 100
    for code, attr in pal.items():
        draw.rectangle([x0, y, x0 + 28, y + 28], fill=tuple(attr["rgb"]),
                       outline=(255, 255, 255))
        walk = "walk" if attr["walkable"] else "block"
        draw.text((x0 + 40, y + 2),
                  f"{code} {attr['name']} ({walk})",
                  fill=(230, 230, 230), font=font)
        y += 40
    return canvas


def main() -> None:
    data = load_map()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    seg = render_seg(data)
    seg.save(OUT_DIR / "seg.png")
    # Softened seg: blurs the hard block edges so a high-denoise img2img run
    # (0.8-0.85) can go painterly instead of locking onto pixel blocks.
    blur_radius = max(8, data["cell_px"] // 2)
    seg.filter(ImageFilter.GaussianBlur(blur_radius)).save(OUT_DIR / "seg_soft.png")
    render_walkable(data).save(OUT_DIR / "walkable.png")
    render_depth(data).save(OUT_DIR / "depth.png")
    render_canny(data).save(OUT_DIR / "canny.png")
    render_preview(data, seg).save(OUT_DIR / "preview.png")

    side = data["grid_size"] * data["cell_px"]
    print(f"rendered {side}x{side}px control images into {OUT_DIR}")
    for name in ("seg", "seg_soft", "walkable", "depth", "canny", "preview"):
        print(f"  - {name}.png")


if __name__ == "__main__":
    main()
