"""Generate a water mask + a river flow-map from the baked HD battle map.

The HD map (stage1_hd.png) has water/river painted in as flat blue pixels.
For the URP flow-map water shader we need two extra textures aligned 1:1 with it:

  * stage1_hd_watermask.png  - grayscale, water = white, everything else = black,
                               soft-feathered edge so the shader fades out cleanly.
  * stage1_hd_flowmap.png    - RG encodes a unit flow direction that runs ALONG the
                               river channel (so water flows down the bend, not just
                               left-to-right).  Neutral 0.5,0.5 outside the water.

Both are written next to the HD map in Assets/Art/Maps/ so the Unity builder can
pick them up.

Usage:
    .venv/Scripts/python.exe scripts/water/gen_water_mask_flowmap.py
    # optional: --hd <path> --preview
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def load_rgb(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    return np.asarray(img).astype(np.float32)


def detect_water(rgb: np.ndarray) -> np.ndarray:
    """Boolean water mask from blue-ness of the painted river."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # Water is a saturated blue/cyan: blue clearly dominant and reasonably bright.
    blue_dominant = (b > r + 22) & (b > g + 8) & (b > 95)
    # Keep some cyan-ish shallows too (green close to blue but both above red).
    cyan = (b > r + 15) & (g > r + 10) & (b > 110)
    mask = blue_dominant | cyan
    return mask


def clean_mask(mask: np.ndarray, min_area_frac: float = 0.0015) -> np.ndarray:
    """Drop tiny blue specks, fill interior holes, keep the big river blobs."""
    h, w = mask.shape
    min_area = int(min_area_frac * h * w)

    labelled, n = ndimage.label(mask)
    if n > 0:
        sizes = ndimage.sum(np.ones_like(labelled), labelled, index=range(1, n + 1))
        keep = {i + 1 for i, s in enumerate(sizes) if s >= min_area}
        mask = np.isin(labelled, list(keep)) if keep else np.zeros_like(mask)

    mask = ndimage.binary_fill_holes(mask)
    # Small closing to smooth the shore line.
    mask = ndimage.binary_closing(mask, structure=np.ones((3, 3)), iterations=2)
    mask = ndimage.binary_opening(mask, structure=np.ones((3, 3)), iterations=1)
    return mask


def feather(mask_bool: np.ndarray, radius: float = 6.0) -> np.ndarray:
    """Soft 0..1 mask: blur, then erode a touch so the feather sits inside the water."""
    inside = ndimage.binary_erosion(
        mask_bool, structure=np.ones((3, 3)), iterations=max(1, int(radius // 2))
    )
    soft = ndimage.gaussian_filter(inside.astype(np.float32), sigma=radius)
    soft = np.clip(soft, 0.0, 1.0)
    return soft


def compute_flowmap(mask_soft: np.ndarray, mask_bool: np.ndarray) -> np.ndarray:
    """Structure-tensor flow field: direction runs ALONG the river channel.

    Across a thin channel the image gradient is strongest perpendicular to the
    channel, so the *minor* eigenvector of the structure tensor points along it.
    We orient the field so it generally flows downward (positive Y in image space).
    """
    m = ndimage.gaussian_filter(mask_soft.astype(np.float32), sigma=3.0)
    gy, gx = np.gradient(m)  # gy = d/drow (down), gx = d/dcol (right)

    sigma = 12.0
    jxx = ndimage.gaussian_filter(gx * gx, sigma)
    jyy = ndimage.gaussian_filter(gy * gy, sigma)
    jxy = ndimage.gaussian_filter(gx * gy, sigma)

    # Orientation of the dominant gradient (edge normal / across-channel).
    theta = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    # Flow = tangent = normal rotated 90 degrees.
    flow_x = -np.sin(theta)
    flow_y = np.cos(theta)

    # Consistent sign: make the river flow downward where possible.
    flip = flow_y < 0
    flow_x = np.where(flip, -flow_x, flow_x)
    flow_y = np.where(flip, -flow_y, flow_y)

    # Smooth the field inside the water and renormalise.
    wx = ndimage.gaussian_filter(flow_x * mask_soft, sigma=8.0)
    wy = ndimage.gaussian_filter(flow_y * mask_soft, sigma=8.0)
    mag = np.sqrt(wx * wx + wy * wy) + 1e-6
    fx = wx / mag
    fy = wy / mag

    # Neutral (still) outside the water.
    fx = np.where(mask_bool, fx, 0.0)
    fy = np.where(mask_bool, fy, 0.0)

    # Encode to 0..1 (RG). Note image Y is down; the shader treats G as +down.
    r = np.clip(0.5 + 0.5 * fx, 0.0, 1.0)
    g = np.clip(0.5 + 0.5 * fy, 0.0, 1.0)
    b = np.zeros_like(r)
    return np.stack([r, g, b], axis=-1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hd", default="Assets/Art/Maps/stage1_hd.png")
    ap.add_argument("--preview", action="store_true",
                    help="also write a debug overlay next to the outputs")
    args = ap.parse_args()

    hd_path = Path(args.hd)
    rgb = load_rgb(hd_path)

    mask_bool = clean_mask(detect_water(rgb))
    mask_soft = feather(mask_bool, radius=6.0)

    mask_img = (mask_soft * 255.0).astype(np.uint8)
    mask_out = hd_path.with_name("stage1_hd_watermask.png")
    Image.fromarray(mask_img, mode="L").save(mask_out)
    print(f"water mask  -> {mask_out}  (water px: {int(mask_bool.sum())})")

    flow = compute_flowmap(mask_soft, mask_bool)
    flow_img = (flow * 255.0).astype(np.uint8)
    flow_out = hd_path.with_name("stage1_hd_flowmap.png")
    Image.fromarray(flow_img, mode="RGB").save(flow_out)
    print(f"flow map    -> {flow_out}")

    if args.preview:
        base = rgb.copy()
        # tint water red, draw flow arrows sparsely
        overlay = base.copy()
        overlay[mask_bool] = overlay[mask_bool] * 0.4 + np.array([255, 40, 40]) * 0.6
        prev = Image.fromarray(overlay.astype(np.uint8), mode="RGB")
        prev_out = hd_path.with_name("stage1_hd_watermask_preview.png")
        prev.save(prev_out)
        print(f"preview     -> {prev_out}")


if __name__ == "__main__":
    main()
