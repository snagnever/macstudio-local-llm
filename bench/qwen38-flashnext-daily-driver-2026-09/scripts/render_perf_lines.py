#!/usr/bin/env python3
"""Render results/reports.json into reports/qwen38-flashnext-perf-lines.html.

Same layout as the dense campaign's reports/perf-lines.html: rig strip, setup
by candidate, runtime cards, takeaways, SVG line panels by context, a cache hit
heatmap and a table with every value. The points are the canonical groups of
each band (Stage B when it exists, otherwise Stage A or the probe).

    python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/consolidate_reports.py
    python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_perf_lines.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[1]
REPORTS_JSON = CAMPAIGN / "results" / "reports.json"
OUT = CAMPAIGN.parents[1] / "reports" / "qwen38-flashnext-perf-lines.html"

LINE_CTX = [32768, 131072, 262144, 524288]
TABLE_CTX = [8192, 32768, 131072, 262144, 524288]
SERIES_COLOR = {"c1": "--s1", "c2": "--s2", "c3": "--s3", "c4": "--s5"}

# Bands with no measured group: the reason shows in the tooltip and the table.
ABSENT = {
    ("c2", 524288): "no YaRN: 262K ceiling",
    ("c3", 524288): "no YaRN: 262K ceiling",
    ("c4", 524288): "not run: refused already at 128K",
}

TECH = [
    {"name": "mlx-serve", "repo": "ddalcu/mlx-serve",
     "what": "MLX server with <b>native MTP for Flash-Next</b> and a two-tier prefix cache. It is the runtime for the ddalcu pack.",
     "cache": "Hot cache in RAM (<b>16 GB, 64 entries</b>) and a disk cache (100 GB). <code>--ssm-checkpoint-max 16</code> keeps checkpoints of the DeltaNet state; the warm turn reuses the prefix without a re-prefill.",
     "spec": "MTP <b>depth 6 with PLD</b> (prompt lookup through the pack's n-gram table). Acceptance 0.50–0.67, read from the <code>[spec-stats]</code> log: <code>/metrics</code> exposes no counter.",
     "configs": "c1 ddalcu mixed-4/8"},
    {"name": "oMLX", "repo": "jundot/omlx",
     "what": "MLX server for agents: continuous batching and a <b>two-tier paged KV cache</b>. Speculation comes from the checkpoint.",
     "cache": "Blocks in RAM that <b>spill over to an SSD tier</b>. The oQ4e PLE stays in mmap (<code>qwen4_ple_ssd_offload</code> in <code>model_settings.json</code>); without it the pack saturates the 128 GB.",
     "spec": "MTP from the oQ4e-mtp checkpoint (<code>mtp_enabled</code>). oMLX telemetry does not expose acceptance. oMLX has no YaRN, so the ceiling is 262K.",
     "configs": "c2 oMLX 0.6.4 · c3 oMLX 0.7.0.dev2"},
    {"name": "MTPLX", "repo": "youssofal/MTPLX",
     "what": "Speculation <b>ships in the quantized checkpoint</b>: the model's own MTP heads draft tokens, with no external model.",
     "cache": "Session bank in RAM and <b>SSD session cache on</b> (vendor default). A memory plan computes the context that fits and refuses any prompt above it with HTTP 507.",
     "spec": "<b>Turbo profile, depth 3</b>, verified by rejection sampling (lossless). Acceptance 0.24–0.46; at 32K it gives 1.8× decode over MTP off.",
     "configs": "c4 MTPLX Optimized-Speed"},
]
TECH_SRC = [
    ["ddalcu/mlx-serve", "https://github.com/ddalcu/mlx-serve"],
    ["jundot/omlx", "https://github.com/jundot/omlx"],
    ["youssofal/MTPLX", "https://github.com/youssofal/MTPLX"],
]


def point(g: dict) -> dict:
    return {
        "t_turno": g["t_turno_s"], "ttft_tool": g["ttft_s"]["tool_turn"],
        "ttft_append": g["ttft_s"]["append"], "cold": g["cold_ttft_s"],
        "decode": g["decode_tps"], "decode_range": g["decode_range"],
        "prefill": g["prefill_tps"], "wired": g["wired_peak_gb"],
        "free": g["mem_free_min_gb"], "hit_tool": g["hit"]["tool_turn"],
        "mtp": g["mtp_acceptance"], "reps": g["reps"], "stage": g["stage"],
        "note": g["note"],
        "status": ("refused " + ", ".join(k.replace("http_", "HTTP ") for k in g["error_kinds"])
                   if g["refused"] else ""),
    }


def build_payload(data: dict) -> dict:
    canon = {(g["cand"], g["context"]): g for g in data["groups"] if g["canonical"]}
    points: dict = {}
    hitmap: dict = {}
    for c in data["candidates"]:
        cid = c["id"]
        points[cid], hitmap[cid] = {}, {}
        for ctx in TABLE_CTX:
            g = canon.get((cid, ctx))
            if g is None:
                if (cid, ctx) in ABSENT:
                    points[cid][str(ctx)] = {"status": ABSENT[(cid, ctx)]}
                continue
            points[cid][str(ctx)] = point(g)
            hitmap[cid][str(ctx)] = {
                s: (g["hit"][s] if s in g["scenarios_served"] else "x")
                for s in g["scenarios_run"]
            }
    series = [{"id": c["id"], "name": c["name"], "short": c["short"], "cv": SERIES_COLOR[c["id"]]}
              for c in data["candidates"]]
    cfg = {c["id"]: {"runtime": f'{c["runtime"]} {c["runtime_version"]}',
                     "model": f'{c["model"]} ({c["revision"]})',
                     "quant": f'{c["quant"]} · {c["bpw"]} bpw · {c["disk_gb"]:.0f} GB',
                     "cache": c["cache"], "spec": c["spec"], "ceiling": c["ceiling"],
                     "status": c["status"], "state": c["state"]}
           for c in data["candidates"]}
    return {"points": points, "hitmap": hitmap, "series": series, "cfg": cfg,
            "rig": data["rig"], "takeaways": data["takeaways"], "tech": TECH,
            "tech_src": TECH_SRC, "line_ctx": LINE_CTX, "table_ctx": TABLE_CTX,
            "generated_at": data["generated_at"]}


def render(data: dict) -> str:
    payload = json.dumps(build_payload(data), ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("/*__CSS__*/", CSS).replace("__PAYLOAD__", payload)


CSS = r"""
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
body{
  background:var(--plane); color:var(--ink); font-family:var(--sans);
  line-height:1.5; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1180px; margin:0 auto; padding:32px 20px 64px}
