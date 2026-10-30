#!/usr/bin/env python3
"""Sections of the concurrency report page, organized by use scenario (spec 2026-10-30).

Each function takes the collect() payload and returns one <section id="..."> string. The copy is fixed
English; every number comes from payload["scenarios"]. A missing value shows as n/m (hatched in charts).
"""
from __future__ import annotations

import html
from typing import Any, Optional

import render_report as RR  # only used at call time (render_report imports this module)
from report_charts import svg_band_bars, svg_diverging, svg_dumbbell, svg_lines, svg_timeline, table_view

BAND_ICON = {"good": "✓ good", "ok": "~ acceptable", "poor": "✕ poor"}


def _e(s: Any) -> str:
    return html.escape(str(s))


def _n(v: Optional[float], fmt: str = "{:.1f}", unit: str = "") -> str:
    return "n/m" if v is None else (fmt.format(v) + (f" {unit}" if unit else "")).strip()


def _pct(v: Optional[float]) -> str:
    return "n/m" if v is None else f"{'+' if v >= 0 else '−'}{abs(v) * 100:.0f}%"


def _sec(sid: str, title: str, question: str, body: str) -> str:
    q = f'<p class="s-note q">{_e(question)}</p>' if question else ""
    return f'<section id="{sid}" class="block"><h2 class="sec">{_e(title)}</h2>{q}{body}</section>'


def _servers(data: dict) -> list[dict]:
    return data["servers"]


def _legend(data: dict, extra: Optional[list[tuple[str, str]]] = None) -> str:
    items = [(f'<span class="sw" style="background:var(--{s["series"]})"></span>', s["label"]) for s in _servers(data)]
    items += extra or []
    items.append(('<span class="sw hatch"></span>', "not measured (n/m)"))
    return '<div class="legend">' + "".join(f'<span class="chip">{sw}{_e(t)}</span>' for sw, t in items) + "</div>"


def _panel(chart: str, table: str = "", caption: str = "") -> str:
    cap = f'<p class="p-interp">{caption}</p>' if caption else ""
    return f'<div class="panel"><div class="chart">{chart}</div>{table}{cap}</div>'


def _rows_value(data: dict, block: dict, key: str, note_key: Optional[str] = None) -> list[dict]:
    rows = []
    for s in _servers(data):
        v = block[s["key"]]
        rows.append({"label": s["label"], "series": s["series"], "value": v.get(key),
                     "note": ("*" if note_key and v.get(note_key) == "synthetic" else "")})
    return rows


def _vmax(values: list[Optional[float]], floor: float) -> float:
    vals = [v for v in values if v is not None]
    return max(floor, RR._nice(max(vals) * 1.15)) if vals else floor


def _band_chips() -> str:
    chips = "".join(f'<span class="band-chip {k}">{_e(v)}</span>' for k, v in BAND_ICON.items())
    return ('<div class="bands"><b>Experience bands:</b> ' + chips +
            ' <span class="band-rule">reply starts ≤ 2 / 2–5 / &gt; 5 s · generation ≥ 60 / 30–60 / &lt; 30 tok/s '
            '· first prompt ≤ 30 / 30–60 / &gt; 60 s · side call ≤ 5 / 5–60 / &gt; 60 s</span></div>')


def _tbench_text(data: dict) -> str:
    tb = data.get("tbench")
    if not tb:
        return ("Agent quality (does the agent finish real tasks?) is <b>not measured</b> on either server yet: no "
                "Terminal-Bench run has finished on these weights.")
    srv = _e(tb.get("server", ""))
    if tb.get("score") is not None:
        return f"Agent quality: Terminal-Bench on {srv} scored {_e(tb['score'])} ({_e(tb.get('done'))} of {_e(tb.get('total'))} tasks)."
    return (f"Agent quality (does the agent finish real tasks?) is <b>not measured</b> yet: Terminal-Bench on {srv} is "
            f"running ({_e(tb.get('done'))} of {_e(tb.get('total'))} tasks); nothing on the other server.")


# ---- sections ----

