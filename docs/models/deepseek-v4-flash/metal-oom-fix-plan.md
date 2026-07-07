# DeepSeek V4 Flash Metal OOM — fix-application plan

> Model card: [deepseek-v4-flash](README.md)


> **CURRENT PLAN (2026-05-30): see [Phase 2-revised](#phase-2-revised--fix-plan-for-the-per-step-residency-leak-hypothesis-h7).**
> Phase 0 + Phase 1 + Phase 1.5 are complete and establish the root cause: an unbounded
> per-decode-step leak of ~1 live Metal buffer per layer, localized to the compressor +
> indexer. **The original Phase 1 hypothesis ladder (H1–H6) is dead** — H1 was tested and
> failed; H2–H4 are invalidated by the live-buffer-*count* mechanism (Phase 1.5). Read
> Phase 1.5 (in the Results log) for the evidence, then Phase 2-revised for the fix steps.
> The H1–H6 material below is retained verbatim as a record of the wrong turn.

**Goal:** make `deepseek-v4-flash-dq` meet the daily-driver bar (§"Definition of done" in [`docs/deepseek-v4-flash-metal-oom-investigation.md`](metal-oom-investigation.md)). The original framing — "apply the investigation doc's hypotheses in confidence order" — held until 2026-05-30; the work then pivoted to the per-step residency-leak hypothesis (H7) once H1 failed.

**Done bar (carried from investigation doc §6):**
1. Phase 3 #10 bench sweep runs on a **single long-lived** `mlx_lm.server` process with **zero Metal OOMs** (no restart-per-batch wrapper).
2. [Spicyneuron's 4000-token reproducer gist](https://gist.github.com/spicyneuron/deeb395b2f2f7d5c97a6ab2590b72cb5) runs to completion without looping/hanging.
3. A 30-turn Open WebUI chat session completes without manual restart.

We attack these in order: get (2) green (cheap fast signal), then (1), then (3).

---

## Phase 0 — Build the fast feedback signal

**Why first:** every hypothesis test needs the same probe. Set this up once.

### 0.1 Capture spicyneuron's reproducer locally

```bash
cd /Users/vitor/LocalProjects/local-llms/bench/deepseek-v4-flash/scripts
curl -sSL https://gist.githubusercontent.com/spicyneuron/deeb395b2f2f7d5c97a6ab2590b72cb5/raw \
  -o spicyneuron-deepseek-v4-reproducer.py
# Sanity: print the first 30 lines to confirm we got something runnable
head -30 spicyneuron-deepseek-v4-reproducer.py
```

If the gist is a single-file Python script, save as `repro_spicyneuron.py` in the same dir. If it's bash + python, save both pieces.

### 0.2 Write our own minimal reproducer (independent of the gist)

A small Python that hits `/v1/chat/completions` 25 times in a row against the same server, growing the per-request context, and reports first-error case. Saves us from depending on the gist being available.

Save at [`bench/deepseek-v4-flash/scripts/repro_oom_minimal.py`](../../../bench/deepseek-v4-flash/scripts/repro_oom_minimal.py):

```python
"""Minimal OOM reproducer — hit the server 25 times, log first failure."""
import json, sys, time, urllib.request
BASE = "http://127.0.0.1:8765/v1"
MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
PROMPTS = [f"Tell me an interesting fact about the number {i}." for i in range(25)]
for i, p in enumerate(PROMPTS, 1):
    payload = json.dumps({"model": MODEL, "messages": [{"role":"user","content": p}],
                          "max_tokens": 256, "temperature": 0.0}).encode()
    req = urllib.request.Request(f"{BASE}/chat/completions", data=payload,
                                 headers={"Content-Type":"application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.loads(r.read())
        dt = time.time() - t0
        toks = d["usage"]["completion_tokens"]
        print(f"{i:2d}/25  {dt:6.1f}s  {toks:4d}tok  OK")
    except Exception as e:
        dt = time.time() - t0
        print(f"{i:2d}/25  {dt:6.1f}s  FAIL  {type(e).__name__}: {e}")
        sys.exit(1)
print("REPRO_CLEAN: all 25 requests succeeded")
```

### 0.3 Calibrate baseline (un-patched, before any hypothesis applied)

This is the **known-bad** reference. The repro must FAIL on this run to confirm the test is sensitive.

```bash
# Restart server fresh (current state: chunk=2 patched; revert deepseek_v4.py first
# via the patch -R flow, or use git to restore the venv file)
cd /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/lib/python3.12/site-packages
patch -R -p0 < /Users/vitor/LocalProjects/local-llms/fixes/mlx-lm/mlx-lm-deepseek-v4-indexer-chunk.patch
# Kill any running server
pkill -f mlx_lm.server; sleep 3
# Launch fresh
cd /Users/vitor/LocalProjects/local-llms
nohup /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/bin/python \
  -m mlx_lm.server --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --host 0.0.0.0 --port 8765 --max-tokens 65536 --temp 0.0 \
  >> bench/deepseek-v4-flash/logs/server-baseline.log 2>&1 & disown
# Warm-load
curl -sS -m 360 http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ",
       "messages":[{"role":"user","content":"hi"}],"max_tokens":4}' >/dev/null
# Run the minimal reproducer
python3 bench/deepseek-v4-flash/scripts/repro_oom_minimal.py | tee bench/deepseek-v4-flash/logs/repro-baseline.log
# Count Metal errors in server log
grep -c 'metal::malloc' bench/deepseek-v4-flash/logs/server-baseline.log
```

**Calibration pass criterion:**
- Minimal reproducer FAILS (any request errors or hangs > 30 s — NOT clean 25/25)
- Server log shows ≥ 1 `metal::malloc` error
- (Optional, more authoritative) Spicyneuron reproducer reproduces looping behavior

If the minimal reproducer passes 25/25 clean on the unpatched runtime, the test isn't sensitive enough — **widen it** (more prompts, longer prompts, faster cadence) before continuing to Phase 1.

---

## Phase 1 — Apply hypotheses in confidence order

Each step is **independent** (apply alone against a clean unpatched baseline; don't stack with prior steps unless the "combine" subsection at the end tells you to). Each step has the same shape:

1. **Hypothesis.** Restate.
2. **Exact change.** File / line / new code.
3. **Apply.** Commands to roll it in.
4. **Test.** Reproducer + extended probe.
5. **Pass criterion** → on green, advance to "combine"; on red, advance to next step.
6. **Roll-back.** How to undo before applying the next step.

### Step 1 — H1: per-layer `mx.eval` + `mx.clear_cache` in the model forward pass

**Confidence: high.** Best single-step explanation for the device wedge — once any forward pass exceeds 499 000 resources, the whole device gets stuck because there are no intermediate command-buffer boundaries.

#### 1.1 Exact change

File: `venvs/mlx-v4-flash/lib/python3.12/site-packages/mlx_lm/models/deepseek_v4.py`

In `class DeepseekV4Model` (~line 970), method `__call__`, insert eval/clear every 10 layers:

```python
# ORIGINAL (around line 985)
def __call__(self, inputs, cache=None):
    h = self.embed_tokens(inputs)
    mask = create_attention_mask(h, cache[0])
    for i, layer in enumerate(self.layers):
        h = layer(h, mask, cache[i], inputs)
    return self.norm(h)

# PATCHED
def __call__(self, inputs, cache=None):
    h = self.embed_tokens(inputs)
    mask = create_attention_mask(h, cache[0])
    for i, layer in enumerate(self.layers):
        h = layer(h, mask, cache[i], inputs)
        # H1: per-layer Metal command-buffer boundary to keep the
        # cumulative resource count under Apple Silicon's
        # resource_limit=499000. Every 10 layers (~6 boundaries on a
        # 60-layer model). See docs/deepseek-v4-flash-metal-oom-investigation.md H1.
        if (i + 1) % 10 == 0:
            mx.eval(h)
            mx.clear_cache()
    return self.norm(h)
```

(Verify the exact method signature against the current PR #1192 head — line numbers shift as the PR evolves.)

#### 1.2 Apply

```bash
# Make sure the unpatched baseline indexer is restored from Phase 0.3
cd /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/lib/python3.12/site-packages
# Use Edit on mlx_lm/models/deepseek_v4.py as shown above
# (do NOT apply the indexer chunking patch yet — we're isolating H1)
# Save a clean patch file too:
diff -u /tmp/deepseek_v4.py.orig mlx_lm/models/deepseek_v4.py > \
  /Users/vitor/LocalProjects/local-llms/fixes/mlx-lm/mlx-lm-deepseek-v4-per-layer-eval.patch.candidate
```

#### 1.3 Test

```bash
# Restart server cleanly
pkill -f mlx_lm.server; sleep 3
cd /Users/vitor/LocalProjects/local-llms
nohup /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/bin/python -m mlx_lm.server \
  --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --host 0.0.0.0 --port 8765 --max-tokens 65536 --temp 0.0 \
  >> bench/deepseek-v4-flash/logs/server-h1.log 2>&1 & disown
# Warm-load (smoke chat) — must succeed
curl -sS -m 360 ...  # same as Phase 0.3
# Run the minimal reproducer
python3 bench/deepseek-v4-flash/scripts/repro_oom_minimal.py | tee bench/deepseek-v4-flash/logs/repro-h1.log
# Run spicyneuron's reproducer (if captured)
python3 bench/deepseek-v4-flash/scripts/repro_spicyneuron.py | tee bench/deepseek-v4-flash/logs/repro-h1-spicyneuron.log
# Count Metal errors
grep -c 'metal::malloc' bench/deepseek-v4-flash/logs/server-h1.log
# Extended probe: 8-case jdhodges single-server (no restart wrapper)
cd /Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
/Users/vitor/LocalProjects/local-llms/.venv/bin/python scripts/tool_call_bench.py \
  --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --suite jdhodges \
  --base-url http://127.0.0.1:8765/v1 \
  --only sel_weather_portland,sel_currency_usd_eur,sel_timezone_tokyo,sel_web_python_release,sel_reminder_dentist,sel_email_quick,sel_calendar_create,sel_calendar_read_week,arg_weather_units_celsius,arg_currency_jpy \
  --force \
  --run-prefix toolcall_h1 \
  2>&1 | tee /Users/vitor/LocalProjects/local-llms/bench/deepseek-v4-flash/logs/jdhodges-h1.log
```

#### 1.4 Pass criterion

ALL of:
- Minimal reproducer: `REPRO_CLEAN: all 25 requests succeeded` printed.
- Server log (`bench/deepseek-v4-flash/logs/server-h1.log`): **0** `metal::malloc` errors.
- jdhodges 10-case probe: completes all 10 without hanging > 60 s on any case.

If pass → record in §3 "Results", proceed to **§2 Combine winners** with H1 included.
If fail → record in §3, roll back, advance to **Step 2 (H2)**.

#### 1.5 Roll-back

```bash
cd /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/lib/python3.12/site-packages
# Revert the per-layer eval edit via Edit tool, OR:
patch -R -p0 < /Users/vitor/LocalProjects/local-llms/fixes/mlx-lm/mlx-lm-deepseek-v4-per-layer-eval.patch.candidate
```

---

### Step 2 — H2: `mx.synchronize()` instead of `mx.eval()` between indexer chunks

**Confidence: medium-high.** Would explain why chunk=2 helped only marginally over chunk=8 — if `mx.eval()` doesn't create a real command-buffer barrier, our chunking achieved nothing structural. `mx.synchronize()` is the documented "wait for all pending work" barrier.

#### 2.1 Exact change

Reapply our existing indexer chunking patch first, then swap the boundary primitive:

File: `venvs/mlx-v4-flash/lib/python3.12/site-packages/mlx_lm/models/deepseek_v4.py`, in `Indexer.__call__`:

```python
# After applying fixes/mlx-lm/mlx-lm-deepseek-v4-indexer-chunk.patch, change:
            scores = s if scores is None else scores + s
            mx.eval(scores)
            mx.clear_cache()
# to:
            scores = s if scores is None else scores + s
            mx.synchronize()  # H2: real Metal command-buffer barrier
            mx.clear_cache()
```

Also bump `chunk = 2` back to `chunk = 8` to isolate the eval vs synchronize variable. (If chunk=8 + synchronize beats chunk=2 + eval, H2 is the lever.)

#### 2.2 Apply

```bash
cd /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/lib/python3.12/site-packages
# 1. Apply the existing chunking patch
patch -p0 < /Users/vitor/LocalProjects/local-llms/fixes/mlx-lm/mlx-lm-deepseek-v4-indexer-chunk.patch
# 2. Edit chunk back to 8 + replace mx.eval with mx.synchronize (use Edit tool)
```

#### 2.3 Test

Same suite as Step 1.3, using `server-h2.log`, `repro-h2.log`, `jdhodges-h2.log`.

#### 2.4 Pass criterion

Same as Step 1.4. On green → §2 Combine winners. On red → record + roll back + advance to Step 3.

#### 2.5 Roll-back

```bash
cd /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/lib/python3.12/site-packages
patch -R -p0 < /Users/vitor/LocalProjects/local-llms/fixes/mlx-lm/mlx-lm-deepseek-v4-indexer-chunk.patch
# Then revert the eval→synchronize and chunk back-to-original edit (use Edit tool)
```

---

### Step 3 — H3: chunk over `pooled_seq` (in addition to or instead of `n_heads`)

**Confidence: medium.** `pooled_seq` is the dimension that grows unboundedly with prompt cache; `n_heads=64` is fixed. Chunking the unbounded dimension is the structurally correct fix.

#### 3.1 Exact change

Rewrite `Indexer.__call__` body to chunk over the K dimension of `q @ K`. Mathematically equivalent because there's no softmax — `relu(q @ K) * scale * weights` is linear in K, then top-k at the end concatenates safely.

Replace the chunked loop body (after applying fixes/mlx-lm/...indexer-chunk.patch) with:

```python
weights = self.weights_proj(x).astype(mx.float32) * (self.n_heads**-0.5)
weights_t = weights.swapaxes(-1, -2)[..., None]  # (B, n_heads, L, 1)
pooled_chunk = 256  # tune; total pooled_seq can be 2-4K under warm cache
pooled_seq = pooled.shape[1]
score_chunks = []
for p_start in range(0, pooled_seq, pooled_chunk):
    p_end = min(p_start + pooled_chunk, pooled_seq)
    pooled_t = pooled[:, None, p_start:p_end].swapaxes(-1, -2).astype(mx.float32)
    # Full n_heads in one shot — chunk_n_heads not needed if K is chunked enough
    s = q.astype(mx.float32) @ pooled_t                       # (B, n_heads, L, p_chunk)
    s = mx.maximum(s, 0) * self.scale
    s = (s * weights_t).sum(axis=1)                            # (B, L, p_chunk)
    mx.synchronize()
    score_chunks.append(s)
scores = mx.concatenate(score_chunks, axis=-1)                 # (B, L, pooled_seq)
```

If this works at `pooled_chunk = 256`, try larger (512, 1024) to recover throughput.

#### 3.2 Apply

Edit `Indexer.__call__` in `deepseek_v4.py` per above. Save as a new patch: `fixes/mlx-lm/mlx-lm-deepseek-v4-indexer-chunk-pooled.patch`.

#### 3.3 Test

Same suite as Step 1.3, output to `server-h3.log` / `repro-h3.log` / `jdhodges-h3.log`.

#### 3.4 Pass criterion

Same as Step 1.4. Additionally:
- Throughput at `pooled_chunk = 256` should be **comparable to or better than chunk=2 over n_heads** (target ≥ 10 t/s sustained). If far slower, tune pooled_chunk up.

On green → §2 Combine winners. On red → record + roll back + advance to Step 4.

#### 3.5 Roll-back

Revert the indexer edit; remove the new patch file.

---

### Step 4 — H4: `--prompt-cache-size 1` on the server

**Confidence: medium.** Doesn't fix the root cause (single-request OOM is still possible if pooled_seq grows from one big prompt), but **eliminates the cross-request accumulation** that fired our failures at case 8-9.

#### 4.1 Exact change

No code change. Server-only flag.

#### 4.2 Apply

```bash
pkill -f mlx_lm.server; sleep 3
cd /Users/vitor/LocalProjects/local-llms
nohup /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/bin/python -m mlx_lm.server \
  --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --host 0.0.0.0 --port 8765 --max-tokens 65536 --temp 0.0 \
  --prompt-cache-size 1 \
  >> bench/deepseek-v4-flash/logs/server-h4.log 2>&1 & disown
# Warm-load + reproducer + jdhodges probe as Step 1.3
```

#### 4.3 Test

Same suite as Step 1.3, output to `server-h4.log` / `repro-h4.log` / `jdhodges-h4.log`.

**Crucially**, also test the spicyneuron 4000-token reproducer — H4 should NOT fix that one (single-request OOM is independent of cache size), so a clean run on the multi-request probe BUT a fail on the long-single-prompt probe pinpoints H4 as cache-accumulation specifically.

#### 4.4 Pass criterion

Multi-request probe (minimal reproducer, jdhodges 10-case):
- 0 Metal errors, all clean.

Single-request probe (spicyneuron 4000-token):
- Either clean (means cache size 1 helps single requests too — unexpected, double-check) or fails (expected — confirms hypothesis is about cross-request accumulation).

On green for multi-request probe → §2 Combine winners (H4 is a knob, can layer with any code fix). On red → record + advance to Step 5.

#### 4.5 Roll-back

Restart server without `--prompt-cache-size 1`.

---

### Step 5 — H6: try a different quant (4-bit checkpoint)

**Confidence: low-medium.** Tests whether bojiang's sanitize-gap finding contributes. Independent of any code patch.

#### 5.1 Exact change

Download `mlx-community/DeepSeek-V4-Flash-4bit` (replace path).

#### 5.2 Apply

```bash
# Download (~145 GB) — only do this overnight or with a fast connection
huggingface-cli download mlx-community/DeepSeek-V4-Flash-4bit \
  --local-dir /Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-4bit
# Repeat the config.json int→float patch from docs/deepseek-v4-flash-setup.md §1
# Launch with the new model path
```

#### 5.3 Test

Same suite as Step 1.3. Output to `server-h6.log`, etc.

#### 5.4 Pass criterion

- Server log: 0 `metal::malloc` errors.

On green → 4-bit becomes the recommended checkpoint; document and update the testing-plan. On red → sanitize gap was not the contributor; move to Step 6 or upstream.

#### 5.5 Roll-back

Switch back to 2-bit DQ model path.

---

### Step 6 — H5: `--prompt-concurrency 1`

**Confidence: low.** Default may already be 1; verify first.

#### 6.1 Apply

```bash
# Verify default by checking server log for concurrency value, then if > 1, set explicitly
nohup ... --prompt-concurrency 1 ... & disown
```

#### 6.2 Test

Same probe suite.

#### 6.3 Pass criterion

Same as Step 4.4.

---

## Phase 2-revised — fix plan for the per-step residency leak (hypothesis H7)

> This supersedes the original "Phase 2 — Combine winning hypotheses" (below, kept
> for the record). Phase 1 + Phase 1.5 established that the OOM is an **unbounded
> per-decode-step leak of ~1 live Metal buffer per layer**, localized to the
> **compressor + indexer** (~83%) + core attention (~17%). The cap counts *live*
> buffers, so the old combine-the-chunking-fixes plan is moot.

**Hypothesis (H7):** something in `Compressor.__call__` / `Indexer.__call__`
([`deepseek_v4.py:485` / `:537`](../../../venvs/mlx-v4-flash/lib/python3.12/site-packages/mlx_lm/models/deepseek_v4.py))
or the `PoolingCache` update path allocates a buffer each decode step that stays
**referenced** (not freed, not in the freeable cache) — accumulating in the Metal
`ResidencySet` until `num_resources_ > resource_limit_` (499000) at ~11,300 steps.

**Probe for every step below.** Cheap signal: [`leak_probe.py`](../../../bench/deepseek-v4-flash/scripts/leak_probe.py)
steady-state slope (KB/step) — a real fix drives it toward **~0**. Full verification:
[`repro_oom_gen.py`](../../../bench/deepseek-v4-flash/scripts/repro_oom_gen.py) must stream **20K tokens clean**
(baseline OOMs at 11,314). Both run against a fresh single server / process.

### Detailed diagnostic runbook (R1–R3) — recommended order & shared setup

**Recommended order:** **R3 → R1 → R2**. R3 (≈5 min) narrows *which* sub-module so R1's
shape histogram and R2's fix attempt target the right code. R1 then names *what* grows;
R2 tests *why* it's retained and may yield the fix directly. All three are independent
enough to run in any order, but this sequence minimizes wasted reads.

**Decision tree:**
```
R3 ─ which sub-module? (compressor vs indexer)
 └─ R1 ─ does a Python-visible array grow? ── yes → named tensor ─┐
          └─ no (flat in Python) → retention is C++-internal ──┐  │
 R2 ─ does force-eval cache state flatten the slope? ── yes ───┼──┼→ R5 candidate fix
          └─ no ───────────────────────────────────────────────┘  │ (materialize / consolidate)
 if R1 flat AND R2 no-effect → retention is below Python ──────────┴→ R6 (C++ instrumentation)
```

**Shared harness notes (apply to every R-probe):**
- Build on [`leak_probe.py`](../../../bench/deepseek-v4-flash/scripts/leak_probe.py) / [`ablation_probe.py`](../../../bench/deepseek-v4-flash/scripts/ablation_probe.py). Each run = a **fresh process** (one `load()`, ~16 s); measure the **steady-state slope over the back half** of the steps (KB/step). **Baseline to beat = ~200 KB/step**; a real fix → **~0**.
- Model file stays **unpatched** (`deepseek_v4.py.UNPATCHED.bak` is the reference). Diagnostic monkeypatches live in the probe scripts, not the installed module.
- Pipe through `grep -v "deprecated\|Unrecognized"` to keep logs clean. No server needed — drive the model in-process.
- `num_hidden_layers = 43`, so a per-layer-per-step leak shows as ~43–44 of something per step. `compress_ratios[layer_idx]` varies per layer (0 = `LocalAttention`, 128 = `CompressedAttention`, else `SparseCompressedAttention`) — only the sparse layers carry the compressor/indexer.

---

### R1 — Count & fingerprint the retained arrays (~10 min)

**Goal:** turn the byte-slope proxy into a **count** + a **shape fingerprint** of the leaking tensor.

**R1a — gc-trackability pre-check (60 s, do this FIRST).** `mx.array` is a C-extension type and may not be tracked by Python's cyclic GC, in which case `gc.get_objects()` won't list them and R1b is void:
```python
import gc, mlx.core as mx
a = [mx.zeros((2, 2)) for _ in range(1000)]; mx.eval(*a)
print("mx.array seen by gc:", sum(1 for o in gc.get_objects() if isinstance(o, mx.array)), "/ 1000")
```
- `≈1000` → gc scanning works → do **R1b**.
- `≈0` → mx arrays aren't gc-tracked → **skip R1b**, rely on **R1c**, and treat a flat Python count as positive evidence the retention is **C++-internal** (push toward R6).

**R1b — per-step live-array count + shape histogram** (extend `leak_probe.py`): every ~40 steps, `gc.collect()` then
```python
from collections import Counter
objs = [o for o in gc.get_objects() if isinstance(o, mx.array)]
hist = Counter((tuple(o.shape), str(o.dtype)) for o in objs)
# print len(objs), the top-10 buckets, AND each bucket's delta vs the previous sample
```
- **Read:** the bucket whose count climbs ~43/step (or whose count == step·43) is the leak. Likely suspects by shape: indexer scores `(B, 64, 1, pooled_seq)`, pooled `(B, pooled_seq, head_dim)`, a `(B,1,1,head_dim)` kv slab, or a top-k index `(B,1,index_topk)`.

**R1c — deep cache introspection** (catches arrays `nbytes` misses): each sample, recurse every cache (`CacheList.caches` → `RotatingKVCache` / `PoolingCache`), and for each leaf walk `vars(c)` collecting (a) every `mx.array` attr + its shape, (b) any `list`/`tuple` attr whose `len()` grows.
- **Read:** earlier we saw summed `nbytes` stay flat (~12 MB) — so this step looks for what `nbytes` *doesn't* count: a growing **list** of arrays, or an array whose leading dim grows but isn't in the `nbytes` property. Finding one names the leak precisely.

**Decision gate:** named by R1b/R1c → R2 then R5. Nothing grows in Python → C++-internal → run R2 anyway; if R2 also negative, go R6.

**Cost:** ~10 min. **Risk:** gc blind to mx arrays (handled by R1a).

---

### R2 — Confirm lazy-graph retention + get the first candidate fix (~10 min)

**Goal:** test whether the retained buffers are an un-materialized lazy graph held by the compressor/indexer cache — and if so, the fix falls out.

**R2a — force-eval ALL cache state each step** (extend `leak_probe.py`): after the per-step forward + `mx.eval(y)`:
```python
from mlx.utils import tree_flatten
leaves = [v for _, v in tree_flatten([c.state for c in cache]) if isinstance(v, mx.array)]
mx.eval(*leaves)
```
- **Slope → ~0:** confirmed lazy-graph retention. **Fix candidate (R5):** force per-step materialization — either `mx.eval` the cache leaves at the end of `DeepseekV4Model.__call__`, or `mx.eval(self.pooled)` inside `PoolingCache.update_and_fetch` before returning.
- **Slope unchanged:** not lazy-graph retention; buffers are genuinely resident from elsewhere → escalate to R6.

**R2b — isolate to `PoolingCache.pooled`** (only if R2a positive): repeat, but eval **only** the `pooled` member of the compressor/indexer caches (skip RotatingKVCache state). Still → 0 ⇒ the `mx.concatenate`-grown `pooled` (cache.py:995) is the precise culprit ⇒ fix is local to `PoolingCache.update_and_fetch`.

**R2c — control** (brackets the hypothesis): a separate run that does `mx.synchronize()` + `gc.collect()` each step but **no** state eval. If this flattens the slope while R2a does not, retention is refcount/timing rather than graph depth. (H1 already showed `clear_cache` alone does nothing.)

**Cost:** ~10 min (3 short runs). **Output:** either a confirmed, minimal candidate fix or a clean "not a lazy graph" result that justifies R6.

---

### R3 — Split the 83% between compressor and indexer (~5 min)

**Goal:** attribute the dominant leak to `Compressor` vs `Indexer` so R1/R5 target one ~40-line method.

**Approach:** add two monkeypatch modes of `SparseCompressedAttention.__call__` to [`inner_ablation_probe.py`](../../../bench/deepseek-v4-flash/scripts/inner_ablation_probe.py):
- **`skip_indexer`** — keep `pooled = self.compressor(...)`, but set `topk = None` and force the **compressed** branch (`full_kv = mx.concatenate([kv, pooled[:, None]], axis=2)`; never the sparse branch that needs `topk`). Indexer + its `idx_cache` inactive; compressor + `comp_cache` active.
- **`skip_compressor`** — force `pooled = mx.zeros((B, 0, self.head_dim), x.dtype)` → local branch — but **still call** `self.indexer(...)` (it has its *own* internal compressor + `idx_cache`). Compressor + `comp_cache` inactive; indexer active.

**Read** (vs full = 205, local_only = 34.5 KB/step):
- `skip_indexer ≈ local_only` → the **indexer** owns the bulk.
- `skip_compressor ≈ local_only` → the **compressor** owns the bulk.
- both ≈ midway → split across the two.

**Gotcha:** these break attention correctness — fine, we only read the slope; just confirm the loop runs without shape errors before trusting the number.

**Cost:** ~5 min. **Output:** leak localized to one of two methods, focusing R1/R5.

---

### R4 — Check upstream before patching

- **Do:** diff [spicyneuron/mlx-lm@fix-ds4](https://github.com/spicyneuron/mlx-lm/tree/fix-ds4)
  compressor/indexer/cache vs PR #1192 head; try a newer `mlx` / `mlx-lm` build.
- **Pass:** if upstream already bounds per-step residency, adopt it instead of a local
  patch. (Cheapest possible "fix".)

### R5 — Candidate code fix (driven by R1–R3)

Likely shapes of the fix, in order of preference:
1. **Materialize per-step cache state** (from R2) — smallest change if R2 is the lever.
2. **Consolidate `PoolingCache` storage** so growth doesn't churn/retain buffers — e.g.,
   step-allocate + write-in-place like `RotatingKVCache._update_in_place` (cache.py:469)
   instead of `mx.concatenate` per update, so the live-buffer *count* stays bounded.
3. **Fix the specific retained allocation in `Indexer`/`Compressor`** named by R1.

- **Test:** `leak_probe.py` slope ~0 **and** `repro_oom_gen.py` 20K clean **and** throughput
  ≥ 10 t/s. Then proceed to Phase 3 (daily-driver validation) unchanged.

### R6 — Authoritative fallback: C++ allocator instrumentation (REGISTERED — heavy, optional)

> Registered for completeness; run **only** if R1–R3 + R2's fix attempt all come up empty
> (i.e., retention is genuinely C++-internal and unnamed). This is the authoritative
> "name the exact line" path but costs a source build.

**Procedure (not yet scheduled):**
1. `pip show mlx` → 0.31.2; `git clone https://github.com/ml-explore/mlx && cd mlx && git checkout v0.31.2`.
2. In `mlx/backend/metal/allocator.cpp` (`MetalAllocator::malloc`) and/or `resident.cpp`
   (`ResidencySet::insert`): when `num_resources_` crosses each +10000, `fprintf(stderr,…)`
   the count + requested size + a `backtrace()` / `backtrace_symbols()` dump (or, lighter,
   a histogram of resident-buffer sizes dumped at the threshold).
3. Build into the venv: `CMAKE_ARGS=… pip install -e . --no-build-isolation` (~20–40 min
   compile; needs the Metal/Xcode toolchain).
4. Run [`leak_probe.py`](../../../bench/deepseek-v4-flash/scripts/leak_probe.py) against the instrumented build; the
   threshold dumps reveal the size/backtrace of the ~44-per-step retained allocation →
   maps to the MLX op → maps to the model line.
5. File the backtrace upstream (it's exactly what a maintainer needs to fix it).

**Cost:** hours. **Note:** check first whether a newer MLX exposes a residency/resource
counter or debug env (`MLX_METAL_*`) — would make R6 unnecessary.

### R1–R3 results — mechanism CONFIRMED + fix identified (2026-05-30)

Probes: [`bench/deepseek-v4-flash/scripts/r3_split.py`](../../../bench/deepseek-v4-flash/scripts/r3_split.py), [`bench/deepseek-v4-flash/scripts/r1r2_probe.py`](../../../bench/deepseek-v4-flash/scripts/r1r2_probe.py).

**R3 (compressor vs indexer split), KB/step:** full 204 · compressor_only 196 ·
indexer_only 199 · neither (local attn) 31. Each of compressor_only/indexer_only
*alone* (+165/+167 over `neither`) reproduces almost the whole 173 KB/step leak —
because the **`Indexer` owns its own internal `Compressor` + `PoolingCache`**. ⇒ the
culprit is the **`Compressor`/`PoolingCache` path**, not the indexer's top-k scoring.
Each sparse layer has two `PoolingCache`s (compressor pool + indexer pool); both leak.

**R1 (gc + cache introspection):** `mx.array` IS gc-visible, but the live-array *count*
stays ~flat (~3160 over 320 steps). What grows is `PoolingCache.pooled`'s **shape**:
`(1,3,512)→(1,23,512)→(1,43,512)→(1,63,512)→(1,82,512)` (+1 row every `compress_ratio`=4
steps). So it is not a growing count of Python arrays — it's a growing **concat chain**
held by the cache.

**R2 (force-eval), KB/step:** baseline 205 · **R2a eval-all-cache-state 7.8 (leak gone)**
· R2b eval-`pooled`-only 41 · R2c synchronize+gc 205 (no effect).

**Root cause (final):** `PoolingCache.update_and_fetch` does
`self.pooled = mx.concatenate([self.pooled, px], axis=1)` ([cache.py:995](../../../venvs/mlx-v4-flash/lib/python3.12/site-packages/mlx_lm/models/cache.py)).
This builds an **un-detached lazy graph**: `pooled_N` retains `pooled_{N-1}` (and its live
Metal buffer) as a concat input, recursively, across every decode step. `mx.eval(y)` (the
generation loop's normal eval) materializes the *value* but does not detach the chain, so
each step's intermediate buffer stays resident — ~1 per `PoolingCache` per layer per step
→ the residency `num_resources_` count climbs to 499000 at ~11,300 steps. Eval-ing the
cache state each step (R2a) detaches the chain and releases the intermediates → slope ~0.
`buf_kv`/`buf_gate` (accumulate_windows slice-assign) and RotatingKVCache add the residual
between R2b (41) and R2a (7.8), so the complete fix evals **all** cache state, not just
`pooled`.

**→ Fix (R5), validated in principle by R2a:** force per-step materialization of the
DeepSeek-V4 cache state. Open choice on *where* (throughput / upstream-shape tradeoff):
- (a) inside `PoolingCache.update_and_fetch` / `accumulate_windows` — `mx.eval(self.pooled)`
  (+ `buf_kv`/`buf_gate`); most self-contained, but only covers PoolingCache (≈R2b, 41 →
  needs RotatingKVCache too for full effect).
- (b) at the end of `DeepseekV4Model.__call__` — `mx.eval` the per-layer cache state
  (covers all caches ≈R2a, 7.8) — but must sit after/around the pipeline send/recv logic.
- (c) in the generation integration (eval `[c.state for c in cache]` each step) — exactly
  what R2a did; cleanest semantics, but touches `generate.py`/server rather than the model.
- **Verify any choice:** `leak_probe.py` slope → <15 KB/step **and** `repro_oom_gen.py`
  streams 20K tokens clean **and** throughput ≥ 10 t/s.

### R5 result — FIX VERIFIED (2026-05-30) ✅ done-bar #2 green

Patch: [`fixes/mlx-lm/mlx-lm-deepseek-v4-cache-materialize.patch`](../../../fixes/mlx-lm/mlx-lm-deepseek-v4-cache-materialize.patch)
(single hunk in `DeepseekV4Model.__call__`).

What it took (two dead ends, then the choke point):
1. **(a) `PoolingCache.update_and_fetch` eval** — in-process `leak_probe` 205 → **3.2 KB/step** ✅,
   but the **server still OOMed at ~11,300 tokens**: the server's BatchGenerator uses
   `BatchPoolingCache`, not `PoolingCache`, so the fix was bypassed.
2. **(a′) also patch `BatchPoolingCache`** — server **still OOMed at ~11,300** (fired at our
   own eval). So the dominant *batch-path* leak isn't the pooling cache at all — it's
   `BatchRotatingKVCache._update_in_place` (slice-assign of `keys`/`values` + `mx.array`
   `left_padding`/`offset` updates, in all 43 layers, no eval). Per-class patching = whack-a-mole.
3. **(b) model-forward choke point** — eval **every** cache array (walk each leaf cache's
   `vars()`) once at the end of `DeepseekV4Model.__call__`. Covers every cache class (single
   AND batched) in one place. In-process slope **7.1 KB/step**; **server forced-gen probe
   streamed 19,989 tokens CLEAN at 31.3 t/s with 0 `metal::malloc`** (baseline died at 11,314,
   full throughput, no regression). cache.py reverted to clean — fix lives only in deepseek_v4.py.

**Lesson:** verify on the *server* path, not just in-process — the BatchGenerator swaps in
`Batch*` cache variants with their own (un-evaluated) per-step update graphs.

**Done-bar #1 — PASSED (2026-05-30) ✅.** Full 40-case jdhodges sweep on a single long-lived
patched server ([`bench/deepseek-v4-flash/scripts/verify_jdhodges_sweep.sh`](../../../bench/deepseek-v4-flash/scripts/verify_jdhodges_sweep.sh),
server-cachefix-jdhodges.log): **40/40 completed, 0 `metal::malloc`, 19.8 min, ~33 t/s** — vs
unpatched **49 OOMs, first OOM at case 20, aborted at 161 min**. Case 20
(`multi_email_after_calendar_read`, the original first-OOM trigger) and all `arg_*`/`multi_*`
cases now complete clean — confirms the cross-request cache-accumulation failure is gone, no
restart wrapper. (max-tokens capped at 2048 for the sweep because the model loops at temp=0.0
— a separate known issue, mitigated by `--temp 0.6`; all looping cases completed without OOM.
Tool-call score 8/40, all `edge_cases` prose — the checkpoint isn't a tool-calling fine-tune,
unchanged by this fix.)

**Remaining (done-bar #3):** 30-turn Open WebUI chat session without restart (manual). Then:
promote patch in setup guide (done), file upstream against PR #1192, and optionally re-run the
full Phase 3 #10 knowledge/throughput sweep now that the runtime is stable.

**Done bar:** unchanged — see Phase 3 + investigation doc §6. A fix qualifies when
`repro_oom_gen.py` reaches 20K clean, the single-server bench sweep shows 0 Metal OOMs,
and a 30-turn Open WebUI session needs no restart.

---

## Phase 2 (superseded) — Combine winning hypotheses

> **SUPERSEDED 2026-05-30** by Phase 2-revised above. Kept for the record. This assumed
> some of H1–H3 would pass and be additive; in fact H1 failed and H2–H4 are invalidated
> by the live-buffer-count mechanism, so there is nothing to combine.

For each step that PASSED in Phase 1, re-apply them together and rerun the full probe. The expectation is that combinations are additive (e.g., H1 + H2 should be at least as good as either alone), but watch for interactions (e.g., per-layer eval inside Step 1 might subsume the need for indexer chunking in Step 3).

### 2.1 Combination sequence

If all of H1, H2, H3 passed individually, apply in this order and test after each addition:

1. H1 alone (already tested in Step 1.3).
2. H1 + H2.
3. H1 + H2 + H3.

If only some passed, apply the union of passing hypotheses.

### 2.2 Probe at each combination

Same test suite as Step 1.3, plus the **full 40-case jdhodges run** on a **single long-lived server** (no restart wrapper). This is the gold standard probe — if it passes clean, done bar (1) is met.

### 2.3 Pass criterion for "combined fix"

ALL of:
- Minimal reproducer 25/25 clean.
- Spicyneuron 4000-token reproducer clean (done bar 2).
- Full 40-case jdhodges run on single server, 0 Metal errors (done bar 1).
- Throughput ≥ 10 t/s sustained (so it's actually usable for daily chat, not just technically working).

On green → proceed to Phase 3. On red → revisit hypotheses or escalate (see §"If everything fails" below).

---

## Phase 3 — Daily-driver validation

Once Phase 2 passes its probe, validate the real daily-use scenario.

### 3.1 Open WebUI 30-turn chat probe

Start `mlx_lm.server` with the winning combination of fixes. Open `http://localhost:3000` (Open WebUI). Do a real 30-turn mixed chat session — code review, research questions, longish explanations.

#### Pass criterion (done bar 3)
- No noticeable degradation, repetition, or hangs across 30 turns.
- No need to restart the server during the session.

### 3.2 Wall-clock soak

Leave the server running idle for 6+ hours, then resume a chat session. Pass: still responsive, no Metal errors in the server log accumulated overnight.

### 3.3 Update operational docs

If all three done bars are green:

1. **Promote the winning patch(es) into `fixes/mlx-lm/`.** Document apply order in [`docs/deepseek-v4-flash-setup.md`](setup.md). Bump the relevant Step 3a section.
2. **Update the M4 notes Phase 3 #10 section** — change "blocked" → "daily-driver candidate"; record the bench sweep numbers on a single-server run.
3. **Update [`docs/testing-plan.md`](../../testing-plan.md) Step E** — from BLOCKED to status-of-daily-driver-evaluation.
4. **File an upstream PR or issue** referencing PR #1192 with the winning patch and the data points from this investigation.

---

## If everything fails

If Phase 1 Steps 1-6 all fail individually and the combined Phase 2 application also fails, escalate:

### Escalation paths

1. **Compare against spicyneuron's [`fix-ds4`](https://github.com/spicyneuron/mlx-lm/tree/fix-ds4) branch.** Diff it against PR #1192 head, identify any structural changes we haven't tried.
2. **Look at Metal's actual resource accounting.** Use `mx.metal.start_capture(path)` around a single forward pass, open the capture in Xcode's Metal debugger, count the per-command-buffer resources to see where the budget actually goes. This is the authoritative answer to "what's costing 499 000 resources."
3. **Try the `bf16` (or `fp16`) checkpoint instead of any quantized one.** If the issue is in quantized weight handling (sanitize gap, dequant kernel registering many small buffers), unquantized might dodge it. Expensive (~600 GB download) — last resort.
4. **Wait on upstream.** If PR #1192 gets reopened or a successor appears, retry with that codebase rather than continuing to debug a stalled branch.

---

## Results log

Fill in as steps execute. Use this format:

```
[YYYY-MM-DD HH:MM] Step N (Hx): PASS|FAIL
  Minimal reproducer: <pass count>/25
  Spicyneuron reproducer: <PASS|FAIL|N/A>
  jdhodges 10-case probe: <pass count>/10, <Metal error count> OOMs
  Throughput: <X> t/s sustained
  Notes: <free-form>
```

Initial baseline (Phase 0.3) goes here first; each subsequent step appends.

### Phase 0.3 — unpatched baseline

```
[2026-05-29] un-patched runtime (full jdhodges 40, single-server):
  Minimal reproducer: not yet run with this harness
  Spicyneuron reproducer: not yet run on this rig (see external signals)
  Full jdhodges 40-case probe: 5/40 passes, FIRST FAIL AT CASE 20 (multi_email_after_calendar_read)
  Metal errors in server log: 49
  Wall-clock: 161.5 min (vs ~30 min expected; ~130 min spent in urlopen waits on OOM-aborted requests)
  Notes:
    - This is the §3.1 of the investigation doc — un-patched mlx-lm PR #1192 head, no chunking.
    - Verifies the probe is sensitive enough to catch the issue with margin.
    - Cases 1-19 ran cleanly (all FAIL no_tool_called, but no server errors); case 20 first OOM.
    - 5 passing cases are all in `edge_cases` category where prose is the correct answer.
```

### Phase 0.4 — patched-v2 (chunk=2 + clear_cache) baseline, single-server

```
[2026-05-29] chunk=2 + mx.clear_cache(), single-server jdhodges:
  Multi-request probe: ran to case 8 cleanly, case 9 hung 23.5 min, case 10 errored fast
  Metal errors in server log: 8 (1 in our chunked indexer, 3 in mx.random.seed, 4 scattered)
  Throughput: 6-7 t/s sustained
  Notes:
    - Indexer chunking alone is necessary but not sufficient.
    - OOM migrates to other ops (mx.random.seed) — confirms whole-forward-pass issue.
    - Server enters "wedged" state after first OOM; even trivial ops fail until restart.
```

### Phase 0.5 — restart-per-batch wrapper baseline (operational stop-gap)

```
[2026-05-29] chunk=2 + restart-server between every 8-case batch:
  Batch 1 (sel_*, short prompts):  0 OOMs, 8/8 clean prose, 8.7 min
  Batch 2 (arg_*, longer prompts): ~16 OOMs, 0/8, 32.9 min
  Batch 3 (multi_*, longest):      ~26 OOMs, 2 prose + 6 errors, 33.4 min
  Notes:
    - Wrapper fixes cross-request accumulation but NOT single-request OOMs.
    - Provides direct evidence to prioritize H1 over H4: longer prompts blow the
      cap even on a fresh server, so any fix must bound per-forward-pass resource
      count, not just cross-request cache state.
```

### Step 1 — H1 (per-layer eval + clear_cache)

```
[2026-05-29 23:31] Step 1 (H1): FAIL
  Forced-gen probe (repro_oom_gen.py): OOM_AT ~11,300 tokens
  Unpatched baseline (Phase 0.3, repro-baseline-gen.log): OOM_AT 11,314 tokens
  Δ vs baseline: ~0 (no measurable improvement)
  Server log (bench/deepseek-v4-flash/logs/server-h1.log): metal::malloc fired at OUR mx.eval(h),
    deepseek_v4.py:983 (the H1 boundary itself), during a decode step.
  Trigger prompt: 58 tokens ("count to 20000"). So OOM is purely decode-STEP-COUNT
    driven, NOT prompt/context length (a single 60K-ctx forward pass was clean in
    Phase 0 calibration; 11.3K decode steps from a tiny prompt OOMs).
  Patch applied: every 10 layers in DeepseekV4Model.__call__ (adapted to the real
    enumerate(zip(pipeline_layers, cache)) loop). Saved as
    fixes/mlx-lm/mlx-lm-deepseek-v4-per-layer-eval.patch.candidate. Rolled back after.
  Conclusion: per-layer eval+clear_cache changes nothing because the growing
    resource is LIVE state, not freeable cache — see "Mechanism revision" below.
```

### Mechanism revision (post-H1) — the real root cause is a live-buffer COUNT cap

H1's failure plus a read of the MLX runtime reframes the whole hypothesis set.

**What `[metal::malloc] Resource limit (499000) exceeded` actually means.** In
`mlx/include/mlx/backend/metal/allocator.h` the allocator tracks `num_resources_`
against `resource_limit_`, alongside a `ResidencySet` (`resident.h`). **499000 is a
cap on the number of distinct LIVE Metal buffers (residency-set entries), not bytes
and not graph/command-buffer depth.** It is effectively the Apple-Silicon driver's
max-resident-resources limit. There is **no MLX Python API to raise it** — the only
exposed knobs are `set_cache_limit` / `set_memory_limit` / `set_wired_limit`
(verified against mlx 0.31.2: `dir(mlx.core.metal)` has no resource-limit setter).

**Why this kills H1 (and re-scores H2–H4):**
- The OOM is reached after **~11,300 decode steps regardless of prompt length**
  (≈ "one retained resident buffer per sparse layer per step": 499000 / 11,300 ≈ 44,
  and the model has ~that many SparseCompressedAttention layers).
- `mx.clear_cache()` only evicts *freed-but-cached* buffers; it cannot lower a count
  of *live* buffers. `mx.eval` / `mx.synchronize` only cut the lazy graph / add a
  barrier — they don't reduce live buffer count either. → **H1 FAIL (confirmed), H2
  (synchronize) predicted FAIL for the same reason.**
- **H3 (chunk pooled_seq) is predicted COUNTERPRODUCTIVE:** chunking an op creates
  *more* intermediate buffers per forward pass, raising `num_resources_`, not lowering
  it. It targets per-op tensor *size*, but size is not what is capped.
- **H4 (`--prompt-cache-size 1`) is irrelevant to this signature:** the failure is a
  single long generation within one request; cross-request cache count is not the
  driver.

**Where the per-step buffer growth is NOT:** both model caches are designed to be
buffer-count-stable — `RotatingKVCache._update_in_place` (cache.py:469) pre-allocates
in 256-step blocks and writes in place + rotates (bounded by `sliding_window`);
`PoolingCache.update_and_fetch` (cache.py:986) grows `pooled` via `mx.concatenate`,
which replaces one buffer (bytes grow, count ~stable). So the ~44-buffers/step
residency growth is **below the model layer**, in MLX's allocator / lazy-eval
residency behavior under this decode pattern. Pinning the exact retained allocation
needs the Metal capture (escalation path #2), which is now the authoritative next step.

**Revised confidence order:** H2 LOW (was med-high), H3 LOW/counterproductive (was
med), H4 ~N/A for single-request (was med). The productive paths are now: (a) Metal
capture to identify the per-step retained buffer; (b) an upstream MLX/model fix that
consolidates per-step residency; (c) H6 (different quant) only as an orthogonal check.
See "Decision needed" appended to the Results log tail.

### Step 2 — H2 (mx.synchronize between chunks)

```
[NOT RUN] Re-scored LOW by the Mechanism revision above: synchronize is a barrier,
  not a live-buffer-count reduction, so it cannot move a residency-set count cap.
  Run only if the Metal capture unexpectedly shows graph-depth (not count) is binding.
```

### Step 3 — H3 (chunk pooled_seq)

```
[NOT RUN] Re-scored LOW/counterproductive: chunking adds intermediate buffers per
  forward pass, increasing num_resources_. Targets tensor size, but size is not capped.
```

### Step 4 — H4 (--prompt-cache-size 1)

```
[NOT RUN] Re-scored ~N/A for this signature: failure is a single long generation in
  one request; cross-request cache count is not the driver.
```

### Step 5 — H6 (different quant)

```
[NOT RUN] Orthogonal check only — buffer-count growth is per-layer-per-step and
  architecture-driven, so a different quant of the same architecture is unlikely to
  change the count. Low priority.
```

### Step 6 — H5 (--prompt-concurrency 1)

```
[NOT RUN] ~N/A for single-request single-generation signature.
```

### Decision needed (2026-05-29)

H1 (the plan's highest-confidence fix) FAILED, and the mechanism read invalidates the
written H2–H4 order. The cheap-probe phase of the plan is largely spent. The remaining
productive options each carry a real tradeoff for the user to weigh:

1. **Metal capture (escalation #2, authoritative).** `mx.metal.start_capture` around a
   short forced generation, open the `.gputrace` in Xcode's Metal debugger, count the
   per-step retained resources to pin the exact allocation. Needs Xcode GUI work.
2. **Empirical confirm-then-discard H2/H3 (~20 min each).** Low expected value — the
   mechanism predicts failure — but gives hard data for an upstream report.
3. **Pure-Python residency instrumentation.** Log `get_active_memory()` /
   `get_cache_memory()` per N decode steps to characterise live-byte vs cache growth
   (note: no `num_resources_` getter is exposed, so this is indirect).
4. **Declare not-daily-driver-ready and file upstream.** Report the residency-count
   finding against PR #1192 / mlx-lm; treat the restart-per-batch wrapper as the
   operational stop-gap until upstream consolidates per-step residency.

### Phase 1.5 — capture + residency-instrumentation findings (2026-05-30)

Executed option 1 (Metal capture) + option 3 (Python residency instrumentation).
Probes: [`bench/deepseek-v4-flash/scripts/metal_capture_probe.py`](../../../bench/deepseek-v4-flash/scripts/metal_capture_probe.py),
[`bench/deepseek-v4-flash/scripts/leak_probe.py`](../../../bench/deepseek-v4-flash/scripts/leak_probe.py).

**Metal capture is not viable for this model.** `mx.metal.start_capture` (requires
`MTL_CAPTURE_ENABLED=1`) around 2 consecutive decode steps produced a **90 GB**
`.gputrace` — the ~89 GB of resident weights are bundled into every capture, so no
"capture a few steps" trick makes it small. Opening it in Xcode is impractical. The
Python instrumentation below was far more informative.

**The OOM is a genuine unbounded per-decode-step buffer leak. Measured facts:**
- Active memory grows **strictly linearly at ~166–200 KB/step** with **no plateau**
  through 2000 steps (+358 MB at step 2000). Extrapolates to ~1.9–2.3 GB at the
  ~11,300-step OOM point — modest bytes, confirming the **count** cap (499000 live
  buffers) binds first, not memory.
- Rate ≈ **one retained live buffer per layer per decode step** (`num_hidden_layers
  = 43`; observed ~44 buffers/step from 499000 / 11300).
- Prompt-length independent (58-token prompt OOMs at the same step count).

**Ruled out (each by direct test):**
- *General MLX runtime:* 20,000 evals of a trivial fresh graph leak **zero** bytes.
  So this is model-specific, not a generic allocator bug.
- *`@mx.compile` retention:* slope identical with `mx.disable_compile()` (200.1 vs
  203.3 KB/step). Not the HyperConnection compiled ops.
- *RoPE freqs cache:* `_freqs_cache` keyed by `(head_dim, inverse)` — bounded.
- *Model KV/Pooling caches:* summed `nbytes` stays flat (~12 MB); RotatingKVCache is
  bounded (`sliding_window = 128`, in-place rotation), PoolingCache concats (replaces
  one buffer). Neither grows the count.
- *MoE expert paging:* would plateau by ~step 500 once all 256 experts/layer are
  resident; growth is linear to 2000 steps, so not this.

**Leak localized by ablation** ([`bench/deepseek-v4-flash/scripts/ablation_probe.py`](../../../bench/deepseek-v4-flash/scripts/ablation_probe.py),
[`bench/deepseek-v4-flash/scripts/inner_ablation_probe.py`](../../../bench/deepseek-v4-flash/scripts/inner_ablation_probe.py)) —
monkeypatch the block / attention forward to bypass sub-modules, measure slope:

| ablation | slope (KB/step) | vs full |
|---|---|---|
| full block | 208 | 100% |
| bypass MoE-FFN | 201 | 97% (leak stays) |
| HyperConnections only | 0 | 0% |
| **bypass attention** | **−3** | **~0% (leak gone)** |
| attention: core-local only (skip compressor+indexer) | 34.5 | 17% |

So the leak is **in the attention sub-module**, and **~83% of it is the compressor +
indexer** (the DeepSeek-V4 sparse pooled-KV machinery, `SparseCompressedAttention`
lines ~800/829/831 → `Compressor.__call__` + `Indexer.__call__` + their two
`PoolingCache`s), with ~17% residual in the core q/kv/SDPA path. MoE and
hyper-connections do **not** leak.

**Conclusion / what's left.** The DeepSeek V4 attention forward (mlx-lm PR #1192)
retains ~1 live Metal buffer per layer per decode step, dominated by the
compressor/indexer pooled path, outside the documented caches. Naming the exact
allocation line still requires **C++ allocator-level instrumentation** (log
`num_resources_` / residency inserts per step) — MLX exposes no Python buffer-count
getter and the GPU trace is too large to use — but the fix surface is now narrow:
`Compressor.__call__` / `Indexer.__call__` and the `PoolingCache` (compress + index)
update path. (Next optional drill: split compressor vs indexer.)

**Recommended next step:** file upstream against mlx-lm PR #1192 / mlx with this
characterization + [`leak_probe.py`](../../../bench/deepseek-v4-flash/scripts/leak_probe.py) as a minimal
reproducer (linear residency growth, count-cap OOM at ~11.3K decode steps,
prompt-independent, not compile/RoPE/cache/expert-paging). Keep the restart-per-batch
wrapper as the operational stop-gap. Optional local follow-up before filing:
component ablation (bypass attn vs ffn vs hc in the block forward, measure which
zeroes the slope) to localize the leak to a sub-module — strengthens the report but
does not name the buffer.

**Artifacts:** `bench/deepseek-v4-flash/logs/ds4_decode.gputrace` (90 GB — delete unless needed for
Xcode; trivially regenerable via `metal_capture_probe.py`).

---

## Cross-references

- Root investigation: [`docs/deepseek-v4-flash-metal-oom-investigation.md`](metal-oom-investigation.md)
- Setup guide (venv + config patches): [`docs/deepseek-v4-flash-setup.md`](setup.md)
- Phase 3 #10 benchmark plan: [`bench/deepseek-v4-flash/plan-phase-3.md`](../../../bench/deepseek-v4-flash/plan-phase-3.md)
- Existing carried patches: [`fixes/mlx-lm/`](../../../fixes/mlx-lm)
- Restart-loop wrapper (current stop-gap): [`bench/deepseek-v4-flash/scripts/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh`](../../../bench/deepseek-v4-flash/scripts/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh)
