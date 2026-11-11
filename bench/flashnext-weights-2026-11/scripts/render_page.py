#!/usr/bin/env python3
"""Render the Flash-Next GGUF weights campaign into reports/qwen38-flashnext-gguf-weights.html.

collect() reads results/ (speed test, battery W1 and W2, tool-call probe) and returns a plain dict; render() turns
that payload into a self-contained page in the layout of reports/qwen38-flashnext-swift15.html.

    python3 bench/flashnext-weights-2026-11/scripts/render_page.py

The battery numbers come from summarize_ab.py of the Swift 1.5 campaign (view, suite_stats and the LiveCodeBench
regrade), so they match results/w1/ab/*.md and results/w2/ab/*.md.
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import html as _html
import json
import math
import statistics
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[1]
BENCH = CAMPAIGN.parent
RESULTS = CAMPAIGN / "results"
OUT = BENCH.parent / "reports" / "qwen38-flashnext-gguf-weights.html"
JSON_OUT = RESULTS / "page-data.json"

sys.path.insert(0, str(BENCH / "swift15-flashnext-2026-10" / "scripts"))
sys.path.insert(0, str(BENCH / "qwen38-flashnext-daily-driver-2026-09" / "scripts"))
import summarize_ab as S  # noqa: E402
from render_perf_lines import CSS as PERF_CSS, EXTRA_CSS as PERF_EXTRA_CSS  # noqa: E402

BASE = "k2f"
ARMS = ("k2f", "k6f", "k1f", "k5f", "k8f", "k4f", "k3f")
W2_ARMS = ("k2f", "k6f")
RATIO_SUITES = ("gpqa", "livecodebench")
CANDIDATE_RATIO = 0.90
E2E_RATIO = 1.03
TOOL_PROFILES = ("fp0", "fp1")

# Pack metadata. size_gb is the Hugging Face file size of the variant: etapaW0-preparacao.md for the downloads,
# stack-updates-2026-10 (k2, 97.7 GB) and splash-longctx-2026-10 (k3, 58.4 GB) for the packs already on the rig.
PACKS = {
    "k2f": {"name": "Swift 1.5 IQ4_XS", "vendor": "UkisAI", "repo": "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF",
            "variant": "IQ4_XS", "rev": "0142554", "rev_full": "0142554c963a8653912c0c8283f05f13f63653f3",
            "size_gb": 97.7, "kind": "fine-tune"},
    "k6f": {"name": "Unsloth UD-IQ4_XS V3.1", "vendor": "Unsloth", "repo": "unsloth/Qwen3.8-Flash-Next-GGUF",
            "variant": "UD-IQ4_XS", "rev": "084c631", "size_gb": 93.7, "kind": "base"},
    "k1f": {"name": "Unsloth UD-IQ4_XS base", "vendor": "Unsloth", "repo": "unsloth/Qwen3.8-Flash-Next-GGUF",
            "variant": "UD-IQ4_XS", "rev": "766911a", "size_gb": 93.7, "kind": "base"},
    "k5f": {"name": "Unsloth UD-IQ3_XXS V3.1", "vendor": "Unsloth", "repo": "unsloth/Qwen3.8-Flash-Next-GGUF",
            "variant": "UD-IQ3_XXS", "rev": "084c631", "size_gb": 83.6, "kind": "base"},
    "k8f": {"name": "Swift 1.5 GSQ-RCO Q2_0", "vendor": "UkisAI",
            "repo": "ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF", "variant": "Q2_0", "rev": "99bb8f7",
            "size_gb": 66.6, "kind": "fine-tune"},
    "k4f": {"name": "ISTA GSQ-RCO Q2_0", "vendor": "ISTA-DASLab", "repo": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF",
            "variant": "Q2_0", "rev": "ed59f92", "size_gb": 66.4, "kind": "base"},
    "k3f": {"name": "ISTA GSQ-RCO-Coder IQ1_M", "vendor": "ISTA-DASLab",
            "repo": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF", "variant": "IQ1_M", "rev": "bba8885",
            "size_gb": 58.4, "kind": "Coder variant"},
}
NOT_LOADED = {"name": "BottleCap ThinkingCap IQ4_XS", "repo": "bottlecapai/ThinkingCap-Qwen3.8-Flash-Next-GGUF",
              "variant": "IQ4_XS", "rev": "2a053f7", "size_gb": 95.5,
              "error": "this GGUF stores tensors Splash cannot load: hc_attn_inject.weight IQ4_XS (48 tensors), "
                       "hc_ffn_inject.weight IQ4_XS (48 tensors)"}


def _half_up(x: float, nd: int = 1) -> float:
    """Round half up on the decimal text, so 116.55 GB prints as 116.6 like the campaign reports."""
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def speed_stats(path: Path) -> dict:
    """Speed test at 262144: decode p50 (tok/s), e2e p50 (s, thinking included), RAM peak and accuracy."""
    rows = _read_jsonl(path)
    dec = [r["decode_tps"] for r in rows if r.get("decode_tps") is not None]
    e2e = [r["e2e_ms"] for r in rows if r.get("e2e_ms") is not None]
    ram = [r["ram_peak_gb"] for r in rows if r.get("ram_peak_gb") is not None]
    swap = [r["swap_delta_gb"] for r in rows if r.get("swap_delta_gb") is not None]
    return {"n": len(rows), "correct": sum(r.get("correct") is True for r in rows),
            "decode_p50": _half_up(statistics.median(dec)) if dec else None,
            "decode_p50_raw": statistics.median(dec) if dec else None,
            "e2e_p50_s": _half_up(statistics.median(e2e) / 1000) if e2e else None,
            "ram_peak_gb": _half_up(max(ram)) if ram else None,
            "swap_delta_max_gb": max(swap) if swap else None,
            "model_id": rows[0].get("model_id") if rows else None,
            "model_revision": rows[0].get("model_revision") if rows else None,
            "runtime_revision": rows[0].get("runtime_revision") if rows else None,
            "context": rows[0].get("context_target") if rows else None}


def tool_score(path: Path) -> dict:
    """Sessions of the tool-call probe where every turn is correct: the tool turns and the final verdict.

    The JSONL has no verdict per session that covers the turns, so a session counts only when it has all the
    tool turns it requested and every record of it is correct.
    """
    sessions = collections.defaultdict(list)
    for r in _read_jsonl(path):
        sessions[r["session_id"]].append(r)
    clean = 0
    for recs in sessions.values():
        verdict = [r for r in recs if r.get("record_type") == "verdict"]
        turns = [r for r in recs if r.get("record_type") == "tool_turn"]
        if len(verdict) != 1 or len(turns) != verdict[0].get("turns_requested"):
            continue
        clean += all(r.get("correct") is True for r in recs)
    return {"sessions": len(sessions), "clean": clean}


def battery(path: Path) -> dict:
    loaded = S.load_arm(path)
    suites = {s: S.suite_stats(loaded[s]) for s in S.SUITES if s in loaded}
    return {"suites": suites, "total": sum(v["passed"] for v in suites.values()),
            "n": sum(v["n"] for v in suites.values()), "total_s": round(sum(v["total_s"] for v in suites.values()), 1)}


def _ratio(cand: dict, base: dict, key: str, suite: str):
    b, c = base["suites"][suite][key], cand["suites"][suite][key]
    return round(c / b, 2) if b and c is not None else None


def _g1_fail(cand: dict, base: dict) -> list[str]:
    return [s for s in S.SUITES if s in base["suites"] and s in cand["suites"]
            and cand["suites"][s]["passed"] < base["suites"][s]["passed"] - S.QUALITY_MARGIN[s]]


def collect(results_dir: Path = RESULTS) -> dict:
    results_dir = Path(results_dir)
    speed = {a: speed_stats(results_dir / f"{a}-262144-t1.0-w1.jsonl") for a in ARMS}
    toolcalls = {a: {p: tool_score(results_dir / "toolcall" / f"{a}-{p}-w1.jsonl") for p in TOOL_PROFILES}
                 for a in ARMS}
    w1 = {a: battery(results_dir / "w1" / "t1" / a) for a in ARMS}
    w2 = {a: battery(results_dir / "w2" / "t1" / f"{a}-r2") for a in W2_ARMS}
    base = w1[BASE]

    ratios = {a: {k: {s: _ratio(w1[a], base, col, s) for s in RATIO_SUITES}
                  for k, col in (("tokens", "median_completion"), ("time", "median_s"))} for a in ARMS}
    others = [ratios[a]["tokens"][s] for a in ARMS if a != BASE for s in RATIO_SUITES]

    tb = toolcalls[BASE]
    candidate = {}
    for a in ARMS:
        if a == BASE:
            continue
        g1 = _g1_fail(w1[a], base)
        tools_ok = all(toolcalls[a][p]["clean"] >= tb[p]["clean"] - 1 for p in TOOL_PROFILES)
        tokens_ok = all(ratios[a]["tokens"][s] <= CANDIDATE_RATIO for s in RATIO_SUITES)
        time_ok = all(ratios[a]["time"][s] <= CANDIDATE_RATIO for s in RATIO_SUITES)
        e2e_ratio = round(speed[a]["e2e_p50_s"] / speed[BASE]["e2e_p50_s"], 2)
        e2e_ok = e2e_ratio <= E2E_RATIO
        candidate[a] = {"g1_fail": g1, "tools_ok": tools_ok, "tokens_ok": tokens_ok, "time_ok": time_ok,
                        "e2e_ratio": e2e_ratio, "e2e_ok": e2e_ok,
                        "candidate": not g1 and tools_ok and (tokens_ok or time_ok) and e2e_ok}

    moves = {a: {s: w2[a]["suites"][s]["passed"] - w1[a]["suites"][s]["passed"] for s in w1[a]["suites"]}
             for a in W2_ARMS}
    noise = {
        "total_move": {a: w2[a]["total"] - w1[a]["total"] for a in W2_ARMS},
        "max_total_move": max(abs(w2[a]["total"] - w1[a]["total"]) for a in W2_ARMS),
        "suite_move": moves,
        "max_suite_move": max(abs(v) for m in moves.values() for v in m.values()),
        "k2f_token_ratio": {s: _ratio(w2[BASE], base, "median_completion", s) for s in RATIO_SUITES},
        "k6f_vs_k2f_w2": {s: _ratio(w2["k6f"], w2[BASE], "median_completion", s) for s in RATIO_SUITES},
        "g1_fail_w2": {"k2f W1 vs W2": _g1_fail(w2["k2f"], base), "k6f W1 vs W2": _g1_fail(w2["k6f"], w1["k6f"]),
                       "k6f W2 vs k2f W2": _g1_fail(w2["k6f"], w2[BASE])},
        "sum_two_passes": {a: w1[a]["total"] + w2[a]["total"] for a in W2_ARMS},
    }

    def pct(c, b):
        return round(100 * (c / b - 1))

    med = lambda a, s: w1[a]["suites"][s]["median_completion"]  # noqa: E731
    claims = {
        "v31_tokens_vs_base": {s: pct(med("k6f", s), med("k1f", s)) for s in RATIO_SUITES},
        "v31_decode_vs_base": pct(speed["k6f"]["decode_p50_raw"], speed["k1f"]["decode_p50_raw"]),
        "v31_accuracy": {"k6f_w1": w1["k6f"]["total"], "k6f_w2": w2["k6f"]["total"], "k1f": w1["k1f"]["total"]},
        "swift_tokens_vs_base": {s: pct(med(BASE, s), med("k1f", s)) for s in RATIO_SUITES},
    }
    return {"arms": list(ARMS), "base": BASE, "suites": list(S.SUITES), "quality_margin": dict(S.QUALITY_MARGIN),
            "candidate_ratio": CANDIDATE_RATIO, "e2e_ratio": E2E_RATIO, "packs": PACKS, "not_loaded": NOT_LOADED,
            "speed": speed, "toolcalls": toolcalls, "battery": {"w1": w1, "w2": w2}, "ratios": ratios,
            "token_spread": {"min": min(others), "max": max(others)}, "candidate": candidate, "noise": noise,
            "claims": claims}


# ---------------------------------------------------------------- render
#
# The page is written for readers outside this repo: pack names first, arm codes only as a small tag that ties a
# row to the files in results/.

SUITE_LABEL = {"humaneval": "HumanEval", "gpqa": "GPQA-Diamond", "livecodebench": "LiveCodeBench v6",
               "jdhodges": "Tool calling · jdhodges", "veerman": "Tool calling · Veerman",
               "if": "Instruction following"}
SUITE_SHORT = {"gpqa": "GPQA", "livecodebench": "LiveCodeBench"}
SUITE_SIZE = {"humaneval": 164, "gpqa": 50, "livecodebench": 50, "jdhodges": 40, "veerman": 12, "if": 20}
SERIES_COLOR = {"gpqa": "--s1", "livecodebench": "--s2"}
REPO = "https://github.com/snagnever/macstudio-local-llm"
CAMPAIGN_URL = REPO + "/tree/main/bench/flashnext-weights-2026-11"
SITE = "https://snagnever.github.io/macstudio-local-llm/"
PAGE_FILE = "qwen38-flashnext-gguf-weights.html"
SERVE_FLAGS = "--host 0.0.0.0 --port 8585 --max-context 262144 --idle-release off --no-webui"
BENCH_FLAGS = "--language-only --offline --verify-rows auto"


def E(v) -> str:
    return _html.escape("" if v is None else str(v), quote=True)


def ND(v, fmt="{}", unit="") -> str:
    if v is None:
        return '<span class="na">n/d</span>'
    return E(fmt.format(v)) + (f'<span class="u">{E(unit)}</span>' if unit else "")


def _x(v) -> str:
    return "n/d" if v is None else f"{v:.2f}×"


def _name(d: dict, a: str) -> str:
    return E(d["packs"][a]["name"])


def _tag(a: str) -> str:
    return f'<span class="tag">{E(a)}</span>'


def _hf(repo: str, rev: str) -> str:
    return (f'<a href="https://huggingface.co/{E(repo)}">{E(repo)}</a>'
            f'<span class="u">@{E(rev)}</span>')


def _tile(lab: str, big: str, sub: str) -> str:
    return f'<div class="tile"><p class="t-lab">{lab}</p><p class="t-big">{big}</p><p class="t-sub">{sub}</p></div>'


def _html_verdict(d: dict) -> str:
    b, sp, w1, w2, n = d["base"], d["speed"], d["battery"]["w1"], d["battery"]["w2"], d["noise"]
    lo, hi = d["token_spread"]["min"], d["token_spread"]["max"]
    totals = [w1[a]["total"] for a in d["arms"]]
    lead = (f"<b>The {_name(d, b)} pack stays the best GGUF for Splash.</b> No other pack meets the candidate rule: "
            f"a median token count or median time at least 10% below the Swift pack on both GPQA and LiveCodeBench, "
            f"quality within the per-suite margin, and tool calls no more than one session below. Every other pack "
            f"spends "
            f"<b>{lo:.2f}–{hi:.2f}×</b> the Swift median tokens on those two suites.")
    tiles = (
        _tile("Best GGUF for Splash", "Swift 1.5",
              f'{_name(d, b)} · {ND(sp[b]["decode_p50"], "{:.1f}")} tok/s decode · {ND(sp[b]["e2e_p50_s"], "{:.1f}")} s '
              f'turn · {w1[b]["total"]} and {w2[b]["total"]} of 336 in two passes')
        + _tile("Tokens of the other packs", f"{lo:.2f}–{hi:.2f}×",
                f"the Swift median on GPQA and LiveCodeBench. A candidate needs ≤ {d['candidate_ratio']:.2f}×.")
        + _tile("Quality noise", f"≤ {n['max_total_move']}",
                f"questions of 336 move between two passes of the same pack. The first-pass totals span "
                f"{min(totals)}–{max(totals)}.")
        + _tile("ThinkingCap", "did not load",
                "Splash 1.5.0 and 1.6.0 refuse its IQ4_XS <code>hc_*_inject</code> tensors.")
    )
    return (f'<section class="hero" id="verdict"><p class="hero-lead">{lead}</p><div class="tiles">{tiles}</div>'
            '</section>')


def _html_packs(d: dict) -> str:
    rows = ""
    for a in d["arms"]:
        p, sp, tc, bt = d["packs"][a], d["speed"][a], d["toolcalls"][a], d["battery"]["w1"][a]
        w2 = d["battery"]["w2"].get(a)
        bat = f'{bt["total"]}' + (f' <span class="u">· {w2["total"]} 2nd pass</span>' if w2 else "")
        rows += (f'<tr data-arm="{E(a)}"><td class="nm"><b>{E(p["name"])}</b> {_tag(a)}</td>'
                 f'<td class="nm repo">{_hf(p["repo"], p["rev"])}<span class="u"> · {E(p["variant"])}</span></td>'
                 f'<td>{ND(p["size_gb"], "{:.1f}")} / {ND(sp["ram_peak_gb"], "{:.1f}")}</td>'
                 f'<td>{ND(sp["decode_p50"], "{:.1f}")}</td><td>{ND(sp["e2e_p50_s"], "{:.1f}")}</td>'
                 f'<td>{bat}</td><td>{tc["fp0"]["clean"]} / {tc["fp1"]["clean"]}</td></tr>')
    nl = d["not_loaded"]
    rows += (f'<tr class="dim"><td class="nm"><b>{E(nl["name"])}</b></td>'
             f'<td class="nm repo">{_hf(nl["repo"], nl["rev"])}<span class="u"> · {E(nl["variant"])}</span></td>'
             f'<td>{ND(nl["size_gb"], "{:.1f}")} / –</td><td colspan="4" class="nm">did not load on Splash 1.5.0 or '
             '1.6.0</td></tr>')
    return ('<section class="block" id="packs"><h2 class="sec">Seven packs</h2>'
            '<p class="s-note">Every pack ran on Splash 1.5.0 with a 262,144-token context and '
            '<code>reasoning_effort: xhigh</code>. Decode and turn time are medians of the 13-request speed test at '
            '262,144 tokens. The turn time includes thinking, so it measures each pack, not only the engine. Tool '
            'calls count the sessions, of 20, where all 5 turns are correct.</p>'
            '<div class="tbl-scroll"><table class="packs"><thead><tr><th class="nm">Pack</th>'
            '<th class="nm">Hugging Face repo @ revision</th><th>Size / RAM peak, GB</th><th>Decode, tok/s</th>'
            '<th>Turn, s</th><th>Battery /336</th><th>Tool calls fp0 / fp1</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div></section>')


def _log_x(v: float, lo: float, hi: float, x0: float, x1: float) -> float:
    return x0 + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (x1 - x0)


def _tokens_chart(d: dict) -> str:
    arms = [a for a in d["arms"] if a != d["base"]]
    lo, hi = 0.3, 10.0
    W, x0, x1, top, gh, bh = 520, 8, 470, 30, 56, 13
    H = top + gh * len(arms) + 24
    X = lambda v: _log_x(v, lo, hi, x0, x1)  # noqa: E731
    k2 = d["noise"]["k2f_token_ratio"]
    nlo, nhi = min(k2.values()), max(k2.values())
    g = (f'<rect class="band" x="{X(nlo):.1f}" y="{top - 6}" width="{X(nhi) - X(nlo):.1f}" height="{H - top - 18}">'
         f'<title>Swift median, second pass ÷ first pass: {nlo:.2f}–{nhi:.2f}×</title></rect>')
    for v in (0.5, 1, 2, 5, 10):
        x = X(v)
        g += (f'<line class="gl" x1="{x:.1f}" y1="{top - 6}" x2="{x:.1f}" y2="{H - 18}"/>'
              f'<text class="tick" x="{x:.1f}" y="{H - 4}" text-anchor="middle">{v:g}×</text>')
    xc = X(d["candidate_ratio"])
    g += (f'<line class="cand" x1="{xc:.1f}" y1="{top - 10}" x2="{xc:.1f}" y2="{H - 18}"/>'
          f'<text class="candlab" x="{xc - 4:.1f}" y="{top - 14}" text-anchor="end">candidate ≤ '
          f'{d["candidate_ratio"]:.2f}</text>')
    xb = X(1.0)
    g += (f'<line class="base" x1="{xb:.1f}" y1="{top - 10}" x2="{xb:.1f}" y2="{H - 18}"/>'
          f'<text class="baselab" x="{xb + 4:.1f}" y="{top - 14}">Swift = 1</text>')
    for i, a in enumerate(arms):
        y = top + gh * i
        g += f'<text class="rowlab" x="{x0}" y="{y + 10}">{_name(d, a)}</text>'
        for j, s in enumerate(RATIO_SUITES):
            v = d["ratios"][a]["tokens"][s]
            yb = y + 16 + j * (bh + 3)
            if v is None:
                continue
            xv = X(min(max(v, lo), hi))
            g += (f'<rect class="tbar {s}" x="{xb:.1f}" y="{yb}" width="{max(xv - xb, 1.5):.1f}" height="{bh}" '
                  f'style="fill:var({SERIES_COLOR[s]})"><title>{_name(d, a)} · {SUITE_SHORT[s]} · {v:.2f}× the Swift '
                  f'median tokens</title></rect>'
                  f'<text class="vlab" x="{xv + 4:.1f}" y="{yb + bh - 2}">{v:.2f}</text>')
    return (f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Median tokens per pack, relative to '
            f'the Swift 1.5 IQ4_XS pack, log scale">{g}</svg>')


def _yes(ok: bool, yes="yes", no="no") -> str:
    return f'<span class="stchip pass">{yes}</span>' if ok else f'<span class="stchip fail">{no}</span>'


def _html_tokens(d: dict) -> str:
    legend = ('<div class="legend">'
              + "".join(f'<span class="chip"><span class="sw" style="background:var({SERIES_COLOR[s]});height:10px;'
                        f'width:14px"></span>{SUITE_SHORT[s]}</span>' for s in RATIO_SUITES)
              + '<span class="chip"><span class="sw bandkey"></span>Swift pass-to-pass range</span>'
              + '<span class="chip"><span class="candkey"></span>candidate line</span></div>')
    rows = ""
    tb = d["toolcalls"][d["base"]]
    for a in d["arms"]:
        if a == d["base"]:
            continue
        c, r, tc = d["candidate"][a], d["ratios"][a], d["toolcalls"][a]
        g1 = _yes(True, "within") if not c["g1_fail"] else _yes(
            False, no="outside: " + ", ".join(SUITE_SHORT.get(s, SUITE_LABEL[s]) for s in c["g1_fail"]))
        tcs = f'{tc["fp0"]["clean"]} / {tc["fp1"]["clean"]}'
        rows += (f'<tr data-arm="{E(a)}"><td class="nm">{_name(d, a)}</td><td class="nm">{g1}</td>'
                 f'<td>{_yes(c["tools_ok"], tcs, tcs)}</td>'
                 f'<td>{_x(r["tokens"]["gpqa"])} / {_x(r["tokens"]["livecodebench"])}</td>'
                 f'<td>{_x(r["time"]["gpqa"])} / {_x(r["time"]["livecodebench"])}</td>'
                 f'<td>{_x(c["e2e_ratio"])}</td><td>{_yes(c["candidate"])}</td></tr>')
    m = d["quality_margin"]
    table = ('<div class="tbl-scroll mt"><table class="cand-t"><thead><tr><th class="nm">Pack</th>'
             '<th class="nm">Quality vs Swift</th>'
             f'<th>Tool calls ≥ {tb["fp0"]["clean"] - 1} / {tb["fp1"]["clean"] - 1}</th>'
             '<th>Tokens GPQA / LCB</th><th>Time GPQA / LCB</th><th>Turn time</th><th>Candidate</th></tr></thead>'
             f'<tbody>{rows}</tbody></table></div>')
    return ('<section class="block" id="tokens"><h2 class="sec">Thinking cost against the Swift pack</h2>'
            '<p class="s-note">Median completion tokens per question, divided by the Swift 1.5 IQ4_XS median, first '
            'pass. Log scale. The bars start at the Swift median (1×). A pack must reach the dashed line on both '
            'suites, in tokens or in time, to be a candidate. No pack gets below 1×.</p>'
            + legend
            + '<figure class="card-chart">' + _tokens_chart(d) + '</figure>'
            + f'<p class="s-note mt"><b>Candidate rule, pack by pack.</b> Quality: every suite within the margin of '
              f'the Swift pack ({m["humaneval"]} questions on HumanEval, GPQA and LiveCodeBench, {m["jdhodges"]} on '
              f'jdhodges and instruction following, {m["veerman"]} on Veerman). Tool calls: no more than one session '
              f'below the Swift pack in each profile. Tokens or time: ≤ {d["candidate_ratio"]:.2f}× on both suites. '
              f'Turn time: ≤ {d["e2e_ratio"]:.2f}×. Ratios are pack ÷ Swift.</p>'
            + table + '</section>')


def _html_accuracy(d: dict) -> str:
    b, w1, m = d["base"], d["battery"]["w1"], d["quality_margin"]
    head = "".join(f'<th>{_name(d, a)}</th>' for a in d["arms"])
    rows = ""
    for s in d["suites"]:
        best = max(w1[a]["suites"][s]["passed"] for a in d["arms"])
        tds = ""
        for a in d["arms"]:
            v = w1[a]["suites"][s]["passed"]
            out = a != b and v < w1[b]["suites"][s]["passed"] - m[s]
            cls = " ".join(c for c in ("fail" if out else "", "best" if v == best else "") if c)
            mark = '<span class="fmark" title="outside the margin of the Swift pack">▼</span>' if out else ""
            tds += f'<td class="{cls}">{v}{mark}</td>'
        rows += (f'<tr data-suite="{s}"><td class="nm">{E(SUITE_LABEL[s])} <span class="u">/{SUITE_SIZE[s]} · '
                 f'margin {m[s]}</span></td>{tds}</tr>')
    tot_best = max(w1[a]["total"] for a in d["arms"])
    rows += ('<tr class="tot"><td class="nm"><b>Total</b> <span class="u">/336</span></td>'
             + "".join(f'<td class="{"best" if w1[a]["total"] == tot_best else ""}"><b>{w1[a]["total"]}</b></td>'
                       for a in d["arms"]) + '</tr>')
    return ('<section class="block" id="accuracy"><h2 class="sec">Accuracy per suite</h2>'
            '<p class="s-note">Correct answers, first pass. A truncated answer counts as wrong. ▼ marks a suite '
            'outside the margin of the Swift pack. Bold is the best score in the row. The first-pass totals span 10 '
            'questions, the same size as the pass-to-pass noise below, so only the GPQA drop of the IQ1_M pack '
            'stands out.</p>'
            f'<div class="tbl-scroll"><table class="acc"><thead><tr><th class="nm">Suite</th>{head}</tr></thead>'
            f'<tbody>{rows}</tbody></table></div></section>')


def _dot_plot(d: dict) -> str:
    w1, w2 = d["battery"]["w1"], d["battery"]["w2"]
    vals = [w1[a]["total"] for a in d["arms"]] + [w2[a]["total"] for a in w2]
    lo, hi = 5 * math.floor((min(vals) - 2) / 5), 5 * math.ceil((max(vals) + 2) / 5)
    W, x0, x1, top, rh = 520, 18, 500, 8, 34
    H = top + rh * len(d["arms"]) + 22
    X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)  # noqa: E731
    g = ""
    for v in range(lo, hi + 1, 5):
        g += (f'<line class="gl" x1="{X(v):.1f}" y1="{top}" x2="{X(v):.1f}" y2="{H - 18}"/>'
              f'<text class="tick" x="{X(v):.1f}" y="{H - 4}" text-anchor="middle">{v}</text>')
    for i, a in enumerate(d["arms"]):
        y = top + rh * i
        yc = y + 23
        g += f'<text class="rowlab" x="{x0}" y="{y + 10}">{_name(d, a)}</text>'
        v1 = w1[a]["total"]
        if a in w2:
            v2 = w2[a]["total"]
            g += f'<line class="link" x1="{X(v1):.1f}" y1="{yc}" x2="{X(v2):.1f}" y2="{yc}"/>'
            g += (f'<circle class="pt w2" cx="{X(v2):.1f}" cy="{yc}" r="5"><title>{_name(d, a)} · second pass · '
                  f'{v2}/336</title></circle><text class="vlab" x="{X(v2) + 8:.1f}" y="{yc + 4}">{v2}</text>')
        g += (f'<circle class="pt w1" cx="{X(v1):.1f}" cy="{yc}" r="5"><title>{_name(d, a)} · first pass · '
              f'{v1}/336</title></circle><text class="vlab" x="{X(v1) - 8:.1f}" y="{yc + 4}" '
              f'text-anchor="end">{v1}</text>')
    return (f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Battery total out of 336 per pack, '
            f'first and second pass">{g}</svg>')


def _html_noise(d: dict) -> str:
    w1, w2, n, b = d["battery"]["w1"], d["battery"]["w2"], d["noise"], d["base"]
    pair = list(w2)
    head = "".join(f'<th>{_name(d, a)} 1st</th><th>{_name(d, a)} 2nd</th>' for a in pair)
    rows = ""
    for s in d["suites"]:
        rows += (f'<tr data-suite="{s}"><td class="nm">{E(SUITE_LABEL[s])} <span class="u">/{SUITE_SIZE[s]}</span></td>'
                 + "".join(f'<td>{w1[a]["suites"][s]["passed"]}</td><td>{w2[a]["suites"][s]["passed"]}</td>'
                           for a in pair) + '</tr>')
    rows += ('<tr class="tot"><td class="nm"><b>Total</b> <span class="u">/336</span></td>'
             + "".join(f'<td><b>{w1[a]["total"]}</b></td><td><b>{w2[a]["total"]}</b></td>' for a in pair) + '</tr>')
    trows = ""
    for s in ("gpqa", "livecodebench", "humaneval"):
        trows += (f'<tr><td class="nm">{E(SUITE_LABEL[s])}</td>'
                  + "".join(f'<td>{w1[a]["suites"][s]["median_completion"]:,.0f}</td>'
                            f'<td>{w2[a]["suites"][s]["median_completion"]:,.0f}</td>' for a in pair) + '</tr>')
    k2 = n["k2f_token_ratio"]
    klo, khi = min(k2.values()), max(k2.values())
    kv = n["k6f_vs_k2f_w2"]
    legend = ('<div class="legend"><span class="chip"><span class="dotkey"></span> first pass</span>'
              '<span class="chip"><span class="dotkey hollow"></span> second pass</span></div>')
    lcb_min = min(d["ratios"][a]["tokens"]["livecodebench"] for a in d["arms"] if a != b)
    return ('<section class="block" id="noise"><h2 class="sec">Pass-to-pass noise</h2>'
            f'<p class="s-note">No pack met the rule, so the second pass repeated the battery on {_name(d, "k2f")} and '
            f'{_name(d, "k6f")}, in reverse order of packs and suites. The same pack moves up to '
            f'<b>{n["max_total_move"]} of 336</b> questions between passes, and up to {n["max_suite_move"]} on one '
            f'suite. Both packs went up, so part of the change may come from the day or the suite order. The second '
            f'pass does not separate these effects.</p>'
            + legend + '<figure class="card-chart">' + _dot_plot(d) + '</figure>'
            + '<div class="cgrid">'
            '<figure class="card-chart"><p class="c-head">Correct answers per pass</p>'
            f'<div class="tbl-scroll mt"><table class="acc"><thead><tr><th class="nm">Suite</th>{head}</tr></thead>'
            f'<tbody>{rows}</tbody></table></div></figure>'
            '<figure class="card-chart"><p class="c-head">Median tokens per pass</p>'
            f'<div class="tbl-scroll mt"><table class="acc"><thead><tr><th class="nm">Suite</th>{head}</tr></thead>'
            f'<tbody>{trows}</tbody></table></div>'
            f'<p class="c-note mt">The Swift median moves <b>{klo:.2f}–{khi:.2f}×</b> between passes on GPQA and '
            f'LiveCodeBench. The V3.1 pack still spends {kv["gpqa"]:.2f}× and {kv["livecodebench"]:.2f}× the Swift '
            f'median in the second pass. On LiveCodeBench every other pack is at {lcb_min:.2f}× or more, above '
            f'1/{klo:.2f} = {1 / klo:.2f}.</p></figure></div></section>')


def _html_claims(d: dict) -> str:
    c, sp = d["claims"], d["speed"]
    t, sw, acc = c["v31_tokens_vs_base"], c["swift_tokens_vs_base"], c["v31_accuracy"]

    def sgn(v):
        return f"{v:+d}%".replace("-", "−")

    rows = [
        ("Unsloth, V3.1 vs base", "up to 50% fewer tokens",
         f"{sgn(t['gpqa'])} on GPQA, {sgn(t['livecodebench'])} on LiveCodeBench (median tokens)", "not confirmed",
         "fail"),
        ("Unsloth, V3.1 vs base", "about 15% more accuracy",
         f"{acc['k6f_w1']} and {acc['k6f_w2']} of 336 in two passes, against {acc['k1f']}", "not confirmed", "fail"),
        ("Unsloth, V3.1 vs base", "up to 7% faster",
         f"decode {sgn(c['v31_decode_vs_base'])} ({sp['k6f']['decode_p50']:.1f} vs {sp['k1f']['decode_p50']:.1f} tok/s)",
         "confirmed", "pass"),
        ("UkisAI, Swift 1.5 vs base", "63.4% less thinking at the median",
         f"{sgn(sw['gpqa'])} tokens on GPQA, {sgn(sw['livecodebench'])} on LiveCodeBench", "partial", ""),
        ("BottleCap, ThinkingCap", "38.5% less thinking", "–", "not run", ""),
    ]
    trs = "".join(f'<tr><td class="nm">{E(v)}</td><td class="nm">{E(cl)}</td><td class="nm">{E(m)}</td>'
                  f'<td class="nm"><span class="stchip {cls}">{E(r)}</span></td></tr>' for v, cl, m, r, cls in rows)
    return ('<section class="block" id="claims"><h2 class="sec">Vendor claims against the measurements</h2>'
            '<p class="s-note">The claims come from the model cards. The measurements are first-pass medians on '
            'Splash 1.5.0. The base pack ran one pass, so the token comparisons are not a verdict, but neither pass '
            'of the V3.1 pack shows the reduction.</p>'
            '<div class="tbl-scroll"><table class="claims"><thead><tr><th class="nm">Vendor</th><th class="nm">Claim'
            '</th><th class="nm">Measured</th><th class="nm">Result</th></tr></thead>'
            f'<tbody>{trs}</tbody></table></div></section>')


def _html_method(d: dict) -> str:
    sizes = ", ".join(f"{SUITE_LABEL[s]} {SUITE_SIZE[s]}" for s in d["suites"])
    nl = d["not_loaded"]
    items = [
        "One rig: Mac Studio, Apple M4 Max, 128 GB. Every pack ran on Splash 1.5.0 with a 262,144-token context and "
        "the default flags. Splash 1.6.0 did not pass the switch rule of the Splash 1.6 campaign.",
        "Every request sends <code>reasoning_effort: xhigh</code>, temperature 1.0, top_p 0.95, top_k 20, min_p 0. "
        "Questions run one at a time.",
        f"Battery: {E(sizes)}, 336 in all. GPQA-Diamond and LiveCodeBench are 50-question samples (seed 42).",
        "One pass per pack, except the Swift 1.5 IQ4_XS and the Unsloth UD-IQ4_XS V3.1 packs, which ran twice. The "
        "differences between the other packs are not a verdict.",
        "Tool calls: the probe runs 20 sessions per profile. Each session is 4 tool-call turns and a final check. "
        "The score counts the sessions where all 5 are correct. <code>fp0</code> sends <code>frequency_penalty</code> "
        "0; <code>fp1</code> sends 1, as the Crush harness does. One run per pack. The ISTA Q2_0 pack ran 97 of "
        "100 turns in <code>fp0</code>.",
        "Turn time is the end-to-end p50 of the speed test: 13 requests at 262,144 tokens over 3 repetitions. It "
        "includes thinking. Decode p50 and the RAM peak come from the same requests. Swap did not grow on any pack.",
        "Pack size is the Hugging Face size of the variant.",
        f"ThinkingCap ({E(nl['repo'])}@{E(nl['rev'])}) failed at load on Splash 1.5.0 and 1.6.0: "
        f"<code>{E(nl['error'])}</code>.",
        "Agent quality (for example Terminal-Bench) is not measured.",
    ]
    lis = "".join(f"<li>{t}</li>" for t in items)
    return (f'<section class="block notice" id="method"><p><b>Method and limits</b></p><ul>{lis}</ul></section>')


def _html_commands(d: dict) -> str:
    p = d["packs"][d["base"]]
    dl = f'hf download {p["repo"]} --revision {p["rev_full"]} --include "{p["variant"]}/*"'
    serve = f'splash serve --model {p["repo"]}:{p["variant"]} --revision {p["rev_full"]} {SERVE_FLAGS}'
    return ('<section class="block" id="commands"><h2 class="sec">Commands</h2>'
            f'<p class="s-note">Download and serve the {E(p["name"])} pack at the revision this page measured. The '
            'repository is gated on Hugging Face.</p>'
            f'<pre class="cmd"><code>{E(dl)}\n{E(serve)}</code></pre>'
            f'<p class="s-note mt">The benchmark runs also passed <code>{E(BENCH_FLAGS)}</code>. Scripts, per-question '
            f'results and the test plan: <a href="{CAMPAIGN_URL}">github.com/snagnever/macstudio-local-llm</a>.</p>'
            '</section>')


PAGE_CSS = r"""
.mt{margin-top:12px}
.u{color:var(--muted); font-size:0.9em; margin-left:2px}
a{color:var(--accent)}
code{font-family:var(--mono); font-size:0.9em}
.hero-lead{font-size:1.08rem; line-height:1.55; max-width:76ch; margin:18px 0 0; color:var(--ink)}
.tiles{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,200px),1fr)); gap:12px; margin-top:20px}
.tile{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px}
.tile .t-lab{font-family:var(--mono); font-size:0.68rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); margin:0}
.tile .t-big{font-size:2rem; line-height:1.1; font-weight:700; margin:6px 0 4px; color:var(--ink); font-variant-numeric:tabular-nums}
.tile .t-sub{font-size:0.84rem; color:var(--ink-2); margin:0; line-height:1.4}
.tag{font-family:var(--mono); font-size:0.7rem; color:var(--muted); border:1px solid var(--border); border-radius:4px; padding:0 4px; margin-left:4px}
td.nm, th.nm{font-family:var(--sans); text-align:left; color:var(--ink-2); font-size:0.84rem}
td.nm b{color:var(--ink)}
td.repo{font-family:var(--mono); font-size:0.76rem; white-space:nowrap}
td.repo a{text-decoration:none} td.repo a:hover{text-decoration:underline}
table.packs{min-width:880px} table.acc{min-width:640px} table.cand-t{min-width:720px} table.claims{min-width:640px}
table.acc th{white-space:normal; min-width:72px; vertical-align:bottom}
tr.dim td{color:var(--muted)}
tr.tot td{border-top:1px solid var(--border)}
td.fail{color:var(--warn); font-weight:700}
td.best{font-weight:700; color:var(--ink)}
.fmark{font-size:0.7em; margin-left:3px}
figure.card-chart{margin:14px 0 0; background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:12px 14px}
.cgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr)); gap:14px; margin-top:14px}
.cgrid figure.card-chart{margin:0}
.c-head{margin:0; font-weight:700; font-size:0.92rem}
.c-note{margin:3px 0 0; font-size:0.8rem; color:var(--ink-2)}
svg.chart .tick{font-size:12px}
.rowlab{font-family:var(--sans); font-size:13px; font-weight:600; fill:var(--ink); paint-order:stroke; stroke:var(--surface); stroke-width:4px; stroke-linejoin:round}
.vlab{font-family:var(--mono); font-size:12px; fill:var(--ink)}
.gl{stroke:var(--grid); stroke-width:1}
.band{fill:var(--surface-2); stroke:none}
.cand{stroke:var(--warn); stroke-width:1.6; stroke-dasharray:5 4}
.candlab{font-family:var(--mono); font-size:11.5px; fill:var(--warn)}
.base{stroke:var(--ink); stroke-width:1.6}
.baselab{font-family:var(--mono); font-size:11.5px; fill:var(--ink-2)}
.tbar{rx:2}
.link{stroke:var(--baseline); stroke-width:2}
.pt.w1{fill:var(--s1); stroke:var(--s1); stroke-width:1.5}
.pt.w2{fill:var(--surface); stroke:var(--s1); stroke-width:2}
.dotkey{display:inline-block; width:10px; height:10px; border-radius:50%; background:var(--s1)}
.dotkey.hollow{background:transparent; border:2px solid var(--s1)}
.bandkey{display:inline-block; width:14px!important; height:10px!important; background:var(--surface-2); border:1px solid var(--baseline)}
.candkey{display:inline-block; width:14px; height:0; border-top:2px dashed var(--warn)}
.legend{margin-top:14px}
pre.cmd{background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:12px 14px; overflow-x:auto;
  font-family:var(--mono); font-size:0.8rem; line-height:1.6; color:var(--ink); margin:0; white-space:pre}