def hero(data: dict) -> str:
    sc = data["scenarios"]
    v, rec = sc["verdict"], data["recommended"]
    srv = {s["key"]: s for s in _servers(data)}
    other = next(s for s in _servers(data) if s["key"] != rec)
    one, two = sc["one_session"], sc["two_sessions"]

    def tile(lab: str, word: Optional[str], sub: str, other_line: str) -> str:
        return (f'<div class="tile"><p class="t-lab">{_e(lab)}</p><p class="t-big">{_e(word or "n/m")}</p>'
                f'<p class="t-sub">{sub}</p><p class="t-other">{other_line}</p></div>')

    o, ot = one[rec], one[other["key"]]
    t, tt = two[rec], two[other["key"]]
    many = v["many"]
    tiles = [
        tile("One session", v["one"]["word"],
             f"Reply starts in {_n(o['warm_ttft_s'], unit='s')}. First prompt of a session: {_n(o['first_prompt_s'], '{:.0f}', 's')}.",
             f"{_e(other['label'])}: reply starts {_n(ot['warm_ttft_s'], unit='s')}"),
        tile("Two sessions", v["two"]["word"],
             f"Reply starts in {_n(t['ttft_pair_p50'], unit='s')} instead of {_n(t['ttft_alone_p50'], unit='s')}. "
             + (f"The pair finishes {abs(t['time_saved']) * 100:.0f}% {'sooner' if t['time_saved'] >= 0 else 'later'} "
                f"than the two tasks one after the other." if t["time_saved"] is not None else "Time saved: n/m."),
             f"{_e(other['label'])}: reply starts {_n(tt['ttft_pair_p50'], unit='s')}, time saved {_pct(tt['time_saved'])}"),
        tile("Three or more", many["word"],
             (f"Each turn runs {many['slow_lo']:.1f}×–{many['slow_hi']:.1f}× slower than alone at 128K."
              if many["slow_lo"] is not None else "Not measured."),
             "Measured on the synthetic worst case; see section 4."),
    ]
    lead = (f"Can a local Qwen3.8 Flash-Next server on one Mac Studio ({_e(data['rig'])}) give a usable Claude Code "
            f"session, and what does a second session cost? Two servers: <b>{_e(srv['splash']['label'])}</b> "
            f"({_e(srv['splash']['weights'])}) and <b>{_e(srv['mlx']['label'])}</b> ({_e(srv['mlx']['weights'])}). "
            f"The verdict tiles read the recommended server, {_e(srv[rec]['label'])}; the other server is the small line.")
    body = (f'<p class="hero-lead">{lead}</p><div class="tiles">{"".join(tiles)}</div>' + _band_chips()
            + f'<p class="s-note">{_tbench_text(data)}</p>')
    return f'<section id="verdict" class="hero">{body}</section>'


