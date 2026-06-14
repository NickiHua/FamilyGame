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

POLL_INTERVAL_SEC = 30
POLL_TIMEOUT_SEC = 30 * 60

# Batch mode: one POST with all 8 directions so the server groups them under a
# single animation_group_id (otherwise the webapp UI shows each direction as
# its own animation row). The v2 character endpoint has no animation_group_id
# / replace_existing param (objects do, characters don't) so per-direction
# retries always create separate UI groups — we minimise that by redoing the
# whole batch when too many failed.
#
# Outcome policy (per-action):
#   8/8 succeeded             -> completed
#   PARTIAL_THRESHOLD..7      -> partial: retry just the missing directions
#                                (each retry adds a separate UI group; cheap)
#   < PARTIAL_THRESHOLD       -> redo the whole batch from scratch up to
#                                MAX_FULL_REDOS times; the previous (bad)
#                                group stays in the UI and must be deleted
#                                manually because no API can remove it.
PARTIAL_THRESHOLD = 6  # >=6 success keeps the batch and patches the rest
MAX_RETRIES_PER_DIRECTION = 2
MAX_FULL_REDOS = 1

# Back-off when the server returns 429 (Tier 1 = max 8 concurrent jobs).
# Long enough to outlast someone else's full generation cycle.
SUBMIT_429_BACKOFF_SEC = 60
SUBMIT_429_MAX_RETRIES = 10

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
                if action_name == "rotation":
                    # Rotation has its own skip rule (in do_rotation): runs if
                    # no character_id, or status != completed.
                    will_run = forced or status != "completed" or not char.get("character_id")
                else:
                    # Animations: only run on 'new' by default, --force overrides.
                    will_run = forced or status == "new"
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


def _poll_classified(token: str, job_id: str, label: str) -> str:
    """Poll one job. Returns 'completed', 'failed', or 'gone'.

    Never raises for transient/expected per-job problems (404 GC, generation
    failure, timeout). Lets the caller decide whether to retry that direction.
    Only fatal errors (e.g. network completely down) bubble up.
    """
    try:
        final = poll_until_done(token, job_id, label)
        return "completed" if final.get("status") == "completed" else "failed"
    except PixelLabError as e:
        msg = str(e)
        if "404" in msg or "not found" in msg.lower():
            print(f"      [poll {label}] job gone (404), will retry")
            return "gone"
        if "Timeout" in msg:
            print(f"      [poll {label}] timed out, will retry")
            return "failed"
        # Unknown PixelLab error: treat as transient failure for this direction
        # rather than killing the whole script.
        print(f"      [poll {label}] error: {e}")
        return "failed"


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


def _submit_and_poll_batch(
    token: str,
    char_cfg: dict,
    action_name: str,
    action: dict,
    directions: list[str],
    label_prefix: str,
) -> list[str]:
    """Submit ONE POST for all `directions`, poll every returned job.

    Returns the list of directions that did NOT come back 'completed' (includes
    directions the server silently dropped from the response). Persists in-flight
    job ids in `action['active_jobs']` (dict direction->jid) and checkpoints
    YAML after every state change for crash safety.
    """
    failed: list[str] = []
    action["status"] = "processing"

    # Back-off retry for rate-limit / concurrent-job-cap (429). Tier 1 allows
    # only 8 concurrent background jobs, so when slots are full we must wait
    # for them to drain rather than counting it as a generation failure.
    resp = None
    for attempt in range(SUBMIT_429_MAX_RETRIES + 1):
        try:
            resp = create_animation_v3(
                token,
                character_id=char_cfg["character_id"],
                action_name=action_name,
                action_description=action["prompt"],
                directions=list(directions),
                frame_count=action.get("frame_count", 8),
                seed=char_cfg.get("seed"),
            )
            break
        except PixelLabError as e:
            msg = str(e)
            if "429" in msg and attempt < SUBMIT_429_MAX_RETRIES:
                print(
                    f"    [{label_prefix}] 429 rate-limit (attempt {attempt + 1}/"
                    f"{SUBMIT_429_MAX_RETRIES + 1}); sleeping {SUBMIT_429_BACKOFF_SEC}s"
                )
                time.sleep(SUBMIT_429_BACKOFF_SEC)
                continue
            print(f"    [{label_prefix}] submit error: {e}")
            return list(directions)
    if resp is None:
        return list(directions)

    returned_dirs = resp.get("directions", []) or []
    jids = resp.get("background_job_ids", []) or []
    pairs: dict[str, str] = {}
    for d, j in zip(returned_dirs, jids):
        pairs[d] = j
    missing = [d for d in directions if d not in pairs]
    if missing:
        print(f"    [{label_prefix}] server returned no job for: {missing}")
        failed.extend(missing)

    for d, jid in pairs.items():
        action.setdefault("active_jobs", {})[d] = jid
    save_yaml_now()
    print(f"    submitted {len(pairs)}/{len(directions)} jobs")

    for d in directions:
        jid = pairs.get(d)
        if not jid:
            continue
        outcome = _poll_classified(token, jid, f"{label_prefix}/{d}")
        if outcome != "completed":
            failed.append(d)
        action.get("active_jobs", {}).pop(d, None)
        save_yaml_now()

    if not action.get("active_jobs"):
        action.pop("active_jobs", None)
    return failed


