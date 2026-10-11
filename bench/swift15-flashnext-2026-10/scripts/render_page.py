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
            "median_reasoning_chars": None, "points": []}


def _arm_time(views: list[dict]) -> dict:
    st = S.suite_stats(views)
    st["missing"] = False
    # suite_stats rounds the median to 0.1 s; the G2 gate compares the unrounded medians, as summarize_ab does.
    st["raw_median_s"] = statistics.median(v["elapsed_s"] for v in views) if views else None
    toks = [v["completion_tokens"] for v in views if v["completion_tokens"] is not None]
    st["mean_completion"] = round(statistics.mean(toks)) if toks else None
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
            b, c = arms["n2"]["raw_median_s"], arms["w1"]["raw_median_s"]
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


# ---------------------------------------------------------------- render

import datetime as _dt  # noqa: E402
import html as _html  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402

# The page shares the perf-lines stylesheet, so the two Flash-Next pages keep one look.
sys.path.insert(0, str(CAMPAIGN.parent / "qwen38-flashnext-daily-driver-2026-09" / "scripts"))
from render_perf_lines import CSS as PERF_CSS, EXTRA_CSS as PERF_EXTRA_CSS  # noqa: E402

PERF_LINES = "qwen38-flashnext-perf-lines.html"
ARM_COLOR = {"n2": "--s1", "w1": "--s6", "o1": "--s3", "m1": "--s5", "d1": "--s4", "c1": "--s2"}
SUITE_LABEL = {
    "humaneval": "HumanEval · 164",
    "gpqa": "GPQA-Diamond · 50 (seed 42)",
    "livecodebench": "LiveCodeBench v6 · 50 (seed 42)",
    "jdhodges": "Tool calls · jdhodges 40",
    "veerman": "Tool calls · Veerman 12",
    "if": "Instruction following · 20 (IFEval-style)",
}
PROFILE_LABEL = {
    "t1": "t1 · vendor sampling (temperature 1.0, top_p 0.95, top_k 20, min_p 0, presence 0, repetition 1.0)",
    "t0": "t0 · greedy (temperature 0)",
}
SWITCH_LABEL = {"t1": "t1 · vendor sampling", "t0": "t0 · greedy"}
SERVER_FLAGS = ("--ctx-size 131072 --mtp --ssm-checkpoint-max 16 --prefix-cache-mem 16GB "
                "--prefix-cache-disk 100GB --prefix-cache-entries 64 --metrics")
LIMITS = [
    "One run per arm and profile. GPQA and LiveCodeBench use 50-question samples (seed 42), not the full sets.",
    "The IF probe is an IFEval-style check with 20 cases. It does not reproduce the IFBench score of the Swift 1.5 card.",
    "Tool calls (jdhodges, Veerman): the runner sent <code>reasoning_effort</code> and the sampling, but did not "
    "record the reasoning text in this campaign (n/d in the tables). A median of __TOOLTOKENS__ tokens per answer "
    "(by arm, suite and profile) suggests little or no thinking in these two suites.",
    "The two packs have the same layout, but their n-gram tables differ (different LFS hashes): the A/B compares "
    "the packs, not only the fine-tune.",
    "t1 and t0 of each arm ran in different server starts; the battery paused twice for 512K runs of another "
    "campaign (at profile boundaries, no data lost).",
    "Speed rows other than n2 and w1 (o1, m1 and d1) come from earlier sessions of the October campaign. There n2 "
    "measured within about 2% of its value here, which bounds the drift between sessions.",
    "Agent quality (Terminal-Bench 2.0) is not measured for either arm.",
]


def E(v) -> str:
    return _html.escape("" if v is None else str(v), quote=True)


def ND(v, fmt="{}", unit="") -> str:
    if v is None:
        return '<span class="na">n/d</span>'
    return E(fmt.format(v)) + (f'<span class="u">{E(unit)}</span>' if unit else "")


def _sw(arm: str) -> str:
    series = "m1" if arm.startswith("m1") else arm
    return f'<span class="sw" style="background:var({ARM_COLOR.get(series, "--muted")})"></span>'


def _arm_cell(arm: str) -> str:
    return f'<span class="arm-cell">{_sw(arm)}<span class="code">{E(arm)}</span></span>'


