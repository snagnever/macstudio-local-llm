#!/usr/bin/env python3
"""Render the 2×2 page: Qwen3.8-Flash-Next base and Swift 1.5, on mlx-serve and on Splash.

collect() reads the batteries, the canonical speed groups, the Terminal-Bench task tables, the effort runs and
the Claude Code summaries of four campaigns. render() turns that payload into reports/qwen38-flashnext-base-vs-swift.html,
a self-contained page in the layout of reports/qwen38-flashnext-swift15.html.

A cell with no measurement renders as "not measured". When the k1a battery lands in
bench/splash-longctx-2026-10/results/q262/t1/k1a/, the base × Splash cells fill in with no code change.

    python3 bench/swift15-flashnext-2026-10/scripts/render_matrix.py
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import html as _html
import json
import math
import statistics
import sys
from pathlib import Path

import summarize_ab as S

CAMPAIGN = Path(__file__).resolve().parents[1]
REPO = CAMPAIGN.parents[1]
sys.path.insert(0, str(REPO / "bench" / "qwen38-flashnext-daily-driver-2026-09" / "scripts"))
from render_perf_lines import CSS as PERF_CSS, EXTRA_CSS as PERF_EXTRA_CSS  # noqa: E402

AB = CAMPAIGN / "results" / "ab"
HE_REGRADE_AB = CAMPAIGN / "results" / "humaneval-regrade.json"
SPLASH = REPO / "bench" / "splash-longctx-2026-10" / "results"
HE_REGRADE_SPLASH = SPLASH / "humaneval-regrade.json"
NEXT = REPO / "bench" / "flashnext-next-steps-2026-10" / "results"
CC = REPO / "bench" / "claude-code-concurrency-2026-11" / "results"
REPORTS_JSON = REPO / "bench" / "engine-updates-2026-10" / "results" / "reports-2026-10.json"
OUT = REPO / "reports" / "qwen38-flashnext-base-vs-swift.html"
REPO_URL = "https://github.com/snagnever/macstudio-local-llm"

CTX = [8192, 32768, 131072, 262144, 524288, 1000000]
CTX_LABEL = {8192: "8K", 32768: "32K", 131072: "128K", 262144: "256K", 524288: "512K", 1000000: "1M"}
SUITES = ["humaneval", "gpqa", "livecodebench", "if", "jdhodges", "veerman"]
SUITE_LABEL = {"humaneval": "HumanEval (164)", "gpqa": "GPQA-Diamond (50)", "livecodebench": "LiveCodeBench v6 (50)",
               "if": "Instruction following (20)", "jdhodges": "Tool calls A (40)", "veerman": "Tool calls B (12)"}
G1_MARGIN = S.QUALITY_MARGIN
EFFORTS = ["xhigh", "medium", "low"]
SCENARIOS = ["identical", "append", "tool_turn", "middle_mutation"]
MLX_1M_ABSENT = ("loads, but fails: mlx-serve 26.10.3 serves the first 1M message, then 2–3 of 5 requests fail "
                 "with PrefillDoesNotFit (~18 GB needed, 7–9 GB free)")

# The four cells. `color` is a CSS variable of the shared palette: blue, orange, aqua, violet pass the adjacent-pair
# checks in both modes (dataviz validator, 2026-11-02); aqua needs direct labels on the light surface, which every
# chart here has.
CELLS = [
    {"id": "bm", "model": "base", "engine": "mlx-serve", "name": "base · mlx-serve", "color": "--s1", "marker": "circle",
     "model_name": "Qwen3.8-Flash-Next (base)", "weights": "ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw",
     "rev": "dafff5c", "quant": "iQ-MLX 4.7 bpw", "disk": "107 GB", "runtime": "mlx-serve 26.10.1 (quality) · 26.10.3 (speed)",
     "arms": "n2 · n2z", "spec": "MTP + n-gram lookup", "max": "512K (YaRN 2.0 + 4-bit KV)"},
    {"id": "sm", "model": "swift", "engine": "mlx-serve", "name": "Swift 1.5 · mlx-serve", "color": "--s2", "marker": "square",
     "model_name": "Swift 1.5 (fine-tune by Dankpaws)", "weights": "Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw",
     "rev": "13839b7", "quant": "MLX 4.7 bpw", "disk": "99 GB", "runtime": "mlx-serve 26.10.1 (A/B) · 26.10.3 (the daily driver)",
     "arms": "w1 · w1z", "spec": "MTP + n-gram lookup", "max": "512K (YaRN 2.0 + 4-bit KV)"},
    {"id": "bs", "model": "base", "engine": "splash", "name": "base · Splash", "color": "--s3", "marker": "diamond",
     "model_name": "Qwen3.8-Flash-Next (base)", "weights": "unsloth/Qwen3.8-Flash-Next-GGUF",
     "rev": "766911a", "quant": "UD-IQ4_XS GGUF", "disk": "94 GB", "runtime": "Splash 1.4.0",
     "arms": "k1a", "spec": "DFlash2 draft model", "max": "1M (YaRN, KV int8, SSD past ~860K)"},
    {"id": "ss", "model": "swift", "engine": "splash", "name": "Swift 1.5 · Splash", "color": "--s6", "marker": "triangle",
     "model_name": "Swift 1.5 (GGUF by ukisai)", "weights": "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF",
     "rev": "0142554", "quant": "IQ4_XS GGUF", "disk": "98 GB", "runtime": "Splash 1.4.0 (1.5.0 for Claude Code)",
     "arms": "k2a", "spec": "DFlash2 draft model", "max": "1M (YaRN, KV int8, SSD past ~860K)"},
]
CELL = {c["id"]: c for c in CELLS}

# Speed arms per cell and band. The mlx-serve cells use the 26.10.3 build, the one the Splash arms ran against.
SPEED_ARMS = {
    "bm": {8192: "n2z", 32768: "n2z", 131072: "n2z", 262144: "n2z", 524288: "n2zq4", 1000000: None},
    "sm": {8192: "w1z", 32768: "w1z", 131072: "w1z", 262144: "w1z", 524288: "w1zq4", 1000000: None},
    "bs": {c: "k1a" for c in CTX},
    "ss": {c: "k2a" for c in CTX},
}
TBENCH_ARM = {"sm": "w1z", "ss": "k2a", "bm": None, "bs": None}
CC_FILE = {"sm": "claude-summary-mlx.json", "ss": "claude-summary-splash.json"}
LONGCTX_ARMS = {"sm": ("w1z", "w1zq4"), "ss": ("k2a",), "bm": (), "bs": ("k1a",)}
TOOLCALL_ARM = {"sm": "w1z", "ss": "k2a", "bm": None, "bs": "k1a"}
# Agent probes 3b and 3c of flashnext-next-steps-2026-10/results/etapa3-agent.md (mlx-serve 26.10.1, xhigh).
AGENT_PROBES = {
    "bm": {"tokens_3b": 3949.5, "empty_3c": 4, "wrong_3c": 4},
    "sm": {"tokens_3b": 2328.5, "empty_3c": 0, "wrong_3c": 0},
}


def E(v) -> str:
    return _html.escape(str(v), quote=True)


# ----------------------------------------------------------------------------------------------------------- collect

def _he_regrade(path: Path, key: str) -> int | None:
    if not path.is_file():
        return None
    rg = json.loads(path.read_text(encoding="utf-8")).get(key)
    return None if rg is None else rg["with_imports"]


def _points(views: list[dict]) -> list[dict]:
    return [{"id": v["id"], "s": round(v["elapsed_s"], 2), "ok": v["passed"], "trunc": v["truncated"],
             "tok": v["completion_tokens"]} for v in views]


def _lcb_difficulty(path: Path) -> dict | None:
    f = path / "livecodebench.jsonl"
    if not f.is_file():
        return None
    out = {}
    for r in S.read_rows(f):
        d = r.get("lcb_difficulty") or "?"
        v = S.view("livecodebench", r)
        out.setdefault(d, []).append(v)
    return {d: {"n": len(vs), "passed": sum(v["passed"] for v in vs),
                "median_s": round(statistics.median(v["elapsed_s"] for v in vs), 1)} for d, vs in out.items()}


def load_run(path: Path, he_regrade: tuple[Path, str] | None = None, he_r2: Path | None = None) -> dict | None:
    """One battery run: per-suite stats, points for the dot plots, HumanEval with imports."""
    if not path.is_dir():
        return None
    arm = S.load_arm(path)
    if not arm:
        return None
    out = {}
    for suite, views in arm.items():
        st = S.suite_stats(views)
        st["points"] = _points(views)
        st["sec_per_correct"] = round(st["total_s"] / st["passed"], 1) if st["passed"] else None
        out[suite] = st
    if "humaneval" in out and he_regrade:
        out["humaneval"]["with_imports"] = _he_regrade(*he_regrade)
    if he_r2 and (he_r2 / "humaneval.jsonl").is_file():
        views = S.load_arm(he_r2)["humaneval"]
        out["humaneval"]["strict_r2"] = S.suite_stats(views)["passed"]
        out["humaneval"]["with_imports_r2"] = _he_regrade(he_regrade[0], he_regrade[1] + "-r2") if he_regrade else None
    out["lcb_difficulty"] = _lcb_difficulty(path)
    return out


def collect_quality() -> dict:
    q = {"mlx": {}, "swift262": {}, "splash262": {}}
    for prof in ("t1", "t0"):
        q["mlx"][prof] = {"bm": load_run(AB / prof / "n2", (HE_REGRADE_AB, f"n2-{prof}")),
                          "sm": load_run(AB / prof / "w1", (HE_REGRADE_AB, f"w1-{prof}"))}
    k2a = load_run(SPLASH / "q262" / "t1" / "k2a", (HE_REGRADE_SPLASH, "k2a-262144"), SPLASH / "q262r2" / "t1" / "k2a")
    q["swift262"] = {"sm": load_run(SPLASH / "q262" / "t1" / "w1z", (HE_REGRADE_SPLASH, "w1z-262144")), "ss": k2a}
    q["splash262"] = {"bs": load_run(SPLASH / "q262" / "t1" / "k1a", (HE_REGRADE_SPLASH, "k1a-262144")), "ss": k2a}
    return q


def _pick_group(groups: list[dict], arm: str, ctx: int) -> dict | None:
    cands = [g for g in groups if g.get("arm") == arm and g["context"] == ctx and g.get("mode") == "canonical"]
    if not cands:
        return None
    cands.sort(key=lambda g: (-(g.get("reps") or 0), g.get("file", "")))
    return cands[0]


def collect_speed(data: dict) -> dict:
    speed = {}
    for cid, arms in SPEED_ARMS.items():
        series = []
        for ctx in CTX:
            arm = arms[ctx]
            g = _pick_group(data["groups"], arm, ctx) if arm else None
            if g is None:
                absent = MLX_1M_ABSENT if (ctx == 1000000 and CELL[cid]["engine"] == "mlx-serve") else "not run"
                series.append({"ctx": ctx, "arm": arm, "absent": absent})
                continue
            series.append({"ctx": ctx, "arm": arm, "absent": None, "reps": g["reps"], "config": g.get("tag") or "",
                           "t_turno_s": g["t_turno_s"], "decode_tps": g["decode_tps"], "cold_ttft_s": g["cold_ttft_s"],
                           "warm_ttft_s": g["ttft_s"].get("tool_turn"), "prefill_tps": g.get("prefill_tps"),
                           "hit": {s: g["hit"].get(s) for s in SCENARIOS},
                           "wired_peak_gb": g["wired_peak_gb"], "mem_free_min_gb": g["mem_free_min_gb"]})
        speed[cid] = series
    return speed


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p for b and c discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def _tbench_tasks(path: Path) -> dict[str, dict] | None:
    if not path.is_file():
        return None
    out = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["task"]] = {"passed": float(r["reward"]) >= 1.0, "agent_min": float(r["agent_min"] or 0),
                              "requests": int(r["requests"] or 0), "median_request_s": float(r["median_request_s"] or 0),
                              "output_tokens": int(r["output_tokens"] or 0), "error": r["error"]}
    return out


def collect_tbench() -> dict:
    tb = {}
    for cid, arm in TBENCH_ARM.items():
        tasks = _tbench_tasks(SPLASH / f"tbench21-{arm}-tasks.csv") if arm else None
        if tasks is None:
            tb[cid] = None
            continue
        tb[cid] = {"arm": arm, "n": len(tasks), "passed": sum(t["passed"] for t in tasks.values()),
                   "timeouts": sum(1 for t in tasks.values() if t["error"] == "AgentTimeoutError"),
                   "median_request_s": round(statistics.median(t["median_request_s"] for t in tasks.values()), 1),
                   "median_task_min": round(statistics.median(t["agent_min"] for t in tasks.values()), 1),
                   "tasks": tasks}
    pair = None
    if tb["sm"] and tb["ss"]:
        a, b = tb["sm"]["tasks"], tb["ss"]["tasks"]
        both = sum(1 for t in a if a[t]["passed"] and b.get(t, {}).get("passed"))
        only_sm = sum(1 for t in a if a[t]["passed"] and not b.get(t, {}).get("passed"))
        only_ss = sum(1 for t in b if b[t]["passed"] and not a.get(t, {}).get("passed"))
        neither = sum(1 for t in a if not a[t]["passed"] and not b.get(t, {}).get("passed"))
        pair = {"both": both, "only_sm": only_sm, "only_ss": only_ss, "neither": neither,
                "p": round(mcnemar_exact(only_sm, only_ss), 2)}
    tb["pair"] = pair
    return tb


E3D_LCB_REGRADE = NEXT / "e3d-lcb-regrade.json"


def _load_effort_arm(path: Path) -> dict[str, list[dict]]:
    """Like summarize_ab.load_arm, with the next-steps LCB regrade for the e3d runs (their rows carry the old grader)."""
    out = {}
    for suite in ("gpqa", "livecodebench"):
        f = path / f"{suite}.jsonl"
        if not f.is_file():
            continue
        rows = S.read_rows(f)
        if suite == "livecodebench" and E3D_LCB_REGRADE.is_file():
            key = f"{path.name}/{f.name}"
            verdicts = json.loads(E3D_LCB_REGRADE.read_text(encoding="utf-8")).get(key)
            if verdicts:
                regraded = {v["lcb_question_id"]: v["regraded"] for v in verdicts}
                rows = [dict(r, correct=regraded[r["lcb_question_id"]]) if r.get("lcb_question_id") in regraded else r
                        for r in rows]
        out[suite] = [S.view(suite, r) for r in rows]
    return out


def _effort_run(paths: list[Path]) -> dict | None:
    """Mean over rounds of GPQA and LCB passed, time and tokens."""
    rounds = []
    for p in paths:
        arm = _load_effort_arm(p)
        if "gpqa" in arm and "livecodebench" in arm:
            rounds.append(arm)
    if not rounds:
        return None
    out = {"rounds": len(rounds)}
    for suite in ("gpqa", "livecodebench"):
        out[suite] = {"n": len(rounds[0][suite]),
                      "passed": round(statistics.mean(sum(v["passed"] for v in r[suite]) for r in rounds), 1),
                      "truncated": round(statistics.mean(sum(v["truncated"] for v in r[suite]) for r in rounds), 1)}
    out["total_s"] = round(statistics.mean(sum(v["elapsed_s"] for s in ("gpqa", "livecodebench") for v in r[s])
                                           for r in rounds))
    out["total_tokens"] = round(statistics.mean(sum(v["completion_tokens"] for s in ("gpqa", "livecodebench")
                                                    for v in r[s]) for r in rounds))
    return out


def collect_effort() -> dict:
    sm = {e: _effort_run([NEXT / "e3d" / "t1" / f"w1-{e}-r1", NEXT / "e3d" / "t1" / f"w1-{e}-r2"]) for e in EFFORTS}
    bm = {"xhigh": _effort_run([AB / "t1" / "n2"]),
          "medium": _effort_run([NEXT / "e15" / "t1" / "n2-medium-r1"]),
          "low": _effort_run([NEXT / "e15" / "t1" / "n2-low-r1"])}
    return {"bm": bm if all(bm.values()) else None, "sm": sm if all(sm.values()) else None, "bs": None, "ss": None}


def collect_claude_code() -> dict:
    cc = {"bm": None, "bs": None}
    for cid, name in CC_FILE.items():
        f = CC / name
        if not f.is_file():
            cc[cid] = None
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        alone = {}
        for prof in d["profiles"].values():
            alone.update(prof["alone_s"])
        warm = d["requests"]["alone"]["warm"]
        cc[cid] = {"alone_s": alone, "first_prompt_ttft_s": d["requests"]["alone"]["first_prompt_ttft_s"],
                   "warm_ttft_p50": warm["ttft_p50"], "warm_tps_p50": warm["tps_p50"],
                   "pair_wall_s": {k: v["pair_wall_s"] for k, v in d["profiles"].items()},
                   "serial_sum_s": {k: v["serial_sum_s"] for k, v in d["profiles"].items()}}
    return cc


def collect_longctx() -> dict:
    out = {}
    for cid, arms in LONGCTX_ARMS.items():
        rows = {}
        for f in sorted((SPLASH / "longctx").glob("*.jsonl")):
            arm = f.name.split("-")[0]
            if arm not in arms or "smoke" in f.name:
                continue
            server = int(f.name.split("-")[1])
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get("record_type") != "longctx":  # the file ends with a verdict record
                    continue
                key = (arm, server, int(r["context"]))
                rows.setdefault(key, {"arm": arm, "server": server, "band": int(r["context"]), "n": 0, "correct": 0})
                rows[key]["n"] += 1
                rows[key]["correct"] += 1 if r.get("correct") else 0
        out[cid] = sorted(rows.values(), key=lambda r: (r["server"], r["band"])) or None
    return out


def collect_toolcall() -> dict:
    out = {}
    for cid, arm in TOOLCALL_ARM.items():
        res = {}
        for fp in ("fp0", "fp1"):
            f = SPLASH / "toolcall" / f"{arm}-{fp}-t4.jsonl" if arm else None
            if not f or not f.is_file():
                continue
            # tool_turn records are the tool calls; one verdict record per session judges the final answer too.
            sessions = sessions_ok = turns = ok_turns = 0
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get("record_type") == "tool_turn":
                    turns += 1
                    ok_turns += bool(r.get("correct"))
                elif r.get("record_type") == "verdict":
                    sessions += 1
                    sessions_ok += bool(r.get("correct"))
            res[fp] = {"sessions": sessions, "sessions_ok": sessions_ok, "turns": turns, "turns_ok": ok_turns}
        out[cid] = res or None
    return out


def collect_coverage(p: dict) -> dict:
    cov = {}
    for cid in CELL:
        battery = (p["quality"]["mlx"]["t1"].get(cid) if cid in ("bm", "sm") else None) or \
                  p["quality"]["swift262"].get(cid) or p["quality"]["splash262"].get(cid)
        cov[cid] = {
            "battery": {"measured": battery is not None,
                        "note": "t1 and t0 on 26.10.1; 262K on 26.10.3" if cid == "sm" else "t1 and t0, 26.10.1" if cid == "bm"
                        else "262K, 512K, 1M" if cid == "ss" else "262K, one run"},
            "speed": {"measured": any(not s["absent"] for s in p["speed"][cid]),
                      "note": "8K–512K; 1M fails" if CELL[cid]["engine"] == "mlx-serve" else "8K–1M"},
            "effort": {"measured": p["effort"][cid] is not None, "note": "low, medium, xhigh" if p["effort"][cid] else ""},
            "longctx": {"measured": p["longctx"][cid] is not None, "note": ""},
            "toolcall": {"measured": p["toolcall"][cid] is not None, "note": ""},
            "tbench": {"measured": p["tbench"][cid] is not None, "note": "89 tasks, 262K" if p["tbench"][cid] else ""},
            "claude_code": {"measured": p["claude_code"][cid] is not None, "note": "4 tasks, 2 reps" if p["claude_code"][cid] else ""},
            "probes": {"measured": cid in AGENT_PROBES, "note": "3b, 3c" if cid in AGENT_PROBES else ""},
        }
    return cov


def collect() -> dict:
    data = json.loads(REPORTS_JSON.read_text(encoding="utf-8"))
    p = {"quality": collect_quality(), "speed": collect_speed(data), "tbench": collect_tbench(),
         "effort": collect_effort(), "claude_code": collect_claude_code(), "longctx": collect_longctx(),
         "toolcall": collect_toolcall(), "probes": AGENT_PROBES,
         "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%MZ")}
    p["coverage"] = collect_coverage(p)
    return p


# ------------------------------------------------------------------------------------------------------------ render

def fmt(v, nd=1, unit="") -> str:
    if v is None:
        return '<span class="na">—</span>'
    if isinstance(v, float):
        s = f"{v:,.{nd}f}" if nd else f"{v:,.0f}"
    else:
        s = f"{v:,}" if isinstance(v, int) else str(v)
    return s + (f'<span class="u">{unit}</span>' if unit else "")


def swatch(cid: str) -> str:
    return f'<span class="sw" style="background:var({CELL[cid]["color"]})"></span>'


def cell_label(cid: str, extra: str = "") -> str:
    sfx = f' <span class="u">{E(extra)}</span>' if extra else ""
    return f'<span class="arm-lab">{swatch(cid)}{E(CELL[cid]["name"])}{sfx}</span>'


def _marker(shape: str, x: float, y: float, r: float = 5.0) -> str:
    if shape == "circle":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}"/>'
    if shape == "square":
        return f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r}" height="{2 * r}"/>'
    if shape == "diamond":
        return f'<path d="M{x:.1f} {y - r * 1.25:.1f}L{x + r * 1.25:.1f} {y:.1f}L{x:.1f} {y + r * 1.25:.1f}L{x - r * 1.25:.1f} {y:.1f}Z"/>'
    return f'<path d="M{x:.1f} {y - r * 1.2:.1f}L{x + r * 1.15:.1f} {y + r * 0.9:.1f}L{x - r * 1.15:.1f} {y + r * 0.9:.1f}Z"/>'


def _nice_ticks(top: float, n: int = 4) -> list[float]:
    if top <= 0:
        return [0, 1]
    raw = top / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    return [i * step for i in range(int(math.ceil(top / step)) + 1)]


def line_chart(series: list[tuple[str, list[tuple[int, float | None, str]]]], unit: str, title: str,
               w: int = 620, h: int = 330, nd: int = 1) -> str:
    """One line per cell over the context bands. A point is (ctx, value, tooltip). value None = absent (shown as ×)."""
    L, R, T, B = 52, 16, 14, 42
    xs = {c: L + i * (w - L - R) / (len(CTX) - 1) for i, c in enumerate(CTX)}
    top = max((v for _, pts in series for _, v, _ in pts if v is not None), default=1)
    ticks = _nice_ticks(top * 1.05)
    ymax = ticks[-1]
    y = lambda v: T + (h - T - B) * (1 - v / ymax)  # noqa: E731
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{E(title)}">']
    for t in ticks:
        out.append(f'<line class="gl" x1="{L}" x2="{w - R}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                   f'<text class="tick" x="{L - 6}" y="{y(t) + 4:.1f}" text-anchor="end">{t:g}</text>')
    for c in CTX:
        out.append(f'<text class="tick" x="{xs[c]:.1f}" y="{h - B + 18}" text-anchor="middle">{CTX_LABEL[c]}</text>')
    for cid, pts in series:
        col, shape = CELL[cid]["color"], CELL[cid]["marker"]
        path = []
        for c, v, _ in pts:
            if v is None:
                path.append(None)
            else:
                path.append((xs[c], y(v)))
        d, pen = "", False
        for pt in path:
            if pt is None:
                pen = False
                continue
            d += ("L" if pen else "M") + f"{pt[0]:.1f} {pt[1]:.1f}"
            pen = True
        out.append(f'<g style="--c:var({col})"><path class="ln" d="{d}"/>')
        for c, v, tip in pts:
            if v is None:
                out.append(f'<g class="absent" data-tip="{E(tip)}"><text x="{xs[c]:.1f}" y="{h - B - 6}" text-anchor="middle">×</text>'
                           f'<rect class="hit" x="{xs[c] - 12:.1f}" y="{h - B - 22}" width="24" height="24"/></g>')
            else:
                out.append(f'<g class="mk" data-tip="{E(tip)}">{_marker(shape, xs[c], y(v))}'
                           f'<rect class="hit" x="{xs[c] - 12:.1f}" y="{y(v) - 12:.1f}" width="24" height="24"/></g>')
        last = [(c, v) for c, v, _ in pts if v is not None]
        if last:
            c, v = last[-1]
            out.append(f'<text class="dl" x="{xs[c] + 9:.1f}" y="{y(v) + 4:.1f}">{v:.{nd}f}</text>')
        out.append("</g>")
    out.append("</svg>")
    return "".join(out)


def dot_plot(suite: str, runs: list[tuple[str, str, dict]], w: int = 640) -> str:
    """One row per run, one dot per question, log seconds. runs = (cell id, column label, suite stats)."""
    rows = list(runs)
    if not any(st for _, _, st in rows):
        return '<p class="empty">not measured</p>'
    L, R, T, rh = 150, 24, 26, 40
    h = T + rh * len(rows) + 30
    allv = [p["s"] for _, _, st in rows if st for p in st["points"] if p["s"] > 0]
    lo, hi = max(min(allv), 0.3), max(allv)
    lx, hx = math.log10(lo), math.log10(hi * 1.15)
    x = lambda s: L + (w - L - R) * (math.log10(max(s, lo)) - lx) / (hx - lx)  # noqa: E731
    out = [f'<svg class="chart dots" viewBox="0 0 {w} {h}" role="img" aria-label="{E(SUITE_LABEL[suite])}, time per question">']
    t = 1.0
    while t <= hi * 1.15:
        if t >= lo:
            out.append(f'<line class="gl" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{T - 8}" y2="{h - 26}"/>'
                       f'<text class="tick" x="{x(t):.1f}" y="{h - 10}" text-anchor="middle">{t:g}s</text>')
        t *= 10
    for i, (cid, lab, st) in enumerate(rows):
        cy = T + rh * i + rh / 2
        out.append(f'<g style="--c:var({CELL[cid]["color"]})">')
        out.append(f'<text class="rowlab" x="0" y="{cy - 4:.1f}">{E(CELL[cid]["name"])}</text>'
                   f'<text class="rowsub" x="0" y="{cy + 10:.1f}">{E(lab)}</text>')
        if not st:
            out.append(f'<text class="rowsub" x="{L}" y="{cy + 4:.1f}">not measured</text></g>')
            continue
        for j, p in enumerate(st["points"]):
            jit = ((hash((cid, p["id"])) % 1000) / 1000 - 0.5) * (rh - 14)
            px, py = x(p["s"]), cy + jit
            cls = "dot" + ("" if p["ok"] else " bad") + (" trunc" if p["trunc"] else "")
            tip = f'{lab} · #{p["id"]} · {p["s"]:.1f} s · {p["tok"]} tokens · {"correct" if p["ok"] else "wrong"}{" · truncated" if p["trunc"] else ""}'
            out.append(f'<g class="{cls}" data-tip="{E(tip)}"><circle cx="{px:.1f}" cy="{py:.1f}" r="3.6"/></g>')
        if st["median_s"]:
            mx = x(st["median_s"])
            out.append(f'<line class="med" x1="{mx:.1f}" x2="{mx:.1f}" y1="{cy - rh / 2 + 3:.1f}" y2="{cy + rh / 2 - 3:.1f}"/>'
                       f'<text class="medlab" x="{mx + 5:.1f}" y="{cy - rh / 2 + 11:.1f}">{st["median_s"]:.1f} s</text>')
        out.append("</g>")
    out.append("</svg>")
    return "".join(out)


def hbars(rows: list[tuple], label_w: int = 150, value_w: int = 230) -> str:
    """Horizontal bars: (cell id, value, max, value text[, label suffix]). The label and value columns have fixed widths,
    so every row's track is the same width and equal values draw equal bars."""
    out = [f'<div class="bars" style="--lw:{label_w}px;--vw:{value_w}px">']
    for row in rows:
        cid, v, mx, text = row[:4]
        sub = row[4] if len(row) > 4 else ""
        pct = 0 if not mx else max(0.0, min(100.0, 100 * v / mx))
        out.append(f'<div class="bline">{cell_label(cid, sub)}<span class="btrack"><span class="bfill" '
                   f'style="width:{pct:.1f}%;background:var({CELL[cid]["color"]})"></span></span><span class="bv">{text}</span></div>')
    out.append("</div>")
    return "".join(out)


