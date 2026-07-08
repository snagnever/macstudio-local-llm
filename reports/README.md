# reports/ — maintenance guide

Two self-contained dashboards for local-LLM benchmarks on the Mac Studio (M4 Max / 128GB):

| File | What it shows | Primary scope |
|---|---|---|
| `benchmark-charts.html` | On-rig measurements (accuracy n=100, LCB n=50, tool calling, throughput, speed probe, prefill, elapsed) | The local runs themselves — what was actually measured on this rig |
| `quality-benchmarks-charts.html` | Local-vs-frontier comparison using **published** scores (MMLU-Pro, GPQA, SWE-V, AIME, LCB v6, T-Bench, MMMU) | How the local models rank against frontier / open-weight references |

Both files share a common runtime, `charts-common.js`, and the same two-array data model (`MODELS` + `RESULTS`). Each page still has its own roster, colors, and prose — they are not merged — but the machinery (filter bar, chart builders, scoreboard, sortable/best-highlight helpers) lives in one place. A fix to the machinery is a single edit to `charts-common.js`; a data change is an edit to the `RESULTS`/`MODELS` arrays inline in one page.

## Architecture

Three files, no build step, no network beyond the two CDN `<script>` tags:

- `charts-common.js` — shared runtime, exposes one global `window.ChartsCommon`. Loaded via a plain `<script src="charts-common.js">` (classic script, **not** an ES module — modules would break `file://` opening under CORS). Holds: theme + datalabels + the `Show data labels` toggle, the global filter state + sticky filter bar, chart builders (`buildGroupedChart`, `buildRankedChart`, `buildScatterChart`, `buildRadarChart`), data derivation (`metricValue`, `seriesFor`, `deriveRanked`), and the scoreboard (`buildScoreboard`, `setupSortableTable`, `highlightBestPerColumn`, `applyTableFilter`).
- `benchmark-charts.html`, `quality-benchmarks-charts.html` — each holds its own `MODELS` + `RESULTS` inline at the bottom of `<main>`'s `<script>`, then a handful of builder calls. Open in a browser or attach via the Launch preview panel.
- Renderer: Chart.js 4.4.1 + chartjs-plugin-datalabels 2.2.0, both via CDN. Keeping the pages offline-capable would only require vendoring those two files into `reports/vendor/` and repointing the `<script src>` — not done today.

### Data model (`MODELS` + `RESULTS`)

Everything on a page — every chart, the scoreboard, the filter bar, the scatter, the radar — derives from two inline arrays. **Numbers live exactly once, in `RESULTS`.**

