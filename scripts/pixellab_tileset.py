#!/usr/bin/env python3
r"""Generate a PixelLab top-down Wang tileset and export its tiles.

This is for experiments with PixelLab's /v2/create-tileset endpoint. It reads the
API token from pixellabkey.txt / env / scripts/config.json, prints balance before
and after the run, saves the response metadata, exports each tile PNG, and creates
a contact sheet in our bit order (1=TL/NW, 2=TR/NE, 4=BL/SW, 8=BR/SE).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw


API_BASE = "https://api.pixellab.ai/v2/"
CORNER_BITS = {"NW": 1, "NE": 2, "SW": 4, "SE": 8}


def get_token(key_file: Path | None) -> str:
    if key_file and key_file.is_file():
        token = key_file.read_text(encoding="utf-8").strip()
        if token:
            return token
    env = os.environ.get("PIXELLAB_API_TOKEN", "").strip()
    if env:
        return env
    cfg = Path(__file__).resolve().parent / "config.json"
    if cfg.is_file():
        try:
            token = (json.loads(cfg.read_text(encoding="utf-8")) or {}).get("pixellab_api_token")
            if token:
                return token.strip()
        except (json.JSONDecodeError, OSError):
            pass
    sys.exit("ERROR: no PixelLab token found. Use pixellabkey.txt, PIXELLAB_API_TOKEN, or scripts/config.json.")


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def image_to_b64(path: Path) -> dict[str, str]:
    return {"type": "base64", "base64": base64.b64encode(path.read_bytes()).decode("ascii"), "format": "png"}


def get_balance(token: str) -> dict[str, Any]:
    response = requests.get(API_BASE + "balance", headers=headers(token), timeout=30)
    response.raise_for_status()
    return response.json()


def balance_line(label: str, balance: dict[str, Any]) -> None:
    sub = balance.get("subscription", {}) or {}
    credits = balance.get("credits", {}) or {}
    print(
        f"[{label}] plan={sub.get('plan')} status={sub.get('status')} "
        f"generations={sub.get('generations')}/{sub.get('total')} usd=${credits.get('usd')}"
    )


def generation_delta(before: dict[str, Any], after: dict[str, Any]) -> float | None:
    try:
        return float(before["subscription"]["generations"]) - float(after["subscription"]["generations"])
    except (KeyError, TypeError, ValueError):
        return None


def poll_job(token: str, job_id: str, timeout: int) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_status = None
    while time.time() < deadline:
        response = requests.get(API_BASE + f"background-jobs/{job_id}", headers=headers(token), timeout=30)
        response.raise_for_status()
        job = response.json()
        status = job.get("status")
        if status != last_status:
            print(f"[poll] status={status}")
            last_status = status
        if status == "completed":
            return job
        if status == "failed":
            raise RuntimeError(f"job failed: {json.dumps(job.get('last_response'), ensure_ascii=False)[:2000]}")
        time.sleep(5)
    raise TimeoutError("timed out waiting for PixelLab tileset job")


def tile_image_b64(tile: dict[str, Any]) -> str:
    image = tile.get("image") or {}
    if isinstance(image, dict) and image.get("base64"):
        return image["base64"]
    if tile.get("image_data"):
        data = tile["image_data"]
        if isinstance(data, str) and data.startswith("data:image"):
            return data.split(",", 1)[1]
        return data
    raise KeyError(f"tile has no image base64: {tile.keys()}")


def bit_for_tile(tile: dict[str, Any], upper_name: str) -> int:
    corners = tile.get("corners") or {}
    bits = 0
    for corner, bit in CORNER_BITS.items():
        value = str(corners.get(corner, "")).lower()
        if value == upper_name.lower():
            bits |= bit
    return bits


def save_tiles(data: dict[str, Any], out_dir: Path, upper_name: str) -> dict[int, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tiles = data["tileset"]["tiles"]
    by_bit: dict[int, Path] = {}
    for index, tile in enumerate(tiles):
        bits = bit_for_tile(tile, upper_name)
        name = str(tile.get("name") or f"tile_{index}").replace("/", "-").replace("+", "plus")
        out_path = out_dir / f"{bits:02d}_{name}.png"
        out_path.write_bytes(base64.b64decode(tile_image_b64(tile)))
        by_bit[bits] = out_path
        print(f"[tile] bit={bits:02d} corners={tile.get('corners')} -> {out_path.name}")
    return by_bit


def make_contact(by_bit: dict[int, Path], out_path: Path) -> None:
    order = [0, 1, 2, 4, 8, 3, 5, 10, 12, 6, 9, 7, 11, 13, 14, 15]
    images: list[Image.Image | None] = []
    tile_size = 32
    for bit in order:
        path = by_bit.get(bit)
        if path and path.is_file():
            image = Image.open(path).convert("RGBA")
            tile_size = max(tile_size, image.width, image.height)
            images.append(image)
        else:
            images.append(None)
    scale = 3
    cell = tile_size * scale
    label_h = 18
    margin = 10
    sheet = Image.new("RGB", (margin * 5 + cell * 4, margin * 5 + (cell + label_h) * 4), (34, 36, 40))
    draw = ImageDraw.Draw(sheet)
    for i, bit in enumerate(order):
        x = margin + (i % 4) * (cell + margin)
        y = margin + (i // 4) * (cell + label_h + margin)
        bg = Image.new("RGB", (cell, cell), (104, 126, 78))
        image = images[i]
        if image is not None:
            preview = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
            ox = (cell - preview.width) // 2
            oy = (cell - preview.height) // 2
            bg.paste(preview, (ox, oy), preview)
        sheet.paste(bg, (x, y + label_h))
        draw.text((x, y), f"bit {bit:02d}", fill=(235, 238, 228))
        draw.rectangle((x, y + label_h, x + cell - 1, y + label_h + cell - 1), outline=(86, 90, 98))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    print(f"[ok] contact -> {out_path}")


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Generate a PixelLab top-down Wang tileset.")
    parser.add_argument("--lower", required=True, help="Lower/base terrain description.")
    parser.add_argument("--upper", required=True, help="Upper/overlay terrain description.")
    parser.add_argument("--transition", default="", help="Transition description.")
    parser.add_argument("--lower-ref", type=Path)
    parser.add_argument("--upper-ref", type=Path)
    parser.add_argument("--transition-ref", type=Path)
    parser.add_argument("--color-ref", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tile-size", type=int, default=32, choices=(16, 32, 64))
    parser.add_argument("--mode", choices=("standard", "pro"), default="standard")
    parser.add_argument("--transition-size", type=float, default=0.25, choices=(0.0, 0.25, 0.5, 1.0))
    parser.add_argument("--view", choices=("high top-down", "low top-down"), default="high top-down")
    parser.add_argument("--spread-x", type=float, help="Pro only. Boundary spread, 0=steep, 1=gradual.")
    parser.add_argument("--slope-size", type=float, help="Pro only. Slope height fraction on N/W/E sides.")
    parser.add_argument("--raggedness", type=float, help="Pro only. Terrain boundary noise, 0=smooth, 1=rough.")
    parser.add_argument("--tile-strength", type=float, help="Strength of tile pattern adherence.")
    parser.add_argument("--tileset-adherence", type=float, help="How strongly to follow reference/texture and tileset structure.")
    parser.add_argument("--tileset-adherence-freedom", type=float, help="How flexible to be while following tileset structure.")
    parser.add_argument("--outline", default="lineless")
    parser.add_argument("--shading", default="flat shading")
    parser.add_argument("--detail", default="low detail")
    parser.add_argument("--guidance", type=float, default=8.0)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--key-file", type=Path, default=repo_root / "pixellabkey.txt")
    parser.add_argument("--timeout", type=int, default=240)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token = get_token(args.key_file)

    before = get_balance(token)
    balance_line("before", before)

    payload: dict[str, Any] = {
        "lower_description": args.lower,
        "upper_description": args.upper,
        "transition_description": args.transition,
        "tile_size": {"width": args.tile_size, "height": args.tile_size},
        "mode": args.mode,
        "transition_size": args.transition_size,
        "view": args.view,
        "outline": args.outline,
        "shading": args.shading,
        "detail": args.detail,
        "text_guidance_scale": args.guidance,
    }
    if args.spread_x is not None:
        payload["spread_x"] = args.spread_x
    if args.slope_size is not None:
        payload["slope_size"] = args.slope_size
    if args.raggedness is not None:
        payload["raggedness"] = args.raggedness
    if args.tile_strength is not None:
        payload["tile_strength"] = args.tile_strength
    if args.tileset_adherence is not None:
        payload["tileset_adherence"] = args.tileset_adherence
    if args.tileset_adherence_freedom is not None:
        payload["tileset_adherence_freedom"] = args.tileset_adherence_freedom
    if args.seed is not None:
        payload["seed"] = args.seed
    if args.lower_ref:
        payload["lower_reference_image"] = image_to_b64(args.lower_ref)
    if args.upper_ref:
        payload["upper_reference_image"] = image_to_b64(args.upper_ref)
    if args.transition_ref:
        payload["transition_reference_image"] = image_to_b64(args.transition_ref)
    if args.color_ref:
        payload["color_image"] = image_to_b64(args.color_ref)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "request.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[gen] POST /create-tileset out={args.out}")
    response = requests.post(API_BASE + "create-tileset", headers=headers(token), json=payload, timeout=60)
    if response.status_code not in (200, 202):
        sys.exit(f"ERROR: create-tileset failed {response.status_code}: {response.text}")
    submission = response.json()
    (args.out / "submission.json").write_text(json.dumps(submission, ensure_ascii=False, indent=2), encoding="utf-8")
    job_id = submission.get("background_job_id")
    tileset_id = submission.get("tileset_id")
    print(f"[gen] job={job_id} tileset={tileset_id}")

    job = poll_job(token, job_id, args.timeout)
    (args.out / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    result_response = requests.get(API_BASE + f"tilesets/{tileset_id}", headers=headers(token), timeout=60)
    result_response.raise_for_status()
    data = result_response.json()
    (args.out / "tileset.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    tiles_dir = args.out / "tiles"
    by_bit = save_tiles(data, tiles_dir, upper_name="upper")
    make_contact(by_bit, args.out / "contact_bits.png")

    after = get_balance(token)
    balance_line("after", after)
    delta = generation_delta(before, after)
    print(f"[cost] generations_used={delta if delta is not None else 'unknown'}")


if __name__ == "__main__":
    main()