def tiles(p: dict) -> str:
    out = ['<section class="block" id="tiles"><div class="tiles4">']
    sp = {cid: {s["ctx"]: s for s in p["speed"][cid]} for cid in CELL}
    for cid in ("bm", "sm", "bs", "ss"):
        if cid == "bm":
            q = p["quality"]["mlx"]["t1"]["bm"]
            src = "t1, mlx-serve 26.10.1"
        elif cid == "sm":
            q = p["quality"]["swift262"]["sm"]
            src = "262K, mlx-serve 26.10.3"
        elif cid == "ss":
            q = p["quality"]["swift262"]["ss"]
            src = "262K, Splash 1.4.0"
        else:
            q = p["quality"]["splash262"]["bs"]
            src = "262K, Splash 1.4.0"
        s256 = sp[cid][262144]
        he = fmt(q["humaneval"].get("with_imports"), 0) + "<span class='u'>/164</span>" if q else '<span class="na">not measured</span>'
        gp = fmt(q["gpqa"]["passed"], 0) + "<span class='u'>/50</span>" if q else '<span class="na">not measured</span>'
        out.append(f'<div class="tile" style="--c:var({CELL[cid]["color"]})"><p class="t-lab">{swatch(cid)} {E(CELL[cid]["name"])}</p>'
                   f'<div class="t-row"><span><b>{he}</b><small>HumanEval</small></span><span><b>{gp}</b><small>GPQA</small></span></div>'
                   f'<div class="t-row"><span><b>{fmt(s256["t_turno_s"], 1, " s")}</b><small>agent turn, 256K</small></span>'
                   f'<span><b>{fmt(s256["decode_tps"], 0, " tok/s")}</b><small>decode, 256K</small></span></div>'
                   f'<p class="t-sub">{E(src)} · max context {E(CELL[cid]["max"].split(" ")[0])}</p></div>')
    out.append("</div></section>")
    return "".join(out)


