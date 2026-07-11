#!/usr/bin/env python3
"""Bake map-sized water layers for stage1 from the terrain JSON.

The source texture is a square water material. It is tiled continuously across the
whole map, then masked by the water shape derived from stage1_map.json. Shoreline
layers are generated from the same water field so they line up with the water.

Outputs by default:
  Assets/Art/Maps/stage1_water_surface.png
  Assets/Art/Maps/stage1_shore_shadow.png
  Assets/Art/Maps/stage1_shore_shallow.png
  Assets/Art/Maps/stage1_water_debug.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import distance_transform_edt


CELL = 64
WATER_LETTERS = {"W", "D"}


def smoothstep(edge0: float, edge1: float, value: np.ndarray) -> np.ndarray:
    t = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def load_rows(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("base")
    if not rows or not isinstance(rows, list):
        raise SystemExit(f"ERROR: {path} does not contain a base row list.")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise SystemExit(f"ERROR: {path} contains non-rectangular base rows.")
    return rows


def dual_field(mask: np.ndarray, cell: int) -> np.ndarray:
    """Bilinear dual-grid field in image coordinates (row 0 is map top)."""
    grid_h, grid_w = mask.shape
    height, width = grid_h * cell, grid_w * cell
    py = np.arange(height, dtype=np.float32) / cell - 0.5
    px = np.arange(width, dtype=np.float32) / cell - 0.5
    px_grid, py_grid = np.meshgrid(px, py)
    x0 = np.clip(np.floor(px_grid).astype(np.int32), 0, grid_w - 1)
    y0 = np.clip(np.floor(py_grid).astype(np.int32), 0, grid_h - 1)
    x1 = np.clip(x0 + 1, 0, grid_w - 1)
    y1 = np.clip(y0 + 1, 0, grid_h - 1)
    fx = np.clip(px_grid - np.floor(px_grid), 0.0, 1.0)
    fy = np.clip(py_grid - np.floor(py_grid), 0.0, 1.0)
    m = mask.astype(np.float32)
    return (
        m[y0, x0] * (1.0 - fx) * (1.0 - fy)
        + m[y0, x1] * fx * (1.0 - fy)
        + m[y1, x0] * (1.0 - fx) * fy
        + m[y1, x1] * fx * fy
    )


def tile_texture(source: Image.Image, size: tuple[int, int]) -> np.ndarray:
    src = np.asarray(source.convert("RGB"), dtype=np.uint8)
    height, width = size
    reps_y = height // src.shape[0] + 2
    reps_x = width // src.shape[1] + 2
    return np.tile(src, (reps_y, reps_x, 1))[:height, :width]


def rgba_solid(color: tuple[int, int, int], alpha: np.ndarray) -> Image.Image:
    height, width = alpha.shape
    out = np.zeros((height, width, 4), dtype=np.uint8)
    out[:, :, 0] = color[0]
    out[:, :, 1] = color[1]
    out[:, :, 2] = color[2]
    out[:, :, 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def low_frequency_noise(shape: tuple[int, int], seed: int = 20260709) -> np.ndarray:
    height, width = shape
    rng = np.random.default_rng(seed)
    small = rng.random((max(4, height // 192), max(4, width // 192))).astype(np.float32)
    im = Image.fromarray((small * 255).astype(np.uint8), "L")
    im = im.resize((width, height), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(10.0))
    return np.asarray(im, dtype=np.float32) / 255.0


def shore_distance(field: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    water = field >= 0.5
    return water, distance_transform_edt(water).astype(np.float32)


def save_water_surface(source: Image.Image, field: np.ndarray, out_path: Path) -> None:
    height, width = field.shape
    rgb = tile_texture(source, (height, width)).astype(np.float32)

    water, dist = shore_distance(field)
    edge = np.clip(1.0 - dist / 30.0, 0.0, 1.0) * water
    edge = np.power(edge, 1.15)

    # Simple production rule: brighten only the first ~30 px inside the water.
    # Do not paint a separate coloured band; just lift the existing water texture.
    rgb *= (1.0 + (edge * 0.27)[:, :, None])
    rgb += (edge * 15.0)[:, :, None]
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    # Only a very narrow anti-aliased alpha edge. A wide alpha feather over the debug
    # green background created the visible dark contour; in Unity the land layers will
    # cover this edge anyway.
    alpha = smoothstep(0.48, 0.52, field) * 255.0
    out = np.dstack([rgb, np.clip(alpha, 0, 255).astype(np.uint8)])
    Image.fromarray(out, "RGBA").save(out_path)


def save_shore_layers(field: np.ndarray, shadow_path: Path, shallow_path: Path) -> None:
    # Kept as transparent placeholder layers for the Unity builder. The visible
    # shallow transition is baked into stage1_water_surface.png; separate overlay
    # bands created obvious contour lines on narrow rivers.
    empty = np.zeros_like(field, dtype=np.float32)
    rgba_solid((0, 0, 0), empty).save(shadow_path)
    rgba_solid((0, 0, 0), empty).save(shallow_path)


def save_debug(surface_path: Path, shadow_path: Path, shallow_path: Path, out_path: Path) -> None:
    surface = Image.open(surface_path).convert("RGBA")
    debug = Image.new("RGBA", surface.size, (32, 82, 70, 255))
    debug.alpha_composite(surface)
    debug.alpha_composite(Image.open(shadow_path).convert("RGBA"))
    debug.alpha_composite(Image.open(shallow_path).convert("RGBA"))
    debug.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bake stage1 water surface and shore layers.")
    parser.add_argument("--map", default="Assets/Art/Maps/stage1_map.json")
    parser.add_argument("--source", default="art_undecided/tiles/water/gpt15_water0_512_b90_s92.png")
    parser.add_argument("--out-dir", default="Assets/Art/Maps")
    parser.add_argument("--prefix", default="stage1")
    args = parser.parse_args()

    map_path = Path(args.map)
    source_path = Path(args.source)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(map_path)
    water_mask = np.array([[1.0 if char in WATER_LETTERS else 0.0 for char in row] for row in rows], dtype=np.float32)
    field = dual_field(water_mask, CELL)
    source = Image.open(source_path).convert("RGB")
    if source.width != source.height:
        side = min(source.size)
        source = source.crop((0, 0, side, side))

    surface = out_dir / f"{args.prefix}_water_surface.png"
    shadow = out_dir / f"{args.prefix}_shore_shadow.png"
    shallow = out_dir / f"{args.prefix}_shore_shallow.png"
    debug = out_dir / f"{args.prefix}_water_debug.png"

    save_water_surface(source, field, surface)
    save_shore_layers(field, shadow, shallow)
    save_debug(surface, shadow, shallow, debug)

    print(f"[water] map={len(rows[0])}x{len(rows)} cells -> {field.shape[1]}x{field.shape[0]} px")
    print(f"[water] source={source_path} period={source.width} px")
    print(f"[water] wrote {surface}")
    print(f"[water] wrote {shadow}")
    print(f"[water] wrote {shallow}")
    print(f"[water] wrote {debug}")


if __name__ == "__main__":
    main()