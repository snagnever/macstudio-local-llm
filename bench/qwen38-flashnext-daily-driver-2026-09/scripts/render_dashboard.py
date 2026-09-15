#!/usr/bin/env python3
"""Build reports/qwen38-flashnext-driver.html from the summary.json file(s) of
the flashnext-daily-driver campaign (see scripts/summarize_driver.py).

It runs no benchmark. It reads JSON already on disk and writes one
self-contained HTML page (MODELS + RESULTS inline, `charts-common.js` by
relative path), following the conventions in reports/README.md.

Usage:
    python3 scripts/render_dashboard.py --summary results/summary.json \\
        [--summary-b results/summary-b.json] [--sonda results/sonda-512k.json] \\
        [--verdict results/verdict-en.md] --out ../../reports/qwen38-flashnext-driver.html
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

CANDIDATES: list[tuple[str, str, str]] = [
    ("c1", "ddalcu mixed-4/8 @ mlx-serve 26.9.2", "#2563eb"),
    ("c2", "oQ4e @ oMLX 0.6.4", "#16a34a"),
    ("c3", "oQ4e @ oMLX 0.7.0.dev2", "#65a30d"),
    ("c4", "MTPLX Opt-Speed @ 2.11.2", "#dc2626"),
]

NUMERIC_METRICS = (
    "t_turno_s",
    "cold_ttft_s",
    "decode_tps",
    "prefill_tps",
    "wired_peak_gb",
    "mtp_acceptance",
)
SCENARIOS = ("identical", "append", "tool_turn")
CONTEXTS = (8192, 32768, 131072, 262144)
CONTEXT_LABELS: dict[int, str] = {8192: "8K", 32768: "32K", 131072: "128K", 262144: "256K"}

# The 4 line charts (T_turn / warm TTFT / cold TTFT / decode vs. context) plot
# only the Stage A daily bands. The 8K smoke context is left out on purpose:
# c4@8K is a known MTPLX telemetry outlier (tool_turn TTFT ~75s, T_turn ~82s;
# see results/etapa0-smoke.md) that squashes every 32K/128K/256K point near
# zero on a shared axis. 8K stays everywhere else (cache-hit table, wired bar
# chart, RESULTS/scoreboard).
LINE_CHART_CONTEXTS: tuple[int, ...] = (32768, 131072, 262144)

# A candidate is eliminated if it failed a gate at either daily decisive band
# (32K or 128K), even if it still carries a value at some other context (e.g.
# c4 has a real 32K number but is refused at 128K). Elimination must not be
# inferred from a single band in isolation.
ELIMINATION_CONTEXTS: tuple[int, ...] = (32768, 131072)

PLACEHOLDER_VERDICT = "Verdict pending. The campaign is still running."

# The probe JSON (sonda-512k.json) carries free-text notes written in
# Portuguese. The page is in English, so known notes are translated at render
# time. An unknown note passes through unchanged.
SONDA_NOTE_EN: dict[str, str] = {
    "runtime sem YaRN (oMLX): teto 262K": "runtime has no YaRN (oMLX): 262K ceiling",
    "MTPLX 2.11.2 recusa já a 128K (fit de 114.688 tokens); a sonda não rodou": (
        "MTPLX 2.11.2 already refuses at 128K (fit of 114,688 tokens); the probe did not run"
    ),
}


def load_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def merge_summaries(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Stage B (override) replaces the whole `<cand>@<ctx>` entry from Stage A
    (base). It does not merge field by field."""
    merged = dict(base)
    merged.update(override)
    return merged


def build_models() -> list[dict[str, Any]]:
    return [
        {
            "id": cid,
            "tier": "local",
            "label": label,
            "chartLabel": label,
            "color": color,
            "provider": "Alibaba (Qwen)",
            "family": "Qwen3.8-Flash-Next",
            "arch": "moe",
        }
        for cid, label, color in CANDIDATES
    ]


