#!/usr/bin/env python3
"""Render the actual stage1 game map (tiles + placed objects) to a flat PNG.

Faithful to the engine conventions:
- stage1_map.json base rows are TOP-FIRST; world y is up (cell y=0 = bottom).
- objects use BottomCenter pivot, PPU 64 => 1 world unit = 64 px = 1 cell.
- object pixel: x*64 (centre), (grid_h - y)*64 (sprite bottom). flipX + scale honored.
- painter order: higher world y (further back) drawn first (YSort).
"""
import json
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MAP = json.loads((ROOT / "Assets/Art/Maps/stage1_map.json").read_text(encoding="utf-8"))
OBJS = json.loads((ROOT / "Assets/Art/Maps/stage1_objects.json").read_text(encoding="utf-8"))

CELL = MAP["cell_px"]
W, H = MAP["grid_w"], MAP["grid_h"]
base = MAP["base"]

TILE_FILE = {
    "G": "grass.png", "R": "road.png", "I": "dirt.png",
    "W": "water_base_1.png", "S": "sand.png", "D": "bridge.png", "B": "grass.png",
}
tiles = {k: Image.open(ROOT / "Assets/Art/Tiles" / fn).convert("RGBA") for k, fn in TILE_FILE.items()}

print("terrain counts:", dict(Counter("".join(base))))

img = Image.new("RGBA", (W * CELL, H * CELL), (95, 140, 80, 255))
for r in range(H):
    for x in range(W):
        t = tiles.get(base[r][x], tiles["G"])
        pw, ph = t.size
        sxp, syp = (x * CELL) % pw, (r * CELL) % ph
        cell = t.crop((sxp, syp, sxp + CELL, syp + CELL))
        img.paste(cell, (x * CELL, r * CELL), cell)

cache = {}
def load(sp):
    if sp not in cache:
        cache[sp] = Image.open(ROOT / sp).convert("RGBA")
    return cache[sp]

# back-to-front: larger y first, then larger x (matches YSort x tie-break)
placed = sorted(OBJS["objects"], key=lambda o: (-o["y"], -o["x"]))
for o in placed:
    s = load(o["sprite"])
    sw, sh = int(round(s.width * o["sx"])), int(round(s.height * o["sy"]))
    spr = s.resize((sw, sh), Image.NEAREST) if (sw, sh) != s.size else s
    if o.get("flipX"):
        spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
    px = o["x"] * CELL
    py = (H - o["y"]) * CELL
    img.paste(spr, (int(round(px - sw / 2)), int(round(py - sh))), spr)

out = ROOT / "art/experiments/stage1_map_render_1920.png"
out.parent.mkdir(parents=True, exist_ok=True)
img.convert("RGB").save(out)
print(f"saved {out.relative_to(ROOT)}  {img.size}  objects={len(placed)}")
