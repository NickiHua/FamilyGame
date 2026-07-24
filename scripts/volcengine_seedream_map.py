#!/usr/bin/env python3
"""Generate map redraws through Volcengine Ark Seedream.

Small stdlib-only helper for map experiments. It supports multiple reference
images through the `image` field and intentionally avoids Lite-only parameters
such as sequential_image_generation / stream so Seedream 5.0 Pro accepts it.
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
DEFAULT_MODEL = "doubao-seedream-5-0-pro-260628"


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


def download_url(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=900) as response:
        return response.read()


def sniff_suffix(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ".bin"


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
    parser = argparse.ArgumentParser(description="Generate Seedream map redraws through Ark.")
    parser.add_argument("--ref", action="append", help="Reference image path. Repeat for multiple refs. Omit for pure text-to-image.")
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file", help="Read the prompt from a UTF-8 text file (overrides --prompt).")
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--size", default="1920x1920")
    parser.add_argument("--output-format", default="png", choices=["jpeg", "png"])
    parser.add_argument("--response-format", default="b64_json", choices=["b64_json", "url"])
    parser.add_argument("--key-file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.prompt_file:
        prompt = resolve_path(args.prompt_file).read_text(encoding="utf-8").strip()
    elif args.prompt:
        prompt = args.prompt
    else:
        raise SystemExit("ERROR: provide --prompt or --prompt-file.")

    ref_paths = [resolve_path(value) for value in (args.ref or [])]
    for ref_path in ref_paths:
        if not ref_path.is_file():
            raise SystemExit(f"ERROR: ref image not found: {ref_path}")
    out_path = resolve_path(args.out)
    payload = {
        "model": args.model,
        "prompt": prompt,
        "size": args.size,
        "output_format": args.output_format,
        "response_format": args.response_format,
        "watermark": False,
    }
    if ref_paths:
        payload["image"] = data_url(ref_paths[0]) if len(ref_paths) == 1 else [data_url(p) for p in ref_paths]

    print(f"[seedream-map] model={args.model} size={args.size} out={out_path.relative_to(repo_root())}")
    for i, ref_path in enumerate(ref_paths, 1):
        print(f"[seedream-map] ref{i}={ref_path.relative_to(repo_root())}")
    print(f"[seedream-map] prompt={prompt[:120]}...")
    if args.dry_run:
        print("[seedream-map] dry-run: not calling Ark.")
        return 0

    response = post_json(f"{BASE_URL}/images/generations", load_key(args.key_file), payload)
    saved = save_first_image(response, out_path)
    print(f"[seedream-map] saved {saved.relative_to(repo_root())}")
    usage = response.get("usage")
    if usage:
        print(f"[seedream-map] usage={json.dumps(usage, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())