#!/usr/bin/env python3
"""Render reports/qwen38-flashnext-effort-tail.html from the Task 3, 11, 12 and 15 results.

The page compares the official chat template (effort line at the top of the prompt) with the effort-tail template
(effort line as the last system block) on the Swift 1.5 pack (w1 / w1t) and on the iQ-MLX pack (n2 / n2t):
effort switch at 128K (probe 3e), prefix reuse on short prompts (probe 3f), effort obedience, and time, tokens and
accuracy per effort on GPQA-Diamond and LiveCodeBench.

LiveCodeBench rows graded by the old runner are regraded from e3d-lcb-regrade.json (w1) and from the Swift
campaign's lcb-regrade.json (n2 xhigh). The other runs come from bench2 at 2403125, which already has the fix.

usage: render_effort_tail_page.py [--out reports/qwen38-flashnext-effort-tail.html]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE.parent
REPO = CAMPAIGN.parents[1]
RES = CAMPAIGN / "results"
SWIFT_RES = REPO / "bench" / "swift15-flashnext-2026-10" / "results"
OUT = REPO / "reports" / "qwen38-flashnext-effort-tail.html"

EFFORTS = ("xhigh", "medium", "low")
SUITES = {"gpqa": "GPQA-Diamond", "livecodebench": "LiveCodeBench v6"}
ARMS = {
    "w1": ("Swift 1.5", "official", "s1"),
    "w1t": ("Swift 1.5", "effort tail", "s2"),
    "n2": ("iQ-MLX", "official", "s3"),
    "n2t": ("iQ-MLX", "effort tail", "s4"),
}
PACKS = (("Swift 1.5", "w1", "w1t"), ("iQ-MLX", "n2", "n2t"))
MAX_TOKENS = 65536


# ---------- data ----------

def rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def battery_paths(arm: str, effort: str) -> list[tuple[str, Path]]:
    """(round, dir) pairs for one arm and effort, in the order the page cites them."""
    if arm == "w1":
        return [(r, RES / "e3d" / "t1" / f"w1-{effort}-{r}") for r in ("r1", "r2")]
    if arm == "w1t":
        return [(r, RES / "e11" / "t1" / f"w1t-{effort}-{r}") for r in ("r1", "r2")]
    if arm == "n2" and effort == "xhigh":
        return [("r1", SWIFT_RES / "ab" / "t1" / "n2")]
    return [("r1", RES / "e15" / "t1" / f"{arm}-{effort}-r1")]


def regrade_map() -> dict[str, dict[int, bool]]:
    """Regraded LCB verdicts keyed by '<arm>-<effort>-<round>' then question_num; only for runs the old runner graded."""
    out: dict[str, dict[int, bool]] = {}
    e3d = json.loads((RES / "e3d-lcb-regrade.json").read_text())
    for key, items in e3d.items():
        run = key.split("/")[0]
        out[run] = {int(i["question_num"]): bool(i["regraded"]) for i in items}
    return out


def load_battery() -> dict:
    """battery[arm][effort][suite] = list of question dicts; two rounds are concatenated."""
    regrade = regrade_map()
    n2_fixed = set(json.loads((SWIFT_RES / "lcb-regrade.json").read_text())["n2-t1"]["fixed_by_regrade"])
    out: dict = {}
    for arm in ARMS:
        out[arm] = {}
        for effort in EFFORTS:
            out[arm][effort] = {s: [] for s in SUITES}
            for rnd, d in battery_paths(arm, effort):
                for suite in SUITES:
                    for r in rows(d / f"{suite}.jsonl"):
                        if r.get("error") not in (None, "", "None"):
                            continue
                        correct = bool(r["correct"])
                        if suite == "livecodebench":
                            run = f"{arm}-{effort}-{rnd}"
                            if run in regrade:
                                correct = regrade[run][int(r["question_num"])]
                            elif arm == "n2" and effort == "xhigh" and str(r.get("lcb_question_id")) in n2_fixed:
                                correct = True
                        out[arm][effort][suite].append({
                            "q": r["dataset_idx"], "round": rnd, "t": float(r["elapsed_s"]),
                            "tokens": int(r["total_tokens"] or 0), "reasoning": int(r["reasoning_tokens"] or 0),
                            "correct": correct, "trunc": r["finish_reason"] == "length",
                        })
    return out


def load_3e() -> dict[str, list[dict]]:
    return {arm: rows(RES / "agent" / f"3e-{arm}.jsonl") for arm in ("w1", "w1t", "n2t")}


def load_3f() -> dict[str, dict[str, list[dict]]]:
    src = {"w1": RES / "e3f" / "t1" / "w1-r1", "w1t": RES / "e11" / "t1" / "w1t-r1"}
    out: dict = {}
    for arm, d in src.items():
        out[arm] = {}
        for suite in ("jdhodges", "veerman"):
            out[arm][suite] = [{"id": r["case_id"], "t": float(r["turn_1_elapsed_s"]), "prompt": int(r["prompt_tokens"]),
                                "ok": bool(r["score_pass"])} for r in rows(d / f"{suite}.jsonl")]
    return out


def load_obedience() -> dict[str, dict]:
    return {"swift": json.loads((RES / "e11-obedience.json").read_text()),
            "iq": json.loads((RES / "e15-obedience.json").read_text())}


# ---------- stats ----------

def summary(qs: list[dict]) -> dict:
    n_rounds = len({q["round"] for q in qs})
    return {
        "n": len(qs), "rounds": n_rounds,
        "correct": sum(q["correct"] for q in qs), "trunc": sum(q["trunc"] for q in qs),
        "med_t": st.median(q["t"] for q in qs), "total_t": sum(q["t"] for q in qs),
        "med_tokens": st.median(q["tokens"] for q in qs), "total_tokens": sum(q["tokens"] for q in qs),
        "med_reasoning": st.median(q["reasoning"] for q in qs),
    }


def fmt_int(n: float) -> str:
    return f"{int(round(n)):,}"


def fmt_s(x: float) -> str:
    return f"{x:,.1f} s" if x < 100 else f"{x:,.0f} s"


def fmt_min(x: float) -> str:
    return f"{x / 60:,.0f} min"


def ratio_txt(d: dict) -> str:
    return f"×{math.exp(d['mean']):.2f} ({math.exp(d['lo']):.2f}–{math.exp(d['hi']):.2f})"


# ---------- html helpers ----------

def esc(s) -> str:
    return html.escape(str(s), quote=True)


def arm_lab(arm: str, with_pack: bool = False) -> str:
    pack, tpl, col = ARMS[arm]
    name = f"{pack} · {tpl}" if with_pack else tpl
    return f'<span class="arm-lab"><span class="sw" style="background:var(--{col})"></span>{esc(name)}</span>'


def legend(arms: list[str], extra: str = "", with_pack: bool = False) -> str:
    chips = "".join(f'<span class="chip">{arm_lab(a, with_pack)}</span>' for a in arms)
    return f'<div class="legend">{chips}{extra}</div>'


DOT_KEYS = ('<span class="chip"><span class="dotkey"></span> correct</span>'
            '<span class="chip"><span class="dotkey hollow"></span> wrong</span>'
            '<span class="chip"><span class="crosskey">×</span> hit the max_tokens limit</span>'
            '<span class="chip"><span class="medkey"></span> median</span>')


def strip_svg(series: list[tuple[str, list[dict]]], tmin: float, tmax: float, label: str,
              key: str = "t", unit: str = "s", hover=None) -> str:
    """Dot strip, log x. series = [(arm, questions)], one row per arm; a question dict has key, correct, trunc."""
    W, left, right = 440, 96, 14
    row_h, top = 34, 14
    H = top + row_h * len(series) + 30
    lo, hi = math.log10(tmin), math.log10(tmax)

    def x(v: float) -> float:
        return left + (math.log10(max(v, tmin)) - lo) / (hi - lo) * (W - left - right)

    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}">']
    ticks = [t for t in (0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000) if tmin <= t <= tmax]
    for t in ticks:
        out.append(f'<line class="gl" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top}" y2="{H - 26}"/>'
                   f'<text class="tick" x="{x(t):.1f}" y="{H - 12}" text-anchor="middle">{t:g}{unit}</text>')
    for i, (arm, qs) in enumerate(series):
        cy = top + row_h * i + row_h / 2
        pack, tpl, col = ARMS[arm]
        out.append(f'<text class="axis-t" x="4" y="{cy + 4:.1f}">{esc(tpl)}</text>')
        for q in qs:
            cx = x(q[key])
            title = hover(q) if hover else f"{tpl} · {q[key]:.1f}{unit}"
            if q.get("trunc"):
                out.append(f'<g class="dot trunc" style="--c:var(--{col})"><title>{esc(title)}</title>'
                           f'<path d="M{cx - 3.5:.1f} {cy - 3.5:.1f}l7 7M{cx + 3.5:.1f} {cy - 3.5:.1f}l-7 7"/></g>')
            else:
                cls = "dot" if q.get("correct", True) else "dot bad"
                out.append(f'<circle class="{cls}" style="--c:var(--{col})" cx="{cx:.1f}" cy="{cy:.1f}" r="4">'
                           f'<title>{esc(title)}</title></circle>')
        med = st.median(q[key] for q in qs)
        mx = x(med)
        out.append(f'<line class="med" x1="{mx:.1f}" x2="{mx:.1f}" y1="{cy - 12:.1f}" y2="{cy + 12:.1f}"/>'
                   f'<text class="medlab" x="{mx + 6:.1f}" y="{cy - 13:.1f}">{med:.1f}{unit}</text>')
    out.append("</svg>")
    return "".join(out)


def bar_group(label: str, items: list[tuple[str, float, str]], vmax: float | None = None, with_pack: bool = False) -> str:
    """items = [(arm, value, text)]."""
    vmax = vmax or max(v for _, v, _ in items) or 1
    lines = []
    for arm, v, text in items:
        col = ARMS[arm][2]
        lines.append(f'<div class="bline">{arm_lab(arm, with_pack)}<span class="btrack"><span class="bfill" '
                     f'style="width:{v / vmax * 100:.1f}%;background:var(--{col})" title="{esc(text)}"></span></span>'
                     f'<span class="bv">{esc(text)}</span></div>')
    return f'<div class="bgroup"><p class="b-lab">{esc(label)}</p>{"".join(lines)}</div>'


def card(head: str, note: str, body: str) -> str:
    return f'<figure class="card-chart"><p class="c-head">{head}</p><p class="c-note">{note}</p><div class="bars">{body}</div></figure>'


def interval_svg(rows_: list[tuple[str, str, float, float, float]], lo_x: float, hi_x: float, label: str,
                 band: tuple[float, float] | None = None, ticks=(0.25, 0.33, 0.5, 0.67, 1.0, 1.25),
                 left: int = 150) -> str:
    """Horizontal CI plot on a log axis. rows_ = [(arm, text, mean, lo, hi)] as factors."""
    W, right, row_h, top = 440, 14, 30, 12
    H = top + row_h * len(rows_) + 30
    llo, lhi = math.log(lo_x), math.log(hi_x)

    def x(v: float) -> float:
        return left + (math.log(v) - llo) / (lhi - llo) * (W - left - right)

    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}">']
    if band:
        out.append(f'<rect x="{x(band[0]):.1f}" y="{top}" width="{x(band[1]) - x(band[0]):.1f}" height="{H - 26 - top}" '
                   f'fill="var(--surface-2)"/>')
    for t in ticks:
        if lo_x <= t <= hi_x:
            out.append(f'<line class="gl" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top}" y2="{H - 26}"/>'
                       f'<text class="tick" x="{x(t):.1f}" y="{H - 12}" text-anchor="middle">×{t:g}</text>')
    out.append(f'<line x1="{x(1):.1f}" x2="{x(1):.1f}" y1="{top}" y2="{H - 26}" stroke="var(--baseline)" stroke-width="1.5"/>')
    for i, (arm, text, m, lo, hi) in enumerate(rows_):
        cy = top + row_h * i + row_h / 2
        col = ARMS[arm][2]
        out.append(f'<text class="axis-t" x="4" y="{cy + 4:.1f}">{esc(text)}</text>'
                   f'<line x1="{x(lo):.1f}" x2="{x(hi):.1f}" y1="{cy:.1f}" y2="{cy:.1f}" stroke="var(--{col})" stroke-width="3" stroke-linecap="round"/>'
                   f'<circle cx="{x(m):.1f}" cy="{cy:.1f}" r="5" fill="var(--{col})"/>'
                   f'<text class="medlab" x="{x(hi) + 7:.1f}" y="{cy + 4:.1f}">×{m:.2f}</text>')
    out.append("</svg>")
    return "".join(out)


# ---------- page ----------

CSS = """
:root{
  color-scheme: light;
  --plane:#f9f9f7; --surface:#fcfcfb; --surface-2:#f3f2ee;
  --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --baseline:#c3c2b7; --border:rgba(11,11,11,0.10);
  --accent:#2a78d6; --accent-rgb:42,120,214; --warn:#b06a00; --warn-bg:#fbf1dd;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4;
  --mono:"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
  --sans: system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --plane:#0d0d0d; --surface:#1a1a19; --surface-2:#232321;
    --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,0.10);
    --accent:#3987e5; --accent-rgb:57,135,229; --warn:#e0a63a; --warn-bg:#2a2312;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --plane:#0d0d0d; --surface:#1a1a19; --surface-2:#232321;
  --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,0.10);
  --accent:#3987e5; --accent-rgb:57,135,229; --warn:#e0a63a; --warn-bg:#2a2312;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--plane); color:var(--ink); font-family:var(--sans); line-height:1.5; -webkit-font-smoothing:antialiased}