def one_session(data: dict) -> str:
    sc = data["scenarios"]
    one = sc["one_session"]
    charts = []
    rows = _rows_value(data, one, "warm_ttft_s", "warm_ttft_source")
    charts.append(_panel(svg_band_bars("Reply starts (warm turn, prompt cached)", rows, 6, "s", "ttft"),
                         table_view(["server", "reply starts, s", "source"],
                                    [[s["label"], _n(one[s["key"]]["warm_ttft_s"]), one[s["key"]]["warm_ttft_source"] or "n/m"]
                                     for s in _servers(data)]),
                         "* from the synthetic test (a tool turn on a cached prompt), not yet from Claude Code."
                         if any(r["note"] for r in rows) else ""))
    rows = _rows_value(data, one, "first_prompt_s")
    charts.append(_panel(svg_band_bars("First prompt of a session (~20K tokens)", rows, 70, "s", "first_prompt"),
                         table_view(["server", "first prompt, s"], [[r["label"], _n(r["value"], "{:.0f}")] for r in rows])))
    rows = _rows_value(data, one, "cold_128k_s")
    charts.append(_panel(svg_band_bars("Resume a 128K session (cold read)", rows, _vmax([r["value"] for r in rows], 200), "s", None),
                         table_view(["server", "cold read, s"], [[r["label"], _n(r["value"], "{:.0f}")] for r in rows]),
                         "No band: a cold read is a one-time cost per session."))
    rows = [{"label": s["label"], "series": s["series"], "value": None, "lo": one[s["key"]]["tps_lo"], "hi": one[s["key"]]["tps_hi"]}
            for s in _servers(data)]
    charts.append(_panel(svg_band_bars("Generation speed, range over turns", rows, 200, "tok/s", "tps"),
                         table_view(["server", "slowest turn, tok/s", "fastest turn, tok/s"],
                                    [[r["label"], _n(r["lo"], "{:.0f}"), _n(r["hi"], "{:.0f}")] for r in rows])))
    task_names = {"a": "Small task A: add a CLI flag with a test", "b": "Small task B: fix two bash bugs with tests",
                  "c": "Realistic task C (20–40 turns)", "d": "Realistic task D (20–40 turns)"}
    trows = []
    for p in ("small", "realistic"):
        tasks = sorted({t for s in _servers(data) for t in (one[s["key"]]["tasks"].get(p) or {})})
        for t in tasks:
            trows.append([task_names.get(t, t)] + [_n((one[s["key"]]["tasks"].get(p) or {}).get(t), "{:.0f}", "s") for s in _servers(data)])
    if not trows:
        trows.append(["Small tasks A and B"] + ["n/m"] * len(_servers(data)))
    tb_cells = []
    for s in _servers(data):
        tb = one[s["key"]]["tbench"]
        tb_cells.append("n/m" if not tb else (f"score {tb['score']}" if tb.get("score") is not None
                                              else f"running, {tb.get('done')} of {tb.get('total')} tasks"))
    trows.append(["Agent quality (Terminal-Bench)"] + tb_cells)
    table = RR._table(["task alone", *[s["label"] for s in _servers(data)]], trows, "wide")
    return _sec("one", "1. One session", "What does a normal coding turn feel like, alone on the server?",
                _legend(data) + "".join(charts) + table)


