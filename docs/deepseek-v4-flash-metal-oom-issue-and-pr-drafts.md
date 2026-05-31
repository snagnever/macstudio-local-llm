# Upstream contribution drafts — DeepSeek‑V4 Metal residency leak

Paste‑ready **issue** and **PR** bodies, condensed from
[`deepseek-v4-flash-metal-oom-upstream-writeup.md`](deepseek-v4-flash-metal-oom-upstream-writeup.md)
(link the full writeup, or a gist of it, for depth).

## ✅ Submitted 2026-05-30

- **Issue:** [ml-explore/mlx-lm#1332](https://github.com/ml-explore/mlx-lm/issues/1332)
- **PR:** [Blaizzy/mlx-lm#25](https://github.com/Blaizzy/mlx-lm/pull/25) (base `pc/add-deepseekv4flash-model`, head `snagnever:fix/deepseek-v4-metal-residency-leak`, 1 file / +22)
- **Heads-up comment on #1192:** [comment 4585428668](https://github.com/ml-explore/mlx-lm/pull/1192#issuecomment-4585428668) — links both the issue and the PR.

The drafts below are the source the posted bodies were condensed from.

---

## Targeting note (read first)

DeepSeek‑V4 support is **not merged** — it lives in open PR
[#1192](https://github.com/ml-explore/mlx-lm/pull/1192) (Blaizzy), stalled since 2026‑05‑01,
with multiple testers reporting this exact failure. So:

- **Issue:** file on `ml-explore/mlx-lm` referencing #1192 **and/or** post the same as a comment
  on #1192 (where the affected testers are). The reproducer there is the community signal.
- **PR:** must target the branch that actually contains `mlx_lm/models/deepseek_v4.py` — i.e.
  open it against **Blaizzy's `pc/add-deepseekv4flash-model` branch** (the head of #1192,
  @ `5c10538`), not `main` (the file doesn't exist in `main` yet). Mechanically: branch off that
  head in the `snagnever/mlx-lm` fork, apply the patch, push, then
  `gh pr create --repo Blaizzy/mlx-lm --base pc/add-deepseekv4flash-model --head snagnever:<branch>`.
  Alternatively, offer the patch as a comment on #1192 if the author prefers to fold it in.
- Keep `repetition_penalty`/quant‑quality remarks **out** of the PR — they're unrelated to the
  leak (noted at the end of the PR draft only as a heads‑up).

---

# ISSUE DRAFT

**Title:** DeepSeek‑V4 (Flash/Pro) on Apple Silicon: unbounded Metal residency growth during decode → `[metal::malloc] Resource limit (499000) exceeded` after ~11K tokens

**Body:**

### Summary
On Apple Silicon, the DeepSeek‑V4 port (#1192) aborts generation with
`RuntimeError: [metal::malloc] Resource limit (499000) exceeded` after **~11,300 generated
tokens, independent of prompt length**. After the first failure the Metal command queue is
wedged until a full process restart. This is the "looping / long‑context" failure several
testers have hit in this thread. Root cause is an unbounded per‑decode‑step leak of **live**
Metal buffers in the attention caches. (Fix in the linked PR.)

### Environment
- mlx‑lm @ #1192 head, **mlx 0.31.2**
- Apple **M4 Max, 128 GB**, macOS 26.3 (also reproduced on M3 by others in this thread, ~4000 tokens)
- `mlx-community/DeepSeek-V4-Flash-2bit-DQ`

### Reproduce
Server (`mlx_lm.server --max-tokens 65536`), then stream a long generation — it breaks at ~11,314 tokens:

```python
import json, urllib.request
body = {"model": MODEL, "stream": True, "max_tokens": 20000, "temperature": 0.0,
        "messages": [{"role":"user","content":"Count from 1 to 20000, one number word per line."}]}
# ... stream and count delta tokens; the connection drops at ~11,314 with the server-side OOM
```

In‑process (no server, converges in <1 min) — measures the leak rate directly:

```python
import mlx.core as mx
from mlx_lm import load
from mlx_lm.models.cache import make_prompt_cache
model, tok = load(MODEL); cache = make_prompt_cache(model); MB = 1024**2
y = mx.argmax(model(mx.array(tok.encode("Count upward:\n"))[None], cache=cache)[:, -1], -1); mx.eval(y)
base = mx.get_active_memory() / MB
for s in range(500):
    y = mx.argmax(model(y[:, None], cache=cache)[:, -1], -1); mx.eval(y)
    if s % 100 == 0: print(s, f"{mx.get_active_memory()/MB - base:+.1f} MB")
# active memory grows ~linearly, no plateau (~0.2 MB/step). Adding
# `mx.eval([c.state for c in cache])` after the per-step eval flattens it to ~0.
```

### Root cause
- **`resource_limit` (499000) is a count of live resident Metal buffers**, not bytes
  (`num_resources_` vs `resource_limit_` in `mlx/backend/metal/allocator.h`, backed by the
  `ResidencySet`). No byte‑budget knob (`set_memory_limit`/`set_wired_limit`/`set_cache_limit`)
  affects it. At the OOM point only ~2–3 GB is leaked — it's the *count* that's exhausted.
- **The attention caches build un‑detached per‑step graphs.** `PoolingCache.update_and_fetch`
  does `self.pooled = mx.concatenate([self.pooled, px], axis=1)` each step; `pooled_N`
  references `pooled_{N-1}` in its input graph, and the cache permanently holds the head, so
  **every prior step's intermediate array — and its Metal buffer — stays resident**.
  `RotatingKVCache._update_in_place` and the `Batch*` variants chain identically via sliced
  functional assignment. That's ~**one retained buffer per layer per step** → `499000 / 43
  layers ≈ 11.3K steps`, matching the observed failure point.
- Realizing the network output (`mx.eval(token)`) does **not** detach those intermediate cache
  arrays; explicitly evaluating the cache state each step collapses the growth (~205 → ~7
  KB/step). Standard in‑place `KVCache` writes don't hit this, which is why other models don't.

**It is not** a memory‑size problem, **not** a single‑forward‑pass / per‑command‑buffer
problem, and **not** prompt‑cache‑length driven (a 58‑token prompt OOMs at the same step count).

Full analysis + the diagnostic path (ablation, force‑eval, ruling out `mx.compile`/RoPE/expert‑paging):
**[full writeup](https://github.com/snagnever/macstudio-local-llm/blob/deepseek-v4-metal-oom-fix/docs/deepseek-v4-flash-metal-oom-upstream-writeup.md)**.
PR with the fix: **[Blaizzy/mlx-lm#25](https://github.com/Blaizzy/mlx-lm/pull/25)**.

---

# PR DRAFT

**Title:** Fix DeepSeek‑V4 Metal residency leak: materialize per‑layer cache state each forward

**Body:**

Fixes the Metal residency leak in the DeepSeek‑V4 port that aborts generation with
`[metal::malloc] Resource limit (499000) exceeded` after ~11K decode tokens on Apple Silicon
(see **[issue link]** for the full root cause).

### Cause (short)
The attention caches build per‑decode‑step lazy graphs that are never detached:
`PoolingCache` grows via `mx.concatenate`, `RotatingKVCache` via sliced assignment (and the
`Batch*` variants likewise). Because the cache object holds the *head* of the chain, MLX keeps
every prior step's intermediate array — and its backing Metal buffer — resident. The count of
live buffers grows ~one per layer per step until it hits the device residency cap (499000),
≈ 11.3K tokens regardless of prompt length.

### Change
Materialize all per‑layer cache state once per forward pass in `DeepseekV4Model.__call__`, which
detaches the chains so the resident‑buffer count stays bounded. One `mx.eval` per forward (not
per cache), so the cost is negligible.

```diff
         for layer, layer_cache in zip(self.pipeline_layers, cache):
             h = layer(h, mask, layer_cache, inputs)
+
+        # Cut the per-decode-step lazy graphs in the attention caches. PoolingCache
+        # (concatenate-grow) and RotatingKVCache (sliced assignment), single and
+        # batched, otherwise keep each prior step's intermediate arrays — and their
+        # Metal buffers — resident, so num_resources_ climbs to resource_limit
+        # (499000) after ~11.3K tokens. One eval per forward keeps the count bounded.
+        if cache is not None:
+            _cache_arrays = []
+            for _c in cache:
+                for _leaf in (getattr(_c, "caches", None) or (_c,)):
+                    if _leaf is None:
+                        continue
+                    for _v in vars(_leaf).values():
+                        if isinstance(_v, mx.array):
+                            _cache_arrays.append(_v)
+            if _cache_arrays:
+                mx.eval(*_cache_arrays)

         if pipeline_rank != 0:
```

### Verification (M4 Max 128 GB, mlx 0.31.2)
| | before | after |
|---|---|---|
| in‑process leak slope | ~205 KB/step (linear, no plateau) | **7 KB/step** |
| forced 20K‑token generation | OOM at **11,314** | **clean to 19,989**, 0 OOMs |
| throughput (long gen) | ~31 tok/s | **31.3 tok/s** (no regression) |
| 40‑request tool‑call sweep, single long‑lived server | **49 OOMs**, aborted at request 20 | **0 OOMs, 40/40, 19.8 min** |
| knowledge‑bench soak (MMLU+GPQA+HumanEval, **300 requests**), single long‑lived server | — | **0 OOMs, 300/300, 0 errors, ~2h44m** |

### Notes
- Walking each leaf cache's array attributes (rather than a `.state` accessor) covers
  `PoolingCache`/`RotatingKVCache`/`BatchPoolingCache`/`BatchRotatingKVCache` uniformly; a
  cache‑class‑local fix is possible but is whack‑a‑mole across four classes (two shared with
  other models).
- **Open question for maintainers:** is it intended that realizing the output doesn't detach
  intermediate cache arrays? A cleaner long‑term fix might be storing the pooled cache with
  step‑allocated **in‑place** writes (like `KVCache`/`RotatingKVCache._update_in_place`) instead
  of `concatenate`, removing the chain at the source.
- *(Unrelated heads‑up, not part of this fix:* the 2‑bit DQ checkpoint degenerates/loops in
  open‑ended chat — a quantization‑quality issue independent of this leak.*)*

### Targeting
DeepSeek‑V4 isn't in `main`; this targets the #1192 head branch
`Blaizzy:pc/add-deepseekv4flash-model` (which is where `mlx_lm/models/deepseek_v4.py` lives).
