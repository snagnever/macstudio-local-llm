#!/usr/bin/env python3
"""Regrade every saved LiveCodeBench JSONL with the corrected runner of lcb_regrade.py.

lcb_regrade.main reloads bench2's 50-question sample. Partial and resumed runs in
tools/local-llm-bench-m4-32gb/benchmarks/runs used other sample sizes, so this
driver looks up each answer by ``lcb_question_id`` in the full dataset instead.
It decodes the tests only for the question ids the files reference.

usage: regrade_all.py [--version release_v6] --json OUT.json FILE.jsonl [FILE.jsonl ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcb_regrade  # noqa: E402

bench2 = lcb_regrade.bench2


def read_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.open():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict) and obj.get("lcb_question_id"):
            rows.append(obj)
    return rows


def load_questions_by_id(ids: set[str], version: str) -> dict[str, dict]:
    """Build bench2 question dicts (grading fields only) for the given ids."""
    from huggingface_hub import hf_hub_download
    out = {}
    for fname in bench2.LCB_VERSION_FILES[version]:
        path = hf_hub_download(repo_id="livecodebench/code_generation_lite", filename=fname,
                               repo_type="dataset")
        with open(path) as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                qid = row.get("question_id")
                if qid not in ids or qid in out:
                    continue
                tests = json.loads(row.get("public_test_cases") or "[]") + \
                    bench2._decode_lcb_private_tests(row.get("private_test_cases"))
                try:
                    metadata = json.loads(row.get("metadata") or "{}")
                except Exception:
                    metadata = {}
                out[qid] = {
                    "question_id": qid,
                    "testtype": tests[0].get("testtype", "stdin") if tests else "stdin",
                    "starter_code": row.get("starter_code") or "",
                    "fn_name": metadata.get("func_name"),
                    "test_cases": tests,
                }
    return out


def grade_file(rows: list[dict], questions: dict[str, dict], grader) -> list[dict]:
    verdicts = []
    for r in rows:
        q = questions.get(r["lcb_question_id"])
        if q is None:
            ok, reason = False, "missing_question"
        elif r.get("finish_reason") == "length":
            ok, reason = False, "truncated"
        else:
            ok, _, reason = grader(q, r.get("raw_response") or "")
        verdicts.append({"question_num": r.get("question_num"), "lcb_question_id": r["lcb_question_id"],
                         "timestamp": r.get("timestamp"), "original": bool(r.get("correct")),
                         "original_reason": r.get("grade_reason"), "regraded": ok, "reason": reason})
    return verdicts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--version", default="release_v6")
    ap.add_argument("--json", type=Path, required=True, help="write per-question verdicts here")
    args = ap.parse_args(argv)
    rows_by_file = {f: read_rows(f) for f in args.files}
    ids = {r["lcb_question_id"] for rows in rows_by_file.values() for r in rows}
    questions = load_questions_by_id(ids, args.version)
    report = {}
    print("| file | rows | original | regraded | to pass | to fail |")
    print("|---|---:|---:|---:|---:|---:|")
    for f, rows in rows_by_file.items():
        verdicts = grade_file(rows, questions, lcb_regrade.regrade)
        orig = sum(v["original"] for v in verdicts)
        new = sum(v["regraded"] for v in verdicts)
        up = sum(1 for v in verdicts if v["regraded"] and not v["original"])
        down = sum(1 for v in verdicts if v["original"] and not v["regraded"])
        print(f"| {f.name} | {len(rows)} | {orig} | {new} | {up} | {down} |", flush=True)
        report[str(f)] = verdicts
    args.json.write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
