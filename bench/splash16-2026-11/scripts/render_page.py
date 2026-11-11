#!/usr/bin/env python3
"""Collect the Splash 1.6.0 vs 1.5.0 campaign results and render the public report page.

collect() reads results/ through the committed summarizers (summarize_load.py for the aging and churn JSONL,
engine_restart.verdict for the restart, flashnext-concurrency's summarize_parallel.py and summarize_claude.py
for Task 4, swift15's summarize_ab.py for Task 6, the daily driver's summarize_driver.py for Task 2) and
returns a plain dict. render() turns that dict into one self-contained HTML page (inline SVG, payload embedded
as JSON). main() writes the page and the payload.

    python3 bench/splash16-2026-11/scripts/render_page.py \\
        [--results-dir DIR] [--out-html reports/qwen38-flashnext-splash160.html] [--out-json results/page-data.json]

Numbers that exist only in a stage report (no script computes them) are constants below, each with its
source file. The per-hour table of Task 7 was ad hoc in etapa7-agente-4h.md; _soak_hours() recomputes it.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import html
import importlib.util
import io
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional, Sequence

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE.parent
RESULTS = CAMPAIGN / "results"
REPO = CAMPAIGN.parents[1]
BENCH = REPO / "bench"
CONCURRENCY = BENCH / "flashnext-concurrency-2026-10" / "scripts"
SPLASH_E1 = BENCH / "splash-concurrency-2026-10" / "results"  # Task 4 reference, tag e1, Splash 1.5.0
K2A_T1 = BENCH / "splash-longctx-2026-10" / "results" / "q262" / "t1" / "k2a"  # Task 6 base, Splash 1.4.0

sys.path.insert(0, str(HERE))
if str(CONCURRENCY) not in sys.path:
    sys.path.append(str(CONCURRENCY))
import engine_restart  # noqa: E402
import summarize_load  # noqa: E402
from claude_requests import read_requests, summarize_requests  # noqa: E402
from report_charts import _baseline, _scale, _svg, _text, table_view  # noqa: E402
from summarize_claude import summarize_claude  # noqa: E402
from summarize_parallel import summarize as summarize_parallel  # noqa: E402


def _load_file(name: str, path: Path):
    """Import a module from a path without adding its directory to sys.path (swift15's scripts/ has its own
    render_page.py, which would shadow this one)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


summarize_ab = _load_file("summarize_ab", BENCH / "swift15-flashnext-2026-10" / "scripts" / "summarize_ab.py")
summarize_driver = _load_file("summarize_driver",
                              BENCH / "qwen38-flashnext-daily-driver-2026-09" / "scripts" / "summarize_driver.py")

RIG = "Mac Studio M4 Max 128 GB"
WEIGHTS = "ukisai Swift 1.5 Qwen3.8 Flash-Next GGUF IQ4_XS (revision 0142554)"
DATES = ["2026-11-06", "2026-11-08"]
OLD, NEW = "1.5.0", "1.6.0"
TITLE = "Splash 1.6.0 vs 1.5.0"
CTX = {32768: "32K", 131072: "128K", 262144: "256K", 524288: "512K", 1000000: "1M"}

# Verdict per question. Source: results/summary.md, "Respostas". Tasks 3 and 6 were skipped by the user.
VERDICTS: dict[str, dict[str, Any]] = {
    "1": {"question": "Do the packs load, and does any client break?", "result": "pass",
          "text": "pass", "skipped": False},
    "2": {"question": "Does 1.6.0 keep the turn time and the cache of one stream?", "result": "pass",
          "text": "pass", "skipped": False},
    "3": {"question": "Does the #644 decode drop happen here, and does 1.6.0 remove it?", "result": "na",
          "text": "no regression seen, no verdict", "skipped": True},
    "4": {"question": "Does the new scheduler change the cost of a second session?", "result": "fail",
          "text": "fail", "skipped": False},
    "5": {"question": "Does the memory ledger remove the stalls under a memory limit?", "result": "pass",
          "text": "pass", "skipped": False},
    "6": {"question": "Does quality stay the same?", "result": "na", "text": "no regression seen",
          "skipped": True},
    "7": {"question": "Does a 4-hour agent load stay stable?", "result": "pass",
          "text": "no regression; fix not proven", "skipped": False},
}

# API checks C1 to C6. Source: results/etapa1-contrato.md, "API" (observed values of contract-<ver>.jsonl).
CONTRACT = [
    ("C1", "Messages with stop_sequences as a string", "200", "400 (stop_sequences must be an array of strings)"),
    ("C2", "Messages with stop_sequences as an array", "200", "200"),
    ("C3", "stop of 16385 characters", "200", "400"),
    ("C4", "POST /v1/chat/completions/count_tokens", "404", "55 tokens, equal to usage.prompt_tokens"),
    ("C5", "request ended by a stop sequence, /status counter", "cancelled +1", "completed +1"),
    ("C6", "/status schema", "6", "8, with memory_governor, ttft_parts_ms and decode_gap_causes"),
]

# Order of the Task 4 boots in results/status-t4.jsonl (results/etapa4-concorrencia.md, "Espera por memória").
# The Claude Code boots (rc1, rc2, rc2s) follow.
T4_BOOTS = ["k2c1 32K", "k2c1 128K", "k2c2a 32K", "k2c2a 128K", "k2c2LL 256K"]
STALL_S = 60.0

NOT_MEASURED = [
    "The tool-call probe (toolcall-probe.sh, 20 sessions), Task 6.",
    "longctx_probe.py at 131072 and 262144, Task 6.",
    "The veerman suite (12 questions), Task 6.",
    "Task 3 profile p on 1.5.0 from round 5 on, profile q (the exact #644 pack) and the repeat in reversed order.",
]
CAVEATS = [
    "Task 4 saw a {x} change in the summed decode of two 256K sessions between days, with no cause found: "
    "{ref} tok/s on 2026-10-29 against {ctl} tok/s on 2026-11-07, both on 1.5.0. Absolute numbers compared "
    "across days carry little weight.",
    "Task 7 ran 1.6.0 first and 1.5.0 after it, with one boot each and no reversed order. Its {n_new} vs "
    "{n_old} completed pairs may carry order and time-of-day effects.",
]

GITHUB = "https://github.com/snagnever/macstudio-local-llm"
PLAN_URL = f"{GITHUB}/blob/main/bench/splash16-2026-11/plan.md"
RESULTS_URL = f"{GITHUB}/tree/main/bench/splash16-2026-11/results"
ISSUE_644 = "https://github.com/incoai/splash/issues/644"
NOTES_160 = "https://github.com/incoai/splash/blob/1.6.0/docs/release-notes/1.6.0.md"
API_DOC = "https://github.com/incoai/splash/blob/1.6.0/docs/api.md"


# ---- collect ----

def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def _med(xs) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def _status_last(records: list[dict[str, Any]]) -> dict[str, Any]:
    st = [r for r in records if r.get("kind") == "status"]
    return st[-1] if st else {}


def _claim_wait(status: dict[str, Any]) -> dict[str, Optional[float]]:
    cw = (((status.get("metrics") or {}).get("ttft_parts_ms") or {}).get("claim_wait")) or {}
    return {"max_s": cw["max"] / 1000 if "max" in cw else None,
            "total_s": cw["total"] / 1000 if "total" in cw else None}


def _task1(results: Path) -> dict[str, Any]:
    proxy = {}
    for ver in (OLD, NEW):
        rs = _rows(results / f"proxy-{ver}.jsonl")
        proxy[ver] = {"hits": len(rs), "key_hits": sum(1 for r in rs if r.get("has_key"))}
    er = json.loads((results / "engine-restart.json").read_text(encoding="utf-8"))
    attempts = er["attempts"]
    served = [a for a in attempts if a["status"] == 200]
    v = engine_restart.verdict(attempts, er["boot_seconds"], er["context_before"], er["context_after"])
    codes = Counter(a.get("code") for a in attempts if a["status"] == 503)
    restart = {"first_200_s": served[0]["t"] if served else None, "boot_s": er["boot_seconds"],
               "codes": dict(sorted(codes.items())), "context_kept": er["context_after"] == er["context_before"],
               "context": er["context_after"], "pass": v["pass"],
               "recorded_pass": er.get("verdict", {}).get("pass")}
    c7: dict[str, Any] = {"cached": {}, "first_output": {}, "first_prompt": None}
    for ver in (OLD, NEW):
        valid = [r["observed"] for r in _rows(results / f"contract-c7-{ver}.jsonl")
                 if r.get("check") == "C7" and isinstance(r.get("observed"), dict) and "cached" in r["observed"]]
        c7["cached"][ver] = [o["cached"] for o in valid]
        c7["first_output"][ver] = [o["first_output"] for o in valid]
        c7["first_prompt"] = valid[0]["first_prompt"] if valid else c7["first_prompt"]
    return {"proxy": proxy, "restart": restart, "c7": c7}


