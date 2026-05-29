# DeepSeek V4 Flash on Apple Silicon — Metal `resource_limit` OOM investigation

**Goal:** make `deepseek-v4-flash-dq` reliable as a **daily-driver model** on this rig — sustained multi-hour chat / research / long-context sessions without restarts, hangs, or repetition. Benchmarks are a means to that end (a bench sweep is a useful stress test that proves daily reliability), not the goal itself.

**Status (2026-05-29):** mlx-lm PR #1192's DeepSeek V4 port hits Apple Metal's per-command-buffer `resource_limit: 499000` cap once the prompt cache warms. **Today the model is not daily-reliable**: it works for a single fresh session but degrades within ~10-20 requests or ~4000-token prompts, eventually wedging the server into a state only recoverable by a full process restart. Indexer chunking helps but doesn't fully solve it — the resource exhaustion is broader than a single layer. Investigation ongoing; restart-per-N operational wrapper is the current stop-gap.

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

`resource_limit` is the per-command-buffer count of MTLBuffer / MTLTexture / MTLSampler resources that a single submission can reference. **It's a count, not a byte size**, and it's fixed by the device class — `set_memory_limit`, `set_wired_limit`, `set_cache_limit` (all byte-budget knobs) don't affect it. Verified by inspecting `mx.metal.*` API and by trying small `--prompt-cache-bytes` values without effect.

### 2.2 Why DeepSeek V4 hits it (other models don't)

DeepSeek V4 introduces **Multi-head Latent Attention (MLA)** with an additional `Indexer` component that selects top-k cached positions per query. Per `Indexer.__call__` in [`mlx_lm/models/deepseek_v4.py:524-568`](https://github.com/ml-explore/mlx-lm/pull/1192/files):

```python
# Shapes for this checkpoint (config.json):
#   index_n_heads = 64
#   index_head_dim = 128
#   index_topk = 512
scores = q.astype(mx.float32) @ pooled[:, None].swapaxes(-1, -2).astype(mx.float32)
#   → (B, n_heads=64, L, pooled_seq)
scores = mx.maximum(scores, 0) * self.scale
weights = self.weights_proj(x).astype(mx.float32) * (self.n_heads**-0.5)
scores = (scores * weights.swapaxes(-1, -2)[..., None]).sum(axis=1)
#   → (B, L, pooled_seq)
```

Two compounding factors:

1. **`pooled_seq` grows unboundedly** with the cached prefix. For a fresh request it's small; after a few cached sequences it climbs into the thousands.
2. **The `n_heads × pooled_seq` intermediate** is created in a single un-chunked op chain. With 64 heads and pooled_seq=4000, a single forward pass through this single layer already references many Metal resources — and the model has ~60 such layers.

By contrast, Qwen 3.6 / Qwen3-Coder-Next / Gemma 4 all use standard MHA or GQA attention. There's no Indexer-equivalent component, and their per-layer intermediates are an order of magnitude smaller in resource count. None of them have ever tripped this cap on the same rig.

### 2.3 Why even `mx.random.seed` fails after the first OOM

Once a Metal command buffer fails to submit, the device's command queue appears to enter a partially-broken state. Subsequent submissions inherit corrupted state until a full reset. There's no MLX API documented for explicit device reset short of a process restart.

This explains why "restart-per-N-requests" is the only robust recovery path — the wedge isn't local to the request that errored.

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

Ordered by (confidence × leverage), with the cheapest experiment to confirm/refute each.

### H1. The whole forward pass is one Metal command buffer; chunking the indexer is necessary but not sufficient — we need per-LAYER eval boundaries too
**Confidence: high.**

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

Cheap-first, ordered by likelihood of being THE fix:

| Order | Hypothesis | Edit | Cost | Win condition |
|---|---|---|---|---|
| 1 | **H4** | None (server flag) | 20 min | `--prompt-cache-size 1` survives a 20+ request session with 0 OOMs |
| 2 | **H2** | One-line patch edit | 30 min | chunk=8 + `mx.synchronize()` (instead of `mx.eval`) survives where chunk=2 + `mx.eval()` didn't |
| 3 | **H1** | Per-N-layer eval in model `__call__` | 1 h | survives 30+ requests on a single server |
| 4 | **H3** | Add pooled_seq chunking to indexer | 1-2 h | survives 50+ requests regardless of cache state |
| 5 | **H6** | Test different quant | hours | rules in/out sanitize gap |

**The combined patch we'd likely end up submitting upstream** (if all of 1-4 contribute):
- Chunk indexer over both `n_heads` AND `pooled_seq`
- Use `mx.synchronize()` between chunks (not just `mx.eval()`)
- Add per-N-layer eval boundaries in the model forward
- Document `--prompt-cache-size 1` as recommended for Apple Silicon

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

Things we don't yet know that would sharpen the hypotheses:

1. **What's the actual resource count per forward pass?** If we could instrument MLX to count buffers per `mx.eval`, we'd know exactly where the budget goes. May require a debug build of MLX or `mx.metal.start_capture` introspection.
2. **Does `--prompt-cache-size 1` survive the 4000-token spicyneuron reproducer?** That would tell us if cache fragmentation is the trigger or just an amplifier.
3. **Did spicyneuron's fork solve the looping issue?** Worth diffing against PR #1192 head to see what they tried — could short-circuit half our hypothesis ladder.
4. **Is `mx.eval` actually a command-buffer boundary?** Reading MLX's scheduler source would confirm H2 cheaply.
5. **Do the 4-bit / 6-bit / 8-bit checkpoints OOM the same way?** Rules sanitize gaps (H6) in or out.
6. **Is the wedge state truly unrecoverable without a process restart?** If there's an MLX API to fully reset the Metal device state, the recovery story is much cleaner.
