#!/usr/bin/env python3
"""Batch driver for PixelLab character generation.

Reads `scripts/prompts/characters.yaml` (truth = `docs/pixellab/character-prompt-v3.md`,
manually kept in sync). For every character/action that is not yet `completed`:

  1. POST to PixelLab (rotation first; animations only after rotation done).
  2. Poll the background job every 60s.
  3. Download the full character ZIP (snapshot of rotations + all animations)
     and extract into `art/undecided_art/<CharacterName>/`.
  4. Update `character_id` / per-action `status` back into the YAML.

Skip logic:
  - `character_id` empty           → create rotation
  - rotation.status != 'completed' → poll/finish rotation
  - any action.status != 'completed' → create animation (one job per direction)
  - pass `--force <action>` to regenerate a completed action

Usage:
    # auth (one of):
    export PIXELLAB_API_TOKEN=sk_...
    #   or put {"pixellab_api_token": "..."} in scripts/config.json

    python pixellab_batch.py
    python pixellab_batch.py --only LuLi SuYao
    python pixellab_batch.py --only LuLi --force attack
    python pixellab_batch.py --rotation-only      # do not start animations
    python pixellab_batch.py --dry-run            # print plan, no API calls
    python pixellab_batch.py \
        --yaml scripts/prompts/characters_tacticsogre.yaml \
        --out  art/undecided_art_tacticsogre

Each run writes a JSON log to `scripts/logs/run_<date>_<run_id>.json`
with initial/final balance, planned actions, per-action results, durations,
and any fatal error.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from pixellab_gen_character import (
    ALL_DIRECTIONS,
    PixelLabError,
    create_animation_v3,
    create_character_v3,
    download_character_zip,
    get_balance,
    get_job,
    get_token,
    unzip,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_YAML_PATH = REPO_ROOT / "scripts" / "prompts" / "characters.yaml"
DEFAULT_OUT_ROOT = REPO_ROOT / "art" / "undecided_art"
LOGS_DIR = REPO_ROOT / "scripts" / "logs"

# Set in main() after parsing CLI args. All downstream helpers read these.
YAML_PATH: Path = DEFAULT_YAML_PATH
OUT_ROOT: Path = DEFAULT_OUT_ROOT

POLL_INTERVAL_SEC = 60
POLL_TIMEOUT_SEC = 30 * 60

ACTIONS_ORDER = ("rotation", "idle", "walking", "react", "attack")


class RunLogger:
    """Collects per-run telemetry and writes a JSON log on finalize().

    Schema (top-level):
      run_id, started_at, finished_at, duration_sec, args, yaml_path,
      balance_initial, balance_final, plan[], results[],
      success_count, failed_count, skipped_count, fatal_error
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.run_id = uuid.uuid4().hex[:8]
        self.started_at = datetime.now()
        self.started_monotonic = time.monotonic()
        self.args = vars(args)
        self.balance_initial: Any = None
        self.balance_final: Any = None
        self.plan: list[dict] = []
        self.results: list[dict] = []
        self.fatal_error: str | None = None
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        date_str = self.started_at.strftime("%Y%m%d_%H%M%S")
        self.log_path = LOGS_DIR / f"run_{date_str}_{self.run_id}.json"
        print(f"Run id: {self.run_id}  log: {self.log_path.relative_to(REPO_ROOT)}")

    def snapshot_plan(self, characters: list[dict], rotation_only: bool, force: list[str]) -> None:
        for char in characters:
            actions = char.get("actions", {}) or {}
            for action_name in ACTIONS_ORDER:
                if action_name not in actions:
                    continue
                if rotation_only and action_name != "rotation":
                    continue
                status = actions[action_name].get("status", "new")
                forced = action_name in force
                will_run = forced or status != "completed"
                # rotation gating: if no character_id, rotation runs
                if action_name == "rotation" and not char.get("character_id"):
                    will_run = True
                self.plan.append({
                    "character": char["name"],
                    "action": action_name,
                    "before_status": status,
                    "forced": forced,
                    "will_run": will_run,
                    "frame_count": actions[action_name].get("frame_count"),
                })

    def record(
        self,
        character: str,
        action: str,
        outcome: str,
        *,
        character_id: str | None = None,
        job_ids: list[str] | None = None,
        output_dir: str | None = None,
        duration_sec: float | None = None,
        error: str | None = None,
        note: str | None = None,
    ) -> None:
        self.results.append({
            "character": character,
            "action": action,
            "outcome": outcome,  # success | failed | skipped | partial | dry-run
            "character_id": character_id,
            "job_ids": job_ids,
            "output_dir": output_dir,
            "duration_sec": round(duration_sec, 2) if duration_sec is not None else None,
            "error": error,
            "note": note,
            "at": datetime.now().isoformat(timespec="seconds"),
        })

    def finalize(self) -> None:
        success = sum(1 for r in self.results if r["outcome"] == "success")
        failed = sum(1 for r in self.results if r["outcome"] in ("failed", "partial"))
        skipped = sum(1 for r in self.results if r["outcome"] == "skipped")
        finished = datetime.now()
        try:
            yaml_rel = str(YAML_PATH.relative_to(REPO_ROOT))
        except ValueError:
            yaml_rel = str(YAML_PATH)
        try:
            out_rel = str(OUT_ROOT.relative_to(REPO_ROOT))
        except ValueError:
            out_rel = str(OUT_ROOT)
        payload = {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "finished_at": finished.isoformat(timespec="seconds"),
            "duration_sec": round(time.monotonic() - self.started_monotonic, 2),
            "args": self.args,
            "yaml_path": yaml_rel,
            "output_root": out_rel,
            "balance_initial": self.balance_initial,
            "balance_final": self.balance_final,
            "plan": self.plan,
            "results": self.results,
            "success_count": success,
            "failed_count": failed,
            "skipped_count": skipped,
            "fatal_error": self.fatal_error,
        }
        with self.log_path.open("w") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(
            f"\nRun summary: success={success} failed={failed} skipped={skipped} "
            f"duration={payload['duration_sec']}s"
        )
        print(f"Log written: {self.log_path.relative_to(REPO_ROOT)}")