def _task2(results: Path) -> dict[str, Any]:
    records = []
    for pat in ("k2f-*-t1.0-p*.jsonl", "k2g-*-t1.0-p*.jsonl", "k2f-*-t1.0-l1.jsonl", "k2g-*-t1.0-l1.jsonl"):
        for f in sorted(results.glob(pat)):
            records += _rows(f)
    with contextlib.redirect_stderr(io.StringIO()):  # summarize_driver warns about mixed session ids (ABBA)
        s = summarize_driver.summarize(records)

    def row(ctx: int) -> Optional[dict[str, Any]]:
        f, g = s.get(("k2f", ctx)), s.get(("k2g", ctx))
        if not f or not g:
            return None
        return {"ctx": ctx, "old_s": f["t_turno_s"], "new_s": g["t_turno_s"],
                "ratio": g["t_turno_s"] / f["t_turno_s"], "old_decode": f["decode_tps"],
                "new_decode": g["decode_tps"], "old_cold_s": f["cold_ttft_s"], "new_cold_s": g["cold_ttft_s"]}

    return {"bands": [row(c) for c in (32768, 131072, 262144)], "half_million": row(524288),
            "one_million": row(1000000), "rule": 1.03}


def _aging_run(path: Path, run: str) -> dict[str, Any]:
    recs = _rows(path)
    req = [r for r in recs if r["kind"] == "request"]
    pre, end, idle = (summarize_load._probe(recs, k) for k in ("pre", "fim", "ocioso"))
    ratio = end / pre if pre and end else None
    st = _status_last(recs)
    gaps = [g for r in req for g in r.get("gaps_s") or []]
    return {"run": run, "release": NEW if "-160-" in f"-{run}-" else OLD, "profile": run.split("-")[0],
            # completed rounds: every request of the round answered (an interrupted round has failed requests)
            "rounds": sum(1 for rnd in {r["round"] for r in req}
                          if all(r.get("status") == 200 and not r.get("error") for r in req if r["round"] == rnd)),
            "pre": pre, "end": end, "idle": idle, "ratio": ratio,
            "verdict": summarize_load.verdict(ratio) if ratio else None, "stall": summarize_load.stall(req),
            "max_gap_s": max(gaps) if gaps else None,
            "denied_reservations": (st.get("memory_governor") or {}).get("denied_reservations"),
            "pages_moved": (st.get("kv") or {}).get("pages_moved")}


def _task3(results: Path) -> dict[str, Any]:
    order = ["a-150-r1", "a-160-r1", "p-160-r1", "p-150-r1"]
    return {"runs": [_aging_run(results / f"aging-{r}.jsonl", r) for r in order]}


def _p99(gaps: list[float]) -> Optional[float]:
    gaps = sorted(gaps)
    return gaps[min(len(gaps) - 1, int(0.99 * len(gaps)))] if gaps else None  # summarize_load.stall's p99


def _task5(results: Path) -> dict[str, Any]:
    runs = []
    for run in ("150-r1", "160-r1", "160-r2", "150-r2"):
        recs = _rows(results / f"churn-{run}.jsonl")
        req = [r for r in recs if r["kind"] == "request"]
        gaps = [g for r in req for g in r.get("gaps_s") or []]
        st = _status_last(recs)
        m = st.get("metrics") or {}
        runs.append({
            "run": run, "release": NEW if run.startswith("160") else OLD, "requests": len(req),
            "unanswered": sum(1 for r in req if r.get("status") != 200 or r.get("error")),
            "max_gap_s": max(gaps) if gaps else None, "p99_gap_s": _p99(gaps),
            "gaps_over_5s": sum(1 for g in gaps if g > 5), "ttft_p50_s": _med(r.get("ttft_s") for r in req),
            "rounds": len({r["round"] for r in req}), "stall": summarize_load.stall(req),
            "server_prefill": m.get("prefill_tokens_per_second"), "server_decode": m.get("decode_tokens_per_second"),
            "ssd_read_gb": ((st.get("disk") or {}).get("read_bytes") or 0) / 1e9,
            "denied_reservations": (st.get("memory_governor") or {}).get("denied_reservations"),
        })
    return {"runs": runs, "max_memory": "64G", "minutes": 15}


def _arm(results: Path, arm: str, ctx: int, tag: str, ref_arm: Optional[str] = None) -> Optional[dict[str, Any]]:
    s = summarize_parallel(results, arm, ctx, tag, ref_arm=ref_arm, logs_dir=results / "_no_logs")
    if not s["streams"]:
        return None
    turns = [st["t_turno_s"] for st in s["streams"]]
    ratios = [st["ratio"] for st in s["streams"] if st["ratio"] is not None]
    return {"streams_s": turns, "worst_s": max(t for t in turns if t is not None),
            "worst_ratio": max(ratios) if ratios and ref_arm else None,
            "decode_sum": s["throughput"]["aggregate_decode_tps"],
            "warm_tool_s": [st["warm_ttft_tool_s"] for st in s["streams"]]}


def _side_over_60(path: Path) -> tuple[int, Optional[float]]:
    if not path.exists():
        return 0, None
    vals = [r.get("ttft_s") if r.get("ttft_s") is not None else r.get("total_s") for r in _rows(path)]
    over = [v for v in vals if (v or 0) > STALL_S]
    return len(over), max(over) if over else None


def _t4_boots(path: Path) -> list[dict[str, Any]]:
    """Split status-t4.jsonl into boots (the claim_wait sample counter drops at each new boot) and keep the
    last /status of each boot."""
    boots, cur, prev = [], None, None
    for r in _rows(path):
        cw = r["status"]["metrics"]["ttft_parts_ms"]["claim_wait"]
        if prev is not None and cw["samples"] < prev:
            boots.append(cur)
        cur, prev = cw, cw["samples"]
    if cur is not None:
        boots.append(cur)
    out = []
    for i, cw in enumerate(boots):
        arm = T4_BOOTS[i] if i < len(T4_BOOTS) else f"Claude Code boot {i - len(T4_BOOTS) + 1}"
        out.append({"arm": arm, "max_s": cw["max"] / 1000, "total_s": cw["total"] / 1000, "samples": cw["samples"]})
    return out


def _task4(results: Path, e1: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"k2c1": {}, "k2c2a": {}}
    for ctx in (32768, 131072):
        out["k2c1"][str(ctx)] = {"ref": _arm(e1, "k2c1", ctx, "e1"), "new": _arm(results, "k2c1", ctx, "g1")}
        out["k2c2a"][str(ctx)] = {"ref": _arm(e1, "k2c2a", ctx, "e1", "k2c1"),
                                  "new": _arm(results, "k2c2a", ctx, "g1", "k2c1")}
    out["k2c2LL"] = {"ref": _arm(e1, "k2c2LL", 262144, "e1"), "control": _arm(results / "c150", "k2c2LL", 262144, "c1"),
                     "new": _arm(results, "k2c2LL", 262144, "g1")}
    side, side_max = {}, {}
    for key, path in (("k2c2a-32768", results / "k2c2a-32768-g1-aux.jsonl"),
                      ("k2c2a-131072", results / "k2c2a-131072-g1-aux.jsonl"),
                      ("k2c2LL-262144", results / "k2c2LL-262144-g1-aux.jsonl"),
                      ("k2c2LL-262144-control", results / "c150" / "k2c2LL-262144-c1-aux.jsonl"),
                      ("k2c2a-131072-ref", e1 / "k2c2a-131072-e1-aux.jsonl")):
        side[key], side_max[key] = _side_over_60(path)
    out["side_over_60s"], out["side_max_s"] = side, side_max
    out["claim_wait"] = _t4_boots(results / "status-t4.jsonl")
    return out


def _cc_block(s: dict[str, Any], kind: str) -> dict[str, Any]:
    if kind == "pair":
        prof, warm = s["profiles"]["realistic"], ((s["requests"].get("pair") or {}).get("warm") or {})
    else:
        prof, warm = s["subagents"]["profile"], ((s["subagents"]["requests"] or {}).get("warm") or {})
    return {"wall_s": prof["pair_wall_s"], "ttft_p50": warm.get("ttft_p50"), "ttft_p90": warm.get("ttft_p90"),
            "tps_p50": warm.get("tps_p50"), "tps_min": warm.get("tps_min")}


def _task_done(results: Path) -> str:
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(results.glob("cc-rc*-*.json"))]
    return f"{sum(1 for r in runs if r.get('task_done'))}/{len(runs)}"


