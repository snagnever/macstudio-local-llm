# DeepSeek‑V4 (Flash/Pro) on Apple Silicon: unbounded Metal residency growth during decode → `[metal::malloc] Resource limit (499000) exceeded`

**Audience:** mlx‑lm maintainers / reviewers of [PR #1192](https://github.com/ml-explore/mlx-lm/pull/1192) (DeepSeek‑V4 port). This document is written to be adapted into a GitHub **issue** (symptom + reproducer + root cause, §1–§5) and a **PR** (fix + verification, §6–§8).

---

## 1. TL;DR

DeepSeek‑V4's attention caches (`PoolingCache` and `RotatingKVCache`, including their `Batch*` variants) update their state every decode step with `mx.concatenate` / sliced functional assignment, but the resulting arrays are **never detached from their input graph**. Because the cache object holds the *head* of that growing graph, MLX keeps **every prior step's intermediate array — and its backing Metal buffer — resident**. The number of live resident buffers therefore grows ~linearly with the number of decode steps (≈ **one buffer per layer per step**), and on Apple Silicon it crosses MLX's Metal residency cap (`resource_limit`, observed at **499000**) after **~11,300 generated tokens, regardless of prompt length**, aborting generation with:

```
RuntimeError: [metal::malloc] Resource limit (499000) exceeded.
```

**Fix:** materialize (`mx.eval`) the per‑layer cache state once per forward pass, which detaches the chains so the resident‑buffer count stays bounded. A one‑hunk change in `DeepseekV4Model.__call__` eliminates the leak with **no throughput regression** (verified: 19,989‑token generation clean at 31.3 tok/s, 0 OOMs; and a 40‑case tool‑call sweep that previously hit 49 OOMs now completes 40/40 with 0 OOMs).

This is **not** a memory‑*size* problem, **not** a single‑forward‑pass / per‑command‑buffer problem, and **not** a prompt‑cache‑length problem. It is a *count of live buffers* that grows with decode steps.

---

## 2. Environment

| | |
|---|---|
| Model | `mlx-community/DeepSeek-V4-Flash-2bit-DQ` (284B/13B‑active MoE; `num_hidden_layers = 43`) |
| Runtime | mlx‑lm @ PR #1192 head |
| MLX | 0.31.2 |
| Hardware | Apple M4 Max, 128 GB unified memory |
| OS | macOS 26.3 |
| Server | `mlx_lm.server --max-tokens 65536 --temp 0.0` |

Likely affects **all** DeepSeek‑V4 checkpoints and all Apple‑Silicon classes (the original community reproducer fired on an M3). Reported independently in the PR thread as "looping / long‑context" failures around ~4000 tokens.

---

## 3. Symptom

- Single fresh request: works.
- After enough **decode steps** (sustained generation, or accumulated across requests against a long‑lived `mlx_lm.server`), inference aborts with `[metal::malloc] Resource limit (499000) exceeded`.
- After the first failure the Metal command queue is wedged; subsequent requests fail until a full process restart.
- The error surfaces at whatever op happens to allocate next — we've seen it at the indexer (`weights_proj`), at `mx.random.seed`, and inside `mx.eval` — which is a tell that the limit is a **global live‑buffer count**, not any one op being too large.

**It is decode‑step‑count driven, not context‑length driven.** A single forward pass at 60K context is clean; a **58‑token prompt** generating to ~11,300 tokens OOMs. `499000 / 11300 ≈ 44 ≈ num_hidden_layers` → ~one retained buffer per layer per step.

---

## 4. Minimal reproducer

Streaming forced generation against a server (OOMs at ~11,314 tokens unpatched):

```python
# stream a long generation; prints OOM_AT <n> when the stream breaks, else CLEAN
import json, time, urllib.request
BASE, MODEL = "http://127.0.0.1:8765/v1", "<model-path>"
payload = json.dumps({"model": MODEL,
    "messages": [{"role": "user", "content":
        "Count from 1 to 20000, one number word per line. Do not stop early."}],
    "max_tokens": 20000, "temperature": 0.0, "stream": True}).encode()
req = urllib.request.Request(f"{BASE}/chat/completions", data=payload,
                             headers={"Content-Type": "application/json"})
n, t0 = 0, time.time()
try:
    with urllib.request.urlopen(req, timeout=2400) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("data:") and line[5:].strip() != "[DONE]":
                try:
                    d = json.loads(line[5:].strip())["choices"][0]["delta"]
                    if d.get("content"): n += 1
                except Exception: pass
    print(f"CLEAN: {n} tokens in {time.time()-t0:.0f}s")
except Exception as e:
    print(f"OOM_AT: broke after {n} tokens -- {type(e).__name__}: {e}")
```

A self‑contained in‑process probe (no server) that measures the leak *rate* and converges much faster is in §A (Appendix). It reports steady‑state active‑memory growth per decode step: **~200 KB/step unpatched → ~7 KB/step patched.**

---

## 5. Root cause

### 5.1 The cap counts live resident buffers

`resource_limit` (499000 on this device) is a count tracked by MLX's Metal allocator (`mlx/backend/metal/allocator.h`: `num_resources_` vs `resource_limit_`, backed by the `ResidencySet` in `resident.h`). It is **a count of live buffers, not bytes**. None of the byte‑budget knobs (`set_memory_limit` / `set_wired_limit` / `set_cache_limit`) affect it, and there is no Python API to raise it. At the OOM point the process holds only ~2–3 GB of leaked bytes — well under any memory limit — but ~499000 distinct live buffers.

Because the buffers are **live** (referenced), `mx.clear_cache()` (which only frees the *unused* buffer pool) cannot reclaim them.

### 5.2 The caches build un‑detached per‑step graphs

DeepSeek‑V4 attention (`SparseCompressedAttention`) uses a `Compressor` + `Indexer`, each backed by a `PoolingCache`, plus a `RotatingKVCache` for local attention. The pooled cache grows like this (`mlx_lm/models/cache.py`, `PoolingCache.update_and_fetch`):

```python
self.pooled = mx.concatenate([self.pooled, px], axis=1)   # every `compress_ratio` steps
return self.pooled
```

Each step's `pooled_N` is a new array whose **input graph references `pooled_{N-1}`** (and so on). The cache object permanently holds the *head* (`self.pooled = pooled_N`). MLX keeps an array's inputs alive for as long as the array is alive, so the entire chain `pooled_N → pooled_{N-1} → … → pooled_0` — **and every intermediate's Metal buffer — stays resident**. `RotatingKVCache._update_in_place` and the `Batch*` variants chain the same way via sliced functional assignment (`self.keys[..., i:i+S, :] = keys` rebinds `self.keys` to a new array referencing the old).

### 5.3 Why the normal generation `eval` doesn't save us

The generation loop evaluates the sampled token each step (`mx.eval(y)`), and `y` depends on reading the caches, so `pooled_N`'s *value* is realized. But realizing an array's value is not the same as **detaching** it from its inputs: `pooled_N` remains an intermediate that still references `pooled_{N-1}`. Only an explicit `mx.eval` on the cache array (or otherwise detaching it) drops the inputs. Standard `KVCache`‑style caches avoid this because they write **in place into a pre‑allocated, fixed‑size buffer** (no growing concat chain) — so other models never hit it. DeepSeek‑V4's `concatenate`‑grown pooled cache is the model‑specific trigger.

> *Open question for maintainers (§9): is "the output eval doesn't detach intermediate cache arrays" the intended MLX semantics, and is there a more idiomatic fix than an explicit per‑step `eval`?*

### 5.4 Evidence

- **Leak rate:** active memory grows **strictly linearly, no plateau** through 2000 steps (~166–200 KB/step ≈ one buffer/layer/step). Rules out MoE expert‑paging (which would plateau).
- **Not a generic MLX bug:** 20,000 evals of a trivial fresh graph leak **zero** bytes.
- **Not `@mx.compile`:** identical slope with `mx.disable_compile()`.
- **Localized by ablation** (bypassing sub‑modules and measuring slope): leak is in the **attention path** (bypass attention → slope ~0; bypass MoE → unchanged; hyper‑connections → 0); within attention, the **compressor/indexer (pooled) path dominates**.
- **Confirmed mechanism + fix:** force‑evaluating the cache state each step drops the slope from ~205 to **7.1 KB/step**; force‑evaluating only `pooled` drops it to ~41; `mx.synchronize()` alone does nothing (it's graph retention, not a barrier issue).

---

## 6. The fix

Materialize all per‑layer cache state once per forward pass so the per‑step update graphs are detached and the resident‑buffer count stays bounded. Single hunk in `mlx_lm/models/deepseek_v4.py`, `DeepseekV4Model.__call__`, right after the decoder‑layer loop:

```python
        for layer, layer_cache in zip(self.pipeline_layers, cache):
            h = layer(h, mask, layer_cache, inputs)

        # Cut the per-decode-step lazy graphs in the attention caches. The
        # compressor/indexer PoolingCache (concatenate-grow) and RotatingKVCache
        # (sliced functional assignment), single and batched, otherwise keep the
        # prior step's intermediate arrays — and their Metal buffers — resident,
        # so num_resources_ climbs to resource_limit (499000) after ~11.3K tokens.
        if cache is not None:
            _cache_arrays = []
            for _c in cache:
                for _leaf in (getattr(_c, "caches", None) or (_c,)):
                    if _leaf is None:
                        continue
                    for _v in vars(_leaf).values():
                        if isinstance(_v, mx.array):
                            _cache_arrays.append(_v)
            if _cache_arrays:
                mx.eval(*_cache_arrays)
```

This is **one `mx.eval` per forward pass** (not per cache), so its cost is negligible (see §7 — no throughput change). It deliberately walks every leaf cache's array attributes rather than relying on a `.state` accessor, so it covers `PoolingCache`, `RotatingKVCache`, `BatchPoolingCache`, and `BatchRotatingKVCache` uniformly.

### 6.1 Why this location (and what didn't work)

We first tried fixing the cache classes individually:

1. **`PoolingCache.update_and_fetch` + `mx.eval(self.pooled, self.buf_*)`** → fixed the *in‑process* path (205 → 3.2 KB/step) but the **server still OOMed at ~11,300 tokens**: `mlx_lm`'s batch generator swaps in `BatchPoolingCache`, so the fix was bypassed.
2. **Also patch `BatchPoolingCache`** → server **still OOMed** at the same point. The dominant *batched‑path* leak is actually `BatchRotatingKVCache._update_in_place` (sliced assignment of `keys`/`values` + `mx.array` `left_padding`/`offset` updates, in all 43 layers). Per‑class patching is whack‑a‑mole across four cache classes (two of which — the rotating variants — are shared with other models, so editing them needs extra care).
3. **Single choke point in the model forward** (above) covers every cache class in one place and is the version we verified end‑to‑end.

**Alternative fix shapes** maintainers may prefer (all viable; we recommend the choke point for simplicity + coverage):
- Detach inside each DeepSeek‑V4 cache's update method (`PoolingCache` / `BatchPoolingCache`, plus the rotating variants). More "correctly layered," but more edit sites and touches shared classes.
- Handle per‑step cache materialization generically in the generation loop / a cache base method, if MLX considers this a general lazy‑eval‑vs‑residency concern (§9).

---

## 7. Verification

All on the environment in §2; patched = the §6 hunk only, `--temp 0.0`.

| Probe | Unpatched | Patched |
|---|---|---|
| In‑process leak slope | ~205 KB/step (linear, no plateau) | **7.1 KB/step** |
| Forced‑gen reproducer (§4) | OOM at **11,314** tokens | **CLEAN to 19,989 tokens** |
| Throughput (long gen) | ~31 tok/s | **31.3 tok/s** (no regression) |
| 40‑case tool‑call sweep, single long‑lived server | **49 Metal OOMs**, aborted (first OOM at case 20), 161 min | **0 Metal OOMs, 40/40 complete, 19.8 min** |

The sweep is the strongest signal for the cross‑request accumulation mode: the exact case that triggered the first OOM unpatched (`multi_email_after_calendar_read`) now completes cleanly, and the server never wedges.

*(Unrelated caveat: this checkpoint loops at `temp=0.0` on some prompts — a separate known issue, mitigated with `--temp 0.6`. It is orthogonal to this OOM; with the fix, a loop merely runs to `max_tokens` instead of crashing.)*

---

## 8. Suggested PR

- One‑hunk change in `mlx_lm/models/deepseek_v4.py` (§6), or the maintainer‑preferred location from §6.1.
- Link this analysis + the reproducer.
- Mention the verification numbers (§7).

---

## 9. Open questions for maintainers

1. **Eval semantics:** is it expected that evaluating the network output does not detach intermediate cache arrays from their input graph, so a cache holding the head of a `concatenate`/assignment chain pins every historical buffer? If so, should DeepSeek‑V4 caches detach in their update methods, or is there an idiomatic MLX primitive (e.g., an explicit `detach`) preferable to `mx.eval`?
2. **Right layer for the fix:** model forward (our choke point) vs. each cache class vs. the generation loop / cache base. Which fits mlx‑lm's conventions?
3. **`PoolingCache` design:** would switching the pooled cache from `concatenate`‑grow to step‑allocated **in‑place** writes (like `KVCache`/`RotatingKVCache._update_in_place`) remove the chain at the source and avoid needing any per‑step eval?
4. **`resource_limit`:** is 499000 device‑reported or an MLX default, and is exposing/raising it ever appropriate? (Not needed for this fix — bounding the count is the right answer — but worth confirming.)

---

## Appendix A — in‑process leak‑rate probe (no server)

Loads the model, runs a manual greedy decode loop, prints steady‑state active‑memory growth per step. Converges in <1 min and isolates the runtime from the server; useful as a regression check.

```python
import time, mlx.core as mx
from mlx_lm import load
from mlx_lm.models.cache import make_prompt_cache

MODEL = "<model-path>"; STEPS = 500; MB = 1024**2
model, tok = load(MODEL)
cache = make_prompt_cache(model)
y = mx.argmax(model(mx.array(tok.encode("Count upward:\n"))[None], cache=cache)[:, -1], axis=-1)
mx.eval(y)
base = mx.get_active_memory() / MB
for step in range(STEPS):
    y = mx.argmax(model(y[:, None], cache=cache)[:, -1], axis=-1)
    mx.eval(y)
    if step % 100 == 0:
        print(f"step {step:4d}  growth={mx.get_active_memory()/MB - base:+.1f} MB")
# unpatched: grows ~linearly (~0.2 MB/step). patched: stays flat (~0.007 MB/step).
```

To confirm the mechanism directly, add `mx.eval([c.state for c in cache])` after the per‑step `mx.eval(y)` on an *unpatched* runtime — the growth collapses to ~0, proving the leak is un‑evaluated cache‑update graphs.