header{display:flex; flex-wrap:wrap; gap:20px 32px; align-items:flex-end; justify-content:space-between}
h1{font-size:1.7rem; font-weight:700; letter-spacing:-0.02em; margin:0; text-wrap:balance}
.sub{color:var(--ink-2); max-width:66ch; margin:8px 0 0; font-size:0.98rem}
.eyebrow{font-family:var(--mono); font-size:0.72rem; letter-spacing:0.14em; text-transform:uppercase; color:var(--muted); margin:0 0 6px}
button.theme{
  font-family:var(--mono); font-size:0.74rem; color:var(--ink-2); background:var(--surface);
  border:1px solid var(--border); border-radius:7px; padding:7px 12px; cursor:pointer;
}
button.theme:hover{border-color:var(--baseline)}
button.theme:focus-visible{outline:2px solid var(--accent); outline-offset:2px}

h2.sec{font-size:1.05rem; margin:0 0 4px; letter-spacing:-0.01em}
.s-note{color:var(--ink-2); font-size:0.88rem; margin:0 0 14px; max-width:82ch}
.s-note code{font-family:var(--mono); font-size:0.9em; background:var(--surface-2); padding:1px 5px; border-radius:4px}
section.block{margin-top:30px}

/* rig strip */
.rig{display:grid; grid-template-columns:repeat(auto-fit,minmax(148px,1fr)); gap:10px; margin-top:18px}
.rig .r-item{background:var(--surface); border:1px solid var(--border); border-radius:9px; padding:10px 13px}
.rig .r-lab{font-size:0.72rem; color:var(--muted); margin:0 0 3px}
.rig .r-val{font-family:var(--mono); font-size:0.88rem; color:var(--ink); font-weight:500}

/* tables shared */
.tbl-scroll{overflow-x:auto; border:1px solid var(--border); border-radius:10px; background:var(--surface)}
table{border-collapse:collapse; width:100%; font-size:0.84rem}
th,td{padding:8px 11px; text-align:right; font-variant-numeric:tabular-nums; font-family:var(--mono)}
th{font-size:0.72rem; letter-spacing:0.04em; color:var(--muted); font-weight:500; border-bottom:1px solid var(--border); position:sticky; top:0; background:var(--surface)}
td:first-child,th:first-child{text-align:left}
tbody tr:hover{background:var(--surface-2)}
.arm-cell{display:inline-flex; align-items:center; gap:8px}
.arm-cell .sw{width:10px; height:10px; border-radius:2px; flex:none}
.arm-cell .code{font-weight:700; color:var(--ink)}
.na{color:var(--muted)}

#cfgTable{min-width:780px}
#cfgTable th,#cfgTable td{text-align:left; vertical-align:top; white-space:normal; font-family:var(--sans); font-size:0.83rem; line-height:1.42}
#cfgTable th{font-family:var(--mono); font-size:0.72rem; letter-spacing:0.04em}
#cfgTable td:first-child{font-weight:700; color:var(--ink); white-space:nowrap}
#cfgTable .mono{font-family:var(--mono); font-size:0.9em; color:var(--ink-2)}

