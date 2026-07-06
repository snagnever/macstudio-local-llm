# DeepSeek V4 Flash on Apple Silicon — Metal `resource_limit` OOM investigation

> Model card: [deepseek-v4-flash](models/deepseek-v4-flash.md)


**Goal:** make `deepseek-v4-flash-dq` reliable as a **daily-driver model** on this rig — sustained multi-hour chat / research / long-context sessions without restarts, hangs, or repetition. Benchmarks are a means to that end (a bench sweep is a useful stress test that proves daily reliability), not the goal itself.

**Status (2026-05-30): ROOT CAUSE FIXED — reproducer-verified.** mlx-lm PR #1192's
DeepSeek V4 port hit Apple Metal's `resource_limit: 499000` cap. The cause (see §2) is
an **unbounded per-decode-step leak of live Metal buffers**: the per-layer caches
(compressor/indexer `PoolingCache` concat-grow + `RotatingKVCache` slice-assign, single
*and* batched variants) build un-detached lazy graphs, retaining **~1 live buffer per
layer per decode step**, hitting the live-resource *count* cap at **~11,300 generated
tokens regardless of prompt length**. It is **not** a per-command-buffer / single-forward
problem and **not** prompt-cache-length driven; `mx.clear_cache`/chunking/per-layer-eval
all failed because they cannot reclaim *live* buffers.

