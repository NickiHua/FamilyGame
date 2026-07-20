"""Build a review filmstrip montage for a character: one row per base action
(idle/walk/attack/knockback/knockout), 9 frames each, at a representative dir.
Usage: _filmstrip.py <CharId>"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

char = sys.argv[1]
base = Path('pixellab/characters') / char.lower() / 'animations'
ROWS = [('idle', 'S'), ('walk', 'S'), ('attack', 'SE'), ('knockback', 'SE'), ('knockout', 'SE')]

strips = []
maxh = 0
maxn = 0
cw = 0
for act, d in ROWS:
    folder = base / act / d
    if not folder.is_dir():
        strips.append((f'{act}/{d} (missing)', []))
        continue
    frames = sorted(folder.glob('*.png'))
    ims = [Image.open(f).convert('RGBA') for f in frames]
    strips.append((f'{act}/{d}', ims))
    if ims:
        maxh = max(maxh, max(i.height for i in ims))
        cw = max(cw, max(i.width for i in ims))
        maxn = max(maxn, len(ims))

scale = 2
pad = 4
lab = 62
rowh = maxh + pad
W = lab + maxn * (cw + pad) + pad
H = pad + len(strips) * (rowh + pad)
canvas = Image.new('RGBA', (W, H), (30, 30, 40, 255))
dr = ImageDraw.Draw(canvas)
for r, (label, ims) in enumerate(strips):
    y = pad + r * (rowh + pad)
    dr.text((3, y + rowh // 2 - 4), label, fill=(230, 230, 140, 255))
    for i, im in enumerate(ims):
        x = lab + i * (cw + pad) + (cw - im.width) // 2
        canvas.alpha_composite(im, (x, y + (maxh - im.height)))
big = canvas.resize((W * scale, H * scale), Image.NEAREST)
out = Path('pixellab/characters') / char.lower() / '_filmstrip.png'
big.save(out)
print('saved', out, big.size)