def _claude_code(results: Path) -> dict[str, Any]:
    new = summarize_claude(results, "rc", {"s": "subagents"})
    old = summarize_claude(results / "c150", "rc", {"s": "subagents"})
    alone = ((new["requests"].get("alone") or {}).get("warm")) or {}
    return {"pair": {"old": _cc_block(old, "pair"), "new": _cc_block(new, "pair")},
            "subagents": {"old": _cc_block(old, "subagents"), "new": _cc_block(new, "subagents")},
            "alone_new": {"ttft_p50": alone.get("ttft_p50"), "ttft_p90": alone.get("ttft_p90")},
            "task_done": {"old": _task_done(results / "c150"), "new": _task_done(results)},
            "context": 131072, "reps": {"old": 2, "new": 3}}


def _task6(results: Path, base_dir: Path) -> dict[str, Any]:
    stats = summarize_ab.compare(summarize_ab.load_arm(base_dir), summarize_ab.load_arm(results / "v16" / "t1" / "k2g"))
    g = summarize_ab.gates(stats["base"], stats["cand"])
    suites = [{"suite": k, "n": b["n"], "base": b["passed"], "cand": stats["cand"][k]["passed"],
               "base_truncated": b["truncated"], "cand_truncated": stats["cand"][k]["truncated"],
               "g1": g[f"G1:{k}"]} for k, b in stats["base"].items()]
    return {"suites": suites, "base": "k2a, Splash 1.4.0", "cand": "k2g, Splash 1.6.0"}


def _soak_hours(results: Path, tag: str, probes: dict[str, list[dict[str, Any]]], n_pairs: int) -> list[dict[str, Any]]:
    """Per-hour rows of etapa7-agente-4h.md. The report took a pair's hour from the cc-*.json write time, which
    git does not keep. Here a pair ends at the sum of the earlier pair walls (the slower session of each pair)
    and probe walls, counted from the end of the first probe; this gives the report's pairs per hour. The
    probe p50 pools the 3 reps after every pair of the hour."""
    t, ends = 0.0, []
    for n in range(1, n_pairs + 1):
        walls = [json.loads((results / f"cc-soak{tag}p{n}-{k}.json").read_text(encoding="utf-8"))["wall_s"]
                 for k in ("c", "d")]
        t += max(walls)
        ends.append((n, t))
        t += sum(p.get("wall_s") or 0 for p in probes.get(f"pair{n}", []))
    hours: dict[int, list[int]] = {}
    for n, end in ends:
        hours.setdefault(int(end // 3600), []).append(n)
    return [{"hour": h, "pairs": len(ns),
             "probe_p50": _med(p["decode_tok_s"] for n in ns for p in probes.get(f"pair{n}", []))}
            for h, ns in sorted(hours.items())]


def _soak(results: Path, tag: str) -> dict[str, Any]:
    recs = _rows(results / f"soak-{tag}.jsonl")
    probes: dict[str, list[dict[str, Any]]] = {}
    for r in recs:
        if r["kind"] == "probe":
            probes.setdefault(r["label"], []).append(r)
    n = 0
    while all((results / f"cc-soak{tag}p{n + 1}-{k}.json").exists() for k in ("c", "d")):
        n += 1
    sessions = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(results.glob(f"cc-soak{tag}p*-*.json"))]
    reqs: list[dict[str, Any]] = []
    offset = 0.0
    for p in sorted(results.glob(f"req-soak{tag}p*.jsonl")):  # pairs laid end to end, as summarize_claude does
        rows = read_requests(p)
        reqs += [dict(r, t_start_s=r["t_start_s"] + offset, t_end_s=r["t_end_s"] + offset) for r in rows]
        if reqs:
            offset = max(r["t_end_s"] for r in reqs) + 1.0
    warm = summarize_requests(reqs)["warm"] or {}
    after = [p["decode_tok_s"] for label, ps in probes.items() if label != "pre" for p in ps]
    pre = _med(p["decode_tok_s"] for p in probes.get("pre", []))
    end = _med(p["decode_tok_s"] for p in probes.get(f"pair{n}", []))
    st = _status_last(recs)
    m = st.get("metrics") or {}
    return {"pairs": n, "requests": len(reqs), "errors": sum(1 for r in reqs if r.get("status", 200) != 200),
            "task_done": f"{sum(1 for s in sessions if s.get('task_done'))}/{len(sessions)}",
            "probe_pre": pre, "probe_end": end, "probe_min": min(after) if after else None,
            "ratio": end / pre if pre and end else None,
            "verdict": summarize_load.verdict(end / pre) if pre and end else None,
            "probe_max_gap_s": max((p.get("max_gap_s") or 0) for ps in probes.values() for p in ps),
            "warm_ttft_p50": warm.get("ttft_p50"), "warm_ttft_p90": warm.get("ttft_p90"),
            "server_prefill": m.get("prefill_tokens_per_second"), "server_decode": m.get("decode_tokens_per_second"),
            "denied_reservations": (st.get("memory_governor") or {}).get("denied_reservations"),
            "claim_wait_max_s": _claim_wait(st)["max_s"], "hours": _soak_hours(results, tag, probes, n)}


def collect(results_dir: Path = RESULTS, e1_dir: Path = SPLASH_E1, k2a_dir: Path = K2A_T1) -> dict[str, Any]:
    results = Path(results_dir)
    return {
        "title": TITLE, "rig": RIG, "weights": WEIGHTS, "dates": DATES, "releases": {"old": OLD, "new": NEW},
        "verdicts": VERDICTS, "contract": [list(r) for r in CONTRACT],
        "task1": _task1(results), "task2": _task2(results), "task3": _task3(results),
        "task4": _task4(results, Path(e1_dir)), "claude_code": _claude_code(results), "task5": _task5(results),
        "task6": _task6(results, Path(k2a_dir)),
        "task7": {"new": _soak(results, "g"), "old": _soak(results, "f"), "order": [NEW, OLD]},
    }


# ---- render helpers ----

def _e(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _f(v: Optional[float], digits: int = 1, unit: str = "") -> str:
    return "n/a" if v is None else f"{v:.{digits}f}{unit}"


def _s(v: Optional[float], digits: int = 1) -> str:
    return _f(v, digits, " s")


def _pct(new: Optional[float], old: Optional[float]) -> Optional[int]:
    return None if not new or not old else round((new / old - 1) * 100)


def _table(head: list[str], rows: list[list[str]], cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return (f'<div class="tbl-scroll"><table{c}><thead><tr>' + "".join(f"<th>{h}</th>" for h in head)
            + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{x}</td>" for x in r) + "</tr>" for r in rows)
            + "</tbody></table></div>")


def _legend(items: list[tuple[str, str]]) -> str:
    return ('<div class="legend">' + "".join(f'<span class="chip"><span class="sw" style="background:{c}"></span>'
                                             f'{_e(t)}</span>' for c, t in items) + "</div>")


def _panel(chart: str, caption: str, table: str = "") -> str:
    return (f'<div class="panel"><div class="chart">{chart}</div><p class="p-interp">{caption}</p>{table}</div>')


def _badge(v: dict[str, Any]) -> str:
    out = f'<span class="badge {_e(v["result"])}">{_e(v["text"])}</span>'
    if v["skipped"]:
        out += '<span class="badge skip">Skipped by the user: partial results</span>'
    return out


def _title_text(s: str) -> str:
    return _text(0, 14, s, "ttl", "start")


def _tip(s: str) -> str:
    return f"<title>{html.escape(s)}</title>"


W = 560
OLD_C, OLD_OTHER_C, NEW_C = "var(--s1)", "var(--s1l)", "var(--s2)"


def svg_hbars(title: str, groups: list[dict[str, Any]], vmax: float, unit: str, label_w: float = 170.0,
              rule: Optional[tuple[float, str]] = None) -> str:
    """Horizontal bars in groups: {"label", "bars": [{"name", "value", "color"}]}. `rule` draws a dashed
    vertical line at a value (a gate)."""
    plot_w, bar_h, pitch, gap, top = W - label_w - 70, 12.0, 16.0, 12.0, 44.0 if rule else 28.0
    body = [_title_text(title)]
    y = top
    for g in groups:
        body.append(_text(label_w - 8, y + 10 + (len(g["bars"]) - 1) * pitch / 2, g["label"], "lbl", "end"))
        for b in g["bars"]:
            w = _scale(b["value"], vmax, plot_w)
            tip = _tip(f"{g['label']}, {b['name']}: {b['value']:.1f} {unit}")
            body.append(f'<rect class="bar" x="{label_w:.1f}" y="{y:.1f}" width="{max(w, 1.5):.1f}" height="{bar_h}" '
                        f'rx="2" fill="{b["color"]}">{tip}</rect>')
            body.append(_text(label_w + w + 6, y + 10, f"{b['value']:.1f} {unit}", "value", "start"))
            y += pitch
        y += gap
    base = y - gap + 4
    if rule:
        x = label_w + _scale(rule[0], vmax, plot_w)
        body.append(f'<line x1="{x:.1f}" y1="{top - 6}" x2="{x:.1f}" y2="{base:.1f}" stroke="var(--crit)" '
                    f'stroke-dasharray="4 3" opacity="0.8"/>')
        body.append(_text(x + 4, top - 8, rule[1], "tick", "start"))
    body.append(_baseline(label_w, label_w + plot_w, base))
    step = vmax / 5
    for i in range(6):
        t = i * step
        body.append(_text(label_w + _scale(t, vmax, plot_w), base + 14, f"{t:g}" + (f" {unit}" if i == 5 else ""),
                          "tick", "end" if i == 5 else "middle"))
    return _svg(W, int(base + 22), title, body)


def svg_hour_lines(title: str, series: list[dict[str, Any]], ymin: float = 60.0, ymax: float = 120.0) -> str:
    """Probe decode per soak hour, one line per release: {"name", "color", "points": [(hour, y)], "threshold"}.
    The y axis starts at `ymin`; a series' threshold (0.85 × its probe before the load) is a dashed line."""
    left, plot_w, plot_h, top = 50.0, 380.0, 170.0, 30.0
    base = top + plot_h
    hours = sorted({h for s in series for h, _ in s["points"]})
    step = plot_w / max(len(hours) - 1, 1)
    xpos = {h: left + i * step for i, h in enumerate(hours)}

    def ypos(v: float) -> float:
        return base - _scale(v - ymin, ymax - ymin, plot_h)

    body = [_title_text(title), _baseline(left, left + plot_w, base), _text(left - 6, base + 4, f"{ymin:g}", "tick", "end")]
    for frac in (0.25, 0.5, 0.75, 1.0):
        v = ymin + frac * (ymax - ymin)
        body.append(f'<line x1="{left}" y1="{ypos(v):.1f}" x2="{left + plot_w}" y2="{ypos(v):.1f}" '
                    f'stroke="currentColor" opacity="0.12"/>')
        body.append(_text(left - 6, ypos(v) + 4, f"{v:g}", "tick", "end"))
    for s in series:
        if s.get("threshold"):
            yy = ypos(s["threshold"])
            tip = _tip(f"{s['name']} stable limit: {s['threshold']:.1f} tok/s")
            body.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{left + plot_w}" y2="{yy:.1f}" stroke="{s["color"]}" '
                        f'stroke-dasharray="4 3" opacity="0.7">{tip}</line>')
    lows = [s["threshold"] for s in series if s.get("threshold")]
    if lows:
        body.append(_text(left + 4, ypos(min(lows)) + 14, "dashed: stable limit, 0.85 × probe before the load",
                          "tick", "start"))
    for k, s in enumerate(series):
        pts = [(xpos[h], ypos(v)) for h, v in s["points"]]
        body.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                    + f'" fill="none" stroke="{s["color"]}" stroke-width="2"/>')
        for (h, v), (x, y) in zip(s["points"], pts):
            tip = _tip(f"{s['name']}, hour {h}: {v:.1f} tok/s")
            body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{s["color"]}" stroke="var(--surface)" '
                        f'stroke-width="1.5">{tip}</circle>')
        lx, ly = pts[-1]
        body.append(_text(lx + 8, ly + 4 + (10 if k else -6), f"{s['name']} {s['points'][-1][1]:.1f}", "value", "start"))
    for h in hours:
        body.append(_text(xpos[h], base + 16, str(h), "tick"))
    body.append(_text(left + plot_w / 2, base + 32, "hour of the soak (hour 4 holds only the last pair)", "tick"))
    return _svg(W, int(base + 40), title, body)


