"""Debug: render raw JSON terrain letters as a flat colour grid (no dual-grid)."""
import re
from PIL import Image, ImageDraw

t = open('Assets/Art/Maps/stage1_map.json', encoding='utf-8').read()
rows = re.findall(r'"([GRFWCBLDIS]+)"', t)
H = len(rows)
W = len(rows[0])
col = {'G': (90, 150, 70), 'I': (110, 70, 40), 'R': (200, 170, 110),
       'W': (40, 110, 210), 'S': (225, 205, 150), 'D': (120, 80, 40)}
S = 22
im = Image.new('RGB', (W * S, H * S), (0, 0, 0))
d = ImageDraw.Draw(im)
for r in range(H):
    for x in range(W):
        c = rows[r][x]
        d.rectangle([x * S, r * S, x * S + S, r * S + S], fill=col.get(c, (255, 0, 255)))
        d.text((x * S + 5, r * S + 4), c, fill=(0, 0, 0))
im.save('art/tiles/dual/_letters.png')
print('saved', W, H)
