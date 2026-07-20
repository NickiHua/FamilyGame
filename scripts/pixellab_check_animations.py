"""Check that a character's DOWNLOAD has every REQUIRED animation direction.

Pipeline step (after pull, before organize): the yaml is the source of truth.
For each animation it lists `dirs` = the GAME directions that must be GENERATED
(the mirror side is made in post, so it is NOT required in the download). Each
required game dir is mapped through `anchor` to the pixellab VISUAL frame name,
and we check the download's animations/<action>/<pixellab_dir>/ exists with the
right frame count (frame_count + 1, because PixelLab prepends frame_000).

Usage (repo root, venv):
  .\\.venv\\Scripts\\python.exe scripts\\pixellab_check_animations.py EmpireCaptain
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

YAML_PATH = Path("pixellab/character_status.yaml")


def load_state(char_id: str):
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    for c in data["characters"]:
        if c["id"] == char_id:
            return c["states"][0]
    raise SystemExit(f"character {char_id!r} not found")


def required_px_dirs(game_dirs, anchor):
    """game dir -> pixellab dir; skip mirror-sourced (not required in download)."""
    out = []
    for g in game_dirs:
        a = anchor.get(g)
        if isinstance(a, str) and a.startswith("mirror"):
            continue
        if not a:
            out.append((g, None))       # anchor slot empty
        else:
            out.append((g, a))
    return out


def find_dir(anim_root, action, px):
    """(folder, source_name). Prefer canonical <action>/<px>; else a UNIQUE
    <action>-<hash>/<px> fragment. (None,'AMBIGUOUS'|None) if not found."""
    canon = anim_root / action / px
    if canon.is_dir():
        return canon, action
    frags = [d / px for d in anim_root.glob(f"{action}-*") if (d / px).is_dir()]
    if len(frags) == 1:
        return frags[0], frags[0].parent.name
    if len(frags) > 1:
        return None, "AMBIGUOUS"
    return None, None


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: pixellab_check_animations.py <CharId>")
    char_id = sys.argv[1]
    st = load_state(char_id)
    anchor = st["anchor"]
    char_dir = Path("pixellab/characters") / char_id.lower()
    dl = char_dir / "download"
    anim_roots = list(dl.rglob("animations"))
    if not anim_roots:
        raise SystemExit(f"no download/animations found under {dl} (pull first)")
    anim_root = anim_roots[0]

    print(f"=== {char_id} animation check (anchor {anchor}) ===")
    all_ok = True
    for action, cfg in (st.get("animations") or {}).items():
        want = cfg.get("frame_count", 8) + 1          # +1 for frame_000
        pairs = required_px_dirs(cfg["dirs"], anchor)
        problems, notes = [], []
        for g, px in pairs:
            if px is None:
                problems.append(f"{g}: anchor slot EMPTY")
                continue
            fdir, src = find_dir(anim_root, action, px)
            if fdir is None:
                extra = " (AMBIGUOUS fragments)" if src == "AMBIGUOUS" else ""
                problems.append(f"{g}<-{px}: MISSING{extra}")
                continue
            n = len(list(fdir.glob("*.png")))
            if n != want:
                problems.append(f"{g}<-{px}: {n} frames (want {want})")
            elif src != action:
                notes.append(f"{g}<-{px} via {src}")
        need = " ".join(f"{g}<-{px}" for g, px in pairs)
        if problems:
            all_ok = False
            print(f"  [{action:10}] NEED {need}")
            for pr in problems:
                print(f"       !! {pr}")
        else:
            extra = ("  [" + "; ".join(notes) + "]") if notes else ""
            print(f"  [{action:10}] OK   {need}{extra}")

    # extras present in download but not tracked in yaml
    tracked = set(st.get("animations") or {})
    present = sorted(d.name for d in anim_root.iterdir() if d.is_dir())
    extra = [a for a in present if a not in tracked]
    if extra:
        print(f"  (untracked extras in download, not required: {extra})")
    print("RESULT:", "ALL REQUIRED PRESENT" if all_ok else "GAPS FOUND (see above)")


if __name__ == "__main__":
    main()
