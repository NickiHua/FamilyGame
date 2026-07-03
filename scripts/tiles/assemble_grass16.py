"""Assemble the 16 grass dual-grid corner tiles from the 4 processed shapes by rotation.
Corner bits: TL=1 TR=2 BL=4 BR=8. CW 90 rotation maps TL->TR->BR->BL->TL.
Sources (canonical):
  1corner  = grass in TL              -> bits 1
  2adjacent= grass top half (TL+TR)   -> bits 3
  2opposite= grass TL+BR              -> bits 9
  3corners = grass all but BR (TL+TR+BL) -> bits 7
Output: Assets/Art/Tiles/grass_dual/<bits>.png for bits 1..14 (0 empty, 15 = base grass).
"""
import os
from PIL import Image

SRC = 'art_undecided/tiles/grass_dual_ai'
OUT = 'Assets/Art/Tiles/grass_dual'
os.makedirs(OUT, exist_ok=True)

sources = {1: '1corner', 3: '2adjacent', 9: '2opposite', 7: '3corners'}


def rot_cw(b):
    nb = 0
    if b & 1: nb |= 2   # TL -> TR
    if b & 2: nb |= 8   # TR -> BR
    if b & 8: nb |= 4   # BR -> BL
    if b & 4: nb |= 1   # BL -> TL
    return nb


tiles = {}
for base_bits, name in sources.items():
    img = Image.open(f'{SRC}/{name}_64.png').convert('RGBA')
    b = base_bits
    for _ in range(4):
        if b not in tiles:
            tiles[b] = img
        img = img.transpose(Image.ROTATE_270)  # 90 CW
        b = rot_cw(b)

for b, img in tiles.items():
    img.save(f'{OUT}/{b:02d}.png')

print('assembled bits:', sorted(tiles.keys()), '->', OUT)
