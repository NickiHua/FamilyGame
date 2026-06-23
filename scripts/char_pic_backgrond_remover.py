#!/usr/bin/env python3
r"""
char_pic_backgrond_remover.py — local, free background remover for character art.

Why this exists
---------------
flood-fill keying (used for the demo) only eats *colour-connected* background,
so it CAN'T reach the background trapped inside hair gaps, gives only hard 0/255
alpha (black halos on hair tips, jagged thin-sword edges) and breaks on thin
shapes. For real character portraits we want SOFT alpha that goes into the hair.

`rembg` runs a semantic segmentation model LOCALLY (free, no API). The
`isnet-anime` model is trained specifically on anime / 2.5D art, which is
exactly our portrait style. With alpha matting on, hair tips feather cleanly and
the background trapped between strands is removed.

This is for ORGANIC-edge art (portraits, 立绘). Hard-edge UI (gold frames,
buttons) should keep using GPT-Image native transparency / flood-fill — do NOT
run rembg on those (soft segmentation smears clean geometric edges).

Cost note
---------
Money: zero (fully local). Footprint: pulls onnxruntime + downloads the model
weights (~170MB) into the rembg cache on first run, and is slower / more memory
than flood-fill. No API key, no paid call.

Usage (CWD = FamilyGame/)
-------------------------
    # single file -> <name>_cutout.png next to it
    .\.venv\Scripts\python.exe scripts\char_pic_backgrond_remover.py ^
        art\undecided_art\profilepics\LuLi_007_00001_.png

    # explicit output
    .\.venv\Scripts\python.exe scripts\char_pic_backgrond_remover.py in.png -o out.png

    # tune alpha matting (default on) or turn it off
    .\.venv\Scripts\python.exe scripts\char_pic_backgrond_remover.py in.png ^
        --fg-threshold 240 --bg-threshold 10 --erode 8
    .\.venv\Scripts\python.exe scripts\char_pic_backgrond_remover.py in.png --no-matting

    # batch a whole folder
    .\.venv\Scripts\python.exe scripts\char_pic_backgrond_remover.py ^
        art\undecided_art\profilepics --batch -o art\undecided_art\profilepics\cutout
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image
from rembg import new_session, remove

# isnet-anime: trained on anime/illustration art -> best for our 立绘 portraits.
DEFAULT_MODEL = "isnet-anime"
IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def cut_one(
    src: Path,
    dst: Path,
    session,
    *,
    matting: bool,
    fg_threshold: int,
    bg_threshold: int,
    erode: int,
    post_process: bool,
) -> None:
    img = Image.open(src).convert("RGBA")
    out = remove(
        img,
        session=session,
        alpha_matting=matting,
        alpha_matting_foreground_threshold=fg_threshold,
        alpha_matting_background_threshold=bg_threshold,
        alpha_matting_erode_size=erode,
        post_process_mask=post_process,
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    a = out.split()[-1]
    print(f"  {src.name} -> {dst}  (size {out.width}x{out.height}, "
          f"alpha range {a.getextrema()})")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Local rembg background remover for character portraits."
    )
    p.add_argument("input", type=Path,
                   help="image file, or a folder when --batch is set")
    p.add_argument("-o", "--out", type=Path, default=None,
                   help="output file (single) or output folder (--batch). "
                        "Default: <name>_cutout.png next to the input.")
    p.add_argument("--batch", action="store_true",
                   help="treat input as a folder and process every image in it")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"rembg model name (default: {DEFAULT_MODEL})")
    p.add_argument("--no-matting", dest="matting", action="store_false",
                   help="disable alpha matting (faster, harder edges)")
    p.add_argument("--fg-threshold", type=int, default=240,
                   help="alpha matting foreground threshold (default 240)")
    p.add_argument("--bg-threshold", type=int, default=10,
                   help="alpha matting background threshold (default 10)")
    p.add_argument("--erode", type=int, default=10,
                   help="alpha matting erode size (default 10)")
    p.add_argument("--no-post", dest="post_process", action="store_false",
                   help="disable rembg post_process_mask")
    p.set_defaults(matting=True, post_process=True)
    args = p.parse_args(argv)

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1

    print(f"loading model '{args.model}' (first run downloads weights ~170MB)...")
    session = new_session(args.model)

    common = dict(
        session=session,
        matting=args.matting,
        fg_threshold=args.fg_threshold,
        bg_threshold=args.bg_threshold,
        erode=args.erode,
        post_process=args.post_process,
    )

    if args.batch:
        if not args.input.is_dir():
            print(f"ERROR: --batch needs a folder, got {args.input}",
                  file=sys.stderr)
            return 1
        out_dir = args.out or (args.input / "cutout")
        files = sorted(f for f in args.input.iterdir()
                       if f.is_file() and f.suffix.lower() in IMG_EXTS)
        if not files:
            print(f"no images found in {args.input}", file=sys.stderr)
            return 1
        print(f"batch: {len(files)} image(s) -> {out_dir}")
        for f in files:
            cut_one(f, out_dir / f"{f.stem}_cutout.png", **common)
    else:
        dst = args.out or args.input.with_name(f"{args.input.stem}_cutout.png")
        cut_one(args.input, dst, **common)

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
