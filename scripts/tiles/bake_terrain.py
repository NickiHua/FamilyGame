"""Bake a single continuous terrain image: tile a 128px tile (2 cells period) across the
whole map, keep only cells of the given terrain letter (alpha 0 elsewhere). Same idea as
the water bake, generalised. Usage:
  python scripts/tiles/bake_terrain.py <LETTER> <big_png> <out_png>
e.g. python scripts/tiles/bake_terrain.py G Assets/Art/Tiles/grass_big.png Assets/Art/Maps/stage1_grass.png
"""
import re
import sys
from PIL import Image

MAP = 'Assets/Art/Maps/stage1_map.json'
CELL = 64

letter = sys.argv[1]
big_path = sys.argv[2]
out_path = sys.argv[3]

rows = re.findall(r'"([GRFWCBLDIS]+)"', open(MAP, encoding='utf-8').read())
H = len(rows)
W = len(rows[0])

big = Image.open(big_path).convert('RGBA')
P = big.width  # 128

out = Image.new('RGBA', (W * CELL, H * CELL), (0, 0, 0, 0))
for r in range(H):
    for x in range(W):
        if rows[r][x] != letter:
            continue
        sx = (x * CELL) % P
        sy = (r * CELL) % P
        out.paste(big.crop((sx, sy, sx + CELL, sy + CELL)), (x * CELL, r * CELL))

out.save(out_path)
print('baked', out_path, letter, W * CELL, H * CELL)
