#!/usr/bin/env python3
"""Render the public Splash 1.6.1 vs 1.5.0 report page.

collect() returns a plain dict. Most numbers restate the stage reports (results/etapa*.md); each constant names
its source. The Task 5 largest gaps and the Task 7 probe ratio and per-hour probe are computed from the committed
JSONL. render() turns the dict into one self-contained HTML page, with the CSS, the theme script and the chart
helpers of bench/splash16-2026-11/scripts/render_page.py.

    python3 bench/splash161-2026-11/scripts/render_page.py \\
        [--results-dir DIR] [--out-html reports/qwen38-flashnext-splash161.html]
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE.parent
RESULTS = CAMPAIGN / "results"
REPO = CAMPAIGN.parents[1]
S16_PATH = REPO / "bench" / "splash16-2026-11" / "scripts" / "render_page.py"


def _load_s16():
    spec = importlib.util.spec_from_file_location("splash16_render_page", S16_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["splash16_render_page"] = mod
    spec.loader.exec_module(mod)
    return mod


S16 = _load_s16()
_e, _table, _badge, svg_hbars = S16._e, S16._table, S16._badge, S16.svg_hbars
OLD_C, NEW_C, OTHER_C = S16.OLD_C, S16.NEW_C, S16.OLD_OTHER_C

TITLE = "Splash 1.6.1 vs 1.5.0"
RIG = "Mac Studio M4 Max 128 GB"
WEIGHTS = "ukisai Swift 1.5 Qwen3.8 Flash-Next GGUF IQ4_XS (revision 0142554)"
DATES = ["2026-11-11", "2026-11-12"]

GITHUB = "https://github.com/snagnever/macstudio-local-llm"
PLAN_URL = f"{GITHUB}/blob/main/bench/splash161-2026-11/plan.md"
RESULTS_URL = f"{GITHUB}/tree/main/bench/splash161-2026-11/results"
NOTES_161 = "https://github.com/incoai/splash/blob/1.6.1/docs/release-notes/1.6.1.md"
ISSUE_644 = "https://github.com/incoai/splash/issues/644"

# Source: results/summary.md, "Respostas". Every task passed with PLE auto.
VERDICTS: dict[str, dict[str, Any]] = {
    "1": {"question": "Does the pack load, and does the release switch break any client?", "result": "pass",
          "text": "pass", "skipped": False},
    "2": {"question": "Does 1.6.1 keep the turn time of one stream, in both PLE modes?", "result": "pass",
          "text": "pass in both modes", "skipped": False},
    "3": {"question": "Is the 1.6.0 slowdown of two long sessions gone?", "result": "pass",
          "text": "pass in both modes", "skipped": False},
    "4": {"question": "Do Claude Code sessions keep the 1.6.0 gain?", "result": "pass", "text": "pass",
          "skipped": False},
    "5": {"question": "Under a memory limit, does 1.6.1 stay free of stalls?", "result": "pass", "text": "pass",
          "skipped": False},
    "6": {"question": "Does quality stay the same?", "result": "pass", "text": "pass", "skipped": False},
    "7": {"question": "Does a 4-hour agent load stay stable?", "result": "pass", "text": "stable, no regression",
          "skipped": False},
}

# Task 2. Source: results/etapa2-um-stream.md. Turn time (s), 3 boots per arm and band, ABBA order.
TASK2 = [  # band, 1.5.0, 1.6.1 auto, 1.6.1 off, wired peak 1.5.0 / auto (GB)
    ("32K", 6.0, 6.1, 6.0, 106.5, 77.5),
    ("128K", 6.0, 6.1, 6.0, 108.3, 79.8),
    ("256K", 6.3, 6.3, 6.3, 111.0, 82.2),
]
TASK2_1M = {"old_ref": 9.8, "new": 7.0, "old_decode": 71.4, "new_decode": 101.7}  # 1.5.0 from splash16

# Task 3. Source: results/etapa3-concorrencia.md. Mean worst stream of 3 reps (s), 1.5.0 in the same queue.
TASK3 = [  # arm, 1.5.0, auto, off, claim_wait max auto, off (s)
    ("two 256K sessions", 16.07, 16.63, 16.03, 0.0, 2.9),
    ("two 128K sessions + side requests", 14.63, 15.80, 15.13, 0.0, 0.0),
]
TASK3_160 = {"pct": 65, "claim_wait_max_s": 30.1}  # splash16 etapa4-concorrencia.md

# Task 4. Source: results/etapa4-claude-code.md.
TASK4 = [  # profile, metric, 1.5.0, 1.6.1, ratio
    ("pair", "pair wall", "347.6 s", "336.1 s", 0.967),
    ("pair", "warm TTFT p50", "1.4 s", "0.9 s", 0.64),
    ("pair with subagents", "wall", "848.1 s", "568.4 s", 0.670),
    ("pair with subagents", "warm TTFT p50", "3.2 s", "1.6 s", 0.50),
]

# Task 5. Source: results/etapa5-pressao.md (requests and SSD reads per run). Gaps come from the JSONL.
TASK5 = {"old_requests": [168, 165], "new_requests": [225, 225], "old_ssd_gb": [841, 842], "new_ssd_gb": [258, 246],
         "old_over5": [4, 7], "new_over5": [0, 0]}
CHURN = {"old": ["150-r1", "150-r2"], "new": ["161-r1", "161-r2"]}

# Task 6. Source: results/etapa6-qualidade.md. 1.5.0 W1 and W2 come from bench/flashnext-weights-2026-11.
TASK6 = [  # suite, W1, W2, 1.6.1
    ("HumanEval /164", 144, 144, 145), ("GPQA /50", 42, 44, 43), ("LiveCodeBench /50", 46, 47, 46),
    ("IF /20", 19, 19, 19), ("jdhodges /40", 35, 38, 38), ("veerman /12", 7, 10, 9),
]
TASK6_TOOLS = [("frequency_penalty 0", 20, 20), ("frequency_penalty 1", 11, 16)]
TASK6_LONGCTX = "8/8 at 131072 and 8/8 at 262144"

# Task 7. Source: results/etapa7-agente-4h.md; the probes come from soak-h161.jsonl.
TASK7 = {"pairs": 43, "requests": 1667, "errors": 0, "task_done": "86/86", "max_pages": 32512,
         "denied": 7416, "claim_wait_max_s": 4.9, "warm_ttft": "0.91 / 2.27 s", "ref160_pairs": 43,
         "ref150_pairs": 38}
SOAK_HOURS = [(0, 10), (1, 10), (2, 11), (3, 11), (4, 1)]  # hour, pairs (etapa7 "Por hora")

TERMS = [("k2f", "the weights on Splash 1.5.0, the control"),
         ("k2h / k2hp", "the weights on Splash 1.6.1 with PLE auto / with --ple-memory off"),
         ("k2c2LL", "two 256K sessions"),
         ("k2c2a", "two 128K sessions plus side requests (titles, summaries)"),
         ("rc2 / rc2s", "a pair of real Claude Code sessions / the same with subagents"),
         ("T_turno", "turn time: warm TTFT of a tool turn plus 512 tokens of decode"),
         ("claim_wait", "the part of TTFT a request spends waiting for memory"),
         ("PLE", "the per-layer embedding table of Flash-Next, 27465 MiB")]


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _max_gap(results: Path, run: str) -> float:
    return max(g for r in _rows(results / f"churn-{run}.jsonl") for g in (r.get("gaps_s") or []))


def _soak(results: Path) -> dict[str, Any]:
    recs = [r for r in _rows(results / "soak-h161.jsonl") if r.get("kind") == "probe"]
    med = {}
    for r in recs:
        med.setdefault(r["label"], []).append(r["decode_tok_s"])
    med = {k: statistics.median(v) for k, v in med.items()}
    hours, done = [], 0
    for h, n in SOAK_HOURS:
        done += n
        hours.append((h, round(med[f"pair{done}"], 1)))
    pre, end = med["pre"], med[f"pair{done}"]
    return {"pre": round(pre, 1), "end": round(end, 1), "ratio": round(end / pre, 2), "hours": hours,
            "min": round(min(r["decode_tok_s"] for r in recs), 1), **TASK7}


def collect(results_dir: Path = RESULTS) -> dict[str, Any]:
    gaps = {k: [round(_max_gap(results_dir, run), 1) for run in runs] for k, runs in CHURN.items()}
    return {
        "rig": RIG, "weights": WEIGHTS, "dates": DATES, "verdicts": VERDICTS,
        "task2": {"bands": [dict(zip(("band", "old", "auto", "off", "wired_old", "wired_auto"), b)) for b in TASK2],
                  "m1": TASK2_1M},
        "task3": {"arms": [dict(zip(("arm", "old", "auto", "off", "cw_auto", "cw_off"), a)) for a in TASK3],
                  "ref160": TASK3_160},
        "task4": [dict(zip(("profile", "metric", "old", "new", "ratio"), r)) for r in TASK4],
        "task5": {"old_gaps_s": gaps["old"], "new_gaps_s": gaps["new"], "old_max_gap_s": max(gaps["old"]),
                  "new_max_gap_s": max(gaps["new"]), **TASK5},
        "task6": {"suites": [dict(zip(("suite", "w1", "w2", "new"), s)) for s in TASK6],
                  "tools": [dict(zip(("profile", "old", "new"), t)) for t in TASK6_TOOLS], "longctx": TASK6_LONGCTX},
        "task7": _soak(results_dir),
    }


# ---- sections ----

def _pct(new: float, old: float) -> str:
    return f"{(new / old - 1) * 100:+.1f}%"


def _hero(d: dict[str, Any]) -> str:
    ll = d["task3"]["arms"][0]
    t5, t7 = d["task5"], d["task7"]
    w = d["task2"]["bands"]
    freed = [b["wired_old"] - b["wired_auto"] for b in w]
    tiles = [
        ("Splash launcher", "Switches to 1.6.1", "Every task passes with PLE auto, the 1.6.1 default."),
        ("Two 256K sessions", _pct(ll["auto"], ll["old"]),
         f"Worst stream {ll['old']:.2f} s on 1.5.0 and {ll['auto']:.2f} s on 1.6.1, same queue. On 1.6.0 it was "
         f"+{d['task3']['ref160']['pct']}%. No request waits for memory."),
        ("One stream", "Same", "Turn-time ratio 1.6.1 ÷ 1.5.0 is 1.000 to 1.017 at 32K, 128K and 256K."),
        ("64 GB memory limit", f"{t5['old_max_gap_s']:.1f} s → {t5['new_max_gap_s']:.1f} s",
         "Largest decode gap. 1.6.1 serves 34 to 36% more requests in the same 15 minutes."),
        ("RAM", f"−{max(freed):.0f} GB",
         "Wired peak of one stream at 32K to 256K. The 28.8 GB PLE table stays on the SSD with a 237 MiB row cache."),
        ("4-hour agent load", f"{t7['ratio']:.2f}", "Short-probe ratio end ÷ start, with the KV pool full: stable."),
    ]
    tiles_html = "".join(f'<div class="tile"><p class="t-lab">{_e(a)}</p><p class="t-big">{_e(b)}</p>'
                         f'<p class="t-sub">{_e(c)}</p></div>' for a, b, c in tiles)
    lead = (f"<b>Splash 1.6.1 fixes the 1.6.0 slowdown of two long sessions, and my launcher now runs it.</b> Two "
            f"256K sessions are {_pct(ll['auto'], ll['old'])} against 1.5.0, where 1.6.0 was "
            f"+{d['task3']['ref160']['pct']}%. One stream runs at the same speed, quality is the same, and 1.6.1 keeps "
            "the 1.6.0 gains under a memory limit and in Claude Code sessions. The default PLE mode (auto) frees "
            "22 to 29 GB of RAM.")
    meta = (f"Machine: {_e(d['rig'])}. Weights: {_e(d['weights'])}. Measured {_e(d['dates'][0])} to "
            f"{_e(d['dates'][1])}. Releases: Splash 1.5.0 and 1.6.1 (<a href=\"{NOTES_161}\">release notes</a>). "
            'Earlier campaign: <a href="qwen38-flashnext-splash160.html">Splash 1.6.0 vs 1.5.0</a>.')
    return (f'<section class="hero" id="verdict"><p class="hero-lead">{lead}</p><p class="s-note">{meta}</p>'
            f'<div class="tiles">{tiles_html}</div></section>')


def _q(n: int, d: dict[str, Any], answer: str, body: str) -> str:
    v = d["verdicts"][str(n)]
    return (f'<section class="q" id="task{n}"><h3>Task {n}. {_e(v["question"])}</h3>'
            f'<p class="verdict-line">{_badge(v)}</p><p class="s-note">{answer}</p>{body}</section>')


def _task1_html(d: dict[str, Any]) -> str:
    answer = ("Five smoke boots start. 1.5.0 still starts with <code>--offline</code> after a 1.6.1 boot, so the "
              "update keeps the weights in the cache. The API checks C1 to C6, the proxy check and the engine restart "
              "pass. The reuse check C7 behaves as on 1.5.0 and 1.6.0: the next turn does not reuse the reply tokens.")
    return _q(1, d, answer, "")


def _task2_html(d: dict[str, Any]) -> str:
    rows = [[b["band"], f"{b['old']:.1f} s", f"{b['auto']:.1f} s", f"{b['off']:.1f} s",
             f"{b['wired_old']:.1f} GB", f"{b['wired_auto']:.1f} GB"] for b in d["task2"]["bands"]]
    m = d["task2"]["m1"]
    answer = ("Turn time is within 1.7% of 1.5.0 in both PLE modes; the rule allows 3%. With PLE auto the wired "
              f"peak drops by 29 GB. At 1M, one rep gives a {m['new']:.1f} s turn and {m['new_decode']:.1f} tok/s "
              f"decode, against {m['old_ref']:.1f} s and {m['old_decode']:.1f} tok/s for 1.5.0 on another day.")
    return _q(2, d, answer, _table(["band", "1.5.0", "1.6.1 auto", "1.6.1 off", "wired 1.5.0", "wired 1.6.1 auto"],
                                   rows, "wide"))


def _task3_html(d: dict[str, Any]) -> str:
    arms = d["task3"]["arms"]
    groups = [{"label": a["arm"].replace(" + side requests", "+"), "bars": [
        {"name": "1.5.0", "value": a["old"], "color": OLD_C},
        {"name": "1.6.1 auto", "value": a["auto"], "color": NEW_C},
        {"name": "1.6.1 off", "value": a["off"], "color": OTHER_C}]} for a in arms]
    chart = svg_hbars("Worst stream, mean of 3 reps (lower is better)", groups, 20.0, "s", label_w=190.0)
    rows = [[a["arm"], f"{a['old']:.2f} s", f"{a['auto']:.2f} s ({_pct(a['auto'], a['old'])})",
             f"{a['off']:.2f} s ({_pct(a['off'], a['old'])})", f"{a['cw_auto']:.1f} / {a['cw_off']:.1f} s"]
            for a in arms]
    r = d["task3"]["ref160"]
    answer = (f"On 1.6.0 two 256K sessions were +{r['pct']}% against 1.5.0, with requests waiting up to "
              f"{r['claim_wait_max_s']:.1f} s for memory. On 1.6.1 the worst stream stays within 8% of 1.5.0 in both "
              "modes; the rule allows 10%. Both modes pass and tie within 5% on two 256K sessions, so the launcher "
              "keeps auto, which needs no flag.")
    legend = S16._legend([(OLD_C, "1.5.0"), (NEW_C, "1.6.1 PLE auto"), (OTHER_C, "1.6.1 PLE off")])
    return _q(3, d, answer, legend + S16._panel(chart, "Same queue, 1.5.0 control in each.",
                                               _table(["arm", "1.5.0", "1.6.1 auto", "1.6.1 off",
                                                       "claim_wait max auto / off"], rows, "wide")))


def _task4_html(d: dict[str, Any]) -> str:
    rows = [[_e(r["profile"]), _e(r["metric"]), r["old"], r["new"], f"{r['ratio']:.2f}"] for r in d["task4"]]
    answer = ("Real Claude Code sessions at 131072, Claude Code 2.1.292, 1.5.0 in the same queue. 1.6.1 is faster on "
              "every metric of the rule (limit 1.10). All 20 sessions finish their task.")
    return _q(4, d, answer, _table(["profile", "metric", "1.5.0", "1.6.1", "ratio"], rows, "wide"))


def _task5_html(d: dict[str, Any]) -> str:
    t5 = d["task5"]
    rows = [["largest gap", " and ".join(f"{g:.1f} s" for g in t5["old_gaps_s"]),
             " and ".join(f"{g:.1f} s" for g in t5["new_gaps_s"])],
            ["gaps over 5 s", " and ".join(map(str, t5["old_over5"])), " and ".join(map(str, t5["new_over5"]))],
            ["requests per run", " and ".join(map(str, t5["old_requests"])),
             " and ".join(map(str, t5["new_requests"]))],
            ["SSD reads per run", " and ".join(f"{g} GB" for g in t5["old_ssd_gb"]),
             " and ".join(f"{g} GB" for g in t5["new_ssd_gb"])]]
    answer = ("Fifteen minutes of three sessions at 131072 with <code>--max-memory 64G</code>, order 1.5.0, 1.6.1, "
              "1.6.1, 1.5.0. 1.5.0 stalls the decode for up to "
              f"{t5['old_max_gap_s']:.1f} s. 1.6.1 stays under 5 s. Its 3 HTTP 400 per run come from the load "
              "generator, which grows the prompt past the 131072 context.")
    return _q(5, d, answer, _table(["metric", "1.5.0", "1.6.1"], rows, "wide"))


def _task6_html(d: dict[str, Any]) -> str:
    s = d["task6"]["suites"]
    rows = [[x["suite"], str(x["w1"]), str(x["w2"]), str(x["new"])] for x in s]
    rows.append(["<b>total /336</b>", str(sum(x["w1"] for x in s)), str(sum(x["w2"] for x in s)),
                 f"<b>{sum(x['new'] for x in s)}</b>"])
    rows += [[f"tool calls, {t['profile']} (sessions /20)", str(t["old"]), "", str(t["new"])]
             for t in d["task6"]["tools"]]
    answer = ("The same weights on both releases. On every suite 1.6.1 sits between two 1.5.0 passes or within "
              "one question of the better 1.5.0 pass, and the margin check passes on all six against both. Long "
              "context: " + d["task6"]["longctx"] + ".")
    return _q(6, d, answer, _table(["check", "1.5.0 pass 1", "1.5.0 pass 2", "1.6.1"], rows, "wide"))


def _task7_html(d: dict[str, Any]) -> str:
    t = d["task7"]
    series = [{"name": "1.6.1", "color": NEW_C, "points": t["hours"], "threshold": 0.85 * t["pre"]}]
    chart = S16.svg_hour_lines("Short probe decode per hour (tok/s)", series, ymin=60.0, ymax=120.0)
    rows = [["completed pairs", str(t["pairs"]), str(t["ref160_pairs"]), str(t["ref150_pairs"])],
            ["probe before the load / at the end", f"{t['pre']:.1f} / {t['end']:.1f} tok/s", "99.1 / 90.3 tok/s",
             "101.6 / 97.8 tok/s"],
            ["ratio end ÷ start", f"{t['ratio']:.2f}", "0.91", "0.96"],
            ["sessions that finished the task", t["task_done"], "85/86", "75/76"],
            ["denied memory reservations at the end", str(t["denied"]), "11203", "71422"]]
    answer = ("Pairs of Claude Code sessions for 4 hours on one boot, with a short decode probe after each pair. The "
              f"KV pool is full from the first hour on and peaks at {t['max_pages']} pages, so the test exercises the "
              f'condition of <a href="{ISSUE_644}">#644</a>. The probe does not drop. The 1.6.0 and 1.5.0 columns '
              "come from another day and give no verdict.")
    return _q(7, d, answer, S16._panel(chart, f"The probe before the load was {t['pre']:.1f} tok/s; the hours sit "
                                              "above it.", _table(["metric", "1.6.1", "1.6.0", "1.5.0"], rows,
                                                                  "wide")))


def _questions(d: dict[str, Any]) -> str:
    summary = [[f'<a href="#task{n}">{n}</a>', _e(v["question"]), _badge(v)] for n, v in
               ((int(k), v) for k, v in d["verdicts"].items())]
    intro = (f'<p class="s-note">One block per question of the <a href="{PLAN_URL}">runbook</a>. The launcher '
             "switches to 1.6.1 only when Tasks 1 to 6 pass in one PLE mode and Task 7 shows no regression. Both "
             "hold with PLE auto.</p>")
    body = (intro + _table(["task", "question", "verdict"], summary, "wide") + _task1_html(d) + _task2_html(d)
            + _task3_html(d) + _task4_html(d) + _task5_html(d) + _task6_html(d) + _task7_html(d))
    return f'<section class="block" id="questions"><h2 class="sec">Answers by question</h2>{body}</section>'


def _method_html(d: dict[str, Any]) -> str:
    items = [
        f"One machine ({_e(d['rig'])}), one model at a time, the same weights on both releases. Base flags "
        "<code>--verify-rows auto --idle-release off --language-only --no-webui --offline</code>.",
        "Sampling: temperature 1.0, top_p 0.95, top_k 20, frequency_penalty 0, reasoning effort xhigh.",
        "Every speed verdict compares with 1.5.0 in the same queue: the earlier campaign saw a 2× change in the "
        "summed decode of two 256K sessions between days.",
        "Single stream: 3 boots per arm and band in ABBA order. Two sessions: 3 reps per arm. Claude Code: 2 reps "
        "on 1.5.0 and 3 on 1.6.1.",
        "The 1M row, the quality passes of 1.5.0 and the 1.6.0 and 1.5.0 columns of Task 7 come from other days.",
        "The 512K profile of the launcher was not measured on 1.6.1.",
        "This page restates the stage reports; the Task 5 gaps and the Task 7 probes are computed from the "
        "committed JSONL by <code>bench/splash161-2026-11/scripts/render_page.py</code>.",
    ]
    body = ('<ul class="notes">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
            f'<p class="s-note">Runbook: <a href="{PLAN_URL}">plan.md</a>. Results: <a href="{RESULTS_URL}">'
            "bench/splash161-2026-11/results</a>.</p>")
    return f'<section class="block" id="method"><h2 class="sec">Method and limits</h2>{body}</section>'


def _footer(generated: str) -> str:
    rows = [[f"<code>{_e(a)}</code>", _e(b)] for a, b in TERMS]
    return ('<footer id="terms"><h2 class="sec">Terms</h2>' + _table(["code", "meaning"], rows, "wide")
            + f'<p class="s-note">Generated on {_e(generated)}.</p></footer>')


def render(data: dict[str, Any], generated: Optional[str] = None) -> str:
    generated = generated or datetime.date.today().isoformat()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    ll = data["task3"]["arms"][0]
    eyebrow = " · ".join(["Qwen3.8 Flash-Next", "Splash 1.5.0 vs 1.6.1", data["rig"],
                          f"{data['dates'][0]} to {data['dates'][1]}"])
    desc = (f"Splash 1.6.1 against 1.5.0 on a {data['rig']}: two 256K sessions are {_pct(ll['auto'], ll['old'])}, "
            "one stream and quality are the same, and the launcher switches to 1.6.1.")
    return "".join([
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n',
        f"<title>{_e(TITLE)}</title>\n",
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n',
        f'<meta name="description" content="{_e(desc)}">\n',
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700'
        '&display=swap">\n',
        f"<style>{S16.CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">\n",
        f'<header><div><p class="eyebrow">{_e(eyebrow)}</p><h1>{_e(TITLE)}</h1></div>'
        '<button class="theme" id="themeBtn" type="button">theme: auto</button></header>\n',
        _hero(data), "\n", _questions(data), "\n", _method_html(data), "\n", _footer(generated), "\n</div>\n",
        f'<script id="data" type="application/json">{payload}</script>\n',
        f"<script>{S16.THEME_JS}</script>\n</body>\n</html>\n",
    ])


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Render the public Splash 1.6.1 vs 1.5.0 report page.")
    p.add_argument("--results-dir", default=str(RESULTS))
    p.add_argument("--out-html", default=str(REPO / "reports" / "qwen38-flashnext-splash161.html"))
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    out = Path(args.out_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(collect(Path(args.results_dir))), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
