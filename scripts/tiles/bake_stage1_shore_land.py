#!/usr/bin/env python3
"""Bake a map-sized shoreline decal layer from an AI shoreline brush sheet.

This script keeps the map structure deterministic: stage1_map.json decides where
shoreline exists; the AI sheet only supplies brush texture.

Outputs by default:
  art_undecided/tiles/shoreline/cut/decal_00.png ... decal_05.png
  art_undecided/tiles/shoreline/cut/decal_contact.png
  Assets/Art/Maps/stage1_shore_land.png
  Assets/Art/Maps/stage1_shore_preview.png
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import binary_dilation, distance_transform_edt, label


CELL = 64
WATER = {"W", "D"}


def load_rows(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("base")
    if not rows:
        raise SystemExit(f"ERROR: no base rows in {path}")
    return rows


def median_edge_color(rgb: np.ndarray) -> np.ndarray:
    edge = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]], axis=0)
    return np.median(edge.reshape(-1, 3), axis=0).astype(np.float32)


def alpha_from_gray_background(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    bg = median_edge_color(rgb)
    dist = np.sqrt(np.sum((rgb.astype(np.float32) - bg) ** 2, axis=2))
    hard = dist > 20.0

    # Keep only non-background components that are large enough to be decal content.
    lab, count = label(hard)
    keep = np.zeros_like(hard)
    for i in range(1, count + 1):
        comp = lab == i
        if comp.sum() >= 220:
            keep |= comp
    keep = binary_dilation(keep, iterations=2)

    alpha = np.clip((dist - 14.0) / (50.0 - 14.0), 0.0, 1.0)
    alpha *= keep.astype(np.float32)
    alpha = Image.fromarray((alpha * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.9))
    alpha_arr = np.asarray(alpha, dtype=np.float32) / 255.0

    # Basic unmatte against the estimated gray background to remove background fringe.
    out = rgb.astype(np.float32).copy()
    safe = np.maximum(alpha_arr[:, :, None], 0.08)
    out = (out - (1.0 - alpha_arr[:, :, None]) * bg[None, None, :]) / safe
    out = np.clip(out, 0, 255).astype(np.uint8)
    return out, (alpha_arr * 255).astype(np.uint8)


def mean_rgb(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGBA")
    arr = np.asarray(im, dtype=np.float32)
    mask = arr[:, :, 3] > 20
    if not mask.any():
        mask = np.ones(arr.shape[:2], dtype=bool)
    return arr[:, :, :3][mask].mean(axis=0)


def normalize_decal_colors(rgba: Image.Image, grass: np.ndarray, road: np.ndarray, water: np.ndarray) -> Image.Image:
    arr = np.asarray(rgba.convert("RGBA"), dtype=np.float32).copy()
    rgb = arr[:, :, :3]
    a = arr[:, :, 3] > 8
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]

    green = a & (g > r * 0.86) & (g > b * 0.88)
    blue = a & (b > r + 12) & (b > g * 0.88)
    earth = a & ~(green | blue)

    for mask, target, strength in ((green, grass, 0.42), (blue, water, 0.36), (earth, road, 0.34)):
        if mask.any():
            rgb[mask] = rgb[mask] * (1.0 - strength) + target[None, :] * strength

    # Global compression so it reads as terrain, not a sticker.
    luma = rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114
    rgb[:] = luma[:, :, None] + (rgb - luma[:, :, None]) * 0.76
    rgb[:] = rgb * 0.90
    arr[:, :, :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def crop_to_alpha(rgba: Image.Image, pad: int = 10) -> Image.Image | None:
    arr = np.asarray(rgba)
    ys, xs = np.where(arr[:, :, 3] > 8)
    if len(xs) == 0:
        return None
    x0, x1 = max(0, xs.min() - pad), min(rgba.width, xs.max() + pad + 1)
    y0, y1 = max(0, ys.min() - pad), min(rgba.height, ys.max() + pad + 1)
    return rgba.crop((x0, y0, x1, y1))


def cut_decals(sheet_path: Path, out_dir: Path) -> list[Image.Image]:
    sheet = Image.open(sheet_path).convert("RGB")
    rgb = np.asarray(sheet, dtype=np.uint8)
    cell_w, cell_h = sheet.width // 3, sheet.height // 2
    out_dir.mkdir(parents=True, exist_ok=True)

    grass = mean_rgb(Path("Assets/Art/Tiles/grass_v1/G0.png"))
    road = mean_rgb(Path("Assets/Art/Tiles/road_v1/R0.png"))
    water = mean_rgb(Path("art_undecided/tiles/water/gpt15_water0_512_b90_s92.png"))

    decals: list[Image.Image] = []
    for row in range(2):
        for col in range(3):
            idx = row * 3 + col
            tile = rgb[row * cell_h : (row + 1) * cell_h, col * cell_w : (col + 1) * cell_w]
            clean_rgb, alpha = alpha_from_gray_background(tile)
            rgba = Image.fromarray(np.dstack([clean_rgb, alpha]).astype(np.uint8), "RGBA")
            rgba = normalize_decal_colors(rgba, grass, road, water)
            cropped = crop_to_alpha(rgba)
            if cropped is None:
                continue
            cropped.save(out_dir / f"decal_{idx:02d}.png")
            decals.append(cropped)

    make_contact(decals, out_dir / "decal_contact.png")
    return decals


def make_contact(decals: list[Image.Image], out_path: Path) -> None:
    thumb_w, thumb_h = 220, 96
    pad = 14
    sheet = Image.new("RGBA", (3 * thumb_w + 4 * pad, 2 * thumb_h + 3 * pad), (40, 43, 48, 255))
    for idx, decal in enumerate(decals):
        preview = Image.new("RGBA", (thumb_w, thumb_h), (92, 145, 68, 255))
        water = Image.new("RGBA", (thumb_w, thumb_h // 2), (34, 110, 172, 255))
        preview.alpha_composite(water, (0, thumb_h // 2))
        d = decal.copy()
        d.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = pad + (idx % 3) * (thumb_w + pad)
        y = pad + (idx // 3) * (thumb_h + pad)
        preview.alpha_composite(d, ((thumb_w - d.width) // 2, (thumb_h - d.height) // 2))
        sheet.alpha_composite(preview, (x, y))
    sheet.convert("RGB").save(out_path)


def is_water(rows: list[str], x: int, y: int) -> bool:
    return rows[y][x] in WATER


def dual_field(mask: np.ndarray, cell: int) -> np.ndarray:
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


def resize_for_boundary(decal: Image.Image, horizontal: bool, rng: random.Random) -> Image.Image:
    target_w = rng.randint(94, 132)
    scale = target_w / decal.width
    target_h = max(22, int(decal.height * scale))
    out = decal.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if not horizontal:
        # Rotation happens after resize so depth remains narrow.
        return out
    return out


def paste_center(canvas: Image.Image, decal: Image.Image, cx: float, cy: float) -> None:
    x = int(round(cx - decal.width * 0.5))
    y = int(round(cy - decal.height * 0.5))
    canvas.alpha_composite(decal, (x, y))


def smoothstep(edge0: float, edge1: float, value: np.ndarray) -> np.ndarray:
    t = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def decal_texture_noise(decals: list[Image.Image], shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    tex = Image.new("L", (384, 384), 128)
    rng = random.Random(20260709)
    for _ in range(18):
        d = rng.choice(decals).convert("RGBA")
        d.thumbnail((rng.randint(140, 240), rng.randint(60, 110)), Image.Resampling.LANCZOS)
        arr = np.asarray(d, dtype=np.float32)
        if arr[:, :, 3].max() <= 0:
            continue
        luma = (arr[:, :, 0] * 0.299 + arr[:, :, 1] * 0.587 + arr[:, :, 2] * 0.114)
        luma = np.clip((luma - luma.mean()) * 1.5 + 128, 0, 255).astype(np.uint8)
        patch = Image.fromarray(luma, "L")
        alpha = Image.fromarray(arr[:, :, 3].astype(np.uint8), "L")
        if rng.random() < 0.5:
            patch = patch.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            alpha = alpha.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        tex.paste(patch, (rng.randint(-40, 300), rng.randint(-20, 330)), alpha)
    tex = tex.filter(ImageFilter.GaussianBlur(1.2))
    reps_y = height // tex.height + 2
    reps_x = width // tex.width + 2
    tiled = Image.new("L", (reps_x * tex.width, reps_y * tex.height))
    for y in range(reps_y):
        for x in range(reps_x):
            tiled.paste(tex, (x * tex.width, y * tex.height))
    return np.asarray(tiled.crop((0, 0, width, height)), dtype=np.float32) / 255.0


def bake_shore(rows: list[str], decals: list[Image.Image], out_path: Path) -> None:
    h, w = len(rows), len(rows[0])
    water_mask = np.array([[is_water(rows, x, y) for x in range(w)] for y in range(h)], dtype=np.float32)
    field = dual_field(water_mask, CELL)
    pix_water = field >= 0.5
    pix_land = ~pix_water
    height, width = pix_water.shape

    dist_land_to_water = distance_transform_edt(pix_land).astype(np.float32)
    dist_water_to_land = distance_transform_edt(pix_water).astype(np.float32)
    land_band = pix_land & (dist_land_to_water <= 30)
    wet_band = pix_land & (dist_land_to_water <= 8)
    water_edge = pix_water & (dist_water_to_land <= 6)

    ai_noise = decal_texture_noise(decals, (height, width))
    rng = np.random.default_rng(20260709)
    coarse = rng.random((max(4, height // 192), max(4, width // 192)))
    coarse_img = Image.fromarray((coarse * 255).astype(np.uint8), "L").resize((width, height), Image.Resampling.BICUBIC)
    coarse_noise = np.asarray(coarse_img.filter(ImageFilter.GaussianBlur(10.0)), dtype=np.float32) / 255.0
    texture = np.clip(0.55 * ai_noise + 0.45 * coarse_noise, 0, 1)

    grass = mean_rgb(Path("Assets/Art/Tiles/grass_v1/G0.png"))
    road = mean_rgb(Path("Assets/Art/Tiles/road_v1/R0.png"))
    dirt = mean_rgb(Path("Assets/Art/Tiles/dirt.png"))
    water = mean_rgb(Path("art_undecided/tiles/water/gpt15_water0_512_b90_s92.png"))
    tan = road * 0.34 + np.array([190.0, 167.0, 101.0]) * 0.66
    wet = dirt * 0.44 + np.array([112.0, 112.0, 72.0]) * 0.38 + water * 0.18

    alpha_land = smoothstep(30.0, 0.0, dist_land_to_water) * land_band
    alpha_wet = smoothstep(8.0, 0.0, dist_land_to_water) * wet_band
    alpha_water = smoothstep(6.0, 0.0, dist_water_to_land) * water_edge
    alpha_land *= 0.38 + 0.24 * texture
    alpha_wet *= 0.20 + 0.12 * texture
    alpha_water *= 0.08

    rgb = np.zeros((height, width, 3), dtype=np.float32)
    alpha = np.zeros((height, width), dtype=np.float32)

    land_color = (grass[None, None, :] * 0.58 + tan[None, None, :] * 0.42) * (0.99 + 0.07 * texture[:, :, None])
    wet_color = wet[None, None, :] * (1.02 + 0.05 * texture[:, :, None])
    water_color = water[None, None, :] * 1.04 + np.array([6.0, 12.0, 10.0])[None, None, :]

    def over(color: np.ndarray, a: np.ndarray) -> None:
        nonlocal rgb, alpha
        a = np.clip(a, 0, 1)
        rgb = rgb * (1.0 - a[:, :, None]) + color * a[:, :, None]
        alpha = alpha + a * (1.0 - alpha)

    over(land_color, alpha_land * 0.42)
    over(wet_color, alpha_wet * 0.18)
    over(water_color, alpha_water * 0.16)

    # Small darker flecks on the land side; generated into alpha only near shore.
    speck = (texture > 0.70) & land_band & (dist_land_to_water > 8) & (dist_land_to_water < 26)
    speck = binary_dilation(speck, iterations=1)
    over(np.full((height, width, 3), wet * 0.92, dtype=np.float32), speck.astype(np.float32) * 0.08)

    # PNG/Unity expects straight alpha. The compositing above accumulates colour over
    # transparent black, so divide by alpha before writing; otherwise transparent edges
    # keep near-black RGB and composite as dirty shadow/fringe in Unity/viewers.
    straight_rgb = np.zeros_like(rgb)
    visible = alpha > 0.001
    straight_rgb[visible] = rgb[visible] / alpha[visible, None]
    out = np.dstack([np.clip(straight_rgb, 0, 255), np.clip(alpha * 255, 0, 255)]).astype(np.uint8)
    Image.fromarray(out, "RGBA").filter(ImageFilter.GaussianBlur(0.35)).save(out_path)


def make_preview(rows: list[str], shore_path: Path, out_path: Path) -> None:
    h, w = len(rows), len(rows[0])
    bg = Image.new("RGBA", (w * CELL, h * CELL), (126, 174, 76, 255))
    water_path = Path("Assets/Art/Maps/stage1_water_surface.png")
    if water_path.exists():
        bg.alpha_composite(Image.open(water_path).convert("RGBA"))
    bg.alpha_composite(Image.open(shore_path).convert("RGBA"))
    draw = ImageDraw.Draw(bg)
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c == "R":
                draw.rectangle([x * CELL, y * CELL, (x + 1) * CELL, (y + 1) * CELL], fill=(168, 127, 74, 255))
            elif c == "I":
                draw.rectangle([x * CELL, y * CELL, (x + 1) * CELL, (y + 1) * CELL], fill=(141, 109, 70, 255))
    bg.resize((w * CELL // 2, h * CELL // 2), Image.Resampling.LANCZOS).save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cut AI shoreline decals and bake stage1 shore layer.")
    parser.add_argument("--map", default="Assets/Art/Maps/stage1_map.json")
    parser.add_argument("--sheet", default="art_undecided/tiles/shoreline/gpt15_medium_shoreline_opaque_gray.png")
    parser.add_argument("--cut-dir", default="art_undecided/tiles/shoreline/cut")
    parser.add_argument("--out", default="Assets/Art/Maps/stage1_shore_land.png")
    parser.add_argument("--preview", default="Assets/Art/Maps/stage1_shore_preview.png")
    args = parser.parse_args()

    rows = load_rows(Path(args.map))
    decals = cut_decals(Path(args.sheet), Path(args.cut_dir))
    if not decals:
        raise SystemExit("ERROR: no decals were cut from the sheet.")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bake_shore(rows, decals, out_path)
    make_preview(rows, out_path, Path(args.preview))
    print(f"[shore] cut {len(decals)} decals -> {args.cut_dir}")
    print(f"[shore] wrote {out_path}")
    print(f"[shore] wrote {args.preview}")


if __name__ == "__main__":
    main()