# ---- sections ----

def _more_requests(d: dict[str, Any]) -> str:
    """Task 5: how many more requests a 1.6.0 run serves than a 1.5.0 run, as a range over the run pairs."""
    new = [r["requests"] for r in d["task5"]["runs"] if r["release"] == NEW]
    old = [r["requests"] for r in d["task5"]["runs"] if r["release"] == OLD]
    lo, hi = round((min(new) / max(old) - 1) * 100), round((max(new) / min(old) - 1) * 100)
    return f"{lo}%" if lo == hi else f"{lo} to {hi}%"


def _hero(d: dict[str, Any]) -> str:
    ll = d["task4"]["k2c2LL"]
    pct = _pct(ll["new"]["worst_s"], ll["control"]["worst_s"])
    cw = next(b["max_s"] for b in d["task4"]["claim_wait"] if b["arm"] == "k2c2LL 256K")
    ratios = [b["ratio"] for b in d["task2"]["bands"]]
    old_gap = max(r["max_gap_s"] for r in d["task5"]["runs"] if r["release"] == OLD)
    new_gap = max(r["max_gap_s"] for r in d["task5"]["runs"] if r["release"] == NEW)
    more = _more_requests(d)
    aging = [r["ratio"] for r in d["task3"]["runs"] if r["ratio"] and r["profile"] == "a"]
    soak = [d["task7"][k]["ratio"] for k in ("new", "old")]
    drop = aging + soak
    tiles = [
        ("Rig launcher", "Stays on 1.5.0", "Task 4 fails the switch rule of the plan."),
        ("Two 256K sessions", f"+{pct}%",
         f"Worst stream {_s(ll['control']['worst_s'])} on 1.5.0 and {_s(ll['new']['worst_s'])} on 1.6.0, same "
         f"day. Requests wait up to {_s(cw)} for memory (claim_wait)."),
        ("One stream", "Same", f"Turn-time ratio 1.6.0 ÷ 1.5.0 is {min(ratios):.2f} to {max(ratios):.2f} at 32K, "
                               "128K and 256K."),
        ("64 GB memory limit", f"{old_gap:.1f} s → {new_gap:.1f} s",
         f"Largest decode gap. 1.6.0 also serves {more} more requests in the same 15 minutes."),
        ("#644 decode drop", "Not seen", f"Short-probe ratio end ÷ start {min(drop):.2f} to {max(drop):.2f} on both "
                                         "releases, with the KV pool full."),
    ]
    tiles_html = "".join(f'<div class="tile"><p class="t-lab">{_e(a)}</p><p class="t-big">{_e(b)}</p>'
                         f'<p class="t-sub">{_e(c)}</p></div>' for a, b, c in tiles)
    lead = (f"<b>Stay on Splash 1.5.0 if you run two long sessions.</b> Two 256K sessions are up to {pct}% slower "
            f"on 1.6.0, because requests wait for memory (<code>claim_wait</code> up to {_s(cw)}). A single stream "
            "runs at the same speed. Under a memory limit, 1.6.0 is clearly better. The "
            f'<a href="{ISSUE_644}">#644</a> decode drop did not appear on either release.')
    meta = (f"Rig: {_e(d['rig'])}. Weights: {_e(d['weights'])}. Measured {_e(d['dates'][0])} to "
            f"{_e(d['dates'][1])}. Releases: Splash 1.5.0 and 1.6.0 (<a href=\"{NOTES_160}\">release notes</a>).")
    return (f'<section class="hero" id="verdict"><p class="hero-lead">{lead}</p><p class="s-note">{meta}</p>'
            f'<div class="tiles">{tiles_html}</div></section>')


def _q(n: int, d: dict[str, Any], answer: str, body: str) -> str:
    v = d["verdicts"][str(n)]
    return (f'<section class="q" id="task{n}"><h3>Task {n}. {_e(v["question"])}</h3>'
            f'<p class="verdict-line">{_badge(v)}</p><p class="s-note">{answer}</p>{body}</section>')


def _task1_html(d: dict[str, Any]) -> str:
    t1 = d["task1"]
    r, p = t1["restart"], t1["proxy"]
    rows = [[f"<code>{_e(c)}</code> {_e(req)}", _e(o), _e(nw)] for c, req, o, nw in d["contract"]]
    rows.append(["requests that carried the API key through <code>http_proxy</code>", str(p[OLD]["key_hits"]),
                 str(p[NEW]["key_hits"])])
    rows.append(["engine restart (SIGKILL during a stream)", "not run",
                 f"first 200 at {_s(r['first_200_s'])}; 503 with Retry-After"])
    reused = {v: max(0, max(c) - t1["c7"]["first_prompt"]) if c else None for v, c in t1["c7"]["cached"].items()}
    rows.append(["<code>C7</code> reply tokens reused after a thinking cut", str(reused[OLD]), str(reused[NEW])])
    answer = ("Both releases answer every check. 1.6.0 rejects <code>stop_sequences</code> as a string and a stop "
              "string over 16384 characters, as the plan expected. The rest is in "
              "<a href=\"#api\">API contract notes</a>.")
    return _q(1, d, answer, _table(["check", OLD, NEW], rows, "wide"))


