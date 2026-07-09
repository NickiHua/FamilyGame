#!/usr/bin/env python3
"""Call Volcengine Visual inpainting to make LuLi's face angry.

This script first creates a local mask: black keeps the image unchanged, white is
the face area to redraw. Use ``--dry-run`` to generate and inspect the mask before
submitting a paid/quota-consuming Visual API task.

Credentials are Visual/OpenAPI AK/SK, not the Ark bearer API key. Provide them
with environment variables:

    VOLCENGINE_ACCESS_KEY_ID
    VOLCENGINE_SECRET_ACCESS_KEY

or create a local gitignored file named ``volcengine_aksk.json``:

    {"access_key_id":"...", "secret_access_key":"..."}
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter


ENDPOINT = "https://visual.volcengineapi.com/"
HOST = "visual.volcengineapi.com"
REGION = "cn-north-1"
SERVICE = "cv"
VERSION = "2022-08-31"
DEFAULT_INPUT = (
    "art_undecided/portraits/luli/"
    "luli_full_2k_transparent_doubao-seedream-5-0-260128_"
    "20260707_225710.png"
)
DEFAULT_FACE_BOX = "920,215,1140,390"
DEFAULT_PROMPT = (
    "Expression edit only. Keep the exact same young male swordsman, same face "
    "shape, same brown hair, same clear BLUE eyes, same skin tone, same armor, "
    "same blue scarf and cape, same pose, same lighting, same line art, same "
    "background, and all unselected areas unchanged. Change only the eyebrows, "
    "eye expression, and mouth into an angry serious expression: lowered inward "
    "eyebrows, narrowed intense blue eyes, and a tense frown. The face must stay "
    "fully visible and uncovered. Do not add any face covering, mask, helmet, "
    "visor, mouth guard, scarf over the mouth, facial armor, glowing eyes, yellow "
    "eyes, scars, blood, text, logo, or new clothing."
)
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root() / path
    return path


def load_credentials(key_file: str | None) -> tuple[str, str, str | None]:
    access_key = (
        os.environ.get("VOLCENGINE_ACCESS_KEY_ID")
        or os.environ.get("VOLCENGINE_AK")
        or ""
    ).strip()
    secret_key = (
        os.environ.get("VOLCENGINE_SECRET_ACCESS_KEY")
        or os.environ.get("VOLCENGINE_SK")
        or ""
    ).strip()
    session_token = os.environ.get("VOLCENGINE_SESSION_TOKEN", "").strip() or None
    if access_key and secret_key:
        return access_key, secret_key, session_token

    candidates = []
    if key_file:
        candidates.append(resolve_path(key_file))
    candidates.extend(
        [repo_root() / "volcengine_aksk.json", repo_root() / "volcengine_aksk.txt"]
    )

    ak_file = repo_root() / "volcengineak.txt"
    sk_file = repo_root() / "volcenginesk.txt"
    if ak_file.is_file() and sk_file.is_file():
        access_key = ak_file.read_text(encoding="utf-8").strip()
        secret_key = sk_file.read_text(encoding="utf-8").strip()
        if access_key and secret_key:
            return access_key, secret_key, session_token

    for candidate in candidates:
        if not candidate.is_file():
            continue
        if candidate.suffix.lower() == ".json":
            data = json.loads(candidate.read_text(encoding="utf-8"))
            access_key = str(
                data.get("access_key_id") or data.get("ak") or data.get("AccessKeyId") or ""
            ).strip()
            secret_key = str(
                data.get("secret_access_key")
                or data.get("sk")
                or data.get("SecretAccessKey")
                or ""
            ).strip()
            session_token = str(
                data.get("session_token") or data.get("SessionToken") or ""
            ).strip() or None
        else:
            lines = [line.strip() for line in candidate.read_text(encoding="utf-8").splitlines()]
            lines = [line for line in lines if line and not line.startswith("#")]
            access_key = lines[0] if len(lines) >= 1 else ""
            secret_key = lines[1] if len(lines) >= 2 else ""
            session_token = lines[2] if len(lines) >= 3 else None
        if access_key and secret_key:
            return access_key, secret_key, session_token

    raise SystemExit(
        "ERROR: Visual AK/SK not found. Set VOLCENGINE_ACCESS_KEY_ID and "
        "VOLCENGINE_SECRET_ACCESS_KEY, or create volcengine_aksk.json."
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def canonical_query(params: dict[str, str]) -> str:
    encoded_pairs = []
    for name, value in sorted(params.items()):
        encoded_name = urllib.parse.quote(name, safe="-_.~")
        encoded_value = urllib.parse.quote(value, safe="-_.~")
        encoded_pairs.append(f"{encoded_name}={encoded_value}")
    return "&".join(encoded_pairs)


def sign_headers(
    *,
    action: str,
    payload: bytes,
    access_key: str,
    secret_key: str,
    session_token: str | None,
) -> dict[str, str]:
    timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    short_date = timestamp[:8]
    payload_hash = sha256_hex(payload)
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_headers = (
        "content-type:application/json\n"
        f"host:{HOST}\n"
        f"x-content-sha256:{payload_hash}\n"
        f"x-date:{timestamp}\n"
    )
    query = canonical_query({"Action": action, "Version": VERSION})
    canonical_request = "\n".join(
        [
            "POST",
            "/",
            query,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    credential_scope = f"{short_date}/{REGION}/{SERVICE}/request"
    string_to_sign = "\n".join(
        [
            "HMAC-SHA256",
            timestamp,
            credential_scope,
            sha256_hex(canonical_request.encode("utf-8")),
        ]
    )
    signing_key = hmac_sha256(secret_key.encode("utf-8"), short_date)
    signing_key = hmac_sha256(signing_key, REGION)
    signing_key = hmac_sha256(signing_key, SERVICE)
    signing_key = hmac_sha256(signing_key, "request")
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    headers = {
        "Authorization": (
            f"HMAC-SHA256 Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        ),
        "Content-Type": "application/json",
        "Host": HOST,
        "X-Content-Sha256": payload_hash,
        "X-Date": timestamp,
    }
    if session_token:
        headers["X-Security-Token"] = session_token
    return headers


def visual_post(action: str, body: dict[str, Any], key_file: str | None) -> dict[str, Any]:
    access_key, secret_key, session_token = load_credentials(key_file)
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    url = f"{ENDPOINT}?{canonical_query({'Action': action, 'Version': VERSION})}"
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers=sign_headers(
            action=action,
            payload=payload,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
        ),
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body_text = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"ERROR: Volcengine HTTP {error.code}: {body_text}") from error


def parse_box(text: str, width: int, height: int) -> tuple[int, int, int, int]:
    parts = [float(part.strip()) for part in text.split(",")]
    if len(parts) != 4:
        raise SystemExit("ERROR: --face-box must be x0,y0,x1,y1")
    if all(0 <= value <= 1 for value in parts):
        x0, y0, x1, y1 = (
            int(round(parts[0] * width)),
            int(round(parts[1] * height)),
            int(round(parts[2] * width)),
            int(round(parts[3] * height)),
        )
    else:
        x0, y0, x1, y1 = [int(round(value)) for value in parts]
    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(1, min(width, x1))
    y1 = max(1, min(height, y1))
    if x1 <= x0 or y1 <= y0:
        raise SystemExit(f"ERROR: invalid --face-box after clamping: {(x0, y0, x1, y1)}")
    return x0, y0, x1, y1


def parse_boxes(text: str | None, width: int, height: int) -> list[tuple[int, int, int, int]]:
    if not text:
        return []
    boxes = []
    for item in text.split(";"):
        item = item.strip()
        if item:
            boxes.append(parse_box(item, width, height))
    if not boxes:
        raise SystemExit("ERROR: --mask-boxes did not contain any boxes.")
    return boxes


def make_face_mask(
    image: Image.Image,
    *,
    face_box: str,
    mask_boxes: str | None,
    feather: int,
    mask_path: Path,
    preview_path: Path,
) -> tuple[Path, Path, list[tuple[int, int, int, int]]]:
    width, height = image.size
    boxes = parse_boxes(mask_boxes, width, height) or [parse_box(face_box, width, height)]
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        draw.ellipse(box, fill=255)
    if feather > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    mask.save(mask_path)

    preview = image.convert("RGBA")
    overlay = Image.new("RGBA", preview.size, (255, 0, 0, 0))
    overlay_alpha = mask.point(lambda value: int(value * 0.42))
    overlay.putalpha(overlay_alpha)
    preview = Image.alpha_composite(preview, overlay)
    preview_draw = ImageDraw.Draw(preview)
    for box in boxes:
        preview_draw.rectangle(box, outline=(255, 0, 0, 255), width=4)
    preview.save(preview_path)
    return mask_path, preview_path, boxes


def prepare_mask_file(
    image: Image.Image,
    *,
    mask_file: str,
    mask_path: Path,
    preview_path: Path,
) -> tuple[Path, Path]:
    source_mask_path = resolve_path(mask_file)
    if not source_mask_path.is_file():
        raise SystemExit(f"ERROR: mask file not found: {source_mask_path}")

    mask = Image.open(source_mask_path).convert("L")
    if mask.size != image.size:
        raise SystemExit(
            f"ERROR: mask size {mask.size} does not match image size {image.size}: "
            f"{source_mask_path}"
        )

    mask_path.parent.mkdir(parents=True, exist_ok=True)
    mask.save(mask_path)

    preview = image.convert("RGBA")
    overlay = Image.new("RGBA", preview.size, (255, 0, 0, 0))
    overlay_alpha = mask.point(lambda value: int(value * 0.42))
    overlay.putalpha(overlay_alpha)
    Image.alpha_composite(preview, overlay).save(preview_path)
    return mask_path, preview_path


def encode_input_image(image: Image.Image, *, encoding: str, jpeg_quality: int) -> str:
    buffer = BytesIO()
    if encoding == "jpg":
        image.convert("RGB").save(
            buffer, format="JPEG", quality=jpeg_quality, subsampling=0, optimize=True
        )
    else:
        image.convert("RGB").save(buffer, format="PNG")
    data = buffer.getvalue()
    if len(data) > MAX_IMAGE_BYTES:
        raise SystemExit(
            f"ERROR: RGB input {encoding.upper()} is {len(data) / 1024 / 1024:.2f} MiB; "
            "inpainting input limit is 5 MiB. Use a smaller image."
        )
    return base64.b64encode(data).decode("ascii")


def encode_mask_png(mask_path: Path) -> str:
    data = mask_path.read_bytes()
    if len(data) > MAX_IMAGE_BYTES:
        raise SystemExit(
            f"ERROR: mask PNG is {len(data) / 1024 / 1024:.2f} MiB; "
            "inpainting mask limit is 5 MiB."
        )
    return base64.b64encode(data).decode("ascii")


def ensure_success(response: dict[str, Any], context: str) -> dict[str, Any]:
    if response.get("code") != 10000:
        raise SystemExit(
            f"ERROR: Volcengine {context} response: {json.dumps(response, ensure_ascii=False)}"
        )
    data = response.get("data")
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: Volcengine {context} returned no data object: {response}")
    return data


def submit_task(body: dict[str, Any], key_file: str | None) -> str:
    response = visual_post("CVSync2AsyncSubmitTask", body, key_file)
    data = ensure_success(response, "submit")
    task_id = str(data.get("task_id") or "").strip()
    if not task_id:
        raise SystemExit(f"ERROR: submit did not return task_id: {response}")
    return task_id


def get_result(task_id: str, key_file: str | None, *, return_url: bool) -> dict[str, Any]:
    req_json = {
        "logo_info": {"add_logo": False},
        "return_url": return_url,
    }
    response = visual_post(
        "CVSync2AsyncGetResult",
        {
            "req_key": "i2i_inpainting_edit",
            "task_id": task_id,
            "req_json": json.dumps(req_json, ensure_ascii=False, separators=(",", ":")),
        },
        key_file,
    )
    return response


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
        print(f"[inpaint] poll {attempt}/{max_polls}: status={status or '<missing>'}")
        if status == "done":
            return data
        if status in {"not_found", "expired"}:
            raise SystemExit(f"ERROR: task {task_id} status={status}")
        time.sleep(poll_interval)
    raise SystemExit(f"ERROR: task {task_id} did not finish after {max_polls} polls.")


def sniff_suffix(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ".bin"


def indexed_out_path(out_path: Path, index: int, data: bytes) -> Path:
    sniffed = sniff_suffix(data)
    stem = out_path.stem if index == 0 else f"{out_path.stem}_{index}"
    suffix = sniffed if sniffed != ".bin" and sniffed != out_path.suffix.lower() else out_path.suffix
    return out_path.with_name(f"{stem}{suffix}")


def save_result(data: dict[str, Any], out_path: Path) -> None:
    encoded_images = data.get("binary_data_base64") or []
    image_urls = data.get("image_urls") or []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if encoded_images:
        for image_index, encoded in enumerate(encoded_images):
            image_data = base64.b64decode(encoded)
            target = indexed_out_path(out_path, image_index, image_data)
            target.write_bytes(image_data)
            print(f"[inpaint] saved {target.relative_to(repo_root())}")
        return

    if image_urls:
        for image_index, image_url in enumerate(image_urls):
            with urllib.request.urlopen(image_url, timeout=180) as response_file:
                image_data = response_file.read()
            target = indexed_out_path(out_path, image_index, image_data)
            target.write_bytes(image_data)
            print(f"[inpaint] saved {target.relative_to(repo_root())}")
        return

    raise SystemExit("ERROR: result did not contain binary_data_base64 or image_urls.")


def default_out(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_volc_inpaint_angry_face.png")


def default_mask(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_angry_face_mask.png")


def default_preview(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_angry_face_mask_preview.png")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Volcengine inpainting test: make LuLi's face angry."
    )
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT, help="input image path")
    parser.add_argument("-o", "--out", help="output image path")
    parser.add_argument("--mask-out", help="mask PNG path")
    parser.add_argument("--preview-out", help="red-overlay mask preview path")
    parser.add_argument(
        "--mask-file",
        help="existing same-size mask image; white=redraw, black=keep. Overrides generated masks.",
    )
    parser.add_argument("--key-file", help="local AK/SK json or txt file")
    parser.add_argument("--face-box", default=DEFAULT_FACE_BOX, help="x0,y0,x1,y1 in pixels, or normalized 0..1")
    parser.add_argument(
        "--mask-boxes",
        help="semicolon-separated ellipse boxes x0,y0,x1,y1; overrides --face-box",
    )
    parser.add_argument("--feather", type=int, default=8, help="mask Gaussian blur radius in pixels")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--input-encoding", choices=["jpg", "png"], default="jpg")
    parser.add_argument("--jpeg-quality", type=int, default=95)
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--scale", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--return-url", action="store_true", help="ask get-result for URLs instead of base64")
    parser.add_argument("--poll-interval", type=float, default=3.0)
    parser.add_argument("--max-polls", type=int, default=80)
    parser.add_argument("--dry-run", action="store_true", help="generate mask only; do not call API")
    args = parser.parse_args()

    input_path = resolve_path(args.input)
    if not input_path.is_file():
        raise SystemExit(f"ERROR: input not found: {input_path}")
    out_path = resolve_path(args.out) if args.out else default_out(input_path)
    mask_path = resolve_path(args.mask_out) if args.mask_out else default_mask(input_path)
    preview_path = resolve_path(args.preview_out) if args.preview_out else default_preview(input_path)

    image = Image.open(input_path).convert("RGB")
    boxes = None
    if args.mask_file:
        mask_path, preview_path = prepare_mask_file(
            image,
            mask_file=args.mask_file,
            mask_path=mask_path,
            preview_path=preview_path,
        )
    else:
        mask_path, preview_path, boxes = make_face_mask(
            image,
            face_box=args.face_box,
            mask_boxes=args.mask_boxes,
            feather=args.feather,
            mask_path=mask_path,
            preview_path=preview_path,
        )
    print(f"[inpaint] input={input_path.relative_to(repo_root())}")
    print(f"[inpaint] image={image.width}x{image.height} mode=RGB")
    if args.mask_file:
        print(f"[inpaint] mask_file={resolve_path(args.mask_file).relative_to(repo_root())}")
    else:
        print(f"[inpaint] boxes={boxes} feather={args.feather}")
    print(f"[inpaint] mask={mask_path.relative_to(repo_root())}")
    print(f"[inpaint] preview={preview_path.relative_to(repo_root())}")
    print(f"[inpaint] out={out_path.relative_to(repo_root())}")
    if args.dry_run:
        print("[inpaint] dry-run: mask generated, not calling Volcengine.")
        return 0

    body = {
        "req_key": "i2i_inpainting_edit",
        "binary_data_base64": [
            encode_input_image(
                image, encoding=args.input_encoding, jpeg_quality=args.jpeg_quality
            ),
            encode_mask_png(mask_path),
        ],
        "custom_prompt": args.prompt,
        "steps": args.steps,
        "scale": args.scale,
        "seed": args.seed,
    }
    print("[inpaint] submitting CVSync2AsyncSubmitTask...")
    task_id = submit_task(body, args.key_file)
    print(f"[inpaint] task_id={task_id}")
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