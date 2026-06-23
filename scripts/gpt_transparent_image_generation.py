#!/usr/bin/env python3
r"""
gpt_transparent_image_generation.py — GPT-Image generator for FantacyCentry HD UI assets.

Why this exists
---------------
Gemini / ChatGPT web only ever *paint* a background (magenta or checker), so we
must chroma-key it out afterwards -> fringe, colour bleed, flattened corners.
The OpenAI Image API can output a TRUE alpha channel (like PixelLab sprites):

    background="transparent"   ->   real transparent PNG, NO keying needed.

IMPORTANT model note (verified 2026-06):
    * gpt-image-1 / gpt-image-1-mini / gpt-image-1.5  ->  support transparent bg
    * gpt-image-2 (newest)                            ->  does NOT support it
So we default to model="gpt-image-1".

Auth
----
The API key is read (in priority order) from:
    1. --key-file <path>           (default: openaikey.txt at repo root)
    2. OPENAI_API_KEY env variable
openaikey.txt is gitignored. NEVER commit a key.

Usage (CWD = FamilyGame/)
-------------------------
    # one of the built-in presets (transparent bg, no keying)
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py panel
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py banner-blue
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py banner-red
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py button

    # use an existing image as a STYLE REFERENCE / init (edits endpoint)
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py banner-blue ^
        --ref Assets/Art/UI/hd/panel_info_frame.png

    # free-form prompt (custom REQUIRES --type for the output folder)
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py custom ^
        --type icon --prompt "..." --size 1024x1024

Outputs default to:  art_undecided/ui/<type>/<preset>_<timestamp>_<i>.png
where <type> is the UI component folder (panel / banner / button / icon / ...),
inferred from the preset or set with --type. That top-level art_undecided/ folder
holds RAW output awaiting review; after you approve, the keeper moves to
art/ui/<type>/ (master) and a copy goes to Assets/Art/UI/<plural>/ for Unity.
See docs/pipelines/ui-asset-pipeline.md.
"""
from __future__ import annotations

import argparse
import base64
import datetime as _dt
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Prompts — TRANSPARENT-background variants (no magenta, no checker, real alpha)
# Adapted from docs/prompts/ui-prompts.md §8.2 / §8.3 / §8.4.
# ---------------------------------------------------------------------------
_COMMON_TAIL = (
    "High-resolution SMOOTH digital painting, clean anti-aliased vector-like "
    "rendering, crisp smooth gradients. Flat even lighting, NO 3D plastic gloss, "
    "NO heavy drop shadow, NOT pixel art, no jagged or chunky pixels. "
    "NO text, NO letters, NO numbers, NO icons, NO characters, NO portrait, "
    "no watermark, no signature. "
    "The background MUST be fully transparent — render ONLY the UI shape itself "
    "on a transparent background, nothing else, no backdrop, no plate behind it."
)

# Variant for action-icon buttons: the simple action GLYPH inside each frame IS
# wanted, so we must NOT forbid icons here (only forbid text / letters / numbers).
_ICON_TAIL = (
    "High-resolution SMOOTH digital painting, clean anti-aliased vector-like "
    "rendering, crisp smooth gradients. Flat even lighting, NO 3D plastic gloss, "
    "NO heavy drop shadow, NOT pixel art, no jagged or chunky pixels. "
    "NO text, NO letters, NO numbers, no watermark, no signature. "
    "The background MUST be fully transparent — render ONLY the icon buttons "
    "themselves on a transparent background, nothing else, no backdrop, no plate "
    "behind them, transparent gaps between the separate buttons."
)

# Maps a preset to its UI component TYPE = the art_undecided/ui/<type>/ folder
# (and, by mirror, art/ui/<type>/). Singular names per the UI asset pipeline doc.
PRESET_TYPE: dict[str, str] = {
    "panel": "panel",
    "banner-blue": "banner",
    "banner-red": "banner",
    "button": "button",
    "select-frame": "range",
    "action-icons": "icon",
}

