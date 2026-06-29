"""Visual demo: HARD edge vs DUAL-GRID vs 47-BLOB terrain transitions.

Purpose: let us SEE the difference between the three tile-edge strategies on the
SAME little grass/water map, so we can decide which transition style to commit to.

What it renders (into art_undecided/tileset/):
  cmp_hard.png        baseline: 1 flat tile per cell, hard square seams
  cmp_dual.png        DUAL-GRID: display grid offset half a cell, each display
                      tile chosen by its 4 surrounding cell-corners (16 configs)
  cmp_blob.png        47-BLOB: per-cell, grass mask shaped by 8 neighbours
                      (rounded outer corners + notched inner corners)
  cmp_all.png         the three panels stacked with labels for easy comparison
  dual_16_sheet.png   ALL 16 dual-grid corner tiles (this is the whole set)

Terrain model (2 layers + a tan transition band, like FE / 梦战 coastlines):
  WATER (low)  <  GRASS (high) ; a SAND band is drawn where they meet.

Run from repo root (venv with Pillow + numpy + scipy active):
  python scripts/tiles/demo_transitions.py
"""

from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import gen_base_tiles as gt

TILE = gt.TILE  # 64
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(_REPO_ROOT, "art_undecided", "tileset")

SAND = np.array([206, 184, 130], dtype=np.uint8)   # tan transition band
SAND_DARK = np.array([176, 150, 100], dtype=np.uint8)


# ---------------------------------------------------------------------------
# sample map: 1 = grass (high), 0 = water (low).  A lake with an inlet + island.
# ---------------------------------------------------------------------------
def sample_map() -> np.ndarray:
    g = np.ones((11, 15), dtype=np.uint8)  # start all grass
    lake = [
        "...............",
        "...............",
        "....WWWWW......",
        "...WWWWWWWW....",
        "..WWWWWWWWWW...",
        "..WWWWW.WWWW...",   # the single '.' here = tiny island in the lake
        "...WWWWWWWW....",
        "....WWWWWW.....",
        ".......WW......",
        "...............",
        "...............",
    ]
    for y, row in enumerate(lake):
        for x, ch in enumerate(row):
            if ch == "W":
                g[y, x] = 0
    return g