.wrap{max-width:1180px; margin:0 auto; padding:32px 20px 64px}
header{display:flex; flex-wrap:wrap; gap:20px 32px; align-items:flex-end; justify-content:space-between}
h1{font-size:1.7rem; font-weight:700; letter-spacing:-0.02em; margin:0; text-wrap:balance}
.sub{color:var(--ink-2); max-width:66ch; margin:8px 0 0; font-size:0.98rem}
.eyebrow{font-family:var(--mono); font-size:0.72rem; letter-spacing:0.14em; text-transform:uppercase; color:var(--muted); margin:0 0 6px}
button.theme{font-family:var(--mono); font-size:0.74rem; color:var(--ink-2); background:var(--surface); border:1px solid var(--border); border-radius:7px; padding:7px 12px; cursor:pointer}
button.theme:hover{border-color:var(--baseline)}
button.theme:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
h2.sec{font-size:1.05rem; margin:0 0 4px; letter-spacing:-0.01em}
.s-note{color:var(--ink-2); font-size:0.88rem; margin:0 0 14px; max-width:82ch}
.s-note code,.notice code,footer code,.tbl-note code{font-family:var(--mono); font-size:0.9em; background:var(--surface-2); padding:1px 5px; border-radius:4px}
.s-note b{color:var(--ink)}
section.block{margin-top:30px}
a{color:var(--accent)}
.hero-lead{font-size:1.08rem; line-height:1.55; max-width:72ch; margin:18px 0 0; color:var(--ink)}
.tiles{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,150px),1fr)); gap:12px; margin-top:20px}
.tile{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px}
.tile .t-lab{font-family:var(--mono); font-size:0.68rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); margin:0}
.tile .t-big{font-size:2.2rem; line-height:1.1; font-weight:700; margin:6px 0 4px; color:var(--ink); font-variant-numeric:tabular-nums}
.tile .t-sub{font-size:0.84rem; color:var(--ink-2); margin:0; line-height:1.4}
.mt{margin-top:12px}
.u{color:var(--muted); font-size:0.9em; margin-left:2px}
.tbl-scroll{overflow-x:auto; border:1px solid var(--border); border-radius:10px; background:var(--surface)}
table{border-collapse:collapse; width:100%; font-size:0.84rem}
th,td{padding:8px 11px; text-align:right; font-variant-numeric:tabular-nums; font-family:var(--mono)}
th{font-size:0.72rem; letter-spacing:0.04em; color:var(--muted); font-weight:500; border-bottom:1px solid var(--border); position:sticky; top:0; background:var(--surface)}
td:first-child,th:first-child{text-align:left}
tbody tr:hover{background:var(--surface-2)}
td.nm, th.nm{font-family:var(--sans); text-align:left; color:var(--ink-2); font-size:0.84rem}
td.good{color:var(--s3)} td.badv{color:var(--s2)}
.arm-lab{display:inline-flex; align-items:center; gap:6px; white-space:nowrap; font-weight:600; color:var(--ink)}
.arm-lab .sw{width:10px; height:10px; border-radius:2px; flex:none}
.legend{display:flex; flex-wrap:wrap; gap:8px 18px; margin:14px 0 4px; padding:12px 16px; background:var(--surface); border:1px solid var(--border); border-radius:10px}
.chip{display:inline-flex; align-items:center; gap:7px; font-size:0.84rem; color:var(--ink-2)}
.dotkey{display:inline-block; width:10px; height:10px; border-radius:50%; background:var(--ink-2)}
.dotkey.hollow{background:transparent; border:1.5px solid var(--ink-2)}
.crosskey{font-weight:700; color:var(--ink-2); line-height:1}
.medkey{display:inline-block; width:3px; height:12px; background:var(--ink)}
.sgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr)); gap:14px; margin-top:14px}
figure.strip{margin:0; background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:12px 12px 10px}
.p-head{display:flex; justify-content:space-between; align-items:baseline; gap:10px; margin:0 2px 2px}
.p-title{font-size:0.98rem; font-weight:700; letter-spacing:-0.01em; margin:0}
.p-size{color:var(--muted); font-weight:400; font-size:0.84em}
.p-unit{font-family:var(--mono); font-size:0.72rem; color:var(--muted)}
.p-interp{font-size:0.8rem; color:var(--ink-2); margin:8px 2px 0; line-height:1.4; border-top:1px solid var(--border); padding-top:8px}
.p-interp b{color:var(--ink); font-weight:600}
svg.chart{width:100%; height:auto; display:block}
.tick{font-family:var(--mono); font-size:11px; fill:var(--muted)}
.axis-t{font-family:var(--mono); font-size:12px; font-weight:700; fill:var(--ink)}
.gl{stroke:var(--grid); stroke-width:1}
.dot{fill:var(--c); stroke:var(--c); stroke-width:1.2; fill-opacity:0.72}
.dot.bad{fill:var(--surface); fill-opacity:1; stroke-width:1.6}
g.dot.trunc path{stroke:var(--c); stroke-width:2.4; fill:none; stroke-linecap:round}
.med{stroke:var(--ink); stroke-width:2.5}
.medlab{font-family:var(--mono); font-size:12px; font-weight:700; fill:var(--ink); paint-order:stroke; stroke:var(--surface); stroke-width:3.5px; stroke-linejoin:round}
.cgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr)); gap:14px; margin-top:14px}
figure.card-chart{margin:0; background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:12px 14px}
.c-head{margin:0; font-weight:700; font-size:0.92rem}
.c-note{margin:3px 0 0; font-size:0.8rem; color:var(--muted)}
.bars{margin-top:8px}
.bgroup{margin-top:10px}
.b-lab{margin:0 0 4px; font-size:0.82rem; color:var(--ink-2)}
.bline{display:grid; grid-template-columns:minmax(96px,max-content) 1fr minmax(96px,auto); gap:8px; align-items:center; margin:2px 0}
.bline .arm-lab{font-size:0.8rem; font-weight:500}
.btrack{display:flex; gap:2px; height:12px}
.bfill{display:block; height:100%; border-radius:0 4px 4px 0; min-width:2px}
.bv{font-family:var(--mono); font-size:0.78rem; text-align:right; color:var(--ink); white-space:nowrap}
.takeaways{background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:14px 16px; margin-top:22px}
.takeaways h2{font-size:0.95rem; margin:0 0 9px; letter-spacing:-0.01em}
.takeaways ul{margin:0; padding:0; list-style:none; display:grid; gap:7px}
.takeaways li{font-size:0.85rem; color:var(--ink-2); padding-left:15px; position:relative; line-height:1.4}
.takeaways li::before{content:"›"; position:absolute; left:0; color:var(--accent); font-family:var(--mono); font-weight:700}
.takeaways li b{color:var(--ink)}
.notice{background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:12px 16px; font-size:0.88rem; color:var(--ink-2)}
.notice p{margin:0 0 6px} .notice ul{margin:0; padding-left:18px} .notice li{margin:4px 0}
.notice b{color:var(--ink)}
footer{margin-top:34px; color:var(--ink-2); font-size:0.82rem; max-width:82ch}
details > summary{cursor:pointer; list-style:none}
details > summary::-webkit-details-marker{display:none}
details > summary h2.sec{display:inline}
details > summary h2.sec::after{content:" ▸"; color:var(--muted)}
details[open] > summary h2.sec::after{content:" ▾"}
/* prompt layout diagram */
.prompt-diag{display:grid; gap:10px; margin-top:14px}
.prow{display:grid; grid-template-columns:120px 1fr; gap:10px; align-items:center}
.prow .pl{font-family:var(--mono); font-size:0.78rem; font-weight:700; color:var(--ink)}
.ptrack{display:flex; gap:3px; flex-wrap:wrap}
.pblk{font-family:var(--mono); font-size:0.72rem; padding:6px 9px; border-radius:6px; border:1px solid var(--border); background:var(--surface); color:var(--ink-2); white-space:nowrap; position:relative}
.pblk.eff{background:var(--warn-bg); color:var(--warn); border-color:var(--warn); font-weight:700}
.pblk.same{border-style:dashed}
.pblk.ckpt::after{content:"▲ checkpoint"; position:absolute; left:0; top:100%; font-size:0.62rem; color:var(--accent); white-space:nowrap; margin-top:1px}
.prompt-diag.ck .prow{margin-bottom:12px}
.diag-note{font-size:0.8rem; color:var(--ink-2); margin:6px 0 0}
@media (max-width:520px){.bline{grid-template-columns:80px 1fr minmax(80px,auto)} .tile .t-big{font-size:1.8rem} .prow{grid-template-columns:1fr}}
"""

JS = """
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
"""


def blk(text: str, cls: str = "") -> str:
    return f'<span class="pblk {cls}">{esc(text)}</span>'


def section_templates() -> str:
    official = "".join([blk("effort: xhigh", "eff"), blk("system", "same"), blk("tools", "same"),
                        blk("user: question", "same ckpt"), blk("assistant")])
    tail = "".join([blk("system", "same"), blk("tools", "same"), blk("user: question", "same"),
                    blk("effort: xhigh", "eff ckpt"), blk("assistant")])
    return f"""