def _html_verdict(d: dict) -> str:
    g, t1, t0 = d["gates"], d["time"]["t1"], d["time"]["t0"]
    dec = g["decision"]
    head = {True: "Swift 1.5 (w1) passes the three gates and is promoted to Flash-Next daily driver.",
            False: "Swift 1.5 (w1) fails at least one gate and is not promoted.",
            None: "The decision is open: at least one gate has no data."}[dec["promote"]]
    sp = {c: {r["arm"]: r for r in d["speed"][c]} for c in CONTEXTS}

    def med(s, a):
        return t1[s]["arms"][a]["median_s"]

    def status(ok):
        return {True: "passes", False: "fails", None: "has no data"}[ok]

    items = []
    if dec["g1_t1"] and dec["g1_t0"]:
        spread = max(abs(c[p]["w1"] - c[p]["n2"]) for c in g["g1"].values() for p in PROFILES)
        items.append(("Same quality", "Every suite stays inside its G1 margin in both sampling profiles. Per-suite "
                                      f"differences are 0–{spread} questions on the gated grades, within one-run noise."))
    else:
        items.append(("Quality", f"G1 {status(dec['g1_t1'])} in t1 and {status(dec['g1_t0'])} in t0; see Gates."))
    items.append(("Time to the final answer",
                  f"With the vendor sampling (t1), the median per question goes from {ND(med('gpqa', 'n2'), '{:.1f}')} s "
                  f"to {ND(med('gpqa', 'w1'), '{:.1f}')} s on GPQA ({ND(t1['gpqa']['ratio'], '{:.2f}')}×) and from "
                  f"{ND(med('livecodebench', 'n2'), '{:.1f}')} s to {ND(med('livecodebench', 'w1'), '{:.1f}')} s on "
                  f"LiveCodeBench ({ND(t1['livecodebench']['ratio'], '{:.2f}')}×). Greedy (t0): "
                  f"{ND(t0['gpqa']['ratio'], '{:.2f}')}× and {ND(t0['livecodebench']['ratio'], '{:.2f}')}×."))
    if dec["g3"]:
        w, n = sp["131072"]["w1"], sp["131072"]["n2"]
        items.append(("Same agent-turn speed",
                      f"T_turn {ND(sp['32768']['w1']['t_turno_s'], '{:.1f}')} s vs "
                      f"{ND(sp['32768']['n2']['t_turno_s'], '{:.1f}')} s at 32K and {ND(w['t_turno_s'], '{:.1f}')} s vs "
                      f"{ND(n['t_turno_s'], '{:.1f}')} s at 128K, on the same runtime and prefix cache; "
                      f"decode {ND(w['decode_tps'], '{:.1f}')} vs {ND(n['decode_tps'], '{:.1f}')} tok/s at 128K."))
    else:
        items.append(("Agent-turn speed", f"G3 {status(dec['g3'])}; see Gates."))
    items.append(("Still open", "Agent quality on Terminal-Bench is not measured. Rollback is one variable: "
                                "<code>FLASHNEXT_MODEL=&lt;iQ pack&gt;</code>."))
    lis = "".join(f"<li><b>{h}.</b> {t}</li>" for h, t in items)
    return f'<section class="takeaways" id="verdict"><h2>{E(head)}</h2><ul>{lis}</ul></section>'


def _html_rig(d: dict) -> str:
    items = "".join(f'<div class="r-item"><p class="r-lab">{E(r["lab"])}</p><p class="r-val">{E(r["val"])}</p></div>'
                    for r in d["rig"])
    return f'<section class="block"><h2 class="sec">Rig</h2><div class="rig" id="rig">{items}</div></section>'


def _html_setup(d: dict) -> str:
    rows = ""
    for a in d["arms"]:
        s = d["stacks"][a]
        rows += (f"<tr><td>{_arm_cell(a)}</td><td><span class=\"mono\">{E(s['weights'])}</span><br>"
                 f"rev <span class=\"mono\">{E(s['rev'])}</span></td><td class=\"mono\">{E(s['runtime'])}</td>"
                 f"<td>{E(s.get('role', ''))}</td></tr>")
    return (
        '<section class="block" id="setup"><h2 class="sec">Setup by arm</h2>'
        '<p class="s-note">Both arms run on the same binary with the same flags. Only the weights change.</p>'
        '<div class="tbl-scroll"><table class="cfg"><thead><tr><th>Arm</th><th>Weights</th><th>Runtime</th>'
        f'<th>Role</th></tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p class="s-note mt">Server: <code>{E(SERVER_FLAGS)}</code>. Client: <code>reasoning_effort xhigh</code> in every '
        'request. Without it, mlx-serve answers with no thinking. Profiles: '
        f'<b>{E(PROFILE_LABEL["t1"])}</b>; <b>{E(PROFILE_LABEL["t0"])}</b>. <code>max_tokens</code>: HumanEval '
        '32,768; GPQA and LiveCodeBench 65,536; tool calls 32,768; IF 16,384.</p></section>')