def _task2_html(d: dict[str, Any]) -> str:
    t2 = d["task2"]
    rows = []
    for b in t2["bands"] + [t2["half_million"], t2["one_million"]]:
        if b:
            rows.append([CTX[b["ctx"]], _s(b["old_s"]), _s(b["new_s"]), f"{b['ratio']:.3f}",
                         _f(b["old_decode"]), _f(b["new_decode"]), _s(b["old_cold_s"]), _s(b["new_cold_s"])])
    answer = (f"Turn time (<code>T_turno</code>: warm TTFT of a tool turn plus 512 tokens of decode) stays within "
              f"the {t2['rule']:.2f} rule at 32K, 128K and 256K, with 3 boots per release in ABBA order. 512K ties. "
              "At 1M the ratio is 1.031 with one rep per release; the rule does not cover 1M, so it is an "
              "observation. 1M started without <code>capacity_exhausted</code>.")
    return _q(2, d, answer, _table(["context", f"{OLD} T_turno", f"{NEW} T_turno", "ratio", f"{OLD} decode",
                                    f"{NEW} decode", f"{OLD} cold TTFT", f"{NEW} cold TTFT"], rows))


def _task3_html(d: dict[str, Any]) -> str:
    rows = []
    for r in d["task3"]["runs"]:
        rows.append([f"<code>{_e(r['run'])}</code>", r["release"], f"{r['rounds']} of 6", _f(r["pre"]), _f(r["end"]),
                     _f(r["idle"]), _f(r["ratio"], 2), _e({"estavel": "stable"}.get(r["verdict"], "no end probe")),
                     _s(r["max_gap_s"], 2), _e(r["denied_reservations"])])
    answer = ("Six rounds of three new 191K-token sessions at 262144, one boot per run. No run showed a decode drop "
              "or a stall. Profile <code>a</code> (the rig's flags) is complete on both releases; profile "
              "<code>p</code> (the #644 flags, <code>--max-memory 96G</code>) is complete only on 1.6.0. The user "
              "stopped the task before profile <code>q</code> and the reversed-order repeat, so these are partial "
              "results with no final verdict. With the pool full, 1.6.0 refused about 18 times fewer memory "
              "reservations in profile <code>a</code>.")
    return _q(3, d, answer, _table(["run", "release", "rounds", "probe before", "probe end", "probe idle",
                                    "end ÷ before", "reading", "largest gap", "denied reservations"], rows))


def _task4_html(d: dict[str, Any]) -> str:
    t4 = d["task4"]
    ll, a = t4["k2c2LL"], t4["k2c2a"]
    cw = {b["arm"]: b for b in t4["claim_wait"]}
    pct = _pct(ll["new"]["worst_s"], ll["control"]["worst_s"])

    def pair(x: Optional[dict], key: str = "streams_s") -> str:
        return "n/a" if not x else " / ".join(_s(v) for v in x[key])

    def worst(x: Optional[dict]) -> str:
        if not x:
            return "n/a"
        return _s(x["worst_s"]) + (f", {x['worst_ratio']:.2f}×" if x.get("worst_ratio") else "")

    rows = [
        ["1 session, 32K, turn time", _s(t4["k2c1"]["32768"]["ref"]["worst_s"]), "–", _s(t4["k2c1"]["32768"]["new"]["worst_s"])],
        ["1 session, 128K, turn time", _s(t4["k2c1"]["131072"]["ref"]["worst_s"]), "–", _s(t4["k2c1"]["131072"]["new"]["worst_s"])],
        ["2 sessions + side requests, 32K, worst stream", worst(a["32768"]["ref"]), "–", worst(a["32768"]["new"])],
        ["2 sessions + side requests, 128K, worst stream", worst(a["131072"]["ref"]), "–", worst(a["131072"]["new"])],
        ["2 × 256K, stream 1 / stream 2", pair(ll["ref"]), pair(ll["control"]), f"<b>{pair(ll['new'])}</b>"],
        ["2 × 256K, summed decode (tok/s)", _f(ll["ref"]["decode_sum"]), _f(ll["control"]["decode_sum"]),
         _f(ll["new"]["decode_sum"])],
        ["2 × 256K, warm TTFT of the tool turn, s1 / s2", "–", pair(ll["control"], "warm_tool_s"),
         pair(ll["new"], "warm_tool_s")],
        ["claim_wait max, 2 × 256K", "–", "–", _s(cw["k2c2LL 256K"]["max_s"])],
    ]
    groups = [
        {"label": "2 × 256K", "bars": [
            {"name": "1.5.0, 2026-10-29", "value": ll["ref"]["worst_s"], "color": OLD_OTHER_C},
            {"name": "1.5.0, same day", "value": ll["control"]["worst_s"], "color": OLD_C},
            {"name": "1.6.0", "value": ll["new"]["worst_s"], "color": NEW_C}]},
        {"label": "2 sessions + side, 128K", "bars": [
            {"name": "1.5.0, 2026-10-29", "value": a["131072"]["ref"]["worst_s"], "color": OLD_OTHER_C},
            {"name": "1.6.0", "value": a["131072"]["new"]["worst_s"], "color": NEW_C}]},
        {"label": "2 sessions + side, 32K", "bars": [
            {"name": "1.5.0, 2026-10-29", "value": a["32768"]["ref"]["worst_s"], "color": OLD_OTHER_C},
            {"name": "1.6.0", "value": a["32768"]["new"]["worst_s"], "color": NEW_C}]},
        {"label": "1 session, 128K", "bars": [
            {"name": "1.5.0, 2026-10-29", "value": t4["k2c1"]["131072"]["ref"]["worst_s"], "color": OLD_OTHER_C},
            {"name": "1.6.0", "value": t4["k2c1"]["131072"]["new"]["worst_s"], "color": NEW_C}]},
    ]
    title = "Worst-stream turn time, seconds (lower is better)"
    chart = svg_hbars(title, groups, 30.0, "s")
    tv = table_view(["configuration", "release", "worst stream (s)"],
                    [[g["label"], b["name"], f"{b['value']:.1f}"] for g in groups for b in g["bars"]])
    legend = _legend([(OLD_OTHER_C, "1.5.0, 2026-10-29 (reference campaign)"), (OLD_C, "1.5.0, same-day control"),
                      (NEW_C, "1.6.0")])
    caption = (f"Two 256K sessions: the worst stream goes from {_s(ll['control']['worst_s'])} to "
               f"{_s(ll['new']['worst_s'])} against the same-day control (+{pct}%). Two sessions at 32K and 128K "
               "and one session do not get worse.")
    cw_rows = [[_e(b["arm"]), _s(b["max_s"]), _s(b["total_s"])] for b in t4["claim_wait"] if b["arm"] in T4_BOOTS]
    rc = [b for b in t4["claim_wait"] if b["arm"] not in T4_BOOTS]
    cw_rows.append([f"Claude Code at 131072 ({len(rc)} boots)", _s(max(b["max_s"] for b in rc)) if rc else "n/a",
                    _s(sum(b["total_s"] for b in rc)) if rc else "n/a"])
    answer = (f"<b>Yes, for two 256K sessions.</b> On 1.6.0 the worst stream is {pct}% slower than on 1.5.0 the same "
              "day. The likely cause is the new memory governor: a request waits for memory "
              f"(<code>claim_wait</code>) for up to {_s(cw['k2c2LL 256K']['max_s'])}. The wait appears only with two "
              "sessions of 128K or more, and the maximum of about 30 s in both arms suggests a fixed timeout. The "
              "summed decode is the same on both releases that day, so the loss is in time to first token. "
              "Sessions at 32K and 128K and one session do not get worse. 1.5.0 numbers marked 2026-10-29 come "
              "from another day; the 256K pair has a same-day 1.5.0 control with 1 rep.")
    body = (_table(["test", f"{OLD}, 2026-10-29", f"{OLD}, same day", f"{NEW} (3 reps)"], rows, "wide")
            + legend + _panel(chart, caption, tv)
            + '<p class="s-note">Memory wait on 1.6.0, last <code>/status</code> of each boot '
              "(<code>metrics.ttft_parts_ms.claim_wait</code>). 1.5.0 has no such field.</p>"
            + _table(["boot", "claim_wait max", "claim_wait total"], cw_rows))
    return _q(4, d, answer, body)


