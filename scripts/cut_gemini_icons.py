"""Cut the Gemini-generated 6x3 icon sheet into individual transparent PNGs.

Background (black) is keyed out via connected-component flood fill seeded from
the outer border and an inner ring just inside the gold frame, so the gold frame
and the central object stay opaque while the black backdrop becomes transparent.
"""
from PIL import Image
import numpy as np
from scipy import ndimage
import os

SRC = "art_undecided/ui/icon/Gemini_Generated_Image_1dl7471dl7471dl7.png"
OUTDIR = "art_undecided/ui/icon/cut"

COL_LEFT = [43, 270, 497, 724, 950, 1177]
ROW_TOP = [56, 290]
CW = 200
CH = 200

NAMES = [
    ["icon_frame_empty", "icon_attack", "icon_skill", "icon_magic", "icon_defend", "icon_wait"],
    ["icon_item", "icon_move", "icon_transform", "icon_equip", "icon_status", "icon_summon"],
]


def cut_cell(cell):
    rgb = cell[:, :, :3].astype(int)
    mx = rgb.max(axis=2)
    black = mx < 60
    lbl, _ = ndimage.label(black)
    h, w = black.shape
    seeds = []
    for x in range(0, w, 8):
        seeds += [(0, x), (h - 1, x)]
    for y in range(0, h, 8):
        seeds += [(y, 0), (y, w - 1)]
    m = 48
    for x in range(m, w - m, 10):
        seeds += [(m, x), (h - 1 - m, x)]
    for y in range(m, h - m, 10):
        seeds += [(y, m), (y, w - 1 - m)]
    keep = set()
    for (yy, xx) in seeds:
        v = lbl[yy, xx]
        if v != 0:
            keep.add(v)
    bg = np.zeros_like(black)
    for v in keep:
        bg |= (lbl == v)
    out = cell.copy()
    out[:, :, 3] = np.where(bg, 0, 255).astype(np.uint8)
    return out


def main():
    im = np.array(Image.open(SRC).convert("RGBA"))
    os.makedirs(OUTDIR, exist_ok=True)
    for ri, rowtop in enumerate(ROW_TOP):
        for ci, left in enumerate(COL_LEFT):
            cell = im[rowtop:rowtop + CH, left:left + CW].copy()
            out = cut_cell(cell)
            Image.fromarray(out, "RGBA").save(f"{OUTDIR}/{NAMES[ri][ci]}.png")

    pad = 8
    mw = 6 * (CW + pad) + pad
    mh = 2 * (CH + pad) + pad
    mont = Image.new("RGBA", (mw, mh), (255, 0, 255, 255))
    for ri in range(2):
        for ci in range(6):
            p = Image.open(f"{OUTDIR}/{NAMES[ri][ci]}.png")
            mont.paste(p, (pad + ci * (CW + pad), pad + ri * (CH + pad)), p)
    mont.save(f"{OUTDIR}/_montage_review.png")
    print("done; saved 12 icons + _montage_review.png to", OUTDIR)


if __name__ == "__main__":
    main()