def _pass_chip(ok) -> str:
    if ok is None:
        return '<span class="stchip">n/d</span>'
    return '<span class="stchip pass">pass</span>' if ok else '<span class="stchip fail">fail</span>'


def _html_gates(d: dict) -> str:
    g = d["gates"]
    rows = ""
    for s, cell in g["g1"].items():
        thr = f"w1 ≥ n2 − {cell['t1']['margin']}"
        vals = [f"{ND(cell[p]['w1'])} vs {ND(cell[p]['n2'])} {_pass_chip(cell[p]['pass'])}" for p in PROFILES]
        name = "HumanEval (with prompt imports)" if s == "humaneval" else SUITE_LABEL[s]
        rows += f"<tr><td>G1 quality · {E(name)}</td><td>{E(thr)}</td><td>{vals[0]}</td><td>{vals[1]}</td></tr>"
    for s, cell in g["g2"].items():
        vals = [f"{ND(cell[p]['ratio'], '{:.2f}')}× {_pass_chip(cell[p]['pass'])}" for p in PROFILES]
        rows += (f"<tr><td>G2 thinking · {E(SUITE_LABEL[s])}</td><td>median time w1/n2 ≤ {g['time_ratio']}</td>"
                 f"<td>{vals[0]}</td><td>{vals[1]}</td></tr>")
    for c, cell in g["g3"].items():
        rows += (f"<tr><td>G3 speed · T_turn at {int(c) // 1024}K</td><td>w1 ≤ {g['g3_ratio']} × n2</td>"
                 f"<td>{ND(cell['w1'], '{:.1f}')} vs {ND(cell['n2'], '{:.1f}')} s ({ND(cell['ratio'], '{:.2f}')}×) "
                 f"{_pass_chip(cell['pass'])}</td><td><span class=\"na\">—</span></td></tr>")
    dec = g["decision"]
    rule = (f"Promote when G1 and G2 pass in t1, G1 passes in t0 and G3 passes. "
            f"G1 t1 {_pass_chip(dec['g1_t1'])} · G2 t1 {_pass_chip(dec['g2_t1'])} · G1 t0 {_pass_chip(dec['g1_t0'])} "
            f"· G3 {_pass_chip(dec['g3'])} → <b>{'promote' if dec['promote'] else 'keep n2' if dec['promote'] is False else 'open'}</b>.")
    return ('<section class="block" id="gates"><h2 class="sec">Gates</h2>'
            '<p class="s-note">The gates were fixed in the runbook before the runs. G2 in t0 is informative: the '
            'rule reads G2 in t1, the vendor sampling.</p>'
            '<div class="tbl-scroll"><table class="gates"><thead><tr><th>Gate</th><th>Threshold</th><th>t1</th>'
            f'<th>t0</th></tr></thead><tbody>{rows}</tbody></table></div><p class="s-note mt">{rule}</p></section>')


def _html_switch() -> str:
    btns = "".join(f'<button type="button" data-set-profile="{p}" aria-pressed="{"true" if p == "t1" else "false"}" '
                   f'title="{E(PROFILE_LABEL[p])}">{E(SWITCH_LABEL[p])}</button>' for p in PROFILES)
    return (f'<div class="switch" id="profile-switch" role="group" aria-label="Sampling profile">'
            f'<span class="sw-lab">Profile for Quality, Time per task and Tool-call latency</span>{btns}</div>')