/* tech cards */
.tech{display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:14px; margin-top:16px}
.tcard{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:16px 16px 14px}
.tcard .t-name{font-size:1.02rem; font-weight:700; letter-spacing:-0.01em; display:flex; align-items:baseline; gap:8px; flex-wrap:wrap}
.tcard .t-repo{font-family:var(--mono); font-size:0.72rem; color:var(--muted)}
.tcard .t-what{font-size:0.86rem; color:var(--ink-2); margin:7px 0 13px; line-height:1.45}
.tcard dl{margin:0; display:grid; gap:11px}
.tcard dt{font-family:var(--mono); font-size:0.66rem; letter-spacing:0.09em; text-transform:uppercase; color:var(--accent); margin-bottom:3px}
.tcard dd{margin:0; font-size:0.83rem; color:var(--ink-2); line-height:1.45}
.tcard dd b{color:var(--ink); font-weight:600}
.tcard .t-configs{margin:13px 0 0; padding-top:11px; border-top:1px solid var(--border); font-size:0.8rem; color:var(--ink-2)}
.tcard .t-configs b{color:var(--ink); font-family:var(--mono); font-weight:600; font-size:0.9em}
.tech-src{margin-top:12px; font-size:0.78rem; color:var(--muted)}
.tech-src a{color:var(--accent); text-decoration:none}
.tech-src a:hover{text-decoration:underline}

/* legend */
.legend{display:flex; flex-wrap:wrap; gap:8px 18px; margin:22px 0 4px; padding:12px 16px;
  background:var(--surface); border:1px solid var(--border); border-radius:10px}
.chip{display:inline-flex; align-items:center; gap:7px; font-size:0.84rem; color:var(--ink-2)}
.chip .sw{width:22px; height:3px; border-radius:2px; flex:none}
.chip .code{font-family:var(--mono); font-weight:700; color:var(--ink)}

/* takeaways compact */
.takeaways{background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:14px 16px; margin-top:22px}
.takeaways h2{font-size:0.95rem; margin:0 0 9px; letter-spacing:-0.01em}
.takeaways ul{margin:0; padding:0; list-style:none; display:grid; gap:7px}
.takeaways li{font-size:0.85rem; color:var(--ink-2); padding-left:15px; position:relative; line-height:1.4}
.takeaways li::before{content:"›"; position:absolute; left:0; color:var(--accent); font-family:var(--mono); font-weight:700}
.takeaways li b{color:var(--ink)}

/* chart grid */
.grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:14px; margin-top:14px}
.panel{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 14px 10px; position:relative}
.p-head{display:flex; justify-content:space-between; align-items:baseline; gap:10px; margin:0 2px 2px}
.p-title{font-size:0.98rem; font-weight:700; letter-spacing:-0.01em}
.p-unit{font-family:var(--mono); font-size:0.72rem; color:var(--muted)}
.p-dir{font-family:var(--mono); font-size:0.68rem; letter-spacing:0.06em; color:var(--muted)}
.p-note{font-size:0.76rem; color:var(--warn); background:var(--warn-bg); border-radius:6px;
  padding:3px 8px; margin:2px 2px 0; display:inline-block}
.p-interp{font-size:0.8rem; color:var(--ink-2); margin:8px 2px 0; line-height:1.4; border-top:1px solid var(--border); padding-top:8px}
.p-interp b{color:var(--ink); font-weight:600}
svg.chart{width:100%; height:auto; display:block; touch-action:none}
.tick{font-family:var(--mono); font-size:10px; fill:var(--muted)}
.axis-t{font-family:var(--mono); font-size:10.5px; fill:var(--ink-2)}
.endlab{font-family:var(--mono); font-size:9.5px; font-weight:700}
.crosshair{stroke:var(--baseline); stroke-width:1; stroke-dasharray:3 3; opacity:0}

.tip{position:absolute; pointer-events:none; z-index:5; background:var(--surface);
  border:1px solid var(--baseline); border-radius:8px; padding:8px 10px; font-size:0.78rem;
  box-shadow:0 6px 20px rgba(0,0,0,0.13); opacity:0; transition:opacity .08s; min-width:158px}
.tip .t-ctx{font-family:var(--mono); font-weight:700; color:var(--ink); margin-bottom:5px; font-size:0.76rem}
.tip .t-row{display:flex; align-items:center; gap:7px; justify-content:space-between; margin:2px 0}
.tip .t-left{display:flex; align-items:center; gap:6px; color:var(--ink-2)}
.tip .t-left .sw{width:9px; height:9px; border-radius:2px; flex:none}
.tip .t-left .code{font-family:var(--mono); font-weight:700; color:var(--ink); font-size:0.74rem}
.tip .t-val{font-family:var(--mono); color:var(--ink); font-variant-numeric:tabular-nums}
.tip .t-na{color:var(--muted)}

/* hit heatmap */
#hitTable{min-width:640px}
#hitTable th{text-align:center}
#hitTable th:first-child,#hitTable td:first-child{text-align:left}
#hitTable td.grp{background:var(--surface-2); font-family:var(--sans); font-weight:700; color:var(--ink); font-size:0.8rem}
.hcell{text-align:center; font-variant-numeric:tabular-nums; border-radius:4px}
.hcell.na{color:var(--muted); background:transparent!important}
.hcell.est{box-shadow:inset 0 0 0 1.6px var(--muted); font-style:italic}
.hcell .star{font-style:normal; font-weight:700; margin-left:1px}
.est-note{margin:10px 0 0; font-size:0.78rem; color:var(--ink-2)}
.est-note .star{font-weight:700; font-style:normal}
.hit-legend{display:flex; align-items:center; gap:10px; margin-top:12px; font-size:0.8rem; color:var(--ink-2); flex-wrap:wrap}
.hit-legend .bar{height:12px; width:150px; border-radius:3px; border:1px solid var(--border);
  background:linear-gradient(90deg, var(--surface-2), rgba(var(--accent-rgb),0.88))}

