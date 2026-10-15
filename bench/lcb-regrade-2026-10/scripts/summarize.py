#!/usr/bin/env python3
"""Merge regrade_all.py verdicts per model run and print original vs regraded scores.

Published scores combine a full run with later partial reruns of the same questions
(for example truncation reruns at a larger context). This script groups files by the
GROUPS table below, keeps the latest answer per question id (by row timestamp), and
counts passes before and after the regrade.

usage: summarize.py VERDICTS.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter

# group label -> substrings of the file path that belong to it
GROUPS = {
    "agents-a1-xl (MLX)": ["livecodebench_agents-a1-xl-mlx_"],
    "deepseek-v4-flash 2bit-DQ (MLX)": ["DeepSeek-V4-Flash-2bit-DQ"],
    "deepseek-v4-flash IQ2_XS (GGUF, partial)": ["deepseek-v4-flash-iq2xs"],
    "gemma-4-26b-a4b @4bit": ["gemma-4-26b-a4b-it-mlx@4bit"],
    "gemma-4-26b-a4b @6bit": ["gemma-4-26b-a4b-it-mlx@6bit"],
    "gemma-4-31b": ["gemma-4-31b-it-mlx"],
    "gemma-4-e4b": ["gemma-4-e4b-it-mlx"],
    "minimax-m2.5 (MLX, aborted)": ["livecodebench_minimax-m2.5_2026"],
    "minimax-m2.5 Q3_K_S (GGUF)": ["unsloth_minimax-m2.5"],
    "qwen3.6-27b": ["livecodebench_qwen3.6-27b_"],
    "qwen3.6-35b-a3b @6bit": ["qwen3.6-35b-a3b@6bit"],
    "qwen3-coder-next": ["qwen_qwen3-coder-next"],
    "swift15 A/B t0 n2": ["ab/t0/n2/"],
    "swift15 A/B t0 w1": ["ab/t0/w1/"],
    "swift15 A/B t1 n2": ["ab/t1/n2/"],
    "swift15 A/B t1 w1": ["ab/t1/w1/"],
}


def group_of(path: str) -> str | None:
    if "/.archived_failed_" in path:
        return None
    for label, keys in GROUPS.items():
        if any(k in path for k in keys):
            return label
    return None


def main(argv: list[str]) -> int:
    report = json.load(open(argv[1]))
    merged: dict[str, dict[str, dict]] = {}
    ungrouped = []
    for path, verdicts in report.items():
        label = group_of(path)
        if label is None:
            ungrouped.append(path)
            continue
        latest = merged.setdefault(label, {})
        for v in verdicts:
            prev = latest.get(v["lcb_question_id"])
            if prev is None or (v.get("timestamp") or "") >= (prev.get("timestamp") or ""):
                latest[v["lcb_question_id"]] = v
    print("| run | questions | original | regraded | to pass | to fail | causes of the change |")
    print("|---|---:|---:|---:|---:|---:|---|")
    for label in GROUPS:
        if label not in merged:
            continue
        vs = list(merged[label].values())
        n = len(vs)
        orig = sum(v["original"] for v in vs)
        new = sum(v["regraded"] for v in vs)
        up = [v for v in vs if v["regraded"] and not v["original"]]
        down = sum(1 for v in vs if v["original"] and not v["regraded"])
        causes = Counter("Errno 7" if "Argument list too long" in (v["original_reason"] or "")
                         else "NameError" if "NameError" in (v["original_reason"] or "")
                         else (v["original_reason"] or "?").split(":")[0] for v in up)
        pct = lambda k: f"{k}/{n} ({100 * k / n:.0f}%)"  # noqa: E731
        print(f"| {label} | {n} | {pct(orig)} | {pct(new)} | {len(up)} | {down} | "
              f"{', '.join(f'{c} ×{k}' for c, k in causes.most_common())} |")
    if ungrouped:
        print("\nnot grouped: " + ", ".join(ungrouped), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
