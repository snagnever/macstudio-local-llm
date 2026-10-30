#!/usr/bin/env python3
"""Summarize the Claude Code runs of one campaign: results/cc-<prefix>{1,2}r<rep>-<task>.json (wall time per
session, from run-claude-pair.sh) and results/req-<prefix>*.jsonl (per-request records, see claude_requests.py).

    python3 summarize_claude.py --results-dir DIR --prefix kcc --out DIR/claude-summary.json [--markdown]

Output: {"prefix", "profiles": {"small" | "realistic": {"tasks", "alone_s", "pair_s", "pair_wall_s",
"serial_sum_s", "time_saved", "turns", "task_done", "errors"}}, "requests": {"alone", "pair"}}.
time_saved = 1 - pair_wall_s / serial_sum_s: the share of the two tasks' sequential time that running them
together saves (negative when the pair finishes later). Python 3.9 stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_requests import read_requests, summarize_requests  # noqa: E402

PROFILES = {"small": ("a", "b"), "realistic": ("c", "d")}


def _reps(results_dir: Path, kind: str, task: str) -> list[Path]:
    return sorted(results_dir.glob(f"cc-{kind}r*-{task}.json"))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rep(name: str, prefix: str, kind: str) -> Optional[str]:
    """The rep number in cc-<prefix><kind>r<rep>-<task>.json or req-<prefix><kind>r<rep>[-<task>].jsonl."""
    m = re.match(rf"^(?:cc|req)-{re.escape(prefix)}{kind}r(\d+)(?:-[^.]+)?\.jsonl?$", name)
    return m.group(1) if m else None


def _failed(r: dict[str, Any]) -> bool:
    """A session that timed out, exited non-zero or whose output did not parse: an error, not a wall time."""
    return bool(r.get("is_error") or r.get("parse_error") or r.get("exit", 0) != 0)


def _profile(results_dir: Path, prefix: str, tasks: tuple[str, ...]) -> Optional[dict[str, Any]]:
    alone = {t: [_load(p) for p in _reps(results_dir, f"{prefix}1", t)] for t in tasks}
    pair = {t: [_load(p) for p in _reps(results_dir, f"{prefix}2", t)] for t in tasks}
    if not any(alone.values()) and not any(pair.values()):
        return None
    runs = [r for rs in list(alone.values()) + list(pair.values()) for r in rs]
    good_alone = {t: [r for r in rs if not _failed(r)] for t, rs in alone.items()}
    good_pair = {t: [r for r in rs if not _failed(r)] for t, rs in pair.items()}
    alone_s = {t: statistics.mean(r["wall_s"] for r in rs) if rs else None for t, rs in good_alone.items()}
    pair_s = {t: statistics.mean(r["wall_s"] for r in rs) if rs else None for t, rs in good_pair.items()}
    # One pair wall per rep: the later of the two sessions; a rep with a failed session has no pair wall.
    by_rep: dict[str, list[Optional[float]]] = {}
    for t in tasks:
        for p in _reps(results_dir, f"{prefix}2", t):
            r = _load(p)
            by_rep.setdefault(_rep(p.name, prefix, "2") or p.name, []).append(None if _failed(r) else r["wall_s"])
    pair_walls = [max(ws) for ws in by_rep.values() if len(ws) == len(tasks) and None not in ws]
    pair_wall = statistics.mean(pair_walls) if pair_walls else None
    serial = sum(alone_s.values()) if all(v is not None for v in alone_s.values()) else None
    turns = {}
    for t in tasks:
        n = [r["num_turns"] for r in alone[t] + pair[t] if r.get("num_turns") is not None]
        turns[t] = statistics.median(n) if n else None
    return {"tasks": list(tasks), "alone_s": alone_s, "pair_s": pair_s, "pair_wall_s": pair_wall,
            "serial_sum_s": serial,
            "time_saved": (1 - pair_wall / serial) if pair_wall is not None and serial else None,
            "turns": turns, "task_done": all(r.get("task_done") for r in runs),
            "errors": sum(1 for r in runs if _failed(r))}


def _requests(results_dir: Path, prefix: str, kind: str, per_file: bool) -> Optional[dict[str, Any]]:
    """Pool the request files of one kind (1 = alone, 2 = pair). Files of the same group share one clock (the
    sessions of a pair rep, written by the proxy); groups are laid end to end so runs never look concurrent."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for p in sorted(results_dir.glob(f"req-{prefix}{kind}r*.jsonl")):
        rep = _rep(p.name, prefix, kind)
        if rep is None:
            continue
        rows = read_requests(p)
        if rows:
            groups.setdefault(p.name if per_file else rep, []).extend(rows)
    reqs: list[dict[str, Any]] = []
    offset = 0.0
    for key in sorted(groups):
        rows = groups[key]
        reqs += [dict(r, t_start_s=r["t_start_s"] + offset, t_end_s=r["t_end_s"] + offset) for r in rows]
        offset = max(r["t_end_s"] for r in reqs) + 1.0
    return summarize_requests(reqs) if reqs else None


def summarize_claude(results_dir: Path, prefix: str) -> dict[str, Any]:
    results_dir = Path(results_dir)
    profiles = {name: _profile(results_dir, prefix, tasks) for name, tasks in PROFILES.items()}
    return {"prefix": prefix, "profiles": {k: v for k, v in profiles.items() if v is not None},
            "requests": {"alone": _requests(results_dir, prefix, "1", per_file=True),
                         "pair": _requests(results_dir, prefix, "2", per_file=False)}}


def _f(v: Optional[float], fmt: str = "{:.1f}") -> str:
    return "n/d" if v is None else fmt.format(v)


def markdown(summary: dict[str, Any]) -> str:
    lines = ["| profile | task | alone_s | pair_s | pair_wall_s | serial_sum_s | time_saved | turns |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for name, p in summary["profiles"].items():
        for t in p["tasks"]:
            lines.append(f"| {name} | {t} | {_f(p['alone_s'][t])} | {_f(p['pair_s'][t])} | {_f(p['pair_wall_s'])} "
                         f"| {_f(p['serial_sum_s'])} | {_f(p['time_saved'], '{:+.0%}')} | {_f(p['turns'][t], '{:.0f}')} |")
    lines += ["", "| requests | n | max_concurrent | first_prompt_ttft_s | warm ttft p50 / p90 | warm tok/s p50 / min |",
              "|---|---:|---:|---:|---|---|"]
    for kind, r in summary["requests"].items():
        if r is None:
            lines.append(f"| {kind} | n/d | | | | |")
            continue
        w = r["warm"] or {}
        lines.append(f"| {kind} | {r['n']} | {r['max_concurrent']} | {_f(r['first_prompt_ttft_s'])} "
                     f"| {_f(w.get('ttft_p50'))} / {_f(w.get('ttft_p90'))} | {_f(w.get('tps_p50'))} / {_f(w.get('tps_min'))} |")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Summarize the Claude Code runs of a campaign.")
    p.add_argument("--results-dir", required=True)
    p.add_argument("--prefix", required=True, help="kcc (Splash campaign), cc (mlx-serve 26.10.1 campaign)")
    p.add_argument("--out", required=True)
    p.add_argument("--markdown", action="store_true")
    args = p.parse_args(argv)
    summary = summarize_claude(Path(args.results_dir), args.prefix)
    Path(args.out).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        print(markdown(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