def _task5_html(d: dict[str, Any]) -> str:
    runs = d["task5"]["runs"]
    rows = [[f"<code>{_e(r['run'])}</code>", r["release"], str(r["requests"]),
             f"{r['unanswered']}" + (" (400)" if r["unanswered"] and r["release"] == NEW else ""),
             _s(r["max_gap_s"]), _s(r["p99_gap_s"], 2), str(r["gaps_over_5s"]), _s(r["ttft_p50_s"]),
             _f(r["server_prefill"], 0), _f(r["server_decode"]), _f(r["ssd_read_gb"], 0, " GB")] for r in runs]
    groups = [{"label": f"run {r['run']}", "bars": [{"name": f"Splash {r['release']}", "value": r["max_gap_s"],
                                                      "color": NEW_C if r["release"] == NEW else OLD_C}]} for r in runs]
    title = "Largest decode gap per run, seconds (lower is better)"
    chart = svg_hbars(title, groups, 50.0, "s", label_w=110.0, rule=(10.0, "stall gate 10 s"))
    tv = table_view(["run", "release", "largest gap (s)"], [[r["run"], r["release"], f"{r['max_gap_s']:.1f}"] for r in runs])
    old_gap = max(r["max_gap_s"] for r in runs if r["release"] == OLD)
    new_gap = max(r["max_gap_s"] for r in runs if r["release"] == NEW)
    caption = (f"1.5.0 stops decoding for up to {_s(old_gap)}; 1.6.0 never pauses longer than {_s(new_gap)}. "
               "Runs in the order they ran (ABBA).")
    answer = ("<b>Yes.</b> Three clients for 15 minutes at 131072 with <code>--max-memory 64G</code>. 1.5.0 fails the "
              "stall gate (largest gap ≤ 10 s, p99 ≤ 5 s) in both runs. 1.6.0 passes it on gaps and serves "
              f"{_more_requests(d)} more requests. Each 1.6.0 run has two 400 <code>context_length_exceeded</code> "
              "answers; they come from the load generator: "
              "the prompt grows every round, and 1.6.0 ran fast enough to reach 131072 tokens before the 15 minutes "
              "ended. 1.6.0 also read about a third as much from the SSD.")
    body = (_table(["run", "release", "requests", "unanswered", "largest gap", "p99 gap", "gaps > 5 s",
                    "median TTFT", "server prefill", "server decode", "SSD read"], rows)
            + _legend([(OLD_C, "Splash 1.5.0"), (NEW_C, "Splash 1.6.0")]) + _panel(chart, caption, tv))
    return _q(5, d, answer, body)


def _task6_html(d: dict[str, Any]) -> str:
    t6 = d["task6"]
    rows = [[_e(s["suite"]), f"{s['base']}/{s['n']}", f"{s['cand']}/{s['n']}",
             f"{s['base_truncated']} / {s['cand_truncated']}", "pass" if s["g1"] else "fail"] for s in t6["suites"]]
    answer = ("Same weights, new release. The user skipped the task after 5 of 6 suites, so these are partial "
              "results. 1.6.0 (<code>k2g</code>) shows no quality loss against the same weights on Splash 1.4.0 "
              "(<code>k2a</code>, the stored baseline at 262144, effort <code>xhigh</code>), one pass per release. "
              "The baseline is 1.4.0, not 1.5.0. Gate G1 of <code>summarize_ab.py</code> passes in every suite.")
    return _q(6, d, answer, _table(["suite", "1.4.0 (k2a)", "1.6.0 (k2g)", "truncated 1.4.0 / 1.6.0", "G1"], rows))


def _task7_html(d: dict[str, Any]) -> str:
    n, o = d["task7"]["new"], d["task7"]["old"]

    def row(label: str, key: str, fmt) -> list[str]:
        return [label, fmt(n.get(key)), fmt(o.get(key))]

    rows = [
        row("completed pairs (sessions c + d)", "pairs", str),
        row("requests", "requests", str),
        row("HTTP errors", "errors", str),
        row("sessions that did the task", "task_done", str),
        row("short probe before the load (tok/s)", "probe_pre", _f),
        row("short probe after the last pair (tok/s)", "probe_end", _f),
        ["end ÷ before", f"{n['ratio']:.2f}, stable", f"{o['ratio']:.2f}, stable"],
        row("lowest probe rep (tok/s)", "probe_min", _f),
        ["warm TTFT p50 / p90", f"{_s(n['warm_ttft_p50'])} / {_s(n['warm_ttft_p90'])}",
         f"{_s(o['warm_ttft_p50'])} / {_s(o['warm_ttft_p90'])}"],
        row("server prefill (tok/s)", "server_prefill", lambda v: _f(v, 0)),
        row("server decode (tok/s)", "server_decode", _f),
        row("denied memory reservations at the end", "denied_reservations", str),
        ["claim_wait max", _s(n["claim_wait_max_s"]), "no such field"],
    ]
    series = [{"name": "1.5.0", "color": OLD_C, "points": [(h["hour"], h["probe_p50"]) for h in o["hours"]],
               "threshold": 0.85 * o["probe_pre"]},
              {"name": "1.6.0", "color": NEW_C, "points": [(h["hour"], h["probe_p50"]) for h in n["hours"]],
               "threshold": 0.85 * n["probe_pre"]}]
    title = "Short-probe decode per hour, tok/s (median of the reps; axis starts at 60)"
    chart = svg_hour_lines(title, series)
    tv = table_view(["hour", "1.6.0 pairs", "1.6.0 probe p50", "1.5.0 pairs", "1.5.0 probe p50"],
                    [[str(a["hour"]), str(a["pairs"]), f"{a['probe_p50']:.1f}", str(b["pairs"]), f"{b['probe_p50']:.1f}"]
                     for a, b in zip(n["hours"], o["hours"])])
    caption = ("Neither release drops below its dashed line. The plan calls a run stable when the end probe is at "
               "least 0.85 × the probe before the load. Hour 4 holds a single pair, so its point rests on one set "
               "of 3 reps.")
    answer = (f"<b>Yes, on both releases.</b> Pairs of real Claude Code sessions for 4 hours at 131072, one boot per "
              f"release, with a 64-token decode probe (3 reps) after each pair. The KV pool reached its ceiling on "
              f"both, so the load exercised the #644 condition. Neither release dropped, so the plan records "
              f"<b>fix not proven</b>: 1.5.0 is stable too. 1.6.0 completed {n['pairs']} pairs against {o['pairs']} "
              "and denied about 6 times fewer memory reservations. 1.6.0 ran first, so the gap in completed work may "
              "carry order and time effects.")
    body = (_table(["metric", f"{NEW} (ran first)", f"{OLD} (ran second)"], rows, "wide")
            + _legend([(OLD_C, "Splash 1.5.0"), (NEW_C, "Splash 1.6.0")]) + _panel(chart, caption, tv))
    return _q(7, d, answer, body)


def _questions(d: dict[str, Any]) -> str:
    summary = [[f'<a href="#task{n}">{n}</a>', _e(v["question"]), _badge(v)] for n, v in
               ((int(k), v) for k, v in d["verdicts"].items())]
    intro = ('<p class="s-note">One block per question of the <a href="' + PLAN_URL + '">runbook</a>. The rig '
             "launcher switches to 1.6.0 only when Tasks 1, 2, 4, 5 and 6 pass and Tasks 3 and 7 show no regression. "
             "Task 4 fails, so the launcher stays on 1.5.0.</p>")
    body = (intro + _table(["task", "question", "verdict"], summary, "wide")
            + _task1_html(d) + _task2_html(d) + _task3_html(d) + _task4_html(d) + _task5_html(d) + _task6_html(d)
            + _task7_html(d))
    return f'<section class="block" id="questions"><h2 class="sec">Answers by question</h2>{body}</section>'


