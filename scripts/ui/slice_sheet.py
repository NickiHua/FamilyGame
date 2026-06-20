"""Slice a transparent UI sheet into its individual parts via gutter detection.

The Gemini sheets lay parts out in rows/columns separated by fully-transparent gutters.
This finds those empty bands (projection profiles on alpha), splits the sheet into a
grid of content blocks, trims each to its tight bounding box, and writes them out.

Usage (run from repo root, venv with Pillow active):
  # auto-name parts <stem>_0.png, <stem>_1.png ... into <out>/<stem>/
  python scripts/ui/slice_sheet.py art/undecided_art/ui/_alpha/command_icons.png

  # custom output dir and gutter sensitivity
  python scripts/ui/slice_sheet.py sheet.png -o out/ --min-gap 8 --alpha 16

Options:
  -o/--output   Output directory (default: <sheet_dir>/sliced/<stem>/).
  --alpha       Alpha at/below which a pixel counts as empty. Default 12.
  --min-gap     Minimum transparent run (px) to treat as a gutter. Default 10.
  --min-size    Drop parts smaller than this (px, either dimension). Default 12.
  --pad         Transparent padding kept around each crop. Default 0.
"""

from __future__ import annotations

import argparse
import os

from PIL import Image


def _runs_with_content(profile: list[int], min_gap: int) -> list[tuple[int, int]]:
    """Given a per-line content count, return [start,end) spans of content, where
    gutters are transparent runs at least `min_gap` long. Short transparent runs
    inside a part are NOT treated as gutters (kept as content)."""
    n = len(profile)
    spans: list[tuple[int, int]] = []
    i = 0
    while i < n:
        if profile[i] == 0:
            i += 1
            continue
        # start of a content region; extend across short transparent gaps
        start = i
        gap = 0
        end = i
        while i < n:
            if profile[i] > 0:
                end = i + 1
                gap = 0
            else:
                gap += 1
                if gap >= min_gap:
                    break
            i += 1
        spans.append((start, end))
    return spans


def slice_sheet(img: Image.Image, alpha_thresh: int, min_gap: int,
                min_size: int, pad: int) -> list[Image.Image]:
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()

    # Binary opacity map.
    opaque = [[1 if px[x, y][3] > alpha_thresh else 0 for x in range(w)] for y in range(h)]

    # Row profile -> horizontal bands (rows of parts).
    row_profile = [sum(opaque[y]) for y in range(h)]
    bands = _runs_with_content(row_profile, min_gap)

    parts: list[Image.Image] = []
    for (y0, y1) in bands:
        # Column profile within this band -> individual parts left-to-right.
        col_profile = [sum(opaque[y][x] for y in range(y0, y1)) for x in range(w)]
        cols = _runs_with_content(col_profile, min_gap)
        for (x0, x1) in cols:
            # Tight-trim this block to actual content.
            bx0, by0, bx1, by1 = _tight_box(opaque, x0, x1, y0, y1, alpha_thresh)
            if bx1 - bx0 < min_size or by1 - by0 < min_size:
                continue
            bx0 = max(0, bx0 - pad)
            by0 = max(0, by0 - pad)
            bx1 = min(w, bx1 + pad)
            by1 = min(h, by1 + pad)
            parts.append(img.crop((bx0, by0, bx1, by1)))
    return parts


def _tight_box(opaque, x0: int, x1: int, y0: int, y1: int, _a: int):
    min_x, max_x, min_y, max_y = x1, x0, y1, y0
    for y in range(y0, y1):
        row = opaque[y]
        for x in range(x0, x1):
            if row[x]:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y
    if max_x < min_x:
        return x0, y0, x1, y1
    return min_x, min_y, max_x + 1, max_y + 1


def main() -> None:
    ap = argparse.ArgumentParser(description="Slice a transparent UI sheet into parts.")
    ap.add_argument("input", help="A transparent PNG sheet, or a folder of them.")
    ap.add_argument("-o", "--output", help="Output directory.")
    ap.add_argument("--alpha", type=int, default=12)
    ap.add_argument("--min-gap", type=int, default=10)
    ap.add_argument("--min-size", type=int, default=12)
    ap.add_argument("--pad", type=int, default=0)
    args = ap.parse_args()

    sheets: list[str]
    if os.path.isdir(args.input):
        sheets = [os.path.join(args.input, f) for f in sorted(os.listdir(args.input))
                  if f.lower().endswith(".png")]
    else:
        sheets = [args.input]

    for sheet in sheets:
        stem = os.path.splitext(os.path.basename(sheet))[0]
        out_dir = args.output or os.path.join(os.path.dirname(sheet), "sliced", stem)
        os.makedirs(out_dir, exist_ok=True)
        parts = slice_sheet(Image.open(sheet), args.alpha, args.min_gap,
                            args.min_size, args.pad)
        for i, part in enumerate(parts):
            out = os.path.join(out_dir, stem + "_" + str(i) + ".png")
            part.save(out)
        print(stem + ": " + str(len(parts)) + " part(s) -> " + os.path.relpath(out_dir))

    print("Done.")


if __name__ == "__main__":
    main()
