#!/usr/bin/env python3
"""Gera reports/qwen38-flashnext-driver.html a partir do(s) summary.json da
campanha flashnext-daily-driver (ver scripts/summarize_driver.py).

Não roda benchmark nenhum: só lê JSON já escrito em disco e escreve uma página
HTML self-contained (MODELS + RESULTS inline, `charts-common.js` por caminho
relativo), seguindo as convenções descritas em reports/README.md.

Uso:
    python3 scripts/render_dashboard.py --summary results/summary.json \\
        [--summary-b results/summary-b.json] [--sonda results/sonda-512k.json] \\
        [--verdict results/verdict.md] --out ../../reports/qwen38-flashnext-driver.html
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

PLACEHOLDER_VERDICT = "Veredito pendente — campanha em andamento"


def load_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def merge_summaries(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Etapa B (override) substitui integralmente a entrada `<cand>@<ctx>` da
    etapa A (base) — não faz merge campo a campo."""
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


def build_gates(summary: dict[str, Any]) -> dict[str, list[str]]:
    """`<cand>@<ctx>` -> lista de gates falhados (fora do modelo RESULTS: não é
    um valor numérico medido, é um veredito derivado que só o scoreboard usa)."""
    return {key: list((r or {}).get("gates_failed", []) or []) for key, r in summary.items()}