# ---------------------------------------------------------------------------
# texture layers: stamp a fresh base tile per cell, then composite by a label map
# ---------------------------------------------------------------------------
def _stamp_layer(maker, gh: int, gw: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.empty((gh * TILE, gw * TILE, 3), dtype=np.uint8)
    for cy in range(gh):
        for cx in range(gw):
            out[cy * TILE:(cy + 1) * TILE, cx * TILE:(cx + 1) * TILE] = maker(rng)
    return out


def _sand_layer(gh: int, gw: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = gt._fbm(gh * TILE, rng, freqs=(40, 80), amps=(0.6, 0.4))  # noqa: SLF001
    base = base[:, : gw * TILE] if base.shape[1] >= gw * TILE else np.tile(
        base, (1, 2))[:, : gw * TILE]
    field = (base[:, :, None] * (SAND.astype(float) - SAND_DARK.astype(float))
             + SAND_DARK.astype(float))
    return np.clip(field, 0, 255).astype(np.uint8)


def _colorize(label: np.ndarray, grass_t: np.ndarray, water_t: np.ndarray,
              sand_t: np.ndarray) -> Image.Image:
    """label: 0 water, 1 sand, 2 grass -> composite the three textures."""
    out = water_t.copy()
    out[label == 1] = sand_t[label == 1]
    out[label == 2] = grass_t[label == 2]
    return Image.fromarray(out, "RGB")


def _add_sand_band(grass_mask: np.ndarray, width: int = 7) -> np.ndarray:
    """label map from a grass boolean mask: grass=2, a sand ring=1, water=0."""
    grass_mask = grass_mask.astype(bool)
    grown = ndimage.binary_dilation(grass_mask, iterations=width)
    label = np.zeros(grass_mask.shape, dtype=np.uint8)
    label[grown & ~grass_mask] = 1     # sand ring just outside grass
    label[grass_mask] = 2
    return label


# ---------------------------------------------------------------------------
# 1) HARD: each cell is its own terrain, full square. No band.
# ---------------------------------------------------------------------------
def hard_mask(g: np.ndarray) -> np.ndarray:
    gh, gw = g.shape
    m = np.zeros((gh * TILE, gw * TILE), dtype=bool)
    for cy in range(gh):
        for cx in range(gw):
            if g[cy, cx]:
                m[cy * TILE:(cy + 1) * TILE, cx * TILE:(cx + 1) * TILE] = True
    return m


# ---------------------------------------------------------------------------
# 2) DUAL-GRID: data = cell centres; display offset half a cell.
#    Each pixel bilinearly interpolates the 4 nearest cell-centre grass values;
#    threshold -> the boundary cuts smoothly between cells (corner-defined, 16).
# ---------------------------------------------------------------------------
def dual_field(g: np.ndarray) -> np.ndarray:
    gh, gw = g.shape
    H, W = gh * TILE, gw * TILE
    py = (np.arange(H) / TILE - 0.5)
    px = (np.arange(W) / TILE - 0.5)
    PX, PY = np.meshgrid(px, py)
    x0 = np.clip(np.floor(PX).astype(int), 0, gw - 1)
    y0 = np.clip(np.floor(PY).astype(int), 0, gh - 1)
    x1 = np.clip(x0 + 1, 0, gw - 1)
    y1 = np.clip(y0 + 1, 0, gh - 1)
    fx = np.clip(PX - x0, 0, 1)
    fy = np.clip(PY - y0, 0, 1)
    gf = g.astype(float)
    v = (gf[y0, x0] * (1 - fx) * (1 - fy) + gf[y0, x1] * fx * (1 - fy)
         + gf[y1, x0] * (1 - fx) * fy + gf[y1, x1] * fx * fy)
    return v


def dual_label(g: np.ndarray, band: bool = True) -> np.ndarray:
    v = dual_field(g)
    label = np.zeros(v.shape, dtype=np.uint8)
    label[v >= 0.5] = 2          # grass
    if band:
        label[(v >= 0.34) & (v < 0.5)] = 1  # sand band on the water side of the cut
    return label


# ---------------------------------------------------------------------------
# 3) 47-BLOB: per grass cell, fill the square but reshape the 4 corners from the
#    8 neighbours: outer corner (a cardinal is water) -> round it off;
#    inner corner (both cardinals grass but diagonal water) -> notch the tip.
# ---------------------------------------------------------------------------
def blob_mask(g: np.ndarray, r: int = 20) -> np.ndarray:
    gh, gw = g.shape
    H, W = gh * TILE, gw * TILE
    m = np.zeros((H, W), dtype=bool)

    def gv(y, x):
        return 0 <= y < gh and 0 <= x < gw and g[y, x] == 1

    ly, lx = np.mgrid[0:TILE, 0:TILE]
    for cy in range(gh):
        for cx in range(gw):
            if not g[cy, cx]:
                continue
            cell = np.ones((TILE, TILE), dtype=bool)
            N, S = gv(cy - 1, cx), gv(cy + 1, cx)
            Wn, E = gv(cy, cx - 1), gv(cy, cx + 1)
            NW, NE = gv(cy - 1, cx - 1), gv(cy - 1, cx + 1)
            SW, SE = gv(cy + 1, cx - 1), gv(cy + 1, cx + 1)
            # corners: (region predicate, cardinalA, cardinalB, diagonal, cx0, cy0)
            corners = [
                (lx < r, ly < r, Wn, N, NW, r, r),                 # TL
                (lx >= TILE - r, ly < r, E, N, NE, TILE - r, r),   # TR
                (lx < r, ly >= TILE - r, Wn, S, SW, r, TILE - r),  # BL
                (lx >= TILE - r, ly >= TILE - r, E, S, SE, TILE - r, TILE - r),  # BR
            ]
            for cond_x, cond_y, ca, cb, diag, ox, oy in corners:
                region = cond_x & cond_y
                dist2 = (lx - ox) ** 2 + (ly - oy) ** 2
                if not (ca and cb):
                    # outer corner -> carve away outside the quarter circle
                    cell[region & (dist2 > r * r)] = False
                elif not diag:
                    # inner corner -> small concave notch at the very tip
                    nr = r // 2
                    cell[region & (dist2 < nr * nr)] = False
            m[cy * TILE:(cy + 1) * TILE, cx * TILE:(cx + 1) * TILE] = cell
    return m


# ---------------------------------------------------------------------------
# dual-grid 16-tile reference sheet (all corner configurations)
# ---------------------------------------------------------------------------
def dual_16_sheet(grass_t: np.ndarray, water_t: np.ndarray,
                  band: bool = True) -> Image.Image:
    """Render every one of the 16 dual tiles: corners = (TL,TR,BL,BR) each 0/1.

    Each tile is annotated with a dot at its 4 corners: GREEN = that corner is
    grass, BLUE = water -> makes it obvious every tile is a grass+water PAIR piece.
    """
    fx = (np.arange(TILE)[None, :] + 0.5) / TILE
    fy = (np.arange(TILE)[:, None] + 0.5) / TILE
    cols, rows = 8, 2
    pad, lab = 10, 16
    cellw, cellh = TILE + pad, TILE + pad + lab
    sheet = Image.new("RGB", (cols * cellw + pad, rows * cellh + pad), (40, 40, 46))
    draw = ImageDraw.Draw(sheet)
    gtex = grass_t[:TILE, :TILE]
    wtex = water_t[:TILE, :TILE]
    G, B = (90, 210, 90), (70, 150, 240)
    for cfg in range(16):
        TL = (cfg >> 0) & 1
        TR = (cfg >> 1) & 1
        BL = (cfg >> 2) & 1
        BR = (cfg >> 3) & 1
        v = (TL * (1 - fx) * (1 - fy) + TR * fx * (1 - fy)
             + BL * (1 - fx) * fy + BR * fx * fy)
        label = np.zeros((TILE, TILE), dtype=np.uint8)
        label[v >= 0.5] = 2
        if band:
            label[(v >= 0.34) & (v < 0.5)] = 1
        img = wtex.copy()
        sand = np.full_like(wtex, SAND)
        img[label == 1] = sand[label == 1]
        img[label == 2] = gtex[label == 2]
        tile = Image.fromarray(img, "RGB")
        c, r = cfg % cols, cfg // cols
        x0, y0 = pad + c * cellw, pad + r * cellh
        sheet.paste(tile, (x0, y0))
        # corner dots: green=grass, blue=water
        rr = 5
        for cornerval, (dx, dy) in zip(
                (TL, TR, BL, BR),
                ((0, 0), (TILE, 0), (0, TILE), (TILE, TILE))):
            col = G if cornerval else B
            cxp, cyp = x0 + dx, y0 + dy
            draw.ellipse((cxp - rr, cyp - rr, cxp + rr, cyp + rr),
                         fill=col, outline=(20, 20, 24))
        draw.text((x0 + 2, y0 + TILE + 2), f"#{cfg}", fill=(220, 220, 220))
    return sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)


def _label(img: Image.Image, text: str) -> Image.Image:
    out = Image.new("RGB", (img.width, img.height + 28), (28, 28, 32))
    out.paste(img, (0, 28))
    d = ImageDraw.Draw(out)
    d.text((8, 7), text, fill=(235, 235, 235))
    return out


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    g = sample_map()
    gh, gw = g.shape

    grass_t = _stamp_layer(gt.grass, gh, gw, seed=101)
    water_t = _stamp_layer(gt.water, gh, gw, seed=202)
    sand_t = _sand_layer(gh, gw, seed=303)

    # HARD (no band)
    hard = _colorize(np.where(hard_mask(g), 2, 0).astype(np.uint8),
                     grass_t, water_t, sand_t)
    hard.save(os.path.join(OUT_DIR, "cmp_hard.png"))

    # DUAL (with tan beach band) and DUAL (grass meets water directly)
    dual = _colorize(dual_label(g, band=True), grass_t, water_t, sand_t)
    dual.save(os.path.join(OUT_DIR, "cmp_dual.png"))
    dual_nb = _colorize(dual_label(g, band=False), grass_t, water_t, sand_t)
    dual_nb.save(os.path.join(OUT_DIR, "cmp_dual_noband.png"))

    # BLOB
    blob = _colorize(_add_sand_band(blob_mask(g), width=6),
                     grass_t, water_t, sand_t)
    blob.save(os.path.join(OUT_DIR, "cmp_blob.png"))

    # stacked comparison
    panels = [_label(hard, "1) HARD  (current: 1 flat tile/cell, square seams)"),
              _label(dual, "2) DUAL-GRID  (16 tiles, corner-defined, smooth)"),
              _label(blob, "3) 47-BLOB  (8-neighbour, rounded+notched corners)")]
    Wp = max(p.width for p in panels)
    Hp = sum(p.height for p in panels) + 16
    allp = Image.new("RGB", (Wp, Hp), (18, 18, 20))
    y = 0
    for p in panels:
        allp.paste(p, (0, y))
        y += p.height + 8
    allp.save(os.path.join(OUT_DIR, "cmp_all.png"))

    # the 16-tile dual sheets (with band + corner dots, and a no-band version)
    dual_16_sheet(grass_t, water_t, band=True).save(
        os.path.join(OUT_DIR, "dual_16_sheet.png"))
    dual_16_sheet(grass_t, water_t, band=False).save(
        os.path.join(OUT_DIR, "dual_16_sheet_noband.png"))

    # side-by-side: band vs no-band dual on the real map
    pair = [_label(dual, "DUAL  grass | SAND band | water"),
            _label(dual_nb, "DUAL  grass | water  (direct, no band)")]
    Wp = sum(p.width for p in pair) + 8
    Hp = max(p.height for p in pair)
    bandcmp = Image.new("RGB", (Wp, Hp), (18, 18, 20))
    bandcmp.paste(pair[0], (0, 0))
    bandcmp.paste(pair[1], (pair[0].width + 8, 0))
    bandcmp.save(os.path.join(OUT_DIR, "cmp_dual_band_vs_noband.png"))

    print("wrote ->", OUT_DIR)
    for f in ("cmp_hard.png", "cmp_dual.png", "cmp_dual_noband.png",
              "cmp_dual_band_vs_noband.png", "cmp_blob.png", "cmp_all.png",
              "dual_16_sheet.png", "dual_16_sheet_noband.png"):
        print("  ", f)


if __name__ == "__main__":
    main()