.notice ul li{line-height:1.45}
@media (max-width:520px){.tile .t-big{font-size:1.7rem} .wrap{padding:24px 16px 48px}}
"""

TEMPLATE = r"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Flash-Next GGUF weights</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="__DESC__">
<meta property="og:type" content="article">
<meta property="og:title" content="Qwen3.8-Flash-Next GGUF weights on Splash">
<meta property="og:description" content="__DESC__">
<meta property="og:url" content="__URL__">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>
/*__CSS__*/
</style>
<div class="wrap">
  <header>
    <div>
      <p class="eyebrow">Qwen3.8-Flash-Next · GGUF on Splash 1.5.0 · Apple M4 Max 128 GB · November 2026</p>
      <h1>Flash-Next GGUF weights: the Swift 1.5 IQ4_XS stays the best pack</h1>
      <p class="sub">Seven GGUF packs of the same model on the same Splash release: Swift 1.5 fine-tunes by UkisAI, Unsloth UD quants, and GSQ-RCO quants by ISTA-DASLab. Speed, a six-suite battery and a tool-call probe for each, and a second battery pass for two of them.</p>
    </div>
    <button class="theme" id="themeBtn" type="button">theme: auto</button>
  </header>
__VERDICT__
__PACKS__
__TOKENS__
__ACCURACY__
__NOISE__
__CLAIMS__
__METHOD__
__COMMANDS__
  <footer id="foot">Data, scripts and per-question results: <a href="__CAMPAIGN__">github.com/snagnever/macstudio-local-llm</a>. Generated <code>__GENERATED__</code>.</footer>
</div>
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
</script>
"""


