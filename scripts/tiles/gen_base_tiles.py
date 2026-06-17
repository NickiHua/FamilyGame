"""Procedurally generate seamless 64x64 pixel-art base tiles for the SRPG.

Why: AI image models cannot guarantee a SEAMLESS tile (the hardest part). These
procedural tiles are graybox-quality, 100% tileable, and drop straight into Unity
now. Replace with AI-painted versions later via re-skin if desired.

Tiles: grass, road (cobblestone), water, bridge (planks), rock.

Outputs into scripts/tiles/out/:
  <name>.png          -- single 64x64 tile (RGB)
  <name>_preview.png  -- the tile repeated 3x3 (to eyeball seamlessness)
  all_tiles.png       -- row of all single tiles side by side

Run from repo root (venv with Pillow + numpy active):
  python scripts/tiles/gen_base_tiles.py
"""

from __future__ import annotations

import os

import numpy as np
from PIL import Image

TILE = 64
OUT_DIR = os.path.join("scripts", "tiles", "out")


# ---------------------------------------------------------------------------
# seamless value noise (periodic -> tiles perfectly on all four edges)
# ---------------------------------------------------------------------------
def _value_noise(size: int, freq: int, rng: np.random.Generator) -> np.ndarray:
    """Periodic bilinear-interpolated value noise in [0,1], shape (size, size)."""
    grid = rng.random((freq, freq))
    coords = np.arange(size) * freq / size
    i0 = np.floor(coords).astype(int) % freq
    i1 = (i0 + 1) % freq
    frac = coords - np.floor(coords)
    # smoothstep for nicer patches
    frac = frac * frac * (3 - 2 * frac)

    # bilinear over wrapped grid
    gx0 = grid[i0][:, i0]
    gx1 = grid[i0][:, i1]
    gy0 = grid[i1][:, i0]
    gy1 = grid[i1][:, i1]
    fx = frac[None, :]
    fy = frac[:, None]
    top = gx0 * (1 - fx) + gx1 * fx
    bot = gy0 * (1 - fx) + gy1 * fx
    return top * (1 - fy) + bot * fy


def _fbm(size: int, rng: np.random.Generator,
         freqs=(4, 8, 16), amps=(0.6, 0.3, 0.1)) -> np.ndarray:
    """Fractal sum of seamless value noise, normalized to [0,1]."""
    out = np.zeros((size, size), dtype=float)
    for f, a in zip(freqs, amps):
        out += a * _value_noise(size, f, rng)
    out -= out.min()
    out /= max(out.max(), 1e-9)
    return out


def _quantize(values: np.ndarray, palette: list[tuple[int, int, int]]) -> np.ndarray:
    """Map [0,1] field into discrete palette bands -> (size,size,3) uint8."""
    n = len(palette)
    idx = np.clip((values * n).astype(int), 0, n - 1)
    pal = np.array(palette, dtype=np.uint8)
    return pal[idx]


# ---------------------------------------------------------------------------
# individual tiles
# ---------------------------------------------------------------------------
def grass(rng: np.random.Generator) -> np.ndarray:
    greens = [(52, 102, 38), (70, 132, 50), (92, 160, 64), (126, 192, 86)]
    base = _fbm(TILE, rng, freqs=(7, 14, 24), amps=(0.5, 0.32, 0.18))
    img = _quantize(base, greens)
    # clustered tufts + tiny flowers for richer ground breakup
    _scatter_tufts(img, rng, count=20, color=(40, 82, 30))
    _scatter_tufts(img, rng, count=12, color=(154, 206, 108))
    for _ in range(18):
        x = int(rng.integers(TILE))
        y = int(rng.integers(TILE))
        c = (224, 206, 90) if rng.random() < 0.55 else (196, 222, 242)
        _put(img, x, y, c)
    for _ in range(8):
        x = int(rng.integers(TILE))
        y = int(rng.integers(TILE))
        _put(img, x, y, (112, 92, 58))
    return img


def rock(rng: np.random.Generator) -> np.ndarray:
    greys = [(82, 86, 92), (112, 116, 122), (142, 146, 152), (172, 176, 182)]
    base = _fbm(TILE, rng, freqs=(5, 10, 18), amps=(0.55, 0.3, 0.15))
    img = _quantize(base, greys)
    _scatter_cracks(img, rng, count=6, color=(62, 66, 72))
    # chipped highlights
    for _ in range(22):
        x = int(rng.integers(TILE))
        y = int(rng.integers(TILE))
        for dx, dy in ((0, 0), (1, 0), (0, 1)):
            _put(img, x + dx, y + dy, (190, 194, 198))
    return img


