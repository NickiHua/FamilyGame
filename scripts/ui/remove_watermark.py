"""Remove the Gemini sparkle watermark from UI sprites.

The watermark is a small light-pink / lavender four-point star that sits
DETACHED from the artwork (separated by transparent pixels). We seed on
pink pixels and flood-fill across the opaque region from those seeds; the
transparent gutter stops the fill from leaking into the real artwork, so
only the isolated sparkle blob gets erased.

Usage:
    python scripts/ui/remove_watermark.py <file|folder> [-o OUT]
                                          [--max-area 12000] [--alpha 8]
                                          [--pink 20] [--dry-run]

Folder mode processes every PNG recursively. Without -o the files are
edited in place; with -o the cleaned copies mirror the tree under OUT.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import deque

import numpy as np
from PIL import Image


def find_watermark_mask(rgba: np.ndarray, alpha_thresh: int,
                        pink_delta: int, max_area: int) -> np.ndarray:
    """Return a boolean mask of pixels belonging to detached pink blobs."""
    h, w, _ = rgba.shape
    r = rgba[:, :, 0].astype(np.int16)
    g = rgba[:, :, 1].astype(np.int16)
    b = rgba[:, :, 2].astype(np.int16)
    a = rgba[:, :, 3]

    opaque = a > alpha_thresh
    # Pink / lavender: red and blue both clearly above green, and bright.
    pink_seed = (opaque
                 & ((r - g) >= pink_delta)
                 & ((b - g) >= pink_delta)
                 & (r > 120) & (b > 120))

    remove = np.zeros((h, w), dtype=bool)
    if not pink_seed.any():
        return remove

    visited = np.zeros((h, w), dtype=bool)
    seed_coords = np.argwhere(pink_seed)

    for sy, sx in seed_coords:
        if visited[sy, sx]:
            continue
        # Flood fill the connected opaque blob containing this seed.
        blob: list[tuple[int, int]] = []
        dq = deque([(int(sy), int(sx))])
        visited[sy, sx] = True
        while dq:
            y, x = dq.popleft()
            blob.append((y, x))
            if len(blob) > max_area:
                break  # too big -> not a watermark, abandon
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w \
                        and not visited[ny, nx] and opaque[ny, nx]:
                    visited[ny, nx] = True
                    dq.append((ny, nx))

        if len(blob) <= max_area:
            for (y, x) in blob:
                remove[y, x] = True

    return remove


def process(path: str, out_path: str, alpha_thresh: int,
            pink_delta: int, max_area: int, dry_run: bool) -> bool:
    img = Image.open(path).convert("RGBA")
    arr = np.array(img)
    mask = find_watermark_mask(arr, alpha_thresh, pink_delta, max_area)
    count = int(mask.sum())
    if count == 0:
        return False

    if not dry_run:
        arr[mask] = (0, 0, 0, 0)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        Image.fromarray(arr, "RGBA").save(out_path)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="Strip Gemini sparkle watermark.")
    ap.add_argument("target", help="PNG file or folder")
    ap.add_argument("-o", "--out", default=None,
                    help="Output file/folder (default: in place)")
    ap.add_argument("--alpha", type=int, default=8,
                    help="Alpha threshold for 'opaque' (default 8)")
    ap.add_argument("--pink", type=int, default=20,
                    help="Min (R-G) and (B-G) to count as pink (default 20)")
    ap.add_argument("--max-area", type=int, default=12000,
                    help="Max blob area in px to treat as watermark")
    ap.add_argument("--dry-run", action="store_true",
                    help="Only report, do not write")
    args = ap.parse_args()

    targets: list[tuple[str, str]] = []
    if os.path.isdir(args.target):
        for root, _dirs, files in os.walk(args.target):
            for name in files:
                if name.lower().endswith(".png"):
                    src = os.path.join(root, name)
                    if args.out:
                        rel = os.path.relpath(src, args.target)
                        dst = os.path.join(args.out, rel)
                    else:
                        dst = src
                    targets.append((src, dst))
    else:
        dst = args.out or args.target
        targets.append((args.target, dst))

    hit = 0
    for src, dst in targets:
        changed = process(src, dst, args.alpha, args.pink,
                           args.max_area, args.dry_run)
        if changed:
            hit += 1
            tag = "would clean" if args.dry_run else "cleaned"
            print(tag + ": " + src)
    print("done. watermark found in " + str(hit) + " / "
          + str(len(targets)) + " file(s).")


if __name__ == "__main__":
    main()
