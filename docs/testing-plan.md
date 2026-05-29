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
| **Terminal-Bench 2.0** (agentic shell) | Multi-turn agent loop in a Linux container; only end-to-end shell-agent signal on this rig | Harbor 0.8 → LiteLLM → LM Studio (`.bench-logs/run-tbench-*.sh` drivers; adapter [`tools/local-llm-bench-m4-32gb/scripts/harbor_to_summary.py`](../tools/local-llm-bench-m4-32gb/scripts/harbor_to_summary.py)) |
| **Qualitative coding output** | Subjective code quality, stack choice, completeness — complements pass-rate | [`results/coding-task/`](../results/coding-task/) (one subdir per model) |
| **Dashboards** | At-a-glance comparison + frontier overlay | [`reports/benchmark-charts.html`](../reports/benchmark-charts.html), [`reports/quality-benchmarks-charts.html`](../reports/quality-benchmarks-charts.html) |

These signals don't substitute for each other. Knowledge rank does **not**
predict tool-calling rank (confirmed empirically — see Phase 1 outcomes
below), and neither predicts code quality on a real brief.

## Model inventory (LM Studio, verified 2026-05-18)

Source: `lms ls`, `lms ps`, `GET /v1/models` against
`http://<lm-studio-host>:1234/v1`. Sizes are on-disk weights.

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
this table. The reference doc was reconciled with this inventory on
2026-05-29; flag any new drift here when it appears.

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

## Current status (2026-05-29, Phase 1 + Phase 2 + Steps B/C/G complete)

Full write-up: [`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`](../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).
Phase 2 plan: [`docs/benchmark-plans/2026-05-20-gemma-4-phase-2.md`](benchmark-plans/2026-05-20-gemma-4-phase-2.md).
Raw data: [`tools/local-llm-bench-m4-32gb/benchmarks/runs/`](../tools/local-llm-bench-m4-32gb/benchmarks/runs/),
[`tools/local-llm-bench/results/`](../tools/local-llm-bench/results/).

### Accuracy + coding + tool-calling

| Phase | Model | HumanEval | LCB v6 | MMLU | MATH | DROP | GPQA (raw) | jdhodges (40) | veerman (12) | T-Bench 2.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 #1 | `qwen/qwen3-coder-next` (6-bit) | **89 %** | **56 %** (clean) | **76 %** | **84 %** | **83 %** | **37 %** | **90 %** (18.6 t/s) | **83.3 %** (35.4 t/s) | **32.6 %** ⌛0.5x cap |
| 1 #2 | `qwen3.6-27b` (6-bit dense) | **93 %** | **62 %** † 1 trunc | **88 %** | **88 %** | **90 %** | **70 %** ⚠ 15 trunc | **95 %** (14.5 t/s) | **83.3 %** (18.4 t/s) | **31.5 %** ⌛0.5x cap |
| 1 #3 | `qwen3.6-35b-a3b@6bit` | **87 %** | 54 % ⚠ 6 trunc | **83 %** ⚠ 2 trunc | **89 %** ⚠ 2 trunc | **89 %** | **65 %** ⚠ 23 trunc | **97.5 %** (72.4 t/s) | **75.0 %** (85.8 t/s) | **28.1 %** ⌛0.5x cap |
| 2 #4 | `gemma-4-26b-a4b@4bit` | **98 %** | 66 % † 8 trunc | 78 % | 80 % ⚠ 1 trunc | 79 % | **47 %** † 1 trunc | **97.5 %** (73.4 t/s) | **83.3 %** (82.1 t/s) | **20.2 %** ⌛0.5x cap |
| 2 #5 | `gemma-4-26b-a4b@6bit` | **97 %** | **80 %** † 1 trunc | 78 % | **83 %** | 79 % | **53 %** † 2 trunc | **97.5 %** (57.8 t/s) | **83.3 %** (66.6 t/s) | **21.3 %** ⌛0.5x cap |
| 2 #6 | `gemma-4-31b-it-mlx` (8-bit dense) | 95 % | 76 % | 77 % | 79 % | **85 %** | 48 % | **97.5 %** (11.4 t/s) | **83.3 %** (12.3 t/s) | **22.5 %** ⌛0.5x cap |
| 2 #7 | `gemma-4-e4b-it-mlx` (4B/8-bit) | 91 % | 68 % | 65 % | 14 % ⚠ | 65 % | 34 % | **87.5 %** (42.5 t/s) | **66.7 %** (60.3 t/s) | **4.5 %** ⌛0.5x cap |
| 2 #8, 2 #9, 3 #10 | (not yet run) | — | — | — | — | — | — | — | — | — |