# Module-level logger handle, set in main()
_LOGGER: RunLogger | None = None


def load_yaml() -> dict:
    if not YAML_PATH.exists():
        raise SystemExit(f"Missing config: {YAML_PATH}")
    with YAML_PATH.open() as f:
        return yaml.safe_load(f) or {}


def save_yaml(data: dict) -> None:
    tmp = YAML_PATH.with_suffix(".yaml.tmp")
    with tmp.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=1000)
    tmp.replace(YAML_PATH)


def poll_until_done(token: str, job_id: str, label: str) -> dict:
    """Block until job is completed/failed. Polls every POLL_INTERVAL_SEC."""
    deadline = time.time() + POLL_TIMEOUT_SEC
    last: dict = {}
    while time.time() < deadline:
        last = get_job(token, job_id)
        status = last.get("status", "unknown")
        print(f"      [poll {label}] status={status}")
        if status in ("completed", "failed"):
            return last
        time.sleep(POLL_INTERVAL_SEC)
    raise PixelLabError(f"Timeout waiting for job {job_id} ({label})")


def char_out_dir(name: str) -> Path:
    d = OUT_ROOT / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def download_and_extract(token: str, character_id: str, name: str) -> None:
    out_dir = char_out_dir(name)
    zip_path = out_dir / "character.zip"
    print(f"    download ZIP -> {zip_path.relative_to(REPO_ROOT)}")
    download_character_zip(token, character_id, zip_path)
    unzip(zip_path, out_dir)