def grid_section() -> str:
    rows = "".join(
        f'<tr><td>{cell_label(c["id"])}</td><td class="nm">{E(c["model_name"])}</td><td class="nm"><span class="mono">{E(c["weights"])}</span> '
        f'<span class="mono">@{E(c["rev"])}</span></td><td class="nm">{E(c["quant"])}</td><td class="nm">{E(c["disk"])}</td>'
        f'<td class="nm">{E(c["runtime"])}</td><td class="nm">{E(c["spec"])}</td><td class="nm">{E(c["max"])}</td><td class="nm mono">{E(c["arms"])}</td></tr>'
        for c in CELLS)
    return ('<section class="block" id="grid"><h2 class="sec">1 · The four cells</h2>'
            '<p class="s-note">Two weights of the same model on two servers. The base model is Qwen3.8-Flash-Next as released; '
            'Swift 1.5 is a fine-tune that keeps the architecture and trains the model to think with fewer tokens. mlx-serve runs MLX '
            'packs; Splash runs GGUF only, so each engine has its own quant of each model.</p>'
            '<div class="tbl-scroll"><table class="cfg"><thead><tr><th>cell</th><th class="nm">model</th><th class="nm">weights</th>'
            '<th class="nm">quant</th><th class="nm">disk</th><th class="nm">runtime</th><th class="nm">speculation</th>'
            f'<th class="nm">max context</th><th class="nm">arm ids</th></tr></thead><tbody>{rows}</tbody></table></div></section>')


