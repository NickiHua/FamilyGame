"""Render a big map image from a segmentation PNG using procedural base tiles.

Reads a seg image (flat color blocks on a 64px grid), maps each seg color to a
tile maker from gen_base_tiles, and stamps a freshly-generated 64px tile into
each cell (fresh RNG per cell -> variation, no obvious repetition, still seamless
within each cell). Objects (tree) are alpha-composited on top of their ground.

Run from repo root (venv with Pillow + numpy active):
  python scripts/tiles/render_seg.py [path-to-seg.png]
Default seg: scripts/tiles/segnew.png  ->  scripts/tiles/out/segnew_rendered.png
"""

from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image

import gen_base_tiles as gt

TILE = gt.TILE  # 64

# seg color (R,G,B) -> ("ground maker name", optional "object maker name")
COLOR_MAP: dict[tuple[int, int, int], tuple[str, str | None]] = {
    (124, 176, 76): ("grass", None),     # light green
    (47, 92, 47): ("grass", "tree"),     # dark green -> grass + tree object
    (60, 120, 200): ("water", None),     # blue river
    (201, 178, 124): ("road", None),     # tan path
    (150, 110, 70): ("bridge", None),    # medium brown bridge
    (96, 60, 56): ("house", None),       # dark brown house
    (180, 180, 185): ("rock", None),     # light grey rock
    (120, 110, 130): ("cliff", None),    # purple-grey cliff
}

GROUND_MAKERS = {
    "grass": gt.grass, "road": gt.road, "water": gt.water, "bridge": gt.bridge,
    "rock": gt.rock, "forest": gt.forest, "cliff": gt.cliff, "house": gt.house,
}
OBJECT_MAKERS = {"tree": gt.tree}


def _nearest_key(rgb: np.ndarray, keys: np.ndarray) -> int:
    d = np.sum((keys.astype(int) - rgb.astype(int)) ** 2, axis=1)
    return int(np.argmin(d))


def _components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    """4-connectivity connected components of True cells in a (gy, gx) mask."""
    gy, gx = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps: list[list[tuple[int, int]]] = []
    for sy in range(gy):
        for sx in range(gx):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            stack = [(sy, sx)]
            seen[sy, sx] = True
            cells: list[tuple[int, int]] = []
            while stack:
                cy, cx = stack.pop()
                cells.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < gy and 0 <= nx < gx and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            comps.append(cells)
    return comps


def _draw_building(out: Image.Image, x0: int, y0: int, x1: int, y1: int,
                   rng: np.random.Generator) -> None:
    """Draw one whole building filling the pixel bbox [x0,x1)x[y0,y1)."""
    w, h = x1 - x0, y1 - y0
    m = max(6, min(w, h) // 8)  # grass margin around the footprint
    fx0, fy0, fx1, fy1 = x0 + m, y0 + m, x1 - m, y1 - m
    fw, fh = fx1 - fx0, fy1 - fy0

    wall = (150, 120, 92)
    wall_dark = (120, 92, 68)
    roof = (150, 70, 56)
    roof_lit = (182, 96, 78)
    roof_dark = (112, 50, 40)

    px = out.load()
    roof_h = int(fh * 0.5)
    ridge = fy0 + 5
    eaves = fy0 + roof_h - 5
    base_strip = max(6, fh // 8)
    for y in range(fy0, fy1):
        for x in range(fx0, fx1):
            if y < fy0 + roof_h:
                if y < ridge:
                    c = roof_lit
                elif y > eaves:
                    c = roof_dark
                else:
                    c = roof
            elif y > fy1 - base_strip:
                c = wall_dark
            else:
                c = wall
            px[x, y] = c

    # doors + windows spaced along the wall, one per ~64px of width
    wall_top = fy0 + roof_h
    n = max(1, fw // 64)
    seg = fw / (n + 1)
    for i in range(1, n + 1):
        cx = int(fx0 + seg * i)
        # door
        for y in range(fy1 - max(12, fh // 5), fy1):
            for x in range(cx - 4, cx + 4):
                if fx0 <= x < fx1:
                    px[x, y] = (78, 54, 36)
        # window above the door
        wy = wall_top + 4
        for y in range(wy, wy + 8):
            for x in range(cx - 4, cx + 4):
                if fx0 <= x < fx1 and y < fy1:
                    px[x, y] = (96, 150, 170)


def main() -> None:
    seg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        "scripts", "tiles", "segnew.png")
    seg = np.array(Image.open(seg_path).convert("RGB"))
    h, w, _ = seg.shape
    gx, gy = w // TILE, h // TILE
    print(f"seg {w}x{h} -> grid {gx}x{gy} cells of {TILE}px")

    keys = np.array(list(COLOR_MAP.keys()))
    key_list = list(COLOR_MAP.keys())

    out = Image.new("RGBA", (gx * TILE, gy * TILE))
    rng = np.random.default_rng(20260616)
    house_mask = np.zeros((gy, gx), dtype=bool)

    for cy in range(gy):
        for cx in range(gx):
            block = seg[cy * TILE:(cy + 1) * TILE, cx * TILE:(cx + 1) * TILE]
            # dominant color in this cell
            cols, counts = np.unique(block.reshape(-1, 3), axis=0,
                                     return_counts=True)
            dom = cols[int(np.argmax(counts))]
            ki = _nearest_key(dom, keys)
            ground_name, obj_name = COLOR_MAP[key_list[ki]]

            # house cells become grass here; the whole building is drawn later
            if ground_name == "house":
                house_mask[cy, cx] = True
                ground_name, obj_name = "grass", None

            cell_rng = np.random.default_rng(int(rng.integers(2**31)))
            ground = GROUND_MAKERS[ground_name](cell_rng)
            tile_img = Image.fromarray(ground, "RGB").convert("RGBA")

            if obj_name:
                obj = OBJECT_MAKERS[obj_name](cell_rng)
                tile_img.alpha_composite(Image.fromarray(obj, "RGBA"))

            out.paste(tile_img, (cx * TILE, cy * TILE))

    # merge connected house cells into single buildings
    for cells in _components(house_mask):
        ys = [c[0] for c in cells]
        xs = [c[1] for c in cells]
        x0, y0 = min(xs) * TILE, min(ys) * TILE
        x1, y1 = (max(xs) + 1) * TILE, (max(ys) + 1) * TILE
        _draw_building(out, x0, y0, x1, y1,
                       np.random.default_rng(int(rng.integers(2**31))))

    os.makedirs(gt.OUT_DIR, exist_ok=True)
    stem = os.path.splitext(os.path.basename(seg_path))[0]
    out_path = os.path.join(gt.OUT_DIR, f"{stem}_rendered.png")
    out.convert("RGB").save(out_path)
    print(f"wrote {out_path}  ({out.width}x{out.height})")


if __name__ == "__main__":
    main()
