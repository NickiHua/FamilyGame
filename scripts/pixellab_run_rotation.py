"""Run a PixelLab rotation for character(s) in pixellab/character_status.yaml.

STOPS after rotation — this is step ①/② of the pipeline. It generates the
8-direction rotation, downloads it, copies the 8 PNGs into
pixellab/characters/<id>/rotations/, and builds a LABELED contact sheet
(pixellab/characters/<id>/rotations/_contact.png) for the USER to review and
manually anchor S / E / N. It does NOT write the anchor or run animations.

The new character_id is printed (and written to _character_id.txt) — paste it
into the yaml's `character_id:` field by hand (PyYAML would strip the comments).

Usage (repo root, venv):
  .\\.venv\\Scripts\\python.exe scripts\\pixellab_run_rotation.py SuYao
  .\\.venv\\Scripts\\python.exe scripts\\pixellab_run_rotation.py SuYao EmpireCavalier
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

sys.path.insert(0, "scripts")
import pixellab_gen_character as p  # noqa: E402

YAML_PATH = Path("pixellab/character_status.yaml")
POLL_SEC = 20
POLL_MAX = 90


def load_state(char_id: str):
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    for c in data["characters"]:
        if c["id"] == char_id:
            return c, c["states"][0]
    raise SystemExit(f"character {char_id!r} not found in {YAML_PATH}")


def poll(token: str, job: str) -> None:
    for _ in range(POLL_MAX):
        time.sleep(POLL_SEC)
        st = p.get_job(token, job).get("status")
        print("  status:", st)
        if st in ("completed", "failed", "cancelled"):
            if st != "completed":
                raise SystemExit(f"job {st}")
            return
    raise SystemExit("timed out")


def find_rotation_pngs(extract_dir: Path) -> dict[str, Path]:
    """Map pixellab direction name -> PNG in the extracted zip."""
    out: dict[str, Path] = {}
    for d in p.ALL_DIRECTIONS:
        hits = list(extract_dir.rglob(f"{d}.png"))
        if hits:
            out[d] = hits[0]
    return out


def build_contact(pngs: dict[str, Path], out_path: Path) -> None:
    """4x2 labeled sheet in PixelLab's canonical direction order."""
    cell = 160
    label_h = 18
    cols, rows = 4, 2
    sheet = Image.new("RGBA", (cols * cell, rows * (cell + label_h)), (40, 40, 48, 255))
    draw = ImageDraw.Draw(sheet)
    for i, d in enumerate(p.ALL_DIRECTIONS):
        cx = (i % cols) * cell
        cy = (i // cols) * (cell + label_h)
        draw.text((cx + 4, cy + 3), d, fill=(230, 230, 120, 255))
        if d in pngs:
            im = Image.open(pngs[d]).convert("RGBA")
            im.thumbnail((cell - 8, cell - 8))
            ox = cx + (cell - im.width) // 2
            oy = cy + label_h + (cell - im.height) // 2
            sheet.alpha_composite(im, (ox, oy))
    sheet.save(out_path)


def run_one(token: str, char_id: str) -> None:
    char, st = load_state(char_id)
    prompt = st["prompt"]
    print(f"\n=== {char_id} ===  prompt {len(prompt)} chars")
    if len(prompt) > 1000:
        raise SystemExit("prompt too long")

    created = p.create_character_v3(token, description=prompt, name=f"{char_id} (base)")
    cid = created["character_id"]
    job = created.get("background_job_id") or created.get("job_id")
    print("character_id =", cid, "job =", job)
    poll(token, job)

    base = Path(st["rotation"]["dir"]).parent          # pixellab/characters/<id>
    dl = base / "download"
    dl.mkdir(parents=True, exist_ok=True)
    zpath = dl / "character.zip"
    p.download_character_zip(token, cid, zpath)
    p.unzip(zpath, dl)

    pngs = find_rotation_pngs(dl)
    print("rotation PNGs found:", sorted(pngs))
    rot = base / "rotations"
    rot.mkdir(parents=True, exist_ok=True)
    for d, src in pngs.items():
        shutil.copy2(src, rot / f"{d}.png")
    build_contact(pngs, rot / "_contact.png")
    (base / "_character_id.txt").write_text(cid, encoding="utf-8")
    print(f"  -> {rot}  (+ _contact.png)")
    print(f"  PASTE into yaml {char_id}.character_id: {cid}")


def main() -> None:
    ids = sys.argv[1:]
    if not ids:
        raise SystemExit("usage: pixellab_run_rotation.py <CharId> [<CharId> ...]")
    token = Path("pixellabkey.txt").read_text(encoding="utf-8").strip()
    print("balance before:", p.get_balance(token)["subscription"]["generations"])
    for cid in ids:
        run_one(token, cid)
    print("\nbalance after:", p.get_balance(token)["subscription"]["generations"])


if __name__ == "__main__":
    main()
