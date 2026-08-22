#!/usr/bin/env python3
"""Generate isolated, versioned oMLX state for the Qwen3.8 campaign."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any


GLOBAL_SETTINGS_VERSION = "1.0"
MODEL_SETTINGS_VERSION = 1
ANE_BOOL_FIELDS = frozenset(
    {
        "qwen35_ane_prefill_enabled",
        "qwen35_ane_prefill_dual_ane",
        "qwen35_ane_prefill_gdn",
        "qwen35_ane_prefill_cpu_enabled",
        "qwen35_ane_prefill_cpu_shared_resource",
    }
)
ANE_INT_RANGES = {
    "qwen35_ane_prefill_sequence_length": (1024, None),
    "qwen35_ane_prefill_max_layers": (1, None),
    "qwen35_ane_prefill_gdn_max_layers": (0, None),
    "qwen35_ane_prefill_cpu_threads": (0, 64),
}
ANE_FLOAT_RANGES = {
    "qwen35_ane_prefill_fraction": (0.05, 0.90),
    "qwen35_ane_prefill_gdn_fraction": (0.05, 0.90),
    "qwen35_ane_prefill_cpu_fraction": (0.0, 0.25),
    "qwen35_ane_prefill_cpu_down_fraction": (0.0, 0.50),
    "qwen35_ane_prefill_cpu_gdn_fraction": (0.0, 0.50),
}
ANE_FIELDS = frozenset(ANE_BOOL_FIELDS | ANE_INT_RANGES.keys() | ANE_FLOAT_RANGES.keys())


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
    invalid_keys = [key for key in data if key not in ANE_FIELDS]
    if invalid_keys:
        raise ValueError("ANE tuner profile contains unknown settings")
    for key, value in data.items():
        if key in ANE_BOOL_FIELDS:
            if not isinstance(value, bool):
                raise ValueError(f"ANE tuner profile {key} must be boolean")
        elif key in ANE_INT_RANGES:
            minimum, maximum = ANE_INT_RANGES[key]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"ANE tuner profile {key} must be an integer")
            if value < minimum or (maximum is not None and value > maximum):
                raise ValueError(f"ANE tuner profile {key} is outside its allowed range")
            if key == "qwen35_ane_prefill_sequence_length" and value % 64:
                raise ValueError("ANE tuner profile sequence length must be a multiple of 64")
        else:
            minimum, maximum = ANE_FLOAT_RANGES[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"ANE tuner profile {key} must be numeric")
            if not math.isfinite(value) or not minimum <= value <= maximum:
                raise ValueError(f"ANE tuner profile {key} is outside its allowed range")
    return data


def _target_model_dir(profile: dict, model_root: Path) -> Path:
    model = profile["model"]
    directory_name = f"{model['repository'].replace('/', '-')}-{model['revision']}"
    return model_root / directory_name


def validate_arm(profile: dict, model_paths: dict[str, Path]) -> None:
    """Check optional per-arm local inputs before any state is written."""
    model_root = model_paths.get("model_root")
    if model_root is None or not model_root.is_dir():
        raise ValueError("model_root local directory is required")
    target_dir = _target_model_dir(profile, model_root)
    if not target_dir.is_dir():
        raise ValueError(f"target model directory is required: {target_dir.name}")

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
    model_root = model_paths["model_root"]
    target_dir = _target_model_dir(profile, model_root)

    model_settings = _resolved_model_settings(profile, model_paths)

    global_state = {
        "version": GLOBAL_SETTINGS_VERSION,
        "server": {"port": 8000},
        "model": {"model_dirs": [str(model_root)]},
        "cache": {"enabled": profile["cache_enabled"]},
    }
    per_model_state = {
        "version": MODEL_SETTINGS_VERSION,
        "models": {target_dir.name: model_settings},
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