<section class="block" id="templates"><h2 class="sec">The two templates</h2>
<p class="s-note">Qwen3.8-Flash-Next reads its thinking effort (<code>reasoning_effort</code>: <code>low</code>, <code>medium</code> or
<code>xhigh</code>) from one line in the prompt. The official chat template writes that line first. The
<a href="https://github.com/snagnever/macstudio-local-llm/blob/main/fixes/qwen3.8-flash-next/swift15-effort-tail.jinja">effort-tail template</a>
moves it to a short system block after the last message. Nothing else changes: at <code>medium</code> the two templates render the same prompt.</p>
<div class="prompt-diag ck">
<div class="prow"><span class="pl">official</span><span class="ptrack">{official}</span></div>
<div class="prow"><span class="pl">effort tail</span><span class="ptrack">{tail}</span></div>
</div>
<p class="diag-note">Dashed blocks are the part that stays equal between two requests of one session. <b>▲ checkpoint</b> marks where the server
saves the state it needs to restore a cached prefix; it sits at the start of the last message before <code>assistant</code>. This position was
inferred from the server logs, not read from the mlx-serve code.</p>
</section>"""


def section_switch(d3e: dict) -> str:
    # Group rows into runs of four steps (prime, control, switch, back), keyed by the effort of the switch row.
    runs: dict[str, dict[str, list[dict]]] = {}
    for arm, rs in d3e.items():
        cur: list[dict] = []
        for r in rs:
            cur.append(r)
            if r["step"] == "back":
                eff = next(x["reasoning_effort"] for x in cur if x["step"] == "switch")
                runs.setdefault(arm, {}).setdefault(eff, []).append({x["step"]: x for x in cur})
                cur = []

    def agg(arm: str, eff: str, step: str, key: str) -> float:
        return st.median(run[step][key] for run in runs[arm][eff])

    steps = [("control", "control: same effort"), ("switch", "switch: new effort"), ("back", "back to xhigh")]
    groups = []
    for eff in ("medium", "low"):
        items = [(arm, agg(arm, eff, "switch", "ttft_ms") / 1000,
                  f"{agg(arm, eff, 'switch', 'ttft_ms') / 1000:,.1f} s · hit {agg(arm, eff, 'switch', 'cache_hit_ratio'):.2f}")
                 for arm in ("w1", "w1t", "n2t")]
        groups.append(bar_group(f"xhigh → {eff}, time to first token", items, vmax=170))
    switch_card = card("Switching the effort at 128K", "Time to the first token of the turn that changes the effort. The prompt keeps the same 126K-token history.", "".join(groups))

    rows_ = []
    for step, label in steps:
        for arm in ("w1", "w1t", "n2t"):
            t = st.median(run[step]["ttft_ms"] for eff in runs[arm] for run in runs[arm][eff]) / 1000
            hit = st.median(run[step]["cache_hit_ratio"] for eff in runs[arm] for run in runs[arm][eff])
            rows_.append((arm, label, t, hit))
    tbl = "".join(f'<tr><td class="nm" style="white-space:nowrap">{esc(l)}</td><td>{arm_lab(a, True)}</td><td>{t:,.2f}</td><td>{h:.2f}</td></tr>'
                  for a, l, t, h in rows_)
    table = f"""<div class="tbl-scroll"><table><thead><tr><th class="nm">Turn</th><th class="nm">Pack · template</th><th>TTFT, s</th><th>cache hit</th></tr></thead><tbody>{tbl}</tbody></table></div>"""
    return f"""