def road(rng: np.random.Generator) -> np.ndarray:
    """Cobblestones on a 16px grid (divides 64 -> seamless)."""
    stone_shades = [(160, 148, 128), (178, 166, 146), (142, 130, 112)]
    grout = (92, 84, 72)
    img = np.empty((TILE, TILE, 3), dtype=np.uint8)
    img[:] = grout
    cell = 16
    tex = _fbm(TILE, rng, freqs=(16, 32), amps=(0.6, 0.4))
    for gy in range(0, TILE, cell):
        for gx in range(0, TILE, cell):
            shade = np.array(stone_shades[rng.integers(len(stone_shades))], dtype=float)
            # rounded stone: inset 2px, skip corners for a pebble look
            for y in range(gy + 1, gy + cell - 1):
                for x in range(gx + 1, gx + cell - 1):
                    ly, lx = y - gy, x - gx
                    # round the corners
                    if (ly in (1, cell - 2) and lx in (1, cell - 2)):
                        continue
                    t = 0.74 + 0.52 * tex[y, x]
                    img[y, x] = np.clip(shade * t, 0, 255).astype(np.uint8)
            # tiny chip specks per cobble
            for _ in range(3):
                sx = int(rng.integers(gx + 2, gx + cell - 2))
                sy = int(rng.integers(gy + 2, gy + cell - 2))
                img[sy, sx] = (112, 104, 92)
    return img


def water(rng: np.random.Generator) -> np.ndarray:
    base = _fbm(TILE, rng, freqs=(8, 16), amps=(0.6, 0.4))
    y = np.arange(TILE)[:, None]
    x = np.arange(TILE)[None, :]
    # horizontal ripples; integer wave count k keeps it seamless in y
    ripple = 0.5 + 0.5 * np.sin(2 * np.pi * 4 * y / TILE + 5.5 * base)
    field = np.clip(0.58 * base + 0.42 * ripple, 0, 1)
    blues = [(22, 70, 118), (34, 94, 148), (50, 122, 180), (98, 168, 214)]
    img = _quantize(field, blues)
    # foam highlights where ripple crests
    crest = ripple > 0.86
    img[crest] = (170, 208, 236)
    img[np.logical_and(crest, base > 0.62)] = (132, 188, 224)
    return img


def bridge(rng: np.random.Generator) -> np.ndarray:
    """Horizontal planks; gap lines on a 16px pitch -> seamless in y."""
    img = np.empty((TILE, TILE, 3), dtype=np.uint8)
    plank_shades = [(154, 110, 64), (142, 98, 56), (166, 120, 72)]
    grain = _fbm(TILE, rng, freqs=(32, 16), amps=(0.6, 0.4))
    pitch = 16
    for gy in range(0, TILE, pitch):
        shade = np.array(plank_shades[rng.integers(len(plank_shades))], dtype=float)
        for y in range(gy, gy + pitch):
            for x in range(TILE):
                t = 0.78 + 0.46 * grain[y, x]
                img[y, x] = np.clip(shade * t, 0, 255).astype(np.uint8)
        # dark gap line at the top of each plank (y=gy)
        img[gy, :] = (74, 48, 26)
        img[gy + 1, :] = np.clip(np.array((74, 48, 26)) * 1.2, 0, 255).astype(np.uint8)
    # side beams + simple nails
    img[:, 0:2] = (98, 64, 36)
    img[:, TILE - 2:TILE] = (98, 64, 36)
    for gy in range(8, TILE, 16):
        for x in (8, TILE - 9):
            img[gy:gy + 2, x:x + 2] = (64, 52, 42)
    return img


def forest(rng: np.random.Generator) -> np.ndarray:
    """Deep-green grass base with rounded tree-canopy blobs -> reads as forest."""
    greens = [(28, 64, 30), (36, 80, 36), (46, 98, 44), (58, 118, 52)]
    base = _fbm(TILE, rng, freqs=(8, 16, 24), amps=(0.5, 0.35, 0.15))
    img = _quantize(base, greens)
    # a few rounded canopy blobs, wrap-safe, with a lighter top-left lit side
    for _ in range(5):
        cx = int(rng.integers(TILE))
        cy = int(rng.integers(TILE))
        r = int(rng.integers(6, 10))
        dark = (22, 52, 26)
        mid = (40, 92, 42)
        lit = (70, 138, 64)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                d = (dx * dx + dy * dy) ** 0.5
                if d > r:
                    continue
                # top-left lit, bottom-right shaded
                if dx + dy < -r * 0.3:
                    c = lit
                elif dx + dy > r * 0.5:
                    c = dark
                else:
                    c = mid
                _put(img, cx + dx, cy + dy, c)
    # twig shadows
    _scatter_cracks(img, rng, count=4, color=(18, 42, 22))
    return img


def tree(rng: np.random.Generator) -> np.ndarray:
    """A single standalone tree sprite on transparent bg (RGBA), top-down-ish."""
    img = np.zeros((TILE, TILE, 4), dtype=np.uint8)
    cx, cy, r = TILE // 2, TILE // 2 - 2, 22
    trunk = (96, 64, 38)
    # trunk
    for y in range(cy + r - 8, cy + r + 6):
        for x in range(cx - 3, cx + 3):
            if 0 <= y < TILE:
                img[y, x] = trunk + (255,)
    # canopy: layered circles, top-left light
    layers = [(r, (30, 72, 34)), (r - 4, (44, 100, 46)), (r - 9, (70, 144, 66)),
              (r - 14, (104, 178, 92))]
    for rad, col in layers:
        ox = -2 if rad < r else 0
        oy = -2 if rad < r else 0
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                if dx * dx + dy * dy <= rad * rad:
                    y, x = cy + dy + oy, cx + dx + ox
                    if 0 <= y < TILE and 0 <= x < TILE:
                        img[y, x] = col + (255,)
    return img


