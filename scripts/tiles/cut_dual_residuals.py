"""Cut dual-grid corner residuals from base tiles.

Dual-grid: a display tile covers the 4 corners of 4 logic cells; each corner is
either "this terrain" or "not". 16 combinations -> 16 residual tiles. The residual
is the terrain texture masked to the present corners with a feathered alpha, so it
drapes over any lower-priority base beneath (priority handled in Unity).

Bit order (corner -> bit): TL=1, TR=2, BL=4, BR=8.
Output: art/tiles/dual/<name>/<bits>.png (64x64 RGBA), plus 0.png fully transparent.
"""
import os
import numpy as np
from PIL import Image

SRC = "Assets/Art/Tiles"
OUT = "art/tiles/dual"
TERRAINS = ["grass", "dirt", "road", "sand", "water"]
SIZE = 64
EDGE = 0.10  # smoothstep half-width; smaller = crisper/harder transition edge


def corner_weights(size):
    """Bilinear weight of each corner at every pixel (u,v in [0,1])."""
    u = (np.arange(size) + 0.5) / size
    v = (np.arange(size) + 0.5) / size
    U, V = np.meshgrid(u, v)  # V down, U right
    return {
        "TL": (1 - U) * (1 - V),
        "TR": U * (1 - V),
        "BL": (1 - U) * V,
        "BR": U * V,
    }


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def build_alpha(bits, cw):
    a = np.zeros((SIZE, SIZE))
    for name, bit in (("TL", 1), ("TR", 2), ("BL", 4), ("BR", 8)):
        if bits & bit:
            a = a + cw[name]
    # Hard cut: each pixel belongs fully to this terrain where its corners dominate
    # (weight >= 0.5), else fully transparent. No feather, no colour blending — the
    # adjacent higher-priority terrain simply clips the lower one.
    return np.where(a >= 0.5, 255, 0).astype("uint8")


def main():
    cw = corner_weights(SIZE)
    for t in TERRAINS:
        img = Image.open(f"{SRC}/{t}.png").convert("RGBA").resize((SIZE, SIZE))
        rgb = np.asarray(img)[..., :3]
        d = f"{OUT}/{t}"
        os.makedirs(d, exist_ok=True)
        for bits in range(16):
            a = build_alpha(bits, cw)
            out = np.dstack([rgb, a]).astype("uint8")
            Image.fromarray(out, "RGBA").save(f"{d}/{bits:02d}.png")
        print(f"{t}: 16 tiles -> {d}")


if __name__ == "__main__":
    main()
