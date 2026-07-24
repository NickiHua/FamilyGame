#!/usr/bin/env python3
"""Generate 64x64 solid-color MARKER tiles for map-object placeholders.

Two sets per object (tree/house/stone/bridge):
  - plain : solid color only
  - letter: same solid color + a centered capital letter (white, dark outline)

These are painted onto a DUPLICATE Stage1 tilemap in Unity, exported/rendered,
then fed to Seedream as a layout ref. The letters help YOU eyeball them; Seedream
mostly keys off the distinct COLORS + the prompt legend.

Output -> art/tiles/markers/{house,tree,stone,bridge}.png
                            /{house_H,tree_T,stone_S,bridge_B}.png
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "art/tiles/markers"
OUT.mkdir(parents=True, exist_ok=True)

SIZE = 64

# name -> (RGB color, letter)
MARKERS = {
    "house":  ((74, 47, 27),  "H"),   # 深棕 dark brown
    "tree":   ((28, 74, 38),  "T"),   # 深绿 dark green
    "stone":  ((130, 130, 130), "S"), # 灰   gray
    "bridge": ((150, 95, 50), "B"),   # 棕   mid brown
}

FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


font = load_font(44)

for name, (rgb, letter) in MARKERS.items():
    # plain
    plain = Image.new("RGBA", (SIZE, SIZE), rgb + (255,))
    plain.save(OUT / f"{name}.png")

    # letter
    lettered = plain.copy()
    d = ImageDraw.Draw(lettered)
    bbox = d.textbbox((0, 0), letter, font=font, stroke_width=3)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (SIZE - tw) / 2 - bbox[0]
    y = (SIZE - th) / 2 - bbox[1]
    d.text((x, y), letter, font=font, fill=(255, 255, 255, 255),
           stroke_width=3, stroke_fill=(0, 0, 0, 255))
    suffix = {"house": "H", "tree": "T", "stone": "S", "bridge": "B"}[name]
    lettered.save(OUT / f"{name}_{suffix}.png")

    print(f"{name}: {rgb} letter '{letter}'")

print(f"\nsaved 8 tiles -> {OUT.relative_to(ROOT)}")
