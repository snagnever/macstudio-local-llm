#!/usr/bin/env python3
"""Render results/overview.json into an interactive dashboard (overview.html).

Data is embedded as JSON; the chart, table, filters, sorting, metric selector,
context matrix, search and tooltips are built client-side in vanilla JS.

    python3 bench/qwen3.8-prefix-cache/scripts/consolidate.py
    python3 bench/qwen3.8-prefix-cache/scripts/render_overview.py
"""

from __future__ import annotations

import html
import json
from pathlib import Path


CAMPAIGN = Path(__file__).resolve().parents[1]
RESULTS = CAMPAIGN / "results"
OVERVIEW = RESULTS / "overview.json"
OUT = RESULTS / "overview.html"

STATE_CLASS = {
    "pass": "ok", "done": "ok", "control": "neutral", "fail": "bad",
    "running": "run", "pending": "wait", "blocked": "bad",
}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def fnum(value, digits=1):
    return "—" if value is None else f"{value:.{digits}f}"


def build_tiles(data: dict) -> str:
    arms = data["arms"]
    canonical = [a for a in arms if a["mode"] == "canonical"]
    gate_pass = sum(
        1 for name, g in data["gates"].items()
        if isinstance(g, dict) and g.get("passed") is True and "greedy" not in name
    )
    best = max((a for a in canonical if a.get("decode_tps")),
               key=lambda a: a["decode_tps"], default=None)
    done = sum(1 for q in data["queue"] if q["status"] == "done")
    best_val = (f'{fnum(best["decode_tps"])} <span class="unit">tok/s</span>'
                if best else "—")
    best_sub = f'{best["arm"]} · {best["model"]}' if best else ""
    tiles = [
        ("Canonical groups", str(len(canonical)), "measured with vendor sampling"),
        ("Best decode", best_val, best_sub),
        ("Gates passed", str(gate_pass), "canonical gates passing"),
        ("Stages", f'{done}<span class="unit">/{len(data["queue"])}</span>', "completed"),
    ]
    return "".join(
        f'<div class="tile"><span class="tlabel">{esc(t)}</span>'
        f'<span class="tval">{v}</span><span class="tsub">{esc(s)}</span></div>'
        for t, v, s in tiles
    )


def build_verdicts(verdicts: list[dict]) -> str:
    cards = []
    for v in verdicts:
        cls = STATE_CLASS.get(v["state"], "neutral")
        cards.append(
            f'<div class="vcard {cls}"><div class="vtop">'
            f'<span class="vgate">{esc(v["gate"])}</span>'
            f'<span class="chip {cls}">{esc(v["state"])}</span></div>'
            f'<div class="varm mono">{esc(v["arm"])}</div>'
            f'<p class="vnote">{esc(v["note"])}</p></div>'
        )
    return "".join(cards)


def build_queue(queue: list[dict]) -> str:
    items = []
    for q in queue:
        cls = STATE_CLASS.get(q["status"], "wait")
        items.append(
            f'<li class="{cls}"><span class="dot"></span>'
            f'<span class="qstage">{esc(q["stage"])}</span>'
            f'<span class="chip {cls}">{esc(q["status"])}</span></li>'
        )
    return "".join(items)


def render(data: dict) -> str:
    omlx_gate = data["gates"].get("omlx-mtp-gate", {})
    gate_line = "L MTP gate: " + ("PASSED" if omlx_gate.get("passed") else "open")
    return (
        TEMPLATE
        .replace("/*__CSS__*/", CSS)
        .replace("__DATA__", json.dumps(data, ensure_ascii=False))
        .replace("__TILES__", build_tiles(data))
        .replace("__VERDICTS__", build_verdicts(data["verdicts"]))
        .replace("__QUEUE__", build_queue(data["queue"]))
        .replace("__GENERATED__", esc(data["generated_at"]))
        .replace("__GATELINE__", esc(gate_line))
    )