**The fix** ([`patches/mlx-lm-deepseek-v4-cache-materialize.patch`](../patches/mlx-lm-deepseek-v4-cache-materialize.patch)):
one hunk in `DeepseekV4Model.__call__` that `mx.eval`s every per-layer cache array once
per forward pass, cutting the lazy chains so the live-buffer count stays bounded.
**Verified:** the forced-generation reproducer streamed **19,989 tokens clean at 31.3 t/s
with 0 `metal::malloc`** (baseline died at 11,314), leak slope 205 → 7 KB/step, **no
throughput regression**. Done-bar #2 green. Full 40-case bench sweep (#1) and 30-turn
chat (#3) validation in progress. See [`docs/deepseek-v4-flash-metal-oom-fix-plan.md`](deepseek-v4-flash-metal-oom-fix-plan.md)
Phase 1.5 + Phase 2-revised (R5 result) for the full path and the two dead ends.

This document captures everything we've learned in case someone (us, an upstream contributor, or a future maintainer) picks the investigation back up.

---

## 1. The problem

### 1.1 What we're trying to do

Run `mlx-community/DeepSeek-V4-Flash-2bit-DQ` (96.53 GB on disk, 284 B / 13 B active MoE) **as a daily-driver model** on a Mac Studio M4 Max 128 GB, driven by the patched `mlx_lm.server` documented in [`docs/deepseek-v4-flash-setup.md`](deepseek-v4-flash-setup.md).

"Daily-driver" means: the model survives sustained chat / research / long-context sessions without manual restarts, repetition spirals, hangs, or "device wedge" recoveries. Concretely, the bar is:

- ≥ 30 distinct chat turns against the same long-lived `mlx_lm.server` process without hitting the resource cap
- Single requests with prompts up to ~32 K tokens complete cleanly (spicyneuron's reproducer fires at ~4000 today)
- No need to restart the server between sessions for routine use

The Phase 3 benchmark sweep in [`docs/benchmark-plans/2026-05-29-deepseek-v4-flash-phase-3.md`](benchmark-plans/2026-05-29-deepseek-v4-flash-phase-3.md) is the **stress test** that proves daily reliability — a 40-case tool-call run is roughly equivalent to a multi-hour mixed chat session in terms of cache pressure. If the bench sweep completes cleanly on a single long-lived server, daily reliability is essentially proven. If we have to restart per batch (where we are today), that's the same workaround a daily user would have to apply manually.

### 1.2 What fails

After ~10-19 requests against a single long-lived server (or after a single prompt grows past ~4000 tokens — see §4.2), inference aborts with:

```
RuntimeError: [metal::malloc] Resource limit (499000) exceeded.
```

The first occurrence has been observed at:
- `mlx_lm/models/deepseek_v4.py:557` — `scores = mx.maximum(scores, 0) * self.scale` (un-patched indexer matmul)
- `mlx_lm/models/deepseek_v4.py:573` — `mx.eval(scores)` (inside our chunked indexer patch)

After the first OOM, the server enters a degraded state where even unrelated operations fail:
- `mx.random.seed(args.seed)` (server bookkeeping at request start) — observed 3× in our patched-v2 run
- Generic stack traces with no clear MLX line

Server only recovers on full restart (kill + relaunch + 20-300 s warm-load).

---

## 2. Root cause

### 2.1 The cap is count-based, not bytes

Apple Silicon Metal device on M4 Max (`applegpu_g16s`) reports the following limits via `mx.device_info()`:

| Field | Value | Interpretation |
|---|---|---|
| `device_name` | Apple M4 Max | — |
| `memory_size` | 137 438 953 472 (128 GB) | Total unified memory |
| `max_recommended_working_set_size` | 115 448 725 504 (~115 GB) | Soft byte budget for resident memory |
| `max_buffer_length` | 86 586 540 032 (~86 GB) | Maximum single MTLBuffer allocation |
| **`resource_limit`** | **499 000** | **Count of MTLResource references per command buffer** ← the cap being hit |

`resource_limit` is **a count, not a byte size**, and it's fixed by the device class — `set_memory_limit`, `set_wired_limit`, `set_cache_limit` (all byte-budget knobs) don't affect it (verified: no Python setter exists in `mx.metal`, mlx 0.31.2).

**Correction (2026-05-30): it is the count of LIVE resident resources, accumulated across the whole process — NOT "per command buffer".** In MLX's Metal backend (`mlx/include/mlx/backend/metal/allocator.h`) the allocator tracks `num_resources_` against `resource_limit_`, alongside a `ResidencySet` (`resident.h`). Every live buffer inserted into the residency set counts; the cap fires when the *cumulative live count* crosses 499000. The earlier "per-command-buffer" reading was wrong and led the original H1–H4 hypotheses astray (see §2.2). Because the cap counts *live* buffers, `mx.clear_cache()` (which only evicts freed-but-cached buffers) and `mx.eval` / `mx.synchronize` (which only cut the lazy graph or add a barrier) cannot lower it.

### 2.2 Why DeepSeek V4 hits it (CORRECTED 2026-05-30)

**The original theory in this section was wrong** and is preserved only as a cautionary note below. The original claim was that `pooled_seq` grows unboundedly and a single un-chunked `(B, n_heads=64, L, pooled_seq)` op in `Indexer.__call__` references too many Metal resources *within one forward pass*. The 2026-05-30 probing **disproved** this:

- A single forward pass at **60K context is clean** (prefill + a few decode steps never OOM).
- A **58-token prompt** OOMs after **~11,300 generated tokens** — the trigger is the *number of decode steps*, not prompt/context length and not `pooled_seq` size in any one pass.

**Actual mechanism: an unbounded per-decode-step leak of live Metal buffers.** Each decode step retains **~1 live buffer per layer** (`num_hidden_layers = 43`; observed ~44 buffers/step from 499000 / 11300). Active memory grows **strictly linearly with no plateau** (measured to 2000 steps: ~166–200 KB/step, ~2.3 GB extrapolated at the ~11,300-step OOM — modest bytes, so the *count* cap binds first, not memory). The retained buffers are **live** (referenced), not freeable cache, which is exactly why per-layer `mx.eval`+`mx.clear_cache` (old H1) and chunking (old H3) cannot help.

DeepSeek V4 introduces Multi-head Latent Attention with a `Compressor` (pooled KV) + `Indexer` (top-k pooled-position selection). Ablation (§2.4) shows the leak lives in this attention machinery. Other models (Qwen 3.6 / Qwen3-Coder-Next / Gemma 4) use standard MHA/GQA with no compressor/indexer and have never tripped the cap on this rig — consistent with the leak being specific to DeepSeek V4's sparse pooled-KV path.

> **Cautionary note (the wrong turn):** reading `resource_limit` as "per-command-buffer" (it's a process-wide *live* count, §2.1) made a single-forward-pass / chunking story look plausible. It cost the entire H1–H4 ladder. Lesson: confirm what a limit *counts* before designing fixes around it.

### 2.3 Why even `mx.random.seed` fails after the first OOM

Once a Metal command buffer fails to submit, the device's command queue appears to enter a partially-broken state. Subsequent submissions inherit corrupted state until a full reset. There's no MLX API documented for explicit device reset short of a process restart.

This explains why "restart-per-N-requests" is the only robust recovery path — the wedge isn't local to the request that errored.

### 2.4 Localized by ablation to the compressor/indexer (2026-05-30)

Monkeypatching the block / attention forward to bypass sub-modules and measuring the per-step active-memory slope (probes: [`.bench-logs/ablation_probe.py`](../.bench-logs/ablation_probe.py), [`.bench-logs/inner_ablation_probe.py`](../.bench-logs/inner_ablation_probe.py)):

| ablation | slope (KB/step) | vs full |
|---|---|---|
| full block | 208 | 100% |
| bypass MoE-FFN | 201 | 97% (leak stays) |
| HyperConnections only | 0 | 0% |
| **bypass attention** | **−3** | **~0% (leak gone)** |
| attention: core-local only (skip compressor+indexer) | 34.5 | 17% |

→ The leak is **in the attention sub-module**, and **~83% of it is the compressor + indexer** (`SparseCompressedAttention.__call__` at [`deepseek_v4.py:805`](../venvs/mlx-v4-flash/lib/python3.12/site-packages/mlx_lm/models/deepseek_v4.py) → `Compressor.__call__` / `Indexer.__call__` + their two `PoolingCache`s), ~17% the core q/kv/SDPA path. MoE and hyper-connections do not leak.

**Ruled out by direct test** (so the fix surface stays narrow):
- *Generic MLX runtime:* 20,000 evals of a trivial fresh graph leak **zero** bytes → model-specific.
- *`@mx.compile` retention:* slope identical with `mx.disable_compile()` (200.1 vs 203.3 KB/step).
- *RoPE freqs cache:* keyed by `(head_dim, inverse)` → bounded.
- *KV/Pooling cache bytes:* summed `nbytes` flat (~12 MB); RotatingKVCache is `sliding_window=128` in-place, PoolingCache concat replaces one buffer.
- *MoE expert paging:* would plateau by ~step 500; growth is linear to 2000 steps.

The fix surface is `Compressor.__call__` / `Indexer.__call__` and their `PoolingCache` update path. Naming the exact retained allocation still needs C++ allocator instrumentation (no Python buffer-count getter) — see §6 next steps.

---

## 3. Tests we've run

Chronological. All on Mac Studio M4 Max 128 GB / macOS 26.3 / mlx-lm built from PR #1192 head + the short-prompt 404 fix patch + the indexer chunking patch (versions noted).

### 3.1 Run #1 — un-patched runtime, jdhodges (40)

- **Server flags:** `--max-tokens 4096 --temp 0.0` (initial), then `--max-tokens 65536 --temp 0.0`
- **Bench:** `tool_call_bench.py --suite jdhodges` (40 cases)
- **Result:** **12.5 % (5/40)**, all 5 passes in `edge_cases` category (prose-correct)
- **Wall-clock:** 161.5 min (cases hung for 350–960 s waiting for OOM-aborted requests)
- **Metal OOMs in server log:** **49**
- **First OOM at:** case 20 (`multi_email_after_calendar_read`), cache had 10 cached sequences
- **Bench summary:** [`benchmarks/runs/toolcall_jdhodges__Users_vitor_.lmstudio_models_mlx-community_DeepSeek-V4-Flash-2bit-DQ_20260529_121729_summary.json`](../tools/local-llm-bench-m4-32gb/benchmarks/runs/)
- **Server log:** `.bench-logs/mlx-server-deepseek-v4.log`

### 3.2 Run #2 — speed probe baseline (cold cache)

- **Bench:** `speed_probe.py` (3 prompts: trivial / mmlu_atmosphere / code_second_largest)
- **Result:** 26 t/s steady-state on the code prompt, total 2.5 s
- **Metal OOMs:** **0** (cold cache fits trivially)
- **Result file:** [`tools/local-llm-bench-m4-32gb/results/speed_probe/_Users_vitor_.lmstudio_models_mlx-community_DeepSeek-V4-Flash-2bit-DQ_20260529_121622_results.json`](../tools/local-llm-bench-m4-32gb/results/speed_probe/)

### 3.3 Run #3 — patched v1 (chunk=8 over n_heads), jdhodges restart

- **Patch:** [`patches/mlx-lm-deepseek-v4-indexer-chunk.patch`](../patches/mlx-lm-deepseek-v4-indexer-chunk.patch) at v1 (chunk=8, `mx.eval(scores)` between chunks)
- **Bench:** `tool_call_bench.py --suite jdhodges --force`
- **Result:** got to case 8 cleanly; bench then killed at ~40 min by Claude Code harness wall-clock limit; would have continued degrading
- **Throughput:** 12-16 t/s (vs 22-29 t/s un-patched cold) — chunking added ~2× overhead per indexer call
- **Metal OOMs:** **3** (at server stack — cases 9-11 area)
- **Bench log:** `.bench-logs/toolcall-jdhodges-deepseek-v4-flash-patched.log`

### 3.4 Run #4 — patched v2 (chunk=2 + `mx.clear_cache()`), jdhodges restart

- **Patch:** [`patches/mlx-lm-deepseek-v4-indexer-chunk.patch`](../patches/mlx-lm-deepseek-v4-indexer-chunk.patch) at v2 (chunk=2, `mx.clear_cache()` after each `mx.eval`)
- **Bench:** `tool_call_bench.py --suite jdhodges --force` via detached driver (PPID=1)
- **Result:** got to case 8 cleanly; case 9 (`arg_weather_units_celsius`) hung 23.5 min waiting for OOM-aborted response; case 10 errored fast on a wedged server
- **Throughput:** 6-7 t/s (chunk=2 doubled the per-indexer overhead vs chunk=8)
- **Metal OOMs:** **8** (one in our chunked indexer at `mx.eval(scores)`, **three in `mx.random.seed`**, rest scattered)
- **Bench log:** `.bench-logs/toolcall-jdhodges-deepseek-v4-flash-patched-v2.log`
- **Server log:** `.bench-logs/mlx-server-deepseek-v4-patched-v2.log`

**Surprising finding:** patched-v2 was **not meaningfully better than v1**. Same fail point (case 8-9 boundary). The chunked indexer is necessary but not sufficient — the resource exhaustion has migrated to other parts of the forward pass and to server bookkeeping ops.

### 3.5 Run #5 — restart-per-batch wrapper (3 of 5 batches ran, then stopped)

- **Approach:** kill + restart `mlx_lm.server` between each batch of 8 cases; 5 batches total
- **Driver:** [`.bench-logs/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh`](../.bench-logs/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh)
- **Status:** stopped after 3 of 5 batches when results made it clear the wrapper isn't sufficient as a fix.

**Per-batch breakdown:**

| Batch | Category | Score | Wall-clock | Server log Metal errors at end | Failure mode |
|---|---|---|---|---|---|
| 1 | `sel_*` (8 short-prompt selection cases, p≈74-105 tok) | 0/8 (all prose, no tool calls) | 8.7 min | 0 | **Clean** — model produced coherent responses, just doesn't tool-call |
| 2 | `arg_*` (8 argument-accuracy cases, longer prompts) | 0/8 | 32.9 min | ~16 | Mostly `Connection error` mid-batch |
| 3 | `multi_*` (8 multi-tool cases, longest prompts) | 0/8 (2 prose, 6 errors) | 33.4 min | ~26 | 2 cases ran clean, case 3 timed out at 30 min, rest wedged |
| 4 | `edge_*` | (not run) | — | — | — |
| 5 | `fmt_*` | (not run) | — | — | — |

**Cumulative:** 42 Metal OOMs across 3 fresh-server batches. Server warm-up was 14-20 s per restart (OS page cache stays hot when the model isn't fully evicted between restarts).

**The key finding:** the restart-per-batch wrapper helps batches with **short prompts** (`sel_*` ran clean — proves the wrapper *can* prevent cross-request accumulation). It does **not** help batches with longer prompts (`arg_*`, `multi_*` failed within the batch even on a fresh server). This is direct evidence that **single-request OOMs are a real failure mode independent of cache accumulation** — a single prompt with enough cached/processed context blows the 499 000 resource cap by itself.

**Implication for the fix plan:** H1 (per-layer eval boundaries in the model forward pass) becomes the highest-leverage single fix, because it's the only hypothesis that bounds resource count *within* a single forward pass. H4 (`--prompt-cache-size 1`) addresses cross-request accumulation only and wouldn't have saved the `arg_*` or `multi_*` batches.

- **Bench logs:** `.bench-logs/jdhodges-restart-loop-{driver,bench,server}.log`
- **Partial summaries:** `tools/local-llm-bench-m4-32gb/benchmarks/runs/toolcall_{sel,arg,multi}_jdhodges_*_summary.json`

### 3.6 Side-finding (independent of OOM): no tool-calling

For every request, the server log emits:

```
WARNING - Received tools but model does not support tool calling.
If you think this is an error, file an issue here:
https://github.com/ml-explore/mlx-lm/issues
```

Consistent with the inventory in [`docs/testing-plan.md:54`](testing-plan.md) marking `deepseek-v4-flash-dq` as **Tools: —**. Even with the OOM fixed, the 2-bit DQ checkpoint isn't a tool-calling fine-tune — only the `edge_cases` jdhodges category (where the correct answer is prose) would pass.

This is orthogonal to the Metal OOM but worth recording: a "fix" to the runtime won't help tool-call scores meaningfully. For agentic workflows on this rig, `qwen/qwen3-coder-next` remains the right slot.

### 3.7 Run #6 — root-cause session (2026-05-30): H1 test + capture + leak/ablation probes

The decisive session. Switched from request-level bench probes to a streaming forced-generation probe and direct residency instrumentation. Full detail in [`docs/deepseek-v4-flash-metal-oom-fix-plan.md`](deepseek-v4-flash-metal-oom-fix-plan.md) Phase 0.3 + Step 1 + Phase 1.5.

- **Calibration:** un-patched server, forced generation from a 58-token prompt OOMs at **11,314 tokens** (`metal::malloc` at a decode step). Single 60K-context forward pass: clean. → trigger is decode-step count, not context length.
- **H1 (per-layer `mx.eval`+`mx.clear_cache` every 10 layers): FAIL.** OOM at ~11,300 tokens (= baseline), fired *inside our own* `mx.eval(h)`. No improvement. Rolled back.
- **Metal capture:** `mx.metal.start_capture` (needs `MTL_CAPTURE_ENABLED=1`) around 2 decode steps → **90 GB** `.gputrace` (resident weights dominate). Capture is not viable for a model this size.
- **Residency instrumentation** ([`.bench-logs/leak_probe.py`](../.bench-logs/leak_probe.py)): linear ~166–200 KB/step active-memory growth, no plateau to 2000 steps; ~1 buffer/layer/step; ruled out generic MLX, `mx.compile`, RoPE, cache bytes, expert paging (see §2.2/§2.4).
- **Ablation** ([`.bench-logs/ablation_probe.py`](../.bench-logs/ablation_probe.py), [`.bench-logs/inner_ablation_probe.py`](../.bench-logs/inner_ablation_probe.py)): leak is in attention; **~83% compressor/indexer**, ~17% core attention (§2.4 table).

**Net:** the original hypothesis set (single-forward-pass resource explosion, fixable by chunking / eval boundaries) is disproved; the real bug is a per-decode-step live-buffer leak in the compressor/indexer. New hypothesis = H7 (§5).

---

## 4. External signals

### 4.1 mlx-lm PR #1192 — current state (queried 2026-05-29)

- **URL:** https://github.com/ml-explore/mlx-lm/pull/1192
- **Title:** "Add DeepSeek-v4 (Flash/Pro)"
- **Author:** [Blaizzy](https://github.com/Blaizzy) (Prince Canuma)
- **State:** OPEN, `REVIEW_REQUIRED`, not merged
- **Created:** 2026-04-24
- **Last commit:** 2026-05-01 — **stalled for ~4 weeks at time of writing**
- **Last comment:** 2026-05-19 (bojiang sanitize gap)
- **Size:** +2192 / -2 across 6 files
- **No labels assigned**

### 4.2 Community testers (PR thread)

Most relevant signals from the PR comments (in chronological order):

#### 2026-05-08 — ivaniguarans (M5 Max 128 GB)
Tested branch by requantizing DeepSeek-V4-Flash from FP8 source to lower-precision affine (2-3 bpp) via `mlx_lm.convert`. Reported that `sanitize` in `Model.sanitize()` correctly converts FP8 weights but has gaps elsewhere.

#### 2026-05-10 — spicyneuron
> "I did several rounds of brute force Codex / Opus comparisons between this branch vs transformers and vLLM implementations. … I'm testing out rough fixes on my own server to see if it helps with the looping / long context issues."

- Their fork with proposed fixes: **[spicyneuron/mlx-lm@fix-ds4](https://github.com/spicyneuron/mlx-lm/tree/fix-ds4)**
- This is direct evidence that the issue is broader than one user's setup.

#### 2026-05-11 — spicyneuron (the key data point)
> "Superseding my previous comment on model looping, I've isolated a script that reliably reproduces the issue at ~4000 tokens on my Mac Studio M3. Could someone else try it?"

- **Reproducer gist:** https://gist.github.com/spicyneuron/deeb395b2f2f7d5c97a6ab2590b72cb5
- **"~4000 tokens"** matches our hypothesis: `pooled_seq` growing past a threshold trips the resource cap, manifesting as "model looping" because Metal returns garbage / partial outputs when the indexer aborts.
- Tested on **Mac Studio M3** — confirms it's not M4-specific. Likely affects all current Apple Silicon classes.

#### 2026-05-14 — kidroca
Confirmed the reproducer on another machine. Strengthens reproducibility evidence.

#### 2026-05-19 — bojiang
Flagged that the mlx-community DeepSeek-V4-Flash conversions (`mlx-community/deepseek-ai-DeepSeek-V4-Flash-{2,3,4,6,8}bit` and `-fp16`, all uploaded 2026-04-24/25) ship weights in a format the current `sanitize` doesn't recognize. Two specific gaps observed on a 4-bit load. Documented in [`docs/deepseek-v4-flash-setup.md`](deepseek-v4-flash-setup.md) §"Known risks".

### 4.3 Recent commit activity (mlx-lm PR #1192)

All from a 2026-05-01 burst; no commits since:

- 2026-05-01 11:36 — Fix tensor parallel distributed
- 2026-05-01 10:04 — Fix batch cache edge case
- 2026-05-01 09:13 — Add hyper_connection.py
- 2026-05-01 09:07 — Simplify HyperConnection
- 2026-05-01 00:01 — Major cache refactor and attention simplification

**Implication:** the PR is functionally abandoned (no maintainer response in ~4 weeks) despite multiple community testers reporting reliability issues. Most likely paths forward are (a) PR author returns, (b) someone else picks it up, or (c) a successor PR (potentially spicyneuron's fork).

### 4.4 Related infrastructure docs

- **Setup guide:** [`docs/deepseek-v4-flash-setup.md`](deepseek-v4-flash-setup.md) — patched venv, config.json int→float patch, server launch
- **Benchmark plan & post-mortem:** [`docs/benchmark-plans/2026-05-29-deepseek-v4-flash-phase-3.md`](benchmark-plans/2026-05-29-deepseek-v4-flash-phase-3.md)
- **Phase 3 #10 section in M4 notes:** [`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`](../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)
- **Existing carried patches:**
  - [`patches/mlx-lm-find-negative-start.patch`](../patches/mlx-lm-find-negative-start.patch) — unrelated 404 fix
  - [`patches/mlx-lm-deepseek-v4-indexer-chunk.patch`](../patches/mlx-lm-deepseek-v4-indexer-chunk.patch) — our chunking attempt (v2)

---

## 5. Hypotheses, ranked

> **2026-05-30 update:** H7 below is the current leading hypothesis and supersedes H1–H6. H1 was **tested and FAILED**; H2–H4 are invalidated by the corrected mechanism (§2: the cap counts *live* buffers, so barriers/chunking/cache-size cannot help); H6 is an orthogonal long-shot. H1–H6 are retained verbatim for the record but **do not act on them** — see Phase 1.5 in the fix-plan doc for why each is dead.

### H7. The compressor/indexer retains ~1 live Metal buffer per layer per decode step (current leading hypothesis, 2026-05-30)
**Confidence: high (mechanism + localization both measured).**

**Reasoning:** §2.2/§2.4. The OOM is a *live-resident-buffer count* cap (499000), reached by an unbounded per-decode-step leak of ~1 buffer/layer/step, localized by ablation to the compressor+indexer (~83%) with a smaller core-attention residual (~17%). Something in `Compressor.__call__` / `Indexer.__call__` (or the `PoolingCache` update path) allocates a buffer each step that stays referenced (not freed, not cached) — `mx.clear_cache`/`mx.eval` provably don't reclaim it.

**Experiments (cheap → authoritative), see fix-plan Phase 2-revised:**
1. Count live `mlx.core.array` objects via `gc` per decode step — confirms count growth and may name the retained tensor by shape. (~5 min)
2. Force-eval cache state each step (`mx.eval(*tree_flatten(c.state))`) — if the slope drops, it's an un-evaluated lazy graph held by `PoolingCache`; that is both the mechanism *and* a candidate fix. (~5 min)
3. Split compressor vs indexer by ablation to divide the 83%. (~2 min)
4. Diff [spicyneuron/mlx-lm@fix-ds4](https://github.com/spicyneuron/mlx-lm/tree/fix-ds4) + try a newer mlx/mlx-lm — may already be fixed upstream.
5. C++ allocator instrumentation (log `num_resources_` / `ResidencySet::insert` size + backtrace) — authoritative line-level answer; requires building MLX from source.

**Win condition:** a change (likely in `PoolingCache`/`Indexer`, or forcing per-step cache materialization) that flattens the `leak_probe.py` slope to ~0 and lets the forced-generation probe reach 20K tokens clean.

---

### H1. The whole forward pass is one Metal command buffer; chunking the indexer is necessary but not sufficient — we need per-LAYER eval boundaries too
**Confidence: high.** — **SUPERSEDED 2026-05-30: TESTED, FAILED.** Per-layer `mx.eval`+`mx.clear_cache` every 10 layers gave zero improvement (OOM at the same ~11,300 tokens, inside our own eval). Live buffers can't be cleared. See fix-plan Step 1.

**Reasoning:** Best explanation for the `mx.random.seed` failure and the device wedge. MLX uses lazy evaluation — the model's `__call__` builds a graph spanning all ~60 layers. Even with indexer chunking, the whole-forward-pass dependencies likely fuse into one Metal command buffer at the final eval. 1800+ MLX ops × multiple resources each = easily 500K resources when prompt cache adds buffer references.

**Experiment:** add `mx.eval(h); mx.clear_cache()` (or `mx.synchronize()`) inside the layer loop in [`mlx_lm/models/deepseek_v4.py:983-987`](https://github.com/ml-explore/mlx-lm/pull/1192/files) every N layers (start with N=10). Should bound cumulative resource count regardless of how big any one indexer call gets.

**Cost to test:** ~5 lines, restart server, rerun jdhodges. ~30 min wall-clock.

**Risk:** per-layer eval overhead could hurt throughput meaningfully. May need to tune N.

### H2. `mx.eval()` doesn't actually create a Metal command-buffer boundary — only `mx.synchronize()` does
**Confidence: medium-high.**

**Reasoning:** Would explain why chunk=2 helped surprisingly little (Run #4 ≈ Run #3 fail point). `mx.eval()` triggers evaluation but the docs suggest it may still batch into ongoing command buffer submissions. `mx.synchronize()` is documented as "wait for all pending work to complete" — that's a true barrier.

**Experiment:** replace `mx.eval(scores)` with `mx.synchronize()` inside our chunked indexer (one-line edit). If chunk=8 + synchronize beats chunk=2 + eval, this is the real lever.

**Cost to test:** 1-line edit + restart + rerun. ~30 min.

### H3. Chunking over `pooled_seq` is more targeted than chunking over `n_heads`
**Confidence: medium.**

**Reasoning:** `pooled_seq` is the dimension that grows unboundedly with cache; `n_heads=64` is fixed. The intermediate is `(B, n_heads=64, L, pooled_seq)`. With chunk_n_heads=2 we get 32 chunks of `(B, 2, L, pooled_seq)`. If pooled_seq goes from 100 (cold) to 4000 (warm), each chunk grows 40×. Chunking pooled_seq into 200-element slices would give 20 chunks of `(B, 64, L, 200)` — bounded regardless of cache size.

**The math works cleanly here:** unlike attention with softmax (needs online softmax for K-dim chunking), the indexer is `relu(q @ K) * scale * weights`, then sum over heads — both reductions are over the FIXED-size n_heads dim. We can chunk the K dim and just concatenate the score slices, then top-k at the end.

**Experiment:** rewrite the indexer to chunk pooled_seq instead of (or in addition to) n_heads.

**Cost to test:** ~30 lines, careful indexing. ~1-2 hours.

### H4. Per-layer KV cache fragmentation: the LRU prompt cache stores per-layer per-sequence buffers separately; resource count scales with `n_layers × n_cached_sequences`
**Confidence: medium.**

**Reasoning:** Would explain why N-cases-then-fail scales with cached sequence count, not just total bytes. If each cached sequence registers ~60 layers × 2 cache buffers = 120 distinct Metal resources, then 10 cached sequences = 1200 resources just from cache references. Plus the active forward pass's resources, approaching cap. Adding one more cached sequence might tip past.

**Experiment:** flip `--prompt-cache-size 1` on the server flags (already a built-in CLI option — see `mlx_lm.server --help`). No code change. If this alone fixes the OOM, cache fragmentation hypothesis wins.

**Cost to test:** Trivial — just a server flag. ~20 min including warm-up + smoke chat.

### H5. `--prompt-concurrency > 1` lets requests stack resources additively
**Confidence: low.**

**Reasoning:** Default is probably already 1, but worth verifying. If two requests' graphs are queued into the same Metal command queue, resource counts add. Setting `--prompt-concurrency 1` would serialize them.

**Experiment:** `mlx_lm.server --prompt-concurrency 1`.

**Cost to test:** Trivial. ~20 min.

### H6. The 2-bit DQ checkpoint's `sanitize` shape gaps (bojiang's May 19 comment) leave dangling weight buffers that never get freed
**Confidence: low-medium.**

**Reasoning:** Bojiang flagged sanitize gaps on the PR thread. Could be unrelated to our OOM but worth noting — if sanitize leaves stale weight references in Metal's resource accounting, every forward pass starts already partway to the cap.

**Experiment:** try a different quant (4-bit or 6-bit from the same `mlx-community/deepseek-ai-DeepSeek-V4-Flash-*bit` family) — if those don't OOM, sanitize is a contributor. If they do OOM the same way, sanitize isn't the issue.

**Cost to test:** Several hours (4-bit is ~145 GB download, 6-bit ~200 GB).

---

## 6. Recommended sequencing for next investigation pass

> **2026-05-30:** the old H4→H2→H1→H3→H6 table is obsolete (all dead, §5). The current plan pursues **H7** (per-step live-buffer leak in compressor/indexer). Detailed apply/test/pass steps live in [`docs/deepseek-v4-flash-metal-oom-fix-plan.md`](deepseek-v4-flash-metal-oom-fix-plan.md) **Phase 2-revised**. Summary, cheap-first:

| Order | Step | Edit | Cost | Win condition |
|---|---|---|---|---|
| 1 | Count live `mx.array` objects per step (`gc`) | New probe | ~5 min | count climbs ~44/step; retained arrays' shapes identify the tensor |
| 2 | Force-eval cache state per step | ~2 lines in probe | ~5 min | slope → ~0 ⇒ lazy-graph retention in `PoolingCache` (mechanism + candidate fix) |
| 3 | Split compressor vs indexer by ablation | Probe edit | ~2 min | divides the 83% to one sub-module |
| 4 | Diff spicyneuron `fix-ds4` + try newer mlx/mlx-lm | None | ~30 min | upstream may already fix it ⇒ beat any local patch |
| 5 | C++ allocator instrumentation (backtrace on residency insert) | Build MLX from source | hours | names the exact allocating line (authoritative) |

**The fix we'd likely end up submitting upstream** is no longer "chunk + eval boundaries". Based on H7 it is one of:
- A `PoolingCache` / `Indexer` change that stops retaining a live buffer per step (e.g., materialize/consolidate per-step state so the residency count stays bounded), **or**
- Forcing per-step materialization of the compressor/indexer cache state in the generation loop, **or**
- An upstream MLX residency-set fix if the retention turns out to be in the allocator's handling of the specific op pattern.

Document the winning change against PR #1192 with [`leak_probe.py`](../.bench-logs/leak_probe.py) as the minimal reproducer (linear residency growth, count-cap OOM at ~11.3K decode steps, prompt-independent).

**Definition of done.** A fix qualifies as "this model is now daily-usable" when **all three** hold:

1. The bench sweep in [`docs/benchmark-plans/2026-05-29-deepseek-v4-flash-phase-3.md`](benchmark-plans/2026-05-29-deepseek-v4-flash-phase-3.md) completes on a **single long-lived** `mlx_lm.server` process with **zero Metal OOMs** in the server log (no restart-per-batch wrapper, no manual intervention).
2. Spicyneuron's [4000-token reproducer gist](https://gist.github.com/spicyneuron/deeb395b2f2f7d5c97a6ab2590b72cb5) runs to completion without looping or hanging.
3. A 30-turn chat session in Open WebUI (per [the setup-guide workflow](deepseek-v4-flash-setup.md)) completes without the user noticing degradation, repetition, or needing to restart anything.

If only (1) holds via the operational wrapper, that's the current state — **the model is bench-able but not daily-usable.** Bench numbers from a restart-per-batch sweep are valid as quality measurements; they just don't demonstrate the runtime is production-grade.

**Note on the tool-calling caveat.** Independent of the OOM, the 2-bit DQ checkpoint isn't a tool-calling fine-tune — `Tools: —` in the inventory; the server emits `WARNING - model does not support tool calling` for every request. That means even after the OOM is fully fixed, this model won't be the right pick for **agentic** daily workflows (OpenCode / Cline / Aider). Its daily-driver slot is **chat / research / long-context reasoning**, where `qwen3.6-27b`'s ~20 t/s ceiling is the bar to beat. DeepSeek V4 Flash's faster MoE inference (13 B active) is the reason we're chasing this fix at all.

---

## 7. Operational workaround in use now (NOT the daily-driver target)

While the investigation continues, the **restart-per-batch wrapper** lets us produce benchmark numbers, but **it is not the daily-driver experience we're aiming for** — it's a stop-gap that keeps the bench harness moving until the root cause is fixed.

- Driver: [`.bench-logs/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh`](../.bench-logs/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh)
- Pattern: kill + restart `mlx_lm.server` between every batch of N cases (currently N=8)
- Cost: ~5 min/restart (96 GB cold load), or ~20 s with hot OS page cache
- Per-batch JSONLs need to be merged into a canonical summary after all batches complete

The same pattern (manual server restart before any heavy session, restart-on-symptom recovery) is what a daily user would have to apply today — and that's exactly what we're trying to make unnecessary. A real fix means **no wrapper, no manual restart, no babysitting**: launch the server once, use it for the day.

---

## 8. Links (for the next person)

### This repo
- Phase 3 #10 benchmark plan + post-mortem: [`docs/benchmark-plans/2026-05-29-deepseek-v4-flash-phase-3.md`](benchmark-plans/2026-05-29-deepseek-v4-flash-phase-3.md)
- Setup guide (patched venv, config patch): [`docs/deepseek-v4-flash-setup.md`](deepseek-v4-flash-setup.md)
- Master testing plan (Phase 3 #10 status): [`docs/testing-plan.md`](testing-plan.md#step-e--phase-3-fit-test-for-deepseek-v4-flash-dq--blocked-2026-05-29)
- Phase 3 #10 outcome section: [`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`](../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)
- Carried patches: [`patches/`](../patches/)
- Bench / server logs: [`.bench-logs/*deepseek-v4*`](../.bench-logs/)
- Restart-loop driver: [`.bench-logs/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh`](../.bench-logs/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh)

### Upstream
- **mlx-lm PR #1192** (DeepSeek V4 architecture port): https://github.com/ml-explore/mlx-lm/pull/1192
- **spicyneuron/mlx-lm@fix-ds4** (community fork with proposed fixes): https://github.com/spicyneuron/mlx-lm/tree/fix-ds4
- **spicyneuron's reproducer gist** (model looping at ~4000 tokens on M3): https://gist.github.com/spicyneuron/deeb395b2f2f7d5c97a6ab2590b72cb5
- **MLX core repo** (Metal backend): https://github.com/ml-explore/mlx
- **MLX `mx.metal` API** (limit knobs, `device_info`): https://ml-explore.github.io/mlx/build/html/python/metal.html

### Related
- DeepSeek V4 paper (architecture / MLA): https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash
- mlx-community quantized conversions: https://huggingface.co/mlx-community?search_models=DeepSeek-V4
- Apple Metal documentation (resource limits, command buffers): https://developer.apple.com/documentation/metal/mtldevice

---

## 9. Open questions

Updated 2026-05-30. Several originals are now answered:

1. ~~What's the actual resource count per forward pass?~~ **Partially answered:** it's a *live-resident-buffer count* cap (499000), and the leak is ~1 buffer/layer/step (~166–200 KB/step, no plateau). The *exact* per-step allocation site still needs C++ allocator instrumentation (no Python buffer-count getter; `start_capture` gives a 90 GB trace dominated by weights).
2. ~~Does `--prompt-cache-size 1` survive the reproducer?~~ **Moot:** the OOM is decode-step driven, not cache-length driven (a 58-token prompt OOMs after ~11,300 generated tokens). Cross-request cache size is irrelevant to a single long generation.
3. **Did spicyneuron's `fix-ds4` fork solve it?** Still open — now elevated to a primary next step (diff its compressor/indexer/cache against PR #1192). Could short-circuit the fix.
4. ~~Is `mx.eval` a command-buffer boundary?~~ **Answered/moot:** `mx.eval` does force evaluation, but the cap counts *live* buffers, so a boundary doesn't lower it (H1 proved this empirically).
5. **Do other quants OOM the same way?** Still open, low priority — the leak is per-layer-per-step and architecture-driven, so quant is unlikely to change it (old H6).
6. **Is the wedge state recoverable without a process restart?** Still open — no known MLX device-reset API.

**The sharp remaining question:** *which* allocation in `Compressor.__call__` / `Indexer.__call__` / `PoolingCache` is retained each step, and what holds the reference? §6 steps 1–2 (gc array count + force-eval cache) should answer this without a source build.