PRESETS: dict[str, dict] = {
    # ① panel anchor — defines the gold style. 9-slice friendly, ~4:1.
    # 2026-06-22: thin gold + small corner flourishes + SOLID navy centre (not hollow).
    # Best run with --ref art/ui/button/button_normal_long.png as the style anchor.
    "panel": dict(
        size="1536x1024",
        prompt=(
            "Using the attached image as the exact style reference for the gold "
            "border (same THIN delicate gold line, same SMALL simple corner "
            "flourishes — do NOT make the gold thicker or more ornate), generate ONE "
            "single wide horizontal UI panel frame for a Japanese fantasy tactical "
            "RPG, isolated and centered, and NOTHING ELSE, roughly 4:1 (wide) aspect "
            "with rounded corners. The interior is a SOLID, FLAT, EVENLY filled deep "
            "NAVY-BLUE (completely opaque, NOT hollow, NOT transparent, NOT a window). "
            "The thin gold border runs cleanly around all four sides with ONE small "
            "simple gold flourish at each of the four corners, minimal and "
            "understated. The four straight edges are plain thin gold lines so it can "
            "be 9-sliced (corners fixed, navy center and edges stretch). The wide "
            "middle is plain flat navy with NO ornament, so engine text sits on top. "
            "Lightweight and clean — the gold must NOT dominate. " + _COMMON_TAIL
        ),
    ),
    # ② phase banner — solid navy bar, simple gold end-caps, ~3:1 (API max ratio).
    "banner-blue": dict(
        size="1536x1024",
        prompt=(
            "Generate ONE long horizontal ornamental phase BANNER for a Japanese "
            "fantasy tactical RPG and NOTHING ELSE, a very wide thin horizontal bar "
            "(about 3:1, as wide and short as allowed), isolated and centered. The "
            "whole banner is a SOLID filled deep NAVY-BLUE horizontal bar (the center "
            "is SOLID navy, completely filled, NOT hollow, NOT a window). On the far "
            "left and far right place a SMALL, SIMPLE, restrained gold corner accent "
            "each — just a single thin elegant gold flourish, MINIMAL scrollwork, NOT "
            "a big ornate baroque block, NOT busy, NOT dense filigree. A thin clean "
            "gold pinstripe runs along the top and bottom edges of the whole bar. The "
            "wide middle is plain, flat, even solid navy with NO ornament, so engine "
            "text can sit on top of it. Refined, elegant, mostly empty, understated. "
            + _COMMON_TAIL
        ),
    ),
    "banner-red": dict(
        size="1536x1024",
        prompt=(
            "Generate ONE long horizontal ornamental phase BANNER for a Japanese "
            "fantasy tactical RPG and NOTHING ELSE, a very wide thin horizontal bar "
            "(about 3:1, as wide and short as allowed), isolated and centered. The "
            "whole banner is a SOLID filled deep CRIMSON-RED horizontal bar (the "
            "center is SOLID red, completely filled, NOT hollow, NOT a window). On the "
            "far left and far right place a SMALL, SIMPLE, restrained gold corner "
            "accent each — just a single thin elegant gold flourish, MINIMAL "
            "scrollwork, NOT a big ornate baroque block, NOT busy, NOT dense filigree. "
            "A thin clean gold pinstripe runs along the top and bottom edges of the "
            "whole bar. The wide middle is plain, flat, even solid red with NO "
            "ornament, so engine text can sit on top of it. Refined, elegant, mostly "
            "empty, understated. " + _COMMON_TAIL
        ),
    ),
    # ③ command button frames — 3 states in a row, PLAIN gold edge only.
    # 2026-06-22: stripped of corner accents — a clean rounded gold-edged navy
    # button, hollow centre (engine draws label/icon on top). Reused for the
    # character command menu rows and the END TURN button.
    "button": dict(
        size="1536x1024",
        prompt=(
            "Generate THREE horizontal command BUTTON frames for a Japanese fantasy "
            "tactical RPG, arranged in a single row side by side, and NOTHING ELSE. "
            "Each is a compact wide rounded rectangle (about 3:1) with generously "
            "ROUNDED, soft corners and a deep translucent navy-blue interior, framed "
            "by ONE single smooth gold edge with a gently ROUNDED, slightly raised "
            "bevel that follows the rounded rectangle all the way around — soft and "
            "rounded, not a razor-thin sharp line, but still simple: absolutely NO "
            "corner flourish, NO scrollwork, NO ornament, NO accent, NO gems, just a "
            "clean smooth rounded gold rim. Hollow empty center so engine icons and "
            "text sit on top. The three differ ONLY in state: left = NORMAL (calm "
            "navy + gold), middle = HOVER (slightly brighter, subtle gold glow), "
            "right = PRESSED (slightly darker / inset). Identical shape and size "
            "across all three. NO text, NO icons inside. Do NOT draw panels, bars, or "
            "a kit — only the three plain rounded gold-edged button frames. "
            + _COMMON_TAIL
        ),
    ),
    # ④ select / cursor frame — gold corner brackets, hollow transparent centre,
    # sized to overlay a single battle-map cell. HD replacement for the old pixel
    # art/ui/range/select_frame.png. Run WITH --ref art/ui/range/select_frame.png.
    "select-frame": dict(
        size="1024x1024",
        prompt=(
            "Using the attached image as the exact style/layout reference, generate "
            "ONE square selected-tile CURSOR FRAME for a Japanese fantasy tactical "
            "RPG, isolated and centered, and NOTHING ELSE. It is made of FOUR gold "
            "corner BRACKETS (one in each corner) joined by thin gold edges, in the "
            "same refined navy-and-gold style as the reference, with elegant small "
            "gold corner scrollwork. The ENTIRE CENTER is COMPLETELY HOLLOW and "
            "fully TRANSPARENT — an empty window, NO fill, NO navy, NO glass, so the "
            "battle map shows straight through it. Only the thin gold bracket border "
            "ring is drawn. Square, sized to overlay a single map cell. " + _COMMON_TAIL
        ),
    ),
    # ⑤ action icon buttons — SEVEN small square HD gold-framed buttons in TWO
    # rows (4 on top, 3 on bottom), smooth (NOT pixel art), matching the
    # panel/button gold family. Navy fill, each with its action glyph baked in.
    # Glyph order: attack / skill / magic / item / wait / defend / move.
    # Run WITH --ref art_undecided/ui/icon_ref_transparent.png (icon CONTENT only;
    # render in smooth HD gold style, NOT the reference's pixel-art look).
    "action-icons": dict(
        size="1024x1024",
        prompt=(
            "Generate SEVEN small SQUARE command icon BUTTONS for a Japanese fantasy "
            "tactical RPG, laid out in a TIDY GRID of TWO ROWS — FOUR buttons in the "
            "top row and THREE buttons in the bottom row — evenly spaced, and NOTHING "
            "ELSE. The attached image shows the action concepts for reference ONLY — "
            "match what each icon DEPICTS, but DO NOT copy its pixel-art style; "
            "instead render everything SMOOTH and high-resolution with refined gold "
            "filigree, the same elegant navy-and-gold look as a matching UI panel. "
            "Every button is identical in size and frame: a small rounded-corner "
            "square with a thin refined SMOOTH gold border and a SMALL tasteful gold "
            "corner flourish at each corner, filled with a SOLID deep navy-blue "
            "interior (NOT hollow, NOT transparent inside). Centered on each navy face "
            "is ONE clear, bold, smooth golden action symbol. Top row left-to-right: "
            "(1) a SWORD for attack, (2) a four-point SPARKLE / star burst for skill, "
            "(3) a wizard STAFF topped with a glowing magic orb for magic, (4) a "
            "round POTION bottle for item. Bottom row left-to-right: (5) an HOURGLASS "
            "for wait, (6) a SHIELD for defend, (7) a BOOT for move. All SEVEN buttons "
            "must be FULLY INSIDE the canvas with clear even margins on every side — "
            "none touching, overlapping or cropped by any edge. Identical frame on "
            "all seven; only the inner symbol differs. Do NOT draw panels, bars, big "
            "buttons or a kit — only the seven small icon buttons in a two-row grid. "
            + _ICON_TAIL
        ),
    ),
}