<section class="block" id="switch"><h2 class="sec">Switching the effort in a long session</h2>
<p class="s-note">Probe 3e: a 128K-token conversation at <code>xhigh</code>, then one turn at <code>medium</code> or <code>low</code>, then back to <code>xhigh</code>.
With the official template the effort line is the first token of the prompt, so changing it invalidates the whole prefix cache and the server
re-reads 126K tokens: <b>167 s</b> before the first token. With the effort line at the tail, the history stays cached and the switch costs <b>0.8–5.8 s</b>.
Median of 2 rounds per switch; the iQ-MLX official template was not re-run here, since its prompt is identical to the Swift one.</p>
{legend(["w1", "w1t", "n2t"], with_pack=True)}
<div class="cgrid">{switch_card}<figure class="card-chart"><p class="c-head">All turns of the probe</p><p class="c-note">Median over the medium and low runs. The control turn pays more with the tail template: the server re-reads the text after its last checkpoint, which now sits before the effort block.</p>{table}</figure></div>
</section>"""


def section_short(d3f: dict) -> str:
    figs = []
    for suite, title, n in (("jdhodges", "Tool calling · jdhodges", 40), ("veerman", "Tool calling · Veerman", 12)):
        series = [(arm, [{"t": c["t"], "correct": c["ok"], "id": c["id"], "prompt": c["prompt"]} for c in d3f[arm][suite]])
                  for arm in ("w1", "w1t")]
        allt = [c["t"] for _, qs in series for c in qs]
        m1 = st.median(c["t"] for c in d3f["w1"][suite])
        m2 = st.median(c["t"] for c in d3f["w1t"][suite])
        svg = strip_svg(series, 0.9, max(allt) * 1.15, f"{title}, first turn time",
                        hover=lambda q: f"{q['id']} · {q['t']:.2f} s · prompt {q['prompt']} tokens")
        figs.append(f"""<figure class="strip"><div class="p-head"><p class="p-title">{esc(title)} <span class="p-size">{n} cases, xhigh, 1 round</span></p>
