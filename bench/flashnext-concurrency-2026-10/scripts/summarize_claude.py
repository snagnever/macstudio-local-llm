#!/usr/bin/env python3
"""Summarize the Claude Code runs of one campaign: results/cc-<prefix>{1,2}[<variant>]r<rep>-<task>.json (wall
time per session, from run-claude-pair.sh) and results/req-<prefix>*.jsonl (per-request records, see
claude_requests.py and request_log.py).

    python3 summarize_claude.py --results-dir DIR --prefix kcc --out DIR/claude-summary.json [--markdown]
    python3 summarize_claude.py --results-dir DIR --prefix rc --variants s=subagents,d=decode_share --out ...

Output: {"prefix", "profiles": {"small" | "realistic": {"tasks", "alone_s", "pair_s", "pair_wall_s",
"serial_sum_s", "time_saved", "turns", "task_done", "errors"}}, "requests": {"alone", "pair"}} plus, for each
variant letter found in the file names (cc-rc2sr1-c.json is variant "s"), {"<name>": {"profile": {...},
"requests": {...}, "parallel_agent_calls", "subagents_spawned"}}, whose serial_sum_s is the main alone's.
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
VARIANT_TASKS = ("c", "d")


def _reps(results_dir: Path, kind: str, task: str) -> list[Path]:
    """kind = <prefix><1|2>[<variant>]; the glob cc-{kind}r*-{task}.json only matches that exact kind."""
    return sorted(results_dir.glob(f"cc-{kind}r*-{task}.json"))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rep(name: str, prefix: str, kind: str, variant: str = "") -> Optional[str]:
    """The rep number in cc-<prefix><kind><variant>r<rep>-<task>.json or req-<prefix><kind><variant>r<rep>[-<task>].jsonl."""
    m = re.match(rf"^(?:cc|req)-{re.escape(prefix)}{kind}{re.escape(variant)}r(\d+)(?:-[^.]+)?\.jsonl?$", name)
    return m.group(1) if m else None


def _failed(r: dict[str, Any]) -> bool:
    """A session that timed out, exited non-zero or whose output did not parse: an error, not a wall time."""
    return bool(r.get("is_error") or r.get("parse_error") or r.get("exit", 0) != 0)


def _timed(r: dict[str, Any]) -> bool:
    """A session has a task time only when it ran to the end and did the task: a session that exited 0 with the
    work undone (an empty answer after 12 turns) is reported through task_done, not as a shorter task."""
    return not _failed(r) and bool(r.get("task_done"))


def _mean_wall(runs: list[dict[str, Any]]) -> Optional[float]:
    good = [r["wall_s"] for r in runs if _timed(r)]
    return statistics.mean(good) if good else None


def _pair_walls(results_dir: Path, prefix: str, tasks: tuple[str, ...], variant: str = "") -> Optional[float]:
    """One pair wall per rep: the later of the two sessions; a rep with a failed or unfinished session has no pair wall."""
    by_rep: dict[str, list[Optional[float]]] = {}
    for t in tasks:
        for p in _reps(results_dir, f"{prefix}2{variant}", t):
            r = _load(p)
            by_rep.setdefault(_rep(p.name, prefix, "2", variant) or p.name, []).append(r["wall_s"] if _timed(r) else None)
    walls = [max(ws) for ws in by_rep.values() if len(ws) == len(tasks) and None not in ws]
    return statistics.mean(walls) if walls else None


def _turns(runs: list[dict[str, Any]]) -> Optional[float]:
    n = [r["num_turns"] for r in runs if r.get("num_turns") is not None]
    return statistics.median(n) if n else None


def _pair_block(pair: dict[str, list[dict[str, Any]]], pair_wall: Optional[float], serial: Optional[float],
                alone: dict[str, list[dict[str, Any]]], tasks: tuple[str, ...]) -> dict[str, Any]:
    runs = [r for rs in list(alone.values()) + list(pair.values()) for r in rs]
    return {"tasks": list(tasks), "pair_s": {t: _mean_wall(rs) for t, rs in pair.items()}, "pair_wall_s": pair_wall,
            "serial_sum_s": serial,
            "time_saved": (1 - pair_wall / serial) if pair_wall is not None and serial else None,
            "turns": {t: _turns(alone.get(t, []) + pair[t]) for t in tasks},
            "task_done": all(r.get("task_done") for r in runs), "errors": sum(1 for r in runs if _failed(r))}


def _alone(results_dir: Path, prefix: str, tasks: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
    return {t: [_load(p) for p in _reps(results_dir, f"{prefix}1", t)] for t in tasks}


def _serial(alone: dict[str, list[dict[str, Any]]]) -> Optional[float]:
    alone_s = {t: _mean_wall(rs) for t, rs in alone.items()}
    return sum(alone_s.values()) if all(v is not None for v in alone_s.values()) else None


def _profile(results_dir: Path, prefix: str, tasks: tuple[str, ...]) -> Optional[dict[str, Any]]:
    alone = _alone(results_dir, prefix, tasks)
    pair = {t: [_load(p) for p in _reps(results_dir, f"{prefix}2", t)] for t in tasks}
    if not any(alone.values()) and not any(pair.values()):
        return None
    block = _pair_block(pair, _pair_walls(results_dir, prefix, tasks), _serial(alone), alone, tasks)
    block = dict(block, alone_s={t: _mean_wall(rs) for t, rs in alone.items()})
    order = ["tasks", "alone_s", "pair_s", "pair_wall_s", "serial_sum_s", "time_saved", "turns", "task_done", "errors"]
    return {k: block[k] for k in order}


PROFILE_OF_TASK = {t: name for name, tasks in PROFILES.items() for t in tasks}


def _task_of(name: str) -> str:
    """The task letter of req-<kind>r<rep>-<task>.jsonl, or "" for the old one-file-per-rep layout."""
    stem = name.rsplit(".", 1)[0]
    return stem.rsplit("-", 1)[1] if stem.count("-") >= 2 else ""


def _requests(results_dir: Path, prefix: str, kind: str, per_file: bool, variant: str = "") -> Optional[dict[str, Any]]:
    """Pool the request files of one kind (1 = alone, 2 = pair). Files of the same group share one clock (the
    sessions of a pair rep of one profile, written by the proxy; the a+b and c+d pairs reuse the rep tags but
    are separate boots); groups are laid end to end so runs never look concurrent."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for p in sorted(results_dir.glob(f"req-{prefix}{kind}{variant}r*.jsonl")):
        rep = _rep(p.name, prefix, kind, variant)
        if rep is None:
            continue
        rows = read_requests(p)
        if rows:
            key = p.name if per_file else f"{rep}-{PROFILE_OF_TASK.get(_task_of(p.name), '')}"
            groups.setdefault(key, []).extend(rows)
    reqs: list[dict[str, Any]] = []
    offset = 0.0
    for key in sorted(groups):
        rows = groups[key]
        reqs += [dict(r, t_start_s=r["t_start_s"] + offset, t_end_s=r["t_end_s"] + offset) for r in rows]
        offset = max(r["t_end_s"] for r in reqs) + 1.0
    return summarize_requests(reqs) if reqs else None


