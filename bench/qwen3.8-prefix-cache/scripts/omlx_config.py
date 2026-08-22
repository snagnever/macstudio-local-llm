#!/usr/bin/env python3
"""Generate isolated, versioned oMLX state for the Qwen3.8 campaign."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


GLOBAL_SETTINGS_VERSION = "1.0"
MODEL_SETTINGS_VERSION = 1


def load_arm(path: Path, arm: str) -> dict:
    """Load one declared arm and resolve its target model metadata."""
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        declared = data["arms"][arm]
    except KeyError as exc:
        raise ValueError(f"unknown arm: {arm}") from exc

    profile = copy.deepcopy(declared)
    model_key = profile.pop("model_key")
    try:
        profile["model"] = copy.deepcopy(data["models"][model_key])
    except KeyError as exc:
        raise ValueError(f"arm {arm} references unknown model: {model_key}") from exc
    profile["model"]["key"] = model_key
    profile["arm"] = arm
    return profile


def _read_ane_profile(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid ANE tuner profile: {path}") from exc
    if not isinstance(data, dict) or not data:
        raise ValueError(f"invalid ANE tuner profile: {path}")
    invalid_keys = [key for key in data if not key.startswith("qwen35_ane_prefill_")]
    if invalid_keys:
        raise ValueError("ANE tuner profile contains non-ANE settings")
    return data


def validate_arm(profile: dict, model_paths: dict[str, Path]) -> None:
    """Check optional per-arm local inputs before any state is written."""
    draft_key = profile.get("draft_key")
    if draft_key:
        draft_path = model_paths.get(draft_key)
        if draft_path is None or not draft_path.is_dir():
            raise ValueError(f"{draft_key} local draft path is required")

    if profile.get("ane_profile_required"):
        profile_path = model_paths.get("ane_profile")
        if profile_path is None or not profile_path.is_file():
            raise ValueError("ANE tuner profile is required")
        _read_ane_profile(profile_path)


def _resolved_model_settings(profile: dict, model_paths: dict[str, Path]) -> dict:
    """Return the persisted model settings, including local-only inputs."""
    settings = copy.deepcopy(profile["model_settings"])
    draft_key = profile.get("draft_key")
    if draft_key:
        settings["specprefill_draft_model"] = str(model_paths[draft_key])
    if profile.get("ane_profile_required"):
        settings.update(_read_ane_profile(model_paths["ane_profile"]))
        settings["qwen35_ane_prefill_enabled"] = True
    return settings


def write_omlx_state(
    base_path: Path, profile: dict, model_paths: dict[str, Path]
) -> None:
    """Write the oMLX v0.6.3rc2 global and per-model state envelopes."""
    validate_arm(profile, model_paths)
    model_root = model_paths.get("model_root")
    if model_root is None:
        raise ValueError("model_root is required")

    model_settings = _resolved_model_settings(profile, model_paths)

    global_state = {
        "version": GLOBAL_SETTINGS_VERSION,
        "server": {"port": 8000},
        "model": {"model_dirs": [str(model_root)]},
        "cache": {"enabled": profile["cache_enabled"]},
    }
    per_model_state = {
        "version": MODEL_SETTINGS_VERSION,
        "models": {profile["model"]["local_name"]: model_settings},
    }

    base_path.mkdir(parents=True, exist_ok=True)
    (base_path / "settings.json").write_text(
        json.dumps(global_state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (base_path / "model_settings.json").write_text(
        json.dumps(per_model_state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--base-path", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--draft-2b-path", type=Path)
    parser.add_argument("--draft-08b-path", type=Path)
    parser.add_argument("--ane-profile", type=Path)
    parser.add_argument("--print-profile", action="store_true")
    args = parser.parse_args()

    profile = load_arm(args.config, args.arm)
    model_paths = {
        "model_root": args.model_root,
        "draft-2b": args.draft_2b_path,
        "draft-08b": args.draft_08b_path,
        "ane_profile": args.ane_profile,
    }
    model_paths = {key: value for key, value in model_paths.items() if value is not None}
    validate_arm(profile, model_paths)
    write_omlx_state(args.base_path, profile, model_paths)
    if args.print_profile:
        resolved = copy.deepcopy(profile)
        resolved["model_settings"] = _resolved_model_settings(profile, model_paths)
        print(json.dumps(resolved, sort_keys=True))


if __name__ == "__main__":
    main()