CSS = """
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


TEMPLATE = """<title>Qwen3.8 Prefix-Cache Campaign</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;500&display=swap">
<style>/*__CSS__*/</style>
<script id="campaign-data" type="application/json">__DATA__</script>
<div class="wrap">
  <header class="head">
    <div class="eyebrow">Mac Studio M4 Max · 128 GB · local benchmark</div>
    <h1>Qwen3.8-27B — prefix cache, MTP &amp; runtime</h1>
    <p class="sub">Selection of the highest-performance setup. Correctness is an eliminatory gate;
    among the correct ones, warm total time, TTFT and sustained decode decide.</p>
    <div class="meta"><span class="mono">__GENERATED__</span>
      <span class="sep">·</span><span>__GATELINE__</span></div>
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
      <h2 id="chart-title">Sustained decode <span class="h2sub" id="chart-sub"></span></h2>
      <div class="controls" style="margin-bottom:14px;">
        <div class="fgroup"><span class="fglabel">Metric</span>
          <div class="seg" id="metric-seg"></div></div>
      </div>
      <div id="chart-host"></div>
      <div class="deltas" id="deltas"></div>
    </section>

    <section class="panel">
      <h2>Same model per context <span class="h2sub">decode tok/s · canonical</span></h2>
      <div class="matrix" id="matrix"></div>
    </section>

    <section class="panel">
      <h2>Measured arms <span class="h2sub" id="table-count"></span></h2>
      <div class="controls">
        <div class="fgroup"><span class="fglabel">Mode</span><div class="seg" id="f-mode"></div></div>
        <div class="fgroup"><span class="fglabel">Runtime</span><div class="seg" id="f-runtime"></div></div>
        <div class="fgroup"><span class="fglabel">Context</span><div class="seg" id="f-ctx"></div></div>
        <div class="fgroup"><span class="fglabel">Class</span><div class="seg" id="f-class"></div></div>
        <div class="fgroup"><span class="fglabel">Group</span><div class="seg" id="f-group"></div></div>
        <div class="fgroup search"><span class="fglabel">Search arm / model</span>
          <input id="search" type="text" placeholder="e.g.: MTPLX, oQ8e, L" autocomplete="off"></div>
      </div>
      <div class="scroll"><table><thead id="thead"></thead><tbody id="tbody"></tbody></table></div>
      <p class="foot"><span class="chip neutral">canonical</span> = vendor sampling
      (decision metric); <span class="chip wait">greedy</span> = diagnostic
      <span class="mono">temp=0</span>, dimmed, does not count for verdict and inflates decode.
      E2E does not compare across classes (<span class="mono">code</span> short vs
      <span class="mono">audit</span> long). Arms with cache off (W/X) have cold TTFT by design.</p>
    </section>
  </div>

  <div class="tabpanel" data-panel="compare" role="tabpanel" hidden>
    <section class="panel">
      <h2>Runtime offerings <span class="h2sub">what each one seeks, how, and the cost</span></h2>
      <div class="profgrid" id="runtime-profiles"></div>
    </section>
    <section class="panel">
      <h2>Quantization offerings <span class="h2sub">target of each quant and the trade-off it makes</span></h2>
      <div class="profgrid" id="quant-profiles"></div>
    </section>
    <section class="panel">
      <h2>Decode measured per runtime <span class="h2sub">best decode per runtime · canonical; greedy dimmed</span></h2>
      <div class="cmp" id="runtimes"></div>
    </section>
    <section class="panel">
      <h2>Decode measured per quant <span class="h2sub">best decode per bits/weight · fewer bits tends to faster</span></h2>
      <div class="cmp" id="quants"></div>
    </section>
  </div>

  <div class="tabpanel" data-panel="tests" role="tabpanel" hidden>
    <section class="panel">
      <h2>What each test evaluates <span class="h2sub">cache-probe (5 scenarios × 2 modes) + tool loop</span></h2>
      <div id="test-catalog"></div>
    </section>
    <section class="panel">
      <h2>Which configurations ran which tests <span class="h2sub">scenario per arm · mode measured</span></h2>
      <div class="scroll"><table id="tcov-table"><thead id="tcov-head"></thead><tbody id="tcov-body"></tbody></table></div>
      <p class="foot"><span class="cov-y">■</span> canonical (temp=1, counts for verdict) ·
      <span class="cov-p">■</span> greedy only (temp=0, diagnostic) ·
      <span class="cov-d">—</span> not run. The <b>tool loop</b> column shows majority (passes/total).
      Not every arm runs all scenarios — depends on the gate.</p>
    </section>
  </div>

  <div class="tabpanel" data-panel="gates" role="tabpanel" hidden>
    <section class="panel"><h2>Gate verdicts</h2><div class="vgrid">__VERDICTS__</div></section>
    <section class="panel"><h2>Campaign queue</h2><ol class="queue">__QUEUE__</ol></section>
  </div>

  <div class="tabpanel" data-panel="glossary" role="tabpanel" hidden>
    <section class="panel">
      <h2>Coverage matrix <span class="h2sub">quant/model + runtime × what has been measured · cache, MTP, context</span></h2>
      <div class="scroll"><table id="cov-table"><thead id="cov-head"></thead><tbody id="cov-body"></tbody></table></div>
      <p class="foot"><span class="mono">canonical</span> = temp=1 (counts for verdict);
      <span class="mono">greedy</span> = temp=0 (diagnostic). <b>—</b> in context = planned arm,
      not yet run. MTP: <span class="mono">✓</span> native, <span class="mono">draft</span> via draft
      model, <span class="mono">auto</span> vendor default.</p>
    </section>
    <section class="panel"><h2>What each arm is</h2><div class="gloss" id="arm-gloss"></div></section>
    <section class="panel"><h2>What each gate is</h2><div class="gatelist" id="gate-gloss"></div></section>
  </div>
  <footer class="pfoot">Generated by <span class="mono">consolidate.py</span> +
    <span class="mono">render_overview.py</span>. Raw data not versioned in
    <span class="mono">results/</span>.</footer>
