# Testing plan — local LLMs on Mac Studio M4 Max 128 GB

The master plan for benchmarking and comparing the local models running on this
rig. Coordinates the two benchmarking tools, the qualitative coding artifacts,
and the dashboards.

## What this rig enables

| Constraint | This rig (Mac Studio M4 Max 128 GB) |
|---|---|
| Practical model size ceiling | ~80 GB weights (60–70 GB safe with KV cache) |
| Dense > 24B feasibility | Fine — active cooling, no thermal throttling |
| Need for REAP / aggressive prune | No — full-precision 27B dense fits easily |
| Loaded models at once | Up to two (JIT swap recommended past that) |
| Best inference path | MLX primarily, GGUF for engine A/B |

No fanless thermal throttling, no REAP-pruned weights, no quant-floor
contortions. The benchmarks here have to *find* the limits, not work around
them.

## What we measure (and with what)

| Signal | Why we care | Tool / entry point |
|---|---|---|
| **Knowledge accuracy** (MMLU, MATH, HumanEval, DROP, GPQA) | Baseline "is this model actually smart?" | [`tools/local-llm-bench-m4-32gb/scripts/bench2.py`](../tools/local-llm-bench-m4-32gb/scripts/bench2.py) |
| **Frontier-comparable coding** (LiveCodeBench v5/v6) | Contamination-resistant pass@1; comparable across providers | `bench2.py livecodebench --lcb-version release_v6` |
| **Tool calling** (jdhodges-40, Veerman-12) | The signal that actually predicts day-to-day usefulness in OpenCode / Cline / Aider | [`tools/local-llm-bench-m4-32gb/scripts/tool_call_bench.py`](../tools/local-llm-bench-m4-32gb/scripts/tool_call_bench.py) |
| **Effective throughput** (ops-agent, doc-summary, prefill-test, creative-writing) | Tokens/sec including prefill — what we actually wait for in agentic loops | [`tools/local-llm-bench/bench.py`](../tools/local-llm-bench/bench.py) |
| **Qualitative coding output** | Subjective code quality, stack choice, completeness — complements pass-rate | [`results/coding-task/`](../results/coding-task/) (one subdir per model) |
| **Dashboards** | At-a-glance comparison + frontier overlay | [`reports/benchmark-charts.html`](../reports/benchmark-charts.html), [`reports/quality-benchmarks-charts.html`](../reports/quality-benchmarks-charts.html) |

These signals don't substitute for each other. Knowledge rank does **not**
predict tool-calling rank (confirmed empirically — see Phase 1 outcomes
below), and neither predicts code quality on a real brief.

## Model inventory (LM Studio, verified 2026-05-18)

Source: `lms ls`, `lms ps`, `GET /v1/models` against
`http://192.168.68.124:1234/v1`. Sizes are on-disk weights.

### Daily-driver candidates (in scope)

| Model ID (use with API) | Format | Quant | Arch | Size | Vision | Tools |
|---|---|---|---|---|:---:|:---:|
| `qwen/qwen3-coder-next` | MLX safetensors | 6-bit (4-bit also on disk) | qwen3_next (80B/3B MoE) | 64.76 GB | — | ✓ |
| `qwen3.6-27b` | MLX safetensors | 6-bit | qwen3_5 (27B dense) | 22.80 GB | ✓ | ✓ |
| `qwen3.6-35b-a3b@6bit` | MLX safetensors | 6-bit | qwen3_5_moe (35B/3B) | 29.09 GB | ✓ | ✓ |
| `qwen3.6-35b-a3b@8bit` | MLX safetensors | 8-bit | qwen3_5_moe (35B/3B) | 37.75 GB | ✓ | ✓ |
| `gemma-4-26b-a4b-it-mlx@4bit` | MLX safetensors | 4-bit | gemma4 (26B/4B MoE) | 15.64 GB | ✓ | ✓ |
| `gemma-4-26b-a4b-it-mlx@6bit` | MLX safetensors | 6-bit | gemma4 (26B/4B MoE) | 21.81 GB | ✓ | ✓ |
| `gemma-4-31b-it-mlx` | MLX safetensors | 8-bit | gemma4 (31B dense) | 33.80 GB | ✓ | ✓ |
| `gemma-4-e4b-it-mlx` | MLX safetensors | 8-bit | gemma4 (4B) | 8.97 GB | ✓ | ✓ |
| `deepseek-v4-flash-dq` | MLX safetensors | 2-bit DQ | deepseek_v4 | 96.53 GB | — | — |

