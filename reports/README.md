# reports/ — maintenance guide

Two self-contained dashboards for local-LLM benchmarks on the Mac Studio (M4 Max / 128GB):

| File | What it shows | Primary scope |
|---|---|---|
| `benchmark-charts.html` | On-rig measurements (accuracy n=100, LCB n=50, tool calling, throughput, speed probe, prefill, elapsed) | The local runs themselves — what was actually measured on this rig |
| `quality-benchmarks-charts.html` | Local-vs-frontier comparison using **published** scores (MMLU-Pro, GPQA, SWE-V, AIME, LCB v6, T-Bench, MMMU) | How the local models rank against frontier / open-weight references |

Both files share the same conventions: inline data, Chart.js via CDN, the same wide Models card layout, and the same sortable scoreboard helper (`setupSortableTable` + `highlightBestPerColumn`). Edits to one usually want a parallel edit to the other.

## What the pages are

Single HTML files with embedded Chart.js charts. No build step. Open in a browser, or attach via the Launch preview panel.

- Page files: `benchmark-charts.html`, `quality-benchmarks-charts.html` (same directory as this README)
- Renderer: Chart.js 4.4.1 + chartjs-plugin-datalabels 2.2.0, both via CDN
- All chart data lives **inline as JS literals** at the bottom of each file — there is no fetch/network beyond the CDN scripts. Updating data = editing the literals.
- The Models table and the Benchmark scoreboard are **HTML tables** at the top of `<main>`, not Chart.js charts — edit the `<tr>` rows directly.

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
- Raw run dirs (per-task transcripts, logs, lockfiles): `.bench-logs/tbench-runs/<run-name>/` with a `result.json` at the root.
- Driver scripts that launched each run: `.bench-logs/run-tbench-<run-name>.sh` — use these as templates when adding new models.

**Harness:** Harbor + LiteLLM proxy → LM Studio, terminus-2 agent in Docker (linux/amd64), `--concurrency 1`, `--agent-timeout-multiplier 0.5` (caps the 14 long-budget tasks; full-budget would land ≤5 pp higher). N=89 vanilla T-Bench 2.0 task set.

**Pass-rate extraction (from `result.json`):**

```bash
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); ev=next(iter(d['stats']['evals'].values())); print(f\"{ev['metrics'][0]['mean']*100:.1f}% ({len(ev['reward_stats']['reward'].get('1.0',[]))}/{ev['n_trials']})\")" .bench-logs/tbench-runs/<run-name>/result.json
```

…or just read the `_summary.json` if it exists (the runner writes one once the run finishes).

**Phase A snapshot as of 2026-05-26** (live in `benchmark-charts.html` chartTBench + scoreboard, and `quality-benchmarks-charts.html` chartTBench + scoreboardQuality):

| Run dir | Model | Score | Wall-clock |
|---|---|---|---|
| `coder-next` | qwen/qwen3-coder-next | 32.6 % (29/89) | 1009 min ≈ 16.8 h |
| `gemma-26b-a4b-6bit` | gemma-4-26b-a4b-it-mlx@6bit | 21.3 % (19/89) | 864 min ≈ 14.4 h |
| `gemma-e4b` | gemma-4-e4b-it-mlx | 4.5 % (4/89) | 383 min ≈ 6.4 h |
| `gemma-26b-a4b-4bit` | gemma-4-26b-a4b-it-mlx@4bit | **in progress** (2/89, both errored at snapshot) | — |

**Phase B pending** (driver scripts exist but no result dirs yet): `run-tbench-qwen-27b.sh`, `run-tbench-qwen-35b-a3b-6bit.sh`, `run-tbench-gemma-31b.sh`. Each takes 6–17 h on this rig — schedule overnight.

**To refresh after a new run completes:**

1. Confirm the summary JSON exists at `tools/local-llm-bench-m4-32gb/benchmarks/runs/tbench_<model>_<timestamp>_summary.json`. If only the raw `result.json` is available, the score is `stats.evals.<key>.metrics[0].mean`.
2. Update the scoreboard cells (`#scoreboardMain` row's T-Bench cell in `benchmark-charts.html`; `#scoreboardQuality` row's T-Bench cell in `quality-benchmarks-charts.html`) — drop the `dash` class and set the value.
3. Update the chartTBench `data: [null]` to `data: [<value>]` in `benchmark-charts.html`, and rewrite the dataset label suffix to match (e.g. `— 35/89`).
4. Add a row to `buildBenchChart('chartTBench', …)` in `quality-benchmarks-charts.html` if it's a model not already listed, or update the `value:` if it is.
5. Refresh the subtitle of both T-Bench cards and the scoreboard hints with the new headline numbers.