</div>
<div id="tip" role="tooltip"></div>
<script>
const DATA = JSON.parse(document.getElementById("campaign-data").textContent);
const ARMS = DATA.arms, TL = DATA.tool_loop || {};
const VERDICT = {}; (DATA.verdicts||[]).forEach(v => { (v.arm||"").split("/").forEach(a => VERDICT[a.trim()] = v.state); });
const METRICS = {
  decode:   {btn:"decode",    label:"decode tok/s",     key:"decode_tps",        better:"high", fmt:v=>v.toFixed(1)},
  ttft:     {btn:"TTFT q.",   label:"warm TTFT",        key:"ttft_identical_ms", better:"low",  fmt:v=>(v/1000).toFixed(1)+"s"},
  ttftcold: {btn:"TTFT cold", label:"cold TTFT",        key:"ttft_cold_ms",      better:"low",  fmt:v=>(v/1000).toFixed(1)+"s"},
  e2e:      {btn:"E2E q.",    label:"warm E2E",         key:"e2e_identical_ms",  better:"low",  fmt:v=>(v/1000).toFixed(1)+"s"},
  cache:    {btn:"cache",     label:"cache hit",        key:"cache_hit_identical", better:"high", fmt:v=>Math.round(v*100)+"%"},
};
const state = {
  metric:"decode", mode:"all", runtime:"all", ctx:"all", cls:"all",
  group:"none", search:"", sortKey:"decode_tps", sortDir:-1,
};
const uniq = (arr) => [...new Set(arr)];
const ctxK = (c) => (c/1024)+"K";
const shortModel = (m) => m.replace(" Optimized Speed","").replace("MLX-Serve ","").replace(/ \(.*\)/,"");
const badge = (a) => { const s = VERDICT[a]; if(!s) return "";
  const cls = s==="fail"?"bad":(s==="control"?"neutral":(s==="pass"?"ok":"")); if(!cls) return "";
  const txt = s==="pass"?"gate ✓":(s==="fail"?"gate ✗":"ctrl"); return `<span class="badge ${cls}">${txt}</span>`; };

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
function filtered(){
  return ARMS.filter(a =>
    (state.mode==="all"    || a.mode===state.mode) &&
    (state.runtime==="all" || a.runtime===state.runtime) &&
    (state.ctx==="all"     || String(a.context)===state.ctx) &&
    (state.cls==="all"     || (a.content_class||"")===state.cls));
}
function matchSearch(a){ const q = state.search.trim().toLowerCase(); if(!q) return false;
  return (a.arm+" "+a.runtime+" "+a.model+" "+a.config).toLowerCase().includes(q); }