Embeddings (`text-embedding-nomic-embed-text-v1.5`) and community
abliterated re-quants (`qwen3.6-27b-paro`, `qwen3.6-27b-ud-mlx`,
`qwen3.6-27b-jang_4m-crack`, `gemma-4-31b-jang_4m-crack`) are on disk but
**out of scope** here — different workload class.

Keep [`docs/local-llm-reference.md`](local-llm-reference.md) in sync with
this table. Known stale entries there: `qwen/qwen3-coder-next` should be
6-bit / 64.76 GB (not 4-bit); `gemma-4-e4b` is MLX 8-bit (not GGUF Q4_K_M);
the "vision: to add" line is wrong — all MLX models above advertise
vision + tools per their metadata.

## Phases — model prioritization

Run a phase to completion before starting the next.

### Phase 1 — current daily drivers (must-test)

| # | Model | Role | Size | Why |
|---|---|---|---|---|
| 1 | `qwen/qwen3-coder-next` (6-bit) | Agentic coder, default | 64.76 GB | The daily driver. Need the numbers to defend the slot. |
| 2 | `qwen3.6-27b` (6-bit dense) | Reasoning specialist | 22.80 GB | Vendor claims "Opus 4.5 parity" on SWE-bench — verify on the same harness. |
| 3 | `qwen3.6-35b-a3b@6bit` | Fast generalist | 29.09 GB | Pulls weight between the other two, or doesn't — settle it. |

### Phase 2 — already-on-disk candidates (high value, zero download cost)

| # | Model | Why |
|---|---|---|
| 4 | `gemma-4-26b-a4b-it-mlx@4bit` | Could displace 35B-A3B in the "fast generalist" slot if it lives up to published numbers. Cheap to test (15.64 GB). |
| 5 | `gemma-4-26b-a4b-it-mlx@6bit` | Same weights as #4, heavier quant. Tests whether 4→6-bit closes the gap, or whether Gemma is quant-robust. |
| 6 | `gemma-4-31b-it-mlx` (8-bit dense) | Dense 31B at 8-bit (33.80 GB). Knowledge bench it against MoE-26B-A4B-at-4-bit. |
| 7 | `gemma-4-e4b-it-mlx` (8-bit) | Small Gemma (4B, 8.97 GB) — candidate for the FIM / quick-call slot. |
| 8 | `qwen/qwen3-coder-next@4bit` | Same weights as #1, lighter quant. Quantifies quality vs. memory tradeoff at 80B/3B. |
| 9 | `qwen3.6-35b-a3b@8bit` | Same weights as #3, heavier quant. Same-active-param A/B against `coder-next`. |

### Phase 3 — fit / feasibility experiments

| # | Model | Plan |
|---|---|---|
| 10 | `deepseek-v4-flash-dq` (2-bit DQ, 96.53 GB) | Load-test first: cap context at 32 768, confirm it loads and stays under 128 GB with margin. If yes, run **tool-calling only** — cheapest useful signal. Full knowledge suite only if it actually fits long-context workloads. |

### Phase 4 — watchlist (not on disk; test on arrival)

From [`docs/local-llm-reference.md`](local-llm-reference.md):

- `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` — FIM autocomplete (speed_probe only; full suite not appropriate for the workload).
- `mlx-community/Qwen2.5-VL-72B-Instruct-4bit` — only if current MLX models' built-in vision proves insufficient (probe first).
- `mlx-community/Kimi-K2.6-Thinking-*` distilled — watch for a fitting distillation size.
- `0xSero/Gemma-4-21B-REAP` (GGUF) — optional reproducibility check now that the un-pruned 26B-A4B is local.

