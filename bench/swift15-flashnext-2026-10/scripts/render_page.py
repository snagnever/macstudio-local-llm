#!/usr/bin/env python3
"""Render the Swift 1.5 × n2 findings into reports/qwen38-flashnext-swift15.html.

collect() reads the A/B battery (results/ab), the HumanEval regrade, the T_turno summary of this campaign and
the canonical speed groups of the October perf-lines data; render() turns that payload into a self-contained
page in the layout of reports/qwen38-flashnext-perf-lines.html.

    python3 bench/swift15-flashnext-2026-10/scripts/render_page.py
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import summarize_ab as S

CAMPAIGN = Path(__file__).resolve().parents[1]
RESULTS = CAMPAIGN / "results"
REPORTS_JSON = CAMPAIGN.parent / "engine-updates-2026-10" / "results" / "reports-2026-10.json"
OUT = CAMPAIGN.parents[1] / "reports" / "qwen38-flashnext-swift15.html"
JSON_OUT = RESULTS / "page-data.json"

ARMS = ("n2", "w1")
PROFILES = ("t1", "t0")
CONTEXTS = ("32768", "131072")
THIS_CAMPAIGN = "swift15-flashnext-2026-10"
# Stacks from the October perf-lines data, in table order. m1 is the MTPLX series: m1p at 32K, m1x at 128K.
OTHER_SERIES = ("o1", "m1", "d1", "c1")
G3_RATIO = 1.03

STACKS = {
    "n2": {"label": "n2", "name": "iQ-MLX 4.7 bpw · mlx-serve 26.10.1",
           "weights": "ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw", "rev": "dafff5c",
           "runtime": "mlx-serve 26.10.1", "role": "previous driver (rollback)"},
    "w1": {"label": "w1", "name": "Swift 1.5 MLX 4.7 bpw · mlx-serve 26.10.1",
           "weights": "Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw", "rev": "13839b7",
           "runtime": "mlx-serve 26.10.1", "role": "new driver"},
    "o1": {"label": "o1", "name": "oQ4e · oMLX 0.7.0", "weights": "Jundot/Qwen3.8-Flash-Next-oQ4e-mtp",
           "rev": "2615fc0", "runtime": "oMLX 0.7.0"},
    "m1": {"label": "m1", "name": "Optimized-Speed · MTPLX 2.12.2",
           "weights": "Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed", "rev": "6bc2f6e", "runtime": "MTPLX 2.12.2"},
    "d1": {"label": "d1", "name": "Q4 GGUF · ds4 upstream", "weights": "antirez/qwen3.8-flash-next-gguf (Q4)",
           "rev": "qwen38-q4k", "runtime": "ds4 0aaea5a"},
    "c1": {"label": "c1", "name": "mixed-4/8 · mlx-serve 26.9.2 (Sept)",
           "weights": "ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit", "rev": "ef5b919", "runtime": "mlx-serve 26.9.2"},
}

# Earlier batteries: no reasoning_effort sent, temperature 0. Sources are cited on the page.
LEGACY = {
    "sources": ["bench/engine-updates-2026-10/results/quality-o1-mtplx.md",
                "bench/qwen38-flashnext-updates-2026-10/results/quality-n1-n2.md"],
    "rows": [
        {"arm": "n2", "stack": "iQ-MLX 4.7 bpw · mlx-serve 26.10.1", "date": "2026-10-07", "he_strict": 154,
         "he_imports": 156, "he_truncated": 0, "jdhodges": 38, "veerman": 9, "he_tokens": 201, "he_minutes": 8,
         "thinking": "almost none (~200 tokens per answer)"},
        {"arm": "n1", "stack": "mixed-4/8 · mlx-serve 26.10.1", "date": "2026-10-07", "he_strict": 151,
         "he_imports": None, "he_truncated": None, "jdhodges": 39, "veerman": 8, "he_tokens": None,
         "he_minutes": None, "thinking": "not recorded"},
        {"arm": "o1", "stack": "oQ4e · oMLX 0.7.0", "date": "2026-10-09", "he_strict": 140, "he_imports": 157,
         "he_truncated": 5, "jdhodges": 36, "veerman": 10, "he_tokens": 1807, "he_minutes": 64,
         "thinking": "yes (~1 800 tokens per answer)"},
        {"arm": "m1x", "stack": "Optimized-Speed · MTPLX 2.12.2", "date": "2026-10-09", "he_strict": 132,
         "he_imports": 151, "he_truncated": 10, "jdhodges": 35, "veerman": 10, "he_tokens": 3345, "he_minutes": 100,
         "thinking": "yes (~3 300 tokens per answer)"},
    ],
}


def _median(xs):
    xs = [float(x) for x in xs if x not in (None, "None", "")]
    return round(statistics.median(xs), 2) if xs else None


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _missing_stats() -> dict:
    return {"missing": True, "n": 0, "passed": None, "truncated": None, "total_s": None, "median_s": None,
            "median_completion": None, "median_reasoning_chars": None, "points": []}


def _arm_time(views: list[dict]) -> dict:
    st = S.suite_stats(views)
    st["missing"] = False
    st["points"] = [{"id": v["id"], "s": v["elapsed_s"], "ok": v["passed"], "trunc": v["truncated"]} for v in views]
    return st


def _tool_latency(path: Path) -> dict:
    if not path.is_file():
        return {"missing": True}
    rows = _read_jsonl(path)
    multi = [r for r in rows if S._true(r.get("multi_turn")) and r.get("turn_2_elapsed_s") is not None]
    return {"missing": False, "n": len(rows), "passed": sum(S._true(r.get("score_pass")) for r in rows),
            "turn1_median_s": _median([r.get("turn_1_elapsed_s") for r in rows]),
            "turn2_median_s": _median([r.get("turn_2_elapsed_s") for r in multi]), "turn2_n": len(multi)}


def _speed_row(arm: str, series: str, src: dict | None, source: str, absent: str | None = None) -> dict:
    row = {"arm": arm, "series": series, "name": STACKS[series]["name"], "source": source, "absent": absent,
           "t_turno_s": None, "ttft_tool_turn_s": None, "hit_tool_turn": None, "cold_ttft_s": None,
           "decode_tps": None, "prefill_tps": None, "mtp_acceptance": None, "wired_peak_gb": None, "gates_failed": [], "config": ""}
    if src is None:
        return row
    ttft = src.get("warm_ttft_s") or src.get("ttft_s") or {}
    row.update({"t_turno_s": src.get("t_turno_s"), "ttft_tool_turn_s": ttft.get("tool_turn"),
                "hit_tool_turn": (src.get("hit") or {}).get("tool_turn"), "cold_ttft_s": src.get("cold_ttft_s"),
                "decode_tps": src.get("decode_tps"), "prefill_tps": src.get("prefill_tps"),
                "mtp_acceptance": src.get("mtp_acceptance"), "wired_peak_gb": src.get("wired_peak_gb"),
                "gates_failed": list(src.get("gates_failed") or []), "config": src.get("config") or ""})
    return row


def _speed(results_dir: Path, reports: dict) -> dict:
    tt = json.loads((results_dir / "tturno-summary.json").read_text(encoding="utf-8"))
    canon = [g for g in reports.get("groups", []) if g.get("canonical")]
    out = {"drift": {}}
    for ctx in CONTEXTS:
        rows = [_speed_row(a, a, tt.get(f"{a}@{ctx}"), THIS_CAMPAIGN,
                           None if f"{a}@{ctx}" in tt else "not measured") for a in ARMS]
        for series in OTHER_SERIES:
            g = next((g for g in canon if g.get("cand") == series and str(g.get("context")) == ctx), None)
            if g is None:
                rows.append(_speed_row(series, series, None, "", "no canonical group in this band"))
            else:
                rows.append(_speed_row(g.get("arm", series), series, g, g.get("campaign", "")))
        n2 = next((g for g in canon if g.get("cand") == "n2" and str(g.get("context")) == ctx), None)
        out["drift"][ctx] = n2.get("t_turno_s") if n2 else None
        out[ctx] = rows
    return out


def _gates(quality: dict, regrade: dict, time: dict, speed: dict) -> dict:
    g1 = {}
    for p in PROFILES:
        for suite in S.SUITES:
            if suite == "humaneval" and f"n2-{p}" in regrade and f"w1-{p}" in regrade:
                base, cand = regrade[f"n2-{p}"]["with_imports"], regrade[f"w1-{p}"]["with_imports"]
            else:
                base, cand = quality[p]["n2"][suite]["passed"], quality[p]["w1"][suite]["passed"]
            margin = S.QUALITY_MARGIN[suite]
            ok = None if base is None or cand is None else cand >= base - margin
            g1.setdefault(suite, {})[p] = {"n2": base, "w1": cand, "margin": margin, "pass": ok}
    g2 = {s: {p: {"ratio": time[p][s]["ratio"],
                  "pass": None if time[p][s]["ratio"] is None else time[p][s]["ratio"] <= S.TIME_RATIO}
              for p in PROFILES} for s in S.TIME_SUITES}
    g3 = {}
    for ctx in CONTEXTS:
        rows = {r["arm"]: r for r in speed[ctx]}
        b, c = rows["n2"]["t_turno_s"], rows["w1"]["t_turno_s"]
        ratio = round(c / b, 2) if b and c else None
        g3[ctx] = {"n2": b, "w1": c, "ratio": ratio, "pass": None if ratio is None else c <= G3_RATIO * b}

    def all_pass(cells):
        vals = [c["pass"] for c in cells]
        return None if None in vals else all(vals)

    decision = {
        "g1_t1": all_pass([g1[s]["t1"] for s in g1]), "g1_t0": all_pass([g1[s]["t0"] for s in g1]),
        "g2_t1": all_pass([g2[s]["t1"] for s in g2]), "g3": all_pass(list(g3.values())),
    }
    decision["promote"] = None if None in decision.values() else all(decision.values())
    return {"g1": g1, "g2": g2, "g3": g3, "time_ratio": S.TIME_RATIO, "g3_ratio": G3_RATIO, "decision": decision}


def collect(results_dir: Path = RESULTS, reports_json: Path = REPORTS_JSON) -> dict:
    results_dir, reports_json = Path(results_dir), Path(reports_json)
    reports = json.loads(reports_json.read_text(encoding="utf-8"))
    quality, time, tool_latency = {}, {}, {}
    for p in PROFILES:
        loaded = {a: S.load_arm(results_dir / "ab" / p / a) for a in ARMS}
        quality[p] = {a: {} for a in ARMS}
        time[p] = {}
        for suite in S.SUITES:
            arms = {}
            for a in ARMS:
                views = loaded[a].get(suite)
                if views is None:
                    quality[p][a][suite] = {"n": 0, "passed": None, "missing": True}
                    arms[a] = _missing_stats()
                else:
                    quality[p][a][suite] = {"n": len(views), "passed": sum(v["passed"] for v in views),
                                            "missing": False}
                    arms[a] = _arm_time(views)
            b, c = arms["n2"]["median_s"], arms["w1"]["median_s"]
            time[p][suite] = {"arms": arms, "ratio": round(c / b, 2) if b and c else None}
        tool_latency[p] = {s: {a: _tool_latency(results_dir / "ab" / p / a / f"{s}.jsonl") for a in ARMS}
                           for s in S.SUITES if s in S.TOOL_SUITES}
    regrade_path = results_dir / "humaneval-regrade.json"
    regrade = json.loads(regrade_path.read_text(encoding="utf-8")) if regrade_path.is_file() else {}
    regrade = {k: {"n": v.get("n"), "strict": v.get("strict"), "with_imports": v.get("with_imports"),
                   "truncated": len(v.get("truncated") or [])} for k, v in regrade.items()}
    speed = _speed(results_dir, reports)
    return {"arms": list(ARMS), "profiles": list(PROFILES), "suites": list(S.SUITES), "stacks": STACKS,
            "rig": reports.get("rig", []), "quality": quality, "humaneval_regrade": regrade, "time": time,
            "tool_latency": tool_latency, "speed": speed, "legacy": LEGACY,
            "gates": _gates(quality, regrade, time, speed)}