def _acc_cell(st: dict | None, suite: str) -> str:
    if st is None or suite not in st:
        return '<td class="na">not measured</td>'
    s = st[suite]
    if suite == "humaneval":
        imp = s.get("with_imports")
        r2 = s.get("with_imports_r2")
        strict = f'{s["passed"]}' + (f' · {s["strict_r2"]}' if s.get("strict_r2") is not None else "")
        if imp is None:
            return f'<td>{strict}/{s["n"]}</td>'
        return f'<td><b>{imp}{" · " + str(r2) if r2 else ""}</b>/{s["n"]} <span class="u">strict {strict}</span></td>'
    tr = f' <span class="u">{s["truncated"]} trunc</span>' if s["truncated"] else ""
    return f'<td><b>{s["passed"]}</b>/{s["n"]}{tr}</td>'


def accuracy_section(p: dict) -> str:
    q = p["quality"]
    cols = [("bm", "t1 · 26.10.1", q["mlx"]["t1"]["bm"]), ("sm", "t1 · 26.10.1", q["mlx"]["t1"]["sm"]),
            ("sm", "262K · 26.10.3", q["swift262"]["sm"]), ("ss", "262K · Splash 1.4.0", q["swift262"]["ss"]),
            ("bs", "262K · Splash 1.4.0", q["splash262"]["bs"])]
    head = "".join(f'<th>{cell_label(cid, lab)}</th>' for cid, lab, _ in cols)
    body = ""
    for suite in SUITES:
        body += f'<tr><td class="nm">{E(SUITE_LABEL[suite])} <span class="u">G1 margin {G1_MARGIN[suite]}</span></td>'
        body += "".join(_acc_cell(st, suite) for _, _, st in cols) + "</tr>"
    # bars: share correct per suite, the five columns
    panels = []
    for suite in SUITES:
        rows = []
        for cid, lab, st in cols:
            if st and suite in st:
                s = st[suite]
                v = s.get("with_imports") if suite == "humaneval" and s.get("with_imports") else s["passed"]
                rows.append((cid, v, s["n"], f'{v}/{s["n"]}', lab))
            else:
                rows.append((cid, 0, 1, '<span class="na">not measured</span>', lab))
        panels.append(f'<figure class="card-chart"><p class="c-head">{E(SUITE_LABEL[suite])}</p>{hbars(rows, 215, 72)}</figure>')
    g1 = []
    for a, b, lab in (("bm", "sm", "Swift vs base, mlx-serve t1"), ("sm", "ss", "Splash vs mlx-serve, Swift 262K")):
        pa = q["mlx"]["t1"] if a == "bm" else q["swift262"]
        pb = q["mlx"]["t1"] if a == "bm" else q["swift262"]
        sa, sb = pa[a], pb[b]
        if not sa or not sb:
            continue
        fails = [s for s in SUITES if s in sa and s in sb and sb[s]["passed"] < sa[s]["passed"] - G1_MARGIN[s]]
        g1.append(f'<li><b>{E(lab)}:</b> G1 {"passes in all six suites" if not fails else "fails in " + ", ".join(fails)}.</li>')
    sa, sb = q["splash262"]["ss"], q["splash262"]["bs"]
    fails = [s for s in SUITES if sb and sb[s]["passed"] < sa[s]["passed"] - G1_MARGIN[s]] if sb else []
    g1.append('<li><b>base vs Swift, Splash 262K:</b> ' + ("not measured: the base battery on Splash has not run." if not sb else
              "G1 " + ("passes in all six suites" if not fails else "fails in " + ", ".join(fails))) + ".")
    if sb and "humaneval" in fails and sb["humaneval"].get("with_imports") and sa["humaneval"].get("with_imports") \
            and sb["humaneval"]["with_imports"] >= sa["humaneval"]["with_imports"] - G1_MARGIN["humaneval"]:
        g1[-1] += (f' HumanEval fails on the strict grade only; with the prompt\'s imports it scores '
                   f'{sb["humaneval"]["with_imports"]}/164 against {sa["humaneval"]["with_imports"]}/164.')
    g1[-1] += "</li>"
    return ('<section class="block" id="accuracy"><h2 class="sec">2 · Accuracy</h2>'
            '<p class="s-note">Six suites, vendor sampling (temperature 1.0, top-p 0.95, top-k 20), reasoning effort xhigh, one run per column. '
            'HumanEval counts a solution with the prompt\'s import lines in front (bold) and the strict grade beside it. '
            'G1 passes when a candidate scores at least the reference minus the margin. Two runs of the same setup differ by 4–6 HumanEval questions.</p>'
            f'<ul class="s-note">{"".join(g1)}</ul>'
            f'<div class="tbl-scroll"><table class="qual"><thead><tr><th class="nm">suite</th>{head}</tr></thead><tbody>{body}</tbody></table></div>'
            f'<div class="cgrid">{"".join(panels)}</div></section>')