def _html_quality(d: dict) -> str:
    q, rg = d["quality"], d["humaneval_regrade"]
    head = "".join(f"<th>{a} {p}</th>" for p in PROFILES for a in d["arms"])

    def row(key, label, cells, margin):
        tds = "".join(f"<td>{ND(v)}</td>" for v in cells)
        return f'<tr data-suite="{key}"><td>{E(label)}</td>{tds}<td>{E(margin)}</td></tr>'

    rows = ""
    for s in d["suites"]:
        cells = [q[p][a][s]["passed"] for p in PROFILES for a in d["arms"]]
        label = SUITE_LABEL[s]
        if s == "humaneval":
            cells = [(rg.get(f"{a}-{p}") or {}).get("with_imports", q[p][a][s]["passed"])
                     for p in PROFILES for a in d["arms"]]
            label += ", with prompt imports"
        rows += row(s, label, cells, S.QUALITY_MARGIN[s])
        if s == "humaneval":
            strict = [(rg.get(f"{a}-{p}") or {}).get("strict") for p in PROFILES for a in d["arms"]]
            rows += row("humaneval-strict", "HumanEval · 164, strict bench2 grade", strict, "—")
    bars = ""
    for p in PROFILES:
        blocks = ""
        for s in d["suites"]:
            lines = ""
            for a in d["arms"]:
                c = q[p][a][s]
                passed = c["passed"]
                if s == "humaneval":
                    passed = (rg.get(f"{a}-{p}") or {}).get("with_imports", passed)
                pct = None if passed is None or not c["n"] else 100.0 * passed / c["n"]
                bar = (f'<span class="fill" style="width:{pct:.1f}%;background:var({ARM_COLOR[a]})"></span>'
                       if pct is not None else "")
                val = ND(pct, "{:.0f}", "%") + (f' <span class="u">{passed}/{c["n"]}</span>' if pct is not None else "")
                lines += f'<div class="qline">{_arm_cell(a)}<span class="qbar">{bar}</span><span class="qv">{val}</span></div>'
            blocks += f'<div class="qblock"><p class="q-title">{E(SUITE_LABEL[s])}</p>{lines}</div>'
        bars += f'<div class="prof prof-{p}"><div class="qgrid">{blocks}</div></div>'
    return ('<section class="block" id="quality"><h2 class="sec">Quality</h2>'
            '<p class="s-note">Correct answers per suite. The table always shows both profiles; the bars follow the '
            'profile switch. HumanEval uses the grade with the prompt imports for G1: the strict bench2 grader runs '
            'only the answer code, so a correct answer without <code>from typing import List</code> fails. That '
            'defect hits both arms.</p>'
            f'<div class="tbl-scroll"><table class="qual"><thead><tr><th>Suite</th>{head}<th>G1 margin</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>{bars}</section>')


def _log_ticks(lo: float, hi: float) -> list[float]:
    out = []
    for e in range(-1, 5):
        for m in (1, 2, 5):
            v = m * 10 ** e
            if lo <= v <= hi:
                out.append(v)
    return out


def _strip(p: str, s: str, cell: dict) -> str:
    arms = cell["arms"]
    pts = [x["s"] for a in ARMS for x in arms[a]["points"] if x["s"] and x["s"] > 0]
    title = f'<p class="p-title">{E(SUITE_LABEL[s])}</p>'
    if not pts:
        return (f'<figure class="strip" data-profile="{p}" data-suite="{s}">{title}'
                '<p class="empty">n/d: no records for this suite.</p></figure>')
    lo, hi = min(pts) / 1.25, max(pts) * 1.25
    W, H, x0, x1, lane = 560, 132, 30, 548, 46
    lx = lambda v: x0 + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (x1 - x0)  # noqa: E731
    g = ""
    for v in _log_ticks(lo, hi):
        x = lx(v)
        g += (f'<line class="gl" x1="{x:.1f}" y1="8" x2="{x:.1f}" y2="{H - 20}"/>'
              f'<text class="tick" x="{x:.1f}" y="{H - 6}" text-anchor="middle">{v:g}s</text>')
    for i, a in enumerate(ARMS):
        yc = 14 + lane * i + lane / 2
        g += f'<text class="axis-t" x="2" y="{yc + 3:.1f}">{a}</text>'
        st = arms[a]
        if st["missing"]:
            g += f'<text class="tick" x="{x0}" y="{yc + 3:.1f}">n/d</text>'
            continue
        for j, x in enumerate(st["points"]):
            if not x["s"] or x["s"] <= 0:
                continue
            jit = ((j * 37) % 17 - 8) * 1.6
            cls = f"dot {a} {'ok' if x['ok'] else 'bad'}" + (" trunc" if x["trunc"] else "")
            tip = f"{a} · question {x['id']} · {x['s']:.1f} s · {'pass' if x['ok'] else 'fail'}" + \
                  (" · truncated" if x["trunc"] else "")
            g += (f'<circle class="{cls}" cx="{lx(x["s"]):.1f}" cy="{yc + jit:.1f}" r="3.6" '
                  f'style="--c:var({ARM_COLOR[a]})"><title>{E(tip)}</title></circle>')
        if st["median_s"]:
            mx = lx(st["median_s"])
            g += (f'<line class="med" x1="{mx:.1f}" y1="{yc - 17:.1f}" x2="{mx:.1f}" y2="{yc + 17:.1f}" '
                  f'style="--c:var({ARM_COLOR[a]})"/>'
                  f'<text class="medlab" x="{mx + 4:.1f}" y="{yc - 10:.1f}">{st["median_s"]:.1f}s</text>')
    ratio = f'<span class="p-unit">median w1/n2 {ND(cell["ratio"], "{:.2f}")}×</span>'
    return (f'<figure class="strip" data-profile="{p}" data-suite="{s}"><div class="p-head">{title}{ratio}</div>'
            f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{E(SUITE_LABEL[s])}, time per question">'
            f'{g}</svg></figure>')


