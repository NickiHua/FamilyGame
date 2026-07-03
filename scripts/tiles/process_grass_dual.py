"""Process the 4 AI grass dual-grid source images:
  magenta chroma-key -> alpha, despill, keep largest grass blob(s) (drop watermark sparkle),
  downscale to 64x64. Output: art_undecided/tiles/grass_dual_ai/<name>_64.png + a preview
  composited over dirt so the dark grass edge reads.
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import label, binary_closing

SRC = 'art_undecided/experiments/grass'
OUT = 'art_undecided/tiles/grass_dual_ai'
NAMES = ['1corner', '2adjacent', '2opposite', '3corners']
os.makedirs(OUT, exist_ok=True)


def key_magenta(im):
    a = np.asarray(im.convert('RGB')).astype(int)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    m = np.minimum(R, B) - G          # high on magenta, low/neg on green
    lo, hi = 40, 130
    alpha = np.clip((hi - m) / (hi - lo), 0, 1)   # 1 = grass, 0 = magenta
    grass = alpha > 0.5
    # Drop small floating blobs (watermark sparkle): keep components >= 1% of area.
    grass = binary_closing(grass, iterations=2)
    lab, n = label(grass)
    if n:
        keep = np.zeros_like(grass)
        thresh = grass.size * 0.01
        for i in range(1, n + 1):
            comp = lab == i
            if comp.sum() >= thresh:
                keep |= comp
        grass = keep
    rgb = np.asarray(im.convert('RGB'))
    out = np.dstack([rgb, np.where(grass, 255, 0).astype('uint8')])
    return Image.fromarray(out, 'RGBA')


tiles = []
for name in NAMES:
    im = Image.open(f'{SRC}/{name}.png')
    keyed = key_magenta(im)
    small = keyed.resize((64, 64), Image.LANCZOS)
    # Re-harden alpha after resample.
    arr = np.asarray(small).copy()
    arr[..., 3] = np.where(arr[..., 3] >= 128, 255, 0)
    small = Image.fromarray(arr, 'RGBA')
    small.save(f'{OUT}/{name}_64.png')
    tiles.append(small)

bg = Image.new('RGBA', (64 * 4, 64), (120, 80, 45, 255))
for i, t in enumerate(tiles):
    bg.alpha_composite(t, (i * 64, 0))
bg.save(f'{OUT}/_preview.png')
print('done ->', OUT)