<span class="p-unit">median {m1:.1f} s → {m2:.1f} s</span></div>{svg}
<p class="p-interp">One dot per case: time of the first turn (the one that writes the tool call). Prompts are {min(c['prompt'] for c in d3f['w1'][suite]):,}–{max(c['prompt'] for c in d3f['w1'][suite]):,} tokens, same system prompt and tools in every case.</p></figure>""")
    return f"""
<section class="block" id="short"><h2 class="sec">Short prompts lose the prefix cache</h2>
<p class="s-note">Probe 3f, Swift 1.5: 55 tool-calling cases that share the system prompt and the tool list (600–1,200 tokens each). With the official template the
server reused the shared prefix in <b>53 of 55</b> requests. With the effort line at the tail it reused it in <b>0 of 55</b>: every request paid the full prefill,
<b>+0.9 to +1.4 s</b> on the first turn. Accuracy did not change (36→37 of 40, 10→10 of 12). This regression is why the tail template did not become the default.</p>
{legend(["w1", "w1t"], DOT_KEYS)}
<div class="sgrid">{"".join(figs)}</div>
<p class="s-note mt"><b>Why.</b> Qwen3.8-Flash-Next is a hybrid model: its attention layers keep one entry per token, but its Gated DeltaNet (SSM) layers keep one
state that summarizes everything read so far. To resume from a cached prefix the server needs a saved copy of that state, a checkpoint, inside the part of the
prompt that stayed equal. The logs show one checkpoint at the start of the last message. With the official template that message is the user question, right
after the shared prefix, so the checkpoint is inside it. With the tail template the last message is the effort block, after the question, so when the question
changes no checkpoint falls inside the equal part and the server starts cold (<code>hybrid miss (no checkpoint ≤ 555 of 618); cold prefill</code>). At 128K the
periodic checkpoints (<code>--ssm-checkpoint-stride</code>) fall inside the history, so long sessions do not have this problem.</p>
</section>"""


def section_obedience(ob: dict) -> str:
    rows_ = []
    for pack, key, base, cand in (("Swift 1.5", "swift", "w1", "w1t"), ("iQ-MLX", "iq", "n2", "n2t")):
        f = ob[key]["factor"]
        for arm in (base, cand):
            for eff in ("medium", "low"):
                d = f[arm][eff]  # factors are stored as ratios; shifts below are stored in log units
                rows_.append((arm, f"{pack} · {ARMS[arm][1]} · {eff}", d["mean"], d["lo"], d["hi"]))
    factor_svg = interval_svg(rows_, 0.18, 1.1, "Thinking tokens against xhigh", left=215, ticks=(0.25, 0.5, 0.67, 1.0))
    rows2 = []
    for pack, key, base, cand in (("Swift 1.5", "swift", "w1", "w1t"), ("iQ-MLX", "iq", "n2", "n2t")):
        s = ob[key]["shift"]
        for eff in EFFORTS:
            d = s[eff]
            rows2.append((cand, f"{pack} · {eff}" + (" (A/A)" if eff == "medium" else ""), math.exp(d["mean"]), math.exp(d["lo"]), math.exp(d["hi"])))
    shift_svg = interval_svg(rows2, 0.7, 1.45, "Thinking tokens, tail against official", band=(0.8, 1.25), ticks=(0.8, 1.0, 1.25))
    return f"""
