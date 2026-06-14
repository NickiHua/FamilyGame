# PixelLab Batch Pipeline

End-to-end driver for generating game character sprites (rotations + 4-action
animations) via the [PixelLab v2 API](https://api.pixellab.ai/v2).

## Layout

```
scripts/
├── README.md                    ← you are here
├── config.json                  ← LOCAL ONLY, gitignored, holds API token
├── config.json.example          ← template, safe to commit
├── pixellab_gen_character.py    ← low-level API wrappers (create / poll / zip)
├── pixellab_batch.py            ← orchestrator: reads YAML, runs jobs, writes log
├── prompts/
│   └── characters.yaml          ← source of truth: per-character prompts + state
└── logs/                        ← run logs (auto-created, gitignored)
    └── run_<date>_<run_id>.json
```

Output art is extracted to `art/undecided_art/<CharacterName>/`.

## One-time setup

1. Copy the template and paste your PixelLab API token:

   ```bash
   cp scripts/config.json.example scripts/config.json
   # then edit scripts/config.json
   ```

   The token can alternatively be supplied via the `PIXELLAB_API_TOKEN` env
   variable (env var wins over `config.json`).

2. Install Python deps (only `pyyaml` and `requests` are needed beyond stdlib).

## Running

All commands assume CWD = `FamilyGame/`.

```bash
# Plan-only, no API calls — print what WOULD be done
python scripts/pixellab_batch.py --dry-run

# Full pipeline for every character: rotation first, then 4 animations each
python scripts/pixellab_batch.py

# Limit to specific characters
python scripts/pixellab_batch.py --only LuLi SuYao

# Force-regenerate a specific action (overwrites completed state)
python scripts/pixellab_batch.py --only LuLi --force attack

# Generate rotations only; skip animations
python scripts/pixellab_batch.py --rotation-only
```

Long runs are safe to background:

```bash
nohup python -u scripts/pixellab_batch.py > /tmp/pixellab.log 2>&1 &
```

The YAML is checkpointed after every API state change, so killing and
re-running picks up where the previous run left off.

## Run logs

Every invocation writes `scripts/logs/run_<YYYYMMDD_HHMMSS>_<8charid>.json`
containing:

| field              | meaning                                                  |
| ------------------ | -------------------------------------------------------- |
| `run_id`           | 8-char unique id, also in the filename                   |
| `started_at`       | ISO timestamp                                            |
| `finished_at`      | ISO timestamp                                            |
| `duration_sec`     | wall time of the whole run                               |
| `args`             | CLI arguments as parsed                                  |
| `balance_initial`  | PixelLab credit balance before the run                   |
| `balance_final`    | PixelLab credit balance after the run                    |
| `plan[]`           | snapshot of what was planned (char / action / before)    |
| `results[]`        | one entry per attempted action with outcome + duration   |
| `success_count`    | actions that completed                                   |
| `failed_count`     | actions that failed or returned partial                  |
| `skipped_count`    | actions skipped because already completed                |
| `fatal_error`      | uncaught exception or `KeyboardInterrupt`, else `null`   |

Each `results[]` entry:

```jsonc
{
  "character": "LuLi",
  "action": "attack",
  "outcome": "success",          // success | failed | partial | skipped | dry-run
  "character_id": "e466...",
  "job_ids": ["...", "..."],
  "output_dir": "art/undecided_art/LuLi",
  "duration_sec": 312.4,
  "error": null,
  "note": null,
  "at": "2026-06-07T21:30:11"
}
```

## State machine (YAML)

`scripts/prompts/characters.yaml` is updated in place after every state
transition. Per-action `status` values:

- `new`        — never submitted; will be picked up by a normal run
- `processing` — in-flight, polling in progress (intermediate / crash state)
- `completed`  — finished, art downloaded; skipped by default
- `partial`    — some directions failed after retries; skipped by default
- `failed`     — fatal error; skipped by default

**Default skip rule (animations):** only `status: new` is processed. Anything
else is left alone so manual mirror fixes in the PixelLab web UI are not
clobbered. Use `--force <action>` to redo, or hand-edit the YAML.

To redo an already-completed rotation: set `character_id: ''` and the rotation
`status: new` in YAML, then rerun. The script will pre-clean the output
directory before extracting the new ZIP.

## Per-action robustness (animations only)

Each animation submission runs through three phases automatically:

1. **Initial submit** — POST one job per direction (8 total), poll each.
2. **Per-direction retry** — for any direction that returns `failed`,
   `404 Job not found`, or polling timeout, resubmit JUST that direction
   up to `MAX_RETRIES_PER_DIRECTION` (default 2) times.
3. **Nuke-and-redo** — if anything is still failing, throw away the whole
   animation and resubmit all 8 directions fresh once
   (`ENABLE_NUKE_FALLBACK`, default on).

After all that, the latest character ZIP is always downloaded (even on
partial), so locally you always have whatever did succeed. The action is
then marked `completed` or `partial`; partial actions record the leftover
`failed_directions` in YAML for inspection.

A single per-direction error (404, timeout, generation failure) no longer
aborts the whole character — only fatal submit-side errors do.

## Notes / known quirks

- ZIPs from PixelLab are extracted as-is. If a character name collides with an
  existing one in your PixelLab account, the inner folder will be named
  `<character_id[:8]>` instead of the display name. This does not affect any
  downstream code (`metadata.json` still carries the correct name).
- The PixelLab balance read in `balance_initial` / `balance_final` lives under
  `subscription.generations` in the API response; the JSON in the log captures
  the full response so you can see USD credits separately.
