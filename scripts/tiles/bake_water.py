"""Bake a single continuous water image: tile water_big.png (128px = 2 cells) across the
whole map with a 2-cell period, then keep only water ('W') cells (alpha 0 elsewhere).
The result is one sprite that drapes over the water shape with a continuous texture — a
3-cell span shows two full 128 tiles + a half, no per-cell seams, no cutting, no randomness.
Output: Assets/Art/Maps/stage1_water.png  (re-run after editing the map or the water tile).
"""
import re
from PIL import Image

MAP = 'Assets/Art/Maps/stage1_map.json'
BIG = 'Assets/Art/Tiles/water_big.png'   # 128x128
OUT = 'Assets/Art/Maps/stage1_water.png'
CELL = 64

t = open(MAP, encoding='utf-8').read()
rows = re.findall(r'"([GRFWCBLDIS]+)"', t)
H = len(rows)
W = len(rows[0])

big = Image.open(BIG).convert('RGBA')
P = big.width  # period in px (128)

out = Image.new('RGBA', (W * CELL, H * CELL), (0, 0, 0, 0))
for r in range(H):          # image row 0 = top
    for x in range(W):
        if rows[r][x] != 'W':
            continue
        sx = (x * CELL) % P
        sy = (r * CELL) % P
        cell = big.crop((sx, sy, sx + CELL, sy + CELL))
        out.paste(cell, (x * CELL, r * CELL))

out.save(OUT)
print('baked', OUT, W * CELL, H * CELL)