<section class="block" id="obedience"><h2 class="sec">The model still obeys the effort line at the tail</h2>
<p class="s-note">Paired test on the same 100 questions (GPQA-Diamond 50 + LiveCodeBench 50): thinking tokens per question, geometric mean of the ratio,
90% bootstrap interval. Swift 1.5 has 2 rounds per arm; iQ-MLX has 1. The <code>medium</code> prompt is identical in both templates, so its ratio is an
A/A test that shows the noise floor.</p>
<div class="cgrid">
<figure class="card-chart"><p class="c-head">Thinking at medium and low, as a share of xhigh</p><p class="c-note">Per pack and template. Lower is less thinking.</p>{factor_svg}
<p class="p-interp"><b>iQ-MLX reacts more to the effort line than Swift 1.5.</b> At <code>low</code>, iQ-MLX thinks ×0.26 of its <code>xhigh</code>; Swift 1.5 thinks ×0.45. Swift 1.5 already thinks less at <code>xhigh</code>, so it has less to cut. The position of the line does not change these ratios.</p></figure>
<figure class="card-chart"><p class="c-head">Tail against official, same effort</p><p class="c-note">Shaded band: the ×0.80–×1.25 acceptance range of the campaign rule.</p>{shift_svg}
<p class="p-interp">Every interval sits inside the band. <b>Swift 1.5 at <code>low</code> thinks 10% less with the tail template</b> (×0.90, interval 0.86–0.94), outside the noise floor of the A/A (×0.98). At <code>xhigh</code> both packs lean slightly above ×1.0 (×1.04 and ×1.05), and both truncate a few more answers; the intervals include 1.0, so this is a hint, not a result.</p></figure>
</div>
</section>"""


def section_per_question(bat: dict) -> str:
    figs = []
    for pack, base, cand in PACKS:
        for suite, sname in SUITES.items():
            for eff in EFFORTS:
                series = [(arm, bat[arm][eff][suite]) for arm in (base, cand)]
                allt = [q["t"] for _, qs in series for q in qs]
                sb, sc = summary(bat[base][eff][suite]), summary(bat[cand][eff][suite])
                rounds = f"{sb['rounds']}+{sc['rounds']} rounds" if sb["rounds"] != sc["rounds"] else f"{sb['rounds']} round{'s' if sb['rounds'] > 1 else ''}"
                svg = strip_svg(series, max(min(allt) * 0.8, 0.5), max(allt) * 1.2, f"{pack} {sname} {eff}, time per question",
                                hover=lambda q, a=None: f"q{q['q']} {q['round']} · {q['t']:.1f} s · {q['tokens']:,} tokens · {'correct' if q['correct'] else 'wrong'}{' · truncated' if q['trunc'] else ''}")
                acc = (f"{sb['correct']}/{sb['n']} → {sc['correct']}/{sc['n']}")
                figs.append(f"""<figure class="strip" data-pack="{esc(pack)}" data-suite="{suite}" data-effort="{eff}"><div class="p-head"><p class="p-title">{esc(pack)} · {esc(sname)} · <code>{eff}</code> <span class="p-size">{rounds}</span></p>
<span class="p-unit">median {sb['med_t']:.1f} s → {sc['med_t']:.1f} s</span></div>{svg}
<p class="p-interp">Correct <b>{acc}</b> · truncated at {MAX_TOKENS:,} tokens {sb['trunc']} → {sc['trunc']} · median tokens {fmt_int(sb['med_tokens'])} → {fmt_int(sc['med_tokens'])}.</p></figure>""")
    return f"""
<section class="block" id="per-question"><h2 class="sec">Time per question, template against template</h2>
<p class="s-note">One dot per question and round: wall time to the final answer, log scale; the top row is the official template, the bottom row the effort tail.
Hover a dot for the question, the time and the token count. The iQ-MLX <code>xhigh</code> official run comes from the
<a href="qwen38-flashnext-swift15.html">Swift 1.5 vs iQ-MLX</a> page (2026-10-10); every other run is from 2026-10-13 to 2026-10-17 on the same server build.</p>
{legend(["w1", "w1t", "n2", "n2t"], DOT_KEYS, with_pack=True)}
<div class="sgrid">{"".join(figs)}</div>
<p class="s-note mt">The medians move by less than the round-to-round noise. What moves is the tail: at <code>xhigh</code> the effort-tail template hit the
token limit more often (Swift 1.5: 4 → 7 answers over 2 rounds; iQ-MLX: 7 → 9 in 1 round), and each truncated answer costs about 1,000 s. The four GPQA
questions iQ-MLX lost at <code>xhigh</code> were all truncations.</p>
</section>"""


def section_levels(bat: dict) -> str:
    cards = []
    for suite, sname in SUITES.items():
        for metric, head, fmt in (
            ("med_t", "Median time per question", fmt_s),
            ("med_reasoning", "Median thinking tokens", fmt_int),
        ):
            vmax = max(summary(bat[a][e][suite])[metric] for a in ("w1", "n2") for e in EFFORTS)
            groups = []
            for eff in EFFORTS:
                items = [(arm, summary(bat[arm][eff][suite])[metric], fmt(summary(bat[arm][eff][suite])[metric])) for arm in ("w1", "n2")]
                groups.append(bar_group(eff, items, vmax=vmax, with_pack=True))
            cards.append(card(f"{head} · {sname}", "Official template. Swift 1.5 median over 2 rounds, iQ-MLX over 1.", "".join(groups)))
    # accuracy table per level, official template, per round sum
    trs = []
    for suite, sname in SUITES.items():
        for eff in EFFORTS:
            cells = []
            for arm in ("w1", "n2"):
                s = summary(bat[arm][eff][suite])
                cells.append(f"<td>{s['correct']}<span class='u'>/{s['n']}</span></td><td>{s['trunc']}</td><td>{fmt_s(s['med_t'])}</td><td>{fmt_int(s['total_t'] / max(s['correct'], 1))} s</td>")
            trs.append(f'<tr><td class="nm">{esc(sname)}</td><td class="nm"><code>{eff}</code></td>{"".join(cells)}</tr>')
    table = f"""<div class="tbl-scroll"><table><thead><tr><th class="nm" rowspan="2">Suite</th><th class="nm" rowspan="2">Effort</th><th colspan="4">{arm_lab('w1', True)}</th><th colspan="4">{arm_lab('n2', True)}</th></tr>
<tr><th>correct</th><th>truncated</th><th>median time</th><th>s per correct</th><th>correct</th><th>truncated</th><th>median time</th><th>s per correct</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>"""
    return f"""
