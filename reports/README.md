# benchmark-charts.html — maintenance guide

Self-contained dashboard for local LLM benchmarks on the Mac Studio (M4 Max / 128GB).
This file documents every data source the page uses and exactly how to refresh or extend it.

## What the page is

A single HTML file with embedded Chart.js charts. No build step. Open in a browser, or attach via the Launch preview panel.

- Page file: `benchmark-charts.html` (same directory as this README)
- Renderer: Chart.js 4.4.1 + chartjs-plugin-datalabels 2.2.0, both via CDN
- All chart data lives **inline as JS literals** at the bottom of the file — there is no fetch/network beyond the CDN scripts. Updating data = editing the literals.

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

The HTML has 5 logical sections, all inside `<main>`:

| # | Section | Data location | Source |
|---|---|---|---|
| 0 | System + Models cards | Hard-coded markup at top of `<main>` | Update from `machine-configuration.md` and `local-llm-reference.md` |
| 1 | Accuracy + frontier reference | `chartAccuracy` + `REF_MODELS` array + `chartRefMMLU/HumanEval/MATH/DROP/GPQA` | §1 (local) + §4 (frontier) |
| 2 | Tool calling | `chartToolScore`, `chartToolTps` | §1 (`toolcall_*_summary.json`) |
| 3 | Throughput by scenario | `chartGenTps`, `chartEffectiveTps`, `chartPrefill` | §3 (throughput benchmark md headlines) |
| 4 | Speed probe | `chartProbeTotal`, `chartProbeReason` | §2 (`speed_probe/*_results.json`) |
| 5 | Elapsed per benchmark | `chartElapsed` | §1 (`elapsed_min` from each summary) |

The toggle `Show data labels on bars` (header) flips `labelsOn` which the datalabels plugin reads at draw time. No need to touch when adding charts — registering via `registerChart(...)` auto-wires it.

## How to add a new model run

1. **Run the benchmarks.** For accuracy: `python local-llm-bench-m4-32gb/scripts/bench2.py <bench> --model <model_id>`. For throughput: see `benchmarking/local-llm-bench/README.md`. For speed probe: `local-llm-bench-m4-32gb/scripts/speed_probe.py`.

2. **Add to the System & Models card.** Extend the model table in the markup (preserve the `<span class="swatch">` color pattern so charts and the table agree).

3. **Pick a chart color** and add it to the `COLOR` map at the top of the `<script>` block.

4. **Add data to each chart's `datasets` array.** Use the same label string everywhere so legends stay consistent across charts. Use `null` for benchmarks not yet run — Chart.js renders gaps gracefully and the datalabels plugin's formatter is already `null`-safe.

5. **For the frontier-reference charts**, add an entry to `REF_MODELS` if the new model is a frontier/open-weight reference; the 5 per-benchmark charts rebuild themselves from that array (`buildRefChart`).

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

- `../docs/local-llm-reference.md` — model lineup, params, quant, disk size, context window, vision/tool support. The "Models benchmarked" table in the HTML mirrors this.
- `../docs/machine-configuration.md` — chip, RAM, OS. The "System" card mirrors this.
- `../tools/local-llm-bench-m4-32gb/results/reference_scores.md` — older third-party comparison notes (Claude 3.x / GPT-4o era). Useful for context but the inline `REF_MODELS` in the HTML is fresher.
- `../tools/local-llm-bench-m4-32gb/TESTING_PLAN.md` — what's intended to run, what's pending.