/* ---------- chart ---------- */
function renderChart(){
  const m = METRICS[state.metric], host = document.getElementById("chart-host");
  document.getElementById("chart-sub").textContent =
    m.label + " · " + (m.better==="high"?"higher is better":"lower is better") + " · canonical highlighted";
  let rows = filtered().filter(a => a[m.key]!=null);
  rows.sort((x,y) => m.better==="high" ? y[m.key]-x[m.key] : x[m.key]-y[m.key]);
  rows = rows.slice(0, 16);
  if(!rows.length){ host.innerHTML = '<p class="empty">No arm with this metric in the current filter.</p>'; document.getElementById("deltas").innerHTML=""; return; }
  const max = Math.max(...rows.map(a=>a[m.key]));
  const searching = !!state.search.trim();
  const H=34, G=11, PL=196, PR=64, W=820, height=rows.length*(H+G)+G;
  let best = rows[0][m.key];
  let svg = `<svg viewBox="0 0 ${W} ${height}" class="chart" role="img" aria-label="${m.label} per arm">`;
  rows.forEach((a,i)=>{
    const y=G+i*(H+G), w=Math.max(2,(a[m.key]/max)*(W-PL-PR));
    const lead = a[m.key]===best && a.mode==="canonical";
    const gd = a.mode==="greedy" ? " greedy":"";
    const hl = searching && matchSearch(a) ? " hl":"";
    const dim = searching && !matchSearch(a) ? " dim":"";
    svg += `<g class="brow${gd}${hl}${dim}" data-arm="${a.arm}" data-ctx="${a.context}" data-cls="${a.content_class||''}">`
      + `<text x="${PL-12}" y="${y+H/2-4}" class="ylab" text-anchor="end">${a.arm} · ${shortModel(a.model)}</text>`
      + `<text x="${PL-12}" y="${y+H/2+11}" class="ysub" text-anchor="end">${a.runtime} · ${ctxK(a.context)} · ${a.mode}</text>`
      + `<rect x="${PL}" y="${y}" width="${w.toFixed(1)}" height="${H}" rx="5" class="${lead?'lead':'bar'}"/>`
      + `<text x="${(PL+w+8).toFixed(1)}" y="${y+H/2}" class="vlab" dominant-baseline="central">${m.fmt(a[m.key])}</text>`
      + `</g>`;
  });
  svg += `</svg>`; host.innerHTML = svg;
  host.querySelectorAll(".brow").forEach(g => {
    g.addEventListener("mousemove", e => showTip(e, g.dataset.arm, +g.dataset.ctx, g.dataset.cls));
    g.addEventListener("mouseleave", hideTip);
  });
  renderDeltas();
}
function findArm(arm,ctx,cls){ return ARMS.find(a=>a.arm===arm&&a.context===ctx&&(a.content_class||"")===cls); }
function renderDeltas(){
  const host = document.getElementById("deltas");
  const pairs = [
    {label:"MTP · L vs K", a:["L",32768,"code"], b:["K",32768,"code"]},
    {label:"DFlash2 · X vs W", a:["X",32768,"audit_retrieval"], b:["W",32768,"audit_retrieval"]},
    {label:"SpecPrefill · M vs L", a:["M",16384,"audit_retrieval"], b:["L",16384,"audit_retrieval"]},
  ];
  const m = METRICS[state.metric]; let out="";
  pairs.forEach(p=>{
    const A=findArm(...p.a), B=findArm(...p.b); if(!A||!B||A[m.key]==null||B[m.key]==null) return;
    const g=(A[m.key]-B[m.key])/B[m.key]*100;
    const good = (m.better==="high") ? g>0 : g<0;
    out += `<div class="delta"><span class="dl">${p.label}</span>`
      + `<span class="dv ${good?'up':'down'}">${g>=0?'+':''}${g.toFixed(0)}% ${m.label.split(' ')[0]}</span></div>`;
  });
  host.innerHTML = out;
}

/* ---------- context matrix ---------- */
function renderMatrix(){
  const host = document.getElementById("matrix");
  const canon = ARMS.filter(a=>a.mode==="canonical" && a.decode_tps!=null);
  const byArm = {};
  canon.forEach(a=>{ (byArm[a.arm] ||= {arm:a.arm, model:a.model, runtime:a.runtime, pts:[]}).pts.push(a); });
  const rows = Object.values(byArm).sort((x,y)=> y.pts.length-x.pts.length ||
    Math.max(...y.pts.map(p=>p.decode_tps))-Math.max(...x.pts.map(p=>p.decode_tps)));
  const gmax = Math.max(...canon.map(a=>a.decode_tps));
  host.innerHTML = rows.map(r=>{
    const pts = r.pts.sort((a,b)=>a.context-b.context);
    const multi = pts.length>1 ? ' style="border-color:var(--accent)"' : '';
    const bars = pts.map(p=>`<div class="mbar"><span class="mctx">${ctxK(p.context)}</span>`
      + `<span class="mtrack"><span class="mfill" style="width:${(p.decode_tps/gmax*100).toFixed(1)}%"></span></span>`
      + `<span class="mval">${p.decode_tps.toFixed(1)}</span></div>`).join("");
    return `<div class="mrow"${multi}><h3><span class="marm">${r.arm}</span> · ${shortModel(r.model)}</h3>${bars}</div>`;
  }).join("") || '<p class="empty">No canonical data.</p>';
}

