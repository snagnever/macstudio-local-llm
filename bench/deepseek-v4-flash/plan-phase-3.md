# 2026-05-29 — DeepSeek V4 Flash full sweep (Phase 3 #10)

## Context

`deepseek-v4-flash-dq` (`mlx-community/DeepSeek-V4-Flash-2bit-DQ`, 96.53 GB on disk) is **Phase 3 #10** in [`docs/testing-plan.md`](../../docs/testing-plan.md) — the last untested model in scope and the only one capable of pushing the knowledge frontier past `qwen3.6-27b` (best Gemma still trails 27b by ~10 pp MMLU per Phase 2 outcome). It cannot run in LM Studio: LM Studio's bundled `mlx-lm 0.31.3` predates DeepSeek-V4 architecture support, which lives in [mlx-lm PR #1192](https://github.com/ml-explore/mlx-lm/pull/1192) (still open as of 2026-05-19). The standing workaround is a patched `mlx-lm.server` in an isolated venv at port 8765, already documented in [`docs/deepseek-v4-flash-setup.md`](../../docs/models/deepseek-v4-flash/setup.md). This plan layers the full benchmark sweep on top of that runtime.

**Outcome:** complete row in every existing scoreboard for `deepseek-v4-flash-dq-2bit`, matching the seven models already there. Settles whether the 2-bit DQ quant on a 284B/13B MoE actually outperforms the rig's best dense knowledge model on contamination-resistant signals (LCB v6, GPQA, MMLU).

**Scope (full sweep, user-confirmed 2026-05-29):**
- Speed probe + tool-calling (jdhodges-40 + Veerman-12)
- HumanEval, LiveCodeBench v6, MMLU, MATH, DROP, GPQA — all `--max-tokens 65536`
- 4 throughput scenarios (ops-agent, doc-summary, prefill-test, creative-writing)
- Terminal-Bench 2.0 (Phase A protocol, `--agent-timeout-multiplier 0.5`)

## Approach

Drive every existing benchmark harness against the patched `mlx-lm.server` on `http://127.0.0.1:8765/v1` by overriding the `LMSTUDIO_URL` / `OPENAI_API_BASE` env vars. **No new harnesses, no new scripts — only env-var routing and detached driver shells** (mirroring the Step C 2-h-silent-kill lesson from the [LCB backfill plan](../lcb-phase1/plan.md)). Run benchmarks in the per-model order from `testing-plan.md` (cheap signals first, expensive last); a model that disqualifies on tool-calling or HumanEval saves the 30+ hour tail.

Run **model-major**: the entire suite belongs to one model. LM Studio must have **zero MLX models loaded** for the duration (96.53 GB weight + dynamic KV must be the only thing resident). Sequence benches one-at-a-time against a single long-lived `mlx_lm.server` process — cold-loading 96 GB per bench would waste hours.

**Model ID gotcha:** mlx_lm.server validates the OpenAI `model` field against the `--model` path; sending a friendly alias triggers a HF lookup error (verified 2026-05-29). Use the full path `/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ` as the `--model` argument to every bench command. Filenames will sanitize to `_Users_vitor_.lmstudio_models_mlx-community_DeepSeek-V4-Flash-2bit-DQ` — rename to the canonical `deepseek-v4-flash-dq-2bit` label when updating scoreboards.

## Pre-flight (must pass before starting)