def load_sonda(path: str | None) -> dict[str, Any]:
    return load_json(path)


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
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<title>Flash-Next — driver responsivo</title>
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
  table.scoreboard tbody tr:hover { background: rgba(255,255,255,0.03); }
  table.scoreboard td.model-cell { white-space: nowrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: #cdd1d6; }
  tr.filtered-out { display: none; }
  /* Cache-hit table */
  .hit-table { margin-bottom: 18px; }
  .hit-table h3 { margin: 0 0 6px; font-size: 12px; color: var(--muted); font-weight: 600; }
  td.hit-ok  { color: #7ee787; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
  td.hit-bad { color: #ff6b6b; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
  td.hit-na  { color: #555; text-align: right; }
  ul.caveats { margin: 0; padding-left: 20px; font-size: 13px; }
  ul.caveats li { margin-bottom: 6px; }
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div>
      <h1>Flash-Next — driver responsivo</h1>
      <p>Apple Mac Studio · M4 Max · 128 GB unificados · Qwen3.8-Flash-Next (MoE) · 4 candidatos (quant × runtime) · campanha <code>bench/qwen38-flashnext-daily-driver-2026-09</code></p>
    </div>
    <div class="header-actions">
      <label class="toggle">
        <input type="checkbox" id="toggleLabels" checked />
        Mostrar rótulos nos gráficos
      </label>
    </div>
  </div>
</header>

<div class="filter-bar" id="filterBar"></div>

<main>

  <section class="card wide" id="sec-verdict">
    <h2>Veredito</h2>
    @@VERDICT_HTML@@
  </section>

  <section class="card wide">
    <h2>Placar</h2>
    <p class="sub">T_turno = TTFT quente do cenário <code>tool_turn</code> + tempo de decode de 512 tokens de resposta — o que o usuário sente por turno. Wired pico é o máximo de <code>wired_peak_gb</code> entre as bandas medidas. Gates falhados usa os limiares da campanha (hit ≥0.90 a 32K/128K, sem erro HTTP, wired ≤102 GB, swap ≤0.5 GB, resposta correta). Menor é melhor para T_turno/TTFT/wired e maior é melhor para decode — colunas com semânticas opostas, por isso esta tabela não destaca automaticamente uma "melhor" célula por coluna (só ordena ao clicar no cabeçalho).</p>
    <div class="scoreboard-wrap">
      <table class="scoreboard" id="scoreboardDriver">
        <thead>
          <tr>
            <th data-sort="str">Candidato</th>
            <th class="num" data-sort="num">T_turno @32K (s)</th>
            <th class="num" data-sort="num">T_turno @128K (s)</th>
            <th class="num" data-sort="num">cold TTFT @128K (s)</th>
            <th class="num" data-sort="num">decode @128K (tok/s)</th>
            <th class="num" data-sort="num">wired pico (GB)</th>
            <th data-sort="str">gates falhados</th>
          </tr>
        </thead>
        <tbody><!-- gerado por charts-common.js --></tbody>
      </table>
    </div>
  </section>

  <section class="card">
    <h2>T_turno vs contexto</h2>
    <p class="sub">TTFT quente (tool_turn) + decode de 512 tokens, por banda de contexto. Lacuna na linha = banda não medida.</p>
    <div class="chart-wrap"><canvas id="chartTturno"></canvas></div>
  </section>

  <section class="card">
    <h2>TTFT quente (tool_turn) vs contexto</h2>
    <p class="sub">Tempo até o primeiro token no cenário de turno de ferramenta, cache já aquecido.</p>
    <div class="chart-wrap"><canvas id="chartWarmTtft"></canvas></div>
  </section>

  <section class="card">
    <h2>TTFT frio vs contexto</h2>
    <p class="sub">Tempo até o primeiro token com cache vazio (primeira carga do prompt na banda).</p>
    <div class="chart-wrap"><canvas id="chartColdTtft"></canvas></div>
  </section>

  <section class="card">
    <h2>Decode vs contexto</h2>
    <p class="sub">Velocidade de geração (tok/s), mediana dos cenários quentes.</p>
    <div class="chart-wrap"><canvas id="chartDecode"></canvas></div>
  </section>

  <section class="card wide">
    <h2>Cache hit por cenário</h2>
    <p class="sub">Fração de tokens reaproveitados do prefix cache, por cenário e candidato, banda a banda. Verde = ≥0.90 (gate passa); vermelho = abaixo; cinza = não medido.</p>
    <div id="hitTable"></div>
  </section>

  <section class="card wide">
    <h2>Wired (memória) por contexto</h2>
    <p class="sub">Pico de memória unificada residente (<code>wired_peak_gb</code>) por banda de contexto.</p>
    <div class="chart-wrap"><canvas id="chartWired"></canvas></div>
  </section>

  <section class="card wide">
    <h2>Sonda de capacidade a 512K</h2>
    <p class="sub">Cada candidato alcança a banda de 512K e sustenta um follow-up sem estourar memória? "não testado" quando a sonda não rodou para o candidato.</p>
    <div class="scoreboard-wrap">
      <table class="scoreboard" id="sondaTable">
        <thead>
          <tr>
            <th data-sort="str">Candidato</th>
            <th class="num">Alcança 512K</th>
            <th class="num">Follow-up ok</th>
            <th class="num">decode (tok/s)</th>
            <th class="num">cold TTFT (s)</th>
            <th>Nota</th>
          </tr>
        </thead>
        <tbody><!-- gerado via JS a partir de SONDA --></tbody>
      </table>
    </div>
  </section>

  <section class="card wide">
    <h2>Lacunas e ressalvas</h2>
    <ul class="caveats">
      <li>A telemetria de cache do MTPLX não é confiável a 8K.</li>
      <li>O hash de verificação cobre só a resposta final, não a cadeia de raciocínio inteira.</li>
      <li>O oMLX não implementa YaRN — o teto prático de contexto fica em 262K.</li>
    </ul>
  </section>

</main>

<footer>Gerado por <code>bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_dashboard.py</code> a partir de <code>summary.json</code> (+ <code>summary-b.json</code> quando presente).</footer>

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
// GATES and SONDA are supplementary lookups (not RESULTS metrics): GATES is
// keyed "<cand>@<ctx>" -> list of failed gate names; SONDA is keyed by
// candidate id -> 512K capacity-probe fields.
// ---------------------------------------------------------------------------
const MODELS = @@MODELS_JSON@@;

const RESULTS = @@RESULTS_JSON@@;

const GATES = @@GATES_JSON@@;

const SONDA = @@SONDA_JSON@@;

const CONTEXTS = [8192, 32768, 131072, 262144];
const CONTEXT_LABELS = { 8192:'8K', 32768:'32K', 131072:'128K', 262144:'256K' };
function ctxLabel(ctx) { return CONTEXT_LABELS[ctx] || String(ctx); }

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
  return Object.assign({}, C.gridOpts(yLabel), {
    scales: {
      x: { type:'linear', grid:{color:'#262a33'}, ticks:{color:'#9aa0a6'}, title:{display:true,text:'Contexto (tokens)',color:'#9aa0a6'} },
      y: { grid:{color:'#262a33'}, ticks:{color:'#9aa0a6'}, title:{display:true,text:yLabel,color:'#9aa0a6'}, beginAtZero:true }
    }
  });
}

// --- T_turno vs contexto (linha) ---
C.buildGroupedChart('chartTturno', {
  state: state, type: 'line',
  labels: CONTEXTS,
  datasets: MODELS.map(m => dset(m.id, {
    data: C.seriesFor(RESULTS, m.id, {metric:'t_turno_s'}, CONTEXTS, 'context'),
    tension: 0.25, fill: false
  })),
  options: lineOptions('T_turno (s)')
});

// --- TTFT quente (tool_turn) vs contexto (linha) ---
C.buildGroupedChart('chartWarmTtft', {
  state: state, type: 'line',
  labels: CONTEXTS,
  datasets: MODELS.map(m => dset(m.id, {
    data: C.seriesFor(RESULTS, m.id, {metric:'warm_ttft_s', scenario:'tool_turn'}, CONTEXTS, 'context'),
    tension: 0.25, fill: false
  })),
  options: lineOptions('TTFT quente — tool_turn (s)')
});

// --- TTFT frio vs contexto (linha) ---
C.buildGroupedChart('chartColdTtft', {
  state: state, type: 'line',
  labels: CONTEXTS,
  datasets: MODELS.map(m => dset(m.id, {
    data: C.seriesFor(RESULTS, m.id, {metric:'cold_ttft_s'}, CONTEXTS, 'context'),
    tension: 0.25, fill: false
  })),
  options: lineOptions('TTFT frio (s)')
});

// --- Decode vs contexto (linha) ---
C.buildGroupedChart('chartDecode', {
  state: state, type: 'line',
  labels: CONTEXTS,
  datasets: MODELS.map(m => dset(m.id, {
    data: C.seriesFor(RESULTS, m.id, {metric:'decode_tps'}, CONTEXTS, 'context'),
    tension: 0.25, fill: false
  })),
  options: lineOptions('decode (tok/s)')
});

// --- Wired por contexto (barras) ---
C.buildGroupedChart('chartWired', {
  state: state,
  labels: CONTEXTS.map(ctxLabel),
  datasets: MODELS.map(m => dset(m.id, {
    data: C.seriesFor(RESULTS, m.id, {metric:'wired_peak_gb'}, CONTEXTS, 'context')
  })),
  options: C.gridOpts('wired pico (GB)')
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
    return g.length ? g.join(', ') : 'passa';
  };
  return '32K: ' + fmt('32768') + ' · 128K: ' + fmt('131072');
}

C.buildScoreboard(document.getElementById('scoreboardDriver'), MODELS, RESULTS, [
  { kind:'num', query:{metric:'t_turno_s', context:32768} },
  { kind:'num', query:{metric:'t_turno_s', context:131072} },
  { kind:'num', query:{metric:'cold_ttft_s', context:131072} },
  { kind:'num', query:{metric:'decode_tps', context:131072} },
  { kind:'str', get: m => { const v = wiredPeak(m.id); return v == null ? '—' : v.toFixed(1); } },
  { kind:'str', get: m => gatesCell(m.id) }
]);
C.setupSortableTable('scoreboardDriver');
state.onChange(st => C.applyTableFilter('scoreboardDriver', state, {}));

// --- Cache-hit table (custom markup, driven by RESULTS) ---
(function renderHitTable() {
  const el = document.getElementById('hitTable');
  const present = CONTEXTS.filter(ctx => RESULTS.some(r => r.context === ctx && r.metric === 'hit'));
  if (!present.length) { el.innerHTML = '<p>Sem dados de cache hit ainda.</p>'; return; }
  let out = '';
  present.forEach(ctx => {
    out += '<div class="hit-table"><h3>' + ctxLabel(ctx) + '</h3><table><thead><tr><th>Cenário</th>' +
      MODELS.map(m => '<th class="num">' + escapeHtml(m.label) + '</th>').join('') + '</tr></thead><tbody>';
    ['identical', 'append', 'tool_turn'].forEach(sc => {
      out += '<tr><td>' + sc + '</td>' + MODELS.map(m => {
        const v = C.metricValue(RESULTS, m.id, {metric:'hit', context:ctx, scenario:sc});
        if (v == null) return '<td class="hit-na">não testado</td>';
        const cls = v >= 0.90 ? 'hit-ok' : 'hit-bad';
        return '<td class="' + cls + '">' + v.toFixed(2) + '</td>';
      }).join('') + '</tr>';
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
      return '<tr data-model-id="' + m.id + '">' + nameCell + '<td class="num" colspan="4">não testado</td><td></td></tr>';
    }
    const reaches = s.reaches == null ? '—' : (s.reaches ? 'sim' : 'não');
    const followup = s.followup == null ? '—' : (s.followup ? 'sim' : 'não');
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
) -> str:
    page = PAGE_TEMPLATE
    page = page.replace("@@MODELS_JSON@@", json.dumps(models, ensure_ascii=False, indent=1))
    page = page.replace("@@RESULTS_JSON@@", json.dumps(results, ensure_ascii=False, indent=1))
    page = page.replace("@@GATES_JSON@@", json.dumps(gates, ensure_ascii=False, indent=1))
    page = page.replace("@@SONDA_JSON@@", json.dumps(sonda, ensure_ascii=False, indent=1))
    page = page.replace("@@VERDICT_HTML@@", verdict_html)
    return page


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--summary", required=True, help="summary.json (etapa A)")
    ap.add_argument("--summary-b", default=None, help="summary-b.json (etapa B; sobrescreve chaves iguais)")
    ap.add_argument("--sonda", default=None, help="sonda-512k.json (sonda de capacidade a 512K)")
    ap.add_argument("--verdict", default=None, help="markdown com o veredito em prosa")
    ap.add_argument("--out", required=True, help="caminho de saída (reports/qwen38-flashnext-driver.html)")
    a = ap.parse_args(argv)

    base = load_json(a.summary)
    override = load_json(a.summary_b)
    summary = merge_summaries(base, override)

    models = build_models()
    results = build_results(summary)
    gates = build_gates(summary)
    sonda = load_sonda(a.sonda)
    verdict_html = render_verdict_html(a.verdict)

    page = render_page(models, results, gates, sonda, verdict_html)
    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    print(f"wrote {out_path} ({len(results)} RESULTS records, {len(models)} models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
