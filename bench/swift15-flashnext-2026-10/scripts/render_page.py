#!/usr/bin/env python3
"""Render the Swift 1.5 × n2 findings into reports/qwen38-flashnext-swift15.html.

collect() reads the A/B battery (results/ab), the HumanEval regrade, the T_turno summary of this campaign and
the canonical speed groups of the October perf-lines data; render() turns that payload into a self-contained
page in the layout of reports/qwen38-flashnext-perf-lines.html.

    python3 bench/swift15-flashnext-2026-10/scripts/render_page.py

The link preview image (reports/qwen38-flashnext-swift15-og.png, 1200×630) is a screenshot of the top of the
page. It does not regenerate with the page: retake it when the headline numbers change, for example with
Chrome --headless=new --window-size=1200,630 --screenshot over a local http.server.
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
# The perf-lines page dropped the September reference (c1), and so does this table.
OTHER_SERIES = ("o1", "m1", "d1")
G3_RATIO = 1.03
FN_REPS = 3  # run-all.sh runs the T_turno probe of this campaign with --repeat 3
SOURCE_LABEL = {THIS_CAMPAIGN: "this campaign",
                "engine-updates-2026-10": "October campaign · engine-updates-2026-10",
                "qwen38-flashnext-daily-driver-2026-09": "September campaign · qwen38-flashnext-daily-driver-2026-09"}

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
            "raw_median_s": None, "median_completion": None, "mean_completion": None,
            "median_reasoning_chars": None, "median_tok_s": None, "median_reasoning_tokens": None,
            "median_visible_tokens": None, "total_completion": None, "sec_per_correct": None, "points": []}


def _arm_time(views: list[dict], rows: list[dict] | None = None) -> dict:
    st = S.suite_stats(views)
    st["missing"] = False
    # suite_stats rounds the median to 0.1 s; the G2 gate compares the unrounded medians, as summarize_ab does.
    st["raw_median_s"] = statistics.median(v["elapsed_s"] for v in views) if views else None
    toks = [v["completion_tokens"] for v in views if v["completion_tokens"] is not None]
    st["mean_completion"] = round(statistics.mean(toks)) if toks else None
    st["total_completion"] = sum(toks) if toks else None
    # The raw bench2 records carry tok_s (completion tokens / wall time) and the thinking/answer split; the
    # tool-calling and IF records do not, so these stay None there.
    rows = rows or []
    st["median_tok_s"] = _median([r.get("tok_s") for r in rows])
    st["median_reasoning_tokens"] = _median([r.get("reasoning_tokens") for r in rows])
    st["median_visible_tokens"] = _median([r.get("visible_tokens") for r in rows])
    passed = st["passed"]
    st["sec_per_correct"] = round(st["total_s"] / passed, 1) if passed else None
    st["points"] = [{"id": v["id"], "s": v["elapsed_s"], "ok": v["passed"], "trunc": v["truncated"],
                     "tok": v["completion_tokens"]} for v in views]
    return st


def _paired(base: list[dict] | None, cand: list[dict] | None) -> dict | None:
    """How many questions the candidate (w1) answered in less wall time than the base (n2)."""
    if not base or not cand:
        return None
    by_id = {v["id"]: v for v in cand}
    pairs = [(v, by_id[v["id"]]) for v in base if v["id"] in by_id]
    return {"n": len(pairs), "faster": sum(c["elapsed_s"] < b["elapsed_s"] for b, c in pairs)}


def _difficulty(rows: list[dict]) -> dict:
    out = {}
    for level in ("easy", "medium", "hard"):
        xs = [r for r in rows if r.get("lcb_difficulty") == level]
        if xs:
            out[level] = {"n": len(xs), "median_s": _median([r.get("elapsed_s") for r in xs]),
                          "passed": sum(S._true(r.get("correct")) and r.get("finish_reason") != "length" for r in xs)}
    return out


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
           "decode_tps": None, "prefill_tps": None, "mtp_acceptance": None, "wired_peak_gb": None, "gates_failed": [], "config": "", "reps": None}
    if src is None:
        return row
    ttft = src.get("warm_ttft_s") or src.get("ttft_s") or {}
    row.update({"t_turno_s": src.get("t_turno_s"), "ttft_tool_turn_s": ttft.get("tool_turn"),
                "hit_tool_turn": (src.get("hit") or {}).get("tool_turn"), "cold_ttft_s": src.get("cold_ttft_s"),
                "decode_tps": src.get("decode_tps"), "prefill_tps": src.get("prefill_tps"),
                "mtp_acceptance": src.get("mtp_acceptance"), "wired_peak_gb": src.get("wired_peak_gb"),
                "gates_failed": list(src.get("gates_failed") or []), "config": src.get("config") or "",
                "reps": src.get("reps", FN_REPS if source == THIS_CAMPAIGN else None)})
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
    def g2_cell(cell):
        b, c = cell["arms"]["n2"]["raw_median_s"], cell["arms"]["w1"]["raw_median_s"]
        return {"ratio": cell["ratio"], "pass": None if not b or c is None else c <= S.TIME_RATIO * b}

    g2 = {s: {p: g2_cell(time[p][s]) for p in PROFILES} for s in S.TIME_SUITES}
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
    quality, time, tool_latency, difficulty = {}, {}, {}, {}
    for p in PROFILES:
        loaded = {a: S.load_arm(results_dir / "ab" / p / a) for a in ARMS}
        raw = {a: {s: _read_jsonl(f) if (f := results_dir / "ab" / p / a / f"{s}.jsonl").is_file() else []
                   for s in S.SUITES if s not in S.TOOL_SUITES} for a in ARMS}
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
                    arms[a] = _arm_time(views, raw[a].get(suite))
            b, c = arms["n2"]["raw_median_s"], arms["w1"]["raw_median_s"]
            time[p][suite] = {"arms": arms, "ratio": round(c / b, 2) if b and c else None,
                              "paired": _paired(loaded["n2"].get(suite), loaded["w1"].get(suite))}
        difficulty[p] = {a: _difficulty(raw[a].get("livecodebench", [])) for a in ARMS}
        tool_latency[p] = {s: {a: _tool_latency(results_dir / "ab" / p / a / f"{s}.jsonl") for a in ARMS}
                           for s in S.SUITES if s in S.TOOL_SUITES}
    regrade_path = results_dir / "humaneval-regrade.json"
    regrade = json.loads(regrade_path.read_text(encoding="utf-8")) if regrade_path.is_file() else {}
    regrade = {k: {"n": v.get("n"), "strict": v.get("strict"), "with_imports": v.get("with_imports"),
                   "truncated": len(v.get("truncated") or [])} for k, v in regrade.items()}
    speed = _speed(results_dir, reports)
    return {"arms": list(ARMS), "profiles": list(PROFILES), "suites": list(S.SUITES), "stacks": STACKS,
            "rig": reports.get("rig", []), "quality": quality, "humaneval_regrade": regrade, "time": time,
            "tool_latency": tool_latency, "lcb_difficulty": difficulty, "speed": speed, "legacy": LEGACY,
            "gates": _gates(quality, regrade, time, speed)}


# ---------------------------------------------------------------- render
#
# The page is written for readers outside this repo (it is shared on Reddit): model names instead of arm codes,
# no gates or runbook vocabulary, the time-per-task comparison first and the detail below it.

import datetime as _dt  # noqa: E402
import html as _html  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402

# The page shares the perf-lines stylesheet, so the Flash-Next pages keep one look.
sys.path.insert(0, str(CAMPAIGN.parent / "qwen38-flashnext-daily-driver-2026-09" / "scripts"))
from render_perf_lines import CSS as PERF_CSS, EXTRA_CSS as PERF_EXTRA_CSS  # noqa: E402

# Blue/orange passes the colorblind check in both themes; the earlier blue/purple pair did not (deutan ΔE 0.8).
ARM_COLOR = {"n2": "--s1", "w1": "--s2"}
ARM_NAME = {"n2": "iQ-MLX", "w1": "Swift 1.5"}
REASONING_SUITES = ("gpqa", "livecodebench", "humaneval")
SHORT_SUITES = ("jdhodges", "veerman", "if")
SUITE_LABEL = {
    "humaneval": "HumanEval",
    "gpqa": "GPQA-Diamond",
    "livecodebench": "LiveCodeBench v6",
    "jdhodges": "Tool calling · jdhodges",
    "veerman": "Tool calling · Veerman",
    "if": "Instruction following",
}
SUITE_SIZE = {
    "humaneval": "164 problems",
    "gpqa": "50 questions, seed 42",
    "livecodebench": "50 problems, seed 42",
    "jdhodges": "40 cases",
    "veerman": "12 cases",
    "if": "20 IFEval-style cases",
}
SWITCH_LABEL = {"t1": "Recommended · temp 1.0", "t0": "Greedy · temp 0"}
PROFILE_LONG = {
    "t1": "recommended sampling: temperature 1.0, top_p 0.95, top_k 20, min_p 0, presence 0, repetition 1.0",
    "t0": "greedy decoding: temperature 0",
}
SERVER_FLAGS = ("--ctx-size 131072 --mtp --ssm-checkpoint-max 16 --prefix-cache-mem 16GB "
                "--prefix-cache-disk 100GB --prefix-cache-entries 64")
MAX_TOKENS = "HumanEval 32,768 · GPQA and LiveCodeBench 65,536 · tool calling 32,768 · instruction following 16,384"
REPO = "https://github.com/snagnever/macstudio-local-llm"
CAMPAIGN_URL = REPO + "/tree/main/bench/swift15-flashnext-2026-10"
SITE = "https://snagnever.github.io/macstudio-local-llm/"
PAGE_FILE = "qwen38-flashnext-swift15.html"
OG_IMAGE = "qwen38-flashnext-swift15-og.png"
RIG_DROP = {"Wired limit", "Ports"}
LIMITS = [
    "One run per model and sampling setting. GPQA-Diamond and LiveCodeBench are 50-question samples (seed 42), "
    "not the full sets, so a difference of 2–3 questions is within run-to-run noise.",
    "Times are medians per question. A few answers on both sides run to the <code>max_tokens</code> limit and "
    "dominate the totals, so the totals improve less than the medians. The page shows both.",
    "The two packs share the same quantization layout but ship different n-gram tables, so this compares the two "
    "packs as published, not only the fine-tuned weights.",
    "Tool calling: the runner did not record the thinking text. A median of __TOOLTOKENS__ tokens per answer "
    "suggests little or no thinking in these suites.",
    "Instruction following is a 20-case IFEval-style probe. It does not reproduce the IFBench score of the "
    "Swift 1.5 model card.",
    "Agent quality (for example Terminal-Bench) is not measured.",
]


def E(v) -> str:
    return _html.escape("" if v is None else str(v), quote=True)


def ND(v, fmt="{}", unit="") -> str:
    if v is None:
        return '<span class="na">n/d</span>'
    return E(fmt.format(v)) + (f'<span class="u">{E(unit)}</span>' if unit else "")


def _sw(arm: str) -> str:
    return f'<span class="sw" style="background:var({ARM_COLOR[arm]})"></span>'


def _arm_lab(arm: str) -> str:
    return f'<span class="arm-lab">{_sw(arm)}{E(ARM_NAME[arm])}</span>'


def _legend(extra: str = "") -> str:
    return f'<div class="legend">{"".join(f"<span class=chip>{_arm_lab(a)}</span>" for a in ARMS)}{extra}</div>'


def _speedup(cell: dict):
    """n2 median / w1 median, from the unrounded medians: > 1 means Swift 1.5 is faster."""
    b, c = cell["arms"]["n2"]["raw_median_s"], cell["arms"]["w1"]["raw_median_s"]
    return b / c if b and c else None


def _speed_words(x, suffix: str = "") -> str:
    if x is None:
        return "n/d"
    if round(x, 1) == 1.0 or round(1 / x, 1) == 1.0:
        return "about the same" + suffix
    return f"{x:.1f}× faster{suffix}" if x > 1 else f"{1 / x:.1f}× slower{suffix}"


def _accuracy_spread(d: dict):
    cells = [c[p] for c in d["gates"]["g1"].values() for p in PROFILES]
    diffs = [abs(c["w1"] - c["n2"]) for c in cells if c["w1"] is not None and c["n2"] is not None]
    return max(diffs) if diffs else None


def _html_hero(d: dict) -> str:
    t1, t0 = d["time"]["t1"], d["time"]["t0"]
    xg, xl = _speedup(t1["gpqa"]), _speedup(t1["livecodebench"])
    g = t1["gpqa"]["arms"]
    tok_n, tok_w = g["n2"]["median_completion"], g["w1"]["median_completion"]
    rate_n, rate_w = g["n2"]["median_tok_s"], g["w1"]["median_tok_s"]
    spread = _accuracy_spread(d)
    rate = (f" Both generate at the same speed ({rate_n:.0f} vs {rate_w:.0f} tokens/s on GPQA)."
            if rate_n and rate_w else "")
    lead = (f"On an Apple M4 Max, Swift 1.5 gets to the final answer <b>{_speed_words(xg)}</b> on GPQA-Diamond and "
            f"<b>{_speed_words(xl)}</b> on LiveCodeBench (median per question), with the same accuracy.{rate} "
            "The gain comes from shorter thinking, not from faster generation.")
    cut = None if not tok_n or tok_w is None else round(100 * (1 - tok_w / tok_n))

    def tile(lab, big, sub):
        return f'<div class="tile"><p class="t-lab">{lab}</p><p class="t-big">{big}</p><p class="t-sub">{sub}</p></div>'

    def time_tile(s, x):
        a = t1[s]["arms"]
        big = "n/d" if x is None else f"{x:.1f}×" if x >= 1 else f"{1 / x:.1f}× slower"
        return tile(E(SUITE_LABEL[s]), big,
                    f'faster to the final answer · median {ND(a["n2"]["median_s"], "{:.1f}")} s → '
                    f'{ND(a["w1"]["median_s"], "{:.1f}")} s')

    tiles = (time_tile("gpqa", xg) + time_tile("livecodebench", xl)
             + tile("Thinking per answer", "n/d" if cut is None else f"−{cut}%",
                    f"GPQA median {ND(tok_n, '{:,.0f}')} → {ND(tok_w, '{:,.0f}')} tokens")
             + tile("Accuracy", "n/d" if spread is None else f"≤ {spread}",
                    "questions apart on every suite, in both directions"))
    greedy = (f"Tiles use the recommended sampling (temperature 1.0). With greedy decoding the gain is smaller: "
              f"{_speed_words(_speedup(t0['gpqa']))} on GPQA-Diamond and "
              f"{_speed_words(_speedup(t0['livecodebench']))} on LiveCodeBench.")
    return (f'<section class="hero" id="tldr"><p class="hero-lead">{lead}</p>'
            f'<div class="tiles">{tiles}</div><p class="s-note mt">{E(greedy)}</p></section>')


def _html_switch() -> str:
    btns = "".join(f'<button type="button" data-set-profile="{p}" aria-pressed="{"true" if p == "t1" else "false"}" '
                   f'title="{E(PROFILE_LONG[p])}">{E(SWITCH_LABEL[p])}</button>' for p in PROFILES)
    return (f'<div class="switch" id="profile-switch" role="group" aria-label="Sampling setting">'
            f'<span class="sw-lab">Sampling for the charts below</span>{btns}</div>')


def _log_ticks(lo: float, hi: float) -> list[float]:
    out = []
    for e in range(-1, 5):
        for m in (1, 2, 5):
            v = m * 10 ** e
            if lo <= v <= hi:
                out.append(v)
    return out


def _faster_bar(cell: dict) -> str:
    pr = cell.get("paired")
    if not pr or not pr["n"]:
        return ""
    k, n = pr["faster"], pr["n"]
    seg = lambda a, m, what: (f'<span class="fseg" style="flex:{m};background:var({ARM_COLOR[a]})" '  # noqa: E731
                              f'title="{E(ARM_NAME[a])} {what} on {m} of {n}"></span>' if m else "")
    return (f'<div class="faster"><div class="ftrack">{seg("w1", k, "faster")}{seg("n2", n - k, "faster or tied")}'
            f'</div><p class="flab"><b>Swift 1.5 faster on {k} of {n}</b> · iQ-MLX faster or tied on {n - k}</p></div>')


def _strip(p: str, s: str, cell: dict, paired: bool = True) -> str:
    arms = cell["arms"]
    pts = [x["s"] for a in ARMS for x in arms[a]["points"] if x["s"] and x["s"] > 0]
    title = f'<p class="p-title">{E(SUITE_LABEL[s])} <span class="p-size">{E(SUITE_SIZE[s])}</span></p>'
    if not pts:
        return (f'<figure class="strip" data-profile="{p}" data-suite="{s}">{title}'
                '<p class="empty">n/d: no records for this suite.</p></figure>')
    lo, hi = min(pts) / 1.25, max(pts) * 1.25
    W, H, x0, x1, lane = 440, 132, 70, 430, 46
    lx = lambda v: x0 + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (x1 - x0)  # noqa: E731
    g = ""
    for v in _log_ticks(lo, hi):
        x = lx(v)
        g += (f'<line class="gl" x1="{x:.1f}" y1="8" x2="{x:.1f}" y2="{H - 20}"/>'
              f'<text class="tick" x="{x:.1f}" y="{H - 6}" text-anchor="middle">{v:g}s</text>')
    for i, a in enumerate(ARMS):
        yc = 14 + lane * i + lane / 2
        g += f'<text class="axis-t" x="2" y="{yc + 4:.1f}">{E(ARM_NAME[a])}</text>'
        st = arms[a]
        if st["missing"]:
            g += f'<text class="tick" x="{x0}" y="{yc + 3:.1f}">n/d</text>'
            continue
        for j, x in enumerate(st["points"]):
            if not x["s"] or x["s"] <= 0:
                continue
            cx, cy = lx(x["s"]), yc + ((j * 37) % 17 - 8) * 1.6
            tok = f" · {x['tok']:,} tokens" if x.get("tok") else ""
            tip = (f"{ARM_NAME[a]} · question {x['id']} · {x['s']:.1f} s{tok} · "
                   f"{'correct' if x['ok'] else 'wrong'}" + (" · hit the max_tokens limit" if x["trunc"] else ""))
            if x["trunc"]:
                # A truncated answer is a cross, so the reader sees it without relying on a ring color.
                g += (f'<g class="dot {a} trunc" style="--c:var({ARM_COLOR[a]})"><title>{E(tip)}</title>'
                      f'<path d="M{cx - 4:.1f} {cy - 4:.1f}L{cx + 4:.1f} {cy + 4:.1f}M{cx - 4:.1f} {cy + 4:.1f}'
                      f'L{cx + 4:.1f} {cy - 4:.1f}"/></g>')
                continue
            cls = f"dot {a} {'ok' if x['ok'] else 'bad'}"
            g += (f'<circle class="{cls}" cx="{cx:.1f}" cy="{cy:.1f}" r="3.6" '
                  f'style="--c:var({ARM_COLOR[a]})"><title>{E(tip)}</title></circle>')
        if st["median_s"]:
            mx = lx(st["median_s"])
            g += (f'<line class="med" x1="{mx:.1f}" y1="{yc - 17:.1f}" x2="{mx:.1f}" y2="{yc + 17:.1f}"/>'
                  f'<text class="medlab" x="{mx + 4:.1f}" y="{yc - 11:.1f}">{st["median_s"]:.1f}s</text>')
    words = _speed_words(_speedup(cell))
    head = f'<span class="p-unit"><b>{E(words)}</b> (median)</span>' if words != "n/d" else ""
    return (f'<figure class="strip" data-profile="{p}" data-suite="{s}"><div class="p-head">{title}{head}</div>'
            f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{E(SUITE_LABEL[s])}, time per question">'
            f'{g}</svg>{_faster_bar(cell) if paired else ""}</figure>')


DOT_LEGEND = ('<span class="chip"><span class="dotkey"></span> correct</span>'
              '<span class="chip"><span class="dotkey hollow"></span> wrong</span>'
              '<span class="chip"><span class="crosskey">×</span> hit the max_tokens limit</span>'
              '<span class="chip"><span class="medkey"></span> median</span>')


def _bars(groups: list, fmt: str, unit: str = "", notes: dict | None = None) -> str:
    """Paired horizontal bars on one zero-based scale. groups: [(key, label, {arm: value})]."""
    vals = [v for _, _, vs in groups for v in vs.values() if v is not None]
    mx = max(vals) if vals else 1
    out = ""
    for key, label, vs in groups:
        lines = ""
        for a in ARMS:
            v = vs.get(a)
            note = (notes or {}).get((key, a))
            if v is None:
                lines += f'<div class="bline">{_arm_lab(a)}<span class="btrack"></span><span class="bv">{ND(None)}</span></div>'
                continue
            txt = fmt.format(v) + unit
            tip = f"{ARM_NAME[a]} · {label} · {txt}" + (f" · {note}" if note else "")
            lines += (f'<div class="bline">{_arm_lab(a)}<span class="btrack"><span class="bfill" '
                      f'style="width:{100.0 * v / mx:.1f}%;background:var({ARM_COLOR[a]})" title="{E(tip)}"></span>'
                      f'</span><span class="bv">{E(txt)}{f" <span class=u>{E(note)}</span>" if note else ""}</span></div>')
        out += f'<div class="bgroup" data-key="{E(key)}"><p class="b-lab">{E(label)}</p>{lines}</div>'
    return f'<div class="bars">{out}</div>'


def _chart(cid: str, title: str, note: str, body: str) -> str:
    return (f'<figure class="card-chart" id="{cid}"><p class="c-head">{E(title)}</p>'
            f'{f"<p class=c-note>{note}</p>" if note else ""}{body}</figure>')


def _per_profile(build) -> str:
    return "".join(f'<div class="prof prof-{p}">{build(p)}</div>' for p in PROFILES)


def _html_time(d: dict) -> str:
    def build(p):
        T = d["time"][p]
        figs = "".join(_strip(p, s, T[s]) for s in REASONING_SUITES)
        total = _bars([(s, SUITE_LABEL[s], {a: None if T[s]["arms"][a]["total_s"] is None
                                            else T[s]["arms"][a]["total_s"] / 60 for a in ARMS})
                       for s in REASONING_SUITES], "{:.0f}", " min")
        return (_legend(DOT_LEGEND) + f'<div class="sgrid">{figs}</div>'
                + _chart(f"total-time-{p}", "Total time to run the suite",
                         "Sum of the wall time of every question, one question at a time.", total))
    return ('<section class="block" id="time-per-task"><h2 class="sec">Time per task</h2>'
            '<p class="s-note">One dot per question: wall time from the request to the final answer, log scale. '
            'Hover a dot for the question, the time and the token count. The bar under each chart counts the '
            'questions each model finished first.</p>' + _per_profile(build) + '</section>')


def _html_why(d: dict) -> str:
    def build(p):
        T = d["time"][p]
        toks = _bars([(s, SUITE_LABEL[s], {a: T[s]["arms"][a]["median_completion"] for a in ARMS})
                      for s in REASONING_SUITES], "{:,.0f}", " tokens")
        rate = _bars([(s, SUITE_LABEL[s], {a: T[s]["arms"][a]["median_tok_s"] for a in ARMS})
                      for s in REASONING_SUITES], "{:.1f}", " tok/s")
        g = T["gpqa"]["arms"]
        tot = ""
        if g["n2"]["total_completion"] and g["w1"]["total_completion"]:
            tot = (f"Medians. The total token count on GPQA-Diamond drops less, from "
                   f"{g['n2']['total_completion'] / 1000:,.0f}k to {g['w1']['total_completion'] / 1000:,.0f}k tokens, "
                   f"because a few answers on both sides run to the max_tokens limit "
                   f"({g['n2']['truncated']} for iQ-MLX, {g['w1']['truncated']} for Swift 1.5).")
        return (_legend() + '<div class="cgrid">'
                + _chart(f"tokens-{p}", "Tokens per answer (median)", "Thinking plus the visible answer.", toks)
                + _chart(f"rate-{p}", "Generation speed (median)",
                         "Output tokens divided by the wall time of each answer.", rate)
                + f'</div><p class="s-note mt">{E(tot)}</p>')
    return ('<section class="block" id="why"><h2 class="sec">Why it is faster</h2>'
            '<p class="s-note">Same runtime, same flags, same generation speed. Swift 1.5 writes fewer thinking '
            'tokens before it answers.</p>' + _per_profile(build) + '</section>')


def _html_accuracy(d: dict) -> str:
    q, rg = d["quality"], d["humaneval_regrade"]

    def cell_val(p, a, s):
        c = q[p][a][s]
        passed = (rg.get(f"{a}-{p}") or {}).get("with_imports", c["passed"]) if s == "humaneval" else c["passed"]
        return passed, c["n"]

    def build(p):
        rows = ""
        for s in d["suites"]:
            vals = {a: cell_val(p, a, s) for a in ARMS}
            tds = ""
            for a in ARMS:
                v, n = vals[a]
                tds += f"<td>{ND(v)}<span class=\"u\">/{n}</span></td>" if v is not None else f"<td>{ND(None)}</td>"
            dv = None if vals["w1"][0] is None or vals["n2"][0] is None else vals["w1"][0] - vals["n2"][0]
            diff = ND(None) if dv is None else ("0" if dv == 0 else f"{dv:+d}".replace("-", "−"))
            rows += (f'<tr data-suite="{s}"><td class="nm">{E(SUITE_LABEL[s])} <span class="u">{E(SUITE_SIZE[s])}</span>'
                     f'</td>{tds}<td>{diff}</td></tr>')
        strict = [(rg.get(f"{a}-{p}") or {}).get("strict") for a in ARMS]
        foot = ""
        if None not in strict:
            foot = (f'<p class="s-note mt">HumanEval is graded with the imports of the prompt added, because a correct '
                    f'answer that omits <code>from typing import List</code> fails the strict grader. Strict grade: '
                    f'{strict[0]} (iQ-MLX) vs {strict[1]} (Swift 1.5).</p>')
        return ('<div class="tbl-scroll"><table class="qual"><thead><tr><th class="nm">Suite</th>'
                f'<th>{_arm_lab("n2")}</th><th>{_arm_lab("w1")}</th><th>Swift − iQ</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>{foot}')
    return ('<section class="block" id="accuracy"><h2 class="sec">Accuracy</h2>'
            '<p class="s-note">Correct answers per suite. A truncated answer counts as wrong.</p>'
            + _per_profile(build) + '</section>')


def _html_detail(d: dict) -> str:
    def build(p):
        T = d["time"][p]
        spc = _bars([(s, SUITE_LABEL[s], {a: T[s]["arms"][a]["sec_per_correct"] for a in ARMS})
                     for s in REASONING_SUITES], "{:.0f}", " s")
        diff = d["lcb_difficulty"][p]
        levels = [lv for lv in ("easy", "medium", "hard") if any(lv in diff[a] for a in ARMS)]
        notes = {(lv, a): f"{diff[a][lv]['passed']}/{diff[a][lv]['n']} solved" for lv in levels for a in ARMS
                 if lv in diff[a]}
        n_of = {lv: next(diff[a][lv]["n"] for a in ARMS if lv in diff[a]) for lv in levels}
        lcb = _bars([(lv, f"{lv} · {n_of[lv]} problems", {a: (diff[a].get(lv) or {}).get("median_s") for a in ARMS})
                     for lv in levels], "{:.1f}", " s", notes)
        split = ""
        for s in ("livecodebench", "humaneval"):
            lines = ""
            parts = {a: (T[s]["arms"][a]["median_reasoning_tokens"], T[s]["arms"][a]["median_visible_tokens"])
                     for a in ARMS}
            mx = max((r or 0) + (v or 0) for r, v in parts.values()) or 1
            for a in ARMS:
                r, v = parts[a]
                if r is None or v is None:
                    lines += f'<div class="bline">{_arm_lab(a)}<span class="btrack"></span><span class="bv">{ND(None)}</span></div>'
                    continue
                lines += (f'<div class="bline">{_arm_lab(a)}<span class="btrack stack" style="width:{100.0 * (r + v) / mx:.1f}%">'
                          f'<span class="bfill" style="flex:{r};background:var({ARM_COLOR[a]})" '
                          f'title="{E(ARM_NAME[a])} · thinking {r:,.0f} tokens"></span>'
                          f'<span class="bfill answer" style="flex:{v};background:var({ARM_COLOR[a]})" '
                          f'title="{E(ARM_NAME[a])} · answer {v:,.0f} tokens"></span></span>'
                          f'<span class="bv">{r:,.0f} + {v:,.0f}</span></div>')
            split += f'<div class="bgroup"><p class="b-lab">{E(SUITE_LABEL[s])}</p>{lines}</div>'
        split = f'<div class="bars">{split}</div>'
        return (_legend() + '<div class="cgrid">'
                + _chart(f"per-correct-{p}", "Seconds per correct answer",
                         "Total suite time divided by the number of correct answers.", spc)
                + _chart(f"lcb-difficulty-{p}", "LiveCodeBench by difficulty (median time)",
                         "The gain grows with the difficulty of the problem.", lcb)
                + _chart(f"split-{p}", "Thinking + answer tokens (median of each part)",
                         "Solid: thinking. Light: the visible answer. Only the thinking shrinks.", split)
                + '</div>')
    return ('<section class="block" id="detail"><h2 class="sec">More detail</h2>'
            + _per_profile(build) + '</section>')


def _html_short(d: dict) -> str:
    def build(p):
        figs = "".join(_strip(p, s, d["time"][p][s], paired=False) for s in SHORT_SUITES)
        return _legend(DOT_LEGEND) + f'<div class="sgrid">{figs}</div>'
    return ('<section class="block" id="short-tasks"><h2 class="sec">Short tasks: about the same</h2>'
            '<p class="s-note">Tool calling and instruction following need little thinking, and both models answer '
            'in 2–3 seconds. For tool calling, the time adds the turn that writes the call and, for the multi-turn '
            'cases, the turn that reads the tool result.</p>' + _per_profile(build) + '</section>')


def _html_agent_turn(d: dict) -> str:
    rows = ""
    for c in CONTEXTS:
        r = {x["arm"]: x for x in d["speed"][c]}
        n, w = r.get("n2") or {}, r.get("w1") or {}
        rows += (f'<tr><td class="nm">{int(c) // 1024}K tokens</td>'
                 f'<td>{ND(n.get("t_turno_s"), "{:.1f}")}</td><td>{ND(w.get("t_turno_s"), "{:.1f}")}</td>'
                 f'<td>{ND(n.get("decode_tps"), "{:.1f}")}</td><td>{ND(w.get("decode_tps"), "{:.1f}")}</td>'
                 f'<td>{ND(n.get("prefill_tps"), "{:.0f}")}</td><td>{ND(w.get("prefill_tps"), "{:.0f}")}</td></tr>')
    two = f'<th>{_arm_lab("n2")}</th><th>{_arm_lab("w1")}</th>'
    devs = []
    for c in CONTEXTS:
        r = {x["arm"]: x for x in d["speed"][c]}
        n, w = (r.get("n2") or {}).get("t_turno_s"), (r.get("w1") or {}).get("t_turno_s")
        if n and w:
            devs.append(abs(w / n - 1))
    within = f" The two packs are within {math.ceil(100 * max(devs))}% of each other." if devs else ""
    return ('<section class="block" id="agent-turn"><h2 class="sec">Agent turn at long context</h2>'
            '<p class="s-note">One coding-agent turn on a long conversation: the time to the first token of a turn '
            'that carries a tool result, plus 512 generated tokens. Prefix cache on, median of 3 repetitions, '
            f'recommended sampling.{within}</p>'
            '<div class="tbl-scroll"><table class="speedt"><thead>'
            '<tr><th class="nm" rowspan="2">Context</th><th colspan="2">Turn time, s</th>'
            '<th colspan="2">Decode, tok/s</th><th colspan="2">Prefill, tok/s</th></tr>'
            f'<tr>{two}{two}{two}</tr></thead><tbody>{rows}</tbody></table></div></section>')


def _html_numbers(d: dict) -> str:
    def build(p):
        rows = ""
        for s in d["suites"]:
            A = d["time"][p][s]["arms"]

            def two(f):
                return "".join(f"<td>{f(A[a])}</td>" for a in ARMS)
            rows += (f'<tr data-suite="{s}"><td class="nm">{E(SUITE_LABEL[s])}</td>'
                     + two(lambda x: ND(x["median_s"], "{:.1f}"))
                     + two(lambda x: ND(None if x["total_s"] is None else x["total_s"] / 60, "{:.0f}"))
                     + two(lambda x: ND(x["median_completion"], "{:,.0f}"))
                     + two(lambda x: ND(x["truncated"])) + "</tr>")
        two = f'<th>{_arm_lab("n2")}</th><th>{_arm_lab("w1")}</th>'
        return ('<div class="tbl-scroll"><table class="timet"><thead><tr><th class="nm" rowspan="2">Suite</th>'
                '<th colspan="2">Median time, s</th><th colspan="2">Total time, min</th>'
                '<th colspan="2">Median tokens</th><th colspan="2">Hit max_tokens</th></tr>'
                f'<tr>{two * 4}</tr></thead><tbody>{rows}</tbody></table></div>')
    return ('<section class="block" id="numbers"><h2 class="sec">All numbers</h2>'
            + _per_profile(build) + '</section>')


def _html_setup(d: dict) -> str:
    rig = "".join(f'<div class="r-item"><p class="r-lab">{E(r["lab"])}</p><p class="r-val">{E(r["val"])}</p></div>'
                  for r in d["rig"] if r["lab"] not in RIG_DROP)
    models = ""
    for a in ARMS:
        s = d["stacks"][a]
        models += (f'<tr><td>{_arm_lab(a)}</td><td class="nm"><a href="https://huggingface.co/{E(s["weights"])}">'
                   f'{E(s["weights"])}</a> <span class="u">rev {E(s["rev"])}</span></td></tr>')
    return ('<section class="block" id="setup"><details><summary><h2 class="sec">Setup and how to reproduce</h2>'
            '</summary>'
            f'<div class="rig" id="rig">{rig}</div>'
            '<p class="s-note mt">Two 4.7-bit MLX packs of Qwen3.8-Flash-Next on the same mlx-serve 26.10.1 binary '
            'with the same flags. Only the weights change.</p>'
            '<div class="tbl-scroll"><table class="cfg"><thead><tr><th>Model</th><th class="nm">Weights '
            f'(Hugging Face)</th></tr></thead><tbody>{models}</tbody></table></div>'
            f'<p class="s-note mt">Server flags: <code>{E(SERVER_FLAGS)}</code>. Every request sends '
            '<code>reasoning_effort: xhigh</code>; without it, mlx-serve answers with no thinking. '
            f'{E(PROFILE_LONG["t1"]).capitalize()}; {E(PROFILE_LONG["t0"])}. <code>max_tokens</code>: {E(MAX_TOKENS)}. '
            'Questions run one at a time.</p>'
            f'<p class="s-note">Scripts, per-question results and the test plan: <a href="{CAMPAIGN_URL}">'
            'github.com/snagnever/macstudio-local-llm</a>.</p></details></section>')


def _html_limits(d: dict) -> str:
    toks = [d["time"][p][s]["arms"][a]["median_completion"] for p in PROFILES for s in S.TOOL_SUITES
            for a in ARMS if d["time"][p][s]["arms"][a]["median_completion"] is not None]
    rng = "n/d" if not toks else f"{min(toks):.0f}" if min(toks) == max(toks) else f"{min(toks):.0f}–{max(toks):.0f}"
    lis = "".join(f"<li>{t.replace('__TOOLTOKENS__', rng)}</li>" for t in LIMITS)
    return f'<section class="block notice" id="limits"><p><b>Limits</b></p><ul>{lis}</ul></section>'


PAGE_CSS = r"""
html[data-profile="t1"] .prof-t0, html[data-profile="t0"] .prof-t1{display:none}
.mt{margin-top:12px}
.u{color:var(--muted); font-size:0.9em; margin-left:2px}
a{color:var(--accent)}
.hero-lead{font-size:1.08rem; line-height:1.55; max-width:72ch; margin:18px 0 0; color:var(--ink)}
.tiles{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,150px),1fr)); gap:12px; margin-top:20px}
.tile{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px}
.tile .t-lab{font-family:var(--mono); font-size:0.68rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); margin:0}
.tile .t-big{font-size:2.2rem; line-height:1.1; font-weight:700; margin:6px 0 4px; color:var(--ink); font-variant-numeric:tabular-nums}
.tile .t-sub{font-size:0.84rem; color:var(--ink-2); margin:0; line-height:1.4}
.switch{position:sticky; top:0; z-index:4; display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top:30px;
  padding:10px 12px; background:var(--plane); border:1px solid var(--border); border-radius:10px}
