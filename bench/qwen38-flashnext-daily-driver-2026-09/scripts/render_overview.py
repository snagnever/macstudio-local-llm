#!/usr/bin/env python3
"""Render results/reports.json into reports/qwen38-flashnext-overview.html.

Same layout as the dense campaign's reports/overview.html: tiles, tabs
(Performance, Runtimes & quants, Tests, Gates & queue, Glossary), a bar chart
with a metric selector, a matrix by context and a filterable table. The data is
embedded as JSON; the browser builds the chart, filters and tables.

    python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/consolidate_reports.py
    python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_overview.py
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[1]
REPORTS_JSON = CAMPAIGN / "results" / "reports.json"
OUT = CAMPAIGN.parents[1] / "reports" / "qwen38-flashnext-overview.html"

GATE_CTX = (32768, 131072)
STATE_CLASS = {"pass": "ok", "done": "ok", "control": "neutral", "fail": "bad",
               "running": "run", "pending": "wait"}
STATE_LABEL = {"pass": "pass", "fail": "fail", "control": "control", "done": "done",
               "running": "running", "pending": "pending"}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def _canonical(data: dict) -> dict:
    return {(g["cand"], g["context"]): g for g in data["groups"] if g["canonical"]}


def gate_passers(data: dict) -> list[str]:
    canon = _canonical(data)
    out = []
    for c in data["candidates"]:
        groups = [canon.get((c["id"], ctx)) for ctx in GATE_CTX]
        if all(g is not None and not g["refused"] and not g["gates_failed"] for g in groups):
            out.append(c["id"])
    return out


def build_tiles(data: dict) -> str:
    canon = _canonical(data)
    cands = {c["id"]: c for c in data["candidates"]}
    passers = gate_passers(data)

    def ranked(ctx: int) -> list[dict]:
        rows = [canon[(cid, ctx)] for cid in passers
                if (cid, ctx) in canon and canon[(cid, ctx)]["t_turno_s"] is not None]
        return sorted(rows, key=lambda g: g["t_turno_s"])

    r32, r128 = ranked(32768), ranked(131072)
    winner = cands[r128[0]["cand"]] if r128 else None

    def t_tile(rows: list[dict]) -> tuple[str, str]:
        if not rows:
            return "—", ""
        best = rows[0]
        val = f'{best["t_turno_s"]:.2f}<span class="unit">s</span>'
        sub = f'{best["cand"]} · {best["reps"]} reps'
        if len(rows) > 1:
            sub += f' · 2nd {rows[1]["cand"]} {rows[1]["t_turno_s"]:.2f} s'
        return val, sub

    reach = [g for g in canon.values() if g["served_n"]]
    top = max(reach, key=lambda g: g["context"], default=None)
    v32, s32 = t_tile(r32)
    v128, s128 = t_tile(r128)
    tiles = [
        ("Daily driver", esc(winner["id"]) if winner else "—",
         f'{winner["quant"]} · {winner["runtime"]} {winner["runtime_version"]}' if winner else ""),
        ("T_turn · 32K", v32, s32),
        ("T_turn · 128K", v128, s128),
        ("Pass the gates", f'{len(passers)}<span class="unit">/{len(data["candidates"])}</span>',
         "32K and 128K · " + ", ".join(passers)),
        ("Context ceiling", f'{top["context"] // 1024}<span class="unit">K</span>' if top else "—",
         f'{top["cand"]} · {top["tag"]}' if top else ""),
    ]
    return "".join(
        f'<div class="tile"><span class="tlabel">{esc(t)}</span>'
        f'<span class="tval">{v}</span><span class="tsub">{esc(s)}</span></div>'
        for t, v, s in tiles
    )


def build_verdicts(verdicts: list[dict]) -> str:
    return "".join(
        f'<div class="vcard {STATE_CLASS.get(v["state"], "neutral")}"><div class="vtop">'
        f'<span class="vgate">{esc(v["gate"])}</span>'
        f'<span class="chip {STATE_CLASS.get(v["state"], "neutral")}">'
        f'{esc(STATE_LABEL.get(v["state"], v["state"]))}</span></div>'
        f'<div class="varm mono">{esc(v["arm"])}</div>'
        f'<p class="vnote">{esc(v["note"])}</p></div>'
        for v in verdicts
    )


def build_queue(queue: list[dict]) -> str:
    return "".join(
        f'<li class="{STATE_CLASS.get(q["status"], "wait")}"><span class="dot"></span>'
        f'<span class="qstage">{esc(q["stage"])}</span>'
        f'<span class="chip {STATE_CLASS.get(q["status"], "wait")}">'
        f'{esc(STATE_LABEL.get(q["status"], q["status"]))}</span></li>'
        for q in queue
    )


def render(data: dict) -> str:
    passers = gate_passers(data)
    winner = next((c for c in data["candidates"] if c["state"] == "pass" and c["status"] == "winner"), None)
    verdict_line = (f'Verdict: {winner["id"]} {winner["runtime"]} {winner["runtime_version"]}'
                    if winner else "Verdict pending")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return (
        TEMPLATE
        .replace("/*__CSS__*/", CSS + EXTRA_CSS)
        .replace("__DATA__", payload)
        .replace("__TILES__", build_tiles(data))
        .replace("__VERDICTS__", build_verdicts(data["verdicts"]))
        .replace("__QUEUE__", build_queue(data["queue"]))
        .replace("__GENERATED__", esc(data["generated_at"]))
        .replace("__VERDICTLINE__", esc(verdict_line))
        .replace("__PASSERS__", esc(f"{len(passers)}/{len(data['candidates'])} pass the gates"))
    )


CSS = r"""
:root{
  --ground:#f4f6f7; --surface:#ffffff; --surface-2:#eef1f3; --ink:#151a1f;
  --muted:#5c6772; --hairline:#e0e5e9; --accent:#0e8f9d; --accent-strong:#0b6f7a;
  --ok:#1f8f52; --warn:#b9791b; --bad:#c8465a; --neutral:#4b5763;
  --shadow:0 1px 2px rgba(20,26,31,.05),0 8px 24px rgba(20,26,31,.05);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#0d1116; --surface:#151b21; --surface-2:#1b232b; --ink:#e7edf2;
  --muted:#93a1ae; --hairline:#232c35; --accent:#2fbccb; --accent-strong:#57d3e0;
  --ok:#37c37e; --warn:#e0a53a; --bad:#ec6a7c; --neutral:#8896a3;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}}
:root[data-theme="dark"]{
  --ground:#0d1116; --surface:#151b21; --surface-2:#1b232b; --ink:#e7edf2;
  --muted:#93a1ae; --hairline:#232c35; --accent:#2fbccb; --accent-strong:#57d3e0;
  --ok:#37c37e; --warn:#e0a53a; --bad:#ec6a7c; --neutral:#8896a3;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased;}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums;}
.wrap{max-width:1160px;margin:0 auto;padding:44px 24px 72px;}
.head{border-bottom:1px solid var(--hairline);padding-bottom:24px;margin-bottom:24px;}
.eyebrow{font-family:"Archivo",sans-serif;text-transform:uppercase;letter-spacing:.14em;
  font-size:12px;font-weight:600;color:var(--accent-strong);}
h1{font-family:"Archivo",sans-serif;font-weight:700;font-size:clamp(26px,4vw,40px);
  line-height:1.1;text-wrap:balance;margin:.35em 0 .3em;letter-spacing:-.01em;}
.sub{max-width:64ch;color:var(--muted);margin:0 0 14px;}
.meta{display:flex;gap:10px;align-items:center;font-size:13.5px;color:var(--muted);flex-wrap:wrap;}
.meta .sep{opacity:.5}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-bottom:26px;}
.tile{background:var(--surface);border:1px solid var(--hairline);border-radius:12px;
  padding:16px 18px;display:flex;flex-direction:column;gap:5px;box-shadow:var(--shadow);}
.tlabel{font-family:"Archivo",sans-serif;text-transform:uppercase;letter-spacing:.1em;
  font-size:11px;font-weight:600;color:var(--muted);}
.tval{font-family:"Archivo",sans-serif;font-weight:700;font-size:30px;line-height:1;font-variant-numeric:tabular-nums;}
.tval .unit{font-size:15px;color:var(--muted);font-weight:600;margin-left:2px;}
.tsub{font-size:12.5px;color:var(--muted);}
.panel{background:var(--surface);border:1px solid var(--hairline);border-radius:14px;
  padding:20px 22px 22px;margin-bottom:20px;box-shadow:var(--shadow);}
h2{font-family:"Archivo",sans-serif;font-weight:600;font-size:17px;margin:0 0 14px;
  display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;}
.h2sub{font-family:"IBM Plex Sans",sans-serif;font-weight:400;font-size:12.5px;color:var(--muted);}
/* controls */
.controls{display:flex;flex-wrap:wrap;gap:18px;align-items:flex-end;margin-bottom:6px;}
.fgroup{display:flex;flex-direction:column;gap:6px;}
.fglabel{font-family:"Archivo",sans-serif;font-size:10.5px;font-weight:600;text-transform:uppercase;
  letter-spacing:.09em;color:var(--muted);}
.seg{display:inline-flex;background:var(--surface-2);border:1px solid var(--hairline);border-radius:9px;padding:2px;gap:2px;}
.seg button{font-family:"IBM Plex Mono",monospace;font-size:12px;border:0;background:transparent;color:var(--muted);
  padding:4px 10px;border-radius:7px;cursor:pointer;line-height:1.4;}
.seg button:hover{color:var(--ink);}
.seg button[aria-pressed="true"]{background:var(--surface);color:var(--accent-strong);
  box-shadow:0 1px 2px rgba(0,0,0,.12);font-weight:500;}
.search{flex:1;min-width:160px;}
.search input{width:100%;font-family:"IBM Plex Mono",monospace;font-size:13px;color:var(--ink);
  background:var(--surface-2);border:1px solid var(--hairline);border-radius:9px;padding:7px 11px;}
.search input:focus{outline:2px solid var(--accent);outline-offset:1px;}
.hint{font-size:12px;color:var(--muted);margin:12px 0 0;}
/* chart */
.chart{width:100%;height:auto;}
.chart .bar{fill:var(--accent);opacity:.72;transition:opacity .12s;}
.chart .lead{fill:var(--accent-strong);}
.chart .brow.greedy .bar,.chart .brow.greedy .lead{opacity:.32;}
.chart .brow.dim{opacity:.22;}
.chart .brow.hl .bar,.chart .brow.hl .lead{fill:var(--warn);opacity:1;}
.chart .ylab{fill:var(--ink);font-family:"IBM Plex Mono",monospace;font-size:12.5px;}
.chart .ysub{fill:var(--muted);font-family:"IBM Plex Mono",monospace;font-size:10.5px;}
.chart .vlab{fill:var(--muted);font-family:"IBM Plex Mono",monospace;font-size:12px;font-variant-numeric:tabular-nums;}
.chart .brow{cursor:default;}
/* highlights strip */
.deltas{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px;}
.delta{border:1px solid var(--hairline);border-radius:9px;padding:8px 12px;background:var(--surface-2);
  display:flex;flex-direction:column;gap:2px;min-width:150px;}
.delta .dl{font-size:11px;color:var(--muted);font-family:"Archivo",sans-serif;text-transform:uppercase;letter-spacing:.06em;}
.delta .dv{font-family:"IBM Plex Mono",monospace;font-size:14px;font-weight:500;}
.delta .dv.up{color:var(--ok);} .delta .dv.down{color:var(--bad);}
/* context matrix */
.matrix{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));}
.mrow{border:1px solid var(--hairline);border-radius:10px;padding:12px 14px;background:var(--surface);}
.mrow h3{margin:0 0 9px;font-family:"Archivo",sans-serif;font-size:13.5px;font-weight:600;}
.mrow h3 .marm{color:var(--accent-strong);font-family:"IBM Plex Mono",monospace;}
.mbar{display:flex;align-items:center;gap:9px;margin:5px 0;}
.mbar .mctx{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--muted);width:34px;flex:none;text-align:right;}
.mbar .mtrack{flex:1;height:9px;background:var(--surface-2);border-radius:5px;overflow:hidden;}
.mbar .mfill{height:100%;background:var(--accent);border-radius:5px;}
.mbar .mval{font-family:"IBM Plex Mono",monospace;font-size:12px;width:44px;flex:none;font-variant-numeric:tabular-nums;}
/* table */
.scroll{overflow-x:auto;}
table{width:100%;border-collapse:collapse;font-size:13.5px;min-width:900px;}
thead th{position:sticky;top:0;z-index:2;background:var(--surface);}
th,td{text-align:left;padding:9px 11px;border-bottom:1px solid var(--hairline);white-space:nowrap;}
th{font-family:"Archivo",sans-serif;font-weight:600;font-size:11.5px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);}
th.sortable{cursor:pointer;user-select:none;}
th.sortable:hover{color:var(--ink);}
th .ind{opacity:.4;font-size:10px;margin-left:3px;}
th[data-active="1"] .ind{opacity:1;color:var(--accent-strong);}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;}
td.muted{color:var(--muted);} td.strong{font-weight:500;} td.arm{font-weight:600;color:var(--accent-strong);}
tr:last-child td{border-bottom:none;}
tbody tr:hover{background:var(--surface-2);}
tbody tr.greedy{opacity:.5;} tbody tr.greedy:hover{opacity:.85;}
tbody tr.hl{background:color-mix(in srgb,var(--warn) 15%,transparent);opacity:1;}
tr.grouphdr td{background:var(--surface-2);font-family:"Archivo",sans-serif;font-weight:600;
  font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);}