/* ---------- table ---------- */
const COV = {}; (DATA.coverage||[]).forEach(c => COV[c.arm] = {cache:c.cache, mtp:c.mtp});
// Quant + model without duplication: show the more informative string when one
// contains the other (e.g. quant "AWQ 5bpw" == model "AWQ 5bpw"), else both.
function quantModel(a){
  const m = shortModel(a.model), q = a.quant;
  if(!q) return m;
  const ml = m.toLowerCase(), ql = q.toLowerCase();
  if(ml===ql || ql.includes(ml)) return `<span class="cov-p">${q}</span>`;
  if(ml.includes(ql)) return `<span class="cov-p">${m}</span>`;
  return `<span class="cov-p">${q}</span> <span class="muted">${m}</span>`;
}
const covFlag = (v)=> v==null ? '<span class="cov-d">—</span>'
  : (v==="✓"||String(v).startsWith("✓") ? `<span class="cov-y">${v}</span>`
  : (v==="✗" ? '<span class="cov-n">✗</span>'
  : (v==="—" ? '<span class="cov-d">—</span>' : `<span class="cov-p">${v}</span>`)));
const COLS = [
  {key:"arm", label:"Arm", cls:""},
  {key:"runtime", label:"Runtime", cls:""},
  {key:"model", label:"Quant / model", cls:""},
  {key:"cache", label:"Cache", cls:"cov-c"},
  {key:"mtp", label:"MTP", cls:"cov-c"},
  {key:"context", label:"Ctx", cls:"num"},
  {key:"content_class", label:"Class", cls:""},
  {key:"decode_tps", label:"decode", cls:"num"},
  {key:"ttft_identical_ms", label:"TTFT q.", cls:"num"},
  {key:"e2e_identical_ms", label:"E2E q.", cls:"num"},
  {key:"cache_hit_identical", label:"cache hit", cls:"num"},
  {key:"correct", label:"correctness", cls:"num"},
  {key:"tool", label:"tool loop", cls:"num"},
  {key:"mode", label:"Mode", cls:""},
];
const SORTABLE = new Set(["arm","runtime","context","decode_tps","ttft_identical_ms","e2e_identical_ms","cache_hit_identical","correct","mode"]);
function renderHead(){
  const tr = COLS.map(c=>{
    const s = SORTABLE.has(c.key);
    const active = state.sortKey===c.key;
    const ind = s ? `<span class="ind">${active?(state.sortDir<0?'▼':'▲'):'↕'}</span>` : "";
    return `<th class="${c.cls}${s?' sortable':''}"${s?` data-key="${c.key}"`:''}${active?' data-active="1"':''}>${c.label}${ind}</th>`;
  }).join("");
  document.getElementById("thead").innerHTML = `<tr>${tr}</tr>`;
  document.querySelectorAll("th.sortable").forEach(th=>th.onclick=()=>{
    const k=th.dataset.key; if(state.sortKey===k) state.sortDir*=-1;
    else { state.sortKey=k; state.sortDir = (k==="ttft_identical_ms"||k==="e2e_identical_ms")?1:-1; }
    renderHead(); renderTable();
  });
}
function cell(a){
  const ok = a.total? a.correct/a.total:0;
  const okCls = ok>=0.9?"ok":(ok>=0.6?"run":"bad");
  const tl = TL[a.arm]; const tlTxt = tl?`${tl.passed}/${tl.total}`:"—";
  const num = (v,f)=> v==null?"—":f(v);
  const cov = COV[a.arm] || {};
  return `<td class="mono arm">${a.arm}${badge(a.arm)}</td>`
    + `<td>${a.runtime}</td>`
    + `<td>${quantModel(a)}</td>`
    + `<td class="cov-c">${covFlag(cov.cache)}</td>`
    + `<td class="cov-c">${covFlag(cov.mtp)}</td>`
    + `<td class="num mono">${ctxK(a.context)}</td>`
    + `<td class="muted">${(a.content_class||"").slice(0,5)}</td>`
    + `<td class="num mono strong">${num(a.decode_tps,v=>v.toFixed(1))}</td>`
    + `<td class="num mono">${num(a.ttft_identical_ms,v=>(v/1000).toFixed(1)+'s')}</td>`
    + `<td class="num mono">${num(a.e2e_identical_ms,v=>(v/1000).toFixed(1)+'s')}</td>`
    + `<td class="num mono">${num(a.cache_hit_identical,v=>Math.round(v*100)+'%')}</td>`
    + `<td class="num"><span class="chip ${okCls}">${a.correct}/${a.total}</span></td>`
    + `<td class="num mono">${tlTxt}</td>`
    + `<td><span class="chip ${a.mode==='canonical'?'neutral':'wait'}">${a.mode}</span></td>`;
}
function sortRows(rows){
  const k=state.sortKey, d=state.sortDir;
  return rows.slice().sort((x,y)=>{
    let xv=x[k], yv=y[k];
    if(k==="correct"){ xv=x.correct/(x.total||1); yv=y.correct/(y.total||1); }
    if(xv==null) return 1; if(yv==null) return -1;
    if(typeof xv==="string") return d*xv.localeCompare(yv);
    return d*(xv-yv);
  });
}
function renderTable(){
  let rows = filtered();
  const q = state.search.trim();
  document.getElementById("table-count").textContent =
    `${rows.length} of ${ARMS.length} groups` + (q?` · search "${q}"`:"");
  // canonical-before-greedy stays the primary key unless the user sorts explicitly
  rows = sortRows(rows);
  const tb = document.getElementById("tbody");
  if(!rows.length){ tb.innerHTML = `<tr><td colspan="${COLS.length}" class="empty">Nothing matches the filter.</td></tr>`; return; }
  let html="", lastGroup=null;
  if(state.group==="runtime") rows.sort((x,y)=> x.runtime.localeCompare(y.runtime) || (y.decode_tps||0)-(x.decode_tps||0));
  rows.forEach(a=>{
    if(state.group==="runtime" && a.runtime!==lastGroup){ lastGroup=a.runtime;
      html += `<tr class="grouphdr"><td colspan="${COLS.length}">${a.runtime}</td></tr>`; }
    const hl = q && matchSearch(a) ? " hl" : "";
    html += `<tr class="${a.mode==='greedy'?'greedy':''}${hl}">${cell(a)}</tr>`;
  });
  tb.innerHTML = html;
}