def time_section(p: dict) -> str:
    q = p["quality"]
    runs = [("bm", "t1 · mlx-serve 26.10.1", q["mlx"]["t1"]["bm"]), ("sm", "t1 · mlx-serve 26.10.1", q["mlx"]["t1"]["sm"]),
            ("sm", "262K · mlx-serve 26.10.3", q["swift262"]["sm"]), ("ss", "262K · Splash 1.4.0", q["swift262"]["ss"]),
            ("bs", "262K · Splash 1.4.0", q["splash262"]["bs"])]
    figs = []
    for suite in ("gpqa", "livecodebench", "humaneval"):
        figs.append(f'<figure class="strip"><p class="p-title">{E(SUITE_LABEL[suite])}</p>'
                    + dot_plot(suite, [(cid, lab, st[suite] if st and suite in st else None) for cid, lab, st in runs]) + "</figure>")
    head = "".join(f"<th>{cell_label(cid, lab)}</th>" for cid, lab, _ in runs)
    rows = ""
    for suite in ("gpqa", "livecodebench", "humaneval"):
        for key, name, nd, unit in (("median_s", "median time", 1, " s"), ("total_s", "suite total", 0, " s"),
                                    ("median_completion", "median tokens", 0, ""), ("median_reasoning_chars", "median reasoning", 0, " chars"),
                                    ("truncated", "truncated", 0, ""), ("sec_per_correct", "seconds per correct answer", 1, " s")):
            rows += f'<tr><td class="nm">{E(SUITE_LABEL[suite])} · {name}</td>'
            for _, _, st in runs:
                v = st[suite].get(key) if st and suite in st else None
                rows += f"<td>{fmt(v, nd, unit) if v is not None else fmt(None)}</td>"
            rows += "</tr>"
    # LCB by difficulty
    diff = ""
    for d in ("easy", "medium", "hard"):
        diff += f'<tr><td class="nm">LCB {d}</td>'
        for _, _, st in runs:
            ld = st.get("lcb_difficulty") if st else None
            if ld and d in ld:
                diff += f'<td>{ld[d]["passed"]}/{ld[d]["n"]} <span class="u">{ld[d]["median_s"]:.0f} s</span></td>'
            else:
                diff += '<td class="na">—</td>'
        diff += "</tr>"
    return ('<section class="block" id="time"><h2 class="sec">3 · Time and tokens per answer</h2>'
            '<p class="s-note">One dot per question, log scale; hollow dots are wrong answers, the bar is the median. Both engines and both '
            'models here; the base model reaches the same accuracy with about three times the reasoning tokens on GPQA and twice on LiveCodeBench, '
            'so its answers take 2–3× longer. On Splash, Swift decodes faster but thinks a little longer than on mlx-serve, so the time per '
            'question is close between the two engines.</p>'
            f'<div class="sgrid">{"".join(figs)}</div>'
            '<p class="legend s-note"><span class="dotkey"></span> correct <span class="dotkey hollow"></span> wrong <span class="medkey"></span> median</p>'
            f'<div class="tbl-scroll"><table class="timet"><thead><tr><th class="nm">metric</th>{head}</tr></thead><tbody>{rows}{diff}</tbody></table></div>'
            '</section>')