.switch .sw-lab{font-family:var(--mono); font-size:0.66rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); margin-right:4px}
.switch button{white-space:nowrap; font-family:var(--mono); font-size:0.74rem; color:var(--ink-2); background:var(--surface);
  border:1px solid var(--border); border-radius:7px; padding:7px 11px; cursor:pointer}
.switch button[aria-pressed="true"]{border-color:var(--accent); color:var(--ink); box-shadow:inset 0 0 0 1px var(--accent)}
.switch button:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
.arm-lab{display:inline-flex; align-items:center; gap:6px; white-space:nowrap; font-weight:600; color:var(--ink)}
td.nm, th.nm{font-family:var(--sans); text-align:left; color:var(--ink-2); font-size:0.84rem}
table.cfg td, table.cfg th{text-align:left; font-family:var(--sans); font-size:0.84rem}
table.qual td, table.timet td, table.speedt td{font-variant-numeric:tabular-nums}
.sgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr)); gap:14px; margin-top:14px}
figure.strip{margin:0; background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:12px 12px 10px}
figure.strip .p-title{margin:0} .p-size{color:var(--muted); font-weight:400; font-size:0.84em}
figure.strip .empty{color:var(--muted); font-size:0.84rem}
.strip .tick{font-size:12px} .strip .axis-t{font-size:13px; font-weight:700; fill:var(--ink)}
.gl{stroke:var(--grid); stroke-width:1}
.dot{fill:var(--c); stroke:var(--c); stroke-width:1.2; fill-opacity:0.72}
.dot.bad{fill:var(--surface); fill-opacity:1; stroke-width:1.6}
g.dot.trunc path{stroke:var(--c); stroke-width:2.4; fill:none; stroke-linecap:round}
.med{stroke:var(--ink); stroke-width:2.5}
.medlab{font-family:var(--mono); font-size:12px; font-weight:700; fill:var(--ink); paint-order:stroke; stroke:var(--surface); stroke-width:3.5px; stroke-linejoin:round}
.dotkey{display:inline-block; width:10px; height:10px; border-radius:50%; background:var(--ink-2)}
.dotkey.hollow{background:transparent; border:1.5px solid var(--ink-2)}
.crosskey{font-weight:700; color:var(--ink-2); line-height:1}
.medkey{display:inline-block; width:3px; height:12px; background:var(--ink)}
.legend{margin-top:14px}
.faster{margin-top:8px}
.ftrack{display:flex; gap:2px; height:10px}
.fseg{display:block; height:100%}
.fseg:first-child{border-radius:4px 0 0 4px} .fseg:last-child{border-radius:0 4px 4px 0} .fseg:only-child{border-radius:4px}
.flab{margin:5px 0 0; font-size:0.82rem; color:var(--ink-2)}
.cgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr)); gap:14px; margin-top:14px}
figure.card-chart{margin:14px 0 0; background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:12px 14px}
.cgrid figure.card-chart{margin:0}
.c-head{margin:0; font-weight:700; font-size:0.92rem}
.c-note{margin:3px 0 0; font-size:0.8rem; color:var(--muted)}
.bars{margin-top:8px}
.bgroup{margin-top:10px}
.b-lab{margin:0 0 4px; font-size:0.82rem; color:var(--ink-2)}
.bline{display:grid; grid-template-columns:86px 1fr minmax(84px,auto); gap:8px; align-items:center; margin:2px 0}
.bline .arm-lab{font-size:0.8rem; font-weight:500}
.btrack{display:flex; gap:2px; height:12px}
.bfill{display:block; height:100%; border-radius:0 4px 4px 0; min-width:2px}
.btrack.stack .bfill{border-radius:0}
.btrack.stack .bfill:last-child{border-radius:0 4px 4px 0}
.bfill.answer{opacity:0.45}
.bv{font-family:var(--mono); font-size:0.78rem; text-align:right; color:var(--ink); white-space:nowrap}
details > summary{cursor:pointer; list-style:none}
details > summary::-webkit-details-marker{display:none}
details > summary h2.sec{display:inline}
details > summary h2.sec::after{content:" ▸"; color:var(--muted)}
details[open] > summary h2.sec::after{content:" ▾"}
@media (max-width:520px){.bline{grid-template-columns:72px 1fr minmax(70px,auto)} .tile .t-big{font-size:1.8rem}
  .switch{padding:8px; gap:6px} .switch .sw-lab{display:none} .switch button{padding:6px 8px; font-size:0.7rem}}
