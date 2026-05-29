# DeepSeek V4 Flash Metal OOM — fix-application plan

**Goal:** apply the hypotheses from [`docs/deepseek-v4-flash-metal-oom-investigation.md`](deepseek-v4-flash-metal-oom-investigation.md) in confidence order until the model meets the daily-driver bar (§"Definition of done" in the investigation doc).

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
cd /Users/vitor/LocalProjects/local-llms/.bench-logs
curl -sSL https://gist.githubusercontent.com/spicyneuron/deeb395b2f2f7d5c97a6ab2590b72cb5/raw \
  -o spicyneuron-deepseek-v4-reproducer.py
# Sanity: print the first 30 lines to confirm we got something runnable
head -30 spicyneuron-deepseek-v4-reproducer.py
```

If the gist is a single-file Python script, save as `repro_spicyneuron.py` in the same dir. If it's bash + python, save both pieces.

### 0.2 Write our own minimal reproducer (independent of the gist)

A small Python that hits `/v1/chat/completions` 25 times in a row against the same server, growing the per-request context, and reports first-error case. Saves us from depending on the gist being available.

Save at [`.bench-logs/repro_oom_minimal.py`](../.bench-logs/repro_oom_minimal.py):

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
patch -R -p0 < /Users/vitor/LocalProjects/local-llms/patches/mlx-lm-deepseek-v4-indexer-chunk.patch
# Kill any running server
pkill -f mlx_lm.server; sleep 3
# Launch fresh
cd /Users/vitor/LocalProjects/local-llms
nohup /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/bin/python \
  -m mlx_lm.server --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --host 0.0.0.0 --port 8765 --max-tokens 65536 --temp 0.0 \
  >> .bench-logs/server-baseline.log 2>&1 & disown
# Warm-load
curl -sS -m 360 http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ",
       "messages":[{"role":"user","content":"hi"}],"max_tokens":4}' >/dev/null
# Run the minimal reproducer
python3 .bench-logs/repro_oom_minimal.py | tee .bench-logs/repro-baseline.log
# Count Metal errors in server log
grep -c 'metal::malloc' .bench-logs/server-baseline.log
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
  /Users/vitor/LocalProjects/local-llms/patches/mlx-lm-deepseek-v4-per-layer-eval.patch.candidate
```

#### 1.3 Test

```bash
# Restart server cleanly
pkill -f mlx_lm.server; sleep 3
cd /Users/vitor/LocalProjects/local-llms
nohup /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/bin/python -m mlx_lm.server \
  --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --host 0.0.0.0 --port 8765 --max-tokens 65536 --temp 0.0 \
  >> .bench-logs/server-h1.log 2>&1 & disown
# Warm-load (smoke chat) — must succeed
curl -sS -m 360 ...  # same as Phase 0.3
# Run the minimal reproducer
python3 .bench-logs/repro_oom_minimal.py | tee .bench-logs/repro-h1.log
# Run spicyneuron's reproducer (if captured)
python3 .bench-logs/repro_spicyneuron.py | tee .bench-logs/repro-h1-spicyneuron.log
# Count Metal errors
grep -c 'metal::malloc' .bench-logs/server-h1.log
# Extended probe: 8-case jdhodges single-server (no restart wrapper)
cd /Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
/Users/vitor/LocalProjects/local-llms/.venv/bin/python scripts/tool_call_bench.py \
  --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --suite jdhodges \
  --base-url http://127.0.0.1:8765/v1 \
  --only sel_weather_portland,sel_currency_usd_eur,sel_timezone_tokyo,sel_web_python_release,sel_reminder_dentist,sel_email_quick,sel_calendar_create,sel_calendar_read_week,arg_weather_units_celsius,arg_currency_jpy \
  --force \
  --run-prefix toolcall_h1 \
  2>&1 | tee /Users/vitor/LocalProjects/local-llms/.bench-logs/jdhodges-h1.log
```

#### 1.4 Pass criterion

ALL of:
- Minimal reproducer: `REPRO_CLEAN: all 25 requests succeeded` printed.
- Server log (`.bench-logs/server-h1.log`): **0** `metal::malloc` errors.
- jdhodges 10-case probe: completes all 10 without hanging > 60 s on any case.

If pass → record in §3 "Results", proceed to **§2 Combine winners** with H1 included.
If fail → record in §3, roll back, advance to **Step 2 (H2)**.

#### 1.5 Roll-back

