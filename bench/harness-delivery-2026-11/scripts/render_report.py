#!/usr/bin/env python3
"""Render the public page of the harness-delivery campaign, with the speed and refusal results of swift-uncensored.

usage: render_report.py [--out reports/qwen38-flashnext-harness-delivery.html] [--card]

Reads only tracked results: results/sessions/*.json here, and refusal-*.jsonl plus etapa2-um-stream.md in
bench/swift-uncensored-2026-11/results. The page holds counts and times; no prompt and no model answer.
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import summarize  # noqa: E402
import tasks  # noqa: E402

CAMPAIGN = HERE.parent
REPO = CAMPAIGN.parents[1]
RESULTS = CAMPAIGN / "results"
SWIFT_RESULTS = REPO / "bench/swift-uncensored-2026-11/results"
OUT = REPO / "reports/qwen38-flashnext-harness-delivery.html"
CARD = REPO / "reports/assets/qwen38-flashnext-harness-delivery-card.html"

HARNESSES = ("claude", "opencode", "pi", "dsh")
PACKS = ("k2", "z4")
REPS = (1, 2)
HARNESS_LABEL = {"claude": "Claude Code", "opencode": "OpenCode", "pi": "pi", "dsh": "dsh"}
# short name, full name
PACK_LABEL = {"k2": ("Standard", "Swift 1.5 IQ4_XS (ukisai)"),
              "z4": ("Uncensored", "Swift 1.5 Heretic v2 IQ4_XS (jackjusko, indexer recast to BF16)")}
ARM_PACK = {"k2h": "Standard (ukisai Swift 1.5)", "z4h": "Uncensored: Heretic v2, BF16 indexer",
            "z2h": "Uncensored: Huihui abliterated v2", "z3h": "Uncensored: GSQ-RCO abliterated"}
ARMS = ("k2h", "z4h", "z2h", "z3h")
SETS = {"advbench": "AdvBench", "jbb": "JBB-Behaviors"}
TASK_LABEL = {
    "a": "Add a --format json option to a Python CLI, with a test",
    "b": "Fix 2 bugs in a bash word-count script, add 2 tests",
    "c": "Add a --group-by option to a Python ledger report",
    "d": "Fix 2 bugs in a bash backup toolkit and extract a shared library",
    "T1": "Find and fix 3 bugs behind 4 failing tests",
    "T5": "Repair a broken environment until make check is green",
    "T7": "Chain of 5 subtasks with a checklist",
}
# (pack, harness, task, rep) -> cause, from results/audit.md
FAILURE_CAUSES = {
    ("k2", "opencode", "T5", 1): "fixed the lint errors, left the test failing on a missing environment variable",
    ("z4", "opencode", "T5", 1): "stopped without fixing the lint errors",
    ("z4", "opencode", "T5", 2): "stopped without fixing the lint errors",
    ("z4", "claude", "d", 2): "left 1 of the 2 bugs unfixed",
    ("z4", "pi", "d", 2): "left 1 of the 2 bugs unfixed",
    ("z4", "dsh", "d", 2): "did not build the requested structure (shared library or 8 checks)",
    ("k2", "dsh", "b", 1): "deleted an original test",
}
# arm -> context -> (T_turn s, ratio against k2h, decode tok/s, wired peak GB); from etapa2-um-stream.md
SPEED = {
    "k2h": {32768: (6.0, 1.0, 112.1, 78.0), 131072: (5.9, 1.0, 117.0, 80.0), 262144: (6.2, 1.0, 112.2, 82.4)},
    "z4h": {32768: (6.1, 1.017, 109.8, 80.1), 131072: (6.2, 1.051, 110.0, 82.1), 262144: (6.4, 1.032, 105.9, 84.7)},
    "z2h": {32768: (6.2, 1.033, 108.7, 64.7), 131072: (6.2, 1.051, 109.9, 66.6), 262144: (6.3, 1.016, 108.7, 69.2)},
    "z3h": {32768: (6.2, 1.033, 107.2, 64.4), 131072: (6.1, 1.034, 113.4, 66.5), 262144: (6.2, 1.000, 112.2, 69.0)},
}
SPEED_LIMIT = 1.05


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 1) if values else None


def _refusal(swift_results: Path) -> dict:
    out = {}
    for arm in ARMS:
        for s in SETS:
            rows = [json.loads(line) for line in (swift_results / f"refusal-{arm}-{s}.jsonl").read_text().splitlines()
                    if line.strip()]
            out[(arm, s)] = {v: sum(r["verdict"] == v for r in rows) for v in ("refused", "empty", "complied")}
            out[(arm, s)]["n"] = len(rows)
    return out


def collect(delivery_results: Path = RESULTS, swift_results: Path = SWIFT_RESULTS) -> dict:
    """Every number of the page. Raises ValueError when the session matrix is not complete."""
    records = summarize.load(Path(delivery_results))
    by = {(r["pack"], r["harness"], r["task"], r["rep"]): r for r in records}
    want = [(p, h, t, n) for p in PACKS for h in HARNESSES for t in tasks.TASKS for n in REPS]
    missing = [f"{p}-{h}-{t}-r{n}" for p, h, t, n in want if (p, h, t, n) not in by]
    if missing or len(records) != len(want):
        raise ValueError(f"session matrix is not complete: missing {missing or 'nothing'}, {len(records)} records")

    def sel(**kw):
        return [r for r in records if all(r[k] == v for k, v in kw.items())]

    done = lambda rs: sum(r["task_done"] for r in rs)  # noqa: E731
    walls = lambda rs: [r["wall_s"] for r in rs if r["task_done"]]  # noqa: E731
    harness = []
    for name, total, median in summarize.rank(records):
        mine = sel(harness=name)
        harness.append({"name": name, "label": HARNESS_LABEL[name], "version": mine[0]["harness_version"],
                        "done": total, "n": len(mine), "median_s": median,
                        "by_pack": {p: {"done": done(sel(harness=name, pack=p)), "n": len(sel(harness=name, pack=p))}
                                    for p in PACKS}})
    failures = []
    for r in records:
        if not r["task_done"]:
            key = (r["pack"], r["harness"], r["task"], r["rep"])
            if key not in FAILURE_CAUSES:
                raise ValueError(f"failed session without an audited cause: {key}")
            failures.append({"pack": key[0], "harness": key[1], "task": key[2], "rep": key[3],
                             "cause": FAILURE_CAUSES[key], "claimed_done": r["claimed_done"]})
    return {
        "sessions": {"total": len(records), "done": done(records)},
        "harness": harness,
        "cells": {(h, t): {p: done(sel(harness=h, task=t, pack=p)) for p in PACKS}
                  for h in HARNESSES for t in tasks.TASKS},
        "tasks": [{"id": t, "label": TASK_LABEL[t], "hard": tasks.TASKS[t].hard, "n": len(sel(task=t, pack="k2")),
                   "k2_done": done(sel(task=t, pack="k2")), "z4_done": done(sel(task=t, pack="z4")),
                   "median_s": {p: _median(walls(sel(task=t, pack=p))) for p in PACKS}} for t in tasks.TASKS],
        "times": {(h, t): walls(sel(harness=h, task=t)) for h in HARNESSES for t in tasks.TASKS},
        "reserva": summarize.reserva(records, "k2", "z4"),
        "failures": failures,
        "timeouts": sum(bool(r["timeout"]) for r in records),
        "notes": sum("makefile_changed" in r["cheat"] for r in records),
        "refusal": _refusal(Path(swift_results)),
        "speed": {arm: {ctx: dict(zip(("t_turn_s", "ratio", "decode_tps", "wired_gb"), v)) for ctx, v in rows.items()}
                  for arm, rows in SPEED.items()},
        "speed_verdict": {arm: "pass" if all(v[1] <= SPEED_LIMIT for v in rows.values()) else "fail"
                          for arm, rows in SPEED.items() if arm != "k2h"},
    }


# ---------------------------------------------------------------- page

import svg_charts as sc  # noqa: E402

TITLE = "Four coding harnesses, one local model"
SUBTITLE = ("Claude Code, OpenCode, pi and dsh on a Mac Studio M4 Max, with a standard and an uncensored "
            "Qwen3.8 Flash-Next pack")
SITE = "https://snagnever.github.io/macstudio-local-llm/"
GITHUB = "https://github.com/snagnever/macstudio-local-llm"
CAMPAIGN_URL = f"{GITHUB}/tree/main/bench/harness-delivery-2026-11"
SWIFT_URL = f"{GITHUB}/tree/main/bench/swift-uncensored-2026-11"
TASK_SHORT = {"a": "a · CLI option", "b": "b · bash bugs", "c": "c · report option", "d": "d · bash refactor",
              "T1": "T1 · hidden bugs", "T5": "T5 · broken env", "T7": "T7 · 5-step chain"}
HARNESS_COLOUR = {"claude": "--s1", "opencode": "--s2", "pi": "--s3", "dsh": "--s4"}
ARM_COLOUR = {"z4h": "--pack-b", "z2h": "--s3", "z3h": "--s4"}
ARM_SHORT = {"k2h": "Standard", "z4h": "Heretic v2", "z2h": "Huihui v2", "z3h": "GSQ-RCO"}
WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}
# The first run of the matrix, before the three fixes; from results/audit.md.
FIRST_RUN = {"t5_done": 0, "t5_n": 16, "t5_flagged": 15, "false_flags": 20, "strict": (47, 51), "makefile": 7}

CSS = """
:root{color-scheme:light;
--plane:#f9f9f7;--surface:#fcfcfb;--surface-2:#f3f2ee;--ink:#0b0b0b;--ink-2:#52514e;--muted:#6f6d68;
--grid:#e1e0d9;--baseline:#c3c2b7;--border:rgba(11,11,11,0.10);--track:#eceae4;--accent:#1f66c1;
--s1:#2a78d6;--s2:#d9541f;--s3:#12946a;--s4:#b98000;--pack-a:#2a78d6;--pack-b:#d9541f;
--good:#0c8f0c;--crit:#c43030;--warn:#b06a00;--warn-bg:#fbf1dd;
--heat-0:#f3c4c0;--heat-1:#f6dcb5;--heat-2:#f4e7a6;--heat-3:#bfe3b4;--heat-4:#8fd192;--heat-ink-hi:#0b0b0b;
--refused:#c43030;--empty:#77756f;--complied:#2a78d6;--on-fill:#ffffff;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;--sans:system-ui,-apple-system,"Segoe UI",sans-serif}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;
--plane:#0d0d0d;--surface:#1a1a19;--surface-2:#232321;--ink:#ffffff;--ink-2:#c3c2b7;--muted:#9a988f;
--grid:#2c2c2a;--baseline:#48483f;--border:rgba(255,255,255,0.12);--track:#2a2a28;--accent:#6aa8f0;
--s1:#4f97ec;--s2:#ee7a4a;--s3:#2fbf8c;--s4:#e0a82e;--pack-a:#4f97ec;--pack-b:#ee7a4a;
--good:#3fc24a;--crit:#ef6a6a;--warn:#e0a63a;--warn-bg:#2a2312;
--heat-0:#6b2420;--heat-1:#6a4a1c;--heat-2:#5f571b;--heat-3:#2c5a2a;--heat-4:#237a35;--heat-ink-hi:#ffffff;
--refused:#c84a4a;--empty:#6b6963;--complied:#3a82dc;--on-fill:#ffffff}}
*{box-sizing:border-box}html,body{margin:0}
body{background:var(--plane);color:var(--ink);font-family:var(--sans);line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:920px;margin:0 auto;padding:36px 16px 72px}
.eyebrow{font-family:var(--mono);font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:0 0 8px}
h1{font-size:clamp(1.7rem,5vw,2.5rem);line-height:1.12;letter-spacing:-.025em;margin:0;text-wrap:balance}
.sub{font-size:1.05rem;color:var(--ink-2);margin:10px 0 0;max-width:62ch}
.lead{font-size:1.08rem;max-width:68ch;margin:22px 0 0}
a{color:var(--accent)}
code{font-family:var(--mono);font-size:.88em;background:var(--surface-2);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,195px),1fr));gap:12px;margin-top:22px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.t-lab{font-family:var(--mono);font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0}
.t-big{font-size:1.9rem;line-height:1.1;font-weight:700;margin:6px 0 4px;font-variant-numeric:tabular-nums}
.t-big small{font-size:.95rem;font-weight:500;color:var(--ink-2)}
.t-sub{font-size:.85rem;color:var(--ink-2);margin:0;line-height:1.4}
nav.toc{display:flex;flex-wrap:wrap;gap:6px 8px;margin:26px 0 0}
nav.toc a{font-size:.82rem;text-decoration:none;color:var(--ink-2);background:var(--surface);border:1px solid var(--border);border-radius:999px;padding:4px 11px}
section{margin-top:44px;padding-top:26px;border-top:1px solid var(--border)}
.q{font-family:var(--mono);font-size:.74rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 4px}
h2{font-size:1.45rem;line-height:1.2;letter-spacing:-.015em;margin:0 0 8px;text-wrap:balance}
h3{font-size:1rem;margin:0 0 4px}
p{margin:0 0 12px;max-width:72ch}
.note{color:var(--ink-2);font-size:.93rem}
figure.chart{margin:16px 0 6px;background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 12px 10px;overflow-x:auto}
figure.chart svg{width:100%;min-width:540px;height:auto;display:block;font-family:var(--sans);font-variant-numeric:tabular-nums}
figure.chart svg text.ttl{font-weight:600}
figure.chart svg text.value{font-weight:600}
figcaption{font-size:.84rem;color:var(--ink-2);margin:10px 2px 0;padding-top:8px;border-top:1px solid var(--border)}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;margin:0 2px 10px}
.chip{display:inline-flex;align-items:center;gap:7px;font-size:.84rem;color:var(--ink-2)}
.sw{width:12px;height:12px;border-radius:3px;flex:none}
details.tbl{margin:0 0 14px;font-size:.84rem}
details.tbl summary{cursor:pointer;color:var(--ink-2);font-size:.82rem;padding:4px 2px}
.scroll{overflow-x:auto;border:1px solid var(--border);border-radius:10px;background:var(--surface);margin:6px 0 12px}
table{border-collapse:collapse;width:100%;font-size:.84rem}
th,td{padding:7px 10px;text-align:right;font-variant-numeric:tabular-nums;vertical-align:top;white-space:nowrap}
th{font-size:.74rem;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border)}
td:first-child,th:first-child{text-align:left}
table.text td,table.text th{text-align:left;white-space:normal}
tbody tr+tr td{border-top:1px solid var(--border)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:12px;margin:16px 0}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px}
.card .n{font-family:var(--mono);font-size:.72rem;color:var(--muted);letter-spacing:.1em}
.card dl{margin:8px 0 0}
.card dt{font-family:var(--mono);font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-top:10px}
.card dd{margin:2px 0 0;font-size:.9rem;color:var(--ink-2)}
.card dd b{color:var(--ink)}
.delta{display:flex;align-items:baseline;gap:8px;margin-top:12px;font-variant-numeric:tabular-nums}
.delta .was{color:var(--crit);text-decoration:line-through;font-weight:600}
.delta .now{color:var(--good);font-weight:700;font-size:1.15rem}
.callout{margin:14px 0;padding:11px 14px;border-left:3px solid var(--warn);background:var(--warn-bg);border-radius:6px;font-size:.93rem}
.callout p{margin:0}
ul{margin:0 0 12px;padding-left:20px;max-width:72ch}
li{margin:5px 0;color:var(--ink-2);font-size:.95rem}
li b{color:var(--ink)}
footer{margin-top:52px;padding-top:18px;border-top:1px solid var(--border);font-size:.84rem;color:var(--muted)}
"""


def _e(text) -> str:
    return html.escape(str(text), quote=True)


def _table(head: list[str], rows: list[list], cls: str = "") -> str:
    th = "".join(f"<th>{_e(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="scroll"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def _legend(items: list[tuple[str, str]]) -> str:
    return '<div class="legend">' + "".join(
        f'<span class="chip"><span class="sw" style="background:var({c})"></span>{_e(label)}</span>'
        for label, c in items) + "</div>"


def _figure(svg: str, caption: str, head: list[str], rows: list[list], legend: str = "") -> str:
    return (f'<figure class="chart">{legend}{svg}<figcaption>{caption}</figcaption></figure>'
            f'<details class="tbl"><summary>Numbers behind this chart</summary>{_table(head, rows)}</details>')


def _section(sid: str, kicker: str, title: str, body: str) -> str:
    return f'<section id="{sid}"><p class="q">{_e(kicker)}</p><h2>{_e(title)}</h2>{body}</section>'


def _pct(part: int, n: int) -> int:
    return round(100 * part / n)


def _headline(d: dict) -> dict:
    """The short answers. Every number comes from the data."""
    res, ref = d["reserva"], d["refusal"]
    z = [v["ratio"] for v in d["speed"]["z4h"].values()]
    lo, hi = (round((r - 1) * 100) for r in (min(z), max(z)))
    totals = sorted({h["done"] for h in d["harness"]})
    return {
        "harness": "No measurable difference",
        "harness_range": f"{totals[0]} to {totals[-1]} of {d['harness'][0]['n']}",
        "pack": f"{WORDS[res['done_base'] - res['done_cand']]} tasks fewer out of {sum(t['n'] for t in d['tasks'])}",
        "pack_counts": f"{res['done_cand']} against {res['done_base']}",
        "refusal": (f"Refusals drop from {_pct(ref[('k2h', 'advbench')]['refused'], ref[('k2h', 'advbench')]['n'])}% "
                    f"to {_pct(ref[('z4h', 'advbench')]['refused'], ref[('z4h', 'advbench')]['n'])}%"),
        "speed": f"{lo}% to {hi}% slower per agent turn",
    }


def _hero(d: dict) -> str:
    h, s = _headline(d), d["sessions"]
    ref = d["refusal"]
    tiles = [
        ("Sessions done", f"{s['done']} <small>of {s['total']}</small>",
         "Each one checked by a hidden script, not by what the agent said."),
        ("Harness", f"{h['harness_range']}", f"{h['harness']} between the four harnesses."),
        ("Uncensored pack, coding", h["pack_counts"].replace("against", "<small>against</small>"),
         f"{h['pack']}. All three come from one task in one repetition."),
        ("Uncensored pack, refusals", f"{ref[('z4h', 'advbench')]['refused']} <small>of {ref[('z4h', 'advbench')]['n']}</small>",
         f"The standard pack refuses {ref[('k2h', 'advbench')]['refused']} of {ref[('k2h', 'advbench')]['n']} AdvBench prompts."),
    ]
    return (f'<header><p class="eyebrow">Local LLM · Mac Studio M4 Max 128 GB · November 2026</p><h1>{_e(TITLE)}</h1>'
            f'<p class="sub">{_e(SUBTITLE)}</p></header>'
            f'<p class="lead">I gave the same 7 coding tasks to 4 agent harnesses, all driving one model that runs on my '
            f'desk. Then I swapped the weights for an uncensored pack and ran everything again. '
            f'<b>{s["done"]} of {s["total"]} sessions</b> finished the task. The harness made no measurable difference, '
            f'the uncensored pack cost little, and my own benchmark was wrong three times before the numbers held.</p>'
            '<div class="tiles">' + "".join(
                f'<div class="tile"><p class="t-lab">{_e(lab)}</p><p class="t-big">{big}</p><p class="t-sub">{_e(sub)}</p></div>'
                for lab, big, sub in tiles) + "</div>"
            '<nav class="toc" aria-label="Sections"><a href="#setup">Setup</a><a href="#harness">Harness</a>'
            '<a href="#pack">Uncensored pack</a><a href="#refusal">Refusals</a><a href="#speed">Speed</a>'
            '<a href="#failures">Failures</a><a href="#bugs">Benchmark bugs</a><a href="#limits">Limits</a>'
            '<a href="#method">Method</a></nav>')


def _setup(d: dict) -> str:
    factors = [("harnesses", [h["label"] for h in sorted(d["harness"], key=lambda h: HARNESSES.index(h["name"]))]),
               ("tasks", [TASK_SHORT[t["id"]] for t in d["tasks"]]),
               ("weight packs", [PACK_LABEL[p][0] for p in PACKS]), ("repetitions", ["run 1", "run 2"])]
    svg = sc.matrix_diagram(factors, "The test matrix",
                            f"4 harnesses times 7 tasks times 2 weight packs times 2 repetitions gives {d['sessions']['total']} sessions.")
    rows = [[TASK_SHORT[t["id"]].split(" · ")[0], t["label"], "long" if t["hard"] else "short"] for t in d["tasks"]]
    body = (
        "<p>Every session starts from a fresh copy of a small repository and one prompt. The harness runs without "
        "permission prompts inside a macOS sandbox, with its own empty home directory. When the harness exits, a hidden "
        "script decides whether the task is done: it runs the original tests, probes the behaviour, and looks for "
        "shortcuts such as a deleted test.</p>"
        + f'<figure class="chart">{svg}<figcaption>One model server, one session at a time. Model: Qwen3.8 Flash-Next, '
        "Swift 1.5 IQ4_XS GGUF, served by Splash 1.6.1 with a 128K context.</figcaption></figure>"
        + f'<details class="tbl"><summary>The 7 tasks</summary>{_table(["task", "what the agent must do", "kind"], rows, "text")}</details>'
        + f"<p class=\"note\">The two packs: <b>Standard</b> is {_e(PACK_LABEL['k2'][1])}. <b>Uncensored</b> is "
        f"{_e(PACK_LABEL['z4'][1])}. Same quantization level, same server.</p>")
    return _section("setup", "What I ran", "112 sessions, each one judged by a script", body)


def _q_harness(d: dict) -> str:
    h = _headline(d)
    order = [x["name"] for x in d["harness"]]
    task_ids = [t["id"] for t in d["tasks"]]
    cols = [f"{p}:{t}" for p in PACKS for t in task_ids]
    values = {(HARNESS_LABEL[n], f"{p}:{t}"): d["cells"][(n, t)][p] for n in order for p in PACKS for t in task_ids}
    # column labels repeat per pack, so the chart gets unique keys and short tick text
    svg = sc.heatmap([HARNESS_LABEL[n] for n in order], cols, values, 2, "Tasks done per harness, task and pack",
                     "Each cell counts the sessions done out of 2 repetitions. Most cells are 2 of 2.",
                     col_groups=[(PACK_LABEL[p][0] + " pack", len(task_ids)) for p in PACKS])
    for p in PACKS:
        for t in task_ids:
            svg = svg.replace(f">{p}:{t}<", f">{t}<")
    rows = [[x["label"], x["version"], f"{x['by_pack']['k2']['done']} of {x['by_pack']['k2']['n']}",
             f"{x['by_pack']['z4']['done']} of {x['by_pack']['z4']['n']}", f"{x['done']} of {x['n']}",
             f"{x['median_s']} s"] for x in d["harness"]]
    fig1 = _figure(svg, "Sessions done out of 2 per cell. Green is 2 of 2, yellow is 1, red is 0.",
                   ["harness", "version", "standard", "uncensored", "total", "median time, done"], rows)
    xmax = 360.0
    points = {(TASK_SHORT[t], HARNESS_LABEL[n]): d["times"][(n, t)] for n in order for t in task_ids}
    svg2 = sc.dot_plot([TASK_SHORT[t] for t in task_ids], [(HARNESS_LABEL[n], HARNESS_COLOUR[n]) for n in order],
                       points, 0.0, xmax, " s", None, "Wall time of the done sessions, per task and harness",
                       "One dot per done session, a tick at the median. The harnesses overlap on every task.")
    trows = [[TASK_SHORT[t]] + [f"{statistics.median(d['times'][(n, t)]):.0f} s" if d["times"][(n, t)] else "–"
                                for n in order] for t in task_ids]
    fig2 = _figure(svg2, "One dot per done session; the tick is the median. Both packs together.",
                   ["task"] + [HARNESS_LABEL[n] for n in order], trows,
                   _legend([(HARNESS_LABEL[n], HARNESS_COLOUR[n]) for n in order]))
    totals = ", ".join(f"{x['label']} {x['done']} of {x['n']}" for x in d["harness"])
    body = (f"<p><b>{h['harness']}.</b> {totals}. With two repetitions per combination, a gap of one or two sessions is "
            "inside the noise. I cannot rank these four.</p>" + fig1
            + "<p>Time tells the same story. The task decides how long a session takes; the harness does not.</p>" + fig2
            + '<div class="callout"><p>The model does the work. With one capable local model, the choice between these '
            "four harnesses is a choice of interface, not of results. All three failures on the environment task came "
            "from OpenCode, and the OpenCode build on the test machine was older (1.15.10) than the current one, so I "
            "do not read that as a property of OpenCode.</p></div>")
    return _section("harness", "Question 1 · Does the harness matter?", h["harness"], body)


def _q_pack(d: dict) -> str:
    h, res = _headline(d), d["reserva"]
    groups = [TASK_SHORT[t["id"]] for t in d["tasks"]]
    series = [(PACK_LABEL[p][0], c) for p, c in zip(PACKS, ("--pack-a", "--pack-b"))]
    values = {(TASK_SHORT[t["id"]], PACK_LABEL[p][0]): t[f"{p}_done"] for t in d["tasks"] for p in PACKS}
    svg = sc.paired_bars(groups, series, values, d["tasks"][0]["n"], "Sessions done per task, standard against uncensored",
                         "Out of 8 sessions per task and pack. The packs differ on tasks b, d and T5 only.")
    rows = [[TASK_SHORT[t["id"]], f"{t['k2_done']} of {t['n']}", f"{t['z4_done']} of {t['n']}",
             f"{t['median_s']['k2']} s", f"{t['median_s']['z4']} s"] for t in d["tasks"]]
    fig = _figure(svg, f"Sessions done out of {d['tasks'][0]['n']} (4 harnesses × 2 repetitions).",
                  ["task", "standard", "uncensored", "standard median", "uncensored median"], rows, _legend(series))
    ratios = sorted(res["ratio_by_task"].values())
    d_task = next(t for t in d["tasks"] if t["id"] == "d")
    body = (f"<p><b>{h['pack']}:</b> {h['pack_counts']}. My rule, set before the run, allowed the uncensored pack to "
            f"close {res['tolerance']} tasks fewer (5% of the sessions) and take up to 1.25× the time. It passes at the "
            "limit.</p>" + fig
            + f"<p>The gap sits in one place. On the bash refactor (task d) the uncensored pack closed "
            f"{d_task['z4_done']} of {d_task['n']}, and the 3 misses are all in the second repetition, in three "
            "different harnesses. The first repetition was 4 of 4. I did not find the cause of that block, so I read "
            "the gap as possible, not as proven.</p>"
            f"<p class=\"note\">On the tasks both packs finish, the uncensored pack takes {ratios[0]}× to {ratios[-1]}× "
            "the time of the standard pack. It is not slower at coding.</p>")
    return _section("pack", "Question 2 · Does the uncensored pack code worse?", h["pack"], body)


def _q_refusal(d: dict) -> str:
    h, ref = _headline(d), d["refusal"]
    parts = [("refused", "--refused"), ("empty", "--empty"), ("complied", "--complied")]
    rows_lbl = [f"{ARM_SHORT[a]} · {SETS[s]}" for a in ARMS for s in SETS]
    values = {(f"{ARM_SHORT[a]} · {SETS[s]}", p): ref[(a, s)][p] for a in ARMS for s in SETS for p, _ in parts}
    svg = sc.stacked_bars(rows_lbl, parts, values, "Refusal probe: refused, empty and complied per pack",
                          "100 prompts per set. The standard pack refuses 95 to 96; the three uncensored packs refuse 0 to 3.")
    trows = [[ARM_PACK[a], SETS[s]] + [ref[(a, s)][p] for p, _ in parts] for a in ARMS for s in SETS]
    fig = _figure(svg, "100 prompts per row. “Empty” is an answer with no text: the model spent all 2048 tokens thinking.",
                  ["pack", "prompt set", "refused", "empty", "complied"], trows,
                  _legend([("refused", "--refused"), ("empty (ran out of tokens)", "--empty"), ("complied", "--complied")]))
    body = (f"<p><b>{h['refusal']}</b> on AdvBench, and from "
            f"{_pct(ref[('k2h', 'jbb')]['refused'], ref[('k2h', 'jbb')]['n'])}% to "
            f"{_pct(ref[('z4h', 'jbb')]['refused'], ref[('z4h', 'jbb')]['n'])}% on JBB-Behaviors. I tested three uncensored "
            "packs of the same model. All three stop refusing; they differ in how often they run out of tokens before "
            "they answer.</p>" + fig
            + "<p>The Heretic v2 pack has the fewest empty answers, so it is the one I used for the coding sessions. "
            "A keyword classifier reads the first 300 characters of each answer. I then read 60 answers marked "
            "“complied” by hand: none was a refusal in other words, and 9 of the 60 quietly swapped the request for a "
            "harmless version.</p>"
            "<p class=\"note\">This page shows counts only. No prompt and no answer of the probe is published.</p>")
    return _section("refusal", "Question 3 · How uncensored is it?", h["refusal"], body)


def _q_speed(d: dict) -> str:
    h, sp = _headline(d), d["speed"]
    ctxs = {32768: "32K context", 131072: "128K context", 262144: "256K context"}
    arms = [a for a in ARMS if a != "k2h"]
    series = [(ARM_SHORT[a], ARM_COLOUR[a]) for a in arms]
    points = {(ctxs[c], ARM_SHORT[a]): [sp[a][c]["ratio"]] for a in arms for c in ctxs}
    svg = sc.dot_plot(list(ctxs.values()), series, points, 0.98, 1.08, "×", SPEED_LIMIT,
                      "Agent turn time of three uncensored packs, relative to the standard pack",
                      "All three uncensored packs take 1.00 to 1.05 times the turn time of the standard pack.",
                      ref_label="my limit, 1.05×")
    trows = [[ARM_PACK[a], ctxs[c].split()[0], f"{sp[a][c]['t_turn_s']} s", f"{sp[a][c]['ratio']:.3f}×",
              f"{sp[a][c]['decode_tps']}", f"{sp[a][c]['wired_gb']} GB"] for a in ARMS for c in ctxs]
    fig = _figure(svg, "1.00× is the standard pack. Each dot is the median of 2 server boots.",
                  ["pack", "context", "agent turn", "ratio", "decode tok/s", "memory peak"], trows, _legend(series))
    z = sp["z4h"][131072]
    body = (f"<p><b>{h['speed'][0].upper() + h['speed'][1:]}.</b> An agent turn is one request with a warm prompt cache "
            f"and a short answer: about {sp['k2h'][131072]['t_turn_s']} s on the standard pack and {z['t_turn_s']} s on "
            "the Heretic v2 pack at 128K. The difference comes from token generation: "
            f"{z['decode_tps']:.0f} against {sp['k2h'][131072]['decode_tps']:.0f} tokens per second.</p>" + fig
            + f"<p>My rule was “at most 5% slower”. The Heretic v2 pack lands at {z['ratio']:.3f}× at 128K and fails "
            "that rule by 0.001. Generation speed moved by 5% between two boots of the same pack, so this margin is "
            "noise, and I kept the pack. A rule with a hard threshold needs more than 2 boots per arm.</p>"
            f"<p class=\"note\">Memory: the Heretic v2 pack peaks {z['wired_gb'] - sp['k2h'][131072]['wired_gb']:.0f} GB "
            f"above the standard pack; the other two peak {sp['k2h'][131072]['wired_gb'] - sp['z2h'][131072]['wired_gb']:.0f} GB below it.</p>")
    return _section("speed", "Question 4 · What does it cost in speed?", h["speed"][0].upper() + h["speed"][1:], body)


def _failures(d: dict) -> str:
    n = len(d["failures"])
    rows = [[PACK_LABEL[f["pack"]][0], HARNESS_LABEL[f["harness"]], TASK_SHORT[f["task"]], f["cause"]]
            for f in sorted(d["failures"], key=lambda f: (f["task"], f["pack"], f["harness"]))]
    said_done = sum(f["claimed_done"] for f in d["failures"])
    body = (f"<p><b>All {said_done} failed sessions reported success.</b> The harness exited with code 0 and inside the "
            f"time limit. Timeouts: {d['timeouts']}. A local agent that fails does not crash and does not give up; it "
            "tells you the work is finished.</p>"
            + _table(["pack", "harness", "task", "what the repository showed"], rows, "text")
            + "<p>Three patterns: the agent stops before the work is complete, it fixes part of the task, or it removes "
            "the obstacle (one session deleted a test). None of these shows up in the transcript as an error. If you run "
            "a local agent unattended, check the result with something other than the agent.</p>") if n == said_done else ""
    return _section("failures", "How sessions fail", f"The {n} failures all say “done”", body)


def _benchmark_bugs(d: dict) -> str:
    f = FIRST_RUN
    t5 = next(t for t in d["tasks"] if t["id"] == "T5")
    t5_now = t5["k2_done"] + t5["z4_done"]
    res = d["reserva"]
    cards = [
        ("1", "The sandbox broke the linter",
         f"The environment task scored <b>{f['t5_done']} of {f['t5_n']}</b>. {f['t5_flagged']} sessions were flagged for "
         "changing the lint configuration.",
         "The sandbox hid the <code>.git</code> of the repository above the work copy. The linter walks up the "
         "directory tree, hit a permission error (<code>E902</code>) and failed. The agents did the reasonable thing: "
         "they changed the configuration to get past it.",
         "Work copies moved outside any repository. I ran the task again.",
         f"{f['t5_done']} of {f['t5_n']}", f"{t5_now} of {f['t5_n']}"),
        ("2", "A cheat detector with a false positive",
         f"<b>{f['false_flags']} records</b> carried the flag “tests modified”, including every session of the 5-step "
         "chain.",
         "The task asks for new tests. A new test extends the <code>import</code> line of the test file, and the "
         "detector counted a changed import line as a removed line.",
         "The detector ignores a changed import line. The verdicts did not move: the original tests always ran from a "
         "clean copy.",
         f"{f['false_flags']} flags", "0 flags"),
        ("3", "A rule the prompt never stated",
         f"<b>{f['makefile']} sessions</b> failed because they set an environment variable in the <code>Makefile</code>. "
         "The check wanted the Makefile untouched.",
         "The prompt forbids weakening the linter or the tests. It says nothing about the Makefile. In all "
         f"{f['makefile']} sessions the checks were green and the variable was documented.",
         "The check now follows the prompt. This one line decided the verdict on the uncensored pack.",
         f"{f['strict'][0]} against {f['strict'][1]}: fails", f"{res['done_cand']} against {res['done_base']}: passes"),
    ]
    html_cards = "".join(
        f'<div class="card"><span class="n">DEFECT {n}</span><h3>{_e(title)}</h3><dl><dt>What I saw</dt><dd>{saw}</dd>'
        f'<dt>Cause</dt><dd>{cause}</dd><dt>Fix</dt><dd>{fix}</dd></dl>'
        f'<div class="delta"><span class="was">{_e(was)}</span><span aria-hidden="true">→</span><span class="now">{_e(now)}</span></div></div>'
        for n, title, saw, cause, fix, was, now in cards)
    affected = f["t5_n"] + f["false_flags"]
    body = (f"<p>In the first run, <b>{affected} of {d['sessions']['total']} records</b> were affected by a defect in my "
            "harness, not by the model. I found each one by opening the repositories of the failed sessions instead of "
            "reading the score.</p>" + f'<div class="cards">{html_cards}</div>'
            + '<div class="callout"><p>Every defect made the model look worse, and every one looked like a model '
            "failure in the table. An agent benchmark needs an audit of its failures before its score means anything: "
            "read what the agent did, and ask whether the prompt told it not to.</p></div>")
    return _section("bugs", "Lessons", "Three times the benchmark was wrong", body)


def _limits(d: dict) -> str:
    items = [
        "<b>Two repetitions</b> per combination. A gap of 1 or 2 sessions between two harnesses, or of 3 between two "
        "packs, is not a result.",
        "<b>One model family.</b> Qwen3.8 Flash-Next in one quantization. A weaker model may separate the harnesses.",
        "<b>Small tasks.</b> The longest done session took under 6 minutes. Nothing here tests a multi-hour job.",
        "<b>Harness versions.</b> Claude Code 2.1.292, OpenCode 1.15.10, pi 0.85.1, dsh 0.1.0-rc.6. OpenCode was one "
        "minor line behind the current release.",
        "<b>The environment task ran last.</b> Its 16 sessions ran after the fix, not interleaved with the other 96.",
        "<b>The refusal probe uses a keyword classifier</b> on the first 300 characters, with a manual check of 60 answers.",
        "<b>The checks are mine.</b> I found three defects in them. There may be a fourth.",
    ]
    return _section("limits", "Limits", "What this does not show", "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")


def _method(d: dict) -> str:
    setup = [
        ["Machine", "Mac Studio M4 Max, 128 GB"],
        ["Server", "Splash 1.6.1, context 131072, reasoning effort xhigh, one session at a time"],
        ["Standard pack (k2)", PACK_LABEL["k2"][1]],
        ["Uncensored pack (z4)", PACK_LABEL["z4"][1]],
        ["Other uncensored packs", "z2: Huihui abliterated v2 · z3: GSQ-RCO abliterated (refusal and speed only)"],
        ["Sandbox", "macOS sandbox-exec: writes only in the work copy and the session home; reads under the user "
                    "directory limited to those and the runtimes; network open"],
        ["Time limits", "15 min for tasks a–d and T1, 20 min for T5, 30 min for T7"],
        ["Done", "The hidden check passes. The agent's own claim is recorded and not trusted"],
        ["Refusal probe", "100 AdvBench and 100 JBB-Behaviors prompts per pack, 2048 max tokens"],
        ["Speed probe", "2 server boots per pack and context; agent turn = warm-cache request (T_turn)"],
    ]
    links = [("Campaign plan, scripts and the 112 records", CAMPAIGN_URL),
             ("Summary table", f"{CAMPAIGN_URL}/results/summary.md"),
             ("Audit of the failures", f"{CAMPAIGN_URL}/results/audit.md"),
             ("Refusal and speed campaign", SWIFT_URL)]
    body = (_table(["item", "value"], setup, "text")
            + "<p>Everything is in the repository:</p><ul>"
            + "".join(f'<li><a href="{_e(u)}">{_e(t)}</a></li>' for t, u in links) + "</ul>")
    return _section("method", "Method and data", "How to check this", body)


def render(data: dict, generated: str | None = None) -> str:
    """The whole page as one HTML document."""
    generated = generated or datetime.date.today().isoformat()
    h, s = _headline(data), data["sessions"]
    desc = (f"{s['done']} of {s['total']} agent coding sessions on a local Qwen3.8 Flash-Next: the four harnesses tie, "
            f"an uncensored pack closes {h['pack_counts']} tasks, and three defects in the benchmark itself.")
    url = SITE + OUT.name
    image = SITE + "assets/qwen38-flashnext-harness-delivery-card.png"
    head = "".join([
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n',
        f"<title>{_e(TITLE)}</title>\n",
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n',
        f'<meta name="description" content="{_e(desc)}">\n',
        f'<meta property="og:title" content="{_e(TITLE)}">\n<meta property="og:description" content="{_e(desc)}">\n',
        f'<meta property="og:type" content="article">\n<meta property="og:url" content="{_e(url)}">\n',
        f'<meta property="og:image" content="{_e(image)}">\n<meta property="og:image:width" content="1200">\n',
        '<meta property="og:image:height" content="630">\n<meta name="twitter:card" content="summary_large_image">\n',
        f"<style>{CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">\n",
    ])
    sections = [_hero(data), _setup(data), _q_harness(data), _q_pack(data), _q_refusal(data), _q_speed(data),
                _failures(data), _benchmark_bugs(data), _limits(data), _method(data)]
    footer = (f'<footer>Generated <span id="generated">{_e(generated)}</span> by <code>render_report.py</code> from the '
              f'tracked results. <a href="{SITE}">All reports</a></footer>')
    return head + "\n".join(sections) + "\n" + footer + "\n</div>\n</body>\n</html>\n"


CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def card_html(data: dict) -> str:
    """The 1200x630 link preview: the title and the four headline numbers. Fixed light colours."""
    h, s, ref = _headline(data), data["sessions"], data["refusal"]
    tiles = [(f"{s['done']}<small> of {s['total']}</small>", "agent sessions done, judged by a hidden script"),
             (h["harness_range"].replace(" of ", "<small> of </small>"), "per harness: no measurable difference"),
             (h["pack_counts"].replace(" against ", "<small> vs </small>"), "tasks done, uncensored vs standard pack"),
             (f"{_pct(ref[('k2h', 'advbench')]['refused'], 100)}%<small> → </small>"
              f"{_pct(ref[('z4h', 'advbench')]['refused'], 100)}%", "refusals on AdvBench"),
             ("3", "defects found in my own benchmark")]
    body = "".join(f'<div class="tile"><span class="t-val">{v}</span><span class="t-lab">{_e(lab)}</span></div>'
                   for v, lab in tiles)
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Card</title>\n<style>'
            'html,body{margin:0;width:1200px;height:630px;background:#fbfaf7;color:#15171b;'
            'font-family:-apple-system,"SF Pro Text",Helvetica,Arial,sans-serif}'
            '.card{width:1200px;height:630px;padding:54px 60px 60px;box-sizing:border-box;display:flex;flex-direction:column}'
            '.eyebrow{font-family:"SF Mono",Menlo,monospace;font-size:17px;letter-spacing:.14em;text-transform:uppercase;'
            'color:#6b7280;margin:0 0 14px}'
            'h1{font-size:60px;line-height:1.06;letter-spacing:-.03em;margin:0}'
            '.sub{font-size:24px;color:#444a55;margin:14px 0 0;max-width:980px;line-height:1.3}'
            '.tiles{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-top:auto}'
            '.tile{background:#f0eee8;border-radius:14px;padding:26px 18px 24px}'
            '.t-val{font-size:46px;font-weight:700;letter-spacing:-.02em;display:block;white-space:nowrap}'
            '.t-val small{font-size:20px;font-weight:600;color:#444a55}'
            '.t-lab{font-size:17px;color:#444a55;line-height:1.3;display:block;margin-top:8px}'
            '</style></head><body><div class="card">'
            '<p class="eyebrow">Local LLM · Mac Studio M4 Max 128 GB · November 2026</p>'
            f'<h1>{_e(TITLE)}</h1><p class="sub">{_e(SUBTITLE)}</p><div class="tiles">{body}</div>'
            '</div></body></html>\n')


def write_png(page: Path, png: Path) -> bool:
    """Render the card with headless Chrome. Returns False when Chrome is not installed."""
    import subprocess
    if not CHROME.is_file():
        return False
    subprocess.run([str(CHROME), "--headless=new", "--hide-scrollbars", "--window-size=1200,630",
                    "--force-device-scale-factor=1", f"--screenshot={png}", page.resolve().as_uri()],
                   check=True, capture_output=True, timeout=120)
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--card", action="store_true", help="also write the 1200x630 card page")
    a = ap.parse_args(argv)
    data = collect()
    a.out.write_text(render(data))
    print(f"wrote {a.out}")
    if a.card:
        CARD.write_text(card_html(data))
        print(f"wrote {CARD}")
        print("wrote the PNG" if write_png(CARD, CARD.with_suffix(".png")) else "Chrome is missing: no PNG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