"""

TEMPLATE = r"""<!doctype html>
<html lang="en" data-profile="t1">
<meta charset="utf-8">
<title>Swift 1.5 vs iQ-MLX</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="__DESC__">
<meta property="og:type" content="article">
<meta property="og:title" content="Qwen3.8-Flash-Next: Swift 1.5 vs iQ-MLX on an M4 Max">
<meta property="og:description" content="__DESC__">
<meta property="og:url" content="__URL__">
<meta property="og:image" content="__OGIMG__">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>
/*__CSS__*/
</style>
<div class="wrap">
  <header>
    <div>
      <p class="eyebrow">Qwen3.8-Flash-Next · Apple M4 Max 128 GB · mlx-serve 26.10.1 · October 2026</p>
      <h1>Swift 1.5 vs iQ-MLX: same accuracy, less waiting</h1>
      <p class="sub">Two 4.7-bit MLX packs of the same model on the same runtime: the iQ-MLX pack by ddalcu and the Swift 1.5 fine-tune by Dankpaws. Six suites, two sampling settings, one dot per question.</p>
    </div>
    <button class="theme" id="themeBtn" type="button">theme: auto</button>
  </header>
__HERO__
__SWITCH__
__TIME__
__WHY__
__ACCURACY__
__DETAIL__
__SHORT__
__AGENT__
__NUMBERS__
__SETUP__
__LIMITS__
  <footer id="foot">Data, scripts and per-question results: <a href="__CAMPAIGN__">github.com/snagnever/macstudio-local-llm</a>. Generated <code>__GENERATED__</code>.</footer>