def house(rng: np.random.Generator) -> np.ndarray:
    """A simple top-down village house filling the cell (roof + walls)."""
    img = np.empty((TILE, TILE, 3), dtype=np.uint8)
    img[:] = (124, 176, 76)  # grass border around the house footprint
    # footprint inset
    x0, y0, x1, y1 = 6, 8, 58, 60
    wall = (150, 120, 92)
    wall_dark = (120, 92, 68)
    roof = (150, 70, 56)
    roof_lit = (182, 96, 78)
    roof_dark = (112, 50, 40)
    # walls
    img[y0:y1, x0:x1] = wall
    img[y1 - 10:y1, x0:x1] = wall_dark  # lower wall shade
    # roof occupies top ~55%
    rh = y0 + 26
    for y in range(y0, rh):
        for x in range(x0, x1):
            # ridge highlight near top-left, eaves shaded near bottom
            if y < y0 + 6:
                img[y, x] = roof_lit
            elif y > rh - 6:
                img[y, x] = roof_dark
            else:
                img[y, x] = roof
    # roof tile separators
    for y in range(y0 + 6, rh, 6):
        img[y:y + 1, x0:x1] = (118, 58, 44)
    # door
    img[y1 - 14:y1, 28:36] = (78, 54, 36)
    img[y1 - 14:y1, 31:33] = (56, 38, 24)
    # window
    img[rh + 4:rh + 12, 14:22] = (96, 150, 170)
    img[rh + 4:rh + 12, 42:50] = (96, 150, 170)
    img[rh + 7:rh + 8, 14:22] = (136, 196, 216)
    img[rh + 7:rh + 8, 42:50] = (136, 196, 216)
    return img


def cliff(rng: np.random.Generator) -> np.ndarray:
    """Darker, bluer rock for cliffs/mountains."""
    greys = [(74, 70, 88), (98, 94, 114), (124, 120, 140), (152, 148, 166)]
    base = _fbm(TILE, rng, freqs=(5, 10, 18), amps=(0.55, 0.3, 0.15))
    img = _quantize(base, greys)
    _scatter_cracks(img, rng, count=6, color=(48, 46, 60))
    for _ in range(18):
        x = int(rng.integers(TILE))
        y = int(rng.integers(TILE))
        _put(img, x, y, (166, 162, 182))
    return img



# ---------------------------------------------------------------------------
# decoration helpers (wrap-safe)
# ---------------------------------------------------------------------------
def _put(img: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    img[y % TILE, x % TILE] = color


def _scatter_tufts(img: np.ndarray, rng: np.random.Generator, count: int,
                   color: tuple[int, int, int]) -> None:
    """Tiny chunky V-shaped grass tufts, wrap around edges so they stay seamless."""
    for _ in range(count):
        cx = int(rng.integers(TILE))
        cy = int(rng.integers(TILE))
        for dx, dy in ((-1, 1), (0, 0), (1, 1), (0, -1)):
            _put(img, cx + dx, cy + dy, color)


def _scatter_cracks(img: np.ndarray, rng: np.random.Generator, count: int,
                    color: tuple[int, int, int]) -> None:
    """Short jagged cracks, wrap-safe."""
    for _ in range(count):
        x = int(rng.integers(TILE))
        y = int(rng.integers(TILE))
        length = int(rng.integers(4, 9))
        for _ in range(length):
            _put(img, x, y, color)
            x += int(rng.integers(-1, 2))
            y += 1


# ---------------------------------------------------------------------------
def _tiled_preview(tile: np.ndarray, reps: int = 3, scale: int = 4) -> Image.Image:
    big = np.tile(tile, (reps, reps, 1))
    im = Image.fromarray(big, "RGB")
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(20260616)

    makers = {
        "grass": grass,
        "road": road,
        "water": water,
        "bridge": bridge,
        "rock": rock,
        "forest": forest,
        "cliff": cliff,
        "house": house,
    }

    singles = []
    for name, fn in makers.items():
        tile = fn(rng)
        Image.fromarray(tile, "RGB").save(os.path.join(OUT_DIR, f"{name}.png"))
        _tiled_preview(tile).save(os.path.join(OUT_DIR, f"{name}_preview.png"))
        singles.append(tile)
        print(f"wrote {name}.png + {name}_preview.png")

    # tree is RGBA (standalone object), handled separately
    tree_img = tree(rng)
    Image.fromarray(tree_img, "RGBA").save(os.path.join(OUT_DIR, "tree.png"))
    print("wrote tree.png (RGBA)")

    # contact sheet of single tiles, upscaled for easy viewing
    sheet = np.concatenate(singles, axis=1)
    im = Image.fromarray(sheet, "RGB")
    im = im.resize((im.width * 4, im.height * 4), Image.NEAREST)
    im.save(os.path.join(OUT_DIR, "all_tiles.png"))
    print("wrote all_tiles.png")


if __name__ == "__main__":
    main()