```bash
cd /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/lib/python3.12/site-packages
# Revert the per-layer eval edit via Edit tool, OR:
patch -R -p0 < /Users/vitor/LocalProjects/local-llms/patches/mlx-lm-deepseek-v4-per-layer-eval.patch.candidate
```

---

### Step 2 — H2: `mx.synchronize()` instead of `mx.eval()` between indexer chunks

**Confidence: medium-high.** Would explain why chunk=2 helped only marginally over chunk=8 — if `mx.eval()` doesn't create a real command-buffer barrier, our chunking achieved nothing structural. `mx.synchronize()` is the documented "wait for all pending work" barrier.

#### 2.1 Exact change

Reapply our existing indexer chunking patch first, then swap the boundary primitive:

File: `venvs/mlx-v4-flash/lib/python3.12/site-packages/mlx_lm/models/deepseek_v4.py`, in `Indexer.__call__`:

```python
# After applying patches/mlx-lm-deepseek-v4-indexer-chunk.patch, change:
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
patch -p0 < /Users/vitor/LocalProjects/local-llms/patches/mlx-lm-deepseek-v4-indexer-chunk.patch
# 2. Edit chunk back to 8 + replace mx.eval with mx.synchronize (use Edit tool)
```

#### 2.3 Test

Same suite as Step 1.3, using `server-h2.log`, `repro-h2.log`, `jdhodges-h2.log`.

#### 2.4 Pass criterion

Same as Step 1.4. On green → §2 Combine winners. On red → record + roll back + advance to Step 3.

#### 2.5 Roll-back

```bash
cd /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/lib/python3.12/site-packages
patch -R -p0 < /Users/vitor/LocalProjects/local-llms/patches/mlx-lm-deepseek-v4-indexer-chunk.patch
# Then revert the eval→synchronize and chunk back-to-original edit (use Edit tool)
```

---

### Step 3 — H3: chunk over `pooled_seq` (in addition to or instead of `n_heads`)

**Confidence: medium.** `pooled_seq` is the dimension that grows unboundedly with prompt cache; `n_heads=64` is fixed. Chunking the unbounded dimension is the structurally correct fix.

#### 3.1 Exact change

Rewrite `Indexer.__call__` body to chunk over the K dimension of `q @ K`. Mathematically equivalent because there's no softmax — `relu(q @ K) * scale * weights` is linear in K, then top-k at the end concatenates safely.

Replace the chunked loop body (after applying patches/...indexer-chunk.patch) with:

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

Edit `Indexer.__call__` in `deepseek_v4.py` per above. Save as a new patch: `patches/mlx-lm-deepseek-v4-indexer-chunk-pooled.patch`.

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
  >> .bench-logs/server-h4.log 2>&1 & disown
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

## Phase 2 — Combine winning hypotheses

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

1. **Promote the winning patch(es) into `patches/`.** Document apply order in [`docs/deepseek-v4-flash-setup.md`](deepseek-v4-flash-setup.md). Bump the relevant Step 3a section.
2. **Update the M4 notes Phase 3 #10 section** — change "blocked" → "daily-driver candidate"; record the bench sweep numbers on a single-server run.
3. **Update [`docs/testing-plan.md`](testing-plan.md) Step E** — from BLOCKED to status-of-daily-driver-evaluation.
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
[TODO — next session]
```

### Step 2 — H2 (mx.synchronize between chunks)

```
[TODO]
```

### Step 3 — H3 (chunk pooled_seq)

```
[TODO]
```

### Step 4 — H4 (--prompt-cache-size 1)

```
[TODO]
```

### Step 5 — H6 (different quant)

```
[TODO]
```

### Step 6 — H5 (--prompt-concurrency 1)

```
[TODO]
```

---

## Cross-references

- Root investigation: [`docs/deepseek-v4-flash-metal-oom-investigation.md`](deepseek-v4-flash-metal-oom-investigation.md)
- Setup guide (venv + config patches): [`docs/deepseek-v4-flash-setup.md`](deepseek-v4-flash-setup.md)
- Phase 3 #10 benchmark plan: [`docs/benchmark-plans/2026-05-29-deepseek-v4-flash-phase-3.md`](benchmark-plans/2026-05-29-deepseek-v4-flash-phase-3.md)
- Existing carried patches: [`patches/`](../patches/)
- Restart-loop wrapper (current stop-gap): [`.bench-logs/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh`](../.bench-logs/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh)
