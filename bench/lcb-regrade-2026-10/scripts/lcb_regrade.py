#!/usr/bin/env python3
"""Regrade saved LiveCodeBench answers with a corrected test runner.

The runner in tools/local-llm-bench-m4-32gb/scripts/bench2.py (submodule a4a95bb) has two defects:
1. It runs the answer without the import prelude of the official LiveCodeBench harness, so a correct
   solution that uses ``List[int]`` without ``from typing import List`` fails with NameError.
2. It passes the program to ``python -c``; a functional test with a large input exceeds the OS argument
   limit (``[Errno 7] Argument list too long``).

This script keeps bench2's code extraction, test decoding and comparison, and replaces only the two runner
functions: each program gets the prelude and runs from a temporary file. It reads the JSONL files written by
bench2 (one row per question, with ``raw_response`` and ``lcb_question_id``), reloads the same 50 questions
(bench2's seed), and prints the original and the regraded pass count per file.

Since submodule commit 2403125 (snagnever/local-llm-bench-m4-32gb#3) bench2 has the same fix, so new runs grade
correctly without this script. It stays to regrade answers saved before that commit.

usage: lcb_regrade.py [--version release_v6] [--n 50] [--json OUT] FILE.jsonl [FILE.jsonl ...]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "local-llm-bench-m4-32gb" / "scripts"))
import bench2  # noqa: E402

# Import prelude of the official LiveCodeBench runner (lcb_runner/evaluation/testing_util.py, import_string).
PRELUDE = (
    "from string import *\nfrom re import *\nfrom datetime import *\nfrom collections import *\n"
    "from heapq import *\nfrom bisect import *\nfrom copy import *\nfrom math import *\nfrom random import *\n"
    "from statistics import *\nfrom itertools import *\nfrom functools import *\nfrom operator import *\n"
    "from io import *\nfrom sys import *\nfrom json import *\nfrom builtins import *\nfrom typing import *\n"
    "import string\nimport re\nimport datetime\nimport collections\nimport heapq\nimport bisect\nimport copy\n"
    "import math\nimport random\nimport statistics\nimport itertools\nimport functools\nimport operator\n"
    "import io\nimport sys\nimport json\nsys.setrecursionlimit(50000)\n"
)


def _run_file(program: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    fd, path = tempfile.mkstemp(suffix=".py", prefix="lcb_")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(program)
        return subprocess.run([sys.executable, path], input=stdin, capture_output=True, text=True,
                              timeout=bench2.LCB_TIMEOUT_S)
    finally:
        os.unlink(path)


def _functional(code, test_case, fn_name, starter_code):
    raw_input = test_case.get("input", "")
    expected = (test_case.get("output") or "").strip()
    arg_lines = [ln for ln in raw_input.split("\n") if ln.strip() != ""]
    args_repr = "[" + ", ".join(arg_lines) + "]" if arg_lines else "[]"
    invoke = f"Solution().{fn_name}(*_args)" if ("class Solution" in starter_code or "class Solution" in code) \
        else f"{fn_name}(*_args)"
    program = (f"{PRELUDE}\n{code}\n\nimport json as _json, sys as _sys\n_args = {args_repr}\n"
               f"_result = {invoke}\n_sys.stdout.write(_json.dumps(_result))\n")
    try:
        proc = _run_file(program)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    if proc.returncode != 0:
        return False, f"rc={proc.returncode}: {proc.stderr[-200:]}"
    got = proc.stdout.strip()
    try:
        if json.loads(got) == json.loads(expected):
            return True, "ok"
    except Exception:
        pass
    return (got == expected), "ok" if got == expected else "mismatch"


def _stdin(code, test_case):
    expected = (test_case.get("output") or "").strip()
    try:
        proc = _run_file(f"{PRELUDE}\n{code}\n", stdin=test_case.get("input", ""))
    except subprocess.TimeoutExpired:
        return False, "timeout"
    if proc.returncode != 0:
        return False, f"rc={proc.returncode}: {proc.stderr[-200:]}"
    got_lines = [ln.rstrip() for ln in proc.stdout.strip().split("\n")]
    exp_lines = [ln.rstrip() for ln in expected.split("\n")]
    return (got_lines == exp_lines), "ok" if got_lines == exp_lines else "mismatch"


def regrade(question: dict, response_text: str):
    """bench2.grade_livecodebench with the corrected runners; returns (ok, question_id, reason)."""
    saved = bench2._run_lcb_functional_test, bench2._run_lcb_stdin_test
    bench2._run_lcb_functional_test, bench2._run_lcb_stdin_test = _functional, _stdin
    try:
        return bench2.grade_livecodebench(question, response_text)
    finally:
        bench2._run_lcb_functional_test, bench2._run_lcb_stdin_test = saved


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--version", default="release_v6")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--json", type=Path, help="write per-question verdicts here")
    args = ap.parse_args(argv)
    questions = {q["question_id"]: q for q in bench2.load_livecodebench_questions(args.n, args.version)}
    report = {}
    print("| arquivo | original | reavaliado | viradas para ok | viradas para falha |")
    print("|---|---:|---:|---:|---:|")
    for f in args.files:
        rows = [json.loads(line) for line in f.open() if line.strip()]
        verdicts = []
        for r in rows:
            q = questions.get(r.get("lcb_question_id"))
            if q is None or r.get("finish_reason") == "length":
                ok, reason = False, "missing_question" if q is None else "truncated"
            else:
                ok, _, reason = regrade(q, r.get("raw_response") or "")
            verdicts.append({"question_num": r.get("question_num"), "lcb_question_id": r.get("lcb_question_id"),
                             "original": bool(r.get("correct")), "regraded": ok, "reason": reason})
        orig = sum(v["original"] for v in verdicts)
        new = sum(v["regraded"] for v in verdicts)
        up = sum(1 for v in verdicts if v["regraded"] and not v["original"])
        down = sum(1 for v in verdicts if v["original"] and not v["regraded"])
        label = f"{f.parent.name}/{f.name}"
        print(f"| {label} | {orig}/{len(rows)} | {new}/{len(rows)} | {up} | {down} |")
        report[label] = verdicts
    if args.json:
        args.json.write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