def _variant(results_dir: Path, prefix: str, variant: str, tasks: tuple[str, ...] = VARIANT_TASKS) -> Optional[dict[str, Any]]:
    """The pair files of one variant letter (cc-<prefix>2<variant>r<rep>-<task>.json); serial from the main alone."""
    pair = {t: [_load(p) for p in _reps(results_dir, f"{prefix}2{variant}", t)] for t in tasks}
    if not any(pair.values()):
        return None
    alone = _alone(results_dir, prefix, tasks)
    runs = [r for rs in pair.values() for r in rs]
    profile = _pair_block(pair, _pair_walls(results_dir, prefix, tasks, variant), _serial(alone), {}, tasks)
    profile["turns"] = {t: _turns(pair[t]) for t in tasks}
    return {"profile": profile, "requests": _requests(results_dir, prefix, "2", per_file=False, variant=variant),
            "parallel_agent_calls": sum(int(r.get("parallel_agent_calls") or 0) for r in runs),
            "subagents_spawned": sum(int(r.get("subagents_spawned") or 0) for r in runs)}


def summarize_claude(results_dir: Path, prefix: str, variants: Optional[dict[str, str]] = None) -> dict[str, Any]:
    results_dir = Path(results_dir)
    profiles = {name: _profile(results_dir, prefix, tasks) for name, tasks in PROFILES.items()}
    out: dict[str, Any] = {"prefix": prefix, "profiles": {k: v for k, v in profiles.items() if v is not None},
                           "requests": {"alone": _requests(results_dir, prefix, "1", per_file=True),
                                        "pair": _requests(results_dir, prefix, "2", per_file=False)}}
    for letter, name in (variants or {}).items():
        block = _variant(results_dir, prefix, letter)
        if block is not None:
            out[name] = block
    return out


