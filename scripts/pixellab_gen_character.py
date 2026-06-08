#!/usr/bin/env python3
"""PixelLab v3 character API — low-level building blocks.

This module exposes functions used by `pixellab_batch.py`. It performs
NO polling, NO directory layout decisions, and NO loops — the batch
driver is responsible for orchestration.

Hardcoded defaults (locked by 2026-06-07 process):
  - image_size: 128x128 (PixelLab pads canvas to ~232-248)
  - view: low top-down
  - detail: highly detailed
  - outline: single color black outline
  - template_id: mannequin
  - no_background: True

Auth: pass `token`, set env var PIXELLAB_API_TOKEN, or put
  `{"pixellab_api_token": "..."}` in `scripts/config.json`.
"""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path
from urllib.parse import urljoin

import requests

API_BASE = "https://api.pixellab.ai/v2/"

DEFAULT_SIZE = 128
DEFAULT_VIEW = "low top-down"
DEFAULT_DETAIL = "highly detailed"
DEFAULT_OUTLINE = "single color black outline"
DEFAULT_TEMPLATE = "mannequin"

ALL_DIRECTIONS: tuple[str, ...] = (
    "south", "south-east", "east", "north-east",
    "north", "north-west", "west", "south-west",
)


class PixelLabError(RuntimeError):
    pass


def _auth_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_token(token: str | None = None) -> str:
    t = token or os.environ.get("PIXELLAB_API_TOKEN")
    if not t:
        cfg = Path(__file__).resolve().parent / "config.json"
        if cfg.exists():
            try:
                with cfg.open() as f:
                    t = (json.load(f) or {}).get("pixellab_api_token") or None
            except (json.JSONDecodeError, OSError):
                pass
    if not t:
        raise PixelLabError(
            "Missing PixelLab token: set PIXELLAB_API_TOKEN env var "
            "or put 'pixellab_api_token' in scripts/config.json"
        )
    return t


def create_character_v3(
    token: str,
    *,
    description: str,
    name: str,
    seed: int | None = None,
) -> dict:
    """POST /create-character-v3 — returns immediately with character_id + job_id.

    Caller is responsible for polling background-jobs/<job_id>.
    """
    payload: dict = {
        "description": description,
        "name": name,
        "image_size": {"width": DEFAULT_SIZE, "height": DEFAULT_SIZE},
        "view": DEFAULT_VIEW,
        "template_id": DEFAULT_TEMPLATE,
        "detail": DEFAULT_DETAIL,
        "outline": DEFAULT_OUTLINE,
        "no_background": True,
        "enhance_prompt": False,
    }
    if seed is not None:
        payload["seed"] = seed

    url = urljoin(API_BASE, "create-character-v3")
    resp = requests.post(url, headers=_auth_headers(token), json=payload, timeout=60)
    if resp.status_code != 200:
        raise PixelLabError(f"create-character-v3 failed: {resp.status_code} {resp.text}")
    return resp.json()


def create_animation_v3(
    token: str,
    *,
    character_id: str,
    action_name: str,
    action_description: str,
    directions: list[str] | None = None,
    frame_count: int = 8,
    seed: int | None = None,
) -> dict:
    """POST /characters/animations — V3 mode, one job per direction.

    `directions` defaults to all 8. Returns dict with `background_job_ids`
    (list, one per direction) and `directions` (matching list).
    """
    dirs = list(directions) if directions is not None else list(ALL_DIRECTIONS)
    if frame_count < 4 or frame_count > 16 or frame_count % 2:
        raise PixelLabError(f"frame_count must be even 4-16, got {frame_count}")

    payload: dict = {
        "character_id": character_id,
        "animation_name": action_name,
        "action_description": action_description,
        "mode": "v3",
        "frame_count": frame_count,
        "directions": dirs,
        "async_mode": True,
    }
    if seed is not None:
        payload["seed"] = seed

    url = urljoin(API_BASE, "characters/animations")
    resp = requests.post(url, headers=_auth_headers(token), json=payload, timeout=60)
    if resp.status_code != 200:
        raise PixelLabError(f"characters/animations failed: {resp.status_code} {resp.text}")
    return resp.json()


def get_job(token: str, job_id: str) -> dict:
    """Single GET /background-jobs/{id}. No polling — caller loops."""
    url = urljoin(API_BASE, f"background-jobs/{job_id}")
    resp = requests.get(url, headers=_auth_headers(token), timeout=30)
    if resp.status_code != 200:
        raise PixelLabError(f"background-jobs/{job_id} failed: {resp.status_code} {resp.text}")
    return resp.json()


def get_character(token: str, character_id: str) -> dict:
    url = urljoin(API_BASE, f"characters/{character_id}")
    resp = requests.get(url, headers=_auth_headers(token), timeout=30)
    if resp.status_code != 200:
        raise PixelLabError(f"characters/{character_id} failed: {resp.status_code} {resp.text}")
    return resp.json()


def download_character_zip(token: str, character_id: str, dest: Path) -> None:
    """Download full character snapshot (rotations + ALL animations) as zip.

    Safe to call repeatedly — always returns the latest state.
    """
    url = urljoin(API_BASE, f"characters/{character_id}/zip")
    with requests.get(
        url, headers={"Authorization": f"Bearer {token}"}, stream=True, timeout=180
    ) as resp:
        if resp.status_code != 200:
            raise PixelLabError(f"zip download failed: {resp.status_code} {resp.text}")
        dest.write_bytes(resp.content)


def unzip(zip_path: Path, dest_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)


def get_balance(token: str) -> dict:
    url = urljoin(API_BASE, "balance")
    resp = requests.get(url, headers=_auth_headers(token), timeout=15)
    if resp.status_code != 200:
        raise PixelLabError(f"balance failed: {resp.status_code} {resp.text}")
    return resp.json()
