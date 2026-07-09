#!/usr/bin/env python3
"""Generate Seedream reference-image character pose variants through Ark.

Uses the Ark OpenAI-compatible image generation endpoint with a single reference
image supplied through the ``image`` field as a data URL.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seedream-5-0-260128"
DEFAULT_REF = "art/portraits/luli/_opaque_source/luli_portrait.png"
DEFAULT_OUT_DIR = "art_undecided/portraits/luli/seedream_lite_refs"


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root() / path
    return path


def load_key(key_file: str | None) -> str:
    candidates = []
    if key_file:
        candidates.append(resolve_path(key_file))
    candidates.append(repo_root() / "volcenginekey.txt")
    for candidate in candidates:
        if candidate.is_file():
            key = candidate.read_text(encoding="utf-8").strip()
            if key:
                return key
    for env_name in ("ARK_API_KEY", "VOLCENGINE_API_KEY"):
        key = os.environ.get(env_name, "").strip()
        if key:
            return key
    raise SystemExit("ERROR: no Ark API key found in volcenginekey.txt or env.")


def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    if mime == "image/jpg":
        mime = "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def post_json(url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"ERROR: Ark HTTP {error.code}: {body}") from error


def sniff_suffix(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ".bin"


def download_url(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=900) as response:
        return response.read()


def save_first_image(response: dict[str, Any], out_path: Path) -> Path:
    data_items = response.get("data") or []
    if not data_items:
        raise SystemExit(f"ERROR: response did not contain data[]. Full response: {response}")
    item = data_items[0]
    if item.get("b64_json"):
        image_data = base64.b64decode(item["b64_json"])
    elif item.get("url"):
        image_data = download_url(item["url"])
    elif item.get("image_url"):
        image_data = download_url(item["image_url"])
    else:
        raise SystemExit(f"ERROR: response image had no b64_json/url: {item}")
    suffix = sniff_suffix(image_data)
    if suffix != ".bin" and out_path.suffix.lower() != suffix:
        out_path = out_path.with_suffix(suffix)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(image_data)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Seedream ref-image pose variants.")
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--size", default="1664x2496")
    parser.add_argument("--output-format", default="jpeg", choices=["jpeg", "png"])
    parser.add_argument("--response-format", default="b64_json", choices=["b64_json", "url"])
    parser.add_argument("--key-file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ref_path = resolve_path(args.ref)
    if not ref_path.is_file():
        raise SystemExit(f"ERROR: ref image not found: {ref_path}")
    out_path = resolve_path(args.out)
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "image": data_url(ref_path),
        "size": args.size,
        "output_format": args.output_format,
        "response_format": args.response_format,
        "sequential_image_generation": "disabled",
        "stream": False,
        "watermark": False,
    }
    print(f"[seedream-ref] model={args.model} size={args.size} out={out_path.relative_to(repo_root())}")
    print(f"[seedream-ref] ref={ref_path.relative_to(repo_root())}")
    print(f"[seedream-ref] prompt={args.prompt}")
    if args.dry_run:
        print("[seedream-ref] dry-run: not calling Ark.")
        return 0

    response = post_json(f"{BASE_URL}/images/generations", load_key(args.key_file), payload)
    saved = save_first_image(response, out_path)
    print(f"[seedream-ref] saved {saved.relative_to(repo_root())}")
    usage = response.get("usage")
    if usage:
        print(f"[seedream-ref] usage={json.dumps(usage, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())