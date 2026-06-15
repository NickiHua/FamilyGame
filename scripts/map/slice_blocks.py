#!/usr/bin/env python3
"""Slice the painted battlefield art into a 7x7 grid of review blocks.

35x35 logic grid / 7 = exactly 5x5 cells per block. Blocks are named R1-C1 ..
R7-C7 (R = block row top->bottom, C = block col left->right). Each block image
is upscaled for clarity and overlaid with:
  - per-cell grid lines + the CURRENT JSON terrain letter
  - the GLOBAL cell coordinate (col,row; col 0 = left, row 0 = top) so edits map
    straight back into demo_map.json base[row][col].

Also (re)generates a tracking JSON (scripts/map/out/review_blocks.json) listing
every block with a "status" + "notes" field so we can track which blocks have
been reviewed/fixed together. Existing statuses/notes are preserved on re-run.

Run (CWD = FamilyGame/):
    python scripts/map/slice_blocks.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

JSON = Path("Assets/Art/Maps/demo_map.json")
SRC = Path("art/maps/demo_map.png")
OUT_DIR = Path("scripts/map/out/blocks")
TRACK = Path("scripts/map/out/review_blocks.json")

BLOCKS = 7          # 7x7 blocks
BLOCK_PX = 768      # output size per block (upscaled for readability)

WALKABLE = set("GRFD")
TINT = {
    "W": (60, 120, 230, 110),
    "C": (160, 160, 170, 120),
    "B": (170, 60, 50, 120),
    "L": (245, 245, 250, 120),
    "D": (40, 220, 90, 80),
}


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    data = json.loads(JSON.read_text(encoding="utf-8"))
    size = data["grid_size"]            # 35
    base = data["base"]
    assert size % BLOCKS == 0, f"{size} not divisible by {BLOCKS}"
    cells = size // BLOCKS               # 5

    img = Image.open(SRC).convert("RGB")
    w, h = img.size
    cw, ch = w / size, h / size          # source px per cell

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cell_out = BLOCK_PX / cells          # output px per cell
    font = load_font(int(cell_out * 0.32))
    coord_font = load_font(int(cell_out * 0.16))

    for br in range(BLOCKS):             # block row (top->bottom)
        for bc in range(BLOCKS):         # block col (left->right)
            c0, r0 = bc * cells, br * cells          # top-left global cell
            x0, y0 = round(c0 * cw), round(r0 * ch)
            x1, y1 = round((c0 + cells) * cw), round((r0 + cells) * ch)
            crop = img.crop((x0, y0, x1, y1)).resize(
                (BLOCK_PX, BLOCK_PX), Image.LANCZOS
            ).convert("RGBA")
            ov = Image.new("RGBA", crop.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            for ry in range(cells):
                for rx in range(cells):
                    gc, gr = c0 + rx, r0 + ry        # global cell coord
                    t = base[gr][gc]
                    px, py = rx * cell_out, ry * cell_out
                    if t in TINT:
                        d.rectangle([px, py, px + cell_out, py + cell_out],
                                    fill=TINT[t])
                    d.rectangle([px, py, px + cell_out, py + cell_out],
                                outline=(0, 0, 0, 120), width=2)
                    col = (255, 255, 0, 255) if t not in WALKABLE else (255, 255, 255, 210)
                    d.text((px + cell_out * 0.36, py + cell_out * 0.30), t,
                           fill=col, font=font)
                    d.text((px + 4, py + 3), f"{gc},{gr}",
                           fill=(0, 255, 255, 255), font=coord_font)
            name = f"R{br + 1}-C{bc + 1}"
            out = Image.alpha_composite(crop, ov).convert("RGB")
            out.save(OUT_DIR / f"{name}.png")

    # Build / merge tracking JSON (preserve existing status + notes).
    old = {}
    if TRACK.exists():
        try:
            old = {b["name"]: b for b in json.loads(TRACK.read_text("utf-8"))["blocks"]}
        except (KeyError, json.JSONDecodeError):
            old = {}
    blocks = []
    for br in range(BLOCKS):
        for bc in range(BLOCKS):
            c0, r0 = bc * cells, br * cells
            name = f"R{br + 1}-C{bc + 1}"
            prev = old.get(name, {})
            blocks.append({
                "name": name,
                "cols": [c0, c0 + cells - 1],   # inclusive global col range
                "rows": [r0, r0 + cells - 1],   # inclusive global row range
                "status": prev.get("status", "pending"),  # pending|reviewed|fixed|ok
                "notes": prev.get("notes", ""),
            })
    TRACK.write_text(json.dumps(
        {"grid_size": size, "block_cells": cells, "blocks": blocks},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {BLOCKS*BLOCKS} blocks to {OUT_DIR} and tracking {TRACK}")


if __name__ == "__main__":
    main()
