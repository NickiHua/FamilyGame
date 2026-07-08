#!/usr/bin/env python3
r"""Generate PixelLab 1-direction object candidates.

This wraps /v2/create-1-direction-object (the website Create Object flow) for
experiments where we want multiple static object candidates, e.g. mushroom-tree
forest variants. It reports balance before/after and downloads all returned
candidate frames.
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
    raise TimeoutError("timed out waiting for PixelLab object job")


def collect_urls(obj: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for value in (obj.get("rotation_urls") or {}).values():
        if isinstance(value, str) and value.startswith("http"):
            urls.append(value)
    for value in (obj.get("storage_urls") or {}).values():
        if isinstance(value, str) and value.startswith("http"):
            urls.append(value)
        elif isinstance(value, dict):
            for frame in value.get("frames", []) or []:
                if isinstance(frame, str) and frame.startswith("http"):
                    urls.append(frame)
    for frame in obj.get("frame_urls") or []:
        if isinstance(frame, str) and frame.startswith("http"):
            urls.append(frame)
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def make_contact(paths: list[Path], out_path: Path) -> None:
    if not paths:
        return
    images = [Image.open(path).convert("RGBA") for path in paths]
    max_w = max(image.width for image in images)
    max_h = max(image.height for image in images)
    scale = 2 if max(max_w, max_h) <= 170 else 1
    cell_w = max_w * scale
    cell_h = max_h * scale
    label_h = 22
    margin = 12
    cols = min(4, len(images))
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (margin * (cols + 1) + cell_w * cols, margin * (rows + 1) + (cell_h + label_h) * rows), (34, 36, 40))
    draw = ImageDraw.Draw(sheet)
    for index, (path, image) in enumerate(zip(paths, images)):
        x = margin + (index % cols) * (cell_w + margin)
        y = margin + (index // cols) * (cell_h + label_h + margin)
        bg = Image.new("RGB", (cell_w, cell_h), (32, 34, 38))
        preview = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
        ox = (cell_w - preview.width) // 2
        oy = (cell_h - preview.height) // 2
        bg.paste(preview, (ox, oy), preview)
        sheet.paste(bg, (x, y + label_h))
        draw.text((x, y), path.name, fill=(235, 238, 228))
        draw.rectangle((x, y + label_h, x + cell_w - 1, y + label_h + cell_h - 1), outline=(86, 90, 98))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    print(f"[ok] contact -> {out_path}")


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Generate PixelLab 1-direction object candidates.")
    parser.add_argument("--description", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=int, help="Output size. Omit when using --style-ref; PixelLab derives size from the largest style image.")
    parser.add_argument("--view", choices=("top-down", "sidescroller"), default="top-down")
    parser.add_argument("--style-ref", type=Path, action="append", default=[])
    parser.add_argument("--item", action="append", default=[], help="Optional per-candidate description.")
    parser.add_argument("--key-file", type=Path, default=repo_root / "pixellabkey.txt")
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token = get_token(args.key_file)
    before = get_balance(token)
    balance_line("before", before)

    payload: dict[str, Any] = {
        "description": args.description,
        "view": args.view,
    }
    if args.style_ref:
        payload["style_images"] = [image_to_b64(path) for path in args.style_ref]
        if args.size is not None:
            print("[warn] --size is ignored when --style-ref is provided; PixelLab derives size from the largest style image.")
    else:
        payload["size"] = args.size or 128
    if args.item:
        payload["item_descriptions"] = args.item

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "request.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[gen] POST /create-1-direction-object out={args.out}")
    response = requests.post(API_BASE + "create-1-direction-object", headers=headers(token), json=payload, timeout=60)
    if response.status_code not in (200, 202):
        sys.exit(f"ERROR: create-1-direction-object failed {response.status_code}: {response.text}")
    submission = response.json()
    (args.out / "submission.json").write_text(json.dumps(submission, ensure_ascii=False, indent=2), encoding="utf-8")
    job_id = submission.get("background_job_id")
    object_id = submission.get("object_id")
    print(f"[gen] job={job_id} object={object_id} n_frames={submission.get('n_frames')}")

    job = poll_job(token, job_id, args.timeout)
    (args.out / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    object_response = requests.get(API_BASE + f"objects/{object_id}", headers=headers(token), timeout=60)
    object_response.raise_for_status()
    obj = object_response.json()
    (args.out / "object.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    urls = collect_urls(obj)
    if not urls:
        raise RuntimeError("object completed but no downloadable image URLs found")

    saved: list[Path] = []
    for index, url in enumerate(urls):
        data = requests.get(url, timeout=60).content
        out_path = args.out / f"candidate_{index:02d}.png"
        out_path.write_bytes(data)
        saved.append(out_path)
        print(f"[ok] wrote {out_path} ({len(data)//1024} KB)")
    make_contact(saved, args.out / "contact.png")

    after = get_balance(token)
    balance_line("after", after)
    delta = generation_delta(before, after)
    print(f"[cost] generations_used={delta if delta is not None else 'unknown'}")


if __name__ == "__main__":
    main()