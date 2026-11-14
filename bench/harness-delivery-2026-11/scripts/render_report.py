#!/usr/bin/env python3
"""Render the public page of the harness-delivery campaign, with the speed and refusal results of swift-uncensored.

usage: render_report.py [--out reports/qwen38-flashnext-harness-delivery.html] [--card]

Reads only tracked results: results/sessions/*.json here, and refusal-*.jsonl plus etapa2-um-stream.md in
bench/swift-uncensored-2026-11/results. The page holds counts and times; no prompt and no model answer.
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import summarize  # noqa: E402
import tasks  # noqa: E402

CAMPAIGN = HERE.parent
REPO = CAMPAIGN.parents[1]
RESULTS = CAMPAIGN / "results"
SWIFT_RESULTS = REPO / "bench/swift-uncensored-2026-11/results"
OUT = REPO / "reports/qwen38-flashnext-harness-delivery.html"
CARD = REPO / "reports/assets/qwen38-flashnext-harness-delivery-card.html"

HARNESSES = ("claude", "opencode", "pi", "dsh")
PACKS = ("k2", "z4")
REPS = (1, 2)
HARNESS_LABEL = {"claude": "Claude Code", "opencode": "OpenCode", "pi": "pi", "dsh": "dsh"}
# short name, full name
PACK_LABEL = {"k2": ("Standard", "Swift 1.5 IQ4_XS (ukisai)"),
              "z4": ("Uncensored", "Swift 1.5 Heretic v2 IQ4_XS (jackjusko, indexer recast to BF16)")}
ARM_PACK = {"k2h": "Standard (ukisai Swift 1.5)", "z4h": "Uncensored: Heretic v2, BF16 indexer",
            "z2h": "Uncensored: Huihui abliterated v2", "z3h": "Uncensored: GSQ-RCO abliterated"}
ARMS = ("k2h", "z4h", "z2h", "z3h")
SETS = {"advbench": "AdvBench", "jbb": "JBB-Behaviors"}
TASK_LABEL = {
    "a": "Add a --format json option to a Python CLI, with a test",
    "b": "Fix 2 bugs in a bash word-count script, add 2 tests",
    "c": "Add a --group-by option to a Python ledger report",
    "d": "Fix 2 bugs in a bash backup toolkit and extract a shared library",
    "T1": "Find and fix 3 bugs behind 4 failing tests",
    "T5": "Repair a broken environment until make check is green",
    "T7": "Chain of 5 subtasks with a checklist",
}
# (pack, harness, task, rep) -> cause, from results/audit.md
FAILURE_CAUSES = {
    ("k2", "opencode", "T5", 1): "fixed the lint errors, left the test failing on a missing environment variable",
    ("z4", "opencode", "T5", 1): "stopped without fixing the lint errors",
    ("z4", "opencode", "T5", 2): "stopped without fixing the lint errors",
    ("z4", "claude", "d", 2): "left 1 of the 2 bugs unfixed",
    ("z4", "pi", "d", 2): "left 1 of the 2 bugs unfixed",
    ("z4", "dsh", "d", 2): "did not build the requested structure (shared library or 8 checks)",
    ("k2", "dsh", "b", 1): "deleted an original test",
}
# arm -> context -> (T_turn s, ratio against k2h, decode tok/s, wired peak GB); from etapa2-um-stream.md
SPEED = {
    "k2h": {32768: (6.0, 1.0, 112.1, 78.0), 131072: (5.9, 1.0, 117.0, 80.0), 262144: (6.2, 1.0, 112.2, 82.4)},
    "z4h": {32768: (6.1, 1.017, 109.8, 80.1), 131072: (6.2, 1.051, 110.0, 82.1), 262144: (6.4, 1.032, 105.9, 84.7)},
    "z2h": {32768: (6.2, 1.033, 108.7, 64.7), 131072: (6.2, 1.051, 109.9, 66.6), 262144: (6.3, 1.016, 108.7, 69.2)},
    "z3h": {32768: (6.2, 1.033, 107.2, 64.4), 131072: (6.1, 1.034, 113.4, 66.5), 262144: (6.2, 1.000, 112.2, 69.0)},
}
SPEED_LIMIT = 1.05


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 1) if values else None


def _refusal(swift_results: Path) -> dict:
    out = {}
    for arm in ARMS:
        for s in SETS:
            rows = [json.loads(line) for line in (swift_results / f"refusal-{arm}-{s}.jsonl").read_text().splitlines()
                    if line.strip()]
            out[(arm, s)] = {v: sum(r["verdict"] == v for r in rows) for v in ("refused", "empty", "complied")}
            out[(arm, s)]["n"] = len(rows)
    return out


def collect(delivery_results: Path = RESULTS, swift_results: Path = SWIFT_RESULTS) -> dict:
    """Every number of the page. Raises ValueError when the session matrix is not complete."""
    records = summarize.load(Path(delivery_results))
    by = {(r["pack"], r["harness"], r["task"], r["rep"]): r for r in records}
    want = [(p, h, t, n) for p in PACKS for h in HARNESSES for t in tasks.TASKS for n in REPS]
    missing = [f"{p}-{h}-{t}-r{n}" for p, h, t, n in want if (p, h, t, n) not in by]
    if missing or len(records) != len(want):
        raise ValueError(f"session matrix is not complete: missing {missing or 'nothing'}, {len(records)} records")

    def sel(**kw):
        return [r for r in records if all(r[k] == v for k, v in kw.items())]

    done = lambda rs: sum(r["task_done"] for r in rs)  # noqa: E731
    walls = lambda rs: [r["wall_s"] for r in rs if r["task_done"]]  # noqa: E731
    harness = []
    for name, total, median in summarize.rank(records):
        mine = sel(harness=name)
        harness.append({"name": name, "label": HARNESS_LABEL[name], "version": mine[0]["harness_version"],
                        "done": total, "n": len(mine), "median_s": median,
                        "by_pack": {p: {"done": done(sel(harness=name, pack=p)), "n": len(sel(harness=name, pack=p))}
                                    for p in PACKS}})
    failures = []
    for r in records:
        if not r["task_done"]:
            key = (r["pack"], r["harness"], r["task"], r["rep"])
            if key not in FAILURE_CAUSES:
                raise ValueError(f"failed session without an audited cause: {key}")
            failures.append({"pack": key[0], "harness": key[1], "task": key[2], "rep": key[3],
                             "cause": FAILURE_CAUSES[key], "claimed_done": r["claimed_done"]})
    return {
        "sessions": {"total": len(records), "done": done(records)},
        "harness": harness,
        "cells": {(h, t): {p: done(sel(harness=h, task=t, pack=p)) for p in PACKS}
                  for h in HARNESSES for t in tasks.TASKS},
        "tasks": [{"id": t, "label": TASK_LABEL[t], "hard": tasks.TASKS[t].hard, "n": len(sel(task=t, pack="k2")),
                   "k2_done": done(sel(task=t, pack="k2")), "z4_done": done(sel(task=t, pack="z4")),
                   "median_s": {p: _median(walls(sel(task=t, pack=p))) for p in PACKS}} for t in tasks.TASKS],
        "times": {(h, t): walls(sel(harness=h, task=t)) for h in HARNESSES for t in tasks.TASKS},
        "reserva": summarize.reserva(records, "k2", "z4"),
        "failures": failures,
        "timeouts": sum(bool(r["timeout"]) for r in records),
        "notes": sum("makefile_changed" in r["cheat"] for r in records),
        "refusal": _refusal(Path(swift_results)),
        "speed": {arm: {ctx: dict(zip(("t_turn_s", "ratio", "decode_tps", "wired_gb"), v)) for ctx, v in rows.items()}
                  for arm, rows in SPEED.items()},
        "speed_verdict": {arm: "pass" if all(v[1] <= SPEED_LIMIT for v in rows.values()) else "fail"
                          for arm, rows in SPEED.items() if arm != "k2h"},
    }