/* ---------- tooltip ---------- */
const tip = document.getElementById("tip");
function showTip(e, arm, ctx, cls){
  const a = findArm(arm,ctx,cls); if(!a) return;
  tip.innerHTML = `<div class="tt">${a.arm} · ${shortModel(a.model)}</div>`
    + `<div class="tl">${a.runtime} · ${a.config}</div>`
    + `<dl><dt>context</dt><dd>${ctxK(a.context)} ${a.content_class||''}</dd>`
    + `<dt>decode</dt><dd>${a.decode_tps!=null?a.decode_tps.toFixed(1)+' tok/s':'—'}</dd>`
    + `<dt>TTFT q.</dt><dd>${a.ttft_identical_ms!=null?(a.ttft_identical_ms/1000).toFixed(1)+'s':'—'}</dd>`
    + `<dt>cold TTFT</dt><dd>${a.ttft_cold_ms!=null?(a.ttft_cold_ms/1000).toFixed(1)+'s':'—'}</dd>`
    + `<dt>E2E q.</dt><dd>${a.e2e_identical_ms!=null?(a.e2e_identical_ms/1000).toFixed(1)+'s':'—'}</dd>`
    + `<dt>cache</dt><dd>${a.cache_hit_identical!=null?Math.round(a.cache_hit_identical*100)+'%':'—'}</dd>`
    + `<dt>correctness</dt><dd>${a.correct}/${a.total}</dd><dt>mode</dt><dd>${a.mode}</dd></dl>`;
  tip.classList.add("on");
  const pad=14; let x=e.clientX+pad, y=e.clientY+pad;
  if(x+tip.offsetWidth>innerWidth) x=e.clientX-tip.offsetWidth-pad;
  if(y+tip.offsetHeight>innerHeight) y=e.clientY-tip.offsetHeight-pad;
  tip.style.left=x+"px"; tip.style.top=y+"px";
}
function hideTip(){ tip.classList.remove("on"); }

