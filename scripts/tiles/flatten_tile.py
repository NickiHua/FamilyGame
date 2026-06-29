"""Flatten a tile's low-frequency luminance gradient (de-vignette).

GPT-Image tends to bake a subtle top-left-light / bottom-right-shadow gradient
even when told "flat lighting". On a tiled ground texture that corner-darkening
repeats as a visible grid and breaks edge matching. This removes the low-frequency
brightness trend while keeping local texture, using a WRAP-mode gaussian so the
result stays tileable.

Use on ground tiles (grass/road/dirt/sand/water) as a standard finishing step.

Usage:
  python scripts/tiles/flatten_tile.py in.png out.png [sigma_frac=0.25]
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def flatten(img: np.ndarray, sigma_frac: float = 0.25) -> np.ndarray:
    a = img.astype(np.float32)
    h, w = a.shape[:2]
    sigma = max(h, w) * sigma_frac
    out = np.empty_like(a)
    for c in range(a.shape[2]):
        low = gaussian_filter(a[:, :, c], sigma, mode="wrap")  # low-freq trend (tileable)
        out[:, :, c] = a[:, :, c] * (low.mean() / np.maximum(low, 1e-3))
    return np.clip(out, 0, 255).astype(np.uint8)


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    sf = float(sys.argv[3]) if len(sys.argv) > 3 else 0.25
    im = np.array(Image.open(src).convert("RGB"))
    Image.fromarray(flatten(im, sf), "RGB").save(dst)
    print("wrote", dst)


if __name__ == "__main__":
    main()