def _f(v: Optional[float], fmt: str = "{:.1f}") -> str:
    return "n/d" if v is None else fmt.format(v)


def markdown(summary: dict[str, Any]) -> str:
    lines = ["| profile | task | alone_s | pair_s | pair_wall_s | serial_sum_s | time_saved | turns |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for name, p in summary["profiles"].items():
        for t in p["tasks"]:
            lines.append(f"| {name} | {t} | {_f(p['alone_s'][t])} | {_f(p['pair_s'][t])} | {_f(p['pair_wall_s'])} "
                         f"| {_f(p['serial_sum_s'])} | {_f(p['time_saved'], '{:+.0%}')} | {_f(p['turns'][t], '{:.0f}')} |")
    for name, block in summary.items():
        if name in ("prefix", "profiles", "requests"):
            continue
        p = block["profile"]
        for t in p["tasks"]:
            lines.append(f"| {name} | {t} | | {_f(p['pair_s'][t])} | {_f(p['pair_wall_s'])} "
                         f"| {_f(p['serial_sum_s'])} | {_f(p['time_saved'], '{:+.0%}')} | {_f(p['turns'][t], '{:.0f}')} |")
    lines += ["", "| requests | n | max_concurrent | first_prompt_ttft_s | warm ttft p50 / p90 | warm tok/s p50 / min | errors |",
              "|---|---:|---:|---:|---|---|---:|"]
    reqs = dict(summary["requests"])
    for name, block in summary.items():
        if name not in ("prefix", "profiles", "requests"):
            reqs[name] = block["requests"]
    for kind, r in reqs.items():
        if r is None:
            lines.append(f"| {kind} | n/d | | | | | |")
            continue
        w = r["warm"] or {}
        lines.append(f"| {kind} | {r['n']} | {r['max_concurrent']} | {_f(r['first_prompt_ttft_s'])} "
                     f"| {_f(w.get('ttft_p50'))} / {_f(w.get('ttft_p90'))} | {_f(w.get('tps_p50'))} / {_f(w.get('tps_min'))} "
                     f"| {r.get('errors', 0)} |")
    return "\n".join(lines)


def _parse_variants(text: Optional[str]) -> Optional[dict[str, str]]:
    if not text:
        return None
    out = {}
    for item in text.split(","):
        letter, _, name = item.partition("=")
        if not letter or not name:
            raise SystemExit(f"--variants: expected LETTER=NAME, got {item!r}")
        out[letter.strip()] = name.strip()
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Summarize the Claude Code runs of a campaign.")
    p.add_argument("--results-dir", required=True)
    p.add_argument("--prefix", required=True, help="kcc (Splash campaign), cc (mlx-serve 26.10.1 campaign), rc / rm (campaign B)")
    p.add_argument("--out", required=True)
    p.add_argument("--variants", default=None, help="LETTER=NAME[,LETTER=NAME]: e.g. s=subagents,d=decode_share")
    p.add_argument("--markdown", action="store_true")
    args = p.parse_args(argv)
    summary = summarize_claude(Path(args.results_dir), args.prefix, _parse_variants(args.variants))
    Path(args.out).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        print(markdown(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
