"""Make a tile seamless by healing ONLY a thin border band (no half-image blend).

For each axis, cross-fade just the outermost `band` pixels of the two opposite
edges toward each other so they match when tiled — the interior is left completely
untouched. This kills the hard edge seam WITHOUT introducing the large soft blotch
pattern that a half-offset blend does, so the texture stays uniform.

Good default for noise-like ground tiles (road / dirt / sand / base grass). Still
not for tiles with big placed motifs — fix those by hand in Aseprite.

Usage:
  python scripts/tiles/make_seamless.py in.png out.png [band=6]
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image


def make_seamless(img: np.ndarray, band: int = 6) -> np.ndarray:
    a = img.astype(np.float32)
    h, w, _ = a.shape
    out = a.copy()
    # horizontal: blend the left `band` cols with the right `band` cols
    for k in range(band):
        alpha = 0.5 * (1 - k / band)  # 0.5 at the very edge -> 0 at `band`
        left = out[:, k, :].copy()
        right = out[:, w - 1 - k, :].copy()
        out[:, k, :] = left * (1 - alpha) + right * alpha
        out[:, w - 1 - k, :] = right * (1 - alpha) + left * alpha
    # vertical: blend the top `band` rows with the bottom `band` rows
    for k in range(band):
        alpha = 0.5 * (1 - k / band)
        top = out[k, :, :].copy()
        bot = out[h - 1 - k, :, :].copy()
        out[k, :, :] = top * (1 - alpha) + bot * alpha
        out[h - 1 - k, :, :] = bot * (1 - alpha) + top * alpha
    return np.clip(out, 0, 255).astype(np.uint8)


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    band = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    im = np.array(Image.open(src).convert("RGB"))
    Image.fromarray(make_seamless(im, band), "RGB").save(dst)
    print("wrote", dst)


if __name__ == "__main__":
    main()