.badge{display:inline-block;margin-left:5px;font-size:9.5px;font-weight:700;font-family:"Archivo",sans-serif;
  text-transform:uppercase;letter-spacing:.04em;padding:1px 5px;border-radius:5px;vertical-align:middle;}
.badge.ok{background:var(--ok);color:#fff;} .badge.bad{background:var(--bad);color:#fff;}
.badge.neutral{background:var(--neutral);color:#fff;}
.chip{display:inline-block;padding:2px 9px;border-radius:999px;font-size:11.5px;
  font-family:"IBM Plex Mono",monospace;font-weight:500;line-height:1.5;border:1px solid transparent;}
.chip.ok{color:var(--ok);background:color-mix(in srgb,var(--ok) 14%,transparent);border-color:color-mix(in srgb,var(--ok) 30%,transparent);}
.chip.bad{color:var(--bad);background:color-mix(in srgb,var(--bad) 14%,transparent);border-color:color-mix(in srgb,var(--bad) 30%,transparent);}
.chip.run{color:var(--warn);background:color-mix(in srgb,var(--warn) 15%,transparent);border-color:color-mix(in srgb,var(--warn) 32%,transparent);}
.chip.wait{color:var(--muted);background:var(--surface-2);border-color:var(--hairline);}
.chip.neutral{color:var(--neutral);background:color-mix(in srgb,var(--neutral) 12%,transparent);border-color:color-mix(in srgb,var(--neutral) 26%,transparent);}
.empty{color:var(--muted);font-size:13px;padding:18px 4px;}
.foot,.pfoot{font-size:12.5px;color:var(--muted);margin:14px 0 0;line-height:1.6;}
.vgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:13px;}
.vcard{border:1px solid var(--hairline);border-left-width:3px;border-radius:10px;padding:13px 15px;
  background:var(--surface);display:flex;flex-direction:column;gap:7px;}
.vcard.ok{border-left-color:var(--ok);} .vcard.bad{border-left-color:var(--bad);}
.vcard.run{border-left-color:var(--warn);} .vcard.neutral{border-left-color:var(--neutral);} .vcard.wait{border-left-color:var(--hairline);}
.vtop{display:flex;justify-content:space-between;align-items:center;gap:8px;}
.vgate{font-family:"Archivo",sans-serif;font-weight:600;font-size:13.5px;}
.varm{font-size:12px;color:var(--muted);} .vnote{margin:0;font-size:12.5px;color:var(--muted);line-height:1.5;}
.queue{list-style:none;margin:0;padding:0;} .queue li{display:flex;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid var(--hairline);}
.queue li:last-child{border-bottom:none;} .queue .dot{width:9px;height:9px;border-radius:50%;background:var(--hairline);flex:none;}
.queue li.ok .dot{background:var(--ok);} .queue li.run .dot{background:var(--warn);box-shadow:0 0 0 4px color-mix(in srgb,var(--warn) 22%,transparent);}
.queue .qstage{flex:1;font-size:14px;} .queue li.wait .qstage{color:var(--muted);}
.pfoot{border-top:1px solid var(--hairline);padding-top:18px;margin-top:24px;}
#tip{position:fixed;pointer-events:none;z-index:50;background:var(--surface);border:1px solid var(--hairline);
  border-radius:9px;box-shadow:var(--shadow);padding:9px 11px;font-size:12px;max-width:260px;opacity:0;transition:opacity .1s;}