/* values table */
#table{min-width:720px}
#table td,#table th{font-family:var(--mono)}
.grp-row td{background:var(--surface-2); color:var(--ink); font-family:var(--sans); font-weight:700; font-size:0.8rem; letter-spacing:0.02em; text-align:left; padding:6px 11px}
.tbl-note{color:var(--ink-2); font-size:0.88rem; margin:0 0 14px; max-width:80ch}
.tbl-note code{font-family:var(--mono); font-size:0.9em; background:var(--surface-2); padding:1px 5px; border-radius:4px}

footer{margin-top:34px; color:var(--ink-2); font-size:0.82rem; max-width:82ch}
footer b{color:var(--ink)}
footer code{font-family:var(--mono); font-size:0.9em; background:var(--surface-2); padding:1px 5px; border-radius:4px}
@media (prefers-reduced-motion: reduce){*{transition:none!important}}
"""

EXTRA_CSS = r"""
#cfgTable td.st{white-space:nowrap}
.stchip{display:inline-block; font-family:var(--mono); font-size:0.7rem; padding:1px 7px; border-radius:999px;
  border:1px solid var(--border); color:var(--ink-2); background:var(--surface-2)}
.stchip.pass{color:var(--s3); border-color:var(--s3)}
.stchip.fail{color:var(--s2); border-color:var(--s2)}
.hcell.ref{background:var(--warn-bg)!important; color:var(--warn); font-weight:700}
.reflab{font-family:var(--mono); font-size:9px; fill:var(--warn)}
.hit-legend{display:flex; align-items:center; gap:8px; margin:10px 0 0; font-family:var(--mono); font-size:0.72rem; color:var(--muted)}
.hit-legend .bar{width:140px; height:8px; border-radius:4px;
  background:linear-gradient(90deg, rgba(var(--accent-rgb),0.10), rgba(var(--accent-rgb),0.88))}