def _html_time(d: dict) -> str:
    out = ""
    for p in PROFILES:
        figs = "".join(_strip(p, s, d["time"][p][s]) for s in d["suites"])
        rows = ""
        for s in d["suites"]:
            c = d["time"][p][s]
            A = c["arms"]

            def two(k, fmt="{}"):
                return "".join(f"<td>{ND(A[a][k], fmt)}</td>" for a in ARMS)

            total = "".join(f"<td>{ND(None if A[a]['total_s'] is None else A[a]['total_s'] / 60, '{:.0f}')}</td>"
                            for a in ARMS)
            rows += (f'<tr data-suite="{s}"><td>{E(SUITE_LABEL[s])}</td>{two("median_s", "{:.1f}")}'
                     f'<td><b>{ND(c["ratio"], "{:.2f}")}</b></td>{total}{two("median_completion", "{:.0f}")}'
                     f'{two("median_reasoning_chars", "{:.0f}")}{two("truncated")}</tr>')
        head = ("<th>Suite</th><th>n2 median s</th><th>w1 median s</th><th>ratio</th><th>n2 total min</th>"
                "<th>w1 total min</th><th>n2 tokens</th><th>w1 tokens</th><th>n2 reasoning chars</th>"
                "<th>w1 reasoning chars</th><th>n2 trunc</th><th>w1 trunc</th>")
        out += (f'<div class="prof prof-{p}"><div class="legend">'
                f'<span class="chip">{_sw("n2")}<span class="code">n2</span> iQ-MLX</span>'
                f'<span class="chip">{_sw("w1")}<span class="code">w1</span> Swift 1.5</span>'
                '<span class="chip"><span class="dotkey"></span> pass</span>'
                '<span class="chip"><span class="dotkey hollow"></span> fail</span>'
                '<span class="chip"><span class="dotkey trunc"></span> truncated at max_tokens</span>'
                '<span class="chip"><span class="medkey"></span> median</span></div>'
                f'<div class="sgrid">{figs}</div>'
                f'<div class="tbl-scroll mt"><table class="timet"><thead><tr>{head}</tr></thead>'
                f'<tbody>{rows}</tbody></table></div></div>')
    return ('<section class="block" id="time-per-task"><h2 class="sec">Time per task</h2>'
            '<p class="s-note">One dot per question: wall time from request to final answer, log scale. Tool-call '
            'suites add turn 1 and turn 2. Tokens and reasoning characters are medians per question; '
            '<code>n/d</code> = not recorded. A truncated answer hit <code>max_tokens</code> and counts as a '
            'failure.</p>' + out + '</section>')


