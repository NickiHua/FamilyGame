"""Procedural grass dual-grid corner tiles with RANDOM irregular + darkened edges.

Corner dual-grid: a display tile covers the 4 corners of 4 cells; each corner is grass or
not -> 16 combos. Grass fills the present corners; the boundary toward absent corners is made
irregular with tileable value-noise and darkened in a band just inside the edge. Absent area
is transparent so any lower terrain shows through.

Bit order: TL=1 TR=2 BL=4 BR=8. Output: art_undecided/tiles/grass_dual/<bits>.png (64px RGBA).
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, binary_erosion

SRC = 'Assets/Art/Tiles/grass.png'
OUT = 'art_undecided/tiles/grass_dual'
SIZE = 64
NOISE_AMP = 0.22      # how wavy the edge is
EDGE_PX = 5           # darkened rim width (px)
EDGE_DARK = 0.62      # rim brightness multiplier (lower = darker)
SEED = 7

os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(SEED)
grass = np.asarray(Image.open(SRC).convert('RGBA').resize((SIZE, SIZE)))[..., :3].astype(float)


def corner_weights():
    u = (np.arange(SIZE) + 0.5) / SIZE
    U, V = np.meshgrid(u, u)
    return {'TL': (1 - U) * (1 - V), 'TR': U * (1 - V), 'BL': (1 - U) * V, 'BR': U * V}


def tileable_noise():
    """Smooth value noise that wraps at the tile edges (so neighbours line up)."""
    n = rng.standard_normal((SIZE, SIZE))
    n = gaussian_filter(n, sigma=4.0, mode='wrap')
    n -= n.mean()
    n /= (n.std() + 1e-6)
    return n


CW = corner_weights()
NOISE = tileable_noise()


def build(bits):
    a = np.zeros((SIZE, SIZE))
    for name, bit in (('TL', 1), ('TR', 2), ('BL', 4), ('BR', 8)):
        if bits & bit:
            a = a + CW[name]
    a = a + NOISE * NOISE_AMP            # wobble the boundary
    mask = a >= 0.5

    rgb = grass.copy()
    if EDGE_PX > 0 and mask.any():
        inner = binary_erosion(mask, iterations=EDGE_PX)
        rim = mask & ~inner
        rgb[rim] *= EDGE_DARK            # darken the edge band

    alpha = np.where(mask, 255, 0).astype('uint8')
    out = np.dstack([np.clip(rgb, 0, 255), alpha]).astype('uint8')
    return Image.fromarray(out, 'RGBA')


tiles = []
for b in range(16):
    im = build(b)
    im.save(f'{OUT}/{b:02d}.png')
    tiles.append(im)

# Preview: tiles composited over a dark terrain so the grass edge reads.
bg = Image.new('RGBA', (SIZE * 8, SIZE * 2), (120, 80, 45, 255))
for b in range(16):
    bg.alpha_composite(tiles[b], ((b % 8) * SIZE, (b // 8) * SIZE))
bg.save(f'{OUT}/_preview.png')
print('done ->', OUT)