<section class="block" id="levels"><h2 class="sec">Between the levels: what each effort buys</h2>
<p class="s-note">Official template on both packs. GPQA-Diamond and LiveCodeBench, 50 questions each (seed 42). Swift 1.5 counts are the sum of 2 rounds (out of 100);
iQ-MLX counts are 1 round (out of 50).</p>
{legend(["w1", "n2"], with_pack=True)}
<div class="cgrid">{"".join(cards)}</div>
<div class="mt">{table}</div>
<p class="s-note mt"><b>Code needs <code>xhigh</code>; chat does not.</b> On LiveCodeBench, <code>medium</code> and <code>low</code> drop 5–7 problems per 50 on Swift 1.5 and 1–5 on iQ-MLX. On GPQA, <code>medium</code> costs 1–4 questions per 50 and <code>low</code> 5–6, while the time per correct answer falls 3–6×, because the long tail of
truncated <code>xhigh</code> answers disappears. The campaign's recommendation: <code>xhigh</code> for code and long sessions, <code>medium</code> for chat and short tool calling (where it is 23–28% faster with the same score), fixed per session when the official template is in use.</p>
</section>"""


def section_numbers(bat: dict) -> str:
    trs = []
    for pack, base, cand in PACKS:
        for suite, sname in SUITES.items():
            for eff in EFFORTS:
                sb, sc = summary(bat[base][eff][suite]), summary(bat[cand][eff][suite])
                def pair(a, b, f):
                    return f"<td>{f(a)}</td><td>{f(b)}</td>"
                trs.append(f'<tr><td class="nm">{esc(pack)}</td><td class="nm">{esc(sname)}</td><td class="nm"><code>{eff}</code></td><td class="nm">{sb["rounds"]} / {sc["rounds"]}</td>'
                           f'{pair(sb["correct"], sc["correct"], str)}{pair(sb["trunc"], sc["trunc"], str)}{pair(sb["med_t"], sc["med_t"], fmt_s)}'
                           f'{pair(sb["total_t"], sc["total_t"], fmt_min)}{pair(sb["med_tokens"], sc["med_tokens"], fmt_int)}{pair(sb["total_tokens"] / 1000, sc["total_tokens"] / 1000, lambda v: f"{v:,.0f}K")}</tr>')
    head = ('<tr><th class="nm" rowspan="2">Pack</th><th class="nm" rowspan="2">Suite</th><th class="nm" rowspan="2">Effort</th><th class="nm" rowspan="2">Rounds</th>'
            '<th colspan="2">Correct</th><th colspan="2">Truncated</th><th colspan="2">Median time</th><th colspan="2">Total time</th><th colspan="2">Median tokens</th><th colspan="2">Total tokens</th></tr>'
            '<tr>' + '<th>official</th><th>tail</th>' * 6 + '</tr>')
    return f"""
<section class="block" id="numbers"><details><summary><h2 class="sec">All numbers</h2></summary>
<p class="s-note mt">Counts are sums over the rounds listed (official / tail). Tokens are thinking plus visible answer. Total time is the wall time of the whole suite.</p>
<div class="tbl-scroll"><table><thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></div></details></section>"""


def section_setup() -> str:
    return """
<section class="block" id="setup"><details><summary><h2 class="sec">Setup and how to reproduce</h2></summary>
<p class="s-note mt">Mac Studio, Apple M4 Max, 40-core GPU, 128 GB unified memory, macOS 26.6. Server: mlx-serve 26.10.1 with the same flags for every arm
(<code>--prefix-cache</code> on, 131,072-token context for the batteries, 262,144 for the 3e probe). Sampling: temperature 1.0, top_p 0.95, top_k 20, seed 42,
<code>max_tokens</code> 65,536 on the batteries.</p>
<div class="tbl-scroll"><table><thead><tr><th class="nm">Arm</th><th class="nm">Weights</th><th class="nm">Chat template</th></tr></thead><tbody>
<tr><td class="nm">w1</td><td class="nm"><a href="https://huggingface.co/Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw">Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw</a> <span class="u">rev 13839b7</span></td><td class="nm">official (<code>chat_template.jinja</code> of the pack)</td></tr>
<tr><td class="nm">w1t</td><td class="nm">same weights, hardlink overlay</td><td class="nm"><a href="https://github.com/snagnever/macstudio-local-llm/blob/main/fixes/qwen3.8-flash-next/swift15-effort-tail.jinja">swift15-effort-tail.jinja</a></td></tr>
<tr><td class="nm">n2</td><td class="nm"><a href="https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw">ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw</a> <span class="u">rev dafff5c</span></td><td class="nm">official</td></tr>
<tr><td class="nm">n2t</td><td class="nm">same weights, hardlink overlay</td><td class="nm">swift15-effort-tail.jinja (also patched into <code>tokenizer_config.json</code>)</td></tr>
</tbody></table></div>
<p class="s-note mt">The overlay is built by <code>scripts/make-overlay.sh</code>: every file of the pack hardlinked into a new directory, with only the template replaced.
Probes: <code>scripts/agent_probes.py</code> (3e, 3f), <code>scripts/run-battery.sh</code> with <code>bench2.py</code> (GPQA, LiveCodeBench),
<code>scripts/effort_obedience.py</code> (paired bootstrap), <code>scripts/render_effort_tail_page.py</code> (this page). Runbook:
<a href="https://github.com/snagnever/macstudio-local-llm/blob/main/bench/flashnext-next-steps-2026-10/plan-effort-needles.md">plan-effort-needles.md</a>, Tasks 11 and 15;
write-ups: <a href="https://github.com/snagnever/macstudio-local-llm/blob/main/bench/flashnext-next-steps-2026-10/results/etapa11-effort-tail.md">etapa11-effort-tail.md</a> and
<a href="https://github.com/snagnever/macstudio-local-llm/blob/main/bench/flashnext-next-steps-2026-10/results/etapa15-iq-effort-tail.md">etapa15-iq-effort-tail.md</a>.</p>
</details></section>"""


def section_limits() -> str:
    return """