/* ---------- controls ---------- */
function initControls(){
  seg(document.getElementById("metric-seg"),
    Object.entries(METRICS).map(([k,m])=>({val:k,label:m.btn})),
    state.metric, v=>{ state.metric=v; renderChart(); });
  const opt = (vals,labels)=> [{val:"all",label:"all"}].concat(vals.map((v,i)=>({val:String(v),label:labels?labels[i]:String(v)})));
  seg(document.getElementById("f-mode"), [{val:"all",label:"all"},{val:"canonical",label:"canonical"},{val:"greedy",label:"greedy"}],
    state.mode, v=>{state.mode=v; refresh();});
  seg(document.getElementById("f-runtime"), opt(uniq(ARMS.map(a=>a.runtime))),
    state.runtime, v=>{state.runtime=v; refresh();});
  seg(document.getElementById("f-ctx"), opt(uniq(ARMS.map(a=>a.context)).sort((x,y)=>x-y), uniq(ARMS.map(a=>a.context)).sort((x,y)=>x-y).map(ctxK)),
    state.ctx, v=>{state.ctx=v; refresh();});
  seg(document.getElementById("f-class"), opt(uniq(ARMS.map(a=>a.content_class||"?"))),
    state.cls, v=>{state.cls=v; refresh();});
  seg(document.getElementById("f-group"), [{val:"none",label:"no"},{val:"runtime",label:"runtime"}],
    state.group, v=>{state.group=v; renderTable();});
}
/* ---------- runtime & quant comparisons ---------- */
function bestDecode(arms){
  const canon = arms.filter(a => a.mode==="canonical" && a.decode_tps!=null);
  const pool = canon.length ? canon : arms.filter(a => a.decode_tps!=null);
  if(!pool.length) return null;
  const best = pool.reduce((m,a) => a.decode_tps>m.decode_tps ? a : m);
  return {val:best.decode_tps, arm:best.arm, greedy:!canon.length};
}
function cmpBar(cls, lab, sub, val, max, greedy){
  return `<div class="cmprow${greedy?' greedy':''}"><div class="clab"><b>${cls}</b>`
    + `<small>${sub}</small></div>`
    + `<div class="ctrack"><div class="cfill" style="width:${(val/max*100).toFixed(1)}%"></div></div>`
    + `<div class="cval">${val.toFixed(1)}${greedy?' <small>greedy</small>':''}</div></div>`;
}
function renderRuntimes(){
  const by = {}; ARMS.forEach(a => (by[a.runtime] ||= []).push(a));
  const rows = Object.entries(by).map(([rt,arms]) => {
    const b = bestDecode(arms);
    const nc = new Set(arms.filter(a=>a.mode==="canonical").map(a=>a.arm)).size;
    const ng = new Set(arms.filter(a=>a.mode==="greedy").map(a=>a.arm)).size;
    return b ? {rt, ...b, nc, ng} : null;
  }).filter(Boolean).sort((x,y)=>y.val-x.val);
  const max = Math.max(...rows.map(r=>r.val));
  document.getElementById("runtimes").innerHTML = rows.map(r =>
    cmpBar(r.rt, r.rt, `${r.nc} canonical · ${r.ng} greedy · best ${r.arm}`, r.val, max, r.greedy)).join("");
}
function renderQuants(){
  const by = {}; ARMS.forEach(a => { if(a.quant) (by[a.quant] ||= []).push(a); });
  const rows = Object.entries(by).map(([q,arms]) => {
    const b = bestDecode(arms);
    return b ? {q, bpw:arms[0].bpw, ...b} : null;
  }).filter(Boolean).sort((x,y)=> x.bpw-y.bpw);
  const max = Math.max(...rows.map(r=>r.val));
  document.getElementById("quants").innerHTML = rows.map(r =>
    cmpBar(r.q, r.q, `${r.bpw} bpw · best ${r.arm}`, r.val, max, r.greedy)).join("");
}
function renderGlossaries(){
  const g = DATA.arm_glossary || {};
  document.getElementById("arm-gloss").innerHTML = Object.entries(g).map(([arm,m]) =>
    `<div class="gitem"><span class="gk">${arm}</span><span>${m.desc||""}</span></div>`).join("");
  document.getElementById("gate-gloss").innerHTML = (DATA.gates_glossary||[]).map(x =>
    `<div class="gaterow"><b>Gate ${x.gate}</b> — <span>${x.desc}</span></div>`).join("");
}
/* ---------- qualitative profiles ---------- */
function profCard(p){
  const tagRow = p.bpw
    ? `<span class="ptag">${p.bpw} bpw · ${p.runtime}</span>`
    : `<span class="ptag">${p.tag}</span>`;
  const arm = p.arms ? `<div class="parm mono">arms ${p.arms}</div>` : "";
  const how = p.how ? `<div><dt>How</dt><dd>${p.how}</dd></div>` : "";
  return `<div class="prof"><div class="ptop"><span class="pname">${p.name}</span>${tagRow}</div>`
    + arm + `<p class="pgoal">${p.goal}</p>`
    + `<dl class="pmeta">${how}<div><dt>Cost</dt><dd>${p.cost}</dd></div></dl></div>`;
}
function renderProfiles(){
  document.getElementById("runtime-profiles").innerHTML =
    (DATA.runtime_profiles||[]).map(profCard).join("");
  document.getElementById("quant-profiles").innerHTML =
    (DATA.quant_profiles||[]).map(profCard).join("");
}
/* ---------- tests tab ---------- */
function renderTests(){
  const c = DATA.test_catalog || {};
  const gloss = (items, title, keyw)=> items && items.length
    ? `<div class="tblock"><div class="subhead">${title}</div><div class="gloss">`
      + items.map(x=>`<div class="gitem"><span class="gk ${keyw?'kw':''}">${x.key}</span><span>${x.eval}</span></div>`).join("")
      + `</div></div>` : "";
  let html = "";
  html += gloss(c.scenarios, "cache-probe scenarios", true);
  html += gloss(c.modes, "Sampling modes", true);
  html += gloss(c.correctness, "Correctness check (by content class)", true);
  if(c.tool_loop) html += `<div class="tblock"><div class="subhead">Tool loop</div>`
    + `<p class="tp">${c.tool_loop.eval}</p></div>`;
  if(c.metrics) html += `<div class="tblock"><div class="subhead">Metrics captured per record</div>`
    + `<div class="mchips">${c.metrics.map(m=>`<span class="mchip">${m}</span>`).join("")}</div></div>`;
  document.getElementById("test-catalog").innerHTML = html;
}
function renderTestCoverage(){
  const rows = DATA.test_coverage || [];
  const scen = ["cold","identical","append","middle_mutation","tool_turn"];
  const short = {cold:"cold",identical:"ident.",append:"append",middle_mutation:"mid.mut",tool_turn:"tool_turn"};
  document.getElementById("tcov-head").innerHTML = "<tr>"
    + `<th>Arm</th><th>Runtime</th><th>Model</th>`
    + scen.map(s=>`<th class="cov-c">${short[s]}</th>`).join("")
    + `<th class="cov-c">tool loop</th></tr>`;
  const cellFor = (v)=> v==="canonical" ? '<span class="cov-y">■</span>'
    : (v==="greedy" ? '<span class="cov-p">■</span>' : '<span class="cov-d">—</span>');
  document.getElementById("tcov-body").innerHTML = rows.map(r=>{
    const dim = r.measured ? "" : ' class="cov-un"';
    return `<tr${dim}><td class="mono arm">${r.arm}</td>`
      + `<td>${r.runtime}</td><td>${shortModel(r.model)}</td>`
      + scen.map(s=>`<td class="cov-c">${cellFor(r.scenarios[s])}</td>`).join("")
      + `<td class="cov-c mono">${r.tool||'<span class="cov-d">—</span>'}</td></tr>`;
  }).join("");
}
/* ---------- coverage matrix ---------- */
function renderCoverage(){
  const cov = DATA.coverage || [];
  const cols = ["Arm","Runtime","Quant / model","Cache","MTP","Canonical ctx","Greedy ctx","Tool","Note"];
  document.getElementById("cov-head").innerHTML =
    "<tr>" + cols.map(c=>`<th>${c}</th>`).join("") + "</tr>";
  const flag = (v)=> v==="✓"||v.startsWith("✓") ? `<span class="cov-y">${v}</span>`
    : (v==="✗" ? `<span class="cov-n">✗</span>` : (v==="—" ? `<span class="cov-d">—</span>` : `<span class="cov-p">${v}</span>`));
  const ctxCell = (arr,strong)=> arr.length
    ? `<span class="mono${strong?' cov-strong':''}">${arr.join(", ")}</span>`
    : `<span class="cov-d">—</span>`;
  document.getElementById("cov-body").innerHTML = cov.map(r=>{
    const dim = r.measured ? "" : ' class="cov-un"';
    return `<tr${dim}><td class="mono arm">${r.arm}</td>`
      + `<td>${r.runtime}</td>`
      + `<td>${shortModel(r.model)}${r.quant?` · <span class="cov-d">${r.quant}</span>`:""}</td>`
      + `<td class="cov-c">${flag(r.cache)}</td>`
      + `<td class="cov-c">${flag(r.mtp)}</td>`
      + `<td>${ctxCell(r.canon_ctx,true)}</td>`
      + `<td>${ctxCell(r.greedy_ctx,false)}</td>`
      + `<td class="mono">${r.tool||'<span class="cov-d">—</span>'}</td>`
      + `<td class="cov-note">${r.note||""}</td></tr>`;
  }).join("");
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
renderRuntimes(); renderQuants(); renderProfiles(); renderCoverage();
renderTests(); renderTestCoverage(); renderGlossaries(); renderTable();
</script>
"""


def main() -> int:
    data = json.loads(OVERVIEW.read_text(encoding="utf-8"))
    OUT.write_text(render(data), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
