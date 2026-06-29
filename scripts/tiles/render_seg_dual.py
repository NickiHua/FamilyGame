"""Render the seg map with DUAL-GRID layered ground transitions (vs hard stamping).

Ground terrains (water/road/grass/rock/cliff) are composited by PRIORITY using
the dual-grid corner rule: each terrain rounds smoothly over everything lower,
so coastlines / road edges curve instead of showing square seams. NO transition
art is authored -- the 16 corner shapes are produced by the bilinear-corner math
at render time, sampling each terrain's existing flat 64px tile.

Objects (trees on forest cells, bridges over water, houses) are drawn on top,
exactly like render_seg.py.

Outputs into scripts/tiles/out/:
  <stem>_dual.png         dual-grid, grass meets water directly
  <stem>_dual_band.png    same + a tan sand band on grass/water shorelines

Run from repo root (venv with Pillow + numpy active):
  python scripts/tiles/render_seg_dual.py [path-to-seg.png]
Default seg: scripts/tiles/segnew.png
"""

from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image

import gen_base_tiles as gt
from render_seg import (COLOR_MAP, _components, _draw_building, _nearest_key)

TILE = gt.TILE  # 64
SAND = np.array([206, 184, 130], dtype=np.uint8)

# ground_name (from render_seg.COLOR_MAP) -> the ground category actually rendered
GROUND_OF = {
    "grass": "grass", "road": "road", "water": "water", "bridge": "water",
    "house": "grass", "rock": "rock", "cliff": "cliff", "forest": "grass",
}
# low number = lower layer (everything rounds OVER lower layers)
PRIORITY = {"water": 0, "road": 1, "grass": 2, "rock": 3, "cliff": 3}
MAKER = {"water": gt.water, "road": gt.road, "grass": gt.grass,
         "rock": gt.rock, "cliff": gt.cliff}


def _stamp_full(maker, gh: int, gw: int, seed: int) -> np.ndarray:
    """Tile a fresh base tile per cell across the whole map (variation, seamless)."""
    rng = np.random.default_rng(seed)
    out = np.empty((gh * TILE, gw * TILE, 3), dtype=np.uint8)
    for cy in range(gh):
        for cx in range(gw):
            out[cy * TILE:(cy + 1) * TILE, cx * TILE:(cx + 1) * TILE] = maker(rng)
    return out


def _dual_field(mask: np.ndarray) -> np.ndarray:
    gh, gw = mask.shape
    H, W = gh * TILE, gw * TILE
    py = np.arange(H) / TILE - 0.5
    px = np.arange(W) / TILE - 0.5
    PX, PY = np.meshgrid(px, py)
    x0 = np.clip(np.floor(PX).astype(int), 0, gw - 1)
    y0 = np.clip(np.floor(PY).astype(int), 0, gh - 1)
    x1 = np.clip(x0 + 1, 0, gw - 1)
    y1 = np.clip(y0 + 1, 0, gh - 1)
    fx = np.clip(PX - np.floor(PX), 0, 1)
    fy = np.clip(PY - np.floor(PY), 0, 1)
    m = mask.astype(float)
    return (m[y0, x0] * (1 - fx) * (1 - fy) + m[y0, x1] * fx * (1 - fy)
            + m[y1, x0] * (1 - fx) * fy + m[y1, x1] * fx * fy)


def _blob(canvas: np.ndarray, cx: int, cy: int, r: int,
          color: tuple[int, int, int], squash: float = 1.0) -> None:
    """Stamp a small filled ellipse onto canvas (clipped to bounds)."""
    H, W = canvas.shape[:2]
    y0, y1 = max(0, cy - r), min(H, cy + r + 1)
    x0, x1 = max(0, cx - int(r / squash) - 1), min(W, cx + int(r / squash) + 2)
    if y0 >= y1 or x0 >= x1:
        return
    yy, xx = np.ogrid[y0:y1, x0:x1]
    d = ((xx - cx) * squash / r) ** 2 + ((yy - cy) / r) ** 2
    canvas[y0:y1, x0:x1][d <= 1.0] = color