def _claude_code_html(d: dict[str, Any]) -> str:
    cc = d["claude_code"]
    side = d["task4"]["side_max_s"]["k2c2a-131072"]
    rows = []
    for kind, name in (("pair", "pair (2 sessions)"), ("subagents", "pair with subagents")):
        o, n = cc[kind]["old"], cc[kind]["new"]
        rows += [
            [f"{name}: wall time", _s(o["wall_s"]), f"{_s(n['wall_s'])} ({_pct(n['wall_s'], o['wall_s'])}%)"],
            [f"{name}: warm TTFT p50 / p90", f"{_s(o['ttft_p50'])} / {_s(o['ttft_p90'])}",
             f"{_s(n['ttft_p50'])} / {_s(n['ttft_p90'])}"],
            [f"{name}: warm tok/s p50 / min", f"{_f(o['tps_p50'])} / {_f(o['tps_min'])}",
             f"{_f(n['tps_p50'])} / <b>{_f(n['tps_min'])}</b>"],
        ]
    rows.append(["one session alone: warm TTFT p50 / p90", "not run",
                 f"{_s(cc['alone_new']['ttft_p50'])} / {_s(cc['alone_new']['ttft_p90'])}"])
    rows.append(["sessions that did the task", cc["task_done"]["old"], cc["task_done"]["new"]])
    p, s = cc["pair"], cc["subagents"]
    body = (
        '<p class="s-note"><b>Mixed.</b> Real Claude Code sessions (tasks c and d) at 131072, a same-day 1.5.0 '
        f"control with {cc['reps']['old']} reps against 1.6.0 with {cc['reps']['new']}. On 1.6.0 the pair finishes "
        f"{-_pct(p['new']['wall_s'], p['old']['wall_s'])}% sooner and the pair with subagents "
        f"{-_pct(s['new']['wall_s'], s['old']['wall_s'])}% sooner, and the warm TTFT p50 and p90 are lower. The "
        f"minimum warm tok/s is worse: {_f(p['new']['tps_min'])} against {_f(p['old']['tps_min'])} in the pair and "
        f"{_f(s['new']['tps_min'])} against {_f(s['old']['tps_min'])} with subagents. Each minimum comes from one "
        "request. The failed session on each release is a <code>d</code> task that missed the hidden check of the "
        "work; it is not a server error. No request returned an HTTP error.</p>"
        + _table(["profile and metric", f"{OLD}, same day", NEW], rows, "wide")
        + f'<p class="callout">In the synthetic two-session test at 128K (<code>k2c2a</code>), one side request on '
          f"1.6.0 waited {_s(side)}, over the 60 s stall limit. The same arm has <code>claim_wait</code> up to "
          f"{_s(next(b['max_s'] for b in d['task4']['claim_wait'] if b['arm'] == 'k2c2a 128K'))}.</p>")
    return f'<section class="block" id="claude-code"><h2 class="sec">Claude Code sessions at 131072</h2>{body}</section>'


def _not_measured_html(d: dict[str, Any]) -> str:
    ll = d["task4"]["k2c2LL"]
    ref, ctl = ll["ref"]["decode_sum"], ll["control"]["decode_sum"]
    caveats = [CAVEATS[0].format(x=f"{ref / ctl:.1f}×", ref=f"{ref:.1f}", ctl=f"{ctl:.1f}"),
               CAVEATS[1].format(n_new=d["task7"]["new"]["pairs"], n_old=d["task7"]["old"]["pairs"])]
    body = ('<div class="callout"><p><b>Before a switch, these still need a run on 1.6.0:</b></p><ul>'
            + "".join(f"<li>{_e(i)}</li>" for i in NOT_MEASURED) + "</ul><p><b>Two limits of what did run:</b></p><ul>"
            + "".join(f"<li>{_e(c)}</li>" for c in caveats) + "</ul></div>")
    return f'<section class="block" id="not-measured"><h2 class="sec">Not measured on 1.6.0</h2>{body}</section>'


def _api_html(d: dict[str, Any]) -> str:
    t1 = d["task1"]
    r, c7 = t1["restart"], t1["c7"]
    codes = ", ".join(f"<code>{_e(k)}</code> ×{v}" for k, v in r["codes"].items())
    items = [
        ("The API key no longer goes to the proxy.",
         f"With <code>http_proxy</code> set, the 1.5.0 launcher sent {t1['proxy'][OLD]['key_hits']} request with the "
         "key through the proxy (<code>GET /v1/models</code>) and then did not find the server. 1.6.0 sent none and "
         "gives the agent <code>NO_PROXY=127.0.0.1,localhost,::1</code>. The rig had no <code>http_proxy</code> in "
         "its SSH session, so no key leaked during the campaign. No key value is stored in the results."),
        ("The engine restarts in seconds, with documented 503s.",
         f"After a SIGKILL of <code>serve-native</code> during a stream, the stream ends with a "
         f"<code>runtime_unavailable</code> error event and <code>[DONE]</code>. Retries get 503 with "
         f"<code>Retry-After</code> ({codes}), the codes that <a href=\"{API_DOC}\">api.md</a> documents. The first "
         f"200 comes at {_s(r['first_200_s'])}, within 2 × the {r['boot_s']:.0f} s boot, and the context stays "
         f"{r['context']}."),
        ("KV reuse past a thinking cut, announced for 1.6.0, was not observed on either release.",
         f"With <code>thinking_token_budget</code> 1024 and a tool, the second turn cached "
         f"{', '.join(str(x) for x in sorted(set(c7['cached'][NEW])))} tokens on both releases: the "
         f"{c7['first_prompt']}-token first prompt rounded to the 32-token block, and none of the reply. 1.6.0 cut "
         f"the thinking in all {len(c7['first_output'][NEW])} valid reps "
         f"({', '.join(str(x) for x in c7['first_output'][NEW])} output tokens); 1.5.0 hit "
         f"<code>max_tokens</code> 4096 in 1 of {len(c7['first_output'][OLD])}. This is not a regression."),
        ("Two request shapes now fail on 1.6.0.",
         "<code>stop_sequences</code> as a string and a <code>stop</code> string of 16385 characters get 400. "
         "Clients that send either need a change. <code>/status</code> moves to schema 8."),
    ]
    body = '<ul class="notes">' + "".join(f"<li><b>{a}</b> {b}</li>" for a, b in items) + "</ul>"
    return f'<section class="block" id="api"><h2 class="sec">API contract notes</h2>{body}</section>'


def _method_html(d: dict[str, Any]) -> str:
    items = [
        f"One rig ({_e(d['rig'])}), one model at a time, the same weights on both releases: {_e(d['weights'])}. "
        "Base flags <code>--verify-rows auto --idle-release off --language-only --no-webui --offline</code>.",
        "Sampling: temperature 1.0, top_p 0.95, top_k 20, reasoning effort xhigh. Claude Code 2.1.292, the version "
        "of the earlier baselines.",
        "Single-stream turns: 3 boots per release and band in ABBA order, an idle gate between bands and 120 s "
        "between arms. Speed gates: no HTTP errors, correct needles, cache hit ≥ 0.90, swap growth ≤ 0.5 GB.",
        "Decode drop: a 64-token probe after the load ÷ the same probe before it. ≥ 0.85 is stable, 0.50 to 0.85 "
        "degraded, below 0.50 a drop. The probe varies about ±8% between single reps, so it runs 3 reps.",
        "Stall gate: largest gap between chunks ≤ 10 s and p99 ≤ 5 s, with every request answered.",
        "Controls with 1 rep: the 1.5.0 pair of 256K sessions and the 1.5.0 1M run. The Claude Code minimum tok/s "
        "comes from a single request per profile.",
        "Task 7 runs once per release, in sequence. Its per-hour table places each pair by the summed wall time of "
        "the earlier pairs and probes; the stage report used file times, and both give the same pairs per hour.",
        "Warm TTFT of Claude Code sessions uses the warm definition of <code>claude_requests.py</code> (cached "
        "prompt and at most 2000 new tokens) in Task 4 and Task 7 alike.",
        "Every number on this page is computed from the committed results by "
        "<code>bench/splash16-2026-11/scripts/render_page.py</code>, except the API check table, which restates "
        "the Task 1 stage report.",
    ]
    body = ('<ul class="notes">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
            f'<p class="s-note">Runbook: <a href="{PLAN_URL}">plan.md</a>. Results: <a href="{RESULTS_URL}">results/</a>. '
            "The data behind this page is embedded in it as JSON (<code>#data</code>).</p>")
    return f'<section class="block" id="method"><h2 class="sec">Method and limits</h2>{body}</section>'


TERMS = [("k2f / k2g", "the weights on Splash 1.5.0 / 1.6.0, one stream"),
         ("k2c1", "one session in the concurrency harness"),
         ("k2c2a", "two sessions plus side requests (titles, summaries)"),
         ("k2c2LL", "two 256K sessions"),
         ("rc2 / rc2s", "a pair of real Claude Code sessions / the same with subagents"),
         ("T_turno", "turn time: warm TTFT of a tool turn plus 512 tokens of decode"),
         ("claim_wait", "the part of TTFT a 1.6.0 request spends waiting for memory")]


def _footer(generated: str) -> str:
    rows = [[f"<code>{_e(a)}</code>", _e(b)] for a, b in TERMS]
    return ('<footer id="terms"><h2 class="sec">Terms</h2>' + _table(["code", "meaning"], rows, "wide")
            + f'<p class="s-note">Generated on {_e(generated)}.</p></footer>')


