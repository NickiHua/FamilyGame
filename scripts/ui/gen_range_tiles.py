"""Generate SRPG range-overlay tiles and the selection frame as true-alpha PNGs.

Why this exists: AI image models cannot produce real semi-transparent (alpha) overlays
-- they only paint a lighter solid color, add noise, and sometimes a watermark. Range
tiles are trivial geometry, so we generate them deterministically here.

Outputs (64x64, real alpha) into Assets/Art/UI/range/:
  move_tile.png    -- translucent blue movement-range cell, 1px darker edge
  attack_tile.png  -- translucent red attack-range cell, 1px darker edge
  select_frame.png -- gold corner-bracket selection frame, fully transparent center

Run from repo root (venv with Pillow active):
  python scripts/ui/gen_range_tiles.py
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

TILE = 64
OUT_DIR = os.path.join("Assets", "Art", "UI", "range")


def _range_tile(fill_rgb: tuple[int, int, int], edge_rgb: tuple[int, int, int],
                fill_alpha: int, edge_alpha: int) -> Image.Image:
    """A solid translucent cell with a 1px darker border on all four edges."""
    img = Image.new("RGBA", (TILE, TILE), fill_rgb + (fill_alpha,))
    px = img.load()
    edge = edge_rgb + (edge_alpha,)
    for i in range(TILE):
        px[i, 0] = edge          # top
        px[i, TILE - 1] = edge   # bottom
        px[0, i] = edge          # left
        px[TILE - 1, i] = edge   # right
    return img


def _select_frame(gold: tuple[int, int, int], arm: int = 18,
                  thick: int = 4) -> Image.Image:
    """Four L-shaped gold corner brackets, transparent center."""
    img = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    g = gold + (255,)
    n = TILE - 1
    # each corner = horizontal arm + vertical arm of `thick` px, `arm` px long
    # top-left
    d.rectangle([0, 0, arm, thick - 1], fill=g)
    d.rectangle([0, 0, thick - 1, arm], fill=g)
    # top-right
    d.rectangle([n - arm, 0, n, thick - 1], fill=g)
    d.rectangle([n - thick + 1, 0, n, arm], fill=g)
    # bottom-left
    d.rectangle([0, n - thick + 1, arm, n], fill=g)
    d.rectangle([0, n - arm, thick - 1, n], fill=g)
    # bottom-right
    d.rectangle([n - arm, n - thick + 1, n, n], fill=g)
    d.rectangle([n - thick + 1, n - arm, n, n], fill=g)
    return img


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    tiles = {
        "move_tile.png": _range_tile(
            fill_rgb=(70, 120, 230), edge_rgb=(30, 60, 150),
            fill_alpha=90, edge_alpha=160),
        "attack_tile.png": _range_tile(
            fill_rgb=(220, 70, 70), edge_rgb=(140, 30, 30),
            fill_alpha=90, edge_alpha=160),
        "select_frame.png": _select_frame(gold=(235, 200, 90)),
    }

    for name, img in tiles.items():
        path = os.path.join(OUT_DIR, name)
        img.save(path)
        print(f"wrote {path}  ({img.width}x{img.height} RGBA)")


if __name__ == "__main__":
    main()
