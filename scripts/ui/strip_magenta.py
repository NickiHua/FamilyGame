"""Chroma-key the magenta background out of AI-generated UI art, producing true-alpha PNGs.

The Gemini UI sheets come on a solid magenta (~255,0,255) backdrop. This keys that
color out to real transparency, and also de-fringes (removes the magenta spill that
bleeds onto anti-aliased edges) so the art doesn't get a pink halo on dark backgrounds.

Usage (run from repo root, venv with Pillow active):
  # one file -> writes alongside as <name>_alpha.png
  python scripts/ui/strip_magenta.py art/undecided_art/ui/range_tiles.png

  # a whole folder -> mirrors every *.png into <folder>/_alpha/
  python scripts/ui/strip_magenta.py art/undecided_art/ui

  # explicit output, custom tolerance, key only from the border (flood fill)
  python scripts/ui/strip_magenta.py in.png -o out.png --tolerance 80 --edge-only

Options:
  -o/--output      Output file (single input) or output dir (folder input).
  --tolerance      Color distance (0-441) treated as "background". Default 90.
  --soft           Width of the soft alpha falloff band past the hard cut. Default 40.
  --edge-only      Only remove magenta reachable from the image border (flood fill),
                   so any magenta INSIDE the artwork is preserved.
  --key            Override the key color as "R,G,B". Default = sampled from corners.
"""

from __future__ import annotations

import argparse
import os
from collections import deque

from PIL import Image


def _sample_key(img: Image.Image) -> tuple[int, int, int]:
    """Guess the background color from the four corner pixels (majority)."""
    w, h = img.size
    corners = [img.getpixel((0, 0)), img.getpixel((w - 1, 0)),
               img.getpixel((0, h - 1)), img.getpixel((w - 1, h - 1))]
    corners = [c[:3] for c in corners]
    # pick the corner color that appears most often; ties -> first
    best = max(set(corners), key=corners.count)
    return best


def _dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def strip(img: Image.Image, key: tuple[int, int, int] | None,
          tolerance: float, soft: float, edge_only: bool,
          despill: int = 0, despill_radius: int = 2) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    if key is None:
        key = _sample_key(img)

    # Precompute per-pixel "is background" alpha (0 = fully bg, 255 = fully keep).
    def keep_alpha(r: int, g: int, b: int) -> int:
        d = _dist((r, g, b), key)
        if d <= tolerance:
            return 0
        if d >= tolerance + soft:
            return 255
        return int(255 * (d - tolerance) / soft)

    if edge_only:
        # Flood fill background from the borders; only those pixels become transparent.
        visited = bytearray(w * h)
        q: deque[tuple[int, int]] = deque()
        for x in range(w):
            for y in (0, h - 1):
                q.append((x, y))
        for y in range(h):
            for x in (0, w - 1):
                q.append((x, y))
        while q:
            x, y = q.popleft()
            i = y * w + x
            if visited[i]:
                continue
            visited[i] = 1
            r, g, b, a = px[x, y]
            if _dist((r, g, b), key) > tolerance + soft:
                continue  # solid artwork edge -> stop spreading
            na = keep_alpha(r, g, b)
            px[x, y] = (r, g, b, min(a, na))
            if x > 0:
                q.append((x - 1, y))
            if x < w - 1:
                q.append((x + 1, y))
            if y > 0:
                q.append((x, y - 1))
            if y < h - 1:
                q.append((x, y + 1))
    else:
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                na = keep_alpha(r, g, b)
                if na < a:
                    px[x, y] = (r, g, b, na)

    _defringe(img, key)
    if despill > 0:
        _despill_magenta(img, despill, despill_radius)
    return img


def _despill_magenta(img: Image.Image, strength: int, radius: int) -> None:
    """Neutralise the opaque magenta/purple ring that survives keying at art edges.

    The leftover pixels read as magenta tint: both red and blue sit clearly above green
    (R-G and B-G large). We only touch OPAQUE pixels near a transparent pixel (within
    `radius`), so interior artwork — and genuinely red things like the potion (where blue
    is NOT above green) — are left alone. `strength` is the min channel gap to act on.
    """
    w, h = img.size
    px = img.load()

    # Mark opaque pixels that sit within `radius` of a transparent pixel.
    near_edge = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            if px[x, y][3] != 0:
                continue
            for dy in range(-radius, radius + 1):
                ny = y + dy
                if ny < 0 or ny >= h:
                    continue
                for dx in range(-radius, radius + 1):
                    nx = x + dx
                    if 0 <= nx < w:
                        near_edge[ny * w + nx] = 1

    for y in range(h):
        for x in range(w):
            i = y * w + x
            if not near_edge[i]:
                continue
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            # Magenta tint = red AND blue both above green by at least `strength`.
            if r - g >= strength and b - g >= strength:
                cap = g + strength // 2
                px[x, y] = (min(r, cap), g, min(b, cap), a)


def _defringe(img: Image.Image, key: tuple[int, int, int]) -> None:
    """Pull edge pixels away from the key color so no colored halo remains.

    For partially transparent pixels we un-blend the key spill: the visible color is
    assumed to be (fg*alpha + key*(1-alpha)); solve back for fg and clamp.
    """
    w, h = img.size
    px = img.load()
    kr, kg, kb = key
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0 or a == 255:
                continue
            f = a / 255.0
            nr = int(min(255, max(0, (r - kr * (1 - f)) / f)))
            ng = int(min(255, max(0, (g - kg * (1 - f)) / f)))
            nb = int(min(255, max(0, (b - kb * (1 - f)) / f)))
            px[x, y] = (nr, ng, nb, a)


def _process_file(src: str, dst: str, args: argparse.Namespace) -> None:
    key = None
    if args.key:
        key = tuple(int(c) for c in args.key.split(","))  # type: ignore[assignment]
    img = Image.open(src)
    out = strip(img, key, args.tolerance, args.soft, args.edge_only,
                args.despill, args.despill_radius)
    out.save(dst)
    print("  " + os.path.relpath(src) + "  ->  " + os.path.relpath(dst))


def main() -> None:
    ap = argparse.ArgumentParser(description="Key the magenta background out of UI art.")
    ap.add_argument("input", help="A PNG file or a folder of PNGs.")
    ap.add_argument("-o", "--output", help="Output file (file input) or dir (folder input).")
    ap.add_argument("--tolerance", type=float, default=90.0)
    ap.add_argument("--soft", type=float, default=40.0)
    ap.add_argument("--edge-only", action="store_true")
    ap.add_argument("--despill", type=int, default=40,
                    help="Neutralise the opaque magenta ring at art edges; channel gap "
                         "(R-G and B-G) to act on. 0 disables. Default 40.")
    ap.add_argument("--despill-radius", type=int, default=2,
                    help="How many px from a transparent pixel the despill reaches. Default 2.")
    ap.add_argument("--key", help='Key color "R,G,B" (default: sampled from corners).')
    args = ap.parse_args()

    if os.path.isdir(args.input):
        out_dir = args.output or os.path.join(args.input, "_alpha")
        os.makedirs(out_dir, exist_ok=True)
        pngs = [f for f in sorted(os.listdir(args.input)) if f.lower().endswith(".png")]
        print("Stripping magenta from " + str(len(pngs)) + " file(s) -> " + out_dir)
        for f in pngs:
            _process_file(os.path.join(args.input, f), os.path.join(out_dir, f), args)
    else:
        if args.output:
            dst = args.output
        else:
            root, ext = os.path.splitext(args.input)
            dst = root + "_alpha" + ext
        _process_file(args.input, dst, args)

    print("Done.")


if __name__ == "__main__":
    main()