CSS = """
:root{
  color-scheme: light;
  --plane:#f9f9f7; --surface:#fcfcfb; --surface-2:#f3f2ee;
  --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --baseline:#c3c2b7; --border:rgba(11,11,11,0.10);
  --accent:#2a78d6; --warn:#b06a00; --warn-bg:#fbf1dd;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100;
  --s1l:#9ec5f4; --s2l:#f5b79a; --good:#0ca30c; --warn-s:#fab219; --crit:#d03b3b;
  --mono:"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
  --sans: system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --plane:#0d0d0d; --surface:#1a1a19; --surface-2:#232321;
    --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,0.10);
    --accent:#3987e5; --warn:#e0a63a; --warn-bg:#2a2312;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
    --s1l:#86b6ef; --s2l:#f0a07c; --good:#0ca30c; --warn-s:#fab219; --crit:#d03b3b;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --plane:#0d0d0d; --surface:#1a1a19; --surface-2:#232321;
  --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,0.10);
  --accent:#3987e5; --warn:#e0a63a; --warn-bg:#2a2312;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
  --s1l:#86b6ef; --s2l:#f0a07c; --good:#0ca30c; --warn-s:#fab219; --crit:#d03b3b;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--plane); color:var(--ink); font-family:var(--sans); line-height:1.5; -webkit-font-smoothing:antialiased}
.wrap{max-width:1080px; margin:0 auto; padding:32px 16px 64px}
header{display:flex; flex-wrap:wrap; gap:16px 32px; align-items:flex-end; justify-content:space-between}
h1{font-size:1.7rem; font-weight:700; letter-spacing:-0.02em; margin:0; text-wrap:balance}
.eyebrow{font-family:var(--mono); font-size:0.72rem; letter-spacing:0.14em; text-transform:uppercase; color:var(--muted); margin:0 0 6px}
button.theme{font-family:var(--mono); font-size:0.74rem; color:var(--ink-2); background:var(--surface); border:1px solid var(--border); border-radius:7px; padding:7px 12px; cursor:pointer}
button.theme:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
a{color:var(--accent)}
code{font-family:var(--mono); font-size:0.88em; background:var(--surface-2); padding:1px 5px; border-radius:4px; overflow-wrap:anywhere}
h2.sec{font-size:1.1rem; margin:0 0 6px; letter-spacing:-0.01em}
h3{font-size:1rem; margin:0 0 4px; letter-spacing:-0.01em}
.s-note{color:var(--ink-2); font-size:0.92rem; margin:0 0 12px; max-width:82ch}
.s-note b{color:var(--ink)}
section.block{margin-top:34px}
section.q{margin-top:26px; padding-top:18px; border-top:1px solid var(--border)}
.verdict-line{margin:4px 0 8px; display:flex; flex-wrap:wrap; gap:6px}
.badge{display:inline-block; font-family:var(--mono); font-size:0.72rem; letter-spacing:0.04em; padding:2px 9px; border-radius:5px; color:var(--ink); font-weight:600}
.badge.pass{background:color-mix(in srgb, var(--good) 20%, transparent)}
.badge.fail{background:color-mix(in srgb, var(--crit) 22%, transparent)}
.badge.na{background:var(--surface-2); border:1px solid var(--border)}
.badge.skip{background:color-mix(in srgb, var(--warn-s) 26%, transparent)}
.hero-lead{font-size:1.06rem; line-height:1.55; max-width:72ch; margin:18px 0 10px; color:var(--ink)}
.tiles{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,190px),1fr)); gap:12px; margin-top:16px}
.tile{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px}
.tile .t-lab{font-family:var(--mono); font-size:0.68rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); margin:0}
.tile .t-big{font-size:1.5rem; line-height:1.15; font-weight:700; margin:6px 0 4px; color:var(--ink); font-variant-numeric:tabular-nums}
.tile .t-sub{font-size:0.84rem; color:var(--ink-2); margin:0; line-height:1.4}
.chart text.ttl{font-weight:600; fill:var(--ink)}
.chart text.lbl,.chart text.tick{fill:var(--ink-2)}
.chart text.value{fill:var(--ink)}
details.tbl{margin:6px 0 0; font-size:0.84rem}
details.tbl summary{font-weight:500; color:var(--ink-2); font-size:0.8rem; margin:0}
details.tbl table{margin-top:6px}
.legend{display:flex; flex-wrap:wrap; gap:6px 18px; margin:10px 0 6px}
.chip{display:inline-flex; align-items:center; gap:7px; font-size:0.84rem; color:var(--ink-2)}
.chip .sw{width:12px; height:12px; border-radius:3px; flex:none}
.panel{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 14px 10px; margin:6px 0 12px}
.chart{color:var(--ink-2)}
.chart svg{width:100%; max-width:760px; height:auto; display:block; margin:0 auto; overflow:visible; font-family:var(--sans); font-variant-numeric:tabular-nums}
.p-interp{font-size:0.82rem; color:var(--ink-2); margin:8px 2px 0; line-height:1.4; border-top:1px solid var(--border); padding-top:8px}
.tbl-scroll{overflow-x:auto; border:1px solid var(--border); border-radius:10px; background:var(--surface); margin:0 0 12px}
table{border-collapse:collapse; width:100%; font-size:0.84rem}
th,td{padding:7px 10px; text-align:right; font-variant-numeric:tabular-nums; font-family:var(--mono); vertical-align:top}
th{font-size:0.72rem; letter-spacing:0.04em; color:var(--muted); font-weight:500; border-bottom:1px solid var(--border); background:var(--surface)}
td:first-child,th:first-child{text-align:left}
tbody tr:hover{background:var(--surface-2)}
table.wide td,table.wide th{text-align:left; font-family:var(--sans)}
ul.notes{margin:0; padding-left:20px; display:grid; gap:8px; max-width:82ch}
ul.notes li{font-size:0.92rem; color:var(--ink-2)}
ul.notes li b{color:var(--ink)}
.callout{margin:0 0 12px; padding:10px 14px; border-left:3px solid var(--warn); background:var(--warn-bg); border-radius:6px; font-size:0.92rem}
.callout p{margin:4px 0}
.callout ul{margin:4px 0 8px; padding-left:20px}
footer{margin-top:48px; padding-top:20px; border-top:1px solid var(--border)}
"""

THEME_JS = """
const root=document.documentElement, btn=document.getElementById("themeBtn");
function label(){ btn.textContent="theme: "+(root.getAttribute("data-theme")||"auto"); }
btn.addEventListener("click",()=>{
  const cur=root.getAttribute("data-theme"), next=cur==null?"light":cur==="light"?"dark":null;
  if(next) root.setAttribute("data-theme",next); else root.removeAttribute("data-theme");
  try{ next?localStorage.setItem("theme",next):localStorage.removeItem("theme"); }catch(e){}
  label();
});
try{ const saved=localStorage.getItem("theme"); if(saved) root.setAttribute("data-theme",saved); }catch(e){}
label();
"""


def render(data: dict[str, Any], generated: Optional[str] = None) -> str:
    generated = generated or datetime.date.today().isoformat()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    ll = data["task4"]["k2c2LL"]
    eyebrow = " · ".join(["Qwen3.8 Flash-Next", "Splash 1.5.0 vs 1.6.0", data["rig"],
                          f"{data['dates'][0]} to {data['dates'][1]}"])
    desc = (f"Splash 1.6.0 against 1.5.0 on a {data['rig']}: two 256K sessions are up to "
            f"{_pct(ll['new']['worst_s'], ll['control']['worst_s'])}% slower on 1.6.0, one stream is the same, and "
            "1.6.0 removes the decode stalls under a memory limit.")
    return "".join([
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n',
        f"<title>{_e(TITLE)}</title>\n",
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n',
        f'<meta name="description" content="{_e(desc)}">\n',
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700'
        '&display=swap">\n',
        f"<style>{CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">\n",
        f'<header><div><p class="eyebrow">{_e(eyebrow)}</p><h1>{_e(TITLE)}</h1></div>'
        '<button class="theme" id="themeBtn" type="button">theme: auto</button></header>\n',
        _hero(data), "\n", _questions(data), "\n", _claude_code_html(data), "\n", _not_measured_html(data), "\n",
        _api_html(data), "\n", _method_html(data), "\n", _footer(generated), "\n</div>\n",
        f'<script id="data" type="application/json">{payload}</script>\n',
        f"<script>{THEME_JS}</script>\n</body>\n</html>\n",
    ])


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Render the public Splash 1.6.0 vs 1.5.0 report page.")
    p.add_argument("--results-dir", default=str(RESULTS))
    p.add_argument("--out-html", default=str(REPO / "reports" / "qwen38-flashnext-splash160.html"))
    p.add_argument("--out-json", default=str(RESULTS / "page-data.json"))
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    data = collect(Path(args.results_dir))
    out_html, out_json = Path(args.out_html), Path(args.out_json)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(render(data), encoding="utf-8")
    out_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