def two_sessions(data: dict) -> str:
    sc = data["scenarios"]
    two = sc["two_sessions"]
    srvs = _servers(data)
    extra = [('<span class="sw" style="background:var(--s1l)"></span>', "alone"),
             ('<span class="sw" style="background:var(--s1)"></span>', "in a pair")]

    def sub(key: str, field: str) -> Optional[float]:
        v = two[key].get("subagents")
        return v.get(field) if v else None

    def dumb(title: str, metric: Optional[str], unit: str, vmax: float, keys: list[tuple[str, str, str]],
             sub_field: Optional[str] = None, sub_alone: Optional[str] = None) -> str:
        rows = [{"label": f"{s['label']} · {lab}", "series": s["series"], "alone": two[s["key"]][ka], "pair": two[s["key"]][kp]}
                for s in srvs for lab, ka, kp in keys]
        if sub_field and any(sub(s["key"], sub_field) is not None for s in srvs):
            rows += [{"label": f"{s['label']} · median, with subagents", "series": s["series"],
                      "alone": two[s["key"]][sub_alone], "pair": sub(s["key"], sub_field)} for s in srvs]
        tbl = table_view(["row", "alone", "pair"], [[r["label"], _n(r["alone"]), _n(r["pair"])] for r in rows])
        return _panel(svg_dumbbell(title, rows, vmax, unit, metric, "s1"), tbl)

    charts = [
        dumb("Reply starts (s): alone → pair", "ttft", "s", 8,
             [("median", "ttft_alone_p50", "ttft_pair_p50"), ("p90", "ttft_alone_p90", "ttft_pair_p90")],
             "ttft_p50", "ttft_alone_p50"),
        dumb("Generation (tok/s): alone → pair", "tps", "tok/s", 200,
             [("median", "tps_alone_p50", "tps_pair_p50"), ("slowest turn", "tps_alone_min", "tps_pair_min")],
             "tps_p50", "tps_alone_p50"),
    ]
    task_rows, task_tbl = [], []
    for s in srvs:
        for p, tasks in sorted(two[s["key"]]["tasks"].items()):
            for t, v in sorted(tasks.items()):
                task_rows.append({"label": f"{s['label']} · task {t.upper()}", "series": s["series"],
                                  "alone": v["alone_s"], "pair": v["pair_s"]})
                task_tbl.append([f"{s['label']} · task {t.upper()} ({p})", _n(v["alone_s"], "{:.0f}"), _n(v["pair_s"], "{:.0f}")])
    if not task_rows:
        task_rows = [{"label": s["label"], "series": s["series"], "alone": None, "pair": None} for s in srvs]
    charts.append(_panel(svg_dumbbell("Task time (s): alone → pair", task_rows,
                                      _vmax([r[k] for r in task_rows for k in ("alone", "pair")], 100), "s", None, "s1"),
                         table_view(["row", "alone, s", "pair, s"], task_tbl or [[s["label"], "n/m", "n/m"] for s in srvs])))
    saved_rows = [{"label": s["label"], "series": s["series"], "pct": two[s["key"]]["time_saved"]} for s in srvs]
    charts.append(_panel(svg_diverging("Time saved by running the pair together", saved_rows, 0.5),
                         table_view(["server", "time saved"], [[r["label"], _pct(r["pct"])] for r in saved_rows]),
                         "1 − pair time ÷ the two tasks one after the other. Positive: the pair finishes sooner."))
    side_rows = _rows_value(data, two, "side_p95_s")
    charts.append(_panel(svg_band_bars("Side call (permission check) while the other session works, p95", side_rows,
                                       _vmax([r["value"] for r in side_rows], 60), "s", "side"),
                         table_view(["server", "side call p95, s"], [[r["label"], _n(r["value"])] for r in side_rows]),
                         "From the synthetic 128K test with two sessions and side calls every 20 s."))
    notes = []
    for s in srvs:
        t = two[s["key"]]
        if t["max_concurrent"] is not None:
            notes.append(f"{_e(s['label'])}: measured with <code>claude -p</code>, {t['max_concurrent']} requests open at once "
                         f"at most, {_n(t['new_tokens_p50'], '{:.0f}')} new tokens per turn (median), no subagents.")
            sa = t.get("subagents")
            if sa:
                notes.append(f"With two Explore subagents per session it ran as {sa['max_concurrent']} streams: reply starts "
                             f"{_n(sa['ttft_p50'], unit='s')} (p90 {_n(sa['ttft_p90'], unit='s')}), slowest turn "
                             f"{_n(sa['tps_min'], '{:.0f}', 'tok/s')}, the pair took {_n(sa['pair_wall_s'], '{:.0f}', 's')}.")
        else:
            notes.append(f"{_e(s['label'])}: the Claude Code pair is not measured yet on this build.")
    return _sec("two", "2. Two sessions, daily use", "What does the second session cost me?",
                _legend(data, extra) + "".join(charts) + f'<p class="s-note">{" ".join(notes)}</p>')


def worst_case(data: dict) -> str:
    sc = data["scenarios"]
    w = sc["worst_case"]
    srvs = _servers(data)
    labels = (srvs[0]["label"], srvs[1]["label"])
    intro = ("It happens when a session starts (about 20K new tokens), reads a large file or grep result (5–30K), "
             "compacts, or resumes an old conversation. "
             f"{_e(labels[0])} reads one prompt at a time, so the other session waits for the read. "
             f"{_e(labels[1])} lets a short call wait minutes behind a long read.")
    rows = [{"label": s["label"], "series": s["series"], "alone": w[s["key"]]["turn_alone_s"], "pair": w[s["key"]]["turn_pair_s"]}
            for s in srvs]
    chart = _panel(svg_dumbbell("Turn time, 512-token reply (s): alone → two sessions", rows,
                                _vmax([r[k] for r in rows for k in ("alone", "pair")], 20), "s", None, "s1"),
                   table_view(["server", "alone, s", "two sessions, s"], [[r["label"], _n(r["alone"]), _n(r["pair"])] for r in rows]),
                   "Synthetic test at 128K: every turn brings 32K–128K of new prompt, with side calls.")
    trows = [["Side calls over 60 s"] + [_n(w[s["key"]]["side_over_60"], "{:.0f}") for s in srvs],
             ["Total generation, pair ÷ alone"] + [_n(w[s["key"]]["gain"], "{:.2f}×") for s in srvs],
             ["Best setting"] + [(f"<code>{_e(b['label'])}</code>: {_n(b['turn_s'], unit='s')}, {_e(b['note'])}"
                                  if (b := w[s["key"]]["best_setting"]) else "—") for s in srvs]]

    def real_ds(rd: Optional[dict]) -> str:
        if not rd:
            return "—"
        ts = rd["time_saved"]
        saved = "" if ts is None else f"; the pair finishes {abs(ts) * 100:.0f}% {'sooner' if ts >= 0 else 'later'} than in sequence"
        gain = ("no gain" if rd["ttft_p90_plain"] is not None and rd["ttft_p90"] >= rd["ttft_p90_plain"] else "a gain")
        return (f"reply starts p90 {_n(rd['ttft_p90'], unit='s')} vs {_n(rd['ttft_p90_plain'], unit='s')} without the flag"
                f"{saved}: {gain}")

    trows.append(["<code>--decode-share 1.0</code> on the real pair (Claude Code, realistic tasks)"]
                 + [real_ds(w[s["key"]].get("real_decode_share")) for s in srvs])
    table = RR._table(["two sessions, 128K, big prompts", *[s["label"] for s in srvs]], trows, "wide")
    return _sec("worst", "3. Worst case: both sessions read a big prompt at the same time",
                "When does it happen, and how bad is it?",
                f'<p class="s-note">{intro}</p>' + _panel(svg_timeline(labels)) + _legend(data) + chart + table)


