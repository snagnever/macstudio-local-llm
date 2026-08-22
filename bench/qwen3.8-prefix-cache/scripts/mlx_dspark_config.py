#!/usr/bin/env python3
"""Resolve the fixed mlx-dspark P--S campaign arms without machine paths."""

from __future__ import annotations

import argparse
import copy
import json
import shlex
from pathlib import Path
from typing import Optional


def _snapshot_name(identity: dict[str, str]) -> str:
    return f"{identity['id'].replace('/', '--')}-{identity['revision']}"


def load_arm(path: Path, arm: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if arm not in data.get("arms", {}):
        raise ValueError(f"unknown arm: {arm}")
    profile = copy.deepcopy(data["arms"][arm])
    profile["arm"] = arm
    profile["runtime"] = copy.deepcopy(data["runtime"])
    profile["target"] = copy.deepcopy(data["target"])
    drafter_key = profile.pop("drafter_key")
    profile["drafter_key"] = drafter_key
    profile["drafter"] = copy.deepcopy(data["drafters"][drafter_key]) if drafter_key else None
    if profile["mode"] in {"dspark", "dflash"} and profile["max_draft"] != "auto":
        raise ValueError(f"arm {arm} must use --max-draft auto")
    if profile["mode"] == "baseline" and profile["drafter"] is not None:
        raise ValueError(f"arm {arm} baseline must not configure a drafter")
    return profile


def validate_arm(profile: dict, model_paths: dict[str, Path]) -> None:
    target_path = model_paths.get("target")
    if target_path is None or not target_path.is_dir():
        raise ValueError("target local snapshot directory is required")
    expected_target = _snapshot_name(profile["target"])
    if target_path.name != expected_target:
        raise ValueError(f"target snapshot must be named {expected_target}")
    drafter_key = profile.get("drafter_key")
    if drafter_key is None:
        return
    drafter_path = model_paths.get(drafter_key)
    if drafter_path is None or not drafter_path.is_dir():
        raise ValueError(f"{drafter_key} local draft snapshot directory is required")
    expected_drafter = _snapshot_name(profile["drafter"])
    if drafter_path.name != expected_drafter:
        raise ValueError(f"{drafter_key} snapshot must be named {expected_drafter}")


def build_command(
    profile: dict,
    model_paths: dict[str, Path],
    context_window: Optional[int] = None,
) -> list[str]:
    validate_arm(profile, model_paths)
    runtime = profile["runtime"]
    resolved_context = runtime["context_window"] if context_window is None else context_window
    native_context = profile["target"]["native_context_window"]
    if resolved_context <= 0 or resolved_context > native_context:
        raise ValueError(
            f"context window must be between 1 and target native limit {native_context}"
        )
    command = [
        "mlx-dspark", "serve", "--model", str(model_paths["target"]),
        "--mode", profile["mode"], "--host", runtime["host"],
        "--port", str(runtime["port"]), "--context-window", str(resolved_context),
        "--reasoning-effort", runtime["reasoning_effort"], "--max-batch",
        str(runtime["concurrency"]),
    ]
    if not profile["prefix_cache"]:
        command.append("--no-prefix-cache")
    drafter_key = profile.get("drafter_key")
    if drafter_key:
        command.extend(["--drafter", str(model_paths[drafter_key]), "--max-draft", "auto"])
    return command


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--target-path", type=Path, required=True)
    parser.add_argument("--dspark-path", type=Path)
    parser.add_argument("--dflash-path", type=Path)
    parser.add_argument("--context-window", type=int)
    parser.add_argument("--print-command", action="store_true")
    parser.add_argument("--command-shell", action="store_true")
    args = parser.parse_args()
    profile = load_arm(args.config, args.arm)
    paths = {"target": args.target_path}
    if args.dspark_path is not None:
        paths["dspark"] = args.dspark_path
    if args.dflash_path is not None:
        paths["dflash"] = args.dflash_path
    command = build_command(profile, paths, context_window=args.context_window)
    if args.print_command:
        print(json.dumps(command))
    if args.command_shell:
        print(" ".join(shlex.quote(value) for value in command))


if __name__ == "__main__":
    main()