def _html_tool_latency(d: dict) -> str:
    out = ""
    for p in PROFILES:
        rows = ""
        for s, arms in d["tool_latency"][p].items():
            for a in ARMS:
                c = arms[a]
                if c.get("missing"):
                    rows += (f'<tr data-suite="{s}"><td>{E(SUITE_LABEL[s])}</td><td>{_arm_cell(a)}</td>'
                             '<td colspan="3"><span class="na">n/d</span></td></tr>')
                    continue
                t2 = (f"{ND(c['turn2_median_s'], '{:.2f}')} <span class=\"u\">({c['turn2_n']} cases)</span>"
                      if c["turn2_n"] else '<span class="na">no multi-turn case</span>')
                rows += (f'<tr data-suite="{s}"><td>{E(SUITE_LABEL[s])}</td><td>{_arm_cell(a)}</td>'
                         f'<td>{c["passed"]}/{c["n"]}</td><td>{ND(c["turn1_median_s"], "{:.2f}")}</td><td>{t2}</td></tr>')
        out += (f'<div class="prof prof-{p}"><div class="tbl-scroll"><table class="toolt"><thead><tr><th>Suite</th>'
                '<th>Arm</th><th>pass</th><th>turn 1 median s</th><th>turn 2 median s</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div></div>')
    return ('<section class="block" id="tool-latency"><h2 class="sec">Tool-call latency per turn</h2>'
            '<p class="s-note">Short-context tool calling. Turn 1 = the model picks the tool and writes the call. '
            'Turn 2 = the model reads the tool result and answers; only the multi-turn cases have it. The two arms '
            'stay within a few tenths of a second.</p>' + out + '</section>')


def _html_agent_turn(d: dict) -> str:
    rows = ""
    for c in CONTEXTS:
        rows += f'<tr class="grp-row"><td colspan="10">context {int(c) // 1024}K</td></tr>'
        for r in d["speed"][c]:
            flag = ""
            if r["gates_failed"]:
                flag = f' <span class="stchip fail" title="gates failed">{E(", ".join(r["gates_failed"]))}</span>'
            src = SOURCE_LABEL.get(r["source"], r["source"])
            extra = [r["config"]] if r["config"] else []
            if r["reps"] == 1:
                extra.append("1 rep")
            name = E(r["name"]) + "".join(f' <span class="u">· {E(x)}</span>' for x in extra)
            if r["absent"]:
                rows += (f'<tr><td>{_arm_cell(r["arm"])}</td><td class="nm">{name}</td>'
                         f'<td colspan="8"><span class="na">{E(r["absent"])}</span></td></tr>')
                continue
            rows += (f'<tr><td>{_arm_cell(r["arm"])}{flag}</td><td class="nm">{name}<br><span class="u">{E(src)}</span></td>'
                     f'<td><b>{ND(r["t_turno_s"], "{:.1f}")}</b></td><td>{ND(r["ttft_tool_turn_s"], "{:.1f}")}</td>'
                     f'<td>{ND(r["hit_tool_turn"], "{:.3f}")}</td><td>{ND(r["cold_ttft_s"], "{:.0f}")}</td>'
                     f'<td>{ND(r["decode_tps"], "{:.1f}")}</td><td>{ND(r["prefill_tps"], "{:.0f}")}</td>'
                     f'<td>{ND(r["mtp_acceptance"], "{:.2f}")}</td><td>{ND(r["wired_peak_gb"], "{:.1f}")}</td></tr>')
    drift = d["speed"]["drift"]
    note = ("T_turn = warm TTFT of the <code>tool_turn</code> scenario + 512 tokens at the warm decode rate, median "
            "of 3 reps unless the row says 1 rep, vendor sampling (t1). n2 and w1 ran in this campaign, one after the "
            "other. o1, m1 and d1 come from the October perf-lines campaign, where n2 measured "
            f"{ND(drift.get('32768'), '{:.2f}')} s at 32K and {ND(drift.get('131072'), '{:.2f}')} s at 128K. "
            f'256K and 512K are on the <a href="{PERF_LINES}">perf-lines page</a> (w1 was not run there). The '
            "<code>needle</code> flag on n2 at 32K is one tool_turn request of 13 that missed the three needles; the "
            "other requests of both arms passed.")
    return ('<section class="block" id="agent-turn"><h2 class="sec">Agent turn speed · tool_turn</h2>'
            f'<p class="s-note">{note}</p><div class="tbl-scroll"><table class="speedt"><thead><tr><th>Arm</th>'
            '<th class="nm">Stack</th><th>T_turn s</th><th>warm TTFT tool_turn s</th><th>hit tool_turn</th><th>cold TTFT s</th>'
            '<th>decode tok/s</th><th>prefill tok/s</th><th>MTP accept</th><th>wired peak GB</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div></section>')