def many_sessions(data: dict) -> str:
    sc = data["scenarios"]
    by_n = sc["by_n"]
    srvs = _servers(data)
    xs = [1, 2, 3, 4]
    series = [{"key": s["series"], "label": s["label"],
               "points": {n: {"y": by_n[s["key"]][n]["turn_s"], "legacy": by_n[s["key"]][n]["legacy"]} for n in xs}}
              for s in srvs]
    ymax = _vmax([by_n[s["key"]][n]["turn_s"] for s in srvs for n in xs], 10)
    extra = [('<span class="sw ring"></span>', f"older build ({data['legacy']['label']}): hollow point")]
    tbl = table_view(["sessions", *[s["label"] for s in srvs]],
                     [[str(n)] + [_n(by_n[s["key"]][n]["turn_s"]) + (" (26.10.1)" if by_n[s["key"]][n]["legacy"] else "")
                                  for s in srvs] for n in xs])
    chart = _panel(svg_lines("Turn time of the slowest session (s), 128K with side calls", series, xs, ymax, "s"), tbl)
    trows = [[f"{n} sessions"] + [_n(by_n[s["key"]][n]["turn_s"], unit="s") + (" (26.10.1)" if by_n[s["key"]][n]["legacy"] else "")
                                  for s in srvs] for n in (3, 4)]
    trows.append(["Side call p95, 4 sessions"] + [_n(by_n[s["key"]][4]["side_p95_s"], "{:.0f}", "s")
                                                  + (" (26.10.1)" if by_n[s["key"]][4]["legacy"] else "") for s in srvs])
    two = sc["two_sessions"]
    subs = {s["key"]: two[s["key"]].get("subagents") for s in srvs}
    trows.append(["2 sessions + subagents (real Claude Code)"]
                 + [(f"reply starts {_n(sa['ttft_p50'], unit='s')} (p90 {_n(sa['ttft_p90'], unit='s')}), "
                     f"ran as {sa['max_concurrent']} streams") if (sa := subs[s["key"]]) else "n/m" for s in srvs])
    table = RR._table(["128K", *[s["label"] for s in srvs]], trows, "wide")
    if any(subs.values()):
        measured = "; ".join(f"{_e(s['label'])}: ran as {subs[s['key']]['max_concurrent']} streams (measured)"
                             for s in srvs if subs[s["key"]])
        note = ("A subagent is one more session for the server. Two Claude Code sessions, each asked for two Explore "
                f"subagents in parallel, were measured at the proxy: {measured}. The page reports the measured count, "
                "not a nominal four.")
    else:
        note = ("A subagent is one more session for the server: two Claude Code sessions with one Explore subagent each "
                "are four. Not measured with real Claude Code yet.")
    return _sec("many", "4. Three and four sessions, and subagents",
                "Can I open a third window, or let sessions spawn subagents?",
                _legend(data, extra) + chart + table + f'<p class="s-note">{note}</p>')


