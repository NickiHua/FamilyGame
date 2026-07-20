"""Measure chibi head length (crown->chin) and head:body ratio.

Workflow:
  1. `--gridsheet`  : render a top-aligned 5px grid sheet of every entry so you can
                      read off crown/chin y (in each sprite's own bbox-crop coords).
  2. fill crown/chin into the roster json.
  3. `--verify`     : draw crown/chin/eye lines on each sprite + print a head:body table.

Roster json format: list of {"label","png","crown"?,"chin"?,"eye"?}
crown/chin/eye are y-coords in the sprite's alpha-bbox-cropped space (crop top = 0).
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np


def bbox_crop(png):
    im = Image.open(png).convert('RGBA')
    a = np.array(im)[:, :, 3]
    ys, xs = np.where(a > 16)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def gridsheet(entries, out, scale=7, gap=26, step=5):
    crops = [(e['label'], bbox_crop(e['png'])) for e in entries]
    H = max(c.height for _, c in crops)
    colw = max(c.width for _, c in crops) + gap
    leftm = 40
    W = leftm + colw * len(crops)
    canvas = Image.new('RGBA', (W, H), (24, 24, 32, 255))
    place = []
    for i, (lab, c) in enumerate(crops):
        cx = leftm + i * colw + (colw - c.width) // 2
        canvas.alpha_composite(c, (cx, 0))
        place.append((lab, cx, c.height))
    big = canvas.resize((W * scale, H * scale), Image.NEAREST)
    d = ImageDraw.Draw(big)
    for y in range(0, H + 1, step):
        yy = y * scale
        strong = (y % 10 == 0)
        d.line([(0, yy), (W * scale, yy)], fill=(120, 180, 140, 200) if strong else (55, 85, 65, 120), width=1)
        if strong:
            d.text((2, yy + 1), str(y), fill=(160, 220, 175, 255))
    for lab, cx, ch in place:
        d.text((cx * scale + 2, 2), lab, fill=(235, 235, 130, 255))
        d.text((cx * scale + 2, H * scale - 14), f'h{ch}', fill=(200, 220, 255, 255))
    big.save(out)
    print('saved gridsheet', out, big.size)


def verify(entries, out, scale=7, gap=26):
    ready = [e for e in entries if e.get('crown') is not None and e.get('chin') is not None]
    crops = [(e, bbox_crop(e['png'])) for e in ready]
    H = max(c.height for _, c in crops)
    colw = max(c.width for _, c in crops) + gap
    leftm = 10
    W = leftm + colw * len(crops)
    canvas = Image.new('RGBA', (W, H), (24, 24, 32, 255))
    place = []
    for i, (e, c) in enumerate(crops):
        cx = leftm + i * colw + (colw - c.width) // 2
        canvas.alpha_composite(c, (cx, 0))
        place.append((e, cx, c))
    big = canvas.resize((W * scale, H * scale), Image.NEAREST)
    d = ImageDraw.Draw(big)
    rows = []
    for e, cx, c in place:
        crown, chin, eye = e['crown'], e['chin'], e.get('eye')
        x0 = cx * scale
        x1 = (cx + c.width) * scale
        d.line([(x0, crown * scale), (x1, crown * scale)], fill=(255, 70, 70, 255), width=2)
        d.line([(x0, chin * scale), (x1, chin * scale)], fill=(70, 140, 255, 255), width=2)
        if eye is not None:
            d.line([(x0, eye * scale), (x1, eye * scale)], fill=(255, 200, 60, 200), width=1)
        head = chin - crown
        total = c.height
        ratio = round(total / head, 2)
        d.text((x0 + 2, 2), e['label'], fill=(235, 235, 130, 255))
        d.text((x0 + 2, crown * scale - 13), f'crown {crown}', fill=(255, 70, 70, 255))
        d.text((x0 + 2, chin * scale + 2), f'chin {chin}', fill=(70, 140, 255, 255))
        d.text((x0 + 2, H * scale - 26), f'head {head}', fill=(255, 255, 255, 255))
        d.text((x0 + 2, H * scale - 13), f'{ratio}H', fill=(150, 255, 150, 255))
        rows.append((e['label'], head, total, ratio, round(head / total * 100)))
    big.save(out)
    print('saved verify', out, big.size)
    print()
    print(f'{"label":16s} {"head":>5s} {"total":>6s} {"ratio":>6s} {"head%":>6s}')
    for lab, head, total, ratio, pct in rows:
        print(f'{lab:16s} {head:5d} {total:6d} {ratio:6.2f} {pct:5d}%')


def one(entry, out, scale=12, headview=64):
    crop = bbox_crop(entry['png'])
    W, H = crop.size
    view = min(headview, H)
    reg = crop.crop((0, 0, W, view))
    big = reg.resize((W * scale, view * scale), Image.NEAREST)
    d = ImageDraw.Draw(big)
    for y in range(0, view + 1, 1):
        yy = y * scale
        strong = (y % 5 == 0)
        d.line([(0, yy), (W * scale, yy)], fill=(120, 180, 140, 170) if strong else (55, 85, 65, 90), width=1)
        if strong:
            d.text((2, yy + 1), str(y), fill=(160, 220, 175, 255))
    crown, chin, eye = entry['crown'], entry['chin'], entry.get('eye')
    d.line([(0, crown * scale), (W * scale, crown * scale)], fill=(255, 70, 70, 255), width=2)
    d.line([(0, chin * scale), (W * scale, chin * scale)], fill=(70, 140, 255, 255), width=2)
    if eye is not None:
        d.line([(0, eye * scale), (W * scale, eye * scale)], fill=(255, 200, 60, 220), width=1)
    d.text((W * scale - 150, crown * scale - 13), f'crown {crown}', fill=(255, 70, 70, 255))
    d.text((W * scale - 150, chin * scale + 2), f'chin {chin}', fill=(70, 140, 255, 255))
    head = chin - crown
    d.text((4, 2), f'{entry["label"]}  head={head}  total={H}  {round(H/head,2)}H', fill=(255, 255, 255, 255))
    big.save(out)
    print(f'{entry["label"]}: head={head} total={H} ratio={round(H/head,2)} -> {out} {big.size}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('config')
    ap.add_argument('--gridsheet', action='store_true')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--one', default=None, help='label to render a single small head overlay')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    entries = json.loads(Path(a.config).read_text(encoding='utf-8'))
    if a.gridsheet:
        gridsheet(entries, a.out or 'pixellab/_tmp_luli_candidates/_head_gridsheet.png')
    if a.verify:
        verify(entries, a.out or 'pixellab/_tmp_luli_candidates/_head_verify.png')
    if a.one:
        e = next(x for x in entries if x['label'] == a.one)
        one(e, a.out or 'pixellab/_tmp_luli_candidates/_head_one.png')


if __name__ == '__main__':
    main()