def _html_legacy(d: dict) -> str:
    L = d["legacy"]
    rows = "".join(
        f'<tr><td>{_arm_cell(r["arm"])}</td><td class="nm">{E(r["stack"])}</td><td class="nm nw">{E(r["date"])}</td>'
        f'<td>{ND(r["he_strict"])}</td><td>{ND(r["he_imports"])}</td><td>{ND(r["he_truncated"])}</td>'
        f'<td>{ND(r["jdhodges"])}</td><td>{ND(r["veerman"])}</td><td>{ND(r["he_tokens"])}</td>'
        f'<td>{ND(r["he_minutes"])}</td><td class="nm">{E(r["thinking"])}</td></tr>' for r in L["rows"])
    n2t0 = d["time"]["t0"]["humaneval"]["arms"]["n2"]
    src = " · ".join(f"<code>{E(s)}</code>" for s in L["sources"])
    return ('<section class="block" id="legacy"><h2 class="sec">Earlier quality batteries · not comparable</h2>'
            '<p class="s-note"><b>Do not rank these rows against the tables above.</b> These runs used temperature 0 '
            'and sent no <code>reasoning_effort</code>. Without it, mlx-serve answered with almost no thinking (n2; '
            'n1 not recorded), while oMLX and MTPLX thought. With <code>reasoning_effort xhigh</code> in this campaign, '
            f'the same n2 uses a mean of {ND(n2t0["mean_completion"], "{:.0f}")} tokens per HumanEval answer at t0 '
            f'(median {ND(n2t0["median_completion"], "{:.0f}")}). Sources: {src}.</p>'
            '<div class="tbl-scroll"><table class="legt"><thead><tr><th>Arm</th><th class="nm">Stack</th><th class="nm">Date</th>'
            '<th>HumanEval strict</th><th>HumanEval with imports</th><th>HumanEval truncated</th><th>jdhodges /40</th>'
            '<th>Veerman /12</th><th>tokens per HumanEval answer (mean)</th><th>HumanEval wall time min</th>'
            f'<th class="nm">Thinking</th></tr></thead><tbody>{rows}</tbody></table></div></section>')


def _html_limits(d: dict) -> str:
    toks = [d["time"][p][s]["arms"][a]["median_completion"] for p in PROFILES for s in S.TOOL_SUITES
            for a in ARMS if d["time"][p][s]["arms"][a]["median_completion"] is not None]
    rng = "n/d" if not toks else f"{min(toks):.0f}" if min(toks) == max(toks) else f"{min(toks):.0f}–{max(toks):.0f}"
    lis = "".join(f"<li>{t.replace('__TOOLTOKENS__', rng)}</li>" for t in LIMITS)
    return f'<section class="block notice" id="limits"><p><b>Limits</b></p><ul>{lis}</ul></section>'


PAGE_CSS = r"""
:root{--s6:#7a5cd6}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--s6:#9a80ee}}
:root[data-theme="dark"]{--s6:#9a80ee}
html[data-profile="t1"] .prof-t0, html[data-profile="t0"] .prof-t1{display:none}
.mt{margin-top:12px}
.u{color:var(--muted); font-size:0.9em; margin-left:2px}
.switch{position:sticky; top:0; z-index:4; display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top:30px;
  padding:10px 12px; background:var(--plane); border:1px solid var(--border); border-radius:10px}
.switch .sw-lab{flex-basis:100%; font-family:var(--mono); font-size:0.66rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); margin-right:4px}
.switch button{white-space:nowrap; font-family:var(--mono); font-size:0.74rem; color:var(--ink-2); background:var(--surface);
  border:1px solid var(--border); border-radius:7px; padding:7px 11px; cursor:pointer; text-align:left}
.switch button[aria-pressed="true"]{border-color:var(--accent); color:var(--ink); box-shadow:inset 0 0 0 1px var(--accent)}
.switch button:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
table.cfg td, table.cfg th, table.gates td, table.gates th{text-align:left; font-family:var(--sans); font-size:0.83rem}
table.cfg .mono, table.cfg td.mono{font-family:var(--mono); font-size:0.8rem; color:var(--ink-2)}
table.gates td:nth-child(2){font-family:var(--mono); font-size:0.78rem; color:var(--ink-2)}
td.nm{font-family:var(--sans); text-align:left; color:var(--ink-2); font-size:0.8rem}
th.nm{text-align:left} .nw{white-space:nowrap}
.sgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,470px),1fr)); gap:14px; margin-top:14px}
.strip .tick{font-size:11px} .strip .axis-t{font-size:12px; font-weight:700} .strip .medlab{font-size:11px}
.qgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; margin-top:14px}
.qblock{background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:10px 12px}
.q-title{margin:0 0 8px; font-size:0.86rem; font-weight:700}
.qline{display:grid; grid-template-columns:44px 1fr 92px; gap:8px; align-items:center; margin:5px 0}
.qbar{height:10px; background:var(--surface-2); border-radius:3px; overflow:hidden; display:block}
.qbar .fill{display:block; height:100%; border-radius:3px}
.qv{font-family:var(--mono); font-size:0.78rem; text-align:right}
figure.strip{margin:0; background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:12px 12px 6px}
figure.strip .p-title{margin:0}
figure.strip .empty{color:var(--muted); font-size:0.84rem}
.gl{stroke:var(--grid); stroke-width:1}
.dot{fill:var(--c); stroke:var(--c); stroke-width:1.2; fill-opacity:0.72}
.dot.bad{fill:var(--surface); fill-opacity:1; stroke-width:1.6}
.dot.trunc{stroke:var(--warn); stroke-width:2.4}
.med{stroke:var(--c); stroke-width:2.5}
.medlab{font-family:var(--mono); font-size:9.5px; fill:var(--ink-2)}
.dotkey{display:inline-block; width:10px; height:10px; border-radius:50%; background:var(--ink-2)}
.dotkey.hollow{background:transparent; border:1.5px solid var(--ink-2)}
.dotkey.trunc{background:transparent; border:2px solid var(--warn)}
.medkey{display:inline-block; width:3px; height:12px; background:var(--ink-2)}
#time-per-task .legend{margin-top:14px}
@media (max-width:520px){.qline{grid-template-columns:40px 1fr 80px}}
"""

