#!/usr/bin/env python3
"""Consolida o A/B n2 × w1: nota, truncamentos, tempo e tokens por suíte, e os gates G1 (qualidade) e G2 (thinking)."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

SUITES = ("humaneval", "gpqa", "livecodebench", "jdhodges", "veerman", "if")
TOOL_SUITES = {"jdhodges", "veerman"}
QUALITY_MARGIN = {"humaneval": 3, "gpqa": 3, "livecodebench": 3, "jdhodges": 2, "veerman": 1, "if": 2}
TIME_SUITES = ("gpqa", "livecodebench")
TIME_RATIO = 0.8


def _true(v) -> bool:
    return v is True or str(v) == "True"


def _num(v, cast=float):
    if v in (None, "None", ""):
        return cast(0)
    return cast(float(v))


def view(suite: str, r: dict) -> dict:
    if suite in TOOL_SUITES:
        rid, ok = r["case_id"], _true(r.get("score_pass"))
        elapsed = _num(r.get("turn_1_elapsed_s")) + _num(r.get("turn_2_elapsed_s"))
        fin = r.get("turn_1_finish_reason")
    elif suite == "if":
        rid, ok, elapsed, fin = r["id"], _true(r.get("passed")), _num(r.get("elapsed_s")), r.get("finish_reason")
    else:
        rid = r.get("lcb_question_id") if suite == "livecodebench" else r.get("dataset_idx")
        ok, elapsed, fin = _true(r.get("correct")), _num(r.get("elapsed_s")), r.get("finish_reason")
    # Uma resposta truncada nunca conta como acerto; o registro de tool-calling não grava reasoning_chars (None).
    rc = r.get("reasoning_chars")
    return {"id": str(rid), "passed": ok and fin != "length", "elapsed_s": elapsed,
            "completion_tokens": _num(r.get("completion_tokens"), int),
            "reasoning_chars": None if rc in (None, "None", "") else _num(rc, int), "truncated": fin == "length"}


def suite_stats(views: list[dict]) -> dict:
    def med(k):
        xs = [v[k] for v in views if v[k] is not None]
        return round(statistics.median(xs), 1) if xs else None
    return {"n": len(views), "passed": sum(v["passed"] for v in views),
            "truncated": sum(v["truncated"] for v in views),
            "total_s": round(sum(v["elapsed_s"] for v in views), 1), "median_s": med("elapsed_s"),
            "median_completion": med("completion_tokens"), "median_reasoning_chars": med("reasoning_chars")}


def load_arm(path: Path) -> dict[str, list[dict]]:
    out = {}
    for suite in SUITES:
        f = Path(path) / f"{suite}.jsonl"
        if f.is_file():
            out[suite] = [view(suite, json.loads(l)) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return out


def compare(base: dict[str, list[dict]], cand: dict[str, list[dict]]) -> dict:
    """Estatísticas das suítes presentes nos dois braços. Recusa questões diferentes."""
    stats = {"base": {}, "cand": {}}
    for suite in SUITES:
        if suite not in base or suite not in cand:
            continue
        ids_b, ids_c = {v["id"] for v in base[suite]}, {v["id"] for v in cand[suite]}
        if ids_b != ids_c:
            raise ValueError(f"{suite}: questões diferentes entre os braços "
                             f"(só na base: {sorted(ids_b - ids_c)[:5]}, só no candidato: {sorted(ids_c - ids_b)[:5]})")
        stats["base"][suite], stats["cand"][suite] = suite_stats(base[suite]), suite_stats(cand[suite])
    return stats


def gates(base: dict, cand: dict) -> dict[str, bool]:
    g = {}
    for suite in base:
        g[f"G1:{suite}"] = cand[suite]["passed"] >= base[suite]["passed"] - QUALITY_MARGIN[suite]
    for suite in TIME_SUITES:
        if suite in base:
            g[f"G2:{suite}"] = cand[suite]["median_s"] <= TIME_RATIO * base[suite]["median_s"]
    return g


def render(stats: dict, gate_result: dict, base: str, cand: str) -> str:
    lines = [f"| suíte | métrica | {base} | {cand} |", "| --- | --- | ---: | ---: |"]
    for suite, b in stats["base"].items():
        c = stats["cand"][suite]
        for key, label in (("passed", "acertos"), ("truncated", "truncadas"), ("median_s", "tempo mediano (s)"),
                           ("total_s", "tempo total (s)"), ("median_completion", "tokens medianos"),
                           ("median_reasoning_chars", "reasoning mediano (chars)")):
            val_b = f"{b[key]}/{b['n']}" if key == "passed" else ("n/d" if b[key] is None else b[key])
            val_c = f"{c[key]}/{c['n']}" if key == "passed" else ("n/d" if c[key] is None else c[key])
            lines.append(f"| {suite} | {label} | {val_b} | {val_c} |")
    lines += ["", "| gate | resultado |", "| --- | --- |"]
    lines += [f"| {k} | {'passa' if v else 'falha'} |" for k, v in gate_result.items()]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ab-dir", default=str(Path(__file__).resolve().parents[1] / "results" / "ab" / "t1"),
                    help="results/ab/<perfil>; default t1 (sampling do vendor)")
    ap.add_argument("--base", default="n2")
    ap.add_argument("--cand", default="w1")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    stats = compare(load_arm(Path(a.ab_dir) / a.base), load_arm(Path(a.ab_dir) / a.cand))
    md = render(stats, gates(stats["base"], stats["cand"]), a.base, a.cand)
    print(md)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