### 2. Speed probe (3-prompt cold latency, system metrics)

**Source dir:** `local-llm-bench-m4-32gb/results/speed_probe/`

Pattern: `<model>_<timestamp>_results.json` + `<model>_<timestamp>_macmon.jsonl` (macmon power/temp samples).

The `results.json` has the three prompts (`trivial`, `mmlu_atmosphere`, `code_second_largest`) with per-prompt `elapsed`, `completion_tokens`, `reasoning_tokens` — that last field is what drives the "reasoning tokens emitted" chart.

System metrics block: `peak_ram_gb`, `peak_swap_gb`, `avg_gpu_pct`, `peak_power_w`, `samples`. **Trust nothing under ~10 samples** — that's a known quality issue for short runs (the coder-next probe only has 2 samples and the RAM/power numbers are statistically meaningless).

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

The reference numbers in the "Local vs frontier" section came from a **research subagent web-search pass on 2026-05-17**. They are inlined into `REF_MODELS` in the HTML.

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

`benchmark-charts.html` has these logical sections inside `<main>`, top-to-bottom:

| # | Section | Data location | Source |
|---|---|---|---|
| 0a | System card | Hard-coded markup at top of `<main>` | Update from `../docs/machine-configuration.md` |
| 0b | **Models benchmarked** (wide card) | Hard-coded `<table>` with Best for / Expected usage columns | Update from `../docs/local-llm-reference.md` + this README's "Models card" section below |
| 0c | **Benchmark scoreboard** (wide card, sortable) | Hard-coded `<table id="scoreboardMain">` | See "Sortable scoreboard" section below |
| 1 | Accuracy + frontier reference | `chartAccuracy` + `REF_MODELS` array + `chartRefMMLU/HumanEval/MATH/DROP/GPQA/LCB` | §1 (local) + §4 (frontier) |
| 2 | Tool calling | `chartToolScore`, `chartToolTps` | §1 (`toolcall_*_summary.json`) |
| 3 | Throughput by scenario | `chartGenTps`, `chartEffectiveTps`, `chartPrefill` | §3 (throughput benchmark md headlines) |
| 4 | Speed probe | `chartProbeTotal`, `chartProbeReason` | §2 (`speed_probe/*_results.json`) |
| 5 | Elapsed per benchmark | `chartElapsed` | §1 (`elapsed_min` from each summary) |

`quality-benchmarks-charts.html` follows the same shape but is comparison-oriented: a Scope card, a wide Models card (Best for / Expected usage), a Legend card, a wide Benchmark scoreboard (`#scoreboardQuality`, mixes local + frontier + open rows), then Chart.js charts for MMLU-Pro / GPQA / AIME / SWE-V / LCB / T-Bench / MMMU, followed by the quant-caveats panel and verdict table.

The toggle `Show data labels on bars` (header) flips `labelsOn` which the datalabels plugin reads at draw time. No need to touch when adding charts — registering via `registerChart(...)` auto-wires it. The scoreboard tables are HTML, not Chart.js, so the toggle does not affect them.

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

A single HTML table (`#scoreboardMain` in `benchmark-charts.html`, `#scoreboardQuality` in `quality-benchmarks-charts.html`) that summarizes every model × every benchmark in one matrix. Two small JS helpers do all the work:

- **`setupSortableTable(tableId, defaultSortCol?, defaultDir?)`** — wires every `<th data-sort="...">` for click-to-sort. `data-sort="num"` is a numeric sort that pushes NaN/`—` rows to the bottom; `data-sort="str"` is a `localeCompare`. First click on a numeric column sorts **descending** (highest first); subsequent clicks toggle. **Double-click any header to reset to original document order.** Pass `defaultSortCol` (0-based index) if you want a column pre-sorted on load.
- **`highlightBestPerColumn(tableId)`** — adds class `best` (green, bold) to the cell with the maximum value in every numeric column. Run it once after the DOM is built; it doesn't need to re-run after sorts.

Both helpers are duplicated verbatim in the two files (so each file stays self-contained). If you fix a bug in one, mirror it to the other.

### Adding a new column

1. Add a `<th class="num" data-sort="num">…</th>` to the `<thead>`.
2. For every existing `<tr>` in `<tbody>`, add a corresponding `<td class="num">…</td>`. Use `<td class="num dash">—</td>` for missing data — `parseFloat('—')` is NaN, which the sort treats as "bottom".
3. Save. No JS change needed; the helpers re-scan the table on every sort and on highlight.

### Adding a new row

