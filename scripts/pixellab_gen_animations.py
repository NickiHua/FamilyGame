"""Generate + save PixelLab animations from pixellab/character_status.yaml.

Frames are pulled DIRECTLY from each job's result (last_response.images,
rgba_bytes) — NOT from the character zip. The zip accumulates every historical
regen as walk / walk-<hash> folders with no reliable way to tell which is newest;
the per-job images are always exactly the generation we just launched.

Each job returns 9 images: frame_000 = the rotation start frame (idle rest pose
PixelLab always prepends), frame_001..008 = the F1..F8 we described. So prompts
should NOT waste F1 on idle.

W is produced by mirroring E (flipX). Only the animations passed via --actions
are regenerated; others already on disk are left untouched.

Usage (repo root, venv):
  .\\.venv\\Scripts\\python.exe scripts\\pixellab_gen_animations.py EmpireCaptain
  ...python.exe scripts\\pixellab_gen_animations.py EmpireCaptain --actions walk
  ...python.exe scripts\\pixellab_gen_animations.py EmpireCaptain --actions walk --only-dirs S
"""
from __future__ import annotations

import argparse
import base64
import shutil
import sys
import time
from pathlib import Path

import yaml
from PIL import Image

sys.path.insert(0, "scripts")
import pixellab_gen_character as p  # noqa: E402

YAML_PATH = Path("pixellab/character_status.yaml")
POLL_SEC = 20
POLL_MAX = 90


def load_char(char_id: str):
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    for c in data["characters"]:
        if c["id"] == char_id:
            return c, c["states"][0]
    raise SystemExit(f"character {char_id!r} not found in {YAML_PATH}")


def resolve_dirs(game_dirs, anchor):
    """game dir -> (game dir, pixellab dir). Skips W (produced by mirror)."""
    out = []
    for g in game_dirs:
        a = anchor[g]
        if isinstance(a, str) and a.startswith("mirror"):
            continue
        out.append((g, a))
    return out


def get_job_retry(token, jid):
    for _ in range(5):
        try:
            return p.get_job(token, jid)
        except p.PixelLabError as e:
            print(f"      transient poll error, retry: {str(e)[:70]}")
            time.sleep(6)
    return p.get_job(token, jid)  # final attempt, let it raise


def save_job_images(job, out_dir: Path) -> int:
    imgs = job["last_response"]["images"]
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for i, im in enumerate(imgs):
        w, h = im["width"], im["height"]
        data = base64.b64decode(im["base64"])
        Image.frombytes("RGBA", (w, h), data).save(out_dir / f"frame_{i:03d}.png")
    return len(imgs)


def mirror_sides(anim_out: Path, action: str, cfg_dirs: list, anchor: dict) -> None:
    """For each anchor `X: mirror:Y`, if Y was generated this action, flip Y->X."""
    for x, val in anchor.items():
        if not (isinstance(val, str) and val.startswith("mirror:")):
            continue
        y = val.split(":", 1)[1]
        if y not in cfg_dirs:
            continue
        src = anim_out / action / y
        if not src.is_dir():
            continue
        dst = anim_out / action / x
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        frames = sorted(src.glob("*.png"))
        for f in frames:
            Image.open(f).transpose(Image.FLIP_LEFT_RIGHT).save(dst / f.name)
        print(f"    {action}/{x}: mirrored from {y} ({len(frames)} frames)")