## Current status (2026-05-19, Phase 1 complete)

Full write-up: [`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`](../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).
Raw data: [`tools/local-llm-bench-m4-32gb/benchmarks/runs/`](../tools/local-llm-bench-m4-32gb/benchmarks/runs/),
[`tools/local-llm-bench/results/`](../tools/local-llm-bench/results/).

### Accuracy + coding + tool-calling

| Phase | Model | HumanEval | LCB v6 | MMLU | MATH | DROP | GPQA (raw) | jdhodges (40) | veerman (12) |
|---|---|---|---|---|---|---|---|---|---|
| 1 #1 | `qwen/qwen3-coder-next` (6-bit) | **89 %** | — | **76 %** | **84 %** | **83 %** | **37 %** | **90 %** (18.6 t/s) | **83.3 %** (35.4 t/s) |
| 1 #2 | `qwen3.6-27b` (6-bit dense) | **93 %** | — | **88 %** | **88 %** | **90 %** | **70 %** ⚠ 15 trunc | **95 %** (14.5 t/s) | **83.3 %** (18.4 t/s) |
| 1 #3 | `qwen3.6-35b-a3b@6bit` | **87 %** | — | **83 %** ⚠ 2 trunc | **89 %** ⚠ 2 trunc | **89 %** | **65 %** ⚠ 23 trunc | **97.5 %** (72.4 t/s) | **75.0 %** (85.8 t/s) |
| 2 #4–9, 3 #10 | (not yet run) | — | — | — | — | — | — | — | — |

⚠ = truncated runs — model hit `max_tokens=32 768` before emitting the final
answer letter and was counted as wrong. **Raw GPQA scores under-count true
ability**: 27b corrected ceiling ≈ 78–85 %, 35b-a3b ≈ 75–83 %. See
[Truncation finding](#truncation-finding-gpqa--thinking-models) below.

### Effective throughput (scenario harness)

| Phase | Model | Speed probe (3-q) | creative-writing | doc-summary | ops-agent | prefill-test |
|---|---|---|---|---|---|---|
| 1 #1 | `qwen/qwen3-coder-next` (6-bit) | 1.5 s total | **67.8 eff t/s** / 70.2 gen | **45.6** / 69.9 | **55.8** / 67.9 | **20.6** / 68.0 |
| 1 #2 | `qwen3.6-27b` (6-bit dense) | 74.4 s total | **19.9 eff t/s** / 20.7 gen | **11.2** / 20.2 | **16.2** / 20.0 | **4.0** / 20.4 |
| 1 #3 | `qwen3.6-35b-a3b@6bit` | 15.8 s total (~90 t/s sustained) | **86.9 eff t/s** / 91.6 gen | **55.9** / 91.7 | **71.4** / 85.5 | **22.9** / 85.5 |
| 2/3 | (not yet run) | — | — | — | — | — |

### Qualitative coding artifacts

Two task-manager apps built end-to-end by Phase 1 models, kept for
side-by-side code-quality comparison. See [`results/coding-task/README.md`](../results/coding-task/README.md).

- `qwen3-coder-next-80b-a3b/` — Next.js 16 + Tailwind + SQLite
- `qwen3.6-27b-mlx-6bit/` — Static HTML/JS, localStorage

To add a third: same brief, run it, drop the source in a new
`results/coding-task/<model-id>/` and update its README.

### Phase 1 outcomes

- **`qwen3.6-27b` is the quality king.** Leads or ties every accuracy bench; knowledge avg 85.8 % is the highest in scope. Cost: dense → ~20 tok/s → 37.6 h full suite, dominated by GPQA.
- **`qwen3-coder-next` is the speed / agentic king.** Knowledge avg 73.8 % is the lowest, but it shipped the full suite in **1.9 h** (19× faster than 27b). Daily-driver slot confirmed: default for OpenCode / Cline / agentic loops.
- **`qwen3.6-35b-a3b` is the MoE-thinking middle.** Best jdhodges (97.5 %), best MATH (89 %), ~3× faster than 27b for ~3 pp less knowledge.
- **Knowledge rank ≠ tool-calling rank.** 35b-a3b leads jdhodges, trails Veerman; 27b ties both but is slow.

## Truncation finding (GPQA + thinking models)

`bench2.py`'s default `max_tokens=32 768` is **insufficient for GPQA on
thinking Qwen3.6 models**. GPQA requires a single-letter final answer *after*
the model's full reasoning chain — unlike MATH (where `\boxed{answer}` can be
emitted mid-chain) or HumanEval (where the code is the answer). When the model
spirals beyond 32k thinking tokens, no letter ever lands and the run records
`FAIL`.