def effort_section(p: dict) -> str:
    e = p["effort"]
    head = "".join(f'<th>{cell_label(cid)}</th>' for cid in ("bm", "sm", "bs", "ss"))
    rows = ""
    for eff in EFFORTS:
        for key, name in (("gpqa", "GPQA correct"), ("livecodebench", "LCB correct"), ("total_s", "GPQA+LCB time"),
                          ("total_tokens", "GPQA+LCB tokens")):
            rows += f'<tr><td class="nm">{eff} · {name}</td>'
            for cid in ("bm", "sm", "bs", "ss"):
                r = e.get(cid)
                if not r:
                    rows += '<td class="na">not measured</td>'
                    continue
                v = r[eff]
                if key in ("gpqa", "livecodebench"):
                    rows += f'<td>{fmt(v[key]["passed"], 1 if v["rounds"] > 1 else 0)}/{v[key]["n"]}' + (
                        f' <span class="u">{v[key]["truncated"]:g} trunc</span>' if v[key]["truncated"] else "") + "</td>"
                elif key == "total_s":
                    rows += f'<td>{fmt(v[key] / 60, 0, " min")}</td>'
                else:
                    rows += f'<td>{fmt(v[key] / 1000, 0, "K")}</td>'
            rows += "</tr>"
    # one chart, one group per effort level, the same token scale in every group
    mx = max(e[c][eff]["total_tokens"] for c in ("bm", "sm") if e.get(c) for eff in EFFORTS)
    groups = ""
    for eff in EFFORTS:
        rws = [(cid, e[cid][eff]["total_tokens"], mx,
                f'{e[cid][eff]["total_tokens"] / 1000:,.0f}K · {e[cid][eff]["gpqa"]["passed"]:g}+{e[cid][eff]["livecodebench"]["passed"]:g}')
               for cid in ("bm", "sm") if e.get(cid)]
        groups += f'<div class="bgroup"><p class="b-lab">{eff}</p>{hbars(rws, 150, 130)}</div>'
    bars = [f'<figure class="card-chart"><p class="c-head">Tokens for GPQA 50 + LCB 50 by effort level, lower is cheaper</p>'
            f'<p class="c-note">value: thousands of completion tokens · GPQA + LCB correct answers</p>{groups}</figure>']
    return ('<section class="block" id="effort"><h2 class="sec">4 · Reasoning effort</h2>'
            '<p class="s-note">GPQA-Diamond 50 and LiveCodeBench 50 at three effort levels, mlx-serve 26.10.1. The base at xhigh is the '
            'swift15 A/B run; its medium and low come from the effort-tail task; Swift has two rounds per level (means shown). At xhigh the '
            'base spends 1.7× the tokens of Swift; at medium and low the two are close, so the gap at xhigh is the base thinking longer, not '
            'the engine. Not measured on Splash.</p>'
            f'{"".join(bars)}'
            f'<div class="tbl-scroll mt"><table class="timet"><thead><tr><th class="nm">effort · metric</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            '</section>')


def _tip(cid: str, s: dict, key: str, unit: str, nd: int = 1) -> str:
    cfg = f" · {s['config']}" if s.get("config") else ""
    return f'{CELL[cid]["name"]} · {CTX_LABEL[s["ctx"]]} · {s[key]:.{nd}f}{unit} · {s["reps"]} rep{"s" if s["reps"] != 1 else ""}{cfg} · arm {s["arm"]}'


def speed_section(p: dict) -> str:
    sp = p["speed"]
    order = ("bm", "sm", "bs", "ss")

    def series(key, unit, nd=1):
        return [(cid, [(s["ctx"], None if s["absent"] else s[key],
                        f'{CELL[cid]["name"]} · {CTX_LABEL[s["ctx"]]} · {s["absent"]}' if s["absent"] else _tip(cid, s, key, unit, nd))
                       for s in sp[cid]]) for cid in order]

    legend = "".join(f'<span class="lg">{cell_label(cid)}</span>' for cid in order)
    head = "".join(f"<th>{CTX_LABEL[c]}</th>" for c in CTX)
    rows = ""
    for key, name, nd, unit in (("t_turno_s", "agent turn (T_turn)", 1, " s"), ("decode_tps", "decode", 0, " tok/s"),
                                ("cold_ttft_s", "cold TTFT", 0, " s"), ("warm_ttft_s", "warm TTFT, tool turn", 1, " s"),
                                ("prefill_tps", "prefill", 0, " tok/s")):
        for cid in order:
            rows += f'<tr><td class="nm">{name} · {cell_label(cid)}</td>'
            for s in sp[cid]:
                if s["absent"]:
                    rows += f'<td class="na" title="{E(s["absent"])}">×</td>'
                else:
                    cfg = f' <span class="u">{E(s["config"])}</span>' if s.get("config") else ""
                    rows += f'<td>{fmt(s[key], nd, unit)}{cfg}</td>'
            rows += "</tr>"
    return ('<section class="block" id="speed"><h2 class="sec">5 · Agent turn by context size</h2>'
            '<p class="s-note">T_turn = warm TTFT of a tool turn + 512 tokens at the decode speed, with the server at each context size; '
            'mlx-serve 26.10.3 and Splash 1.4.0, three reps (one at 1M and for mlx-serve at 256K). On mlx-serve the two models tie up to 128K and '
            'the base falls behind from 256K. On Splash the Swift GGUF decodes 8–18% faster than the base GGUF in every band. The engine matters '
            'more than the model: Splash takes 0.72× the mlx-serve turn at 256K and is the only one that serves 1M. ✕ marks a band the '
            'server could not serve; hover for the reason.</p>'
            f'<p class="legend s-note">{legend}</p>'
            '<div class="cgrid"><figure class="card-chart"><p class="c-head">Agent turn (s), lower is better</p>'
            f'{line_chart(series("t_turno_s", " s"), "s", "agent turn by context")}</figure>'
            '<figure class="card-chart"><p class="c-head">Decode speed (tok/s)</p>'
            f'{line_chart(series("decode_tps", " tok/s", 0), "tok/s", "decode speed by context", nd=0)}</figure>'
            '<figure class="card-chart"><p class="c-head">Cold time to first token (s)</p>'
            f'{line_chart(series("cold_ttft_s", " s", 0), "s", "cold TTFT by context", nd=0)}</figure>'
            '<figure class="card-chart"><p class="c-head">Warm time to first token, tool turn (s)</p>'
            f'{line_chart(series("warm_ttft_s", " s"), "s", "warm TTFT by context")}</figure></div>'
            f'<div class="tbl-scroll"><table class="speedt"><thead><tr><th class="nm">metric · cell</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            '</section>')


def cache_section(p: dict) -> str:
    sp = p["speed"]
    head = "".join(f"<th>{CTX_LABEL[c]}</th>" for c in CTX)
    rows = ""
    for sc in SCENARIOS:
        for cid in ("bm", "sm", "bs", "ss"):
            rows += f'<tr><td class="nm">{E(sc)} · {cell_label(cid)}</td>'
            for s in sp[cid]:
                v = None if s["absent"] else s["hit"].get(sc)
                if v is None:
                    rows += '<td class="na">—</td>'
                else:
                    shade = max(0.06, v)
                    rows += f'<td class="heat" style="--a:{shade:.2f}">{v:.2f}</td>'
            rows += "</tr>"
    return ('<section class="block" id="cache"><h2 class="sec">6 · Cache hit by scenario</h2>'
            '<p class="s-note">Share of the prompt served from the prefix cache on the next turn. Both engines hit 0.99–1.00 on an identical '
            'prompt, an appended message and a tool turn from 128K up. The difference is an edit in the middle of the history: mlx-serve keeps the '
            'prefix before the edit (hit 0.41–0.48); Splash recomputes the whole prompt (hit 0), which at 1M costs the 25-minute cold prefill again. '
            'Flash-Next is a hybrid model: its recurrent layers carry a state that cannot roll back, and Splash saves that state only at the end of each request.</p>'
            f'<div class="tbl-scroll"><table class="heatt"><thead><tr><th class="nm">scenario · cell</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            '</section>')


def memory_section(p: dict) -> str:
    sp = p["speed"]
    head = "".join(f"<th>{CTX_LABEL[c]}</th>" for c in CTX)
    rows = ""
    for cid in ("bm", "sm", "bs", "ss"):
        rows += f'<tr><td class="nm">wired peak · {cell_label(cid)}</td>'
        for s in sp[cid]:
            rows += '<td class="na">×</td>' if s["absent"] else f'<td>{fmt(s["wired_peak_gb"], 1, " GB")}</td>'
        rows += "</tr>"
    for cid in ("bm", "sm", "bs", "ss"):
        rows += f'<tr><td class="nm">free memory, minimum · {cell_label(cid)}</td>'
        for s in sp[cid]:
            rows += '<td class="na">×</td>' if s["absent"] else f'<td>{fmt(s["mem_free_min_gb"], 2, " GB")}</td>'
        rows += "</tr>"
    return ('<section class="block" id="memory"><h2 class="sec">7 · Memory on 128 GB</h2>'
            '<p class="s-note">Peak wired memory during the probe and the minimum free memory. Splash pins ~16 GB more than mlx-serve at 8K; '
            'mlx-serve compresses ~8.5 GB during the load instead. Headroom (128 GB minus wired and compressor peaks) at 256K: 9.8 GB for the base '
            'on Splash, 10.1 GB for Swift on Splash, 5.5 GB for Swift on mlx-serve. At 512K mlx-serve needs 4-bit KV and YaRN 2.0 and keeps 3.8 GB of '
            'headroom; at 1M it refuses 2–3 of 5 requests after the first. Splash serves 1M with KV int8 and 14.8–16.9 GB of headroom, with the KV past '
            '~860K tokens on SSD.</p>'
            f'<div class="tbl-scroll"><table class="speedt"><thead><tr><th class="nm">metric · cell</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            '</section>')


def agent_section(p: dict) -> str:
    tb, cc, pr = p["tbench"], p["claude_code"], p["probes"]
    # Terminal-Bench
    tb_rows = [(cid, tb[cid]["passed"], 89, f'{tb[cid]["passed"]}/89 <span class="u">{100 * tb[cid]["passed"] / 89:.1f}% · median task {tb[cid]["median_task_min"]:.1f} min</span>')
               if tb.get(cid) else (cid, 0, 1, '<span class="na">not measured</span>') for cid in ("bm", "sm", "bs", "ss")]
    pair = tb.get("pair")
    pair_html = ""
    if pair:
        pair_html = (f'<p class="s-note mt">Paired: both pass <b>{pair["both"]}</b>, only mlx-serve <b>{pair["only_sm"]}</b>, only Splash <b>{pair["only_ss"]}</b>, '
                     f'neither <b>{pair["neither"]}</b>. Exact McNemar p = {pair["p"]:.2f}: no difference between the two engines with one attempt per task. '
                     f'Median call latency: {tb["sm"]["median_request_s"]:.1f} s on mlx-serve, {tb["ss"]["median_request_s"]:.1f} s on Splash.</p>')
    # Claude Code
    cc_fig = ""
    if cc.get("sm") and cc.get("ss"):
        tasks = [("a", "a · --format json in a small Python package"), ("b", "b · two bugs in a bash script"),
                 ("c", "c · --group-by in a 3.7K-line package, 60–70K context"), ("d", "d · bugs and a refactor in a 1.1K-line bash toolkit")]
        mx = max(v for cid in ("sm", "ss") for v in cc[cid]["alone_s"].values())
        groups = ""
        for t, lab in tasks:
            rws = [(cid, cc[cid]["alone_s"][t], mx, f'{cc[cid]["alone_s"][t]:.0f} s') for cid in ("sm", "ss")]
            groups += f'<div class="bgroup"><p class="b-lab">{E(lab)}</p>{hbars(rws, 150, 64)}</div>'
        cc_fig = ('<figure class="card-chart"><p class="c-head">Claude Code, one session: wall time per task (mean of 2 reps), lower is better</p>'
                  f'<p class="c-note">Claude Code 2.1.292, effort xhigh, 128K servers: Splash 1.5.0 and mlx-serve 26.10.3. Warm TTFT p50 '
                  f'{cc["sm"]["warm_ttft_p50"]:.2f} s / {cc["ss"]["warm_ttft_p50"]:.2f} s, decode p50 {cc["sm"]["warm_tps_p50"]:.0f} / '
                  f'{cc["ss"]["warm_tps_p50"]:.0f} tok/s (mlx-serve / Splash). Swift only.</p>{groups}</figure>')
    # probes
    pr_rows = "".join(
        f'<tr><td>{cell_label(cid)}</td><td>{fmt(pr[cid]["tokens_3b"], 1)}</td><td>{pr[cid]["empty_3c"]}</td><td>{pr[cid]["wrong_3c"]}</td></tr>'
        for cid in ("bm", "sm")) + "".join(
        f'<tr><td>{cell_label(cid)}</td><td class="na" colspan="3">not measured</td></tr>' for cid in ("bs", "ss"))
    return ('<section class="block" id="agent"><h2 class="sec">8 · Agent tasks</h2>'
            '<p class="s-note">Terminal-Bench 2.1: 89 tasks, agent terminus-2, one attempt per task, context 262144, each task\'s own agent timeout. '
            'Only Swift ran it, on both engines. The base model has no Terminal-Bench run: one attempt per task cannot resolve a gap under ~8 tasks, '
            'and a run costs ~31 hours of the rig.</p>'
            f'<figure class="card-chart"><p class="c-head">Terminal-Bench 2.1 tasks passed</p>{hbars(tb_rows)}</figure>{pair_html}'
            f'{cc_fig}'
            '<p class="s-note mt">Long agent sessions on mlx-serve 26.10.1 (probes 3b and 3c of the next-steps campaign): 40 tool-loop sessions and '
            '30 turns that grow a session to ~200K tokens. The base model wrote 1.7× the tokens per turn and returned 4 empty answers and 4 wrong code '
            'turns past 140K; Swift returned none.</p>'
            '<div class="tbl-scroll"><table class="qual"><thead><tr><th class="nm">cell</th><th>3b median tokens per turn</th>'
            f'<th>3c empty turns of 30</th><th>3c wrong code turns of 30</th></tr></thead><tbody>{pr_rows}</tbody></table></div></section>')


def longctx_section(p: dict) -> str:
    lc, tc = p["longctx"], p["toolcall"]
    rows = ""
    for cid in ("bm", "sm", "bs", "ss"):
        if not lc.get(cid):
            rows += f'<tr><td>{cell_label(cid)}</td><td class="na" colspan="5">not measured</td></tr>'
            continue
        by_server = {}
        for r in lc[cid]:
            by_server.setdefault((r["arm"], r["server"]), {})[r["band"]] = r
        for (arm, server), bands in sorted(by_server.items(), key=lambda kv: kv[0][1]):
            rows += f'<tr><td>{cell_label(cid, f"server {CTX_LABEL.get(server, server)} · {arm}")}</td>'
            for band in (131072, 262144, 524288, 1000000):
                r = bands.get(band)
                rows += f'<td>{r["correct"]}/{r["n"]}</td>' if r else '<td class="na">—</td>'
            rows += "</tr>"
    tc_rows = ""
    for cid in ("bm", "sm", "bs", "ss"):
        if not tc.get(cid):
            tc_rows += f'<tr><td>{cell_label(cid)}</td><td class="na" colspan="2">not measured</td></tr>'
            continue
        tc_rows += f'<tr><td>{cell_label(cid)}</td>'
        for fp in ("fp0", "fp1"):
            r = tc[cid].get(fp)
            tc_rows += (f'<td>{r["sessions_ok"]}/{r["sessions"]} sessions <span class="u">{r["turns_ok"]}/{r["turns"]} turns</span></td>'
                        if r else '<td class="na">—</td>')
        tc_rows += "</tr>"
    return ('<section class="block" id="longctx"><h2 class="sec">9 · Long context and tool calls</h2>'
            '<p class="s-note">Long-context recall: eight questions over a document that fills 97% of the band (lookups and sums), on a server '
            'started at the size in the row label. Every measured cell answers 8/8 at its own size; Swift on Splash missed one sum at 128K on the 1M '
            'server. Tool calls: 20 sessions of 4 turns; with frequency_penalty 0 (what the agent clients send) both engines pass every turn; with '
            'penalty 1 both fail, for different reasons. The base model has neither probe.</p>'
            '<div class="tbl-scroll"><table class="qual"><thead><tr><th class="nm">cell · server</th><th>128K</th><th>256K</th><th>512K</th><th>1M</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
            '<div class="tbl-scroll mt"><table class="qual"><thead><tr><th class="nm">cell</th><th>frequency_penalty 0</th><th>frequency_penalty 1</th></tr></thead>'
            f'<tbody>{tc_rows}</tbody></table></div></section>')


COVERAGE_COLS = [("battery", "six-suite battery"), ("speed", "agent turn by context"), ("effort", "effort levels"),
                 ("longctx", "long-context recall"), ("toolcall", "tool-call probe"), ("tbench", "Terminal-Bench 2.1"),
                 ("claude_code", "Claude Code, real sessions"), ("probes", "long-session probes")]


def coverage_section(p: dict) -> str:
    cov = p["coverage"]
    head = "".join(f'<th class="nm">{E(lab)}</th>' for _, lab in COVERAGE_COLS)
    rows = ""
    for cid in ("bm", "sm", "bs", "ss"):
        rows += f"<tr><td>{cell_label(cid)}</td>"
        for key, _ in COVERAGE_COLS:
            c = cov[cid][key]
            note = f' <span class="u">{E(c["note"])}</span>' if c["note"] else ""
            rows += (f'<td class="cov yes">measured{note}</td>' if c["measured"] else f'<td class="cov no">not measured{note}</td>')
        rows += "</tr>"
    return ('<section class="block" id="coverage"><h2 class="sec">10 · What was measured, and what was not</h2>'
            '<p class="s-note">The base model on Splash has speed, cache and memory in every band, and no quality measurement yet: its six-suite '
            'battery at 262144 is the next run. The base model has no Terminal-Bench, long-context or tool-call probe on either engine. The quality '
            'A/B of the two models ran on mlx-serve 26.10.1 (2026-10-10); the same-build comparison on 26.10.3 covers speed only. Every quality cell '
            'is one run; two runs of the same setup differ by 4–6 HumanEval questions.</p>'
            f'<div class="tbl-scroll"><table class="cfg covt"><thead><tr><th class="nm">cell</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            '</section>')


def method_section(p: dict) -> str:
    return ('<section class="block" id="method"><details><summary><h2 class="sec">11 · How I measured</h2></summary>'
            '<ul class="s-note mt">'
            '<li><b>Rig.</b> Mac Studio M4 Max, 128 GB unified memory, macOS 26.6, no sudo (default wired limit). mlx-serve on port 11234, Splash on 8585.</li>'
            '<li><b>Battery.</b> HumanEval 164, GPQA-Diamond 50 (seed 42), LiveCodeBench v6 50 (seed 42), an IFEval-style probe of 20, and two tool-call '
            'suites (40 and 12 cases). temperature 1.0, top-p 0.95, top-k 20, reasoning_effort xhigh, max_tokens 32768–65536. Questions run one at a time. '
            'Runners: bench2.py, tool_call_bench.py and if_probe.py of the local-llm-bench submodule; gates by summarize_ab.py.</li>'
            '<li><b>Agent turn.</b> The audit_retrieval fixture at each context size: cold prompt, identical, append, middle mutation and tool turn; '
            'T_turn = TTFT of the tool turn + 512 / decode tok/s. Three reps where the table says so. summarize_driver.py and the canonical groups of '
            'reports-2026-10.json.</li>'
            '<li><b>Terminal-Bench 2.1.</b> harbor on a MacBook against the rig, agent terminus-2, -n 1, agent timeout 1.0×, build 3.0×, context 262144.</li>'
            '<li><b>Claude Code.</b> claude -p 2.1.292, CLAUDE_CODE_EFFORT_LEVEL=xhigh, four coding tasks, two reps alone per task, request log by a proxy.</li>'
            '<li><b>Effort.</b> GPQA 50 + LCB 50 at low, medium and xhigh; Swift two rounds, base one round at medium and low.</li>'
            '<li><b>Sources.</b> bench/swift15-flashnext-2026-10 (A/B), bench/splash-longctx-2026-10 (Splash, 262K batteries, Terminal-Bench, probes), '
            'bench/flashnext-next-steps-2026-10 (effort, agent probes), bench/claude-code-concurrency-2026-11 (Claude Code), '
            'bench/engine-updates-2026-10/results/reports-2026-10.json (speed groups).</li>'
            '<li><b>What this page does not measure.</b> The base model\'s quality on Splash; the base model in agent tasks; more than one run per cell; '
            'the full GPQA and LiveCodeBench sets.</li></ul></details></section>')


PAGE_CSS = r"""
a{color:var(--accent)}
.mt{margin-top:12px}
.u{color:var(--muted); font-size:0.86em; margin-left:2px; font-weight:400}
.mono{font-family:var(--mono); font-size:0.9em}
.sw{display:inline-block; width:10px; height:10px; border-radius:2px; flex:none; vertical-align:middle}
.arm-lab{display:inline-flex; align-items:center; gap:6px; white-space:nowrap; font-weight:600; color:var(--ink); font-family:var(--sans); font-size:0.84rem}
.hero-lead{font-size:1.08rem; line-height:1.55; max-width:76ch; margin:18px 0 0; color:var(--ink)}
.tiles4{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,250px),1fr)); gap:12px}
.tile{background:var(--surface); border:1px solid var(--border); border-top:3px solid var(--c); border-radius:12px; padding:12px 14px}
.tile .t-lab{font-family:var(--mono); font-size:0.7rem; letter-spacing:0.08em; text-transform:uppercase; color:var(--ink-2); margin:0 0 8px; display:flex; gap:6px; align-items:center}
.t-row{display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:4px 0}
.t-row span{display:flex; flex-direction:column}
.t-row b{font-size:1.35rem; line-height:1.15; font-variant-numeric:tabular-nums; color:var(--ink)}
.t-row b .u{font-size:0.6em}
.t-row small{font-size:0.72rem; color:var(--muted)}
.tile .t-sub{font-size:0.78rem; color:var(--muted); margin:8px 0 0}
td.nm, th.nm{font-family:var(--sans); text-align:left; color:var(--ink-2); font-size:0.84rem}
table.cfg td, table.cfg th{text-align:left; font-family:var(--sans); font-size:0.84rem; vertical-align:top}
table.qual td, table.timet td, table.speedt td, table.heatt td{font-variant-numeric:tabular-nums}
th .arm-lab{font-size:0.76rem}
.sgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr)); gap:14px; margin-top:14px}
.cgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr)); gap:14px; margin-top:14px}
figure.strip, figure.card-chart{margin:0; background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:12px 12px 10px}
figure.card-chart{margin-top:14px} .cgrid figure.card-chart{margin:0}
.p-title, .c-head{margin:0; font-weight:700; font-size:0.92rem}
.c-note{margin:3px 0 0; font-size:0.8rem; color:var(--muted)}
svg.chart{width:100%; height:auto; display:block; margin-top:6px; overflow:visible}
.tick{font-size:12px; fill:var(--muted); font-family:var(--mono)}
.gl{stroke:var(--grid); stroke-width:1}
.ln{fill:none; stroke:var(--c); stroke-width:2; stroke-linejoin:round}
.mk{fill:var(--c); stroke:var(--surface); stroke-width:2}
.hit{fill:transparent; stroke:none; cursor:default}
.dl{font-family:var(--mono); font-size:12px; font-weight:700; fill:var(--ink); paint-order:stroke; stroke:var(--surface); stroke-width:3px}
.absent text{fill:var(--muted); font-size:16px; font-weight:700}
.rowlab{font-size:13px; font-weight:700; fill:var(--ink); font-family:var(--sans)}
.rowsub{font-size:11px; fill:var(--muted); font-family:var(--mono)}
.dot circle{fill:var(--c); stroke:var(--c); stroke-width:1.2; fill-opacity:0.7}
.dot.bad circle{fill:var(--surface); fill-opacity:1; stroke-width:1.6}
.dot.trunc circle{stroke-dasharray:2 1.5}
.med{stroke:var(--ink); stroke-width:2.5}
.medlab{font-family:var(--mono); font-size:12px; font-weight:700; fill:var(--ink); paint-order:stroke; stroke:var(--surface); stroke-width:3.5px}
.dotkey{display:inline-block; width:10px; height:10px; border-radius:50%; background:var(--ink-2); vertical-align:middle; margin:0 4px}
.dotkey.hollow{background:transparent; border:1.5px solid var(--ink-2)}
.medkey{display:inline-block; width:3px; height:12px; background:var(--ink); vertical-align:middle; margin:0 4px}
.legend .lg{margin-right:14px}
.bars{margin-top:8px} .bgroup{margin-top:10px}
.b-lab{margin:0 0 4px; font-size:0.82rem; color:var(--ink-2)}
/* Fixed label and value columns (set per chart by hbars), so the track (1fr) is the same width in every row of a chart. */
.bline{display:grid; grid-template-columns:var(--lw,150px) 1fr var(--vw,230px); gap:8px; align-items:center; margin:3px 0}
.bline .arm-lab{flex-wrap:wrap; white-space:normal; line-height:1.25}
.bline .arm-lab .u{white-space:nowrap}
.bline .arm-lab{font-size:0.78rem; font-weight:500}
.btrack{display:flex; height:12px; background:var(--surface-2); border-radius:0 4px 4px 0}
.bfill{display:block; height:100%; border-radius:0 4px 4px 0; min-width:2px}
.bv{font-family:var(--mono); font-size:0.78rem; text-align:right; color:var(--ink); line-height:1.3}
.empty{color:var(--muted); font-size:0.84rem}
td.heat{background:rgba(var(--accent-rgb),var(--a)); color:var(--ink)}
td.cov{font-family:var(--sans); font-size:0.82rem}
td.cov.yes{color:var(--ink)} td.cov.yes::before{content:"● "; color:var(--s3)}
td.cov.no{color:var(--muted)} td.cov.no::before{content:"○ "}
#tip{position:fixed; z-index:9; pointer-events:none; background:var(--ink); color:var(--plane); font-family:var(--mono); font-size:0.74rem;
  padding:6px 9px; border-radius:6px; max-width:320px; display:none; line-height:1.4}
details > summary{cursor:pointer; list-style:none}
details > summary::-webkit-details-marker{display:none}
details > summary h2.sec{display:inline}
details > summary h2.sec::after{content:" ▸"; color:var(--muted)}
details[open] > summary h2.sec::after{content:" ▾"}
@media (max-width:560px){.bline{grid-template-columns:min(var(--lw,150px),130px) 1fr min(var(--vw,230px),110px)} .t-row b{font-size:1.1rem}}
"""

TEMPLATE = r"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Flash-Next: base vs Swift 1.5, two engines</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="__DESC__">
<meta property="og:type" content="article">
<meta property="og:title" content="Qwen3.8-Flash-Next: base vs Swift 1.5 on mlx-serve and Splash">
<meta property="og:description" content="__DESC__">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>
/*__CSS__*/
</style>
<div class="wrap">
  <header>
    <div>
      <p class="eyebrow">Qwen3.8-Flash-Next · Apple M4 Max 128 GB · October–November 2026</p>
      <h1>Base vs Swift 1.5, on mlx-serve and on Splash</h1>
      <p class="sub">Two weights of the same model on two servers: the released Qwen3.8-Flash-Next and the Swift 1.5 fine-tune, each on mlx-serve (MLX packs) and on Splash (GGUF). Accuracy, time and tokens per answer, agent turn by context size, cache, memory, agent tasks, and what has not been measured yet.</p>
    </div>
    <button class="theme" id="themeBtn" type="button">theme: auto</button>
  </header>
  <p class="hero-lead">__LEAD__</p>
__TILES__
__GRID__
__ACCURACY__
__TIME__
__EFFORT__
__SPEED__
__CACHE__
__MEMORY__
__AGENT__
__LONGCTX__
__COVERAGE__
__METHOD__
  <footer id="foot">Data, scripts and per-question results: <a href="__REPO__">github.com/snagnever/macstudio-local-llm</a>. Generated <code>__GENERATED__</code>.</footer>
</div>
<div id="tip" role="tooltip"></div>
<script>
const root=document.documentElement;
const btn=document.getElementById("themeBtn");
function applyLabel(){ btn.textContent="theme: "+(root.getAttribute("data-theme")||"auto"); }
btn.addEventListener("click",()=>{
  const cur=root.getAttribute("data-theme");
  const next=cur==null?"light":cur==="light"?"dark":null;
  if(next) root.setAttribute("data-theme",next); else root.removeAttribute("data-theme");
  try{ next?localStorage.setItem("theme",next):localStorage.removeItem("theme"); }catch(e){}
  applyLabel();
});
try{ const saved=localStorage.getItem("theme"); if(saved) root.setAttribute("data-theme",saved); }catch(e){}
applyLabel();
const tip=document.getElementById("tip");
document.querySelectorAll("[data-tip]").forEach(el=>{
  el.addEventListener("mouseenter",()=>{ tip.textContent=el.dataset.tip; tip.style.display="block"; });
  el.addEventListener("mousemove",e=>{ const x=Math.min(e.clientX+14, window.innerWidth-330); tip.style.left=x+"px"; tip.style.top=(e.clientY+14)+"px"; });
  el.addEventListener("mouseleave",()=>{ tip.style.display="none"; });
});
</script>
"""


def lead(p: dict) -> str:
    q = p["quality"]
    bm, sm = q["mlx"]["t1"]["bm"], q["mlx"]["t1"]["sm"]
    r_gpqa = bm["gpqa"]["median_s"] / sm["gpqa"]["median_s"]
    r_tok = bm["gpqa"]["median_completion"] / sm["gpqa"]["median_completion"]
    s256 = {cid: next(s for s in p["speed"][cid] if s["ctx"] == 262144) for cid in CELL}
    ratio = s256["ss"]["t_turno_s"] / s256["sm"]["t_turno_s"]
    tb = p["tbench"]
    return (f"<b>The two models score the same; Swift 1.5 gets there with about a third of the tokens.</b> On GPQA-Diamond the base model "
            f"writes {r_tok:.1f}× the tokens and takes {r_gpqa:.1f}× the time per question for the same accuracy, on the same server. "
            f"<b>The engine moves the agent turn more than the model does:</b> at 256K Splash takes {ratio:.2f}× the mlx-serve turn with Swift, "
            f"and only Splash serves 1M. On Terminal-Bench 2.1, Swift passes {tb['sm']['passed']}/89 on mlx-serve and {tb['ss']['passed']}/89 on Splash. "
            + splash_base_lead(q["splash262"]))


def splash_base_lead(sp: dict) -> str:
    sa, sb = sp["ss"], sp["bs"]
    if not sb:
        return "The base model on Splash has speed and memory numbers in every band; its quality battery has not run yet, so those cells say so."
    fails = [s for s in SUITES if sb[s]["passed"] < sa[s]["passed"] - G1_MARGIN[s] and
             not (s == "humaneval" and sb[s].get("with_imports") and sa[s].get("with_imports")
                  and sb[s]["with_imports"] >= sa[s]["with_imports"] - G1_MARGIN[s])]
    t = sum(sb[s]["total_s"] for s in SUITES) / sum(sa[s]["total_s"] for s in SUITES)
    verdict = ("passes G1 against Swift in all six suites" if not fails else
               "fails G1 against Swift in " + ", ".join(f"{SUITE_LABEL[s].split(' (')[0]} ({sb[s]['passed']}/{sb[s]['n']} vs {sa[s]['passed']}/{sa[s]['n']})"
                         for s in fails))
    return (f"On Splash at 262K, in one run, the base model {verdict}, and its battery takes {t:.1f}× Swift's time.")


def render(p: dict) -> str:
    desc = ("Qwen3.8-Flash-Next base and the Swift 1.5 fine-tune on mlx-serve and on Splash, on an Apple M4 Max: accuracy, time and "
            "tokens per answer, agent turn by context size up to 1M, cache, memory and agent tasks.")
    parts = {"/*__CSS__*/": PERF_CSS + PERF_EXTRA_CSS + PAGE_CSS, "__DESC__": E(desc), "__LEAD__": lead(p),
             "__TILES__": tiles(p), "__GRID__": grid_section(), "__ACCURACY__": accuracy_section(p),
             "__TIME__": time_section(p), "__EFFORT__": effort_section(p), "__SPEED__": speed_section(p),
             "__CACHE__": cache_section(p), "__MEMORY__": memory_section(p), "__AGENT__": agent_section(p),
             "__LONGCTX__": longctx_section(p), "__COVERAGE__": coverage_section(p), "__METHOD__": method_section(p),
             "__REPO__": REPO_URL, "__GENERATED__": p["generated_at"]}
    html = TEMPLATE
    for k, v in parts.items():
        html = html.replace(k, v)
    return html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--json", type=Path, default=None, help="also write the collected payload")
    a = ap.parse_args(argv)
    p = collect()
    a.out.write_text(render(p), encoding="utf-8")
    if a.json:
        a.json.write_text(json.dumps(p, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