TEMPLATE = r"""<!doctype html>
<html lang="en" data-profile="t1">
<meta charset="utf-8">
<title>Flash-Next Swift 1.5 A/B</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Swift 1.5 vs the iQ-MLX pack of Qwen3.8-Flash-Next on mlx-serve 26.10.1: quality, time per task, tool-call latency and agent-turn speed.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>
/*__CSS__*/
</style>
<div class="wrap">
  <header>
    <div>
      <p class="eyebrow">Fine-tune A/B · mlx-serve 26.10.1 · October 2026</p>
      <h1>Qwen3.8-Flash-Next: Swift 1.5 vs iQ-MLX</h1>
      <p class="sub">Two 4.7-bpw packs of the same model on the same runtime and flags: the ddalcu iQ-MLX pack (n2, the previous daily driver) and the Dankpaws Swift 1.5 fine-tune (w1). Six quality suites in two sampling profiles, time per question, tool-call latency and agent-turn speed, with the other October stacks as speed reference.</p>
    </div>
    <button class="theme" id="themeBtn" type="button">theme: auto</button>
  </header>
__VERDICT__
<section class="block notice" id="notice"><p><b>Not measured: agent quality.</b> Terminal-Bench 2.0 needs a second machine for the Docker containers, so this campaign suspended it. The driver script is ready (<code>bench/terminal-bench/scripts/run-tbench-flashnext.sh</code>). Speed by context up to 512K for the other runtimes is on the <a href="__PERF__">perf-lines page</a>.</p></section>
__RIG__
__SETUP__
__GATES__
__SWITCH__
__QUALITY__
__TIME__
__TOOL__
__AGENT__
__LEGACY__
__LIMITS__
  <footer id="foot"><b>Sources.</b> <code>bench/swift15-flashnext-2026-10/results/</code> (A/B battery, <code>humaneval-regrade.json</code>, <code>tturno-summary.json</code>, <code>summary.md</code>) and <code>bench/engine-updates-2026-10/results/reports-2026-10.json</code>. Generated at <code>__GENERATED__</code> by <code>bench/swift15-flashnext-2026-10/scripts/render_page.py</code>.</footer>
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


def render(data: dict) -> str:
    parts = {
        "/*__CSS__*/": PERF_CSS + PERF_EXTRA_CSS + PAGE_CSS,
        "__VERDICT__": _html_verdict(data), "__RIG__": _html_rig(data), "__SETUP__": _html_setup(data), "__GATES__": _html_gates(data),
        "__SWITCH__": _html_switch(), "__QUALITY__": _html_quality(data), "__TIME__": _html_time(data),
        "__TOOL__": _html_tool_latency(data), "__AGENT__": _html_agent_turn(data), "__LEGACY__": _html_legacy(data),
        "__LIMITS__": _html_limits(data), "__PERF__": PERF_LINES, "__GENERATED__": E(data.get("generated_at", "")),
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