def _macro_tone(H: int, W: int, rng: np.random.Generator) -> np.ndarray:
    """Low-frequency multiply map (~0.70..1.24) -> big, clearly visible
    light/dark blotches across large areas (kills the flat-tiling look)."""
    n = max(H, W)
    field = gt._fbm(n, rng, freqs=(2, 4, 8), amps=(0.65, 0.25, 0.1))  # noqa: SLF001
    return (0.70 + 0.54 * field[:H, :W])[:, :, None]


def enrich(canvas: np.ndarray, label: np.ndarray, water_idx: int,
           rng: np.random.Generator) -> np.ndarray:
    """Add the two cheap 'richness' layers that break up flat tiling:
       1) a macro tonal blotch layer (multiply), 2) non-grid-aligned decals
       (pebbles + grass tufts on land, foam specks on water)."""
    H, W = canvas.shape[:2]
    out = np.clip(canvas.astype(float) * _macro_tone(H, W, rng), 0, 255).astype(np.uint8)

    land = label != water_idx
    # pebbles / debris on land (non-aligned, overlapping -> reads as a decal layer)
    for _ in range((H * W) // 5500):
        x, y = int(rng.integers(W)), int(rng.integers(H))
        if not land[y, x]:
            continue
        r = int(rng.integers(3, 9))
        base = int(rng.integers(96, 150))
        _blob(out, x, y, r, (base, base, base + 6), squash=rng.uniform(0.7, 1.3))
        _blob(out, x - 1, y - 1, max(1, r - 3), (base + 40, base + 40, base + 46))
    # grass tufts (tiny dark-green V) on land
    for _ in range((H * W) // 7000):
        x, y = int(rng.integers(W)), int(rng.integers(H))
        if not land[y, x]:
            continue
        c = (38, 78, 30)
        for dx, dy in ((-1, 1), (0, 0), (1, 1), (0, -2), (2, 0), (-2, 0)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < W and 0 <= yy < H:
                out[yy, xx] = c
    # foam specks on water
    for _ in range((H * W) // 9000):
        x, y = int(rng.integers(W)), int(rng.integers(H))
        if land[y, x]:
            continue
        _blob(out, x, y, int(rng.integers(2, 5)), (180, 212, 236),
              squash=rng.uniform(1.4, 2.4))
    return out


def classify(seg: np.ndarray, gh: int, gw: int):
    """Return (ground grid, obj grid) of names per cell from the seg image."""
    keys = np.array(list(COLOR_MAP.keys()))
    key_list = list(COLOR_MAP.keys())
    ground = np.empty((gh, gw), dtype=object)
    obj = np.empty((gh, gw), dtype=object)
    for cy in range(gh):
        for cx in range(gw):
            block = seg[cy * TILE:(cy + 1) * TILE, cx * TILE:(cx + 1) * TILE]
            cols, counts = np.unique(block.reshape(-1, 3), axis=0,
                                     return_counts=True)
            dom = cols[int(np.argmax(counts))]
            gname, oname = COLOR_MAP[key_list[_nearest_key(dom, keys)]]
            ground[cy, cx] = gname
            obj[cy, cx] = oname
    return ground, obj


def render(seg_path: str, band: bool, rich: bool = False) -> Image.Image:
    seg = np.array(Image.open(seg_path).convert("RGB"))
    h, w, _ = seg.shape
    gw, gh = w // TILE, h // TILE
    ground, obj = classify(seg, gh, gw)

    # map each cell to its rendered ground category.
    # bridges span land AND water; a bridge cell only counts as WATER ground when
    # it actually sits over the river (an orthogonal neighbour is real water),
    # otherwise it's land -> prevents the river bulging onto the bridge approaches.
    cat = np.empty((gh, gw), dtype=object)
    for cy in range(gh):
        for cx in range(gw):
            g = ground[cy, cx]
            if g == "bridge":
                over_water = any(
                    0 <= ny < gh and 0 <= nx < gw and ground[ny, nx] == "water"
                    for ny, nx in ((cy - 1, cx), (cy + 1, cx),
                                   (cy, cx - 1), (cy, cx + 1)))
                cat[cy, cx] = "water" if over_water else "grass"
            else:
                cat[cy, cx] = GROUND_OF[g]

    # pre-stamp a full-map texture for every category present
    cats = sorted({c for row in cat for c in row}, key=lambda c: PRIORITY[c])
    textures = {c: _stamp_full(MAKER[c], gh, gw, seed=1000 + PRIORITY[c]) for c in cats}
    cat_idx = {c: i for i, c in enumerate(cats)}

    # HARD base: every pixel starts as its OWN cell's terrain. This guarantees no
    # gaps (a pixel never falls back to an unrelated terrain) -- e.g. a road/rock
    # junction can't leak the water base through the seam between their fields.
    canvas = np.empty((gh * TILE, gw * TILE, 3), dtype=np.uint8)
    label = np.empty((gh * TILE, gw * TILE), dtype=np.int16)
    for cy in range(gh):
        for cx in range(gw):
            sl = (slice(cy * TILE, (cy + 1) * TILE), slice(cx * TILE, (cx + 1) * TILE))
            canvas[sl] = textures[cat[cy, cx]][sl]
            label[sl] = cat_idx[cat[cy, cx]]

    # dual-grid rounding: paint each terrain low -> high where its field >= 0.5,
    # so higher-priority terrain rounds smoothly over lower neighbours.
    water_field = None
    for c in cats:
        field = _dual_field(cat == c)
        if c == "water":
            water_field = field
        sel = field >= 0.5
        canvas[sel] = textures[c][sel]
        label[sel] = cat_idx[c]

    # optional tan sand band on the water side of grass/water shorelines
    if band and water_field is not None:
        grass_field = _dual_field(cat == "grass")
        shore = (water_field > 0.0) & (water_field < 0.5) & (grass_field >= 0.34)
        sand_tex = np.empty_like(canvas)
        sand_tex[:] = SAND
        canvas[shore] = sand_tex[shore]

    # optional richness layers (macro tonal blotches + non-aligned decals)
    if rich:
        canvas = enrich(canvas, label, cat_idx.get("water", -1),
                        np.random.default_rng(777))

    out = Image.fromarray(canvas, "RGB").convert("RGBA")

    # ---- objects on top ----
    rng = np.random.default_rng(20260616)
    # bridges: opaque plank over the water
    for cy in range(gh):
        for cx in range(gw):
            if ground[cy, cx] == "bridge":
                plank = gt.bridge(np.random.default_rng(int(rng.integers(2**31))))
                out.paste(Image.fromarray(plank, "RGB"), (cx * TILE, cy * TILE))
    # trees on forest cells
    for cy in range(gh):
        for cx in range(gw):
            if obj[cy, cx] == "tree":
                t = gt.tree(np.random.default_rng(int(rng.integers(2**31))))
                out.alpha_composite(Image.fromarray(t, "RGBA"), (cx * TILE, cy * TILE))
    # houses: merge connected house cells into single buildings
    house_mask = np.array([[ground[cy, cx] == "house" for cx in range(gw)]
                           for cy in range(gh)], dtype=bool)
    for cells in _components(house_mask):
        ys = [c[0] for c in cells]
        xs = [c[1] for c in cells]
        _draw_building(out, min(xs) * TILE, min(ys) * TILE,
                       (max(xs) + 1) * TILE, (max(ys) + 1) * TILE,
                       np.random.default_rng(int(rng.integers(2**31))))
    return out


def main() -> None:
    seg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        "scripts", "tiles", "segnew.png")
    os.makedirs(gt.OUT_DIR, exist_ok=True)
    stem = os.path.splitext(os.path.basename(seg_path))[0]
    for band, rich, suffix in ((False, False, "_dual"),
                               (True, False, "_dual_band"),
                               (False, True, "_dual_rich")):
        img = render(seg_path, band=band, rich=rich)
        p = os.path.join(gt.OUT_DIR, f"{stem}{suffix}.png")
        img.convert("RGB").save(p)
        print(f"wrote {p}  ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
