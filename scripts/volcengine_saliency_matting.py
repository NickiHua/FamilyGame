#!/usr/bin/env python3
"""Call Volcengine Visual saliency segmentation for transparent matting.

Default input is the LuLi Seedream PNG used in the current art experiment.

Credentials are Visual/OpenAPI AK/SK, not the Ark bearer API key. Provide them
with environment variables:

    VOLCENGINE_ACCESS_KEY_ID
    VOLCENGINE_SECRET_ACCESS_KEY

or create a local gitignored file named ``volcengine_aksk.json``:

    {"access_key_id":"...", "secret_access_key":"..."}

Use ``--dry-run`` first to check paths and payload size without calling the API.
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
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image


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
MAX_BASE64_BYTES = int(4.7 * 1024 * 1024)


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


def image_base64(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    encoded_size = len(encoded.encode("ascii"))
    if encoded_size > MAX_BASE64_BYTES:
        raise SystemExit(
            f"ERROR: base64 payload is {encoded_size / 1024 / 1024:.2f} MiB; "
            "saliency_seg base64 input limit is about 4.7 MiB. Use a smaller PNG "
            "or an accessible image URL."
        )
    return encoded


def save_response_images(response: dict[str, Any], out_path: Path) -> None:
    if response.get("code") != 10000:
        raise SystemExit(f"ERROR: Volcengine response: {json.dumps(response, ensure_ascii=False)}")
    data = response.get("data") or {}
    encoded_images = data.get("binary_data_base64") or []
    image_urls = data.get("image_urls") or []
    if not encoded_images and not image_urls:
        raise SystemExit("ERROR: response did not contain binary_data_base64 or image_urls.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if encoded_images:
        for image_index, encoded in enumerate(encoded_images):
            suffix = "" if image_index == 0 else f"_{image_index}"
            target = out_path.with_name(f"{out_path.stem}{suffix}{out_path.suffix}")
            target.write_bytes(base64.b64decode(encoded))
            print(f"[matting] saved {target.relative_to(repo_root())}")
        return

    for image_index, image_url in enumerate(image_urls):
        suffix = "" if image_index == 0 else f"_{image_index}"
        target = out_path.with_name(f"{out_path.stem}{suffix}{out_path.suffix}")
        with urllib.request.urlopen(image_url, timeout=180) as response_file:
            target.write_bytes(response_file.read())
        print(f"[matting] saved {target.relative_to(repo_root())}")


def default_out(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_volc_saliency_seg.png")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Volcengine saliency_seg transparent matting test."
    )
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT, help="input image path")
    parser.add_argument("-o", "--out", help="output PNG path")
    parser.add_argument("--key-file", help="local AK/SK json or txt file")
    parser.add_argument("--only-mask", type=int, default=3, choices=[0, 1, 2, 3, 4])
    parser.add_argument("--refine-mask", type=int, default=2, choices=[0, 1, 2])
    parser.add_argument("--dry-run", action="store_true", help="validate inputs without calling API")
    args = parser.parse_args()

    input_path = resolve_path(args.input)
    if not input_path.is_file():
        raise SystemExit(f"ERROR: input not found: {input_path}")
    out_path = resolve_path(args.out) if args.out else default_out(input_path)

    with Image.open(input_path) as image:
        print(f"[matting] input={input_path.relative_to(repo_root())}")
        print(f"[matting] image={image.width}x{image.height} mode={image.mode}")
    encoded = image_base64(input_path)
    print(f"[matting] base64_size={len(encoded) / 1024 / 1024:.2f} MiB")
    print(f"[matting] out={out_path.relative_to(repo_root())}")

    body = {
        "req_key": "saliency_seg",
        "binary_data_base64": [encoded],
        "only_mask": args.only_mask,
        "rgb": [-1, -1, -1],
        "refine_mask": args.refine_mask,
    }
    if args.dry_run:
        print("[matting] dry-run: not calling Volcengine.")
        return 0

    response = visual_post("CVProcess", body, args.key_file)
    save_response_images(response, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())