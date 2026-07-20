"""Organize a character's DOWNLOAD into our game-direction folders.

Pipeline step (after pull + check pass). Reads the yaml (source of truth):
  - copies the 8 rotation PNGs -> pixellab/characters/<id>/rotations/
  - for each animation, copies the pixellab VISUAL frames into OUR direction
    folders per `anchor`:  animations/<action>/<S|N|E|W|SE|SW>/frame_00N.png
  - produces the mirror sides in post (flipX): every anchor `X: mirror:Y`
    whose Y is a source dir of that action -> X = flipX(Y).
  - builds review frame-strips (review/<action>_<dir>.png) + GIFs (_preview/).

Nothing here calls the API — it only reorganizes what pull already fetched.

Usage (repo root, venv):
  .\\.venv\\Scripts\\python.exe scripts\\pixellab_organize.py EmpireCaptain
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

YAML_PATH = Path("pixellab/character_status.yaml")


def load_state(char_id: str):
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    for c in data["characters"]:
        if c["id"] == char_id:
            return c["states"][0]
    raise SystemExit(f"character {char_id!r} not found")


def mirror_map(anchor: dict) -> dict:
    """{mirror_dir: source_dir}, e.g. {'W':'E','SW':'SE'}."""
    out = {}
    for k, v in anchor.items():
        if isinstance(v, str) and v.startswith("mirror:"):
            out[k] = v.split(":", 1)[1]
    return out


def copy_frames(src: Path, dst: Path) -> int:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    n = 0
    for f in sorted(src.glob("*.png")):
        shutil.copy2(f, dst / f.name)
        n += 1
    return n


def flip_frames(src: Path, dst: Path) -> int:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    n = 0
    for f in sorted(src.glob("*.png")):
        Image.open(f).transpose(Image.FLIP_LEFT_RIGHT).save(dst / f.name)
        n += 1
    return n


def build_review(anim_out: Path, review: Path) -> None:
    if review.exists():
        shutil.rmtree(review)
    review.mkdir(parents=True)
    for adir in sorted(anim_out.iterdir()):
        if not adir.is_dir():
            continue
        dirs = sorted([d for d in adir.iterdir() if d.is_dir()], key=lambda p: p.name)
        rows = []
        for d in dirs:
            frames = sorted(d.glob("*.png"))
            if frames:
                rows.append((d.name, frames))
        if not rows:
            continue
        cell = 96
        lab = 46
        ncol = max(len(f) for _, f in rows)
        W = lab + ncol * cell
        H = len(rows) * cell
        sheet = Image.new("RGBA", (W, H), (32, 32, 40, 255))
        dr = ImageDraw.Draw(sheet)
        for ri, (name, frames) in enumerate(rows):
            y0 = ri * cell
            dr.line([(0, y0), (W, y0)], fill=(70, 70, 80, 255))
            dr.text((4, y0 + cell // 2 - 4), name, fill=(160, 220, 255, 255))
            for ci, f in enumerate(frames):
                im = Image.open(f).convert("RGBA")
                s = min((cell - 6) / im.width, (cell - 6) / im.height)
                im = im.resize((int(im.width * s), int(im.height * s)), Image.NEAREST)
                sheet.alpha_composite(im, (lab + ci * cell + (cell - im.width) // 2,
                                           y0 + (cell - im.height) // 2))
        sheet.save(review / f"{adir.name}.png")
        print(f"    review {adir.name}.png ({len(rows)} dirs)")


def build_gifs(anim_out: Path, prev: Path) -> None:
    if prev.exists():
        shutil.rmtree(prev)
    prev.mkdir(parents=True)
    for adir in sorted(anim_out.iterdir()):
        if not adir.is_dir():
            continue
        for ddir in sorted(adir.iterdir()):
            frames = sorted(ddir.glob("*.png"))
            if len(frames) < 2:
                continue
            imgs = [Image.open(f).convert("RGBA") for f in frames]
            w = max(i.width for i in imgs)
            h = max(i.height for i in imgs)
            canvas = []
            for im in imgs:
                bg = Image.new("RGBA", (w, h), (40, 40, 48, 255))
                bg.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
                canvas.append(bg.convert("P", palette=Image.ADAPTIVE))
            out = prev / f"{adir.name}_{ddir.name}.gif"
            canvas[0].save(out, save_all=True, append_images=canvas[1:],
                           duration=110, loop=0, disposal=2)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: pixellab_organize.py <CharId>")
    char_id = sys.argv[1]
    st = load_state(char_id)
    anchor = st["anchor"]
    mirrors = mirror_map(anchor)
    char_dir = Path("pixellab/characters") / char_id.lower()
    dl = char_dir / "download"
    extract = list(dl.rglob("animations"))
    if not extract:
        raise SystemExit(f"no download/animations under {dl} (pull first)")
    root = extract[0].parent
    anim_src = root / "animations"
    rot_src = root / "rotations"

    # rotations
    rot_dst = char_dir / "rotations"
    contact = rot_dst / "_contact.png"
    keep = contact.read_bytes() if contact.exists() else None
    if rot_dst.exists():
        shutil.rmtree(rot_dst)
    rot_dst.mkdir(parents=True)
    for f in rot_src.glob("*.png"):
        shutil.copy2(f, rot_dst / f.name)
    if keep:
        contact.write_bytes(keep)
    print(f"rotations: {len(list(rot_dst.glob('*.png')))} PNGs")

    # animations
    anim_out = char_dir / "animations"
    if anim_out.exists():
        shutil.rmtree(anim_out)

    def find_src(action: str, px: str):
        """canonical <action>/<px> else a UNIQUE <action>-<hash>/<px> fragment."""
        canon = anim_src / action / px
        if canon.is_dir():
            return canon
        frags = [d / px for d in anim_src.glob(f"{action}-*") if (d / px).is_dir()]
        return frags[0] if len(frags) == 1 else None

    for action, cfg in (st.get("animations") or {}).items():
        made = []
        # source (generated) dirs
        for g in cfg["dirs"]:
            px = anchor.get(g)
            if not px or (isinstance(px, str) and px.startswith("mirror")):
                continue
            sdir = find_src(action, px)
            if sdir is None:
                print(f"  !! {action}/{g}<-{px}: missing/ambiguous in download")
                continue
            n = copy_frames(sdir, anim_out / action / g)
            tag = "" if sdir.parent.name == action else f"<-{sdir.parent.name}"
            made.append(f"{g}({n}){tag}")
        # mirror sides
        for mdir, srcg in mirrors.items():
            if srcg in cfg["dirs"]:
                sdir = anim_out / action / srcg
                if sdir.is_dir():
                    n = flip_frames(sdir, anim_out / action / mdir)
                    made.append(f"{mdir}=flip{srcg}({n})")
        print(f"  {action:10} -> {made}")

    build_review(anim_out, char_dir / "review")
    build_gifs(anim_out, char_dir / "_preview")
    print("DONE. review sheets in", char_dir / "review", "| gifs in", char_dir / "_preview")


if __name__ == "__main__":
    main()