#tip.on{opacity:1;} #tip .tt{font-family:"IBM Plex Mono",monospace;font-weight:600;color:var(--accent-strong);margin-bottom:3px;}
#tip .tl{color:var(--muted);} #tip dl{margin:4px 0 0;display:grid;grid-template-columns:auto auto;gap:1px 10px;}
#tip dt{color:var(--muted);} #tip dd{margin:0;font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;}
.cmp{display:flex;flex-direction:column;gap:9px;}
.cmprow{display:flex;align-items:center;gap:12px;}
.cmprow .clab{width:160px;flex:none;font-size:12.5px;line-height:1.25;}
.cmprow .clab b{font-family:"IBM Plex Mono",monospace;color:var(--accent-strong);}
.cmprow .clab small{display:block;color:var(--muted);font-size:10.5px;margin-top:1px;}
.cmprow.greedy{opacity:.55;}
.cmprow .ctrack{flex:1;height:16px;background:var(--surface-2);border-radius:5px;overflow:hidden;}
.cmprow .cfill{height:100%;background:var(--accent);border-radius:5px;}
.cmprow.greedy .cfill{background:var(--muted);}
.cmprow .cval{width:88px;flex:none;text-align:right;font-family:"IBM Plex Mono",monospace;
  font-size:12.5px;font-variant-numeric:tabular-nums;}
.cmprow .cval small{color:var(--muted);font-size:10px;}
.gloss{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:9px 18px;}
.gitem{display:flex;gap:10px;align-items:flex-start;font-size:12.5px;line-height:1.45;}
.gitem .gk{font-family:"IBM Plex Mono",monospace;font-weight:600;color:var(--accent-strong);
  flex:none;width:18px;text-align:center;}
.gatelist{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:9px 20px;}
.gaterow{font-size:12.5px;line-height:1.45;}
.gaterow b{font-family:"Archivo",sans-serif;font-weight:600;}
.gaterow span{color:var(--muted);}
/* tabs */
.tabs{display:flex;gap:2px;flex-wrap:wrap;border-bottom:1px solid var(--hairline);margin:4px 0 24px;}
.tabs button{font-family:"Archivo",sans-serif;font-weight:600;font-size:13.5px;border:0;background:transparent;
  color:var(--muted);padding:11px 17px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;
  border-radius:8px 8px 0 0;transition:color .12s,border-color .12s;}
.tabs button:hover{color:var(--ink);background:var(--surface-2);}
.tabs button[aria-selected="true"]{color:var(--accent-strong);border-bottom-color:var(--accent);}
.tabpanel[hidden]{display:none;}
/* qualitative profile cards */
.subhead{font-family:"Archivo",sans-serif;font-weight:600;font-size:13px;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted);margin:2px 0 12px;}
.profgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:13px;margin-bottom:6px;}
.prof{border:1px solid var(--hairline);border-radius:11px;padding:14px 16px;background:var(--surface);
  display:flex;flex-direction:column;gap:9px;}
.prof .ptop{display:flex;align-items:baseline;justify-content:space-between;gap:8px;flex-wrap:wrap;}
.prof .pname{font-family:"IBM Plex Mono",monospace;font-weight:600;font-size:15px;color:var(--accent-strong);}
.prof .ptag{font-family:"Archivo",sans-serif;font-size:10.5px;font-weight:600;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);background:var(--surface-2);border:1px solid var(--hairline);
  border-radius:999px;padding:2px 9px;}
.prof .parm{font-size:11.5px;color:var(--muted);margin-top:-4px;}
.prof .pgoal{margin:0;font-size:13px;line-height:1.5;font-weight:500;}
.prof dl.pmeta{margin:0;display:flex;flex-direction:column;gap:7px;}
.prof dl.pmeta > div{display:grid;grid-template-columns:52px 1fr;gap:9px;align-items:start;}
.prof dl.pmeta dt{font-family:"Archivo",sans-serif;font-size:10px;font-weight:600;text-transform:uppercase;
  letter-spacing:.05em;color:var(--muted);padding-top:2px;}
.prof dl.pmeta dd{margin:0;font-size:12.5px;line-height:1.45;color:var(--ink);}
/* coverage matrix */
#cov-table{min-width:820px;}
#cov-table td,#cov-table th{white-space:nowrap;}
td.cov-c,th.cov-c{text-align:center;}
/* tests tab */
.tblock{margin-bottom:20px;}
.tblock:last-child{margin-bottom:0;}
.gitem .gk.kw{width:auto;min-width:104px;text-align:left;font-size:11.5px;}
.tblock .tp{margin:0;font-size:13px;line-height:1.55;max-width:80ch;}
.mchips{display:flex;flex-wrap:wrap;gap:7px;}
.mchip{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--muted);
  background:var(--surface-2);border:1px solid var(--hairline);border-radius:7px;padding:3px 9px;}
#tcov-table{min-width:760px;}
#tcov-table td,#tcov-table th{white-space:nowrap;}
#tcov-table .cov-y,#tcov-table .cov-p{font-size:13px;}
.cov-y{color:var(--ok);font-weight:600;}
.cov-n{color:var(--bad);}
.cov-d{color:var(--muted);}
.cov-p{color:var(--accent-strong);font-family:"IBM Plex Mono",monospace;font-size:12px;}
.cov-strong{font-weight:600;color:var(--ink);}
.cov-note{color:var(--muted);font-size:12px;}
tr.cov-un td{opacity:.5;}
tr.cov-un:hover td{opacity:.85;}
*:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
@media (prefers-reduced-motion:reduce){*{transition:none!important;}}
"""

EXTRA_CSS = r"""
.chart .vref{fill:var(--bad);font-family:"IBM Plex Mono",monospace;font-size:12px;}
.mbar .mval{width:66px;}
.mbar .mval.bad{color:var(--bad);}
.flag{color:var(--warn);margin-left:4px;cursor:help;}
td.num .chip{font-size:11px;}
#gate-table{min-width:860px;}
#gate-table td,#gate-table th{white-space:nowrap;}
.tturno{border:1px solid var(--hairline);border-left:3px solid var(--accent);border-radius:10px;
  padding:11px 14px;background:var(--surface-2);font-size:13px;line-height:1.55;max-width:86ch;}
