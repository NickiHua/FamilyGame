from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


try:
    from scipy import ndimage as ndi
except Exception:  # pragma: no cover - fallback for machines without scipy
    ndi = None


RGB_WEIGHTS = np.array([0.85, 1.0, 0.75], dtype=np.float32)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert an AI object PNG toward the project's restrained pixel-object style."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--palette-ref", type=Path, required=True)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--mask-mode", choices=("alpha", "object"), default="object")
    parser.add_argument("--alpha-min", type=int, default=32)
    parser.add_argument("--alpha-hard", type=int, default=128)
    parser.add_argument("--mask-sat", type=float, default=0.16)
    parser.add_argument("--mask-dark", type=float, default=0.45)
    parser.add_argument("--mask-expand", type=int, default=3)
    parser.add_argument("--keep-components", type=int, default=10)
    parser.add_argument("--max-colors", type=int, default=64)
    parser.add_argument("--input-colors", type=int, default=8)
    parser.add_argument("--contrast", type=float, default=0.70)
    parser.add_argument("--saturation", type=float, default=0.72)
    parser.add_argument("--brightness", type=float, default=0.96)
    parser.add_argument("--mode-filter", type=int, default=3)
    parser.add_argument("--pixel-block", type=int, default=1)
    parser.add_argument("--no-crop", action="store_true")
    return parser.parse_args()


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def alpha_bbox(alpha: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)