1. Insert a `<tr>` (with the swatch `<span>` matching the model's color elsewhere on the page).
2. For `quality-benchmarks-charts.html`, also set the tier class on the row: `tier-local`, `tier-frontier`, or `tier-open` — controls the model-cell color tint.
3. If the new row beats the current max in any column, `highlightBestPerColumn` will reassign the green pill automatically on next page load.

### Changing the displayed metric

The throughput columns (`Gen t/s` / `Eff t/s`) in `benchmark-charts.html` show the **creative-writing** scenario by default — pick a different scenario by editing the cells directly. If you swap scenarios, update the `<p class="sub">` blurb above the table so the reader knows which one.

## How to add a new model run

1. **Run the benchmarks.** For accuracy: `python local-llm-bench-m4-32gb/scripts/bench2.py <bench> --model <model_id>`. For throughput: see `benchmarking/local-llm-bench/README.md`. For speed probe: `local-llm-bench-m4-32gb/scripts/speed_probe.py`.

2. **Add to the Models card.** Extend the wide model table in the markup. Required cells per row, in order:
   `swatch | code-tag model id | author | arch | total params | active | quant | disk | context | vision | tools | Best for (td.bestfor) | Expected usage (td.usage)`.
   Preserve the swatch color so charts and the table agree.

3. **Add to the Benchmark scoreboard.** Insert a `<tr>` into `#scoreboardMain` (and `#scoreboardQuality` if relevant). One `<td class="num">N</td>` per metric column, `<td class="num dash">—</td>` for unmeasured.

4. **Pick a chart color** and add it to the `COLOR` map at the top of the `<script>` block.

5. **Add data to each chart's `datasets` array.** Use the same label string everywhere so legends stay consistent across charts. Use `null` for benchmarks not yet run — Chart.js renders gaps gracefully and the datalabels plugin's formatter is already `null`-safe.

6. **For the frontier-reference charts**, add an entry to `REF_MODELS` if the new model is a frontier/open-weight reference; the per-benchmark charts rebuild themselves from that array (`buildRefChart`).

7. **Re-read the Best for / Expected usage cells.** New numbers may invalidate an old assertion (e.g. "highest GPQA on the rig"). Update prose to match the new data.

## How to add a new benchmark column

Today the page handles MMLU, HumanEval, MATH, DROP, GPQA, and the two tool-calling suites. **LiveCodeBench is wired in the harness but not yet plotted** — see "Next steps" below for the patch. To add a new benchmark (the LCB recipe applies generally):

1. Run it on each local model and produce a `_summary.json` in the same dir & shape (the existing harness already writes that shape).
2. Add a new chart card to the markup with its own canvas id.
3. Add a new `registerChart(new Chart(...))` block with the same color convention.
4. In `REF_MODELS`, extend each model entry with the new metric key (e.g. `LiveCodeBench: 65.9`), and call `buildRefChart('chartRefLCB', 'LiveCodeBench', 'LiveCodeBench')`.

### Next steps for LiveCodeBench specifically

1. Run on each local model: `python3 scripts/bench2.py livecodebench --examples 50 --lcb-version release_v6 --model <model-id>` (n=50 is the LCB convention; full v6 has ~880 problems so n=100 is also fine but ~2× slower).
2. Pull headline scores from `local-llm-bench-m4-32gb/benchmarks/runs/livecodebench_*_summary.json`.
3. Frontier references for LCB (refresh via the research-agent procedure above):
   - DeepSeek-V3: 65.9 (technical report)
   - DeepSeek-R1: 65.9 (HF model card)
   - Qwen3-Coder-480B: 70.7 (HF card)
   - Claude Sonnet 4.5: ~70 (system card, LCB-Pro variant)
   - GPT-5: ~80 (vellum aggregator — verify against system card)
   - Verify all against first-party sources before publishing; LCB scores in particular vary by harness configuration (cumulative vs window, output extraction).
4. Add `LiveCodeBench: <score>` to each entry in `REF_MODELS` and a `chartRefLCB` canvas in the markup; the existing `buildRefChart` helper will sort and color it automatically.

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
- `../research/quality-benchmarks-2026-05.md` — citations and provenance for every published score plotted on `quality-benchmarks-charts.html`. When refreshing frontier numbers, update there first, then mirror into the inlined chart data and the scoreboard rows.
- `../tools/local-llm-bench-m4-32gb/results/reference_scores.md` — older third-party comparison notes (Claude 3.x / GPT-4o era). Useful for context but the inline `REF_MODELS` in the HTML is fresher.
- `../docs/testing-plan.md` — what's intended to run, what's pending.