- **`MODELS`** — one record per model: `{ id, tier, arch, quant, color, label, chartLabel, ... }`.
  - `tier` is `'local' | 'frontier' | 'open'`. `arch` (`'dense'|'moe'`) and `quant` are optional — frontier/open reference models omit them (and therefore always pass the arch/quant filters; the tier pill is what hides them).
  - `label` is the short name (filter checkbox + scoreboard cell). `chartLabel` is the longer legend label for grouped charts. On `benchmark-charts.html`, `refLabel` is the model name used in the ranked "vs frontier" charts and `refNote` is a **compact symbolic marker** (`*`, `‡`, `†`) appended to that name — the markers are explained in each chart's caption. Keep `refNote` to symbols only; **prose caveats go in `caveat`** (see below), never in `refNote`, or they crowd the model name off the bar. `refExclude:true` keeps a model out of those ranked charts entirely (used for `agents-a1-xl-mlx`).
  - `caveat` is a prose measurement caveat (e.g. `"GPQA: 15/100 truncated at 32k; true ≈78-85%"`, `"LCB community ~80"`). It is **not** shown in the y-axis label — it surfaces in the bar's **hover tooltip** (word-wrapped), alongside any per-record `note`. Use it for anything longer than a symbol.
  - `diskGB` (benchmark page) feeds the scatter bubble radius. `rankedOnly:true` (quality page) keeps a model out of the scoreboard/headline/checkboxes/radar and only shows it in the ranked charts (used for `gemma-4-31b`, which appears only in T-Bench).
  - `provider` and `family` are the identity dimensions surfaced as **filter pills** and as columns in the Models table. To keep the pill rows compact, both use a **collapsed taxonomy**:
    - `provider` — **local** models keep a specific vendor (`Alibaba (Qwen)`, `Google`, `NVIDIA`, `DeepSeek`, `InternScience`, …); **frontier** (closed-weight) references all share `Frontier`; **open**-weight references all share `Open Frontier`. So the pills are "which local vendor, or is this a frontier / open reference" rather than one pill per vendor. (Note `dsflash` is tier `local` on the quality page, so it keeps `DeepSeek`, but the tier-`open` DeepSeeks on the benchmark page collapse to `Open Frontier`.)
    - `family` = model line with **versions merged to one base name**: `Qwen3-Coder` / `Qwen3.6` / `Qwen3` / `Qwen2.5` → `Qwen`; `Gemma 4` → `Gemma`; `Claude Opus` / `Claude Sonnet` → `Claude`; `GPT`, `o-series`, `Gemini`, `DeepSeek`, `Llama`, `Kimi`, `Nemotron`, `Agents-A1` stay as-is. The exact version is still visible in the model name (the Model column / `label`), so collapsing loses nothing.
    - Both should be set on every record so the pills group cleanly. The Models tables list only local rows, so the `Frontier` / `Open Frontier` buckets appear only as filter pills, never as table cell values.
  - `hf` is the HuggingFace repo URL for the on-disk quant (from `../docs/models/*.md`). The Models-table row wraps the model name in a link to it. Reference (frontier) models omit `hf`.
  - **Telemetry fields** (local models with a qualifying speed probe only): `peakRamGB`, `cpuPct`, `gpuPct`, `powerW`, `probeN` (sample count), `probeDate`, and optional `probeNote`. These populate the **Peak RAM** column and the **Resource usage** section. They are hand-entered from the speed-probe artifacts (see "Speed probe" below) and only added when `probeN ≥ 10`; models below the gate or without a probe omit them and render `—`.
- **`RESULTS`** — one tidy record per measured value: `{ model, metric, value, ...selector, note? }`. `value:null` means "not run" (renders as a gap / `—`). The extra selector key names the axis:
  - benchmark page: `metric:'accuracy'|'toolScore'|'toolTps'|'genTps'|'effTps'|'prefillEffTps'|'probeSeconds'|'probeReasonTok'|'elapsedMin'` with `bench` / `suite` / `scenario` / `context` / `prompt` as appropriate.
  - quality page: `metric:'score'`, `bench` ∈ `{MMLU-Pro, GPQA, SWE-V, AIME, LCB, TBench, MMMU}`.
  - `note` is a per-record footnote (e.g. `"'26"`, `"(measured; comm ~80)"`, `"(P)"`) shown in the ranked chart's **hover tooltip for that benchmark only** — so a model can carry a different note per benchmark. (Notes and `caveat` used to be concatenated into the y-axis label; they moved to the tooltip so long prose can't push the model name off the bar.)

A value is fetched with `ChartsCommon.metricValue(RESULTS, id, query)` where `query` is the metric + selector (e.g. `{metric:'accuracy', bench:'MMLU'}`). `seriesFor(...)` returns an ordered array for grouped/line datasets; `deriveRanked(...)` returns the filtered, sorted rows for a ranked chart.

### Filtering & the sticky filter bar

`createFilterBar(...)` renders a sticky bar under the header with: per-model checkboxes (local models only — frontier/open are governed by the tier pills), **All/None**, and pill toggles for **Tier / Provider / Family / Arch / Quant**, plus the section anchor-nav. A model is visible when `checked ∧ tier ∧ provider ∧ family ∧ arch ∧ quant` all pass. Each pill group only renders when the roster has ≥2 distinct values for it, so a page with a single provider simply won't show the Provider pills. Every chart, the scoreboard, the Models table, and the Resource-usage table react instantly:

- **Grouped bar / line charts** keep every dataset and hide filtered ones in place (`setDatasetVisibility`) — the legend stays complete (struck-through when hidden), and clicking a **local** model's legend entry toggles it globally across all charts + the checkboxes.
- **Ranked horizontal charts** drop filtered rows and re-rank.
- **The scoreboard** hides filtered rows and recomputes the green best-per-column highlight over the visible rows.
- **The Models table and the Resource-usage table** hide filtered rows the same way (`applyTableFilter` by `data-model-id`).
- **The radar** has its own separate 2–3 model picker; the global filter only constrains which models the picker offers.

### New visualizations

