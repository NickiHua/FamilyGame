"""Slice the experimental attack sprite sheets into individual frames and build a
preview GIF for each.

The three sheets in art_undecided/experiments/ were AI-generated and each has a
different layout (clean grid / captions under frames / dark bg with captions and a
title block). Rather than auto-detect everything, we describe each sheet with a
small config: one or more horizontal "bands" (the sprite rows, excluding caption /
title text), how many columns to split that band into, and which cells to skip
(e.g. a duplicated transition frame).

For every cell we:
  * split the band into equal-width columns,
  * find the foreground (pixels far from the sheet background colour),
  * crop tight to that foreground (clamped to the cell so we don't grab a
    neighbour's staff/sword),
  * paste it bottom-centre onto a uniform canvas filled with the sheet's bg colour.

All frames are then written as a looping GIF (and, optionally, as individual PNGs).

Run from repo root with the project venv:
  .\\.venv\\Scripts\\python.exe scripts\\sprites\\sheet_to_gif.py
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np
from PIL import Image
from scipy import ndimage

EXP = "art_undecided/experiments"
OUT = os.path.join(EXP, "gifs")


@dataclass
class Band:
    y0: int
    y1: int
    cols: int
    x0: int = 0
    x1: int | None = None      # default = full width
    skip: tuple[int, ...] = ()  # column indices (0-based) to drop


@dataclass
class Sheet:
    name: str
    path: str
    bands: list[Band]
    fg_thresh: int = 60         # colour distance from bg to count as foreground
    pad: int = 8                # transparent-ish margin kept around each crop
    frame_ms: int = 120
    bg: tuple[int, int, int] | None = None  # override; else sampled from border


SHEETS = [
    Sheet(
        name="gemini_swordman",
        path=f"{EXP}/gemini_swordman_attack.png",
        bands=[Band(60, 375, 5), Band(420, 755, 5)],
    ),
    Sheet(
        name="gemini_mage",
        path=f"{EXP}/gemini_mage_attack.png",
        # Gemini crammed/overlapped the poses, so frames can't be split on gaps.
        # Manual x ranges: isolated frame 1, the crammed middle (4 frames), the
        # isolated frame 6, then row 2's distinct poses (its first cell repeats
        # frame 6, so skip it).
        bands=[
            Band(20, 335, 1, x0=20, x1=210),     # 1. Ready
            Band(20, 335, 4, x0=210, x1=950),    # 2-5 channel/lunge (crammed)
            Band(20, 335, 1, x0=950, x1=1300),   # 6. The Cast
            Band(440, 705, 5, x0=0, x1=1408, skip=(0,)),  # 7-10
        ],
    ),
    Sheet(
        name="gpt_swordman",
        path=f"{EXP}/gpt_swordman_attack.png",
        # dark bg; sprite rows sit below their captions / the title block
        bands=[Band(295, 665, 4), Band(755, 1140, 4)],
        fg_thresh=40,
    ),
    Sheet(
        name="gemini_swordman2",
        path=f"{EXP}/Gemini_swordman2.png",
        # East-facing draw-and-slash, dark navy bg, clean 2x4
        bands=[Band(45, 375, 4), Band(400, 715, 4)],
        fg_thresh=40,
    ),
    Sheet(
        name="gemini_swordman3",
        path=f"{EXP}/Gemini_swordman3.png",
        # East-facing draw-and-slash, grey-blue bg, clean 2x4
        bands=[Band(40, 385, 4), Band(415, 740, 4)],
    ),
]


def border_bg(rgb: np.ndarray) -> np.ndarray:
    edges = np.concatenate([
        rgb[0:6].reshape(-1, 3), rgb[-6:].reshape(-1, 3),
        rgb[:, 0:6].reshape(-1, 3), rgb[:, -6:].reshape(-1, 3),
    ])
    return np.median(edges, axis=0)


def clean_cell_mask(cell_mask: np.ndarray) -> np.ndarray:
    """Drop small detached components (a neighbour's sword/staff tip that pokes
    into this cell) while keeping the body AND big effects like a sword-light arc.
    A component survives if it is large in absolute terms OR a decent fraction of
    the biggest blob."""
    labels, n = ndimage.label(cell_mask)
    if n <= 1:
        return cell_mask
    areas = ndimage.sum(cell_mask, labels, index=range(1, n + 1))
    biggest = areas.max()
    keep = {i + 1 for i, a in enumerate(areas) if a >= max(450, 0.07 * biggest)}
    return np.isin(labels, list(keep))


def extract_cells(sheet: Sheet) -> tuple[list[tuple[Image.Image, Image.Image]], tuple[int, int, int]]:
    im = Image.open(sheet.path).convert("RGB")
    rgb = np.asarray(im).astype(np.int16)
    bg = np.array(sheet.bg) if sheet.bg else border_bg(rgb)
    fg_mask = np.abs(rgb - bg).sum(axis=2) > sheet.fg_thresh
    bg_tuple = tuple(int(c) for c in bg)

    crops: list[tuple[Image.Image, Image.Image]] = []
    for band in sheet.bands:
        x1 = band.x1 if band.x1 is not None else im.width
        cell_w = (x1 - band.x0) / band.cols
        for c in range(band.cols):
            if c in band.skip:
                continue
            cx0 = int(round(band.x0 + c * cell_w))
            cx1 = int(round(band.x0 + (c + 1) * cell_w))
            cell_mask = clean_cell_mask(fg_mask[band.y0:band.y1, cx0:cx1])
            ys, xs = np.where(cell_mask)
            if len(xs) == 0:
                continue
            bx0 = cx0 + int(xs.min())
            bx1 = cx0 + int(xs.max()) + 1
            by0 = band.y0 + int(ys.min())
            by1 = band.y0 + int(ys.max()) + 1
            # pad, clamped to the cell horizontally and band vertically
            bx0 = max(cx0, bx0 - sheet.pad)
            bx1 = min(cx1, bx1 + sheet.pad)
            by0 = max(band.y0, by0 - sheet.pad)
            by1 = min(band.y1, by1 + sheet.pad)
            crop = im.crop((bx0, by0, bx1, by1))
            # paste-mask in the same crop frame so checkerboard / leftover bg is
            # replaced by a clean flat colour later
            sub = np.zeros(fg_mask.shape, bool)
            sub[band.y0:band.y1, cx0:cx1] = cell_mask
            mask = Image.fromarray((sub[by0:by1, bx0:bx1] * 255).astype(np.uint8))
            crops.append((crop, mask))
    return crops, bg_tuple


def assemble(sheet: Sheet) -> None:
    crops, bg = extract_cells(sheet)
    if not crops:
        print(f"!! {sheet.name}: no frames found")
        return
    cw = max(c.width for c, _ in crops)
    ch = max(c.height for c, _ in crops)
    margin = 16
    canvas_w, canvas_h = cw + margin * 2, ch + margin * 2

    frames: list[Image.Image] = []
    for c, mask in crops:
        frame = Image.new("RGB", (canvas_w, canvas_h), bg)
        # bottom-centre align (feet on a common floor line)
        x = (canvas_w - c.width) // 2
        y = canvas_h - margin - c.height
        frame.paste(c, (x, y), mask)  # mask -> only foreground, clean flat bg
        frames.append(frame)

    os.makedirs(OUT, exist_ok=True)
    gif_path = os.path.join(OUT, f"{sheet.name}.gif")
    frames[0].save(
        gif_path, save_all=True, append_images=frames[1:],
        duration=sheet.frame_ms, loop=0, disposal=2, optimize=True,
    )
    # also dump individual frames for inspection
    fdir = os.path.join(OUT, sheet.name)
    os.makedirs(fdir, exist_ok=True)
    for i, f in enumerate(frames):
        f.save(os.path.join(fdir, f"frame_{i:02d}.png"))
    print(f"OK {sheet.name}: {len(frames)} frames -> {gif_path} (canvas {canvas_w}x{canvas_h})")


def main() -> None:
    for s in SHEETS:
        assemble(s)


if __name__ == "__main__":
    main()