def _load_key(key_file: Path | None) -> str:
    if key_file and key_file.is_file():
        key = key_file.read_text(encoding="utf-8").strip()
        if key:
            return key
    env = os.environ.get("OPENAI_API_KEY", "").strip()
    if env:
        return env
    sys.exit(
        "ERROR: no API key. Put it in openaikey.txt (repo root) or set "
        "OPENAI_API_KEY. (openaikey.txt is gitignored.)"
    )


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent

    ap = argparse.ArgumentParser(description="Generate HD UI assets via GPT-Image.")
    ap.add_argument(
        "preset",
        choices=list(PRESETS) + ["custom"],
        help="Which prompt preset to use, or 'custom' with --prompt.",
    )
    ap.add_argument("--prompt", help="Free-form prompt (required for 'custom').")
    ap.add_argument(
        "--ref",
        action="append",
        default=[],
        help="Reference / init image path (repeatable). Uses the edits endpoint.",
    )
    ap.add_argument("--out", help="Output PNG path. Default: auto-named under art_undecided/ui/<type>/.")
    ap.add_argument(
        "--type",
        help="UI component type = the art_undecided/ui/<type>/ output folder "
             "(panel, banner, button, icon, bar, nameplate). Defaults from the "
             "preset; REQUIRED for 'custom'.",
    )
    ap.add_argument("--model", default="gpt-image-1", help="Default gpt-image-1.")
    ap.add_argument(
        "--size",
        help="WxH, e.g. 1536x1024. Default depends on preset.",
    )
    ap.add_argument(
        "--quality",
        default="high",
        choices=["low", "medium", "high", "auto"],
    )
    ap.add_argument(
        "--background",
        default="transparent",
        choices=["transparent", "opaque", "auto"],
        help="transparent = true alpha PNG, no keying needed.",
    )
    ap.add_argument("--n", type=int, default=1, help="How many images.")
    ap.add_argument(
        "--key-file",
        default=str(repo_root / "openaikey.txt"),
        help="Path to a file containing the API key.",
    )
    args = ap.parse_args()

    # resolve prompt + size
    if args.preset == "custom":
        if not args.prompt:
            sys.exit("ERROR: 'custom' requires --prompt.")
        prompt = args.prompt
        size = args.size or "1024x1024"
    else:
        cfg = PRESETS[args.preset]
        prompt = args.prompt or cfg["prompt"]
        size = args.size or cfg["size"]

    # resolve UI component type -> art_undecided/ui/<type>/ output folder
    ui_type = args.type or PRESET_TYPE.get(args.preset)
    if not ui_type:
        sys.exit(
            "ERROR: cannot infer output folder. Pass --type <panel|banner|button|"
            "icon|bar|nameplate> (required for 'custom')."
        )

    # lazy import so --help works without the SDK installed
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("ERROR: openai SDK missing. Run: .venv\\Scripts\\python -m pip install openai")

    client = OpenAI(api_key=_load_key(Path(args.key_file)))

    common = dict(
        model=args.model,
        prompt=prompt,
        size=size,
        n=args.n,
        background=args.background,
    )
    # gpt-image-1 family supports quality low/medium/high; pass it through.
    if args.quality:
        common["quality"] = args.quality

    print(f"[gen] model={args.model} size={size} bg={args.background} "
          f"quality={args.quality} refs={len(args.ref)}")
    print(f"[gen] prompt: {prompt[:90]}...")

    if args.ref:
        # edits endpoint: use reference image(s) as init / style anchor
        files = []
        try:
            for r in args.ref:
                p = Path(r)
                if not p.is_file():
                    sys.exit(f"ERROR: ref image not found: {r}")
                files.append(open(p, "rb"))
            image_arg = files if len(files) > 1 else files[0]
            result = client.images.edit(image=image_arg, **common)
        finally:
            for f in files:
                f.close()
    else:
        result = client.images.generate(**common)

    # write outputs -> art_undecided/ui/<type>/ (raw, awaiting user review)
    out_arg = args.out
    stamp = _dt.datetime.now().strftime("%H%M%S")
    default_dir = repo_root / "art_undecided" / "ui" / ui_type
    default_dir.mkdir(parents=True, exist_ok=True)

    for i, item in enumerate(result.data):
        b64 = item.b64_json
        data = base64.b64decode(b64)
        if out_arg and args.n == 1:
            out_path = Path(out_arg)
        elif out_arg:
            stem = Path(out_arg)
            out_path = stem.with_name(f"{stem.stem}_{i}{stem.suffix or '.png'}")
        else:
            out_path = default_dir / f"{args.preset}_{stamp}_{i}.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        print(f"[ok] wrote {out_path}  ({len(data)//1024} KB)")


if __name__ == "__main__":
    main()