.tturno code{font-family:"IBM Plex Mono",monospace;font-size:12.5px;}
"""

TEMPLATE = r"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Qwen3.8-Flash-Next Daily Driver Campaign</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;500&display=swap">
<style>/*__CSS__*/</style>
<script id="campaign-data" type="application/json">__DATA__</script>
<div class="wrap">
  <header class="head">
    <div class="eyebrow">Mac Studio M4 Max · 128 GB · local benchmark</div>
    <h1>Qwen3.8-Flash-Next daily driver: quant × runtime</h1>
    <p class="sub">Picks the most responsive setup for daily use. The cache, correctness, swap and server
    gates eliminate candidates. Among those that pass, T_turn at 32K and 128K decides. Decode only breaks ties.</p>
    <div class="meta"><span class="mono">__GENERATED__</span>
      <span class="sep">·</span><span>__VERDICTLINE__</span>
      <span class="sep">·</span><span>__PASSERS__</span></div>
  </header>

  <section class="tiles">__TILES__</section>

  <nav class="tabs" role="tablist" aria-label="Dashboard sections">
    <button role="tab" data-tab="perf" aria-selected="true">Performance</button>
    <button role="tab" data-tab="compare" aria-selected="false">Runtimes &amp; quants</button>
    <button role="tab" data-tab="tests" aria-selected="false">Tests</button>
    <button role="tab" data-tab="gates" aria-selected="false">Gates &amp; queue</button>
    <button role="tab" data-tab="glossary" aria-selected="false">Glossary</button>
  </nav>

  <div class="tabpanel" data-panel="perf" role="tabpanel">
    <section class="panel">
      <h2 id="chart-title">Responsiveness by candidate <span class="h2sub" id="chart-sub"></span></h2>
      <div class="controls" style="margin-bottom:14px;">
        <div class="fgroup"><span class="fglabel">Metric</span><div class="seg" id="metric-seg"></div></div>
        <div class="fgroup"><span class="fglabel">Band</span><div class="seg" id="band-seg"></div></div>
      </div>
      <div id="chart-host"></div>
      <div class="deltas" id="deltas"></div>
    </section>

    <section class="panel">
      <h2>Same candidate by context <span class="h2sub" id="matrix-sub"></span></h2>
      <div class="matrix" id="matrix"></div>
    </section>

    <section class="panel">
      <h2>Measured groups <span class="h2sub" id="table-count"></span></h2>
      <div class="controls">
        <div class="fgroup"><span class="fglabel">Mode</span><div class="seg" id="f-mode"></div></div>
        <div class="fgroup"><span class="fglabel">Candidate</span><div class="seg" id="f-cand"></div></div>
        <div class="fgroup"><span class="fglabel">Context</span><div class="seg" id="f-ctx"></div></div>
        <div class="fgroup"><span class="fglabel">Stage</span><div class="seg" id="f-stage"></div></div>
        <div class="fgroup search"><span class="fglabel">Search candidate / runtime</span>
          <input id="search" type="text" placeholder="e.g. mlx-serve, oQ4e, c3" autocomplete="off"></div>
      </div>
      <div class="scroll"><table><thead id="thead"></thead><tbody id="tbody"></tbody></table></div>
      <p class="foot"><span class="chip neutral">canonical</span> = vendor profile (temp 1.0), the group that
      counts toward the verdict: Stage B when it exists, otherwise Stage A, Stage 0 or probe.
      <span class="chip wait">superseded</span> = Stage A of a band that Stage B re-ran with 3 reps.
      <span class="chip wait">diag</span> = control outside the ranking (temp 0, MTP off, 102G budget).
      <span class="flag">⚠</span> wired above 102 GB (warning). <span class="flag">⚑</span> group
      caveat; hover to read it. Click a column header to sort.</p>
    </section>
  </div>

  <div class="tabpanel" data-panel="compare" role="tabpanel" hidden>
    <section class="panel">
      <h2>Runtimes <span class="h2sub">what each one aims for, how, and the cost</span></h2>
      <div class="profgrid" id="runtime-profiles"></div>
    </section>
    <section class="panel">
      <h2>Quants <span class="h2sub">target of each pack and the trade-off · bpw computed from disk size</span></h2>
      <div class="profgrid" id="quant-profiles"></div>
    </section>
    <section class="panel">
      <h2>T_turn by runtime · 32K <span class="h2sub">canonical group · lower is better</span></h2>
      <div class="cmp" id="cmp-32"></div>
    </section>
    <section class="panel">
      <h2>T_turn by runtime · 128K <span class="h2sub">canonical group · lower is better</span></h2>
      <div class="cmp" id="cmp-128"></div>
    </section>
    <section class="panel">
      <h2>Warm decode by quant · 32K <span class="h2sub">best canonical group of each pack · higher is better</span></h2>
      <div class="cmp" id="cmp-quant"></div>
    </section>
  </div>

  <div class="tabpanel" data-panel="tests" role="tabpanel" hidden>
    <section class="panel">
      <h2>What each test evaluates <span class="h2sub">cache_probe · 5 scenarios · vendor profile + diagnostics</span></h2>
      <div id="test-catalog"></div>
    </section>
    <section class="panel">
      <h2>Who ran what <span class="h2sub">scenario by group · stage and context</span></h2>
      <div class="scroll"><table id="tcov-table"><thead id="tcov-head"></thead><tbody id="tcov-body"></tbody></table></div>
      <p class="foot"><span class="cov-y">■</span> served in canonical mode ·
      <span class="cov-p">■</span> served in a diagnostic ·
      <span class="cov-n">✗</span> refused or failed ·
      <span class="cov-d">—</span> outside the stage protocol.</p>
    </section>
  </div>

  <div class="tabpanel" data-panel="gates" role="tabpanel" hidden>
    <section class="panel"><h2>Verdict by candidate</h2><div class="vgrid">__VERDICTS__</div></section>
    <section class="panel">
      <h2>Gates by band <span class="h2sub">canonical group at 32K and 128K</span></h2>
      <div class="scroll"><table id="gate-table"><thead id="gate-head"></thead><tbody id="gate-body"></tbody></table></div>
      <p class="foot">Cache = lowest hit between append and tool_turn. Correctness counts needles; a truncated answer
      does not eliminate. Server = HTTP refusal or stream error. Wired above 102 GB is a warning, not a gate.</p>
    </section>
    <section class="panel"><h2>Campaign queue</h2><ol class="queue">__QUEUE__</ol></section>
  </div>

  <div class="tabpanel" data-panel="glossary" role="tabpanel" hidden>
    <section class="panel">
      <h2>Coverage matrix <span class="h2sub">candidate × what was measured · cache, MTP, context</span></h2>
      <div class="scroll"><table id="cov-table"><thead id="cov-head"></thead><tbody id="cov-body"></tbody></table></div>
      <p class="foot">Canonical ctx = bands with a group served on the vendor profile. Diag ctx = bands with a
      control outside the ranking. Refusals show in red.</p>
    </section>
    <section class="panel"><h2>What each candidate is</h2><div class="gloss" id="arm-gloss"></div></section>
    <section class="panel"><h2>What each gate is</h2><div class="gatelist" id="gate-gloss"></div></section>
  </div>
  <footer class="pfoot">Generated by <span class="mono">consolidate_reports.py</span> +
    <span class="mono">render_overview.py</span> from <span class="mono">results/*.jsonl</span>
    (data in <span class="mono">results/reports.json</span>). Verdict in prose:
    <span class="mono">results/summary.md</span>.</footer>
</div>
<div id="tip" role="tooltip"></div>
<script>
const DATA = JSON.parse(document.getElementById("campaign-data").textContent);
const G = DATA.groups, CANDS = DATA.candidates;
const CAND = Object.fromEntries(CANDS.map(c => [c.id, c]));
const GATE_CTX = [32768, 131072];
const ctxK = (c) => (c/1024)+"K";
const STAGE_LABEL = {"0":"Stage 0","A":"Stage A","B":"Stage B","C":"Stage C","probe":"Probe","diag":"Diag"};
const rt = (g) => `${CAND[g.cand].runtime} ${CAND[g.cand].runtime_version}`;
const METRICS = {
  tturno:  {btn:"T_turn",      label:"T_turn",                  get:g=>g.t_turno_s,        better:"low",  fmt:v=>v.toFixed(2)+" s"},
  tool:    {btn:"warm TTFT",   label:"warm TTFT (tool_turn)",   get:g=>g.ttft_s.tool_turn, better:"low",  fmt:v=>v.toFixed(2)+" s"},
  cold:    {btn:"cold TTFT",   label:"cold TTFT",               get:g=>g.cold_ttft_s,      better:"low",  fmt:v=>v.toFixed(1)+" s"},
  decode:  {btn:"decode",      label:"warm decode tok/s",       get:g=>g.decode_tps,       better:"high", fmt:v=>v.toFixed(1)},
  prefill: {btn:"prefill",     label:"prefill tok/s",           get:g=>g.prefill_tps,      better:"high", fmt:v=>v.toFixed(0)},
  hit:     {btn:"cache hit",   label:"cache hit (tool_turn)",   get:g=>g.hit.tool_turn,    better:"high", fmt:v=>Math.round(v*100)+"%"},
  wired:   {btn:"wired",       label:"wired peak GB",           get:g=>g.wired_peak_gb,    better:"low",  fmt:v=>v.toFixed(1)+" GB"},
};
const state = {metric:"tturno", chartBand:"131072", mode:"canonical", cand:"all", ctx:"all",
  stage:"all", search:"", sortKey:null, sortDir:1};
const uniq = (arr) => [...new Set(arr)];
const refusalTxt = (g) => "refused " + (g.error_kinds.length ? g.error_kinds.map(k=>k.replace("http_","HTTP ")).join(", ") : "");
const candBadge = (id) => { const s = CAND[id].state;
  const cls = s==="fail"?"bad":(s==="pass"?"ok":"neutral");
  const txt = s==="pass"?"✓":(s==="fail"?"✗":"ctrl"); return `<span class="badge ${cls}">${txt}</span>`; };

function seg(host, opts, cur, onPick){
  host.innerHTML = "";
  opts.forEach(o => { const b = document.createElement("button"); b.textContent = o.label;
    b.setAttribute("aria-pressed", String(o.val===cur));
    b.onclick = () => {
      host.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", "false"));
      b.setAttribute("aria-pressed", "true");
      onPick(o.val);
    };
    host.appendChild(b); });
}
function modeOk(g){
  return state.mode==="all" || (state.mode==="canonical" ? g.canonical : g.mode==="diag");
}
function filtered(useCtx=true){
  return G.filter(g => modeOk(g) &&
    (state.cand==="all" || g.cand===state.cand) &&
    (!useCtx || state.ctx==="all" || String(g.context)===state.ctx) &&
    (state.stage==="all" || g.stage===state.stage));
}
function matchSearch(g){ const q = state.search.trim().toLowerCase(); if(!q) return false;
  const c = CAND[g.cand];
  return (g.cand+" "+c.name+" "+c.runtime+" "+c.runtime_version+" "+c.quant+" "+g.tag).toLowerCase().includes(q); }

/* ---------- chart ---------- */
function renderChart(){
  const m = METRICS[state.metric], host = document.getElementById("chart-host");
  document.getElementById("chart-sub").textContent =
    m.label + " · " + (m.better==="high"?"higher is better":"lower is better") + " · best canonical highlighted";
  let rows = filtered(false).filter(g => state.chartBand==="all" || String(g.context)===state.chartBand);
  const refused = rows.filter(g => m.get(g)==null && g.refused);
  rows = rows.filter(g => m.get(g)!=null);
  rows.sort((x,y) => m.better==="high" ? m.get(y)-m.get(x) : m.get(x)-m.get(y));
  rows = rows.slice(0, 18);
  if(!rows.length && !refused.length){ host.innerHTML = '<p class="empty">No group has this metric under the current filter.</p>'; renderDeltas(); return; }
  const max = rows.length ? Math.max(...rows.map(m.get)) : 1;
  const searching = !!state.search.trim();
  const H=34, GAP=11, PL=236, PR=74, W=820, all=rows.concat(refused), height=all.length*(H+GAP)+GAP;
  const lead = rows.find(g => g.canonical);
  let svg = `<svg viewBox="0 0 ${W} ${height}" class="chart" role="img" aria-label="${m.label} by group">`;
  all.forEach((g,i)=>{
    const y=GAP+i*(H+GAP), v=m.get(g);
    const dim = searching && !matchSearch(g) ? " dim":"";
    const hl = searching && matchSearch(g) ? " hl":"";
    const gd = g.canonical ? "" : " greedy";
    const reps = g.reps>1 ? ` · ${g.reps} reps` : "";
    svg += `<g class="brow${gd}${hl}${dim}" data-i="${G.indexOf(g)}">`
      + `<text x="${PL-12}" y="${y+H/2-4}" class="ylab" text-anchor="end">${g.cand} · ${rt(g)}</text>`
      + `<text x="${PL-12}" y="${y+H/2+11}" class="ysub" text-anchor="end">${ctxK(g.context)} · ${STAGE_LABEL[g.stage]}${g.tag?' · '+g.tag:''}${reps}</text>`;
    if(v==null){
      svg += `<text x="${PL}" y="${y+H/2}" class="vref" dominant-baseline="central">${refusalTxt(g)} · ${ctxK(g.context)}</text>`;
    } else {
      const w=Math.max(2,(v/max)*(W-PL-PR));
      svg += `<rect x="${PL}" y="${y}" width="${w.toFixed(1)}" height="${H}" rx="5" class="${g===lead?'lead':'bar'}"/>`
        + `<text x="${(PL+w+8).toFixed(1)}" y="${y+H/2}" class="vlab" dominant-baseline="central">${m.fmt(v)}</text>`;
    }
    svg += `</g>`;
  });
  host.innerHTML = svg + `</svg>`;
  host.querySelectorAll(".brow").forEach(el => {
    el.addEventListener("mousemove", e => showTip(e, G[+el.dataset.i]));
    el.addEventListener("mouseleave", hideTip);
  });
  renderDeltas();
}
function findG(cand, ctx, spec){
  return G.find(g => g.cand===cand && g.context===ctx &&
    (spec==="canonical" ? g.canonical : (g.mode==="diag" && "diag:"+g.tag===spec)));
}
function renderDeltas(){
  const m = METRICS[state.metric]; let out="";
  (DATA.deltas||[]).forEach(p=>{
    const A=findG(...p.a), B=findG(...p.b); if(!A||!B) return;
    const va=m.get(A), vb=m.get(B); if(va==null||vb==null||!vb) return;
    const g=(va-vb)/vb*100;
    const good = m.better==="high" ? g>0 : g<0;
    out += `<div class="delta"><span class="dl">${p.label}</span>`
      + `<span class="dv ${good?'up':'down'}">${g>=0?'+':''}${g.toFixed(0)}% ${m.btn}</span></div>`;
  });
  document.getElementById("deltas").innerHTML = out;
}

/* ---------- context matrix ---------- */
function renderMatrix(){
  const m = METRICS[state.metric], host = document.getElementById("matrix");
  document.getElementById("matrix-sub").textContent = m.label + " · canonical · bars scaled to 32K+";
  const canon = G.filter(g => g.canonical);
  const scale = Math.max(...canon.filter(g => g.context>=32768 && m.get(g)!=null).map(m.get), 1e-9);
  host.innerHTML = CANDS.map(c => {
    const pts = canon.filter(g => g.cand===c.id).sort((a,b)=>a.context-b.context);
    const win = c.state==="pass" && c.status==="winner" ? ' style="border-color:var(--accent)"' : '';
    const bars = pts.map(g => {
      const v = m.get(g);
      if(v==null){
        const txt = g.refused ? (g.error_kinds[0]||"refused").replace("http_","") : "—";
        return `<div class="mbar"><span class="mctx">${ctxK(g.context)}</span><span class="mtrack"></span>`
          + `<span class="mval${g.refused?' bad':''}">${txt}</span></div>`;
      }
      const w = Math.min(100, v/scale*100);
      const flag = g.note ? `<span class="flag" title="${g.note}">⚑</span>` : "";
      return `<div class="mbar"><span class="mctx">${ctxK(g.context)}</span>`
        + `<span class="mtrack"><span class="mfill" style="width:${w.toFixed(1)}%"></span></span>`
        + `<span class="mval">${m.fmt(v)}${flag}</span></div>`;
    }).join("");
    return `<div class="mrow"${win}><h3><span class="marm">${c.id}</span> · ${c.runtime} ${c.runtime_version}</h3>${bars}</div>`;
  }).join("");
}

/* ---------- table ---------- */
const COLS = [
  {key:"cand", label:"Cand", cls:"", get:g=>g.cand},
  {key:"runtime", label:"Runtime", cls:"", get:g=>rt(g)},
  {key:"quant", label:"Quant", cls:""},
  {key:"stage", label:"Stage", cls:"", get:g=>g.stage},
  {key:"context", label:"Ctx", cls:"num", get:g=>g.context},
  {key:"reps", label:"Reps", cls:"num", get:g=>g.reps},
  {key:"t_turno_s", label:"T_turn", cls:"num", get:g=>g.t_turno_s},
  {key:"tool", label:"TTFT tool", cls:"num", get:g=>g.ttft_s.tool_turn},
  {key:"cold", label:"cold TTFT", cls:"num", get:g=>g.cold_ttft_s},
  {key:"decode", label:"decode", cls:"num", get:g=>g.decode_tps},
  {key:"prefill", label:"prefill", cls:"num", get:g=>g.prefill_tps},
  {key:"hit", label:"hit tool", cls:"num", get:g=>g.hit.tool_turn},
  {key:"wired", label:"wired", cls:"num", get:g=>g.wired_peak_gb},
  {key:"correct", label:"correctness", cls:"num", get:g=>g.correct/(g.n||1)},
  {key:"gates", label:"gates", cls:""},
  {key:"mode", label:"Mode", cls:""},
];
const COLMAP = Object.fromEntries(COLS.map(c=>[c.key,c]));
function renderHead(){
  const tr = COLS.map(c=>{
    const s = !!c.get, active = state.sortKey===c.key;
    const ind = s ? `<span class="ind">${active?(state.sortDir<0?'▼':'▲'):'↕'}</span>` : "";
    return `<th class="${c.cls}${s?' sortable':''}"${s?` data-key="${c.key}"`:''}${active?' data-active="1"':''}>${c.label}${ind}</th>`;
  }).join("");
  document.getElementById("thead").innerHTML = `<tr>${tr}</tr>`;
  document.querySelectorAll("#thead th.sortable").forEach(th=>th.onclick=()=>{
    const k=th.dataset.key; if(state.sortKey===k) state.sortDir*=-1;
    else { state.sortKey=k; state.sortDir = ["decode","prefill","hit","correct"].includes(k)?-1:1; }
    renderHead(); renderTable();
  });
}
function num(v, f){ return v==null ? '<span class="cov-d">—</span>' : f(v); }
function corrChip(g){
  const cls = g.failed ? "bad" : (g.truncated ? "run" : "ok");
  const tr = g.truncated ? ` · ${g.truncated} trunc.` : "";
  return `<span class="chip ${cls}">${g.correct}/${g.n}${tr}</span>`;
}
function gateChip(g){
  if(g.mode==="diag") return '<span class="chip wait">excluded</span>';
  if(g.gates_failed.length) return `<span class="chip bad" title="${g.gates_failed.join(', ')}">fail</span>`;
  if(!GATE_CTX.includes(g.context)) return '<span class="chip wait">no gate</span>';
  return '<span class="chip ok">pass</span>';
}
function modeChip(g){
  if(g.mode==="diag") return '<span class="chip wait">diag</span>';
  return g.canonical ? '<span class="chip neutral">canonical</span>' : '<span class="chip wait">superseded</span>';
}
function cell(g){
  const c = CAND[g.cand];
  const flag = g.note ? `<span class="flag" title="${g.note}">⚑</span>` : "";
  const warn = (g.warnings||[]).includes("wired>102") ? '<span class="flag" title="wired above 102 GB (warning)">⚠</span>' : "";
  const tt = g.refused ? `<span class="chip bad">${(g.error_kinds[0]||"refused").replace("http_","")}</span>`
    : num(g.t_turno_s, v=>v.toFixed(2)+'s');
  return `<td class="mono arm">${g.cand}${candBadge(g.cand)}</td>`
    + `<td>${rt(g)}</td>`
    + `<td><span class="cov-p">${c.quant}</span></td>`
    + `<td>${STAGE_LABEL[g.stage]}${g.tag?` <span class="muted">${g.tag}</span>`:""}${flag}</td>`
    + `<td class="num mono">${ctxK(g.context)}</td>`
    + `<td class="num mono">${g.reps}</td>`
    + `<td class="num mono strong">${tt}</td>`
    + `<td class="num mono">${num(g.ttft_s.tool_turn, v=>v.toFixed(2)+'s')}</td>`
    + `<td class="num mono">${num(g.cold_ttft_s, v=>v.toFixed(1)+'s')}</td>`
    + `<td class="num mono" title="${g.decode_range?'range '+g.decode_range.join('–'):''}">${num(g.decode_tps, v=>v.toFixed(1))}</td>`
    + `<td class="num mono">${num(g.prefill_tps, v=>v.toFixed(0))}</td>`
    + `<td class="num mono">${num(g.hit.tool_turn, v=>Math.round(v*100)+'%')}</td>`
    + `<td class="num mono">${num(g.wired_peak_gb, v=>v.toFixed(1))}${warn}</td>`
    + `<td class="num">${corrChip(g)}</td>`
    + `<td>${gateChip(g)}</td>`
    + `<td>${modeChip(g)}</td>`;
}
function renderTable(){
  let rows = filtered();
  const q = state.search.trim();
  document.getElementById("table-count").textContent =
    `${rows.length} of ${G.length} groups` + (q?` · search "${q}"`:"");
  if(state.sortKey){
    const get = COLMAP[state.sortKey].get, d = state.sortDir;
    rows = rows.slice().sort((x,y)=>{ const a=get(x), b=get(y);
      if(a==null) return 1; if(b==null) return -1;
      return typeof a==="string" ? d*a.localeCompare(b) : d*(a-b); });
  }
  const tb = document.getElementById("tbody");
  if(!rows.length){ tb.innerHTML = `<tr><td colspan="${COLS.length}" class="empty">Nothing matches the filter.</td></tr>`; return; }
  tb.innerHTML = rows.map(g => {
    const hl = q && matchSearch(g) ? " hl" : "";
    return `<tr class="${g.canonical?'':'greedy'}${hl}">${cell(g)}</tr>`;
  }).join("");
}

/* ---------- tooltip ---------- */
const tip = document.getElementById("tip");
function showTip(e, g){
  const c = CAND[g.cand], s = (v,d)=> v==null?'—':v.toFixed(d)+' s';
  tip.innerHTML = `<div class="tt">${g.cand} · ${c.quant}</div>`
    + `<div class="tl">${rt(g)} · ${STAGE_LABEL[g.stage]}${g.tag?' · '+g.tag:''}</div>`
    + `<dl><dt>context</dt><dd>${ctxK(g.context)} · ${g.reps} rep${g.reps>1?'s':''}</dd>`
    + (g.refused ? `<dt>result</dt><dd>${refusalTxt(g)}</dd>` : "")
    + `<dt>T_turn</dt><dd>${s(g.t_turno_s,2)}</dd>`
    + `<dt>TTFT tool</dt><dd>${s(g.ttft_s.tool_turn,2)}</dd>`
    + `<dt>cold TTFT</dt><dd>${s(g.cold_ttft_s,1)}</dd>`
    + `<dt>decode</dt><dd>${g.decode_tps!=null?g.decode_tps.toFixed(1)+' tok/s':'—'}</dd>`
    + `<dt>hit tool</dt><dd>${g.hit.tool_turn!=null?Math.round(g.hit.tool_turn*100)+'%':'—'}</dd>`
    + `<dt>wired</dt><dd>${g.wired_peak_gb!=null?g.wired_peak_gb.toFixed(1)+' GB':'—'}</dd>`
    + `<dt>correctness</dt><dd>${g.correct}/${g.n}${g.truncated?' · '+g.truncated+' trunc.':''}</dd></dl>`
    + (g.note ? `<div class="tl" style="margin-top:5px">${g.note}</div>` : "");
  tip.classList.add("on");
  const pad=14; let x=e.clientX+pad, y=e.clientY+pad;
  if(x+tip.offsetWidth>innerWidth) x=e.clientX-tip.offsetWidth-pad;
  if(y+tip.offsetHeight>innerHeight) y=e.clientY-tip.offsetHeight-pad;
  tip.style.left=x+"px"; tip.style.top=y+"px";
}
function hideTip(){ tip.classList.remove("on"); }

/* ---------- controls ---------- */
function initControls(){
  const ctxs = uniq(G.map(g=>g.context)).sort((a,b)=>a-b);
  seg(document.getElementById("metric-seg"),
    Object.entries(METRICS).map(([k,m])=>({val:k,label:m.btn})),
    state.metric, v=>{ state.metric=v; renderChart(); renderMatrix(); });
  seg(document.getElementById("band-seg"),
    ctxs.map(c=>({val:String(c),label:ctxK(c)})).concat([{val:"all",label:"all"}]),
    state.chartBand, v=>{ state.chartBand=v; renderChart(); });
  seg(document.getElementById("f-mode"),
    [{val:"canonical",label:"canonical"},{val:"diag",label:"diag"},{val:"all",label:"all"}],
    state.mode, v=>{ state.mode=v; refresh(); });
  seg(document.getElementById("f-cand"),
    [{val:"all",label:"all"}].concat(CANDS.map(c=>({val:c.id,label:c.id}))),
    state.cand, v=>{ state.cand=v; refresh(); });
  seg(document.getElementById("f-ctx"),
    [{val:"all",label:"all"}].concat(ctxs.map(c=>({val:String(c),label:ctxK(c)}))),
    state.ctx, v=>{ state.ctx=v; renderTable(); });
  const stages = ["0","A","B","C","probe","diag"].filter(s=>G.some(g=>g.stage===s));
  seg(document.getElementById("f-stage"),
    [{val:"all",label:"all"}].concat(stages.map(s=>({val:s,label:STAGE_LABEL[s]}))),
    state.stage, v=>{ state.stage=v; refresh(); });
}

/* ---------- runtimes & quants ---------- */
function cmpBar(lab, sub, val, max, txt, extraCls){
  const w = val==null ? 0 : Math.max(1, val/max*100);
  return `<div class="cmprow${extraCls||''}"><div class="clab"><b>${lab}</b><small>${sub}</small></div>`
    + `<div class="ctrack"><div class="cfill" style="width:${w.toFixed(1)}%"></div></div>`
    + `<div class="cval">${txt}</div></div>`;
}
function renderCmpT(hostId, ctx){
  const rows = G.filter(g=>g.canonical && g.context===ctx);
  const ok = rows.filter(g=>g.t_turno_s!=null).sort((a,b)=>a.t_turno_s-b.t_turno_s);
  const max = Math.max(...ok.map(g=>g.t_turno_s));
  document.getElementById(hostId).innerHTML = ok.map(g =>
      cmpBar(`${g.cand} ${CAND[g.cand].runtime}`, `${CAND[g.cand].runtime_version} · ${STAGE_LABEL[g.stage]} · ${g.reps} rep${g.reps>1?'s':''}`,
        g.t_turno_s, max, `${g.t_turno_s.toFixed(2)} <small>s</small>`)).join("")
    + rows.filter(g=>g.t_turno_s==null && g.refused).map(g =>
      cmpBar(`${g.cand} ${CAND[g.cand].runtime}`, `${CAND[g.cand].runtime_version} · ${STAGE_LABEL[g.stage]}`,
        null, max, `<small>${refusalTxt(g)}</small>`, " greedy")).join("");
}
function renderCmpQuant(){
  const by = {};
  G.filter(g=>g.canonical && g.context===32768 && g.decode_tps!=null).forEach(g=>{
    const q = CAND[g.cand].quant; if(!by[q] || g.decode_tps>by[q].decode_tps) by[q]=g; });
  const rows = Object.entries(by).sort((a,b)=>b[1].decode_tps-a[1].decode_tps);
  const max = Math.max(...rows.map(r=>r[1].decode_tps));
  document.getElementById("cmp-quant").innerHTML = rows.map(([q,g]) =>
    cmpBar(q, `${CAND[g.cand].bpw} bpw · ${CAND[g.cand].disk_gb.toFixed(0)} GB · best ${g.cand}`,
      g.decode_tps, max, `${g.decode_tps.toFixed(1)} <small>tok/s</small>`)).join("");
}
function profCard(p){
  const tagRow = p.bpw ? `<span class="ptag">${p.bpw} bpw · ${p.runtime}</span>` : `<span class="ptag">${p.tag}</span>`;
  const arm = p.arms ? `<div class="parm mono">candidate ${p.arms}</div>` : "";
  const how = p.how ? `<div><dt>How</dt><dd>${p.how}</dd></div>` : "";
  return `<div class="prof"><div class="ptop"><span class="pname">${p.name}</span>${tagRow}</div>`
    + arm + `<p class="pgoal">${p.goal}</p>`
    + `<dl class="pmeta">${how}<div><dt>Cost</dt><dd>${p.cost}</dd></div></dl></div>`;
}
function renderProfiles(){
  document.getElementById("runtime-profiles").innerHTML = (DATA.runtime_profiles||[]).map(profCard).join("");
  document.getElementById("quant-profiles").innerHTML = (DATA.quant_profiles||[]).map(profCard).join("");
}

/* ---------- tests ---------- */
function renderTests(){
  const c = DATA.test_catalog || {};
  const gloss = (items, title)=> items && items.length
    ? `<div class="tblock"><div class="subhead">${title}</div><div class="gloss">`
      + items.map(x=>`<div class="gitem"><span class="gk kw">${x.key}</span><span>${x.eval}</span></div>`).join("")
      + `</div></div>` : "";
  let html = "";
  if(c.t_turno) html += `<div class="tblock"><div class="subhead">Decision metric</div><p class="tturno">${c.t_turno}</p></div>`;
  html += gloss(c.scenarios, "cache_probe scenarios");
  html += gloss(c.modes, "Sampling modes");
  html += gloss(c.correctness, "Correctness");
  if(c.metrics) html += `<div class="tblock"><div class="subhead">Per-record metrics</div>`
    + `<div class="mchips">${c.metrics.map(m=>`<span class="mchip">${m}</span>`).join("")}</div></div>`;
  document.getElementById("test-catalog").innerHTML = html;
}
function renderTestCoverage(){
  const scen = ["cold","identical","append","middle_mutation","tool_turn"];
  const short = {cold:"cold",identical:"ident.",append:"append",middle_mutation:"mid.mut",tool_turn:"tool_turn"};
  document.getElementById("tcov-head").innerHTML = "<tr><th>Cand</th><th>Runtime</th><th>Stage</th><th>Ctx</th><th>Reps</th>"
    + scen.map(s=>`<th class="cov-c">${short[s]}</th>`).join("") + "</tr>";
  document.getElementById("tcov-body").innerHTML = G.map(g=>{
    const cellFor = s => !g.scenarios_run.includes(s) ? '<span class="cov-d">—</span>'
      : (!g.scenarios_served.includes(s) ? '<span class="cov-n">✗</span>'
      : (g.mode==="diag" ? '<span class="cov-p">■</span>' : '<span class="cov-y">■</span>'));
    return `<tr${g.canonical||g.mode==="diag"?'':' class="cov-un"'}><td class="mono arm">${g.cand}</td><td>${rt(g)}</td>`
      + `<td>${STAGE_LABEL[g.stage]}${g.tag?` <span class="cov-note">${g.tag}</span>`:""}</td>`
      + `<td class="mono">${ctxK(g.context)}</td><td class="mono">${g.reps}</td>`
      + scen.map(s=>`<td class="cov-c">${cellFor(s)}</td>`).join("") + "</tr>";
  }).join("");
}

/* ---------- gates ---------- */
function renderGateTable(){
  document.getElementById("gate-head").innerHTML = "<tr><th>Cand</th><th>Runtime</th><th>Band</th><th>Source</th>"
    + "<th class='cov-c'>Cache ≥ 0.90</th><th class='cov-c'>Correctness</th><th class='cov-c'>Swap ≤ 0.5</th>"
    + "<th class='cov-c'>Server</th><th class='cov-c'>Wired</th><th>Result</th></tr>";
  const y = t => `<span class="cov-y">✓ ${t}</span>`, n = t => `<span class="cov-n">✗ ${t}</span>`;
  const rows = [];
  CANDS.forEach(c => GATE_CTX.forEach(ctx => {
    const g = G.find(x => x.canonical && x.cand===c.id && x.context===ctx);
    if(!g) return;
    const hits = [g.hit.append, g.hit.tool_turn].filter(v=>v!=null);
    const cache = hits.length ? (Math.min(...hits)>=0.90 ? y(Math.min(...hits).toFixed(2)) : n(Math.min(...hits).toFixed(2)))
      : (g.refused ? n("no data") : '<span class="cov-d">—</span>');
    const corr = g.refused ? n("refused") : (g.failed ? n(g.failed+" failed") : y(g.truncated? g.truncated+" trunc." : g.correct+"/"+g.n));
    const swap = g.swap_delta_gb<=0.5 ? y(g.swap_delta_gb.toFixed(2)) : n(g.swap_delta_gb.toFixed(2));
    const srv = (g.refused || g.error_kinds.length || g.stream_failures)
      ? n(g.error_kinds.map(k=>k.replace("http_","")).join(",")||"error") : y("0 errors");
    const wired = g.wired_peak_gb==null ? '<span class="cov-d">—</span>'
      : (g.wired_peak_gb>102 ? `<span class="cov-p">⚠ ${g.wired_peak_gb.toFixed(1)}</span>` : `<span class="mono">${g.wired_peak_gb.toFixed(1)}</span>`);
    const res = g.gates_failed.length ? `<span class="chip bad" title="${g.gates_failed.join(', ')}">fail</span>` : '<span class="chip ok">pass</span>';
    rows.push(`<tr><td class="mono arm">${c.id}</td><td>${c.runtime} ${c.runtime_version}</td><td class="mono">${ctxK(ctx)}</td>`
      + `<td>${STAGE_LABEL[g.stage]} · ${g.reps} rep${g.reps>1?'s':''}</td>`
      + `<td class="cov-c">${cache}</td><td class="cov-c">${corr}</td><td class="cov-c">${swap}</td>`
      + `<td class="cov-c">${srv}</td><td class="cov-c">${wired}</td><td>${res}</td></tr>`);
  }));
  document.getElementById("gate-body").innerHTML = rows.join("");
}

/* ---------- glossary ---------- */
function renderCoverage(){
  const cols = ["Cand","Runtime","Quant / model","bpw","Disk","Cache","Speculation","Canonical ctx","Diag ctx","Ceiling","Status"];
  document.getElementById("cov-head").innerHTML = "<tr>" + cols.map(c=>`<th>${c}</th>`).join("") + "</tr>";
  document.getElementById("cov-body").innerHTML = CANDS.map(c=>{
    const mine = G.filter(g=>g.cand===c.id);
    const canon = mine.filter(g=>g.canonical).map(g => g.refused
      ? `<span class="cov-n">${ctxK(g.context)}</span>` : `<span class="cov-strong">${ctxK(g.context)}</span>`).join(", ");
    const diag = uniq(mine.filter(g=>g.mode==="diag").map(g=>ctxK(g.context))).join(", ");
    const st = c.state==="fail"?"bad":(c.state==="pass"?"ok":"neutral");
    return `<tr><td class="mono arm">${c.id}</td><td>${c.runtime} ${c.runtime_version}</td>`
      + `<td><span class="cov-p">${c.quant}</span> <span class="cov-d">${c.model} · ${c.revision}</span></td>`
      + `<td class="mono">${c.bpw}</td><td class="mono">${c.disk_gb.toFixed(0)} GB</td>`
      + `<td class="cov-note">${c.cache}</td><td class="cov-note">${c.spec}</td>`
      + `<td class="mono">${canon||'<span class="cov-d">—</span>'}</td>`
      + `<td class="mono">${diag||'<span class="cov-d">—</span>'}</td>`
      + `<td class="cov-note">${c.ceiling}</td><td><span class="chip ${st}">${c.status}</span></td></tr>`;
  }).join("");
}
function renderGlossaries(){
  document.getElementById("arm-gloss").innerHTML = CANDS.map(c =>
    `<div class="gitem"><span class="gk">${c.id}</span><span><b>${c.name}</b> — ${c.note}</span></div>`).join("");
  document.getElementById("gate-gloss").innerHTML = (DATA.gates_glossary||[]).map(x =>
    `<div class="gaterow"><b>${x.gate}</b> — <span>${x.desc}</span></div>`).join("");
}

/* ---------- tabs ---------- */
function initTabs(){
  const tabs = [...document.querySelectorAll(".tabs button")];
  const panels = [...document.querySelectorAll(".tabpanel")];
  tabs.forEach(t => t.onclick = () => {
    tabs.forEach(x => x.setAttribute("aria-selected", String(x===t)));
    panels.forEach(p => p.hidden = p.dataset.panel !== t.dataset.tab);
  });
}

function refresh(){ renderChart(); renderTable(); }
document.getElementById("search").addEventListener("input", e=>{ state.search=e.target.value; renderChart(); renderTable(); });

initTabs(); initControls(); renderHead(); renderChart(); renderMatrix();
renderProfiles(); renderCmpT("cmp-32", 32768); renderCmpT("cmp-128", 131072); renderCmpQuant();
renderTests(); renderTestCoverage(); renderGateTable(); renderCoverage(); renderGlossaries(); renderTable();
</script>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(REPORTS_JSON))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    data = json.loads(Path(a.data).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.write_text(render(data), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