def long_context(data: dict) -> str:
    sc = data["scenarios"]
    lc = sc["long_256k"]
    srvs = _servers(data)
    rows = [{"label": s["label"], "series": s["series"], "value": None if lc[s["key"]]["legacy"] else lc[s["key"]]["turn_s"],
             "note": "" if lc[s["key"]]["legacy"] else f"— {lc[s['key']]['note']}"} for s in srvs]
    chart = _panel(svg_band_bars("Two 256K sessions, slowest turn (s)", rows, _vmax([r["value"] for r in rows], 20), "s", None),
                   table_view(["server", "slowest turn, s", "setting"],
                              [[s["label"], _n(lc[s["key"]]["turn_s"]) + (" (26.10.1)" if lc[s["key"]]["legacy"] else ""), lc[s["key"]]["note"]]
                               for s in srvs]))
    legacy = next((lc[s["key"]] for s in srvs if lc[s["key"]]["legacy"] and lc[s["key"]]["turn_s"] is not None), None)
    note = ("A cold 256K read takes about 12 minutes, and the other session waits for it. After the read, both "
            "sessions turn in about 12 s on Splash 1.5.0 with no memory setting.")
    if legacy:
        note += (f" The current mlx-serve build has no 256K pair run; the older build (26.10.1) fit two 256K sessions "
                 f"only with a {_e(legacy['note'])}, slowest turn {_n(legacy['turn_s'], unit='s')}.")
    return _sec("long", "5. Long sessions: two at 256K", "", _legend(data) + chart + f'<p class="s-note">{note}</p>')


def recommendation(data: dict) -> str:
    srv = {s["key"]: s for s in _servers(data)}
    rec = srv[data["recommended"]]["label"]
    rows = [["One or two Claude Code sessions", rec, "faster alone, cheaper second session, short calls do not stall"],
            ["Quality-critical work", "pending Terminal-Bench on both", "the two servers run different weights (GGUF IQ4_XS vs MLX 4.7 bpw)"],
            ["Three sessions, or parallel subagents", "neither", "2.4× or slower per turn"],
            ["Two long (256K) sessions", rec, "fits without settings; expect a long first read"]]
    return _sec("recommend", "6. Recommendation", "", RR._table(["use", "server", "why"], rows, "wide"))


def coverage(data: dict) -> str:
    sc = data["scenarios"]
    mark = {"measured": "●", "running": "◐", "missing": "○"}
    cols = [s for s in _servers(data)] + [data["legacy"]]
    rows = [[r["scenario"]] + [f'<span class="cov {r["cells"][c["key"]]}">{mark[r["cells"][c["key"]]]}</span>' for c in cols]
            for r in sc["coverage"]]
    head = ["scenario"] + [s["label"] for s in _servers(data)] + [f"older build ({data['legacy']['label']}, appendix)"]
    legend = '<p class="s-note">● measured · ◐ running · ○ not measured</p>'
    return _sec("coverage", "What was measured", "", legend + RR._table(head, rows, "wide cov"))


def appendix(data: dict) -> str:
    old = [RR._hero(data), RR._splash(data), RR._how(data), RR._glossary(), RR._sessions(data), RR._throughput(data),
           RR._side_requests(data), RR._max_concurrent(data), RR._long_context(data), RR._claude_code_section(data),
           RR._pds(data), RR._learned(data), RR._upstream(), RR._refusals(data), RR._not_measured(), RR._reproduce(data)]
    intro = (f"Method, the campaign pass rule (worst slowdown ≤ 1.5× passes, ≤ 2.0× warns, above fails) and its "
             f"verdicts, recall checks, every configuration, and the {_e(data['legacy']['label'])} campaign of "
             f"{' and '.join(data['dates'])} as it was published.")
    return (f'<section id="appendix" class="block"><h2 class="sec">Appendix</h2><p class="s-note">{intro}</p>'
            f'<details class="appx"><summary>Open the appendix</summary>{"".join(old)}</details></section>')