Lower-rate truncations also appeared in MATH (1 on 27b, 2 on 35b-a3b) and
MMLU (2 on 35b-a3b). Format only matters meaningfully for GPQA.

**Affected question IDs** (verified against `bench2.py gpqa --only` syntax):

| Model | Trunc count | Question IDs |
|---|---|---|
| `qwen3.6-27b` | 15 / 100 | `2,15,24,28,36,40,43,44,46,51,55,71,80,87,92` |
| `qwen3.6-35b-a3b@6bit` | 23 / 100 | `2,4,12,15,21,24,28,32,43,46,52,53,55,60,69,70,71,80,84,87,89,92,96` |

**11 questions both models truncated on** — the hardest cluster: `2, 15, 24,
28, 43, 46, 55, 71, 80, 87, 92`. Likely the test set's hardest
physics/chemistry/biology MCQs; worth tagging for any future GPQA work on
thinking models.

**Implication for ranks**: 27b's recorded 70 % is the floor — corrected
ceiling ≈ 78–85 %. 35b-a3b similar: raw 65 %, ceiling ≈ 75–83 %.

## Next steps — prioritized

Ranked by **(value × confidence) / cost**.

### Step A — rerun truncated GPQA questions with `--max-tokens 65536`

```bash
# 27b — 15 questions
cd tools/local-llm-bench-m4-32gb
python3 scripts/bench2.py gpqa --examples 100 --model qwen3.6-27b \
  --only 2,15,24,28,36,40,43,44,46,51,55,71,80,87,92 --max-tokens 65536

# 35b-a3b@6bit — 23 questions
python3 scripts/bench2.py gpqa --examples 100 --model "qwen3.6-35b-a3b@6bit" \
  --only 2,4,12,15,21,24,28,32,43,46,52,53,55,60,69,70,71,80,84,87,89,92,96 \
  --max-tokens 65536
```

- **Cost:** ~7–10 h on 27b dense, ~3–5 h on 35b-a3b MoE (worst-case if every question spirals up to 65k tokens).
- **Expected outcome:** corrected GPQA scores. Either confirms 27b ≈ 80 % / 35b-a3b ≈ 78 %, or reveals questions truly unsolvable at this scale.
- **Risk:** 65 536 is also the loaded context length. Residual truncations would form the floor of "unanswerable at this scale" — publish them explicitly.
- **Harness check first:** confirm `bench2.py` merges `--only` re-runs into the existing summary rather than writing a separate run. If it writes a fresh summary, the chart script + `M4_MAX_128GB_NOTES.md` need to point at the merged result.

### Step B — patch `max_tokens` default for GPQA before Phase 2

For any future thinking-model GPQA run (Phase 2 Gemmas, anything in Phase 4),
use `--max-tokens 65536` by default. Either patch the default in
`scripts/bench2.py`, or pass it explicitly in every run command. **Don't**
let Phase 2 inherit the silent 32k cap.

### Step C — add LiveCodeBench to the Phase 1 daily drivers

```bash
cd tools/local-llm-bench-m4-32gb
for m in qwen/qwen3-coder-next qwen3.6-27b qwen3.6-35b-a3b@6bit; do
  python3 scripts/bench2.py livecodebench --examples 50 --lcb-version release_v6 --model "$m"
done
```