def do_animation(
    token: str,
    char_cfg: dict,
    action_name: str,
    force: bool,
    dry_run: bool,
) -> bool:
    name = char_cfg["name"]
    action = char_cfg["actions"][action_name]
    status = action.get("status", "new")
    # Default: only run actions in state 'new'. Anything else (completed,
    # partial, processing, failed) is left alone unless --force is given.
    # Rationale: partial/processing may have been manually fixed via PixelLab
    # web UI mirror; re-running would clobber the fix.
    if status != "new" and not force:
        note = {
            "completed": "already completed",
            "partial": "previously partial; pass --force to redo",
            "processing": "left in processing state; pass --force to redo",
            "failed": "previously failed; pass --force to redo",
        }.get(status, f"status={status}; pass --force to redo")
        if _LOGGER:
            _LOGGER.record(name, action_name, "skipped",
                           character_id=char_cfg.get("character_id"),
                           note=note)
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
    label = f"{name}/{action_name}"

    try:
        # Clear stale state from previous runs; we always start fresh because
        # PixelLab GCs background jobs and old job_ids may 404.
        for k in ("job_ids", "active_jobs", "failed_jobs", "failed_directions"):
            action.pop(k, None)

        total_dirs = len(ALL_DIRECTIONS)

        # Phase 1: full-batch submission, with up to MAX_FULL_REDOS redos
        # when too few directions came back successfully.
        failed_dirs: list[str] = []
        for redo in range(MAX_FULL_REDOS + 1):
            attempt_label = label if redo == 0 else f"{label}/redo{redo}"
            failed_dirs = _submit_and_poll_batch(
                token, char_cfg, action_name, action,
                list(ALL_DIRECTIONS), attempt_label,
            )
            success = total_dirs - len(failed_dirs)
            if success >= PARTIAL_THRESHOLD:
                break
            if redo < MAX_FULL_REDOS:
                print(
                    f"    [{label}] only {success}/{total_dirs} succeeded "
                    f"(< {PARTIAL_THRESHOLD}); redoing whole batch "
                    f"(redo {redo + 1}/{MAX_FULL_REDOS}). "
                    f"Previous group remains in UI and must be deleted manually."
                )
            else:
                print(
                    f"    [{label}] only {success}/{total_dirs} succeeded "
                    f"after {MAX_FULL_REDOS} redo(s); patching the rest per-direction."
                )

        # Phase 2: per-direction retries for whatever's still missing.
        # These create separate animation groups in the UI (API limitation).
        for attempt in range(1, MAX_RETRIES_PER_DIRECTION + 1):
            if not failed_dirs:
                break
            print(f"    [{label}] retry {attempt}/{MAX_RETRIES_PER_DIRECTION} for {failed_dirs}")
            failed_dirs = _submit_and_poll_batch(
                token, char_cfg, action_name, action,
                failed_dirs, f"{label}/retry{attempt}",
            )

        # Always grab the latest ZIP — captures whatever did succeed, even if
        # the action ended up partial. Cheap (no extra credits).
        try:
            download_and_extract(token, char_cfg["character_id"], name)
        except PixelLabError as e:
            print(f"    [{label}] WARN: download failed: {e}")

        if failed_dirs:
            action["status"] = "partial"
            action["failed_directions"] = failed_dirs
        else:
            action["status"] = "completed"
            action.pop("failed_directions", None)
        save_yaml_now()
    except Exception as e:
        if _LOGGER:
            _LOGGER.record(name, action_name, "failed",
                           character_id=char_cfg.get("character_id"),
                           duration_sec=time.monotonic() - t0,
                           error=str(e))
        raise

    if _LOGGER:
        outcome = "success" if action.get("status") == "completed" else "partial"
        _LOGGER.record(name, action_name, outcome,
                       character_id=char_cfg.get("character_id"),
                       output_dir=str((OUT_ROOT / name).relative_to(REPO_ROOT)),
                       duration_sec=time.monotonic() - t0,
                       error=None if outcome == "success"
                                  else f"failed_directions={action.get('failed_directions')}")
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
    p.add_argument("--actions", nargs="*", default=None,
                   help="Only consider these animations (e.g. walking attack). Rotation is always evaluated separately.")
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
                    if args.actions and action_name not in args.actions:
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