<section class="block notice" id="limits"><p><b>Limits</b></p><ul>
<li>GPQA-Diamond and LiveCodeBench are 50-question samples, not the full sets. Swift 1.5 has 2 rounds per effort and template, iQ-MLX has 1. A difference of 2–3 questions is within noise; the campaign rule accepts a drop of up to 3 per round.</li>
<li>The iQ-MLX <code>xhigh</code> official run is from another server session (2026-10-10). Its thinking ratio against the tail run (×1.05) is close to the same-session A/A at <code>medium</code> (×1.01), so the sessions look comparable, but it is not a same-day pair.</li>
<li>The checkpoint position (start of the last message) is inferred from the <code>hybrid miss</code> and <code>inherited N checkpoints</code> lines of the server log, not from the mlx-serve source.</li>
<li>The short-prompt probe (3f) ran only on Swift 1.5. The prompt is the same for iQ-MLX, so the cache behaviour should match, but it was not measured.</li>
<li>Two fixes were not tested: a smaller <code>--ssm-checkpoint-stride</code>, which would place checkpoints inside short prompts at a prefill cost, and a template that puts the effort block before the last user message.</li>
<li>LiveCodeBench answers graded by the old runner were regraded with the official import prelude; no passing answer turned into a failure.</li>
</ul></section>"""


def hero(bat: dict) -> str:
    return """
<section class="hero" id="tldr"><p class="hero-lead">Qwen3.8-Flash-Next takes its thinking effort from one line of the prompt. Put that line <b>first</b> (the official template) and changing the effort
in a 128K session costs <b>167 s</b>, because the whole prefix cache is lost. Put it <b>last</b> and the switch costs <b>0.8–5.8 s</b>, the model still obeys it, and accuracy holds.
But the same move breaks prefix reuse on short prompts: every tool-calling turn starts cold, <b>+0.9 to +1.4 s</b>. On a hybrid attention/SSM model, where a variable line sits decides where the server can save its state.</p>
<div class="tiles">
<div class="tile"><p class="t-lab">Effort switch at 128K</p><p class="t-big">167 → 0.8 s</p><p class="t-sub">time to first token, xhigh → low · cache hit 0.00 → 1.00</p></div>
<div class="tile"><p class="t-lab">Short prompts, prefix reuse</p><p class="t-big">53 → 0</p><p class="t-sub">of 55 tool-calling requests reused the system prompt · +0.9 to +1.4 s each</p></div>
<div class="tile"><p class="t-lab">Obedience</p><p class="t-big">×0.90–×1.05</p><p class="t-sub">thinking tokens, tail against official, at the same effort · rule ×0.80–×1.25</p></div>
<div class="tile"><p class="t-lab">Accuracy</p><p class="t-big">≤ 3</p><p class="t-sub">questions apart per 50 on GPQA and LiveCodeBench, every effort, both packs</p></div>
</div></section>"""


def takeaways() -> str:
    return """
<div class="takeaways"><h2>What we learned</h2><ul>
<li><b>Where the effort line sits is a cache decision, not a prompt-engineering one.</b> The model obeys it in either position. The server's prefix cache does not: with a hybrid GDN/SSM model, mlx-serve can only resume at a saved state checkpoint, and the checkpoint goes at the start of the last message.</li>
<li><b>Tail template: good for long sessions, bad for short ones.</b> Effort switch at 128K: 167 s → 0.8–5.8 s. Same-effort control turn at 128K: 1.3 s → 3.0 s. Short tool-calling turn: +0.9 to +1.4 s, prefix reuse 53/55 → 0/55.</li>
<li><b>Both packs behave the same way.</b> Swift 1.5 and iQ-MLX give the same cache hits at every step of the probe (0.97–1.00 on switch, 0.98 on control) and pass the same accuracy rules.</li>
<li><b>iQ-MLX cuts more thinking per level than Swift 1.5.</b> At <code>low</code>, iQ-MLX thinks ×0.26 of its <code>xhigh</code>; Swift 1.5 ×0.45. Swift 1.5 thinks less to begin with (GPQA median 1.7K vs 5.1K tokens at xhigh on the earlier page).</li>
<li><b>At xhigh, the tail template hits the token limit a little more often</b> (Swift 4 → 7 in 2 rounds, iQ 7 → 9 in 1), and its thinking ratio leans to ×1.04–×1.05. The intervals include 1.0, so this is not confirmed.</li>
<li><b>Decision:</b> the official template stays the default; the harness fixes the effort per session (<code>xhigh</code> for code and long sessions, <code>medium</code> for chat and short tool calling). The tail template is kept as an optional profile for long sessions that need to change effort mid-way.</li>
</ul></div>"""


def render() -> str:
    bat = load_battery()
    d3e, d3f, ob = load_3e(), load_3f(), load_obedience()
    desc = ("Where the thinking-effort line sits in the prompt of Qwen3.8-Flash-Next decides what the prefix cache can reuse: "
            "first line, an effort switch at 128K costs 167 s; last line, 0.8–5.8 s, but short prompts lose the shared prefix. "
            "Swift 1.5 and iQ-MLX packs on mlx-serve, Apple M4 Max.")
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Effort line: top or tail</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:title" content="Qwen3.8-Flash-Next: where the thinking-effort line goes decides the prefix cache">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="https://snagnever.github.io/macstudio-local-llm/qwen38-flashnext-effort-tail.html">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>{CSS}</style>
<div class="wrap">
  <header>
    <div>
      <p class="eyebrow">Qwen3.8-Flash-Next · Apple M4 Max 128 GB · mlx-serve 26.10.1 · October 2026</p>
      <h1>Where the thinking-effort line goes decides what the prefix cache can reuse</h1>
      <p class="sub">The same effort line, first or last in the prompt, on two 4.7-bit MLX packs (Swift 1.5 and iQ-MLX): effort switches at 128K, short tool-calling prompts, obedience to the level, and time, tokens and accuracy at xhigh, medium and low.</p>
    </div>
    <button class="theme" id="themeBtn" type="button">theme: auto</button>
  </header>
{hero(bat)}
{takeaways()}
{section_templates()}
{section_switch(d3e)}
{section_short(d3f)}
{section_obedience(ob)}
{section_levels(bat)}
{section_per_question(bat)}
{section_numbers(bat)}
{section_setup()}
{section_limits()}
  <footer id="foot">Data, scripts and per-question results: <a href="https://github.com/snagnever/macstudio-local-llm/tree/main/bench/flashnext-next-steps-2026-10">github.com/snagnever/macstudio-local-llm</a>. Generated <code>{now}</code>.</footer>
</div>
<script>{JS}</script>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    a.out.write_text(render(), encoding="utf-8")
    print(f"wrote {a.out} ({a.out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