- **Cost:** ~30–90 min per model. Total ~5 h.
- **Value:** contamination-resistant coding signal comparable across the rig and every current frontier provider. HumanEval is largely saturated.

### Step D — start Phase 2 with Gemma 4 26B-A4B

Already on disk in both 4-bit (15.64 GB) and 6-bit (21.81 GB). Upstream's
knowledge-quality winner.

- **Cost:** ~12–20 h per quant per full suite (thinking model — apply the Step B GPQA rule).
- **Decision point:** does it beat or tie 27b on knowledge at a fraction of the wall-clock? If yes, the 6-bit becomes the new "knowledge generalist" slot in `local-llm-reference.md`.

### Step E — pre-Phase-2 throughput sweep (decoupled from knowledge)

Run the scenario harness for every Phase 2/3 candidate before the multi-day
knowledge runs start. See [Effective-throughput run plan](#effective-throughput-run-plan)
below for the table + commands. ~15–25 min per model, **~2–3 h total** for
all 7 to-do entries. Fills the speed table early so the operator has a
"is X usable day-to-day?" answer without waiting for accuracy data.

### Step F — defer

- `deepseek-v4-flash-dq` fit-test (Phase 3): only worth it if a Phase 2 model demonstrates a quality ceiling. Otherwise it's a 96 GB resident that locks out everything else.
- Engine A/B (LM Studio MLX vs llama.cpp GGUF): needs a GGUF pulled first. Pair it with whichever model has both formats available when the moment is right (likely Gemma 4 26B-A4B).
- Phase 4 watchlist: nothing to do until something lands.

### Recommended next session

- **Interactive day:** Step E (throughput sweep, ~2–3 h) → Step A 35b-a3b leg only (~3–5 h). Confirms 35b-a3b's true GPQA before committing to the longer 27b rerun; fills the speed table in the same day. Save Step A 27b for an unattended overnight block.
- **Headless overnight:** Step A both legs back-to-back (~10–15 h). Single decision point at end-of-day; leaves the morning clean for Step C (LCB) or starting Phase 2.

## Per-model run order

For each model in scope, in this order. Cheap signals first; expensive
benchmarks only if the cheap signal warrants them.

1. **Speed probe** (~10 min) — confirms the model loads and responds, gives a rough tok/s. If broken, stop and fix before committing hours.
2. **Tool calling** (~15–30 min) — jdhodges + Veerman via `tool_call_bench.py`. Fastest signal for day-to-day usability in OpenCode/Cline/Aider.
3. **HumanEval** (~30–60 min) — quick sanity check on code generation; backward-comparable to historical numbers.
4. **LiveCodeBench** (~30–90 min at n=50) — primary coding signal going forward. Use `release_v6` (cutoff ~Apr 2025) or `release_v5` if v6 is suspected to overlap a model's pre-training cutoff.
5. **MMLU** (~30–60 min) — broad knowledge, fast scoring (single letter).
6. **MATH** (~2–8 h) — slow for thinking models.
7. **DROP** (~1–2 h) — reading comprehension, generous substring scoring.
8. **GPQA** (~2–10 h) — hardest, slowest. Skip on first pass if a model has clearly already qualified or disqualified itself.

## Cross-model order

Run **model-major, not benchmark-major**: complete the full suite on
qwen3-coder-next before starting qwen3.6-27b. An interrupted run then
leaves at least one model fully characterized, instead of three models
partially characterized.

## Engine A/B (LM Studio GGUF vs MLX)

Re-test the upstream rule of thumb (*"llama.cpp short, MLX long"*) for any
model that has both formats on disk. For each format, run tool-calling
(short outputs) and MATH (long outputs) at n=100; compare wall-clock and
quality. Record findings in
[`tools/local-llm-bench-m4-32gb/results/engine_comparison.md`](../tools/local-llm-bench-m4-32gb/results/engine_comparison.md)
under a "M4 Max 128 GB findings" section.

Same-engine quant A/Bs (already covered above) live in Phase 2:
`coder-next @4 vs @6`, `Gemma-26B-A4B @4 vs @6`, `Qwen3.6-35B-A3B @6 vs @8`.
All other current models are MLX-only on disk — true cross-engine A/B would
require pulling a GGUF first.

## Effective-throughput run plan

Separate measurement track from the per-model speed_probe (which only
confirms "loads and responds"). The scenario harness at
[`tools/local-llm-bench/`](../tools/local-llm-bench/) measures **effective
throughput** — output tokens divided by total wall-clock including prefill —
across four realistic workloads (ops-agent, doc-summary, prefill-test,
creative-writing). This is what we actually wait for in agentic loops,
and prefill dominates as context grows.

Where this run overlaps a model's "speed probe" step, prefer this bench —
if it completes the 4 scenarios cleanly, the probe step is satisfied by
definition.

### Already characterized

| Plan ref | Model | Result folder | Backend label |
|---|---|---|---|
| Phase 1 #1 | `qwen/qwen3-coder-next` (6-bit) | [`tools/local-llm-bench/results/qwen3-coder-next-6bit/`](../tools/local-llm-bench/results/qwen3-coder-next-6bit/) | `lmstudio` |
| Phase 1 #2 | `qwen3.6-27b` (6-bit dense) | [`tools/local-llm-bench/results/qwen3.6-27b-dense-mlx-6bit/`](../tools/local-llm-bench/results/qwen3.6-27b-dense-mlx-6bit/) | `lmstudio` |
| Phase 1 #3 | `qwen3.6-35b-a3b@6bit` | [`tools/local-llm-bench/results/qwen3.6-35b-a3b/`](../tools/local-llm-bench/results/qwen3.6-35b-a3b/) | `lmstudio-mlx` |

### Still to run

| Plan ref | Model ID (API) | Suggested `--model-label` | Notes |
|---|---|---|---|
| Phase 2 #4 | `gemma-4-26b-a4b-it-mlx@4bit` | `gemma-4-26b-a4b-mlx-4bit` | First Gemma 4 speed numbers on this rig. |
| Phase 2 #5 | `gemma-4-26b-a4b-it-mlx@6bit` | `gemma-4-26b-a4b-mlx-6bit` | Pair with #4 for a same-model quant→throughput plot. |
| Phase 2 #6 | `gemma-4-31b-it-mlx` | `gemma-4-31b-dense-mlx-8bit` | Dense 31B at 8-bit; speed cost vs. 26B-A4B is the question. |
| Phase 2 #7 | `gemma-4-e4b-it-mlx` | `gemma-4-e4b-mlx-8bit` | Small model; should top the throughput table. |
| Phase 2 #8 | `qwen/qwen3-coder-next@4bit` | `qwen3-coder-next-4bit` | Pair with the already-done 6-bit. |
| Phase 2 #9 | `qwen3.6-35b-a3b@8bit` | `qwen3.6-35b-a3b-8bit` | Pair with the already-done 6-bit. |
| Phase 3 #10 | `deepseek-v4-flash-dq` | `deepseek-v4-flash-dq-2bit` | **Only if it loads cleanly under the 32 768 context cap.** Skip the 8K prefill-test turn if it OOMs; record what works. |

### Per-run command

```bash
cd tools/local-llm-bench
python3 bench.py \
  --backend lmstudio \
  --base-url http://192.168.68.124:1234/v1 \
  --model <model-id-from-table> \
  --model-label <label-from-table>
```

Add `--no-think` only for explicit thinking-mode models (Qwen3.5-family per
upstream README); Qwen3.6 / Gemma 4 / DeepSeek-V4 do not need it by default
— verify per model before assuming. Results auto-save to
`results/<model-label>/<scenario>/m4-max-128gb-40gpu_lmstudio.json`.

## Operational rules

- **Thermal:** treat sustained > 85 °C as the watch line, > 95 °C as abort. The Mac Studio almost never hits the abort line under normal benches.
- **Memory:** keep `weights + KV < 80 GB`. With LM Studio JIT, only one of {coder-next, 27B, 35B-A3B, Gemma-26B-A4B} should be resident at benchmark time. Two simultaneous large MLX models has caused queue stalls before.
- **DeepSeek-V4-Flash-DQ exception:** at 96.53 GB, it must be the **only** loaded model. Cap context at 32 768; watch wired memory with `sudo memory_pressure`.
- **Context length on load:** set explicitly. 65 536 for tool-calling and knowledge benches (matches the agentic-loop daily-driver setting). Don't max to 256k+ — KV reservation was the root cause of past stalls.
- **Pre-flight:** run the harness's environment check (`python3 scripts/lms.py check` in the M4-32GB tool) before each session.
- **Verify model IDs:** use the exact strings from `GET /v1/models`, not the `mlx-community/...` paths in older configs. Mismatched IDs return 404.

## Deliverables

After each phase, update:

1. `tools/local-llm-bench-m4-32gb/benchmarks/runs/` — per-question JSONL + per-run summary (harness auto-writes).
2. `tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md` — the live commentary on this rig's findings; append phase sections.
3. `tools/local-llm-bench-m4-32gb/results/charts/` — regenerate via `scripts/m4max_charts.py`.
4. `tools/local-llm-bench/results/<model-label>/` — effective-tok/s scenario JSONs (auto-written).
5. `reports/benchmark-charts.html` + `reports/quality-benchmarks-charts.html` — refresh per `reports/README.md`.
6. `docs/local-llm-reference.md` — slot/role updates if a model displaces another in the daily-driver lineup.
7. This plan — bump model IDs / Phase tables / Current status as facts change.

## What's explicitly NOT in scope

- **Long-context needle-in-haystack** — defer until we have a workload that demands it.
- **TurboQuant KV-cache quantization** — only matters when memory-constrained; we aren't (except possibly DeepSeek-V4-Flash-DQ).
- **Cross-machine comparisons** against the M4 Air or external GPUs — not the question being asked here.
- **New benchmarks** — reuse the existing harnesses. If a bug is found, fix it and credit in the relevant tool's audit log.
- **Embeddings model** (`nomic-embed-text-v1.5`) — different workload class.
- **Abliterated / uncensored community re-quants** on disk (`qwen3.6-27b-paro`, `qwen3.6-27b-ud-mlx`, `qwen3.6-27b-jang_4m-crack`, `gemma-4-31b-jang_4m-crack`) — different workload class; pollute the "daily-driver value" ranking.

## Estimated wall-clock

Per model, full suite (tool-calling + 5 knowledge benches at n=100 +
LiveCodeBench at n=50): roughly **9–32 h** depending on whether the model
thinks.

**Phase 1 actuals (2026-05-17 → 2026-05-19):**

- `qwen/qwen3-coder-next` — 1.9 h (no thinking, no truncations)
- `qwen3.6-27b` — 37.6 h (dense thinking; 22.2 h was GPQA alone, 7.2 h of that on the 15 truncated questions consuming the full 32k cap)
- `qwen3.6-35b-a3b@6bit` — 14.7 h (MoE thinking; 6.5 h GPQA, ~4.4 h on truncations)
- **Total Phase 1: ~54 h across 3 models** — outside the original 8–30 h/model estimate on the high end, driven by GPQA truncation behavior.

**Phase 2 forward estimate** — three full-suite candidates (Gemma 4 26B-A4B
@4bit, Gemma 4 31B dense, Gemma 4 E4B) ≈ **2–4 days**, plus three quant-A/B
variants (Gemma 4 26B-A4B @6bit, coder-next @4bit, Qwen3.6-35B-A3B @8bit)
that only need tool-calling + 1–2 knowledge benches to detect drift ≈
another **1–2 days**. **Apply the `max_tokens=65 536` rule for GPQA on all
thinking models** — should shave hours per run by avoiding the
spiral-to-32k-then-fail loop.

Plan around overnight blocks.