def _description(d: dict) -> str:
    lo, hi = d["token_spread"]["min"], d["token_spread"]["max"]
    return (f"Seven GGUF packs of Qwen3.8-Flash-Next on Splash 1.5.0, Apple M4 Max. The Swift 1.5 IQ4_XS pack stays "
            f"the best: every other pack spends {lo:.2f}–{hi:.2f}× its median tokens on GPQA and LiveCodeBench, with "
            "quality within the pass-to-pass noise.")


def render(data: dict) -> str:
    parts = {
        "/*__CSS__*/": PERF_CSS + PERF_EXTRA_CSS + PAGE_CSS,
        "__DESC__": E(_description(data)), "__URL__": SITE + PAGE_FILE,
        "__VERDICT__": _html_verdict(data), "__PACKS__": _html_packs(data), "__TOKENS__": _html_tokens(data),
        "__ACCURACY__": _html_accuracy(data), "__NOISE__": _html_noise(data), "__CLAIMS__": _html_claims(data),
        "__METHOD__": _html_method(data), "__COMMANDS__": _html_commands(data), "__CAMPAIGN__": CAMPAIGN_URL,
        "__GENERATED__": E(data.get("generated_at", "")),
    }
    html = TEMPLATE
    for k, v in parts.items():
        html = html.replace(k, v)
    return html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=RESULTS)
    ap.add_argument("--data", type=Path, help="render from a saved page-data.json instead of the results")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--json-out", default=str(JSON_OUT), help="where to save the payload; empty = do not save")
    a = ap.parse_args(argv)
    if a.data:
        data = json.loads(a.data.read_text(encoding="utf-8"))
    else:
        data = collect(a.results)
        data["generated_at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    a.out.write_text(render(data), encoding="utf-8")
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