⌛ = T-Bench run with `--agent-timeout-multiplier 0.5` to bound the 14
outlier tasks declaring >60-min agent budgets; published scores are a
defensible floor (full-budget would lift ≤5 pp). Plan:
[`docs/benchmark-plans/2026-05-24-terminal-bench-phase-a-plus-b.md`](benchmark-plans/2026-05-24-terminal-bench-phase-a-plus-b.md).
All 7 local rows landed 2026-05-29 (Step G done) — see the chartTBench
panel in [`reports/quality-benchmarks-charts.html`](../reports/quality-benchmarks-charts.html).

⚠ = truncation observed at the harness cap. For GPQA on thinking Qwen models
the cap was 32 768; raw scores under-count true ability (27b ceiling ≈ 78–85 %,
35b-a3b ≈ 75–83 %). For LCB on Gemma the cap was also 32 768; Gemma `@6bit`
LCB ceiling ≈ 86 %.
† = bench was run at the raised cap (`--max-tokens 65536`); remaining
truncations form the "unanswerable at this scale" floor:
- **LCB on Gemma 4 26B-A4B** (Step B, 2026-05-24) — original `⚠` truncations
  at 32 k were reran at 65 k. `@4bit` recovered Q2 only (8 of 9 still
  truncated at 65k → real model limits, not cap artifacts); score
  64 % → **66 %**. `@6bit` recovered Q28 (FAIL→OK), Q8 and Q15 now answer
  cleanly under 10 k tokens but still wrong, Q19 still truncates at 65k;
  score 78 % → **80 %**. Q19 (atcoder/hard abc354_d) is the canonical
  "hard for 26B-A4B at any cap" case across the Gemma family.
