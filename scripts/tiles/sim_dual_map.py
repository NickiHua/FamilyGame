"""Offline render matching the FULL dual-grid DualGridBuilder (no hard base):
layers low->high, opaque, corner prio>=layer, OOB clamped, bridge solid on top."""
import re
from PIL import Image

t = open('Assets/Art/Maps/stage1_map.json', encoding='utf-8').read()
rows = re.findall(r'"([GRFWCBLDIS]+)"', t)
H = len(rows)
W = len(rows[0])
prio = {'G': 5, 'I': 4, 'R': 3, 'W': 2, 'S': 1, 'D': 0}


def nonbridge(*cs):
    for c in cs:
        if c != 'D':
            return c
    return 'D'


def ter(x, y):
    x = min(max(x, 0), W - 1)
    y = min(max(y, 0), H - 1)
    return rows[H - 1 - y][x]  # y up


C = Image.new('RGBA', (W * 64, H * 64), (40, 40, 40, 255))
layers = [('sand', 1), ('water', 2), ('road', 3), ('dirt', 4), ('grass', 5)]
for folder, p in layers:
    ov = [Image.open(f'art/tiles/dual/{folder}/{b:02d}.png') for b in range(16)]
    for y in range(-1, H):
        for x in range(-1, W):
            ctl, ctr = ter(x, y + 1), ter(x + 1, y + 1)
            cbl, cbr = ter(x, y), ter(x + 1, y)
            fill = nonbridge(ctl, ctr, cbl, cbr)
            if fill == 'D':
                continue
            ctl = fill if ctl == 'D' else ctl
            ctr = fill if ctr == 'D' else ctr
            cbl = fill if cbl == 'D' else cbl
            cbr = fill if cbr == 'D' else cbr
            tl = 1 if prio.get(ctl, 0) >= p else 0
            tr = 2 if prio.get(ctr, 0) >= p else 0
            bl = 4 if prio.get(cbl, 0) >= p else 0
            br = 8 if prio.get(cbr, 0) >= p else 0
            bits = tl | tr | bl | br
            if bits == 0:
                continue
            C.alpha_composite(ov[bits], (x * 64 + 32, (H - 1 - y) * 64 - 32))

bridge = Image.open('Assets/Art/Tiles/bridge.png').convert('RGBA').resize((64, 64))
for y in range(H):
    for x in range(W):
        if rows[H - 1 - y][x] == 'D':
            C.alpha_composite(bridge, (x * 64, (H - 1 - y) * 64))

C.save('art/tiles/dual/_full.png')
print('saved', W, H)