- **Quality-vs-speed scatter** (`benchmark-charts.html` only — the quality page has no throughput data): benchmark score vs generation tok/s, bubble radius ∝ disk GB. The y-axis `<select>` picks a benchmark; **Composite** averages the six accuracy suites (skipping any that are missing, flagged in the tooltip).
- **Model radar** (both pages): up to 3 models across the 0–100 benchmark axes. Axes are **fixed 0–100** — every axis is already a percentage, and fixed bounds keep the polygon shapes comparable no matter which models are selected (min-max normalization would silently change a model's shape when the comparison set changes). No throughput axis; the scatter covers that.
- **Resource usage** (both pages): a static, sortable, filter-aware table (`#telemetryTable`) with **Peak RAM / Avg CPU % / Avg GPU % / Peak power / Samples / Probe date** per local model. Unlike the charts it is **not** derived from `RESULTS` — the rows are hand-authored HTML (one `<tr data-model-id="…">` per model, matching the `MODELS` telemetry fields), because telemetry only exists for the subset of models with a speed probe. Models without a qualifying probe (`probeN < 10` or none) still get a row, rendered as `—`, so the filter and the roster stay complete. Wire it with `C.setupSortableTable('telemetryTable')` + `state.onChange(st => C.applyTableFilter('telemetryTable', state, {}))`.
- **Category anchor-nav**: the section links in the filter bar scroll to full-width `<h2 class="category-heading">` headings. These are plain scroll anchors, not show/hide tabs — a `display:none` container renders a Chart.js canvas at 0×0, and anchors also keep Cmd+F / full-page printing working.

## Where the data comes from

### 1. Accuracy benchmarks (HumanEval, MMLU, MATH, DROP, GPQA, LiveCodeBench) and tool-calling

**Source dir:** `local-llm-bench-m4-32gb/benchmarks/runs/`

**Benchmark list as of 2026-05-17:** `mmlu`, `math`, `humaneval`, `gpqa`, `drop`, `livecodebench`.
`livecodebench` is loaded directly from `livecodebench/code_generation_lite` on HuggingFace
Hub (the dataset's loading script is no longer accepted by modern `datasets`; the loader
reads the JSONL shards via `huggingface_hub.hf_hub_download`). Use `--lcb-version
release_v6` (default) for the broadest, most contamination-resistant snapshot. The
summary JSON keeps the same shape as the other accuracy benchmarks.

Each run produces three files:
- `<bench>_<model>_<timestamp>.jsonl` — per-question log
- `<bench>_<model>_<timestamp>_summary.json` — **the canonical scoreboard for that run**
- `console_<bench>_<model>.log` — live stdout (useful when the summary hasn't been written yet)

The summary JSON has this shape (extract from `humaneval_qwen_qwen3-coder-next_20260517_153426_summary.json`):

```json
{
  "benchmark": "humaneval",
  "model": "qwen/qwen3-coder-next",
  "score": 0.89,
  "score_pct": "89.0%",
  "correct": 89,
  "total": 100,
  "elapsed_min": 16.6,
  "model_config": { "size_gb": 60.3, "params": "80B", ... },
  "hardware": { "cpu": "Apple M4 Max", "total_ram_gb": 128, ... }
}
```

Tool-calling summaries (`toolcall_<suite>_<model>_<timestamp>_summary.json`) additionally have:
- `suite` ("jdhodges" or "veerman")
- `by_category` (per-skill breakdown: tool_selection, argument_accuracy, multi_tool, edge_cases, format_compliance)
- `fresh_tok_weighted_tps` — the throughput number plotted in the tool-calling tps chart

**Quick extraction command:**

```bash
for f in local-llm-bench-m4-32gb/benchmarks/runs/*_summary.json; do
  jq -r '[.benchmark // .suite, .model, .score_pct, .elapsed_min, (.fresh_tok_weighted_tps // "-")] | @tsv' "$f"
done | column -t
```

If a run is in progress (no `_summary.json` yet), tail the matching `console_*.log` and read the running score from the last line (format: `... score: NN%`).

### 1b. Terminal-Bench 2.0 (on-rig Phase A)

**Source dirs:**
- Canonical headline summaries: `tools/local-llm-bench-m4-32gb/benchmarks/runs/tbench_<model>_<timestamp>_summary.json` (same schema as the other accuracy benches — `score`, `score_pct`, `correct`, `total`, `elapsed_min`).
- Raw run dirs (per-task transcripts, logs, lockfiles): `bench/terminal-bench/logs/tbench-runs<run-name>/` with a `result.json` at the root.
- Driver scripts that launched each run: `bench/terminal-bench/logs/run-tbench-<run-name>.sh` — use these as templates when adding new models.

**Harness:** Harbor + LiteLLM proxy → LM Studio, terminus-2 agent in Docker (linux/amd64), `--concurrency 1`, `--agent-timeout-multiplier 0.5` (caps the 14 long-budget tasks; full-budget would land ≤5 pp higher). N=89 vanilla T-Bench 2.0 task set.

**Pass-rate extraction (from `result.json`):**

```bash
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); ev=next(iter(d['stats']['evals'].values())); print(f\"{ev['metrics'][0]['mean']*100:.1f}% ({len(ev['reward_stats']['reward'].get('1.0',[]))}/{ev['n_trials']})\")" bench/terminal-bench/logs/tbench-runs<run-name>/result.json
```

…or just read the `_summary.json` if it exists (the runner writes one once the run finishes).

**Final standings as of 2026-05-29** — Phase A + B both complete, all 7 local models measured (live in `benchmark-charts.html` chartTBench + scoreboard, and `quality-benchmarks-charts.html` chartTBench + scoreboardQuality):

| Run dir | Model | Score |
|---|---|---|
| `coder-next` | qwen/qwen3-coder-next | **32.6 %** (29/89) |
| `qwen-27b` | qwen3.6-27b | **31.5 %** (28/89) |
| `qwen-35b-a3b-6bit` | qwen3.6-35b-a3b@6bit | **28.1 %** (25/89) |
| `gemma-31b` | gemma-4-31b-it-mlx | **22.5 %** (20/89) |
| `gemma-26b-a4b-6bit` | gemma-4-26b-a4b-it-mlx@6bit | **21.3 %** (19/89) |
| `gemma-26b-a4b-4bit` | gemma-4-26b-a4b-it-mlx@4bit | **20.2 %** (18/89) |
| `gemma-e4b` | gemma-4-e4b-it-mlx | **4.5 %** (4/89) |

Full write-up: [`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`](../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md). For wall-clock per run, see the matching `tbench_<model>_<timestamp>_summary.json`.

**To refresh after a new run completes:**

1. Confirm the summary JSON exists at `tools/local-llm-bench-m4-32gb/benchmarks/runs/tbench_<model>_<timestamp>_summary.json`. If only the raw `result.json` is available, the score is `stats.evals.<key>.metrics[0].mean`.
2. In `benchmark-charts.html`, update (or add) the T-Bench `RESULTS` record: `{ model:'<id>', metric:'accuracy', bench:'TBench', value:<n> }`. The scoreboard T-Bench column reads it automatically. For the `chartTBench` bar's `— NN/89` suffix, update the `TB_ORDER` entry for that model (the order + fractions are chart-specific display, so they live in that one array).
3. In `quality-benchmarks-charts.html`, update (or add) `{ model:'<id>', metric:'score', bench:'TBench', value:<n>, note:'…' }` in `RESULTS`. The scoreboard and the `chartTBench` ranked chart both re-derive from it.
4. Refresh the subtitle of both T-Bench cards and the scoreboard hints with the new headline numbers (prose is not auto-derived).

### 2. Speed probe (3-prompt cold latency, system metrics)

**Source dir:** `local-llm-bench-m4-32gb/results/speed_probe/`

Pattern: `<model>_<timestamp>_results.json` + `<model>_<timestamp>_macmon.jsonl` (macmon power/temp samples).

The `results.json` has the three prompts (`trivial`, `mmlu_atmosphere`, `code_second_largest`) with per-prompt `elapsed`, `completion_tokens`, `reasoning_tokens` — that last field is what drives the "reasoning tokens emitted" chart.

System metrics block: `peak_ram_gb`, `peak_swap_gb`, `avg_gpu_pct`, `peak_power_w`, `samples`. **Trust nothing under ~10 samples** — that's a known quality issue for short runs (the coder-next probe only has 2 samples and the RAM/power numbers are statistically meaningless).

This block is also the source for the **Resource usage** table and the Models-table **Peak RAM** column (the `MODELS` telemetry fields `peakRamGB` / `gpuPct` / `powerW` / `probeN`). One field is **not** in `results.json`: **Avg CPU %** — `system_metrics` has no CPU aggregate, so compute it as the mean of per-sample `cpu_usage_pct` (a 0–1 fraction) from the matching `*_macmon.jsonl`, ×100. Cross-check: the mean of the macmon `gpu_usage[1]` fractions should match `avg_gpu_pct`. Extraction one-liner (run against the source dir, pick the run with `samples ≥ 10`):

```bash
python3 - "$STEM" <<'PY'
import json, sys
stem = sys.argv[1]  # e.g. qwen3.6-27b_20260517_172229
sm = json.load(open(stem + "_results.json"))["system_metrics"]
cpu = [json.loads(l)["cpu_usage_pct"] for l in open(stem + "_macmon.jsonl") if l.strip()]
print(f"peakRamGB={sm['peak_ram_gb']} gpuPct={sm['avg_gpu_pct']} powerW={sm['peak_power_w']} "
      f"probeN={sm['samples']} cpuPct={sum(cpu)/len(cpu)*100:.1f}")
PY
```

Note that some historical probe filenames (e.g. the 2026-04-08 `google_gemma-4-26b-a4b` run) did not record the quant — attribute those with a `probeNote` rather than guessing a precise quant match.

### 3. Throughput benchmarks (creative-writing, doc-summary, ops-agent, prefill-test)

**Source dir:** `benchmarking/local-llm-bench/results/<model-slug>/<scenario>/`

Each scenario directory contains:
- `<machine-config>_<backend>.json` — raw per-turn measurements
- `<machine-config>_<backend>.md` — pre-rendered markdown table
- `<machine-config>_<backend>_responses.md` — full model responses for sanity-checking

Backend suffix matters: `lmstudio` (default), `lmstudio-mlx` (explicit MLX path), `ollama`, `omlx`. Match what the model card / current rig uses.

The markdown summaries already have the headline numbers — read them, don't re-derive. The four numbers per scenario that the chart consumes:

- **Avg generation tok/s** — pure decode speed, headline of every `.md`
- **Avg effective tok/s** — end-to-end including prefill, headline of every `.md`
- For `prefill-test` specifically, the per-turn `Effective tok/s` column at context [655, 1453, 3015, 8496] feeds the prefill-degradation line chart.

### 4. Third-party reference scores (frontier + open-weight)

The reference numbers in the "Local vs frontier" section came from a **research subagent web-search pass on 2026-05-17**. They are inlined into `RESULTS` in each HTML page: on `benchmark-charts.html` as `{metric:'accuracy', bench:…}` records for the frontier/open `MODELS` entries (which carry a `refNote`), and on `quality-benchmarks-charts.html` as `{metric:'score', bench:…}` records with a per-record `note`.

Refresh procedure:

1. Spawn a research agent with this brief:

> Find current published benchmark scores for major frontier and open-weight LLMs on MMLU, HumanEval, MATH, DROP, GPQA Diamond. Prefer first-party model cards, system cards, or technical reports. Return JSON array with shape `{model, provider, tier, scores: {MMLU, HumanEval, MATH, DROP, GPQA}, sources, notes}`. Use `null` for unverified — do NOT guess. Note when MMLU is actually MMMLU, MATH is actually MATH-500 or AIME 2025, GPQA is not Diamond.

2. The Anthropic **Sonnet 4.6 system card** (search for the latest PDF on anthropic.com/news) is the single best source — Table 2.1.A has apples-to-apples numbers for Opus 4.5/4.6, Sonnet 4.5/4.6, Gemini 3 Pro, GPT-5.2 on the same harness.

3. Other primary sources to crosswalk:
   - OpenAI: `openai.com/index/introducing-<model>/` blog posts + system cards
   - Google DeepMind: `blog.google/products/gemini/` + `storage.googleapis.com/deepmind-media/gemini/` tech reports
   - DeepSeek: HF model cards (`huggingface.co/deepseek-ai/<model>`) + arXiv tech reports
   - Meta: `llama.com/models/<version>/` + HF model cards
   - Qwen: HF model cards (`huggingface.co/Qwen/<model>`)

4. Convention reminders:
   - **GPQA**: always plot Diamond (198q). If a source reports the 448q Main set, note in the model's `note` field, do not mix axes.
   - **MATH**: original MATH for local/legacy; mark `†` for MATH-500, `‡` for AIME 2025.
   - **MMLU**: mark `*` if it's actually MMMLU (multilingual — Anthropic 4.x and recent Google standard).
   - **DROP / HumanEval**: expect nulls. Most frontier providers stopped reporting these after mid-2024.
   - **Reasoning models** (o3, R1, Claude with thinking, Gemini 2.5/3, GPT-5): note in `note` that scores reflect test-time compute. They are **not** comparable to single-pass forward inference.

## Page structure — where to edit what

`benchmark-charts.html` groups its cards under four category headings (the filter-bar nav jumps to them). Charts derive from `RESULTS` unless noted:

| Section (anchor) | Cards | Source |
|---|---|---|
| **Overview** (`sec-overview`) | System card (hard-coded markup), **Models benchmarked** (hard-coded `<table id="modelsTable">`, editorial), **Benchmark scoreboard** (`#scoreboardMain`, generated), **Quality-vs-speed scatter** (`chartScatter`) | machine-configuration.md / local-llm-reference.md / `RESULTS` |
| **Coding** (`sec-coding`) | `chartLCB` (local), `chartRefHumanEval`, `chartRefLCB` | §1 + §4 |
| **Knowledge & reasoning** (`sec-knowledge`) | `chartAccuracy`, `chartRefMMLU/MATH/DROP/GPQA`, **Model radar** (`chartRadar`) | §1 + §4 |
| **Tool use & agents** (`sec-tools`) | `chartTBench` (local), `chartToolScore`, `chartToolTps` | §1b + §1 |
| **Performance** (`sec-performance`) | `chartGenTps`, `chartEffectiveTps`, `chartPrefill`, `chartProbeTotal`, `chartProbeReason`, `chartElapsed` | §3 / §2 |

The six `chartRef*` charts are built by `buildRankedChart(...)` over the full `MODELS` list (local + frontier + open), querying `{metric:'accuracy', bench:…}`. Local models supply the same values as the grouped `chartAccuracy`; frontier/open models supply the published `RESULTS` records.

`quality-benchmarks-charts.html` follows the same category shape (Overview / Knowledge / Coding & agents / Caveats & verdict): Scope card, editorial Models card (`#modelsTable`), Legend card, generated scoreboard (`#scoreboardQuality`, mixes local + frontier + open rows), the `chartHeadline` grouped bar, then `buildRankedChart` charts for MMLU-Pro / GPQA / AIME / MMMU / SWE-V / LCB / T-Bench, the Model radar, and finally the quant-caveats panel and verdict table.

The toggle `Show data labels on bars` (header) flips the shared `labelsOn` inside `charts-common.js` via `ChartsCommon.bindLabelToggle(...)`. Every chart built through the helpers is auto-registered, so no wiring is needed when adding one. The scoreboard is an HTML table, so the toggle does not affect it.

## Models card — Best for / Expected usage

Both files use a **wide** card (`<section class="card wide">`) for the model table so the qualitative-description columns have room to breathe. The two right-most cells per row carry the editorial copy:

- **`<td class="bestfor">`** — short phrase, 1 sentence: what tasks this model is good at. Lead with the strength, not the spec.
- **`<td class="usage">`** — 1–2 sentences: how to actually use it in rotation (decode speed, when to pick it, caveats, known regressions).

CSS clamps `max-width` so the column doesn't stretch into a single long line — let the browser wrap.

Conventions:
- Keep "Best for" assertive ("Coding ceiling at 80 %", not "It performs well at coding").
- Put concrete numbers in "Expected usage" so the reader can act ("decode ~20 t/s", "MATH collapses to 14 %").
- If the model is demoted, say so explicitly ("Skip in normal use") — vague hedging is worse than a clear "don't use this".
- When you change benchmark scores, re-read these two cells and update them if the assertion no longer holds. They're not auto-derived.

The `.model-table-wrap` div around the table provides horizontal scroll on narrow viewports — keep it when adding rows.

## Sortable scoreboard

A single HTML table (`#scoreboardMain` in `benchmark-charts.html`, `#scoreboardQuality` in `quality-benchmarks-charts.html`) summarizing every model × every benchmark. The `<thead>` (with `<th data-sort="…">`) is hard-coded; the `<tbody>` is **generated** by `ChartsCommon.buildScoreboard(tableEl, models, results, columns)` from a column spec. Four helpers in `charts-common.js` (not duplicated between pages) do the work:

- **`buildScoreboard(tableEl, models, results, columns)`** — emits one `<tr data-model-id="…" class="tier-…">` per model (in `MODELS` order), with a swatch model cell followed by one cell per `columns` entry: `{kind:'str', get:m=>…}` for a text column (e.g. Tier), or `{kind:'num', query:{…}, fmt?:fn}` for a metric column. `fmt` defaults to `fmt1` (one decimal, but keeps extra precision like `89.75`); pass `C.fmtInt` for integer columns. Missing values render as `<td class="num dash">—</td>`.
- **`setupSortableTable(tableId, defaultSortCol?, defaultDir?)`** — click-to-sort. `data-sort="num"` pushes NaN/`—` to the bottom; `data-sort="str"` is `localeCompare`. First click on a numeric column sorts **descending**; subsequent clicks toggle; **double-click resets** to `MODELS` order.
- **`highlightBestPerColumn(tableId)`** — adds `best` (green, bold) to the max cell of every numeric column. It **clears prior highlights and ignores `.filtered-out` rows**, so it re-runs on every filter change.
- **`applyTableFilter(tableId, state, {highlight})`** — toggles `.filtered-out` on rows by `data-model-id`; wire it via `state.onChange(...)`. It also filters the editorial `#modelsTable` (rows without a `data-model-id` stay visible).

### Adding a new column

1. Add a `<th class="num" data-sort="num">…</th>` to the `<thead>`.
2. Add a matching entry to the `columns` array in the page's `buildScoreboard(...)` call (`{kind:'num', query:{metric:…, bench:…}}`). No per-row markup — the cell is generated from `RESULTS`.

### Changing the displayed metric

The throughput columns (`Gen t/s` / `Eff t/s`) in `benchmark-charts.html` show the **creative-writing** scenario — change the `scenario` in that column's `query`. If you swap scenarios, update the `<p class="sub">` blurb so the reader knows which one.

## How to add a new model run

1. **Run the benchmarks.** For accuracy: `python local-llm-bench-m4-32gb/scripts/bench2.py <bench> --model <model_id>`. For throughput: see `benchmarking/local-llm-bench/README.md`. For speed probe: `local-llm-bench-m4-32gb/scripts/speed_probe.py`.

2. **Add one `MODELS` entry** at the top of the page's inline `<script>`: pick an `id`, `tier`, `arch`/`quant` (omit for frontier/open), a `color`, and `label`/`chartLabel`. Set `provider` and `family` (drives the pills) using the collapsed taxonomy above — local models get a specific vendor + base family; frontier/open references get `Frontier` / `Open Frontier` and a base family. For local models add `hf` (the on-disk quant's HuggingFace repo, from `../docs/models/*.md`). On `benchmark-charts.html` add `diskGB` (for the scatter); add a `refNote` only for a **compact symbolic marker** (`*`/`‡`/`†`) and put any prose measurement caveat in `caveat` (it shows in the ranked-chart tooltip, not the label). If a speed probe with `probeN ≥ 10` exists, add the telemetry fields `peakRamGB` / `cpuPct` / `gpuPct` / `powerW` / `probeN` / `probeDate` (extraction one-liner under "Speed probe" above).

3. **Add `RESULTS` records** — one per measured value: `{ model:'<id>', metric:'accuracy'|'score', bench:'…', value:<n> }`, plus tool/throughput/etc. records on the benchmark page. Use `value:null` for a run you want to show explicitly as "not run"; omit the record otherwise. That single edit feeds the scoreboard, every chart, the scatter, and the radar.

4. **Add the editorial Models-table row** (`#modelsTable`) with a `data-model-id="<id>"` matching the new `MODELS` id and the swatch color — this is the one place prose still lives. Include the Provider, Family, and Peak RAM cells and wrap the model name in the `<a class="model-link" href="<hf>">…<span class="ext">↗ HF</span></a>` link. The Best/Expected-usage cells are not auto-derived (see "Models card" above).

5. **Add the Resource-usage row** (`#telemetryTable`) with a matching `data-model-id="<id>"`: fill Peak RAM / Avg CPU / Avg GPU / Peak power / Samples / Probe date if you have a qualifying probe, otherwise emit `<td class="num dash">—</td>` cells and a short reason (`n=… (below gate)` / `no probe`) so the row stays in the filterable roster.

6. **Grouped charts only:** the grouped `datasets` arrays (`chartAccuracy`, `chartGenTps`, prefill, …) are still listed explicitly per chart so each keeps its bespoke legend label — add a `dset(...)` line for the new model where you want it to appear. The ranked charts, scoreboard, scatter, and radar pick the model up automatically from `MODELS`/`RESULTS`.

7. **Re-read the Best for / Expected usage cells and chart subtitles.** New numbers may invalidate an old assertion (e.g. "highest GPQA on the rig").

## How to add a new benchmark

The pages already plot accuracy (HumanEval/MMLU/MATH/DROP/GPQA/LCB), Terminal-Bench, the two tool-calling suites, throughput, and (quality page) MMLU-Pro/GPQA/SWE-V/AIME/MMMU. To add another benchmark:

1. Run it on each local model and produce a `_summary.json` in the usual dir & shape.
2. Add `{ model:'<id>', metric:'accuracy'|'score', bench:'<NewBench>', value:<n>, note?:'…' }` records to `RESULTS` for every model that has a score.
3. Add a chart card with its own `<canvas id>`, then one `buildRankedChart('<canvasId>', { state, models: MODELS, results: RESULTS, query:{metric:'…', bench:'<NewBench>'}, axisLabel:'<NewBench>', labelFn })` call — it sorts, colors, and filters itself.
4. To add it as a scoreboard column, add a `<th data-sort="num">` and a `{kind:'num', query:{…}}` entry (see "Adding a new column"). To add it as a radar axis, add `{ label:'<NewBench>', query:{…} }` to the page's `buildRadarChart` `axes`.

## Caveats & gotchas

- The directory name `local-llm-bench-m4-32gb` is misleading — the actual hardware reported in every run's summary is the **128GB** Mac Studio. Don't rename without checking that scripts don't hard-code the path.
- Bench timestamps look like ISO but use `_` separators (`20260517_153426`). Sort lexically and they sort chronologically — that's already enough.
- The `model_config` block reports `size_gb` from the on-disk file. For MoE models this is total weights, not active — don't quote it as the "active footprint."
- The HumanEval scoring branch in `bench2.py` runs the generated code in a subprocess. If you swap in a new code benchmark, make sure the sandbox model matches what the benchmark expects (some need pytest, some need a clean cwd).
- macmon system metrics with `samples < 10` are noise. Always check `system_metrics.samples` before quoting RAM/power.
- The throughput benchmark in `benchmarking/local-llm-bench/` uses a different harness from the accuracy one. Don't try to merge them — they measure different things and write to different schemas.

## Quick refresh commands

```bash
# 1. List all run summaries with scores
ls -t local-llm-bench-m4-32gb/benchmarks/runs/*_summary.json | head -20 | xargs -I{} jq -r '[.benchmark // .suite, .model, .score_pct] | @tsv' {}

# 2. List throughput summary headlines
grep -A2 "Avg effective" benchmarking/local-llm-bench/results/*/*/m4-max-128gb-40gpu_lmstudio*.md

# 3. List speed probe runs
ls local-llm-bench-m4-32gb/results/speed_probe/*_results.json
```

## Source-of-truth files outside this directory

- `../docs/local-llm-reference.md` — model lineup, params, quant, disk size, context window, vision/tool support. The "Models benchmarked" table in `benchmark-charts.html` and the "Local models in this comparison" table in `quality-benchmarks-charts.html` both mirror this. The Best for / Expected usage columns are editorial and do **not** live in any source-of-truth file — they're maintained inline in the HTML.
- `../docs/machine-configuration.md` — chip, RAM, OS. The "System" card mirrors this.
- `../research/quality-benchmarks-2026-05.md` — citations and provenance for every published score plotted on `quality-benchmarks-charts.html`. When refreshing frontier numbers, update there first, then mirror into the inline `RESULTS` records.
- `../tools/local-llm-bench-m4-32gb/results/reference_scores.md` — older third-party comparison notes (Claude 3.x / GPT-4o era). Useful for context but the inline `RESULTS` records in the HTML are fresher.
- `../docs/testing-plan.md` — what's intended to run, what's pending.