def do_rotation(token: str, char_cfg: dict, dry_run: bool) -> bool:
    """Returns True if any state changed."""
    name = char_cfg["name"]
    rotation = char_cfg["actions"]["rotation"]
    if rotation.get("status") == "completed" and char_cfg.get("character_id"):
        if _LOGGER:
            _LOGGER.record(name, "rotation", "skipped",
                           character_id=char_cfg.get("character_id"),
                           note="already completed")
        return False

    print(f"  [rotation] {name}")
    if dry_run:
        print(f"    DRY: would POST /create-character-v3")
        if _LOGGER:
            _LOGGER.record(name, "rotation", "dry-run")
        return False

    t0 = time.monotonic()
    try:
        if not char_cfg.get("character_id"):
            # Create new character
            resp = create_character_v3(
                token,
                description=rotation["prompt"],
                name=name,
                seed=char_cfg.get("seed"),
            )
            char_cfg["character_id"] = resp["character_id"]
            rotation["job_id"] = resp["background_job_id"]
            rotation["status"] = "processing"
            save_yaml_now()  # checkpoint
            print(f"    created character_id={resp['character_id']}")

        job_id = rotation.get("job_id")
        if job_id and rotation.get("status") != "completed":
            final = poll_until_done(token, job_id, f"{name}/rotation")
            if final.get("status") != "completed":
                rotation["status"] = "failed"
                rotation["last_error"] = str(final.get("last_response"))[:500]
                save_yaml_now()
                raise PixelLabError(f"rotation failed for {name}")
            rotation["status"] = "completed"
            rotation.pop("job_id", None)
            download_and_extract(token, char_cfg["character_id"], name)
            save_yaml_now()
    except Exception as e:
        if _LOGGER:
            _LOGGER.record(name, "rotation", "failed",
                           character_id=char_cfg.get("character_id"),
                           duration_sec=time.monotonic() - t0,
                           error=str(e))
        raise
    if _LOGGER:
        _LOGGER.record(name, "rotation", "success",
                       character_id=char_cfg.get("character_id"),
                       output_dir=str((OUT_ROOT / name).relative_to(REPO_ROOT)),
                       duration_sec=time.monotonic() - t0)
    return True


def do_animation(
    token: str,
    char_cfg: dict,
    action_name: str,
    force: bool,
    dry_run: bool,
) -> bool:
    name = char_cfg["name"]
    action = char_cfg["actions"][action_name]
    if action.get("status") == "completed" and not force:
        if _LOGGER:
            _LOGGER.record(name, action_name, "skipped",
                           character_id=char_cfg.get("character_id"),
                           note="already completed")
        return False
    if not char_cfg.get("character_id"):
        print(f"  [skip {action_name}] {name}: no character_id yet")
        if _LOGGER:
            _LOGGER.record(name, action_name, "skipped",
                           note="no character_id")
        return False

    print(f"  [{action_name}] {name}")
    if dry_run:
        print(f"    DRY: would POST /characters/animations action={action_name}")
        if _LOGGER:
            _LOGGER.record(name, action_name, "dry-run")
        return False

    t0 = time.monotonic()
    job_ids: list[str] = action.get("job_ids") or []
    try:
        if not job_ids or force:
            resp = create_animation_v3(
                token,
                character_id=char_cfg["character_id"],
                action_name=action_name,
                action_description=action["prompt"],
                directions=list(ALL_DIRECTIONS),
                frame_count=action.get("frame_count", 8),
                seed=char_cfg.get("seed"),
            )
            job_ids = resp.get("background_job_ids", [])
            action["job_ids"] = job_ids
            action["status"] = "processing"
            save_yaml_now()
            print(f"    submitted {len(job_ids)} jobs")

        all_ok = True
        for i, jid in enumerate(job_ids):
            final = poll_until_done(token, jid, f"{name}/{action_name}/{ALL_DIRECTIONS[i] if i < len(ALL_DIRECTIONS) else i}")
            if final.get("status") != "completed":
                all_ok = False
                action.setdefault("failed_jobs", []).append(jid)

        if all_ok:
            action["status"] = "completed"
            action.pop("job_ids", None)
            download_and_extract(token, char_cfg["character_id"], name)
        else:
            action["status"] = "partial"
        save_yaml_now()
    except Exception as e:
        if _LOGGER:
            _LOGGER.record(name, action_name, "failed",
                           character_id=char_cfg.get("character_id"),
                           job_ids=job_ids,
                           duration_sec=time.monotonic() - t0,
                           error=str(e))
        raise

    if _LOGGER:
        outcome = "success" if action.get("status") == "completed" else "partial"
        _LOGGER.record(name, action_name, outcome,
                       character_id=char_cfg.get("character_id"),
                       job_ids=job_ids,
                       output_dir=str((OUT_ROOT / name).relative_to(REPO_ROOT)),
                       duration_sec=time.monotonic() - t0,
                       error=None if outcome == "success" else "some directions failed")
    return True


