"""Generate portrait test images with ModelArk Seedream.

This is intentionally small and stdlib-only: it reads a local ModelArk key,
sends one image-generation request, and saves either b64 or URL responses as PNG.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


BASE_URLS = {
    "byteplus": "https://ark.ap-southeast.bytepluses.com/api/v3",
    "volcengine": "https://ark.cn-beijing.volces.com/api/v3",
}
DEFAULT_MODELS = {
    "byteplus": "seedream-5-0-260128",
    "volcengine": "doubao-seedream-5-0-260128",
}
DEFAULT_RESPONSE_FORMATS = {
    "byteplus": "b64_json",
    "volcengine": "url",
}

PORTRAIT_STYLE = (
    "Classic modern Japanese SRPG / commercial JRPG character-art style: clean and "
    "refined, smooth natural lineart, soft cel-shading with a light painterly touch, "
    "soft unified lighting, vivid but not oversaturated colours. Slender natural body "
    "proportions, tasteful Japanese-anime facial aesthetics, an elegant yet practical "
    "fantasy costume that is restrained, not over-decorated, not gaudy. Strong class "
    "identity and character identity, cohesive with a single unified party art "
    "direction so every character reads as one commercial JRPG cast. High-quality, "
    "commercial-grade illustration. NO text, NO labels, NO logo, NO watermark, NO "
    "signature, NO border, NO UI elements."
)

LULI = (
    "CHARACTER - Lu Li, the party's protagonist swordsman. "
    "AGE / GENDER: a 20-year-old young man. "
    "BUILD: slender, athletic and fit, tall, about 7.5 heads. "
    "HAIR: short brown hair, tidy with natural bangs. "
    "EYES: clear blue. "
    "FACE: handsome youthful features with a bright, confident, genuine look and an "
    "easy natural smile. "
    "OUTFIT: white LIGHT knight armour with a DEEP BLUE cape; refined and practical, "
    "flexible yet protective, classic Japanese-fantasy, NOT over-complex and NOT "
    "gaudy; clean and crisp. "
    "PALETTE: white + silver armour, a deep blue cape, brown hair - clean and knightly. "
    "SIGNATURE WEAPON: an elegant LONG SWORD worn at the waist in a simple refined "
    "scabbard with a clean guard; natural proportions befitting a young kingdom "
    "swordsman. "
    "CLASS READ: unmistakably a melee swordsman - light armour + sheathed long sword, "
    "standing upright in a confident, relaxed stance, one hand resting naturally near "
    "the sword hilt. "
    "DETAIL: keep the design CLEAN and RESTRAINED - flat cel-shading, NO busy "
    "over-detailing, no heavy painterly noise. "
)

LULI_FULL_PROMPT = (
    "Generate ONE single COMPLETE FULL-BODY character portrait (tachie) for an "
    "original commercial Japanese tactical RPG. The entire figure must be visible "
    "from head to toe, both feet fully visible, standing upright in an elegant natural "
    "pose, centered with generous empty margin on all four sides, with nothing cropped "
    "or touching any edge. "
    + LULI
    + "FRAMING CONSTRAINT: frame as a full-body long shot; the entire head, hair, cape, "
    "sword and both feet must sit fully inside the canvas with clear empty padding "
    "above the head and below the feet; NO cinematic or fashion crop; if anything "
    "does not fit, zoom the camera out until it fully fits. "
    + PORTRAIT_STYLE
)

TRANSPARENT_OUTPUT_HINT = (
    "OUTPUT REQUIREMENT: return a PNG with a real alpha channel. Render ONLY the "
    "character. Everything outside the character silhouette must be fully transparent "
    "alpha, not white, not grey, not black, not checkerboard, and not a painted studio "
    "background. "
)

PRESETS = {
    "luli-full": {
        "prompt": LULI_FULL_PROMPT,
        "type": "luli",
        "filename_prefix": "luli_full_2k_transparent",
    },
}


def load_key(repo_root: Path, provider: str, key_file: str | None) -> str:
    candidates = []
    if key_file:
        candidates.append(Path(key_file))
    if provider == "volcengine":
        candidates.append(repo_root / "volcenginekey.txt")
    else:
        candidates.append(repo_root / "byteplustkey.txt")

    for candidate in candidates:
        if candidate.is_file():
            key = candidate.read_text(encoding="utf-8").strip()
            if key:
                return key

    for env_name in ("ARK_API_KEY", "VOLCENGINE_API_KEY", "BYTEPLUS_API_KEY"):
        key = os.environ.get(env_name, "").strip()
        if key:
            return key

    sys.exit("ERROR: no ModelArk key found in local key file or ARK_API_KEY.")


def post_json(url: str, api_key: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
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
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        sys.exit(f"ERROR: BytePlus HTTP {error.code}: {body}")


def download_url(url: str, out_path: Path) -> None:
    with urllib.request.urlopen(url, timeout=600) as response:
        out_path.write_bytes(response.read())


def save_image(response: dict, out_path: Path) -> None:
    data = response.get("data") or []
    if not data:
        sys.exit("ERROR: response did not contain data[].")

    item = data[0]
    if item.get("b64_json"):
        out_path.write_bytes(base64.b64decode(item["b64_json"]))
        return
    if item.get("url"):
        download_url(item["url"], out_path)
        return
    if item.get("image_url"):
        download_url(item["image_url"], out_path)
        return

    sys.exit("ERROR: response did not contain b64_json, url, or image_url.")


def png_info(path: Path) -> tuple[int, int, int, bool, bool]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        sys.exit(f"ERROR: output is not a PNG: {path}")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    color_type = data[25]
    has_trns = b"tRNS" in data
    has_alpha = color_type in (4, 6) or has_trns
    return width, height, color_type, has_trns, has_alpha


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(description="Generate portraits with ModelArk Seedream.")
    parser.add_argument("preset", choices=list(PRESETS.keys()) + ["custom"])
    parser.add_argument("--prompt", help="Free-form prompt (required for 'custom').")
    parser.add_argument("--type", default="misc", help="Output subfolder under art_undecided/portraits/ (for 'custom').")
    parser.add_argument("--prefix", default="custom", help="Output filename prefix (for 'custom').")
    parser.add_argument("--provider", choices=BASE_URLS.keys(), default="byteplus")
    parser.add_argument("--base-url")
    parser.add_argument("--model")
    parser.add_argument("--size", default="2K")
    parser.add_argument("--background", default="transparent")
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--response-format")
    parser.add_argument("--sequential-image-generation", default="disabled")
    parser.add_argument("--transparent-prompt-hint", action="store_true")
    parser.add_argument("--watermark", action="store_true")
    parser.add_argument("--key-file")
    parser.add_argument("--out")
    args = parser.parse_args()

    base_url = args.base_url or BASE_URLS[args.provider]
    model = args.model or DEFAULT_MODELS[args.provider]
    response_format = args.response_format or DEFAULT_RESPONSE_FORMATS[args.provider]

    if args.preset == "custom":
        if not args.prompt:
            sys.exit("ERROR: 'custom' requires --prompt.")
        preset = {
            "prompt": args.prompt,
            "type": args.type,
            "filename_prefix": args.prefix,
        }
    else:
        preset = PRESETS[args.preset]
    out_path = Path(args.out) if args.out else None
    if out_path is None:
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = repo_root / "art_undecided" / "portraits" / preset["type"]
        model_slug = model.replace("/", "_").replace(":", "_")
        out_path = out_dir / f"{preset['filename_prefix']}_{model_slug}_{stamp}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "model": model,
        "prompt": (TRANSPARENT_OUTPUT_HINT + preset["prompt"])
        if args.transparent_prompt_hint
        else preset["prompt"],
        "size": args.size,
        "background": args.background,
        "output_format": args.output_format,
        "response_format": response_format,
        "stream": False,
        "watermark": args.watermark,
    }
    # Some models (e.g. seedream 5.0 PRO) reject `sequential_image_generation`
    # entirely; pass "omit" to leave the key out of the request.
    if args.sequential_image_generation.lower() != "omit":
        payload["sequential_image_generation"] = args.sequential_image_generation

    print(
        f"[seedream] provider={args.provider} model={model} size={args.size} "
        f"background={args.background} output_format={args.output_format} "
        f"transparent_prompt_hint={args.transparent_prompt_hint}"
    )
    response = post_json(
        f"{base_url}/images/generations",
        load_key(repo_root, args.provider, args.key_file),
        payload,
    )
    save_image(response, out_path)
    width, height, color_type, has_trns, has_alpha = png_info(out_path)
    print(f"[seedream] out={out_path.relative_to(repo_root)}")
    print(
        f"[seedream] png={width}x{height} color_type={color_type} "
        f"has_tRNS={has_trns} has_alpha={has_alpha}"
    )


if __name__ == "__main__":
    main()