def generate(token, state, anchor, char_dir: Path,
             only=None, only_dirs=None, submit_only=False) -> None:
    """ONE create call per ACTION (all its source dirs at once). Partial failures
    are NOT retried (user always reviews manually) — completed dirs are saved,
    failed/timed-out dirs are just skipped with a warning."""
    cid = state["character_id"]
    anim_out = char_dir / "animations"
    for action, cfg in state["animations"].items():
        if only and action not in only:
            continue
        pairs = resolve_dirs(cfg["dirs"], anchor)
        if only_dirs:
            pairs = [(g, px) for g, px in pairs if g in only_dirs]
        if not pairs:
            continue
        if not submit_only and (anim_out / action).exists():
            shutil.rmtree(anim_out / action)   # drop stale dirs from old schemes
        px_to_game = {px: g for g, px in pairs}
        px_dirs = [px for _, px in pairs]
        print(f"  [{action}] one call, dirs={px_dirs} (game {[g for g, _ in pairs]})")
        resp = p.create_animation_v3(
            token, character_id=cid, action_name=action,
            action_description=cfg["prompt"], directions=px_dirs,
            frame_count=cfg.get("frame_count", 8),
        )
        rdirs = resp.get("directions", []) or []
        jids = resp.get("background_job_ids", []) or []
        pending = dict(zip(rdirs, jids))
        if submit_only:
            for d, j in pending.items():
                print(f"    SUBMITTED {action}/{d} job={j}")
            continue
        done_dirs = []
        for _ in range(POLL_MAX):
            if not pending:
                break
            time.sleep(POLL_SEC)
            for px in list(pending):
                job = get_job_retry(token, pending[px])
                st = job.get("status")
                print(f"    [{action}/{px}] {st}")
                if st == "completed":
                    g = px_to_game[px]
                    n = save_job_images(job, anim_out / action / g)
                    print(f"    {action}/{g}<-{px}: saved {n} frames")
                    done_dirs.append(g)
                    pending.pop(px)
                elif st in ("failed", "cancelled"):
                    print(f"    !! {action}/{px} {st} — NOT retrying (manual review)")
                    pending.pop(px)
        if pending:
            print(f"    !! {action}: timed out {list(pending)} — skipped, no retry")
        # mirror only the source dirs that actually succeeded
        mirror_sides(anim_out, action, done_dirs, anchor)


def build_gifs(char_dir: Path) -> None:
    anim_out = char_dir / "animations"
    prev = char_dir / "_preview"
    prev.mkdir(exist_ok=True)
    for dir_path in sorted(anim_out.rglob("*")):
        if not dir_path.is_dir() or "_backup" in dir_path.parts:
            continue
        frames = sorted(dir_path.glob("*.png"))
        if len(frames) < 2:
            continue
        imgs = [Image.open(f).convert("RGBA") for f in frames]  # include frame_000 (start)
        w = max(i.width for i in imgs)
        h = max(i.height for i in imgs)
        canvas = []
        for im in imgs:
            bg = Image.new("RGBA", (w, h), (40, 40, 48, 255))
            bg.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
            canvas.append(bg.convert("P", palette=Image.ADAPTIVE))
        action = dir_path.parent.name
        gd = dir_path.name
        out = prev / f"{action}_{gd}.gif"
        canvas[0].save(out, save_all=True, append_images=canvas[1:],
                       duration=110, loop=0, disposal=2)
        print(f"    gif {out.name} ({len(imgs)} frames)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("char_id")
    ap.add_argument("--actions", nargs="+", default=None)
    ap.add_argument("--only-dirs", nargs="+", default=None)
    ap.add_argument("--gifs-only", action="store_true")
    ap.add_argument("--submit-only", action="store_true",
                    help="POST the animation request(s) and exit; no poll/download")
    args = ap.parse_args()

    char, state = load_char(args.char_id)
    anchor = state["anchor"]
    char_dir = Path("pixellab/characters") / args.char_id.lower()
    token = Path("pixellabkey.txt").read_text(encoding="utf-8").strip()

    print(f"char={args.char_id} cid={state['character_id']}")
    if args.submit_only:
        print("balance:", p.get_balance(token)["subscription"]["generations"])
        generate(token, state, anchor, char_dir,
                 only=args.actions, only_dirs=args.only_dirs, submit_only=True)
        print("submitted; review on the PixelLab web page, pull later.")
        return
    if not args.gifs_only:
        print("balance:", p.get_balance(token)["subscription"]["generations"])
        generate(token, state, anchor, char_dir,
                 only=args.actions, only_dirs=args.only_dirs)
        print("balance after:", p.get_balance(token)["subscription"]["generations"])
    build_gifs(char_dir)
    print("DONE. preview gifs in", char_dir / "_preview")


if __name__ == "__main__":
    main()