def build_results(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(summary):
        if "@" not in key:
            continue
        cand, ctx_s = key.split("@", 1)
        try:
            ctx = int(ctx_s)
        except ValueError:
            continue
        r = summary[key] or {}
        for metric in NUMERIC_METRICS:
            rows.append({"model": cand, "metric": metric, "context": ctx, "value": r.get(metric)})
        warm = r.get("warm_ttft_s") or {}
        hit = r.get("hit") or {}
        for sc in SCENARIOS:
            rows.append(
                {"model": cand, "metric": "warm_ttft_s", "context": ctx, "scenario": sc, "value": warm.get(sc)}
            )
            rows.append({"model": cand, "metric": "hit", "context": ctx, "scenario": sc, "value": hit.get(sc)})
    return rows


def build_gates(summary: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
    """`<cand>@<ctx>` -> `{"gates": [...failed...], "warnings": [...non-eliminating
    warnings...]}`. This sits outside the RESULTS model: these are derived
    rulings that only the scoreboard uses. `wired>102` comes out as a warning,
    not a gate; see `summarize_driver.apply_warnings`."""
    return {
        key: {
            "gates": list((r or {}).get("gates_failed", []) or []),
            "warnings": list((r or {}).get("warnings", []) or []),
        }
        for key, r in summary.items()
    }


def build_eliminated(summary: dict[str, Any]) -> list[str]:
    """Candidate ids eliminated by a failed gate at 32K or 128K. Used to keep
    a gate-failed candidate out of the scoreboard's default-sort lead and its
    best-cell highlight. It must never read as "winning" just because it
    still carries a value at some other band (see review round 3, finding 1:
    c4 sat first with a green T_turn@32K despite failing gates at 128K)."""
    eliminated = []
    for cid, _, _ in CANDIDATES:
        for ctx in ELIMINATION_CONTEXTS:
            r = summary.get(f"{cid}@{ctx}") or {}
            if r.get("gates_failed"):
                eliminated.append(cid)
                break
    return eliminated


def build_sources(base: dict[str, Any], override: dict[str, Any]) -> dict[str, str]:
    """Which summary file each `<cand>@<ctx>` key's value came from after the
    Stage B override: "B" when overridden (a 3-rep median), "A" otherwise (a
    1-rep Stage A value). The scoreboard (superscript marker) and the T_turn
    chart tooltip show it, so a reader never compares a 3-rep median with a
    1-rep value as if they were equal (review round 3, finding 2).
    """
    sources: dict[str, str] = {key: "A" for key in base}
    for key in override:
        sources[key] = "B"
    return sources


def load_sonda(path: str | None) -> dict[str, Any]:
    """Load the 512K probe JSON and translate known Portuguese notes."""
    sonda = load_json(path)
    for entry in sonda.values():
        if isinstance(entry, dict) and entry.get("note") in SONDA_NOTE_EN:
            entry["note"] = SONDA_NOTE_EN[entry["note"]]
    return sonda


def js_json(obj: Any) -> str:
    """Serialize `obj` for embedding inside the page's inline <script> block.

    Plain `json.dumps` is not safe here: a free-text field (e.g. a probe
    `note` that quotes a log line) could contain the literal substring
    `</script>` and close the tag early, letting whatever follows run
    as markup/script. Escaping "</" as "<\\/" prevents that. "\\/" is a legal
    JSON escape for "/", so `JSON.parse` in the browser (and `json.loads` in
    a test) round-trips it back to "/" unchanged.
    """
    return json.dumps(obj, ensure_ascii=False, indent=1).replace("</", "<\\/")


def render_verdict_html(path: str | None) -> str:
    if not path:
        return f"<p>{PLACEHOLDER_VERDICT}</p>"
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return f"<p>{PLACEHOLDER_VERDICT}</p>"
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return f"<p>{PLACEHOLDER_VERDICT}</p>"
    lines = []
    for p in paragraphs:
        one_line = " ".join(p.split())
        lines.append(f"<p>{html.escape(one_line)}</p>")
    return "\n  ".join(lines)


# ---------------------------------------------------------------------------
# Page template — plain string with @@TOKEN@@ placeholders (not str.format:
# the CSS/JS below is full of literal `{`/`}`, so token replace avoids
# escaping every brace).
# ---------------------------------------------------------------------------

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Qwen3.8-Flash-Next — Responsive Daily Driver</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<script src="charts-common.js"></script>
<style>
  :root {
    --bg: #0f1115;
    --panel: #171a21;
    --border: #262a33;
    --text: #e6e6e6;
    --muted: #9aa0a6;
    --accent: #5aa9ff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    line-height: 1.5;
  }
  header { border-bottom: 1px solid var(--border); }
  .header-inner {
    max-width: 1600px; margin: 0 auto; padding: 24px 32px;
    display: flex; align-items: center; justify-content: space-between; gap: 24px; flex-wrap: wrap;
  }
  header h1 { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
  header p { margin: 0; color: var(--muted); font-size: 13px; }
  .toggle { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--muted); user-select: none; cursor: pointer; }
  .toggle input { accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer; }
  main {
    max-width: 1600px; margin: 0 auto; padding: 24px 32px 64px;
    display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px;
  }
  @media (max-width: 1100px) { main { grid-template-columns: minmax(0, 1fr); } }
  .card { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 18px 20px; }
  .card.wide { grid-column: 1 / -1; }
  .card h2 { margin: 0 0 4px; font-size: 14px; font-weight: 600; letter-spacing: 0.02em; text-transform: uppercase; color: var(--accent); }
  .card .sub { margin: 0 0 16px; font-size: 12px; color: var(--muted); }
  .card p { font-size: 13px; }
  .chart-wrap { position: relative; height: 320px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { padding: 7px 10px; text-align: left; border-bottom: 1px solid var(--border); vertical-align: top; }
  th { color: var(--muted); font-weight: 500; white-space: nowrap; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: baseline; }
  footer { color: var(--muted); font-size: 12px; padding: 16px 32px 32px; text-align: center; }
  /* Sortable scoreboard */
  .scoreboard-wrap { overflow-x: auto; }
  table.scoreboard { width: 100%; min-width: 720px; border-collapse: collapse; font-size: 12px; }
  table.scoreboard th, table.scoreboard td { padding: 7px 10px; border-bottom: 1px solid var(--border); }
  table.scoreboard thead th { color: var(--muted); font-weight: 500; text-align: left; cursor: pointer; user-select: none; position: relative; padding-right: 18px; white-space: nowrap; }
  table.scoreboard thead th.num { text-align: right; }
  table.scoreboard thead th:hover { color: var(--text); }
  table.scoreboard thead th[data-sorted]::after { position: absolute; right: 4px; top: 50%; transform: translateY(-50%); color: var(--accent); font-size: 10px; }
  table.scoreboard thead th[data-sorted="asc"]::after  { content: '▲'; }
  table.scoreboard thead th[data-sorted="desc"]::after { content: '▼'; }
  table.scoreboard tbody td.num { text-align: right; font-variant-numeric: tabular-nums; }
  table.scoreboard tbody td.dash { color: #555; }
  table.scoreboard tbody td.best { color: #7ee787; font-weight: 600; }
  table.scoreboard tbody tr:hover { background: rgba(255,255,255,0.03); }
  table.scoreboard td.model-cell { white-space: nowrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: #cdd1d6; }
  tr.filtered-out { display: none; }
  .scoreboard-hint { font-size: 11px; color: var(--muted); margin: 8px 0 0; }
  .badge-eliminated { margin-left: 6px; font-size: 10px; text-transform: uppercase; letter-spacing: .03em; color: var(--muted); background: #262a33; border-radius: 8px; padding: 1px 6px; font-weight: 600; }
  sup.src-marker { color: var(--accent); margin-left: 1px; }
  /* Cache-hit table */
  .hit-table { margin-bottom: 18px; }
  .hit-table h3 { margin: 0 0 6px; font-size: 12px; color: var(--muted); font-weight: 600; }
  td.hit-ok  { color: #7ee787; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
  td.hit-bad { color: #ff6b6b; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
  td.hit-na  { color: #555; text-align: right; }
  td.hit-refused { color: #e8a33d; font-style: italic; text-align: right; }
  ul.caveats { margin: 0; padding-left: 20px; font-size: 13px; }
  ul.caveats li { margin-bottom: 6px; }
  p.chart-note { grid-column: 1 / -1; margin: 0; font-size: 12px; color: var(--muted); }
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div>
      <h1>Qwen3.8-Flash-Next — Responsive Daily Driver</h1>
      <p>Apple Mac Studio · M4 Max · 128 GB unified · Qwen3.8-Flash-Next (MoE) · 4 candidates (quant × runtime) · campaign <code>bench/qwen38-flashnext-daily-driver-2026-09</code></p>
    </div>
    <div class="header-actions">
      <label class="toggle">
        <input type="checkbox" id="toggleLabels" checked />
        Show chart labels
      </label>
    </div>
  </div>
</header>

<div class="filter-bar" id="filterBar"></div>

<main>

  <section class="card wide" id="sec-verdict">
    <h2>Verdict</h2>
    @@VERDICT_HTML@@
  </section>

  <section class="card wide">
    <h2>Scoreboard</h2>
    <p class="sub">T_turn = <code>tool_turn</code> TTFT + 512 / median decode of the served warm scenarios (<code>identical</code>, <code>append</code>, <code>tool_turn</code>). It is the wait the user feels per turn. Wired peak is the highest <code>wired_peak_gb</code> across the measured bands. A failed gate eliminates the candidate (hit ≥0.90 at 32K/128K, no HTTP errors, swap ≤0.5 GB, correct answer). Wired above 102 GB is a warning in its own column, not an elimination. It is the normal operating point of mlx-serve (KV + a 16 GB prefix cache held in wired memory) when swap does not grow. Default sort is T_turn @32K, lowest first. Click a header to re-sort. Lower is better for T_turn, TTFT and wired; higher is better for decode. The best visible cell in each column is green, using that column's direction.</p>
    <div class="scoreboard-wrap">
      <table class="scoreboard" id="scoreboardDriver">
        <thead>
          <tr>
            <th data-sort="str">Candidate</th>
            <th class="num" data-sort="num">T_turn @32K (s)</th>
            <th class="num" data-sort="num">T_turn @128K (s)</th>
            <th class="num" data-sort="num">cold TTFT @128K (s)</th>
            <th class="num" data-sort="num">decode @128K (tok/s)</th>
            <th class="num" data-sort="num">wired peak (GB)</th>
            <th data-sort="str">failed gates</th>
            <th data-sort="str">warnings</th>
          </tr>
        </thead>
        <tbody><!-- built by charts-common.js --></tbody>
      </table>
    </div>
    <p class="scoreboard-hint" id="srcCaption" hidden>³ median of 3 reps (Stage B); other values: 1 rep (Stage A).</p>
  </section>

  <p class="chart-note">The 8K smoke run is left out of the charts because MTPLX telemetry is inconsistent at 8K. See etapa0-smoke.md.</p>

  <section class="card">
    <h2>T_turn vs context</h2>
    <p class="sub">T_turn = tool_turn TTFT + 512 / median decode of the served warm scenarios (identical, append, tool_turn), per context band. A gap in a line means the band was not measured.</p>
    <div class="chart-wrap"><canvas id="chartTturno"></canvas></div>
  </section>

  <section class="card">
    <h2>Warm TTFT (tool_turn) vs context</h2>
    <p class="sub">Time to first token in the tool-turn scenario, with the cache already warm.</p>
    <div class="chart-wrap"><canvas id="chartWarmTtft"></canvas></div>
  </section>

  <section class="card">
    <h2>Cold TTFT vs context</h2>
    <p class="sub">Time to first token with an empty cache (first load of the prompt at that band).</p>
    <div class="chart-wrap"><canvas id="chartColdTtft"></canvas></div>
  </section>

  <section class="card">
    <h2>Decode vs context</h2>
    <p class="sub">Generation speed (tok/s), median of the warm scenarios.</p>
    <div class="chart-wrap"><canvas id="chartDecode"></canvas></div>
  </section>

  <section class="card wide">
    <h2>Cache hit by scenario</h2>
    <p class="sub">Share of tokens reused from the prefix cache, per scenario and candidate, band by band. Green = ≥0.90 (gate passes); red = below; gray = not measured.</p>
    <div id="hitTable"></div>
  </section>

  <section class="card wide">
    <h2>Wired memory by context</h2>
    <p class="sub">Peak resident unified memory (<code>wired_peak_gb</code>) per context band.</p>
    <div class="chart-wrap"><canvas id="chartWired"></canvas></div>
  </section>

  <section class="card wide">
    <h2>512K capacity probe</h2>
    <p class="sub">Does each candidate reach the 512K band and hold a follow-up without running out of memory? "not tested" means the probe did not run for that candidate.</p>
    <div class="scoreboard-wrap">
      <table class="scoreboard" id="sondaTable">
        <thead>
          <tr>
            <th data-sort="str">Candidate</th>
            <th class="num">Reaches 512K</th>
            <th class="num">Follow-up ok</th>
            <th class="num">decode (tok/s)</th>
            <th class="num">cold TTFT (s)</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody><!-- built in JS from SONDA --></tbody>
      </table>
    </div>
  </section>

  <section class="card wide">
    <h2>Gaps and caveats</h2>
    <ul class="caveats">
      <li>MTPLX cache telemetry is not reliable at 8K.</li>
      <li>The verification hash covers only the final answer, not the full reasoning chain.</li>
      <li>oMLX does not implement YaRN, so its practical context ceiling is 262K.</li>
    </ul>
  </section>

</main>

<footer>Generated by <code>bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_dashboard.py</code> from <code>summary.json</code> (+ <code>summary-b.json</code> when present).</footer>

<script>
const C = ChartsCommon;
C.initTheme();

// ---------------------------------------------------------------------------
// Canonical data model (see reports/README.md). MODELS = one record per
// candidate. RESULTS = one tidy record per measured value — every chart and
// the scoreboard derive from these two arrays.
//   metric='t_turno_s'|'cold_ttft_s'|'decode_tps'|'prefill_tps'|'wired_peak_gb'|'mtp_acceptance'
//     context=8192|32768|131072|262144
//   metric='warm_ttft_s'|'hit'  context=<as above>  scenario=identical|append|tool_turn
// ('t_turno_s' is the data key for T_turn.)
// GATES and SONDA are supplementary lookups (not RESULTS metrics): GATES is
// keyed "<cand>@<ctx>" -> {gates: failed gate names, warnings: [...]}; SONDA
// is keyed by candidate id -> 512K capacity-probe fields.
// ---------------------------------------------------------------------------
const MODELS = @@MODELS_JSON@@;

const RESULTS = @@RESULTS_JSON@@;

const GATES = @@GATES_JSON@@;

const SONDA = @@SONDA_JSON@@;

// Candidate ids eliminated by a failed gate at 32K or 128K (see
// build_eliminated in render_dashboard.py). They stay out of the scoreboard's
// default-sort lead and best-cell highlight, and carry a badge.
const ELIMINATED = @@ELIMINATED_JSON@@;
const ELIMINATED_SET = new Set(ELIMINATED);

// "<cand>@<ctx>" -> "A" (Stage A, 1 rep) | "B" (Stage B override, 3 reps).
// Shown as a superscript in the scoreboard and in the T_turn tooltip so a
// reader never compares a 3-rep median with a 1-rep value unawares.
const SOURCES = @@SOURCES_JSON@@;

const CONTEXTS = [8192, 32768, 131072, 262144];
const CONTEXT_LABELS = { 8192:'8K', 32768:'32K', 131072:'128K', 262144:'256K' };
function ctxLabel(ctx) { return CONTEXT_LABELS[ctx] || String(ctx); }

// The 4 "vs context" line charts use only the daily bands (8K excluded; see
// the chart-note in the markup above). Categorical axis (evenly spaced ticks
// from LINE_CONTEXT_LABELS), not linear-in-tokens, so 32K/128K/256K don't get
// bunched at one edge.
const LINE_CONTEXTS = @@LINE_CONTEXTS_JSON@@;
const LINE_CONTEXT_LABELS = @@LINE_CONTEXT_LABELS_JSON@@;

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

const byId = C.indexModels(MODELS);
const state = C.createFilterState(MODELS);
C.createFilterBar(document.getElementById('filterBar'), state, {});

function dset(id, extra) {
  const m = byId.get(id);
  return Object.assign({ modelId:id, label:m.chartLabel, borderColor:m.color, backgroundColor:m.color }, extra || {});
}

function lineOptions(yLabel) {
  // Categorical x-axis (the default Chart.js category scale, not a linear
  // one), same style as the wired bar chart below, so the 3 daily bands
  // sit evenly spaced instead of bunched together by their raw token counts.
  return Object.assign({}, C.gridOpts(yLabel), {
    scales: {
      x: { grid:{color:'#262a33'}, ticks:{color:'#9aa0a6'} },
      y: { grid:{color:'#262a33'}, ticks:{color:'#9aa0a6'}, title:{display:true,text:yLabel,color:'#9aa0a6'}, beginAtZero:true }
    }
  });
}

// The T_turn vs context tooltip also tags each point with its rep count
// (Stage A = 1 rep, Stage B override = 3 reps). The verdict quotes numbers
// from this chart, so the source must be visible point by point, not only in
// the scoreboard's footnote.
function tturnoOptions(yLabel) {
  const opts = lineOptions(yLabel);
  opts.plugins = Object.assign({}, opts.plugins, {
    tooltip: Object.assign({}, opts.plugins.tooltip, {
      callbacks: {
        label: function (item) {
          const modelId = item.dataset.modelId;
          const ctx = LINE_CONTEXTS[item.dataIndex];
          const m = byId.get(modelId);
          const base = (m ? m.chartLabel : item.dataset.label) + ': ' + item.formattedValue;
          const value = C.metricValue(RESULTS, modelId, {metric:'t_turno_s', context:ctx});
          if (value == null) return base;
          return base + (SOURCES[modelId + '@' + ctx] === 'B' ? ' (3 reps)' : ' (1 rep)');
        }
      }
    })
  });
  return opts;
}

// --- T_turn vs context (line) ---
C.buildGroupedChart('chartTturno', {
  state: state, type: 'line',
  labels: LINE_CONTEXT_LABELS,
  datasets: MODELS.map(m => dset(m.id, {
    data: C.seriesFor(RESULTS, m.id, {metric:'t_turno_s'}, LINE_CONTEXTS, 'context'),
    tension: 0.25, fill: false
  })),
  options: tturnoOptions('T_turn (s)')
});

// --- Warm TTFT (tool_turn) vs context (line) ---
C.buildGroupedChart('chartWarmTtft', {
  state: state, type: 'line',
  labels: LINE_CONTEXT_LABELS,
  datasets: MODELS.map(m => dset(m.id, {
    data: C.seriesFor(RESULTS, m.id, {metric:'warm_ttft_s', scenario:'tool_turn'}, LINE_CONTEXTS, 'context'),
    tension: 0.25, fill: false
  })),
  options: lineOptions('warm TTFT, tool_turn (s)')
});

// --- Cold TTFT vs context (line) ---
C.buildGroupedChart('chartColdTtft', {
  state: state, type: 'line',
  labels: LINE_CONTEXT_LABELS,
  datasets: MODELS.map(m => dset(m.id, {
    data: C.seriesFor(RESULTS, m.id, {metric:'cold_ttft_s'}, LINE_CONTEXTS, 'context'),
    tension: 0.25, fill: false
  })),
  options: lineOptions('cold TTFT (s)')
});

// --- Decode vs context (line) ---
C.buildGroupedChart('chartDecode', {
  state: state, type: 'line',
  labels: LINE_CONTEXT_LABELS,
  datasets: MODELS.map(m => dset(m.id, {
    data: C.seriesFor(RESULTS, m.id, {metric:'decode_tps'}, LINE_CONTEXTS, 'context'),
    tension: 0.25, fill: false
  })),
  options: lineOptions('decode (tok/s)')
});

// --- Wired by context (bars) ---
C.buildGroupedChart('chartWired', {
  state: state,
  labels: CONTEXTS.map(ctxLabel),
  datasets: MODELS.map(m => dset(m.id, {
    data: C.seriesFor(RESULTS, m.id, {metric:'wired_peak_gb'}, CONTEXTS, 'context')
  })),
  options: C.gridOpts('wired peak (GB)')
});

// --- Scoreboard ---
function wiredPeak(id) {
  const vals = CONTEXTS
    .map(ctx => C.metricValue(RESULTS, id, {metric:'wired_peak_gb', context:ctx}))
    .filter(v => v != null);
  return vals.length ? Math.max.apply(null, vals) : null;
}
function gatesCell(id) {
  const fmt = key => {
    const g = GATES[id + '@' + key];
    if (g === undefined) return '—';
    return g.gates.length ? g.gates.join(', ') : 'pass';
  };
  return '32K: ' + fmt('32768') + ' · 128K: ' + fmt('131072');
}
// Display names for warning keys. The data key stays "sem_dados" (it comes
// from summarize_driver.py); the page shows it in English.
const WARNING_LABELS = { 'sem_dados': 'no_data' };
function warningsCell(id) {
  const parts = [];
  ['32768', '131072'].forEach(key => {
    const g = GATES[id + '@' + key];
    if (g && g.warnings && g.warnings.length) {
      parts.push(g.warnings.map(w => WARNING_LABELS[w] || w).join(', ') + ' @' + ctxLabel(Number(key)));
    }
  });
  return parts.length ? parts.join(' · ') : '—';
}

C.buildScoreboard(document.getElementById('scoreboardDriver'), MODELS, RESULTS, [
  { kind:'num', query:{metric:'t_turno_s', context:32768} },
  { kind:'num', query:{metric:'t_turno_s', context:131072} },
  { kind:'num', query:{metric:'cold_ttft_s', context:131072} },
  { kind:'num', query:{metric:'decode_tps', context:131072} },
  { kind:'str', get: m => { const v = wiredPeak(m.id); return v == null ? '—' : v.toFixed(1); } },
  { kind:'str', get: m => gatesCell(m.id) },
  { kind:'str', get: m => warningsCell(m.id) }
]);

// The single decisive context behind each of the 4 per-band numeric columns
// (0 is the Candidate column; 5-7 are wired/gates/warnings, not per-context).
const SB_CONTEXT_BY_COL = { 1:32768, 2:131072, 3:131072, 4:131072 };

// "eliminated" badge next to the candidate name. A candidate that a gate
// eliminated must never read as "winning" just because it still has *a*
// T_turn number at some other band (review round 3, finding 1).
(function addEliminatedBadges() {
  Array.prototype.slice.call(document.querySelectorAll('#scoreboardDriver tbody tr')).forEach(tr => {
    if (!ELIMINATED_SET.has(tr.dataset.modelId)) return;
    const cell = tr.children[0];
    if (!cell) return;
    const badge = document.createElement('span');
    badge.className = 'badge-eliminated';
    badge.textContent = 'eliminated';
    cell.appendChild(badge);
  });
})();

// Stage B ("N reps") superscript on the 4 single-context numeric columns.
// c1/c3 @32K/128K are 3-rep medians while everything else is 1 rep; an
// unlabeled mix reads as apples-to-apples when it isn't (finding 2).
(function addSourceMarkers() {
  Array.prototype.slice.call(document.querySelectorAll('#scoreboardDriver tbody tr')).forEach(tr => {
    const id = tr.dataset.modelId;
    Object.keys(SB_CONTEXT_BY_COL).forEach(colKey => {
      const idx = Number(colKey);
      const ctx = SB_CONTEXT_BY_COL[colKey];
      const cell = tr.children[idx];
      if (!cell || cell.classList.contains('dash')) return;
      if (SOURCES[id + '@' + ctx] === 'B') {
        const sup = document.createElement('sup');
        sup.className = 'src-marker';
        sup.textContent = '³';
        cell.appendChild(sup);
      }
    });
  });
  if (Object.keys(SOURCES).some(k => SOURCES[k] === 'B')) {
    const caption = document.getElementById('srcCaption');
    if (caption) caption.hidden = false;
  }
})();

// A band that ran and refused every request ("sem_dados") reads "refused"
// instead of a plain "—". An untested band and a fully refused one must not
// look identical (finding 3).
(function markRefusedCells() {
  Array.prototype.slice.call(document.querySelectorAll('#scoreboardDriver tbody tr')).forEach(tr => {
    const id = tr.dataset.modelId;
    Object.keys(SB_CONTEXT_BY_COL).forEach(colKey => {
      const idx = Number(colKey);
      const ctx = SB_CONTEXT_BY_COL[colKey];
      const cell = tr.children[idx];
      if (!cell || !cell.classList.contains('dash')) return;
      const g = GATES[id + '@' + ctx];
      if (g && g.warnings && g.warnings.indexOf('sem_dados') !== -1) {
        cell.textContent = 'refused';
      }
    });
  });
})();

// Default sort: ascending on T_turn @32K (column index 1; 0 is the
// Candidate column). Lower is better for T_turn, so ascending (dir=1) puts
// the best candidate on top without the user having to click anything.
C.setupSortableTable('scoreboardDriver', 1, 1);

// Eliminated candidates always sort into a bottom group, in their own
// relative order under whatever column was just sorted. charts-common's
// setupSortableTable has no notion of "eliminated," so this re-groups the
// tbody (a real-DOM appendChild *moves* a row already in the table, it
// doesn't duplicate it) right after every sort instead of patching the
// shared helper.
function regroupEliminated() {
  const table = document.getElementById('scoreboardDriver');
  if (!table) return;
  const tbody = table.querySelector('tbody');
  const rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
  const kept = rows.filter(r => !ELIMINATED_SET.has(r.dataset.modelId));
  const dropped = rows.filter(r => ELIMINATED_SET.has(r.dataset.modelId));
  kept.concat(dropped).forEach(r => tbody.appendChild(r));
}
regroupEliminated();

// charts-common's highlightBestPerColumn always marks the column MAX as
// "best". That is wrong here: T_turn/TTFT/wired are lower-is-better and only
// decode is higher-is-better. Do a small direction-aware highlight locally
// instead of changing the shared helper (which every other report page also
// uses with max-is-best semantics). Eliminated candidates are excluded from
// consideration entirely: a gate-failed row must never read as "winning" a
// column just because it has the extreme number.
const SCOREBOARD_DIRECTIONS = { 1:'min', 2:'min', 3:'min', 4:'max', 5:'min' };
function highlightScoreboardBest() {
  const table = document.getElementById('scoreboardDriver');
  if (!table) return;
  const rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
  Array.prototype.slice.call(table.querySelectorAll('td.best')).forEach(td => td.classList.remove('best'));
  Object.keys(SCOREBOARD_DIRECTIONS).forEach(key => {
    const idx = Number(key);
    const dir = SCOREBOARD_DIRECTIONS[key];
    let best = null;
    let bestCells = [];
    rows.forEach(r => {
      if (r.classList.contains('filtered-out')) return;
      if (ELIMINATED_SET.has(r.dataset.modelId)) return;
      const cell = r.children[idx];
      if (!cell) return;
      const v = parseFloat(cell.textContent.trim());
      if (isNaN(v)) return;
      if (best === null || (dir === 'min' ? v < best : v > best)) { best = v; bestCells = [cell]; }
      else if (v === best) { bestCells.push(cell); }
    });
    bestCells.forEach(c => c.classList.add('best'));
  });
}
highlightScoreboardBest();

// Re-group + re-highlight after any header-driven sort or the dblclick
// reset. charts-common's own click/dblclick handlers (attached by
// setupSortableTable above) run first; same-element listeners fire in
// registration order, so ours runs right after on every click.
Array.prototype.slice.call(document.querySelectorAll('#scoreboardDriver thead th[data-sort]')).forEach(th => {
  th.addEventListener('click', function () { regroupEliminated(); highlightScoreboardBest(); });
  th.addEventListener('dblclick', function () { regroupEliminated(); highlightScoreboardBest(); });
});

state.onChange(st => { C.applyTableFilter('scoreboardDriver', state, {}); highlightScoreboardBest(); });

// --- Cache-hit table (custom markup, driven by RESULTS) ---
// A cell reads "not tested" only when there is no summary row at all for
// that <cand>@<ctx>. When the row exists but its `warnings` carry
// "sem_dados" (the band ran and every request was refused), it reads
// "refused / no data" instead. An untested band and a fully refused one
// must not look identical (finding 3).
function hitCellHtml(id, ctx, sc) {
  const v = C.metricValue(RESULTS, id, {metric:'hit', context:ctx, scenario:sc});
  if (v != null) {
    const cls = v >= 0.90 ? 'hit-ok' : 'hit-bad';
    return '<td class="' + cls + '">' + v.toFixed(2) + '</td>';
  }
  const g = GATES[id + '@' + ctx];
  if (g && g.warnings && g.warnings.indexOf('sem_dados') !== -1) {
    return '<td class="hit-refused">refused / no data</td>';
  }
  return '<td class="hit-na">not tested</td>';
}

(function renderHitTable() {
  const el = document.getElementById('hitTable');
  const present = CONTEXTS.filter(ctx => RESULTS.some(r => r.context === ctx && r.metric === 'hit'));
  if (!present.length) { el.innerHTML = '<p>No cache-hit data yet.</p>'; return; }
  let out = '';
  present.forEach(ctx => {
    out += '<div class="hit-table"><h3>' + ctxLabel(ctx) + '</h3><table><thead><tr><th>Scenario</th>' +
      MODELS.map(m => '<th class="num">' + escapeHtml(m.label) + '</th>').join('') + '</tr></thead><tbody>';
    ['identical', 'append', 'tool_turn'].forEach(sc => {
      out += '<tr><td>' + sc + '</td>' + MODELS.map(m => hitCellHtml(m.id, ctx, sc)).join('') + '</tr>';
    });
    out += '</tbody></table></div>';
  });
  el.innerHTML = out;
})();

// --- 512K capacity probe table ---
(function renderSondaTable() {
  const tbody = document.querySelector('#sondaTable tbody');
  tbody.innerHTML = MODELS.map(m => {
    const s = SONDA[m.id];
    const nameCell = '<td class="model-cell" data-model-id="' + m.id + '"><span class="swatch" style="background:' + m.color + '"></span>' + escapeHtml(m.label) + '</td>';
    if (!s) {
      return '<tr data-model-id="' + m.id + '">' + nameCell + '<td class="num" colspan="4">not tested</td><td></td></tr>';
    }
    const reaches = s.reaches == null ? '—' : (s.reaches ? 'yes' : 'no');
    const followup = s.followup == null ? '—' : (s.followup ? 'yes' : 'no');
    const decode = s.decode_tps == null ? '—' : s.decode_tps;
    const ttft = s.cold_ttft_s == null ? '—' : s.cold_ttft_s;
    const note = s.note ? escapeHtml(s.note) : '';
    return '<tr data-model-id="' + m.id + '">' + nameCell +
      '<td class="num">' + reaches + '</td><td class="num">' + followup + '</td>' +
      '<td class="num">' + decode + '</td><td class="num">' + ttft + '</td><td>' + note + '</td></tr>';
  }).join('');
  state.onChange(st => C.applyTableFilter('sondaTable', state, {}));
})();

// --- Data-label toggle ---
C.bindLabelToggle(document.getElementById('toggleLabels'));
</script>

</body>
</html>
"""


def render_page(
    models: list[dict[str, Any]],
    results: list[dict[str, Any]],
    gates: dict[str, list[str]],
    sonda: dict[str, Any],
    verdict_html: str,
    eliminated: list[str],
    sources: dict[str, str],
) -> str:
    page = PAGE_TEMPLATE
    page = page.replace("@@MODELS_JSON@@", js_json(models))
    page = page.replace("@@RESULTS_JSON@@", js_json(results))
    page = page.replace("@@GATES_JSON@@", js_json(gates))
    page = page.replace("@@SONDA_JSON@@", js_json(sonda))
    page = page.replace("@@LINE_CONTEXTS_JSON@@", js_json(list(LINE_CHART_CONTEXTS)))
    page = page.replace(
        "@@LINE_CONTEXT_LABELS_JSON@@", js_json([CONTEXT_LABELS[c] for c in LINE_CHART_CONTEXTS])
    )
    page = page.replace("@@ELIMINATED_JSON@@", js_json(eliminated))
    page = page.replace("@@SOURCES_JSON@@", js_json(sources))
    page = page.replace("@@VERDICT_HTML@@", verdict_html)
    return page


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--summary", required=True, help="summary.json (Stage A)")
    ap.add_argument("--summary-b", default=None, help="summary-b.json (Stage B; overrides matching keys)")
    ap.add_argument("--sonda", default=None, help="sonda-512k.json (512K capacity probe)")
    ap.add_argument("--verdict", default=None, help="markdown file with the verdict prose")
    ap.add_argument("--out", required=True, help="output path (reports/qwen38-flashnext-driver.html)")
    a = ap.parse_args(argv)

    base = load_json(a.summary)
    override = load_json(a.summary_b)
    summary = merge_summaries(base, override)

    models = build_models()
    results = build_results(summary)
    gates = build_gates(summary)
    sonda = load_sonda(a.sonda)
    verdict_html = render_verdict_html(a.verdict)
    eliminated = build_eliminated(summary)
    sources = build_sources(base, override)

    page = render_page(models, results, gates, sonda, verdict_html, eliminated, sources)
    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    print(f"wrote {out_path} ({len(results)} RESULTS records, {len(models)} models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
