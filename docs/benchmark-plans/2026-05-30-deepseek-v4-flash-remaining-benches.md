# DeepSeek-V4-Flash — remaining benchmarks (ordered runbook)

**Model:** `mlx-community/DeepSeek-V4-Flash-2bit-DQ` (MLX 2-bit DQ, ~96 GB) on Mac Studio
**M4 Max 128 GB**, patched mlx-lm (`patches/mlx-lm-deepseek-v4-cache-materialize.patch`).
**Parent plan:** [`2026-05-29-deepseek-v4-flash-phase-3.md`](2026-05-29-deepseek-v4-flash-phase-3.md).

## Status

Done 2026-05-30 (single long-lived server, 0 OOMs across 300 requests):
**MMLU 44 % · GPQA 24 % · HumanEval 48 % · tool-calling jdhodges 8/40 (20 %).**

This runbook covers the **remaining** benches, **ordered shortest → biggest**, with a
**mandatory doc/chart update after each one finishes** (§Update protocol). The OOM is already
fixed and filed upstream (ml-explore/mlx-lm#1332, Blaizzy/mlx-lm#25); these runs are for
**scores + continued OOM soak**, so the bar is "completes with 0 `metal::malloc`," and the
scores are expected at the 2-bit quality floor.

## Queue (run top-to-bottom)

| # | Bench | Harness | n | max_tok | Est. wall-clock | Why this slot | Done |
|---|---|---|---|---|---|---|---|
| 1 | **Tool-calling Veerman** | `tool_call_bench.py` | 12 | server cap | ~10 min | shortest; unlocks the `tool_combined` chart cell | ☑ 2/12 (N/A — no tool template) |
| 2 | **DROP** | `bench2.py` | 100 | 2048 | ~20–30 min | short extractive answers → low degeneration, fast | ☐ |
| 3 | **Throughput scenarios** | `local-llm-bench/bench.py` | 4 | per-scenario | ~30 min | bounded token budgets; fills throughput scoreboard | ☐ |
| 4 | **MATH** | `bench2.py` | 100 | 4096 | ~60–90 min | long reasoning + degeneration, like GPQA | ☐ |
| 5 | **LiveCodeBench v6** | `bench2.py` | 50 | 8192 | ~60–120 min | long code-gen + per-test execution; slowest knowledge bench | ☐ |
| 6 | **Terminal-Bench 2.0** | `harbor` + docker | 89 tasks | — | multi-hour | multi-turn agent loop; longest + hardest; run last when confident | ☐ |

## Shared setup (one long-lived patched server for the whole queue)

Reuse the soak server config — greedy `temp=0` (standard bench methodology, matches the repo's
reference scores), `thinking=OFF`, high server ceiling with **per-request caps** to bound the
2-bit degeneration runaway:

```bash
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python        # patched mlx-lm
BENCHPY=$ROOT/.venv/bin/python                # bench client
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
SLOG=$ROOT/.bench-logs/server-remaining.log

pkill -f mlx_lm.server; sleep 3; : > "$SLOG"
nohup "$PY" -m mlx_lm.server --model "$MODEL" --host 0.0.0.0 --port 8765 \
  --max-tokens 65536 --temp 0.0 --chat-template-args '{"enable_thinking":false}' \
  >> "$SLOG" 2>&1 & disown
# wait for /v1/models, then warm-load with a 4-token "hi" before benching.

export LMSTUDIO_URL=http://127.0.0.1:8765/v1   # bench2.py + tool_call_bench.py
export BENCH_TIMEOUT=1800
cd "$ROOT/tools/local-llm-bench-m4-32gb"
```

Keeping **one server alive across all six** maximises continued OOM-soak evidence. Restarting
between benches is acceptable (the OOM is already proven) but loses that bonus signal. Watch
`grep -c metal::malloc "$SLOG"` after each — must stay **0**.

## Per-bench commands

```bash
# 1. Veerman (tool-calling, 12 cases)  — see §Data hygiene before computing tool_combined
"$BENCHPY" scripts/tool_call_bench.py --model "$MODEL" --suite veerman \
  --base-url $LMSTUDIO_URL --force --no-cooldown --run-prefix toolcall
  → results in benchmarks/runs/toolcall_veerman_*_summary.json

# 2. DROP (n=100)
"$BENCHPY" scripts/bench2.py drop --examples 100 --model "$MODEL" --max-tokens 2048

# 3. Throughput (4 scenarios) — adapt the coder-next throughput driver
#    (tools/local-llm-bench/bench.py + scenarios/*.json against $LMSTUDIO_URL)
#    See .bench-logs/run-full-*.sh for the scenario list + invocation template.

# 4. MATH (n=100)
"$BENCHPY" scripts/bench2.py math --examples 100 --model "$MODEL" --max-tokens 4096

# 5. LiveCodeBench v6 (n=50)
"$BENCHPY" scripts/bench2.py livecodebench --examples 50 --model "$MODEL" \
  --lcb-version release_v6 --max-tokens 8192

# 6. Terminal-Bench 2.0 — driver already exists (terminus-2 agent, docker)
nohup bash $ROOT/.bench-logs/run-tbench-deepseek-v4-flash.sh >/dev/null 2>&1 & disown
```

## ✅ Update protocol — run after EACH bench finishes (do not batch)

1. **Verify the run.** `grep -c metal::malloc "$SLOG"` (must be 0); note `score`, `correct/total`,
   and `>>> N truncated` (the degeneration count) from the bench output / `_summary.json`.
2. **Regenerate charts.** `"$BENCHPY" scripts/m4max_charts.py` — the new cell auto-fills from
   `benchmarks/runs/*_summary.json`; blank cells remain "not yet measured."
3. **Update `results/M4_MAX_128GB_NOTES.md`** → Phase 3 #10 **Addendum 2** results table: add the
   bench's row (score, TRUNC, wall-clock, OOMs) and remove it from the "Still pending" list.
4. **Update `results/reference_scores.md`** → the DeepSeek-V4-Flash row in the "this rig" local
   table (fill MATH / DROP cells; LCB + tool-calling live in the notes/chart, not that table).
5. **Tick this queue's checkbox** (☐ → ☑) and append the finishing timestamp + score.
6. **Commit** (per-bench is fine): `docs(deepseek-v4): add <bench> result + refresh charts`.

This keeps every artifact in lock-step so a half-finished queue is never ambiguous.

## Data hygiene — `tool_combined` chart cell (do before/at step 1)

`m4max_charts.py` computes `tool_combined` only when **both** a `jdhodges` and a `veerman`
summary exist for the model, and `load_local_runs()` keeps the **last-sorted** summary per
suite. DeepSeek currently has several `jdhodges` summaries from the OOM investigation
(`toolcall_{arg,sel,multi,cachefix,jdhodges}_*`) — the last-sorted is `toolcall_sel_*` (an
8-case subset), so pairing it with Veerman would yield a wrong denominator. **Before computing
tool_combined:** keep only the canonical patched 40-case jdhodges summary (the
`toolcall_cachefix_jdhodges_*` run = 40/40 completed, 8 correct) in the chart's view — move the
diagnostic-variant summaries out of `benchmarks/runs/` (e.g. into `benchmarks/runs/_oom-probes/`)
or rename the canonical one so it sorts last. Then re-run the chart script.

## Risks / notes

- **Degeneration runaway** at `temp=0` is the main time sink, not OOM. The per-request caps bound
  worst-case to ~70 s (2048) / ~140 s (4096) / ~270 s (8192). If a bench projects too long, lower
  its cap — it changes the score slightly but not the OOM signal.
- **Tool-calling will floor** (Veerman ≈ prose-only, like jdhodges) — the checkpoint isn't a
  tool-calling fine-tune. Run it for completeness/`tool_combined`, not for a real number.
- **Terminal-Bench** needs Docker running and is the only bench that exercises the multi-turn
  agent loop (long contexts, many requests/task) — the strongest remaining OOM stressor. Run it
  last, monitor the server log live, and expect a low score (2-bit + non-agent checkpoint).
- **4-bit caveat:** the real quality fix (4-bit) exceeds 128 GB on this rig, so these 2-bit
  numbers are the ceiling achievable here — report them as such, not as the model's true quality.