td.stat{color:var(--warn); font-family:var(--sans); text-align:left}
"""

TEMPLATE = r"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Qwen3.8-Flash-Next Responsiveness to 512K</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>
/*__CSS__*/
""" + EXTRA_CSS + r"""
</style>

<div class="wrap">
  <header>
    <div>
      <p class="eyebrow">Responsiveness test by context</p>
      <h1>Qwen3.8-Flash-Next: responsiveness from 32K to 512K</h1>
      <p class="sub">Four quant × runtime candidates with the same model, the same fixture and the vendor
      sampling. Each panel is one metric; each line is one candidate. Hover over a chart to read the
      values by context.</p>
    </div>
    <button class="theme" id="themeBtn" type="button">theme: auto</button>
  </header>

  <section class="block">
    <h2 class="sec">Rig</h2>
    <div class="rig" id="rig"></div>
  </section>

  <section class="block">
    <h2 class="sec">Setup by candidate</h2>
    <p class="s-note">What changes between candidates: runtime, quant, prefix cache mechanism and speculation.
    Sampling is the same for all of them (vendor): <code>temperature 1.0</code>, <code>top_p 0.95</code>,
    <code>top_k 20</code>, <code>reasoning xhigh</code>, <code>max_tokens 4096</code>. Fixture
    <code>audit_retrieval</code> with needles at 10/50/90%. Native context: 262,144 tokens; 512K uses YaRN 2.0.
    c2 and c3 run the same weights, so they isolate the runtime.</p>
    <div class="tbl-scroll"><table id="cfgTable"></table></div>
  </section>

  <section class="block">
    <h2 class="sec">Runtimes compared</h2>
    <p class="s-note">All three runtimes do speculative decoding with MTP and prefix caching on Apple
    Silicon. They differ in <b>where the KV cache lives</b> (RAM, disk or paged SSD) and in <b>how they handle
    the memory limit</b>: mlx-serve pins it as wired memory, oMLX spills over to SSD and MTPLX refuses the prompt.</p>
    <div class="tech" id="tech"></div>
    <p class="tech-src" id="techSrc"></p>
  </section>

  <div class="takeaways" id="takeaways"></div>

  <div class="legend" id="legend"></div>

  <div class="grid" id="grid"></div>

  <section class="block">
    <h2 class="sec">Cache hit by scenario</h2>
    <p class="s-note">Fraction of the prefix reused in each scenario, for the band's canonical group. <code>cold</code>
    = first pass (≈0 by design). <code>middle_mutation</code> = the prefix diverges in the middle: oMLX and
    mlx-serve reuse the intact part (0.30–0.49); MTPLX re-prefills (0.07). <code>append</code> and
    <code>tool_turn</code> are the gate: ≥ 0.90 at 32K and 128K.</p>
    <div class="tbl-scroll"><table id="hitTable"></table></div>
    <div class="hit-legend"><span>0</span><span class="bar"></span><span>1 (full reuse)</span></div>
    <p class="est-note"><span class="star">*</span> c4 at 8K: incoherent cache telemetry (hit 1.00 even on
    <code>cold</code>; <code>tool_turn</code> TTFT of 75 s). <b>507</b> = scenario refused with HTTP 507.
    <b>—</b> = scenario outside the band's protocol: Stage 0 (8K) runs cold, identical and tool_turn; 256K skips
    append and middle_mutation; the 512K probe runs cold and identical.</p>
  </section>

  <section class="block">
    <h2 class="sec">All values</h2>
    <p class="tbl-note">Single source: <code>results/reports.json</code>, generated from <code>results/*.jsonl</code>.
    Values from each band's canonical group. <code>T_turn</code> = tool_turn TTFT + 512 / warm decode.
    Warm decode = median of served identical, append and tool_turn (range across records).</p>
    <div class="tbl-scroll"><table id="table"></table></div>
  </section>

  <footer id="foot"></footer>
</div>

<div class="tip" id="tip"></div>

<script>
const P = __PAYLOAD__;
const DATA = P.points, HITMAP = P.hitmap, SERIES = P.series, CFG = P.cfg;
const CTX = P.line_ctx, TCTX = P.table_ctx;
const ctxLab = c => (c/1024)+"K";
const STAGE = {"0":"Stage 0 · 1 rep","A":"Stage A · 1 rep","B":"Stage B · 3 reps","C":"Stage C","probe":"512K probe · 1 rep"};
const MISS = {t_turno:"probe has no tool_turn", ttft_tool:"probe has no tool_turn"};
const PANELS = [
  {key:"t_turno", title:"T_turn", unit:"s", dir:"↓ better", fmt:v=>v.toFixed(1),
   tipFmt:v=>v.toFixed(2),
   note:"c1 and c3 at 32K and 128K = median of 3 reps (Stage B). The other points have 1 rep.",
   interp:"<b>c1 stays nearly flat</b> (11.0 → 12.35 → 14.2 s). c2 goes from 17 to 29 s. c4 has only the 32K point."},
  {key:"ttft_tool", title:"Warm TTFT · tool_turn", unit:"s", dir:"↓ better", fmt:v=>v.toFixed(1),
   tipFmt:v=>v.toFixed(2),
   interp:"This term separates c1 and c3: <b>2.1 vs 4.8 s at 128K</b>. TTFT was the same in all 3 reps."},
  {key:"cold", title:"Cold TTFT · first turn", unit:"s", dir:"↓ better", fmt:v=>v.toFixed(0),
   interp:"At 256K dev2 takes <b>578 s vs 1187 s</b> for 0.6.4; c1 takes 379 s. At 512K c1 takes 845 s."},
  {key:"decode", title:"Warm decode", unit:"tok/s", dir:"↑ better", fmt:v=>v.toFixed(1),
   note:"512K: identical decode (the probe runs neither append nor tool_turn).",
   interp:"c4 leads at 32K (~70 tok/s). At 128K <b>c1 and c3 tie at ~50</b>; at 256K c2 drops to 24."},
  {key:"prefill", title:"Prefill · cold", unit:"tok/s", dir:"↑ better", fmt:v=>v.toFixed(0),
   interp:"mlx-serve holds <b>~700 tok/s up to 256K</b>. dev2 stays at 440–520; 0.6.4 drops to 216 at 256K."},
  {key:"wired", title:"Wired · peak", unit:"GB", dir:"↓ better", fmt:v=>v.toFixed(0),
   tipFmt:v=>v.toFixed(1), ref:{v:102, lab:"warning 102"},
   interp:"c1 goes above the warning line from 128K up (<b>104–109 GB, swap 0</b>). The oMLX candidates stay at or below 101 GB."},
];

function cssv(name){ return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

function buildRig(){
  const el=document.getElementById("rig"); el.innerHTML="";
  P.rig.forEach(r=>{
    const d=document.createElement("div"); d.className="r-item";
    d.innerHTML=`<p class="r-lab">${r.lab}</p><p class="r-val">${r.val}</p>`;
    el.appendChild(d);
  });
}
function buildConfigTable(){
  const t=document.getElementById("cfgTable");
  const cols=["Candidate","Runtime","Model / quant","Prefix cache","Speculation","Context ceiling","Result"];
  let h="<thead><tr>"+cols.map(c=>`<th>${c}</th>`).join("")+"</tr></thead><tbody>";
  SERIES.forEach(s=>{
    const c=CFG[s.id];
    h+="<tr>"+
      `<td><span class="arm-cell"><span class="sw" style="background:var(${s.cv})"></span>${s.short}</span></td>`+
      `<td class="mono">${c.runtime}</td>`+
      `<td><span class="mono">${c.model}</span><br>${c.quant}</td>`+
      `<td>${c.cache}</td><td>${c.spec}</td><td>${c.ceiling}</td>`+
      `<td class="st"><span class="stchip ${c.state}">${c.status}</span></td></tr>`;
  });
  t.innerHTML=h+"</tbody>";
}
function buildTech(){
  const el=document.getElementById("tech"); el.innerHTML="";
  P.tech.forEach(t=>{
    const d=document.createElement("div"); d.className="tcard";
    d.innerHTML=
      `<div class="t-name">${t.name} <span class="t-repo">${t.repo}</span></div>`+
      `<p class="t-what">${t.what}</p>`+
      `<dl><div><dt>Prefix cache</dt><dd>${t.cache}</dd></div>`+
      `<div><dt>Speculation</dt><dd>${t.spec}</dd></div></dl>`+
      `<p class="t-configs">Candidates here: <b>${t.configs}</b></p>`;
    el.appendChild(d);
  });
  document.getElementById("techSrc").innerHTML =
    "Sources: "+P.tech_src.map(s=>`<a href="${s[1]}" target="_blank" rel="noopener">${s[0]}</a>`).join(" · ");
}
function buildTakeaways(){
  document.getElementById("takeaways").innerHTML=`<h2>Takeaways</h2><ul>`+
    P.takeaways.map(t=>`<li><b>${t[0]}</b> — ${t[1]}</li>`).join("")+`</ul>`;
}
function buildLegend(){
  const el=document.getElementById("legend"); el.innerHTML="";
  SERIES.forEach(s=>{
    const c=document.createElement("span"); c.className="chip";
    c.innerHTML=`<span class="sw" style="background:var(${s.cv})"></span><span class="code">${s.name}</span>`;
    el.appendChild(c);
  });
}

const W=360, H=232, ML=44, MR=78, MT=16, MB=30;
const x0=ML, x1=W-MR, y0=H-MB, y1=MT;
function xAt(i){ return x0 + (x1-x0)*(i/(CTX.length-1)); }
function niceMax(v){
  if(v<=0) return 1;
  const pow=Math.pow(10, Math.floor(Math.log10(v)));
  const n=v/pow;
  const step = n<=1?1 : n<=2?2 : n<=5?5 : 10;
  return step*pow;
}
function val(sid, ctx, key){ const d=(DATA[sid]||{})[ctx]; return d ? d[key] : undefined; }
function buildPanel(p){
  const panel=document.createElement("div"); panel.className="panel";
  panel.innerHTML =
    `<div class="p-head"><span class="p-title">${p.title}</span>`+
    `<span class="p-unit">${p.unit} · <span class="p-dir">${p.dir}</span></span></div>`+
    (p.note?`<span class="p-note">${p.note}</span>`:"");
  let vmax=p.ref?p.ref.v:0;
  SERIES.forEach(s=>CTX.forEach(c=>{ const v=val(s.id,c,p.key); if(v!=null&&v>vmax)vmax=v; }));
  const top=niceMax(vmax*1.08);
  const yAt=v=> y0 - (y0-y1)*(v/top);
  const NS="http://www.w3.org/2000/svg";
  const svg=document.createElementNS(NS,"svg");
  svg.setAttribute("viewBox",`0 0 ${W} ${H}`); svg.setAttribute("class","chart");
  svg.setAttribute("role","img"); svg.setAttribute("aria-label",`${p.title} (${p.unit}) by context`);
  let g="";
  const TICKS=4;
  for(let t=0;t<=TICKS;t++){
    const v=top*t/TICKS, yy=yAt(v);
    g+=`<line x1="${x0}" y1="${yy}" x2="${x1}" y2="${yy}" stroke="var(--grid)" stroke-width="1"/>`;
    g+=`<text class="tick" x="${x0-6}" y="${yy+3}" text-anchor="end">${p.fmt(v)}</text>`;
  }
  g+=`<line x1="${x0}" y1="${y0}" x2="${x1}" y2="${y0}" stroke="var(--baseline)" stroke-width="1"/>`;
  if(p.ref){
    const ry=yAt(p.ref.v);
    g+=`<line x1="${x0}" y1="${ry}" x2="${x1}" y2="${ry}" stroke="var(--warn)" stroke-width="1" stroke-dasharray="4 3"/>`;
    g+=`<text class="reflab" x="${x0+4}" y="${ry-4}">${p.ref.lab}</text>`;
  }
  CTX.forEach((c,i)=>{ g+=`<text class="axis-t" x="${xAt(i)}" y="${y0+15}" text-anchor="middle">${ctxLab(c)}</text>`; });
  g+=`<line class="crosshair" id="ch-${p.key}" x1="0" y1="${y1}" x2="0" y2="${y0}"/>`;
  const ends=[];
  SERIES.forEach(s=>{
    const col=`var(${s.cv})`;
    const pts=[];
    CTX.forEach((c,i)=>{ const v=val(s.id,c,p.key); if(v!=null) pts.push([i,xAt(i),yAt(v),v]); });
    for(let k=0;k<pts.length-1;k++){
      if(pts[k+1][0]-pts[k][0]===1){
        g+=`<line x1="${pts[k][1]}" y1="${pts[k][2]}" x2="${pts[k+1][1]}" y2="${pts[k+1][2]}" stroke="${col}" stroke-width="2" stroke-linecap="round"/>`;
      }
    }
    pts.forEach(pt=>{ g+=`<circle cx="${pt[1]}" cy="${pt[2]}" r="3.3" fill="${col}" stroke="var(--surface)" stroke-width="1.4"/>`; });
    if(pts.length){ const last=pts[pts.length-1]; ends.push({y:last[2], lab:s.short, col}); }
  });
  ends.sort((a,b)=>a.y-b.y);
  const MINGAP=11;
  for(let k=1;k<ends.length;k++){ if(ends[k].y-ends[k-1].y<MINGAP) ends[k].y=ends[k-1].y+MINGAP; }
  const maxY=y0-2; for(let k=ends.length-1;k>0;k--){ if(ends[k].y>maxY){ends[k].y=maxY; if(ends[k].y-ends[k-1].y<MINGAP)ends[k-1].y=ends[k].y-MINGAP;} }
  ends.forEach(e=>{ g+=`<text class="endlab" x="${x1+5}" y="${e.y+3.5}" fill="${e.col}">${e.lab}</text>`; });
  g+=`<rect x="${x0}" y="${y1}" width="${x1-x0}" height="${y0-y1}" fill="transparent" style="cursor:crosshair"/>`;
  svg.innerHTML=g;
  panel.appendChild(svg);
  const interp=document.createElement("p"); interp.className="p-interp"; interp.innerHTML=p.interp;
  panel.appendChild(interp);
  attachHover(panel, svg, p);
  return panel;
}

const tip=document.getElementById("tip");
function missText(sid, c, key){
  const d=(DATA[sid]||{})[c];
  if(!d) return "no data";
  if(d.status) return d.status;
  return MISS[key] || "no data";
}
function attachHover(panel, svg, p){
  const ch=svg.querySelector(`#ch-${p.key}`);
  const tf=p.tipFmt||p.fmt;
  function move(ev){
    const r=svg.getBoundingClientRect();
    const mx=(ev.clientX-r.left)/r.width*W;
    let idx=Math.round((mx-x0)/((x1-x0)/(CTX.length-1)));
    idx=Math.max(0,Math.min(CTX.length-1,idx));
    const cx=xAt(idx);
    ch.setAttribute("x1",cx); ch.setAttribute("x2",cx); ch.style.opacity=1;
    const c=CTX[idx];
    let rows=`<div class="t-ctx">context ${ctxLab(c)} · ${p.title}</div>`;
    SERIES.forEach(s=>{
      const d=(DATA[s.id]||{})[c]; const v=d?d[p.key]:null;
      const shown = v==null ? `<span class="t-na">${missText(s.id,c,p.key)}</span>`
        : tf(v)+" "+p.unit+(d.reps>1?" · "+d.reps+" reps":"");
      rows+=`<div class="t-row"><span class="t-left"><span class="sw" style="background:var(${s.cv})"></span><span class="code">${s.short}</span></span><span class="t-val">${shown}</span></div>`;
    });
    tip.innerHTML=rows; tip.style.opacity=1;
    let tx=ev.clientX+14, ty=ev.clientY-10;
    const tw=tip.offsetWidth, th=tip.offsetHeight;
    if(tx+tw>window.innerWidth-8) tx=ev.clientX-tw-14;
    if(ty+th>window.innerHeight-8) ty=window.innerHeight-th-8;
    if(ty<8) ty=8;
    tip.style.left=(tx+window.scrollX)+"px"; tip.style.top=(ty+window.scrollY)+"px";
  }
  function leave(){ ch.style.opacity=0; tip.style.opacity=0; }
  svg.addEventListener("mousemove",move);
  svg.addEventListener("mouseleave",leave);
  svg.addEventListener("touchmove",e=>{ if(e.touches[0]){move(e.touches[0]); e.preventDefault();} },{passive:false});
  svg.addEventListener("touchend",leave);
}
function buildGrid(){
  const el=document.getElementById("grid"); el.innerHTML="";
  PANELS.forEach(p=> el.appendChild(buildPanel(p)) );
}

const SCEN=[["cold","cold"],["identical","identical"],["append","append"],["middle_mutation","middle_mut."],["tool_turn","tool_turn"]];
const HIT_FLAG = {"c4":{"8192":true}};
function hitBg(v){ const a=0.10+v*0.78; return `rgba(var(--accent-rgb),${a.toFixed(3)})`; }
function buildHitTable(){
  const t=document.getElementById("hitTable");
  let h="<thead><tr><th>context</th>"+SCEN.map(s=>`<th>${s[1]}</th>`).join("")+"</tr></thead><tbody>";
  SERIES.forEach(s=>{
    h+=`<tr><td class="grp" colspan="${SCEN.length+1}"><span class="arm-cell"><span class="sw" style="background:var(${s.cv})"></span> ${s.name}</span></td></tr>`;
    TCTX.forEach(c=>{
      const row=(HITMAP[s.id]||{})[c];
      if(!row) return;
      const flag=HIT_FLAG[s.id]&&HIT_FLAG[s.id][c];
      h+=`<tr><td>${ctxLab(c)}</td>`+SCEN.map(sc=>{
        const v=row[sc[0]];
        if(v===undefined) return `<td class="hcell na">—</td>`;
        if(v==="x"){ const d=DATA[s.id][c]; const code=d&&d.status?d.status.replace(/\D/g,""):"✗";
          return `<td class="hcell ref" title="${d&&d.status?d.status:'not served'}">${code||"✗"}</td>`; }
        if(v==null) return `<td class="hcell na">—</td>`;
        const txt = v>=0.55 ? "#ffffff" : "var(--ink)";
        if(flag) return `<td class="hcell est" title="incoherent telemetry" style="background:${hitBg(v)};color:${txt}">${v.toFixed(2)}<span class="star">*</span></td>`;
        return `<td class="hcell" style="background:${hitBg(v)};color:${txt}">${v.toFixed(2)}</td>`;
      }).join("")+"</tr>";
    });
  });
  t.innerHTML=h+"</tbody>";
}

function buildTable(){
  const t=document.getElementById("table");
  const cols=[["t_turno","T_turn (s)"],["ttft_tool","TTFT tool (s)"],["ttft_append","TTFT append (s)"],
    ["cold","cold TTFT (s)"],["decode","decode"],["prefill","prefill"],["hit_tool","hit tool"],
    ["wired","wired (GB)"],["free","min free (GB)"],["mtp","MTP acc"],["reps","reps"]];
  let h="<thead><tr><th>candidate</th><th>ctx</th>"+cols.map(c=>`<th>${c[1]}</th>`).join("")+"</tr></thead><tbody>";
  SERIES.forEach(s=>{
    h+=`<tr class="grp-row"><td colspan="${cols.length+2}"><span class="arm-cell"><span class="sw" style="background:var(${s.cv})"></span>${s.name}</span></td></tr>`;
    TCTX.forEach(c=>{
      const d=(DATA[s.id]||{})[c];
      if(!d) return;
      if(d.status && d.t_turno===undefined){
        h+=`<tr><td></td><td>${ctxLab(c)}</td><td class="stat" colspan="${cols.length}">${d.status}</td></tr>`; return;
      }
      if(d.status){
        h+=`<tr><td></td><td>${ctxLab(c)}</td><td class="stat" colspan="${cols.length-1}">${d.note||d.status}</td><td>${d.reps}</td></tr>`; return;
      }
      h+=`<tr title="${d.note||''}"><td></td><td>${ctxLab(c)}${d.note?' ⚑':''}</td>`+cols.map(col=>{
        const v=d[col[0]];
        if(v==null) return `<td class="na">—</td>`;
        if(col[0]==="decode") return `<td title="range ${d.decode_range?d.decode_range.join('–'):''}">${v.toFixed(1)}</td>`;
        if(col[0]==="t_turno"||col[0]==="ttft_tool"||col[0]==="ttft_append"||col[0]==="hit_tool"||col[0]==="free"||col[0]==="mtp") return `<td>${v.toFixed(2)}</td>`;
        if(col[0]==="cold"||col[0]==="wired") return `<td>${v.toFixed(1)}</td>`;
        if(col[0]==="reps") return `<td>${v}</td>`;
        return `<td>${v.toFixed(0)}</td>`;
      }).join("")+"</tr>";
    });
  });
  t.innerHTML=h+"</tbody>";
}

function buildFoot(){
  document.getElementById("foot").innerHTML=
   `<b>How to read.</b> x axis = context (32K, 128K, 256K, 512K; categorical axis). One line per candidate. `+
   `Each point is the band's canonical group: <b>Stage B</b> (3 reps) when it exists, otherwise Stage A (1 rep) or the probe. `+
   `A gap in a line is a refusal or a band outside the runtime's reach; the tooltip says which. `+
   `8K (the Stage 0 smoke test) is left out of the lines: c4 shows a T_turn of 83 s there because of incoherent telemetry; the 8K values are in the table. `+
   `Wired above 102 GB is a warning, not a gate: mlx-serve pins KV and hot cache as wired memory and runs without swap. `+
   `Generated at <code>${P.generated_at}</code> by <code>consolidate_reports.py</code> + <code>render_perf_lines.py</code>.`;
}

buildRig(); buildConfigTable(); buildTech(); buildTakeaways(); buildLegend();
buildGrid(); buildHitTable(); buildTable(); buildFoot();

const btn=document.getElementById("themeBtn");
function applyLabel(){
  const t=document.documentElement.getAttribute("data-theme");
  btn.textContent = "theme: " + (t||"auto");
}
btn.addEventListener("click",()=>{
  const cur=document.documentElement.getAttribute("data-theme");
  const next = cur==null ? "light" : cur==="light" ? "dark" : null;
  if(next) document.documentElement.setAttribute("data-theme",next);
  else document.documentElement.removeAttribute("data-theme");
  try{ next?localStorage.setItem("theme",next):localStorage.removeItem("theme"); }catch(e){}
  applyLabel(); buildGrid(); buildHitTable();
});
try{ const saved=localStorage.getItem("theme"); if(saved) document.documentElement.setAttribute("data-theme",saved); }catch(e){}
applyLabel();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change",()=>{ if(!document.documentElement.getAttribute("data-theme")){ buildGrid(); buildHitTable(); } });
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