</div>
<script>
const root=document.documentElement;
function setProfile(p){
  root.setAttribute("data-profile",p);
  document.querySelectorAll("[data-set-profile]").forEach(b=>b.setAttribute("aria-pressed", b.dataset.setProfile===p?"true":"false"));
  try{ localStorage.setItem("swift15-profile",p); }catch(e){}
}
document.querySelectorAll("[data-set-profile]").forEach(b=>b.addEventListener("click",()=>setProfile(b.dataset.setProfile)));
try{ const p=localStorage.getItem("swift15-profile"); if(p==="t0"||p==="t1") setProfile(p); }catch(e){}
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
</script>
"""


def _description(d: dict) -> str:
    t1 = d["time"]["t1"]
    return (f"Same accuracy; with the recommended sampling, Swift 1.5 reaches the final answer "
            f"{_speed_words(_speedup(t1['gpqa']))} on GPQA-Diamond and {_speed_words(_speedup(t1['livecodebench']))} "
            "on LiveCodeBench than the iQ-MLX pack of Qwen3.8-Flash-Next, at the same generation speed, on an "
            "Apple M4 Max.")


def render(data: dict) -> str:
    parts = {
        "/*__CSS__*/": PERF_CSS + PERF_EXTRA_CSS + PAGE_CSS,
        "__DESC__": E(_description(data)), "__URL__": SITE + PAGE_FILE, "__OGIMG__": SITE + OG_IMAGE,
        "__HERO__": _html_hero(data), "__SWITCH__": _html_switch(), "__TIME__": _html_time(data),
        "__WHY__": _html_why(data), "__ACCURACY__": _html_accuracy(data), "__DETAIL__": _html_detail(data),
        "__SHORT__": _html_short(data), "__AGENT__": _html_agent_turn(data), "__NUMBERS__": _html_numbers(data),
        "__SETUP__": _html_setup(data), "__LIMITS__": _html_limits(data), "__CAMPAIGN__": CAMPAIGN_URL,
        "__GENERATED__": E(data.get("generated_at", "")),
    }
    html = TEMPLATE
    for k, v in parts.items():
        html = html.replace(k, v)
    return html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=RESULTS)
    ap.add_argument("--reports", type=Path, default=REPORTS_JSON)
    ap.add_argument("--data", type=Path, help="render from a saved page-data.json instead of the results")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--json-out", default=str(JSON_OUT), help="where to save the payload; empty = do not save")
    a = ap.parse_args(argv)
    if a.data:
        data = json.loads(a.data.read_text(encoding="utf-8"))
    else:
        data = collect(a.results, a.reports)
        data["generated_at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    a.out.write_text(render(data), encoding="utf-8")
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