1. **mlx-lm runtime ready.** Follow steps 1–5 of [`docs/deepseek-v4-flash-setup.md`](../../docs/models/deepseek-v4-flash/setup.md). The CLI smoke test (step 5) **must** produce a coherent ≥ 25 tok/s paragraph before continuing.
2. **LM Studio idle.** `lms ps` empty / `lms unload --all`. DeepSeek V4 Flash cannot share the rig with another large model (operational rule, testing-plan.md:414).
3. **Wall-clock budget.** Per testing-plan.md estimates and 13B-active MoE behavior similar to `qwen3-coder-next`, expect **~3–5 days** total. Detach any single bench likely to exceed 2 h via `bench/deepseek-v4-flash/logs/run-<name>.sh` + `nohup ... & disown` (note: this rig lacks `setsid`, so use plain nohup+disown rather than the testing-plan's setsid pattern).

## Step 1 — Start the long-lived `mlx_lm.server`

mlx-lm grows KV cache **dynamically** — no pre-allocated context cap on the server. Bumping `--max-tokens` to 65 536 matches the standard raised cap used across every other model on the scoreboard (testing-plan.md:415 operational rule).

```bash
nohup /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/bin/python -m mlx_lm.server \
  --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --chat-template-args '{"enable_thinking":false}' \
  --host 0.0.0.0 --port 8765 \
  --max-tokens 65536 --temp 0.0 \
  > bench/deepseek-v4-flash/logs/mlx-server-deepseek-v4.log 2>&1 &
disown
```

**Memory contingency:** if wired RAM trends past ~120 GB during a long bench (watch with `sudo memory_pressure` in a second pane), drop `--max-tokens` on the offending bench command to 32 768 (no server restart needed). Only restart the server with a lower cap if dynamic KV growth itself OOMs.

If the server emits the repetition bug at `temp=0.0` (HF thread issue per setup-guide step 6), restart with `--temp 0.6`.

## Step 2 — Sanity check via existing harness shape

```bash
export LMSTUDIO_URL=http://127.0.0.1:8765/v1
export BENCH_TIMEOUT=3600
export MODEL_PATH="/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
cd /Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
python3 scripts/bench2.py mmlu --examples 1 --model "$MODEL_PATH"
```

If this returns a graded result, every other bench2.py invocation works. If it errors, fix here — don't proceed.

## Step 3 — Run benchmarks in cheap-first order

All commands assume the Step 2 env vars. All `bench2.py` invocations pass `--max-tokens 65536`. Each writes its summary to `tools/local-llm-bench-m4-32gb/benchmarks/runs/<bench>_<safe_model>_<timestamp>_summary.json`. Use the **detached driver pattern** (`bench/deepseek-v4-flash/logs/run-<name>.sh` + `nohup ... & disown`) for MATH, GPQA, LCB.

### 3a. Speed probe (~10 min)
```bash
python3 scripts/speed_probe.py --model "$MODEL_PATH" --base-url http://127.0.0.1:8765/v1
```
**Decision gate:** if cold-load fails or wired memory pushes past ~120 GB, stop and re-evaluate fit.

### 3b. Tool calling (~15–30 min)
```bash
python3 scripts/tool_call_bench.py --model "$MODEL_PATH" --base-url http://127.0.0.1:8765/v1
```
**Caveat:** DeepSeek V4 Flash is listed in testing-plan.md:54 as **Tools: —** (no native tool-calling). Expect either (a) prompt-based emulation with degraded scores, or (b) plain prose where structured calls are expected. Record whichever lands — it's the signal.

### 3c. HumanEval (~30–60 min)
```bash
python3 scripts/bench2.py humaneval --examples 100 --model "$MODEL_PATH" --max-tokens 65536
```

### 3d. LiveCodeBench v6 (~30–90 min)
```bash
python3 scripts/bench2.py livecodebench --examples 50 --model "$MODEL_PATH" --lcb-version release_v6 --max-tokens 65536
```

### 3e. MMLU (~30–60 min)
```bash
python3 scripts/bench2.py mmlu --examples 100 --model "$MODEL_PATH" --max-tokens 65536
```

### 3f. MATH (~2–8 h — detached)
```bash
# In bench/deepseek-v4-flash/logs/run-deepseek-v4-flash-math.sh, then:
nohup bash bench/deepseek-v4-flash/scripts/run-deepseek-v4-flash-math.sh > /dev/null 2>&1 &
disown
```

### 3g. DROP (~1–2 h)
```bash
python3 scripts/bench2.py drop --examples 100 --model "$MODEL_PATH" --max-tokens 65536
```

### 3h. GPQA (~2–10 h — detached)
```bash
# In bench/deepseek-v4-flash/logs/run-deepseek-v4-flash-gpqa.sh, then:
nohup bash bench/deepseek-v4-flash/scripts/run-deepseek-v4-flash-gpqa.sh > /dev/null 2>&1 &
disown
```
With `enable_thinking:false`, the 64k cap should be ample. Residual truncations are "unanswerable at this scale" floor signal, not a routing bug.

## Step 4 — Throughput scenarios

Skip the 8K prefill-test turn if it OOMs (operational rule, testing-plan.md:392) — at 64k cap less likely but still possible at peak memory.

```bash
cd /Users/vitor/LocalProjects/local-llms/tools/local-llm-bench
python3 bench.py \
  --backend lmstudio \
  --base-url http://127.0.0.1:8765/v1 \
  --model "$MODEL_PATH" \
  --model-label deepseek-v4-flash-dq-2bit
```

`--backend lmstudio` speaks plain OpenAI-compatible HTTP — exactly what mlx_lm.server exposes. Results land in `tools/local-llm-bench/results/deepseek-v4-flash-dq-2bit/<scenario>/m4-max-128gb-40gpu_lmstudio.json`.

## Step 5 — Terminal-Bench 2.0

Create `bench/terminal-bench/scripts/run-tbench-deepseek-v4-flash.sh` modeled on the existing `bench/terminal-bench/scripts/run-tbench-coder-next.sh`:

```bash
export OPENAI_API_BASE="http://127.0.0.1:8765/v1"
export OPENAI_API_KEY="not-needed"

harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/$MODEL_PATH" \
  --env docker \
  -n 1 -y --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name deepseek-v4-flash
```

Launch detached: `nohup bash bench/terminal-bench/scripts/run-tbench-deepseek-v4-flash.sh > /dev/null 2>&1 & disown`.

**Caveat (same as Step 3b):** terminus-2 issues structured commands. If DeepSeek V4 Flash can't reliably produce them, T-Bench scores collapse (compare with `gemma-4-e4b` at 4.5 % as the known floor). Record regardless.

After the run completes (~6–10 h based on coder-next's profile):
```bash
python3 tools/local-llm-bench-m4-32gb/scripts/harbor_to_summary.py \
  --jobs-dir bench/terminal-bench/logs/tbench-runs/deepseek-v4-flash \
  --model "$MODEL_PATH"
```

## Step 6 — Update scoreboards & docs

1. **`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`** — append a "Phase 3 #10 — DeepSeek V4 Flash" section with full numbers, truncation count, wall-clock, one-paragraph commentary mirroring Phase 1/2 outcome blocks.
2. **`docs/testing-plan.md`** — fill in the `2/3 (#8–10)` row in both the accuracy table (line ~121) and the throughput table (line ~169); promote Phase 3 #10 from PENDING to DONE in Step E.
3. **`reports/benchmark-charts.html`** and **`reports/quality-benchmarks-charts.html`** — regenerate per [`reports/README.md`](../../reports/README.md). The chartTBench panel needs the new row too.
4. **`tools/local-llm-bench-m4-32gb/results/charts/`** — regenerate via `python3 scripts/m4max_charts.py`.
5. **`docs/local-llm-reference.md`** — only if DeepSeek V4 Flash actually displaces a model in the Planning / Code / Agent stack.

## Verification

In order. Stop at first failure.

1. `curl -s http://127.0.0.1:8765/v1/models | jq '.data[0].id'` returns the model path.
2. Smoke chat completion returns coherent reply (not a repetition loop).
3. Step 2 (1-question MMLU) returns a graded result, not an HTTP error.
4. Every Step 3 sub-step writes both a `.jsonl` and a `_summary.json`. Summary question count matches request (100 / 50 / 40 / 12).
5. All 4 throughput scenarios produce JSON + MD under `tools/local-llm-bench/results/deepseek-v4-flash-dq-2bit/<scenario>/`.
6. T-Bench writes `result.json` with 89 task slots; adapter writes `tbench_*_summary.json`.
7. Both HTML dashboards show DeepSeek V4 Flash row in every panel.
8. LM Studio still loads other MLX models normally after the run — config.json patch is forward-compatible.

## Known risks

- **No native tool-calling** (inventory marks Tools: —). 3b and Step 5 may produce floor-tier scores; record what lands.
- **Repetition at `temp=0.0`** in server mode (HF thread). Mitigation: restart with `--temp 0.6`.
- **96.53 GB resident + dynamic KV** is the rig's ceiling. Drop per-bench `--max-tokens` to 32 768 if wired RAM > 120 GB.
- **Wall-clock blowout.** `enable_thinking:false` avoids the worst spiral cases; residual truncations are "unanswerable at this scale" floor — publish, don't rerun.
- **PR #1192 sanitize gap** (setup-guide §Known risks). If `mlx_lm.generate` smoke test fails with a shape/key error inside sanitize, benching is blocked upstream.

## Outcome (2026-05-29) — ⚠ Blocked at Step 3b

Full sweep aborted after the runtime tripped Metal's
`resource_limit: 499000` during the jdhodges tool-call bench. Captured
data is a defensible floor only, not a comparison signal.

### Timeline

| Time | Step | Result |
|---|---|---|
| 12:12 | Server start, warm-load | ✅ 96 GB model loaded, ~5 min cold |
| 12:14 | Step 2 — bench2.py 1-q MMLU | ✅ harness routes cleanly via `LMSTUDIO_URL` |
| 12:16 | Step 3a — speed probe (3 prompts) | ✅ 26 t/s steady-state on code prompt, 2.5 s total |
| 12:17 | Step 3b — tool-call jdhodges (40) | ⚠ ran 161.5 min, 12.5 % (5/40), 49 Metal OOMs in server log |
| 14:59 | Sweep aborted, server killed | — |

### Root cause

Metal device on this rig exposes a fixed **`resource_limit: 499000`**
(checked via `mx.device_info()`) — the maximum number of resources a
single Metal command buffer can reference. mlx-lm PR #1192's DeepSeek V4
MLA indexer at `deepseek_v4.py:557` accumulates sub-buffers per forward
pass; once the server's prompt cache grows past a few cached sequences,
the indexer's resource count exceeds the limit and `mx.maximum(scores, 0)
* self.scale` aborts:

```
RuntimeError: [metal::malloc] Resource limit (499000) exceeded.
```

First ~19 jdhodges cases ran cleanly on a cold cache (all `no_tool_called`,
prose-only output, no Metal errors). From case 20 onward, the cache had
grown enough that the resource count crossed the threshold; failed
requests then sat in urlopen for 350–960 s each before timing out as
`request_error: Connection error`. That accounts for the 161 min run time
on a bench projected at ~30 min.

**Not a memory-size issue.** `set_memory_limit` / `set_wired_limit` /
`set_cache_limit` are byte-size knobs and don't help.

> **Root cause CORRECTED 2026-05-30.** The framing above (per-command-buffer
> count; fix = "chunk the indexer") is **wrong** and was disproved. `resource_limit`
> counts **live resident** buffers process-wide, not per command buffer. The real
> bug is an **unbounded per-decode-step leak of ~1 live buffer per layer** in the
> compressor/indexer, hit at ~11,300 generated tokens regardless of prompt length —
> not cross-request cache growth. Chunking and per-layer `mx.eval` were both tested
> and FAILED (can't reclaim live buffers). See
> [`docs/deepseek-v4-flash-metal-oom-investigation.md`](../../docs/models/deepseek-v4-flash/metal-oom-investigation.md)
> §2/§2.4/§5(H7) and the fix plan's Phase 2-revised.

### Side-finding: model is not a tool-calling fine-tune

Independent of the Metal blocker, the mlx_lm.server logged
`WARNING - Received tools but model does not support tool calling` for
every request, consistent with the inventory marking `deepseek-v4-flash-dq`
as **Tools: —**. The 5/40 jdhodges passes are all `edge_cases` where the
correct answer is plain prose (greetings, definitions). Every
tool-emission category — `tool_selection`, `argument_accuracy`,
`multi_tool`, `format_compliance` — scored 0 / 8. Even with the Metal
issue fixed, this checkpoint would floor on tool-calling benches.

### Adjustments to live docs

- [`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)
  gained a "Phase 3 #10 — DeepSeek V4 Flash (blocked, 2026-05-29)" section
  with full numbers, Metal device info, and artifacts list.
- [`docs/testing-plan.md`](../../docs/testing-plan.md):
  - Step E rewritten as ⚠ BLOCKED with the upstream PR reference.
  - Accuracy scoreboard adds a `3 #10` row with `12.5 % ✗` and a new ✗
    legend explaining "did not complete on-rig because of upstream
    runtime bug — not a model-quality signal."
  - Throughput scoreboard adds the cold-cache speed probe (`2.5 s / 3
    prompts (26 t/s code)`) and ✗ for the un-run scenarios.
  - "Still to run" Phase 3 #10 row marked blocked with the same
    explanation.
- Reports (`reports/benchmark-charts.html`,
  `reports/quality-benchmarks-charts.html`) intentionally **not** updated.
  A 12.5 % tool-call row would land in the same bar group as
  `coder-next` (90 %) and `Gemma 4 26B-A4B@6bit` (97.5 %) and visually
  imply they are comparable. Re-evaluate when the upstream fix lands.
- Tiny harness drift: [`tools/local-llm-bench-m4-32gb/scripts/speed_probe.py`](../../tools/local-llm-bench-m4-32gb/scripts/speed_probe.py)
  now reads `LMSTUDIO_URL` like `bench2.py` does; previously the
  endpoint was hard-coded to `:1234`.

### Re-prioritized next step

With Step E parked, [Step D](../../docs/testing-plan.md#step-d--phase-2-quant-ab-variants)
becomes the highest-value pending work — `qwen/qwen3-coder-next@4bit`
vs `@6bit` (tool-call + MATH) and `qwen3.6-35b-a3b@8bit` vs `@6bit`
(does heavier quant close the gap to 27b on knowledge). Both are
already-on-disk, run on the same harnesses with no upstream-runtime
dependency.

### Follow-up investigation (same day)

After the initial sweep was aborted, two follow-ups were attempted: a chunked-indexer patch (`fixes/mlx-lm/mlx-lm-deepseek-v4-indexer-chunk.patch`) and a restart-per-batch operational wrapper (`bench/deepseek-v4-flash/scripts/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh`). Both partially help but neither fully solves the OOM. The full root-cause analysis, ranked hypotheses, and a confidence-ordered fix-application plan are now in dedicated docs:

- [`docs/deepseek-v4-flash-metal-oom-investigation.md`](../../docs/models/deepseek-v4-flash/metal-oom-investigation.md) — Metal `resource_limit: 499000` analysis, all test runs (49 OOMs un-patched → 3 chunk=8 → 8 chunk=2 → 42 across restart-per-batch), external signals (mlx-lm PR #1192 stalled since 2026-05-01; spicyneuron's 4000-token reproducer & `fix-ds4` fork), six ranked hypotheses.
- [`docs/deepseek-v4-flash-metal-oom-fix-plan.md`](../../docs/models/deepseek-v4-flash/metal-oom-fix-plan.md) — confidence-ordered hypothesis-application plan, exact code edits and apply commands for each step, pass/fail tests, daily-driver "done" bar.

**Phase 3 #10 RE-OPENED 2026-05-30 — OOM fixed.** The per-decode-step buffer leak is fixed
by [`fixes/mlx-lm/mlx-lm-deepseek-v4-cache-materialize.patch`](../../fixes/mlx-lm/mlx-lm-deepseek-v4-cache-materialize.patch)
(one hunk in `DeepseekV4Model.__call__` materializing all cache state each forward). Verified:
[`leak_probe.py`](scripts/leak_probe.py) slope 205 → 7 KB/step and
[`repro_oom_gen.py`](scripts/repro_oom_gen.py) streamed **19,989 tokens clean at
31.3 t/s, 0 `metal::malloc`** (baseline died at 11,314). The full sweep is now re-running on
a single long-lived server (no wrapper) to replace the blocked rows below with real data.
(The "H1 per-layer eval" idea in the older write-up was tested 2026-05-30 and FAILED;
"chunk the indexer" also does not work — both can't reclaim *live* buffers.)

### Outcome (2026-05-30) — partial sweep complete, 0 OOMs

With the fix in place the knowledge sweep ran on a **single long-lived patched server** (no
restart wrapper), greedy `temp=0`, thinking=OFF, per-request `max_tokens` capped (2048/4096)
to bound the separate 2-bit degeneration. This doubled as the pre-upstream-submission OOM
soak: **300 requests, 0 `metal::malloc`, 0 errors, ~2h44m, clean shutdown.**

| Bench | n | Score | TRUNC (degenerate) | Wall-clock | Metal OOMs |
|---|---|---|---|---|---|
| MMLU | 100 | **44 %** | 0 | 16 min | 0 |
| GPQA | 100 | **24 %** | 36 | 96 min | 0 |
| HumanEval | 100 | **48 %** | 15 | 52 min | 0 |
| Tool-calling jdhodges (40) | 40 | 8/40 (20 %) | — | 19.8 min | 0 |

- Scores are the **2-bit DQ quality floor** (vs Gemma/Qwen locals at MMLU 65–88 / GPQA 34–70 /
  HumanEval 87–98), orthogonal to the now-fixed OOM. Degeneration is long-form only (0 % on MMLU).
- **Upstream submitted:** issue [ml-explore/mlx-lm#1332](https://github.com/ml-explore/mlx-lm/issues/1332),
  PR [Blaizzy/mlx-lm#25](https://github.com/Blaizzy/mlx-lm/pull/25), comment on
  [#1192](https://github.com/ml-explore/mlx-lm/pull/1192#issuecomment-4585428668).
- **Charts/docs updated:** `chart_m4max_phase1_*.png` regenerated with the DeepSeek row;
  `M4_MAX_128GB_NOTES.md` Phase 3 #10 Addendum 2; `reference_scores.md` local table.

**Still pending** → tracked in a dedicated, ordered runbook:
[`bench/deepseek-v4-flash/plan-remaining-benches.md`](plan-remaining-benches.md)
(MATH, DROP, LiveCodeBench v6, tool-calling Veerman, Terminal-Bench 2.0, throughput — shortest→longest, docs updated after each).

### Retry preconditions (historical — satisfied 2026-05-30; kept for record)

1. mlx-lm PR #1192 (or successor / spicyneuron `fix-ds4`) has merged a fix
   that stops the compressor/indexer retaining a live buffer per layer per
   decode step (so the live-resource count stays bounded over a long generation).
   NOT "chunk the indexer" — that was tried and does not work.
2. A patched mlx-lm version is installable into the
   `venvs/mlx-v4-flash/` venv (or LM Studio bundles it).
3. The smoke test in pre-flight runs 30+ requests sequentially against
   the same `mlx_lm.server` without a `metal::malloc` error in the
   server log.

Until then, leave the model on disk (no re-download cost) and the
detached driver scripts in `bench/deepseek-v4-flash/logs/run-deepseek-v4-flash-*.sh` in
place — they're ready to fire when the runtime is fixed.

## Critical files / paths

- Runtime: `/Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/` + [`docs/deepseek-v4-flash-setup.md`](../../docs/models/deepseek-v4-flash/setup.md)
- Bench harnesses: [`tools/local-llm-bench-m4-32gb/scripts/bench2.py`](../../tools/local-llm-bench-m4-32gb/scripts/bench2.py), [`tool_call_bench.py`](../../tools/local-llm-bench-m4-32gb/scripts/tool_call_bench.py), [`speed_probe.py`](../../tools/local-llm-bench-m4-32gb/scripts/speed_probe.py)
- Throughput: [`tools/local-llm-bench/bench.py`](../../tools/local-llm-bench/bench.py)
- T-Bench drivers: `bench/terminal-bench/logs/run-tbench-*.sh` (template: `coder-next`) + [`harbor_to_summary.py`](../../tools/local-llm-bench-m4-32gb/scripts/harbor_to_summary.py)
- Outputs: `tools/local-llm-bench-m4-32gb/benchmarks/runs/`, `tools/local-llm-bench/results/deepseek-v4-flash-dq-2bit/`, `bench/terminal-bench/logs/tbench-runs/deepseek-v4-flash`
- Scoreboards: [`M4_MAX_128GB_NOTES.md`](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md), [`testing-plan.md`](../../docs/testing-plan.md), [`benchmark-charts.html`](../../reports/benchmark-charts.html), [`quality-benchmarks-charts.html`](../../reports/quality-benchmarks-charts.html)