# Module-level handle for incremental save during long runs
_YAML_DATA: dict = {}


def save_yaml_now() -> None:
    if _YAML_DATA:
        save_yaml(_YAML_DATA)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--yaml", default=str(DEFAULT_YAML_PATH),
                   help=f"Path to characters YAML (default: {DEFAULT_YAML_PATH.relative_to(REPO_ROOT)}).")
    p.add_argument("--out", default=str(DEFAULT_OUT_ROOT),
                   help=f"Output root for downloaded character ZIPs (default: {DEFAULT_OUT_ROOT.relative_to(REPO_ROOT)}).")
    p.add_argument("--only", nargs="*", default=None, help="Only process these character names.")
    p.add_argument("--force", nargs="*", default=[], help="Force-regenerate these actions (rotation/idle/walking/react/attack).")
    p.add_argument("--rotation-only", action="store_true", help="Only do rotations; skip animations.")
    p.add_argument("--dry-run", action="store_true", help="Print plan, no API calls.")
    return p.parse_args()


def _resolve(path_str: str) -> Path:
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    return p


def main() -> None:
    args = parse_args()
    global _YAML_DATA, _LOGGER, YAML_PATH, OUT_ROOT
    YAML_PATH = _resolve(args.yaml)
    OUT_ROOT = _resolve(args.out)
    print(f"YAML:   {YAML_PATH}")
    print(f"Output: {OUT_ROOT}")
    _YAML_DATA = load_yaml()
    characters = _YAML_DATA.get("characters", [])
    if not characters:
        raise SystemExit("No characters in YAML")

    _LOGGER = RunLogger(args)

    token = "" if args.dry_run else get_token()

    if not args.dry_run:
        try:
            bal = get_balance(token)
            print(f"PixelLab balance: {bal}")
            _LOGGER.balance_initial = bal
        except PixelLabError as e:
            print(f"Warning: could not fetch balance: {e}")

    selected = characters
    if args.only:
        selected = [c for c in characters if c["name"] in args.only]
        missing = set(args.only) - {c["name"] for c in selected}
        if missing:
            raise SystemExit(f"Unknown character(s): {missing}")

    _LOGGER.snapshot_plan(selected, args.rotation_only, args.force)

    try:
        for char in selected:
            print(f"\n=== {char['name']} ===")
            try:
                do_rotation(token, char, args.dry_run)
                if args.rotation_only:
                    continue
                for action_name in ACTIONS_ORDER:
                    if action_name == "rotation":
                        continue
                    if action_name not in char.get("actions", {}):
                        continue
                    force = action_name in args.force
                    do_animation(token, char, action_name, force, args.dry_run)
            except PixelLabError as e:
                print(f"  ERROR ({char['name']}): {e}", file=sys.stderr)
                save_yaml_now()
                continue
    except KeyboardInterrupt:
        _LOGGER.fatal_error = "KeyboardInterrupt"
        save_yaml_now()
        print("\nInterrupted by user.", file=sys.stderr)
    except Exception as e:
        _LOGGER.fatal_error = f"{type(e).__name__}: {e}"
        save_yaml_now()
        raise
    finally:
        if not args.dry_run:
            try:
                _LOGGER.balance_final = get_balance(token)
                print(f"PixelLab balance (final): {_LOGGER.balance_final}")
            except PixelLabError as e:
                print(f"Warning: could not fetch final balance: {e}")
        _LOGGER.finalize()

    print("\nDone.")


if __name__ == "__main__":
    main()
