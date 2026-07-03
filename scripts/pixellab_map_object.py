#!/usr/bin/env python3
r"""pixellab_map_object.py — generate a transparent top-down MAP OBJECT (house,
tree, rock, prop) via PixelLab's purpose-built /v2/map-objects endpoint.

Why this exists
---------------
GPT-Image flattens buildings toward a front elevation even when given a correct
high-angle reference. PixelLab's map-object model is trained specifically for
top-down game props, so `view="high top-down"` natively yields the steep overhead
projection (big foreshortened roof + short front wall) we want for SRPG maps.

Billing
-------
PixelLab is a SUBSCRIPTION (Tier 1 = $12/mo, 2000 generations/month). A map-object
call consumes from that monthly quota — it does NOT charge per-image real money
like GPT-Image. Run `--balance` to see remaining generations.

Auth (priority): --key-file (default pixellabkey.txt at repo root) -> env
PIXELLAB_API_TOKEN -> scripts/config.json {"pixellab_api_token": "..."}.
pixellabkey.txt is gitignored.

Usage (CWD = FamilyGame/)
-------------------------
    # check remaining quota
    .\.venv\Scripts\python.exe scripts\pixellab_map_object.py --balance

    # generate a cottage (default high top-down, 128x128, transparent)
    .\.venv\Scripts\python.exe scripts\pixellab_map_object.py ^
        --description "cozy medieval village cottage with golden thatched roof, half-timbered cream-and-brown walls, a wooden door and small window, stone foundation" ^
        --out art_undecided/tiles/houses/pixellab_cottage_0.png

    # use a reference image as an init/style hint
    .\.venv\Scripts\python.exe scripts\pixellab_map_object.py ^
        --description "..." --init-image art/uiconcept/house3.png --out ...
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

API_BASE = "https://api.pixellab.ai/v2/"


def get_token(key_file: Path | None) -> str:
    if key_file and key_file.is_file():
        t = key_file.read_text(encoding="utf-8").strip()
        if t:
            return t
    env = os.environ.get("PIXELLAB_API_TOKEN", "").strip()
    if env:
        return env
    cfg = Path(__file__).resolve().parent / "config.json"
    if cfg.is_file():
        try:
            t = (json.loads(cfg.read_text()) or {}).get("pixellab_api_token")
            if t:
                return t.strip()
        except (json.JSONDecodeError, OSError):
            pass
    sys.exit(
        "ERROR: no PixelLab token. Put it in pixellabkey.txt (repo root), set "
        "PIXELLAB_API_TOKEN, or scripts/config.json. (pixellabkey.txt is gitignored.)"
    )


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _img_to_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def show_balance(token: str) -> None:
    r = requests.get(API_BASE + "balance", headers=_headers(token), timeout=30)
    r.raise_for_status()
    b = r.json()
    sub = b.get("subscription", {})
    cred = b.get("credits", {})
    print(f"[balance] plan={sub.get('plan')} status={sub.get('status')} "
          f"generations={sub.get('generations')}/{sub.get('total')} "
          f"usd_credits=${cred.get('usd')}")


def _collect_image_urls(obj: dict) -> list[str]:
    urls: list[str] = []
    for v in (obj.get("rotation_urls") or {}).values():
        if v:
            urls.append(v)
    su = obj.get("storage_urls") or {}
    for v in su.values():
        if isinstance(v, str) and v.startswith("http"):
            urls.append(v)
        elif isinstance(v, dict):
            for f in v.get("frames", []) or []:
                if isinstance(f, str) and f.startswith("http"):
                    urls.append(f)
    for f in obj.get("frame_urls") or []:
        if isinstance(f, str) and f.startswith("http"):
            urls.append(f)
    # de-dup preserving order
    seen: set[str] = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description="Generate a transparent top-down map object via PixelLab.")
    ap.add_argument("--description", help="What to generate (required unless --balance).")
    ap.add_argument("--out", help="Output PNG path. Default auto under art_undecided/tiles/objects/.")
    ap.add_argument("--view", default="high top-down",
                    choices=["low top-down", "high top-down", "side"])
    ap.add_argument("--width", type=int, default=128)
    ap.add_argument("--height", type=int, default=128)
    ap.add_argument("--outline", default="single color outline",
                    choices=["single color outline", "selective outline", "lineless"])
    ap.add_argument("--shading", default="medium shading",
                    choices=["flat shading", "basic shading", "medium shading", "detailed shading"])
    ap.add_argument("--detail", default="medium detail",
                    choices=["low detail", "medium detail", "high detail"])
    ap.add_argument("--guidance", type=float, default=8.0, help="text_guidance_scale 1-20.")
    ap.add_argument("--init-image", help="Optional reference/init image path (style/angle hint).")
    ap.add_argument("--init-strength", type=int, default=300, help="1-999, init image influence.")
    ap.add_argument("--seed", type=int, help="Optional seed for reproducibility.")
    ap.add_argument("--balance", action="store_true", help="Just print quota and exit.")
    ap.add_argument("--key-file", default=str(repo_root / "pixellabkey.txt"))
    ap.add_argument("--timeout", type=int, default=180, help="Max seconds to poll.")
    args = ap.parse_args()

    token = get_token(Path(args.key_file))

    if args.balance:
        show_balance(token)
        return
    if not args.description:
        sys.exit("ERROR: --description is required (or use --balance).")

    payload: dict = {
        "description": args.description,
        "image_size": {"width": args.width, "height": args.height},
        "view": args.view,
        "outline": args.outline,
        "shading": args.shading,
        "detail": args.detail,
        "text_guidance_scale": args.guidance,
    }
    if args.init_image:
        p = Path(args.init_image)
        if not p.is_file():
            sys.exit(f"ERROR: init image not found: {args.init_image}")
        payload["init_image"] = {"type": "base64", "base64": _img_to_b64(p)}
        payload["init_image_strength"] = args.init_strength
    if args.seed is not None:
        payload["seed"] = args.seed

    print(f"[gen] view={args.view} size={args.width}x{args.height} "
          f"outline='{args.outline}' shading='{args.shading}' detail='{args.detail}' "
          f"init={'yes' if args.init_image else 'no'}")
    show_balance(token)

    r = requests.post(API_BASE + "map-objects", headers=_headers(token), json=payload, timeout=60)
    if r.status_code not in (200, 202):
        sys.exit(f"ERROR: map-objects POST failed: {r.status_code} {r.text}")
    sub = r.json()
    job_id = sub.get("background_job_id")
    object_id = sub.get("object_id")
    print(f"[gen] queued job={job_id} object={object_id}")

    # poll background job
    deadline = time.time() + args.timeout
    last_status = None
    while time.time() < deadline:
        jr = requests.get(API_BASE + f"background-jobs/{job_id}", headers=_headers(token), timeout=30)
        jr.raise_for_status()
        job = jr.json()
        status = job.get("status")
        if status != last_status:
            print(f"[poll] status={status}")
            last_status = status
        if status == "completed":
            break
        if status == "failed":
            sys.exit(f"ERROR: job failed: {json.dumps(job.get('last_response'))}")
        time.sleep(4)
    else:
        sys.exit("ERROR: timed out waiting for job.")

    # fetch the object to get image URL(s)
    orr = requests.get(API_BASE + f"objects/{object_id}", headers=_headers(token), timeout=30)
    orr.raise_for_status()
    obj = orr.json()
    urls = _collect_image_urls(obj)
    if not urls:
        print("[warn] no image URLs on object; dumping object detail:")
        print(json.dumps(obj, indent=2)[:2000])
        sys.exit("ERROR: no downloadable image found.")

    # resolve output path
    out_dir = repo_root / "art_undecided" / "tiles" / "objects"
    if args.out:
        out_base = Path(args.out)
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%H%M%S")
        out_base = out_dir / f"map_object_{stamp}.png"
    out_base.parent.mkdir(parents=True, exist_ok=True)

    for i, u in enumerate(urls):
        data = requests.get(u, timeout=60).content
        if len(urls) == 1:
            out_path = out_base
        else:
            out_path = out_base.with_name(f"{out_base.stem}_{i}{out_base.suffix or '.png'}")
        out_path.write_bytes(data)
        print(f"[ok] wrote {out_path}  ({len(data)//1024} KB)")


if __name__ == "__main__":
    main()
