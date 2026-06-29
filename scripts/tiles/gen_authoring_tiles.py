"""Generate flat, clearly-distinct PLACEHOLDER terrain tiles for hand-painting a
map in Unity's Tile Palette. These are authoring swatches (solid colour + dark
border + a letter), NOT final art -- replace with real base tiles later.

Each tile is 64x64. The filename encodes the terrain code + name so the Unity
exporter can map a painted cell back to its terrain attributes.

Output -> Assets/Art/Tiles/authoring/<CODE>_<name>.png

Run from repo root:
  python scripts/tiles/gen_authoring_tiles.py
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

TILE = 64
OUT = os.path.join("Assets", "Art", "Tiles", "authoring")

# code, name, fill RGB, walkable, move_cost  (letter = code)
TERRAINS = [
    ("G", "grass",    (124, 176, 76),  True,  1),
    ("A", "farmland", (196, 186, 92),  True,  1),
    ("R", "road",     (201, 178, 124), True,  1),
    ("D", "bridge",   (150, 110, 70),  True,  1),
    ("F", "forest",   (47, 92, 47),    True,  2),
    ("H", "ford",     (120, 184, 210), True,  2),
    ("W", "water",    (60, 120, 200),  False, 0),
    ("C", "cliff",    (150, 150, 158), False, 0),
    ("B", "building", (120, 70, 60),   False, 0),
]


def _text_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    return (20, 20, 20) if sum(rgb) > 360 else (240, 240, 240)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for code, name, rgb, _walk, _cost in TERRAINS:
        img = Image.new("RGB", (TILE, TILE), rgb)
        d = ImageDraw.Draw(img)
        # 2px darker border so the grid stays visible while painting
        dark = tuple(max(0, c - 55) for c in rgb)
        d.rectangle((0, 0, TILE - 1, TILE - 1), outline=dark, width=2)
        # big letter in the centre for instant readability
        tc = _text_color(rgb)
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", 34)
        except Exception:
            font = None
        if font:
            bbox = d.textbbox((0, 0), code, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            d.text(((TILE - tw) / 2 - bbox[0], (TILE - th) / 2 - bbox[1]),
                   code, fill=tc, font=font)
        else:
            d.text((TILE // 2 - 4, TILE // 2 - 6), code, fill=tc)
        img.save(os.path.join(OUT, f"{code}_{name}.png"))
        print(f"  {code}_{name}.png  walkable={_walk} cost={_cost}")
    print("wrote ->", OUT)


if __name__ == "__main__":
    main()
