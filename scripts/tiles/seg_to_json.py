"""Export a logic JSON (demo_map.json schema) from segnew.png.

Reads the seg image, classifies each 64px cell by dominant color into a terrain
letter, and writes scripts/tiles/out/segnew_map.json (grid_size, cell_px,
palette, base rows). Does NOT modify the seg image.

Run from repo root (venv with Pillow + numpy):
  python scripts/tiles/seg_to_json.py
"""

from __future__ import annotations

import json
import os

import numpy as np
from PIL import Image

TILE = 64
SEG = os.path.join("scripts", "tiles", "segnew.png")
OUT_JSON = os.path.join("scripts", "tiles", "out", "segnew_map.json")

# letter -> palette entry (rgb + gameplay meta), matches demo_map.json schema
PALETTE = {
    "G": {"name": "Grass/Plains", "rgb": [124, 176, 76], "walkable": True, "move_cost": 1, "height": 110},
    "R": {"name": "Road", "rgb": [201, 178, 124], "walkable": True, "move_cost": 1, "height": 100},
    "F": {"name": "Forest", "rgb": [47, 92, 47], "walkable": False, "move_cost": 0, "height": 150},
    "W": {"name": "Water", "rgb": [60, 120, 200], "walkable": False, "move_cost": 0, "height": 30},
    "C": {"name": "Cliff/Rock", "rgb": [120, 110, 130], "walkable": False, "move_cost": 0, "height": 240},
    "B": {"name": "Building", "rgb": [96, 60, 56], "walkable": False, "move_cost": 0, "height": 210},
    "L": {"name": "Wall", "rgb": [180, 180, 185], "walkable": False, "move_cost": 0, "height": 190},
    "D": {"name": "Bridge", "rgb": [150, 110, 70], "walkable": True, "move_cost": 1, "height": 90},
}
LETTERS = list(PALETTE.keys())
KEY_RGB = np.array([PALETTE[k]["rgb"] for k in LETTERS])


def _nearest_letter(rgb: np.ndarray) -> str:
    d = np.sum((KEY_RGB.astype(int) - rgb.astype(int)) ** 2, axis=1)
    return LETTERS[int(np.argmin(d))]


def main() -> None:
    img = np.array(Image.open(SEG).convert("RGB"))

    h, w, _ = img.shape
    gx, gy = w // TILE, h // TILE
    rows = []
    for cy in range(gy):
        row = []
        for cx in range(gx):
            block = img[cy * TILE:(cy + 1) * TILE, cx * TILE:(cx + 1) * TILE]
            cols, counts = np.unique(block.reshape(-1, 3), axis=0, return_counts=True)
            dom = cols[int(np.argmax(counts))]
            row.append(_nearest_letter(dom))
        rows.append("".join(row))

    data = {
        "name": "segnew_village_battlefield",
        "grid_size": gx,
        "cell_px": TILE,
        "palette": PALETTE,
        "legend": "G=Grass R=Road F=Forest W=Water C=Cliff B=Building L=Wall D=Bridge",
        "base": rows,
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # sanity: every row must be exactly grid_size chars (MapGrid.cs drops bad rows)
    bad = [i for i, r in enumerate(rows) if len(r) != gx]
    print(f"wrote {OUT_JSON}  grid {gx}x{gy}  bad rows: {bad}")


if __name__ == "__main__":
    main()
