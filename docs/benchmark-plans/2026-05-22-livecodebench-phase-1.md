# 2026-05-22 — LiveCodeBench backfill for Phase 1 daily drivers

## Context

LiveCodeBench (LCB) landed in `bench2.py` after Phase 1 closed (2026-05-19),
so the three Qwen daily-driver candidates have every column in the master
table except LCB. Phase 2 added LCB for all four Gemma 4 variants, leaving
the LCB column empty only for Phase 1.

This plan executes [testing-plan Step C](../testing-plan.md#step-c--add-livecodebench-to-the-phase-1-daily-drivers)
verbatim — three runs, no other benches.

**Models in scope (Phase 1, all confirmed in
[`docs/testing-plan.md`](../testing-plan.md) Current-status table):**

| # | Model ID (API) | Class | Why LCB matters |
|---|---|---|---|
| 1 | `qwen/qwen3-coder-next` | non-thinking, 80B/3B MoE | Daily-driver coder. HumanEval 89 % is the lowest Phase 1 coding number — LCB tells us whether that's the saturated-bench artifact it looks like. |
| 2 | `qwen3.6-27b` | thinking, 27B dense | "Quality king" of Phase 1. HumanEval 93 %; LCB is the contamination-resistant cross-check. |
| 3 | `qwen3.6-35b-a3b@6bit` | thinking, 35B/3B MoE | MoE-thinking middle. HumanEval 87 %; LCB separates it from coder-next on real-grade coding. |

## Truncation rule (mandatory — learned in Phase 2)

Phase 2 found Gemma 4 truncates LCB hard problems at the 32 768 default
(`@4bit`: 9/50 trunc, `@6bit`: 4/50 trunc), and the post-hoc rerun at 65 536
recovers most of them. Both `qwen3.6-27b` and `qwen3.6-35b-a3b@6bit` are
**thinking** models — the exact class that spiraled on GPQA during Phase 1.
Apply the rule preemptively so we don't repeat the
[2026-05-19 trap](../testing-plan.md#truncation-finding-gpqa--thinking-models):

- `qwen/qwen3-coder-next` — **default `--max-tokens 32768`** (non-thinking,
  fast; treat truncation as a real signal if it appears).
- `qwen3.6-27b` — **`--max-tokens 65536`**.
- `qwen3.6-35b-a3b@6bit` — **`--max-tokens 65536`**.

If `coder-next` does show truncations at 32 768, rerun the truncated subset
with `--only … --max-tokens 65536` (per Step A/B reconciliation caveat).

## Run order

Cheap / fast first so we get the column populated quickly and abort early if
the harness disagrees with a model:

1. `qwen/qwen3-coder-next` — fast (~67 gen t/s, no thinking). Expect
   **~30–60 min** end-to-end at n=50.
2. `qwen3.6-35b-a3b@6bit` — MoE thinking, ~90 gen t/s sustained but spends
   tokens on reasoning. Expect **~1.5–3 h** at 65 536 cap.
3. `qwen3.6-27b` — dense thinking, ~20 gen t/s + reasoning. Expect
   **~3–6 h** at 65 536 cap (longest leg by far).

Model-major, single-resident: do not co-load. JIT-swap between models. This
also lets the in-flight reports-update agent finish its current pass before
the new LCB numbers land.

## Pre-flight (each session)

```bash
cd /Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
python3 scripts/lms.py check
```

Confirm: target model loaded, **context length 65 536** (matches the
thinking-model rule, fine for `coder-next` too), no other large MLX model
resident. None of these three need `--no-think` — verify per model before
assuming.

## Commands

```bash
cd /Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb

# --- #1: qwen3-coder-next (non-thinking, default cap) ---
python3 scripts/bench2.py livecodebench \
  --examples 50 --lcb-version release_v6 \
  --model "qwen/qwen3-coder-next"

# --- #2: qwen3.6-35b-a3b@6bit (thinking, raised cap) ---
python3 scripts/bench2.py livecodebench \
  --examples 50 --lcb-version release_v6 \
  --model "qwen3.6-35b-a3b@6bit" \
  --max-tokens 65536

# --- #3: qwen3.6-27b (thinking, raised cap) ---
python3 scripts/bench2.py livecodebench \
  --examples 50 --lcb-version release_v6 \
  --model "qwen3.6-27b" \
  --max-tokens 65536
```

Optional wrapper at `.bench-logs/run-lcb-phase1.sh` (mirrors
`run-full-6bit.sh` style) — only if you want one-shot overnight execution
with tee'd logs. Otherwise run interactively model-by-model so the
truncation count is visible before kicking off the next leg.

## Where artifacts land

| Harness | Output path |
|---|---|
| `bench2.py livecodebench` | `tools/local-llm-bench-m4-32gb/benchmarks/runs/livecodebench_<model-slug>_<timestamp>.jsonl` + `_summary.json` |

Each summary includes `correct`, `truncated`, `score`, `max_tokens`,
`elapsed_min` — that's the per-row data for the master table.

## Deliverables — update after all 3 complete

1. [`docs/testing-plan.md`](../testing-plan.md) — fill the **LCB v6** column
   for Phase 1 rows in "Accuracy + coding + tool-calling"; if truncation
   appears, footnote it the same way the Gemma `@4bit`/`@6bit` rows are
   footnoted (raw % + ceiling estimate after Step B).
2. [`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)
   — append a short "Phase 1 LCB backfill" subsection: numbers, trunc count,
   whether the bench moves the Phase-1 rank order.
3. [`tools/local-llm-bench-m4-32gb/results/charts/`](../../tools/local-llm-bench-m4-32gb/results/charts/)
   — regenerate via `scripts/m4max_charts.py` (LCB column will now have all
   7 rows populated).
4. [`reports/benchmark-charts.html`](../../reports/benchmark-charts.html) +
   [`reports/quality-benchmarks-charts.html`](../../reports/quality-benchmarks-charts.html)
   — refresh per [`reports/README.md`](../../reports/README.md). **Wait
   until the in-flight Gemma reports-update pass completes** before kicking
   this one off, to avoid two writers stomping on each other.
5. Strike Step C from [`docs/testing-plan.md`](../testing-plan.md) §Next
   steps once the column is full.

## Wall-clock estimate

| Model | Cap | Estimate |
|---|---|---|
| `qwen/qwen3-coder-next` | 32 768 | 30–60 min |
| `qwen3.6-35b-a3b@6bit` | 65 536 | 1.5–3 h |
| `qwen3.6-27b`          | 65 536 | 3–6 h |

**Total ~5–10 h** — fits an evening + an overnight block, with the dense
27b run as the overnight leg. Aligns with testing-plan Step C's "~5 h"
estimate (which assumed default cap throughout — the raised cap on the two
thinking models is the slack).

## Operational rules (recap)

- Single large MLX model resident at a time.
- Context length on load: **65 536** (same as Phase 1 / Phase 2 default).
- Use exact `GET /v1/models` IDs — `qwen/qwen3-coder-next` has the slash,
  `qwen3.6-35b-a3b@6bit` has the `@6bit` suffix.
- Thermal: 85 °C watch line, 95 °C abort. LCB pass@1 is per-question
  single-shot — no built-in cooldown like the tool-call harness, but per-q
  wall-clock is short enough this hasn't been an issue in prior LCB runs.

## Verification (smoke before the long 27b leg)

Run `qwen/qwen3-coder-next` first and inspect its `_summary.json` for a
non-zero `correct`, `truncated < 5`, and `elapsed_min` in the 30–60 range.
If any of those look off (e.g. zero correct, all truncated, or 5× the
expected wall-clock), stop and diagnose before sinking 6 h into the 27b
run.