- **GPQA on Gemma** — `@4bit` Q1, `@6bit` Q60/Q78. See [Truncation finding](#truncation-finding-gpqa--thinking-models)
  and the Phase 2 sub-finding in `M4_MAX_128GB_NOTES.md`.
- **LCB on Phase 1 Qwen** (added 2026-05-24) — `qwen3.6-27b` Q3
  (atcoder/medium abc365_c) is the only `†` survivor: at 65 536 still
  truncated, but only that one question. `qwen/qwen3-coder-next` finished
  clean after Q19 (atcoder/hard abc354_d) was reran at 65 536 — the
  rerun completed in 36 k tokens without truncation but the answer was
  still wrong, so Q19 is a genuine model failure not a cap artifact.
  `qwen3.6-35b-a3b@6bit` ran the whole bench at 65 536 and still spiraled
  on six questions (Q3, Q4, Q23, Q33, Q39, Q44); originally one of those
  showed as an HTTP 400 cascade, but rerunning Q4 alone on a clean LM Studio
  state confirmed it's a real spiral. With a budget past 1 h or a cap past
  65 k the ceiling for 35b-a3b could land near ~66 %, but the published 54 %
  is the conservatively defensible floor at this rig's standard cap.

### Effective throughput (scenario harness)

| Phase | Model | Speed probe (3-q) | creative-writing | doc-summary | ops-agent | prefill-test |
|---|---|---|---|---|---|---|
| 1 #1 | `qwen/qwen3-coder-next` (6-bit) | 1.5 s total | **67.8 eff t/s** / 70.2 gen | **45.6** / 69.9 | **55.8** / 67.9 | **20.6** / 68.0 |
| 1 #2 | `qwen3.6-27b` (6-bit dense) | 74.4 s total | **19.9 eff t/s** / 20.7 gen | **11.2** / 20.2 | **16.2** / 20.0 | **4.0** / 20.4 |
| 1 #3 | `qwen3.6-35b-a3b@6bit` | 15.8 s total (~90 t/s sustained) | **86.9 eff t/s** / 91.6 gen | **55.9** / 91.7 | **71.4** / 85.5 | **22.9** / 85.5 |
| 2 #4 | `gemma-4-26b-a4b@4bit` | (covered by sweep) | **99.9 eff t/s** / 106.0 gen | **55.8** / 107.6 | **80.7** / 100.3 | **17.9** / 99.2 |
| 2 #5 | `gemma-4-26b-a4b@6bit` | (covered by sweep) | **80.5 eff t/s** / 85.3 gen | **46.9** / 85.9 | **66.6** / 80.8 | **20.5** / 80.9 |
| 2 #6 | `gemma-4-31b-it-mlx` (8-bit dense) | (covered by sweep) | **13.6 eff t/s** / 13.9 gen | **8.0** / 14.3 | **10.3** / 13.7 | **3.3** / 13.6 |
| 2 #7 | `gemma-4-e4b-it-mlx` (4B/8-bit) | (covered by sweep) | **69.5 eff t/s** / 73.7 gen | **46.1** / 75.4 | **62.9** / 70.9 | **29.1** / 69.3 |
| 2/3 (#8–10) | (not yet run) | — | — | — | — | — |

### Qualitative coding artifacts

Two task-manager apps built end-to-end by Phase 1 models, kept for
side-by-side code-quality comparison. See [`results/coding-task/README.md`](../results/coding-task/README.md).

- `qwen3-coder-next-80b-a3b/` — Next.js 16 + Tailwind + SQLite
- `qwen3.6-27b-mlx-6bit/` — Static HTML/JS, localStorage

To add a third: same brief, run it, drop the source in a new
`results/coding-task/<model-id>/` and update its README.

### Phase 1 outcomes

- **`qwen3.6-27b` is the quality king** — and the LCB backfill confirms it on contamination-resistant coding too (LCB 62 %, +6pp over coder-next, +8pp over 35b-a3b). Leads or ties every accuracy bench; knowledge avg 85.8 % is the highest in scope. Cost: dense → ~20 tok/s → 37.6 h full suite + 16.2 h LCB alone, dominated by thinking-spirals on hard problems.
- **`qwen3-coder-next` is the speed / agentic king.** Knowledge avg 73.8 % is the lowest, but it shipped the full suite in **1.9 h** (19× faster than 27b) and LCB at **56 %** in 42 min. HumanEval 89 % held up — LCB 56 % is in the same coding tier as 35b-a3b 54 %. Daily-driver slot confirmed: default for OpenCode / Cline / agentic loops.
- **`qwen3.6-35b-a3b` is the MoE-thinking middle.** Best jdhodges (97.5 %), best MATH (89 %), ~3× faster than 27b for ~3 pp less knowledge. LCB **54 %** with **6 truncations** at 65 k — most spiral-prone of the trio on hard coding problems.
- **Knowledge rank ≠ tool-calling rank.** 35b-a3b leads jdhodges, trails Veerman; 27b ties both but is slow.
- **HumanEval saturation confirmed.** HE spread was 87–93 (6pp). LCB spread is 54–62 (8pp) and rerank-preserves: 27b > coder-next > 35b-a3b. LCB is now the canonical coding signal for Phase 1 going forward.

### Phase 2 outcomes

- **`gemma-4-26b-a4b@6bit` is the Gemma flagship.** Knowledge avg 78.0 % is the best in the Gemma family but still 7.8pp below `qwen3.6-27b`. Wins or ties every Gemma A/B; ops-agent 80.8 gen t/s — 4× faster than 27b for ~8pp less knowledge.
- **`@4bit` is the new throughput king on this rig** (ops-agent 100.3 gen t/s, beats every Phase 1 model). HumanEval 98 % and jdhodges 98 % match `@6bit` — quant cost shows on the hard benches only (LCB −14, GPQA −6 after Step B reruns).
- **`gemma-4-26b-a4b@6bit` is the rig's LCB ceiling at 80 %** (after Step B). +12 pp over the best Qwen Phase 1 result (27b 62 %). The quant tax on LCB stays material (`@4bit` 66 % vs `@6bit` 80 % = 14 pp).
- **`gemma-4-31b-it-mlx` is a cost-trap.** 6× slower decode (13.7 vs 80.8 gen t/s) for indistinguishable quality vs `@6bit`; DROP +6pp is its only standout win. Demote / skip in normal rotation.
- **`gemma-4-e4b-it-mlx` is FIM / quick-call only.** HumanEval 91 % and jdhodges 88 % are usable; MATH **collapses to 14 %**, MMLU −13pp, Veerman −16pp vs `@6bit`. Not a daily-driver fallback.
- **No Gemma beats `qwen3.6-27b` on knowledge.** Best Gemma trails 27b by MMLU −10, MATH −5, DROP −11, GPQA −17pp (raw). 27b retains the "knowledge generalist" slot. But Gemma `@6bit` **does** beat 27b on LCB (80 vs 62) — coding-specific recommendation now diverges from knowledge.
- **Gemma 4 truncation profile differs from Qwen thinking models.** Gemma emits zero thinking tokens but writes long exhaustive code → truncates LCB on hard problems (18 % at `@4bit`, 8 % at `@6bit`). Step B reruns confirmed most of those are real model limits, not cap-too-tight artifacts — only Q2 (`@4bit`) and Q28 (`@6bit`) recovered at 65 k. Operational rule: still worth raising `--max-tokens` on LCB for Gemma 4, but expect modest score lift (~+2 pp), not the +10–15 pp the Phase 2 estimate suggested.
- **Phase 2 wall-clock: ~13.5 h across 4 models** — far under the 2-4 day forward estimate. No thinking spirals → predictable per-question times.

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

## Next steps — prioritized (post-Phase-2)

Ranked by **(value × confidence) / cost**. Phase 2 done; the Step A/B/C/D/E
list below is the carry-over set.

### Step A — rerun truncated GPQA questions with `--max-tokens 65536` (Qwen Phase 1)

Carried over from the original plan. Phase 2 Gemma GPQA was already run at
65 536 so this step still only applies to the two Qwen 3.6 thinking models.

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

- **Cost:** ~7–10 h on 27b dense, ~3–5 h on 35b-a3b MoE (worst-case).
- **Risk:** residual truncations at 65 536 form the floor of "unanswerable at this scale" — publish explicitly.
- **Harness gotcha (confirmed in Phase 2):** `bench2.py` writes a *fresh* summary per run; it does **not** merge `--only` reruns. To produce a canonical corrected score, the per-question JSONLs need to be reconciled manually (or by a small post-hoc script).

### Step B — Gemma LCB truncation reruns at `--max-tokens 65536` ✅ **DONE 2026-05-24**

Both reruns landed; canonical MERGED summaries written:

- `@4bit` 9 reruns (Q2, 8, 11, 19, 28, 39, 44, 45, 46): only Q2 recovered;
  the other 8 still truncated at 65 k → real model limits, not cap artifacts.
  Score 64 % → **66 %** (+2 pp). Truncations 9 → 8.
- `@6bit` 4 reruns (Q8, 15, 19, 28): Q28 recovered (FAIL → OK); Q8 and
  Q15 now answer cleanly under 10 k tokens but still wrong (real model
  limits); Q19 still spirals at 65 k. Score 78 % → **80 %** (+2 pp).
  Truncations 4 → 1.

Both reruns came in well under the original ~1–3 h estimate (116 min for
`@4bit`, 21 min for `@6bit`). The big surprise vs the testing-plan's
~80 %/~86 % projections: most of Gemma 4's LCB failures at 32 k are not
"too thinky for the cap" — they're genuine answers-but-wrong or
spiral-past-65k cases. The raised cap recovers the marginal "almost done
at the buzzer" cases (1 of 9, 1 of 4), not the deep failures. Useful
calibration for any future "raise the cap" plan.

### Step C — add LiveCodeBench to the Phase 1 daily drivers ✅ **DONE 2026-05-24**

Plan: [`docs/benchmark-plans/2026-05-22-livecodebench-phase-1.md`](benchmark-plans/2026-05-22-livecodebench-phase-1.md).
Results in the table above (LCB v6 column). Headline: **27b dense 62 %**
leads, **coder-next 56 %** second, **35b-a3b 54 %** third — same rank order
as knowledge benches; HumanEval saturation was real (89/93/87 collapsed to a
14-point spread on LCB). Costs ran far over the plan's ~5 h estimate:
27b alone took 16.2 h wall-clock (mostly thinking budget for 50 LCB
problems at ~20 t/s), 35b-a3b 4.6 h, coder-next 42 min.

Two harness improvements landed during execution:
1. `bench2.py` now honors `BENCH_TIMEOUT` (seconds) for per-request urlopen
   timeout — the hardcoded 1800 s caused a request-queue cascade on
   slow-thinking 27b at 65 k cap. Set `BENCH_TIMEOUT=3600` for any future
   ≤ 20 t/s thinking-model run at the raised cap.
2. Detached driver pattern (`nohup`/PPID=1 wrapper) for any run longer than
   ~2 h — `Bash run_in_background` was silently killing python processes
   around the 2–3 h mark regardless of timeout flag. See
   [LCB backfill plan §"What broke"](benchmark-plans/2026-05-22-livecodebench-phase-1.md)
   and `.bench-logs/run-27b-lcb-remaining.sh`.

### Step D — Phase 2 quant-A/B variants

The two outstanding "same weights, different quant" comparisons (#8 / #9):

- `qwen/qwen3-coder-next@4bit` vs already-done `@6bit` — does 4-bit hold up on tool-calling + MATH?
- `qwen3.6-35b-a3b@8bit` vs already-done `@6bit` — does the heavier quant close the gap to 27b on knowledge?

Cost: ~2–3 days combined per the Phase 2 forward estimate.

### Step E — Phase 3 fit-test for `deepseek-v4-flash-dq`

Same brief as before: only worth doing if a Phase 2 model demonstrated a quality ceiling. **Phase 2 outcome confirms it does** — best Gemma still trails 27b by ~10pp MMLU. So this step is now warranted if you want to push the knowledge frontier further. Cap context at 32 768 on load; tool-calling only as the first signal.

### Step F — defer

- Engine A/B (LM Studio MLX vs llama.cpp GGUF): still needs a GGUF pulled first. The post-Phase-2 candidate is Gemma 4 26B-A4B since the MLX numbers are now in.
- Phase 4 watchlist: nothing to do until something lands.

### Step G — Terminal-Bench 2.0 backfill ✅ **DONE 2026-05-29**

Plan: [`docs/benchmark-plans/2026-05-24-terminal-bench-phase-a-plus-b.md`](benchmark-plans/2026-05-24-terminal-bench-phase-a-plus-b.md).
All 7 local models measured on-rig — chartTBench in
[`reports/quality-benchmarks-charts.html`](../reports/quality-benchmarks-charts.html)
now shows 7 measured rows. Final standings:
`qwen3-coder-next` **32.6 %** (vendor 36.2) > `qwen3.6-27b` dense **31.5 %** >
`qwen3.6-35b-a3b@6bit` **28.1 %** > `gemma-4-31b` dense **22.5 %** >
`gemma-4-26b-a4b@6bit` **21.3 %** > `@4bit` **20.2 %** > `gemma-4-e4b` **4.5 %**.
Full Phase A + B write-up in
[`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`](../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).

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
  --base-url http://<lm-studio-host>:1234/v1 \
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
