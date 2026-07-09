#!/usr/bin/env python3
"""Call Jimeng interactive inpainting with an explicit mask.

Docs: https://www.volcengine.com/docs/85621/1976207

This is the newer Jimeng mask-based edit API:

    req_key = jimeng_image2image_dream_inpaint

Input is two same-size images: original RGB image and grayscale mask where
black=keep, white=redraw.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from PIL import Image

from volcengine_inpaint_angry_face import (
    encode_input_image,
    encode_mask_png,
    ensure_success,
    prepare_mask_file,
    repo_root,
    resolve_path,
    save_result,
    visual_post,
)


REQ_KEY = "jimeng_image2image_dream_inpaint"
DEFAULT_INPUT = "art/portraits/luli/_opaque_source/luli_concept.png"
DEFAULT_MASK = "art/portraits/luli/_opaque_source/luli_concept_mask_inverted.jpg"


def default_out(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_jimeng_inpaint.jpg")


def default_mask_out(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_jimeng_mask_api.png")


def default_preview_out(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_jimeng_mask_preview.png")


def submit_task(body: dict[str, Any], key_file: str | None) -> str:
    response = visual_post("CVSync2AsyncSubmitTask", body, key_file)
    data = ensure_success(response, "submit")
    task_id = str(data.get("task_id") or "").strip()
    if not task_id:
        raise SystemExit(f"ERROR: submit did not return task_id: {response}")
    return task_id


def get_result(task_id: str, key_file: str | None, *, return_url: bool) -> dict[str, Any]:
    req_json = {
        "return_url": return_url,
        "logo_info": {"add_logo": False},
    }
    return visual_post(
        "CVSync2AsyncGetResult",
        {
            "req_key": REQ_KEY,
            "task_id": task_id,
            "req_json": json.dumps(req_json, ensure_ascii=False, separators=(",", ":")),
        },
        key_file,
    )


def poll_result(
    task_id: str,
    key_file: str | None,
    *,
    return_url: bool,
    poll_interval: float,
    max_polls: int,
) -> dict[str, Any]:
    for attempt in range(1, max_polls + 1):
        response = get_result(task_id, key_file, return_url=return_url)
        data = ensure_success(response, "get-result")
        status = str(data.get("status") or "").strip()
        print(f"[jimeng] poll {attempt}/{max_polls}: status={status or '<missing>'}")
        if status == "done":
            return data
        if status in {"not_found", "expired"}:
            raise SystemExit(f"ERROR: task {task_id} status={status}")
        time.sleep(poll_interval)
    raise SystemExit(f"ERROR: task {task_id} did not finish after {max_polls} polls.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Jimeng mask-based inpainting test.")
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT, help="input image path")
    parser.add_argument("--mask-file", default=DEFAULT_MASK, help="same-size mask; white=redraw, black=keep")
    parser.add_argument("--prompt", required=True, help="Jimeng edit prompt")
    parser.add_argument("-o", "--out", help="output image path")
    parser.add_argument("--mask-out", help="normalized API mask PNG path")
    parser.add_argument("--preview-out", help="red-overlay mask preview path")
    parser.add_argument("--key-file", help="local AK/SK json or txt file")
    parser.add_argument("--input-encoding", choices=["jpg", "png"], default="jpg")
    parser.add_argument("--jpeg-quality", type=int, default=95)
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--return-url", action="store_true", help="ask get-result for URLs instead of base64")
    parser.add_argument("--poll-interval", type=float, default=3.0)
    parser.add_argument("--max-polls", type=int, default=80)
    parser.add_argument("--dry-run", action="store_true", help="prepare mask/preview only; do not call API")
    args = parser.parse_args()

    input_path = resolve_path(args.input)
    if not input_path.is_file():
        raise SystemExit(f"ERROR: input not found: {input_path}")
    out_path = resolve_path(args.out) if args.out else default_out(input_path)
    mask_path = resolve_path(args.mask_out) if args.mask_out else default_mask_out(input_path)
    preview_path = resolve_path(args.preview_out) if args.preview_out else default_preview_out(input_path)

    image = Image.open(input_path).convert("RGB")
    mask_path, preview_path = prepare_mask_file(
        image,
        mask_file=args.mask_file,
        mask_path=mask_path,
        preview_path=preview_path,
    )

    print(f"[jimeng] input={input_path.relative_to(repo_root())}")
    print(f"[jimeng] image={image.width}x{image.height} mode=RGB")
    print(f"[jimeng] mask_file={resolve_path(args.mask_file).relative_to(repo_root())}")
    print(f"[jimeng] mask={mask_path.relative_to(repo_root())}")
    print(f"[jimeng] preview={preview_path.relative_to(repo_root())}")
    print(f"[jimeng] out={out_path.relative_to(repo_root())}")
    print(f"[jimeng] prompt={args.prompt}")
    if args.dry_run:
        print("[jimeng] dry-run: mask generated, not calling Volcengine.")
        return 0

    body = {
        "req_key": REQ_KEY,
        "binary_data_base64": [
            encode_input_image(
                image, encoding=args.input_encoding, jpeg_quality=args.jpeg_quality
            ),
            encode_mask_png(mask_path),
        ],
        "prompt": args.prompt,
        "seed": args.seed,
    }
    print("[jimeng] submitting CVSync2AsyncSubmitTask...")
    task_id = submit_task(body, args.key_file)
    print(f"[jimeng] task_id={task_id}")
    result = poll_result(
        task_id,
        args.key_file,
        return_url=args.return_url,
        poll_interval=args.poll_interval,
        max_polls=args.max_polls,
    )
    save_result(result, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())