def hsv_stats(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rgb_f = rgb.astype(np.float32) / 255.0
    maxc = rgb_f.max(axis=2)
    minc = rgb_f.min(axis=2)
    sat = np.zeros_like(maxc)
    nonzero = maxc > 1e-6
    sat[nonzero] = (maxc[nonzero] - minc[nonzero]) / maxc[nonzero]
    value = maxc
    return sat, value


def keep_largest_components(mask: np.ndarray, keep: int) -> np.ndarray:
    if keep <= 0 or not mask.any():
        return mask
    if ndi is None:
        return mask

    labels, count = ndi.label(mask)
    if count <= keep:
        return mask

    areas = np.bincount(labels.ravel())
    areas[0] = 0
    keep_labels = np.argsort(areas)[-keep:]
    return np.isin(labels, keep_labels)


def make_subject_mask(rgb: np.ndarray, alpha: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    alpha_mask = alpha >= args.alpha_min
    if args.mask_mode == "alpha":
        return alpha_mask

    sat, value = hsv_stats(rgb)
    seed = alpha_mask & ((sat >= args.mask_sat) | (value <= args.mask_dark))
    seed = keep_largest_components(seed, args.keep_components)

    if ndi is not None and args.mask_expand > 0:
        seed = ndi.binary_dilation(seed, iterations=args.mask_expand)
        seed &= alpha_mask
        seed = ndi.binary_fill_holes(seed)
        seed = keep_largest_components(seed, args.keep_components)
    return seed


def crop_to_mask(image: Image.Image, mask: np.ndarray) -> tuple[Image.Image, np.ndarray]:
    bbox = alpha_bbox((mask.astype(np.uint8)) * 255)
    if bbox is None:
        return image, mask
    x0, y0, x1, y1 = bbox
    return image.crop(bbox), mask[y0:y1, x0:x1]


def adjust_color(image: Image.Image, mask: np.ndarray, args: argparse.Namespace) -> Image.Image:
    rgb = image.convert("RGB")
    rgb = ImageEnhance.Contrast(rgb).enhance(args.contrast)
    rgb = ImageEnhance.Color(rgb).enhance(args.saturation)
    rgb = ImageEnhance.Brightness(rgb).enhance(args.brightness)

    out = Image.new("RGBA", image.size, (0, 0, 0, 0))
    alpha = (mask.astype(np.uint8)) * 255
    out_rgb = np.asarray(rgb, dtype=np.uint8)
    out_arr = np.zeros((image.height, image.width, 4), dtype=np.uint8)
    out_arr[:, :, :3] = out_rgb
    out_arr[:, :, 3] = alpha
    out = Image.fromarray(out_arr, "RGBA")
    return out


def quantize_palette(image: Image.Image, mask: np.ndarray, colors: int) -> list[tuple[int, int, int]]:
    if colors <= 0 or not mask.any():
        return []
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    pixels = rgb[mask]
    if len(pixels) == 0:
        return []
    side = max(1, int(np.ceil(np.sqrt(len(pixels)))))
    sample = np.zeros((side * side, 3), dtype=np.uint8)
    if len(pixels) > len(sample):
        indices = np.linspace(0, len(pixels) - 1, len(sample)).astype(np.int64)
        sample[:] = pixels[indices]
    else:
        sample[: len(pixels)] = pixels
        sample[len(pixels) :] = pixels[-1]
    sample_img = Image.fromarray(sample.reshape(side, side, 3), "RGB")
    q = sample_img.quantize(colors=min(colors, 256), method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = q.getpalette()[: colors * 3]
    used = sorted(set(q.getdata()))
    out: list[tuple[int, int, int]] = []
    for idx in used:
        base = idx * 3
        if base + 2 < len(pal):
            out.append((pal[base], pal[base + 1], pal[base + 2]))
    return out


def reference_palette(path: Path, max_colors: int) -> list[tuple[int, int, int]]:
    ref = rgba(path)
    arr = np.asarray(ref, dtype=np.uint8)
    mask = arr[:, :, 3] >= 250
    colors = Counter(map(tuple, arr[:, :, :3][mask].tolist()))
    palette = [tuple(map(int, color)) for color, _ in colors.most_common(max_colors)]
    return palette


def combine_palette(
    ref_palette: list[tuple[int, int, int]], input_palette: list[tuple[int, int, int]], max_colors: int
) -> np.ndarray:
    combined: list[tuple[int, int, int]] = []
    seen: set[tuple[int, int, int]] = set()
    for color in ref_palette + input_palette:
        if color not in seen:
            seen.add(color)
            combined.append(color)
    if len(combined) > max_colors:
        combined = combined[:max_colors]
    return np.array(combined, dtype=np.float32)


def nearest_palette(rgb: np.ndarray, mask: np.ndarray, palette: np.ndarray) -> np.ndarray:
    out = rgb.copy()
    pixels = rgb[mask].astype(np.float32)
    if len(pixels) == 0 or len(palette) == 0:
        return out
    mapped = np.empty_like(pixels, dtype=np.uint8)
    chunk = 50_000
    weighted_palette = palette * RGB_WEIGHTS
    for start in range(0, len(pixels), chunk):
        part = pixels[start : start + chunk]
        diff = part[:, None, :] * RGB_WEIGHTS - weighted_palette[None, :, :]
        dist = np.sum(diff * diff, axis=2)
        mapped[start : start + chunk] = palette[np.argmin(dist, axis=1)].astype(np.uint8)
    out[mask] = mapped
    return out


def mode_filter_rgb(rgb: np.ndarray, mask: np.ndarray, size: int) -> np.ndarray:
    if size <= 1:
        return rgb
    if size % 2 == 0:
        size += 1
    filtered = Image.fromarray(rgb, "RGB").filter(ImageFilter.ModeFilter(size=size))
    filtered_arr = np.asarray(filtered, dtype=np.uint8)
    out = rgb.copy()
    out[mask] = filtered_arr[mask]
    return out


def pixel_block(image: Image.Image, block: int) -> Image.Image:
    if block <= 1:
        return image
    w, h = image.size
    small = image.resize((max(1, w // block), max(1, h // block)), Image.Resampling.BOX)
    return small.resize((w, h), Image.Resampling.NEAREST)


def process(input_path: Path, output_path: Path, args: argparse.Namespace) -> Image.Image:
    src = rgba(input_path)
    src_arr = np.asarray(src, dtype=np.uint8)
    mask = make_subject_mask(src_arr[:, :, :3], src_arr[:, :, 3], args)
    if not args.no_crop:
        src, mask = crop_to_mask(src, mask)

    adjusted = adjust_color(src, mask, args)
    adjusted = pixel_block(adjusted, args.pixel_block)
    adj_arr = np.asarray(adjusted, dtype=np.uint8)
    mask = adj_arr[:, :, 3] >= args.alpha_hard
    filtered_rgb = mode_filter_rgb(adj_arr[:, :, :3], mask, args.mode_filter)

    filtered_arr = adj_arr.copy()
    filtered_arr[:, :, :3] = filtered_rgb
    adjusted_for_palette = Image.fromarray(filtered_arr, "RGBA")

    ref_pal = reference_palette(args.palette_ref, args.max_colors)
    input_pal = quantize_palette(adjusted_for_palette, mask, args.input_colors)
    palette = combine_palette(ref_pal, input_pal, args.max_colors)

    rgb = nearest_palette(filtered_rgb, mask, palette)

    out = np.zeros((adjusted.height, adjusted.width, 4), dtype=np.uint8)
    rgb_clean = np.zeros_like(rgb)
    rgb_clean[mask] = rgb[mask]
    out[:, :, :3] = rgb_clean
    out[:, :, 3] = (mask.astype(np.uint8)) * 255
    out_img = Image.fromarray(out, "RGBA")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_img.save(output_path)
    return out_img


def checker(size: tuple[int, int], cell: int = 16) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, (164, 188, 132))
    draw = ImageDraw.Draw(img)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if (x // cell + y // cell) % 2 == 0:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(132, 158, 96))
    return img


def fit(image: Image.Image, max_w: int, max_h: int) -> Image.Image:
    scale = min(max_w / image.width, max_h / image.height, 1.0)
    size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
    return image.resize(size, Image.Resampling.NEAREST)


def make_preview(input_path: Path, output: Image.Image, ref_path: Path, preview_path: Path) -> None:
    src = rgba(input_path)
    ref = rgba(ref_path)
    panels: list[tuple[str, Image.Image]] = [("original", src), ("processed", output), ("house ref", ref)]
    panel_w, panel_h = 420, 260
    margin = 18
    label_h = 24
    sheet = Image.new("RGB", (panel_w * len(panels) + margin * (len(panels) + 1), panel_h + label_h + margin * 2), (32, 34, 38))
    draw = ImageDraw.Draw(sheet)
    for i, (label, image) in enumerate(panels):
        x = margin + i * (panel_w + margin)
        y = margin + label_h
        bg = checker((panel_w, panel_h))
        fitted = fit(image, panel_w, panel_h)
        ox = x + (panel_w - fitted.width) // 2
        oy = y + (panel_h - fitted.height) // 2
        sheet.paste(bg, (x, y))
        bg.paste(fitted, ((panel_w - fitted.width) // 2, (panel_h - fitted.height) // 2), fitted)
        sheet.paste(bg, (x, y))
        draw.text((x, margin), label, fill=(235, 238, 228))
        draw.rectangle((x, y, x + panel_w - 1, y + panel_h - 1), outline=(64, 70, 76))
        draw.rectangle((ox, oy, ox + fitted.width - 1, oy + fitted.height - 1), outline=(232, 210, 128))
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(preview_path)


def main() -> None:
    args = parse_args()
    out = process(args.input, args.output, args)
    if args.preview:
        make_preview(args.input, out, args.palette_ref, args.preview)


if __name__ == "__main__":
    main()