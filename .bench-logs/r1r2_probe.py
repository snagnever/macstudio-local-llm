"""R1 (count/fingerprint retained arrays) + R2 (force-eval cache state) probes.

R1a: is mx.array visible to gc? (decides if R1b is possible)
R1 : full decode; per-sample gc live-array count + shape histogram (if gc-visible)
     AND deep cache introspection (arrays/lists held by each cache + shapes).
     Goal: find the bucket that grows ~43/step and whether it's inside the caches.
R2 : compare steady-state slope of:
       baseline           - plain decode (== leak_probe, ~200 KB/step)
       R2a force-eval all  - mx.eval all cache state each step
       R2b force-eval pooled- mx.eval only PoolingCache.pooled each step
       R2c sync+gc          - mx.synchronize()+gc.collect() each step, no state eval
     slope -> ~0 in R2a/R2b => lazy-graph retention in the cache (= the fix).
"""
import gc
import time
from collections import Counter

import mlx.core as mx
from mlx.utils import tree_flatten
from mlx_lm import load
from mlx_lm.models.cache import make_prompt_cache

MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
KB = 1024
MB = 1024 ** 2
STEPS = 320


def leaf_caches(cache):
    for c in cache:
        subs = getattr(c, "caches", None)
        if subs is not None:
            yield from subs
        else:
            yield c


def cache_introspect(cache):
    """Return (#arrays held by caches, Counter of (cls,attr,shape), growing list lens)."""
    cnt = Counter()
    n = 0
    lists = []
    for c in leaf_caches(cache):
        for k, v in vars(c).items():
            if isinstance(v, mx.array):
                cnt[(type(c).__name__, k, tuple(v.shape))] += 1
                n += 1
            elif isinstance(v, (list, tuple)):
                for it in v:
                    if isinstance(it, mx.array):
                        cnt[(type(c).__name__, k + "[]", tuple(it.shape))] += 1
                        n += 1
                if v:
                    lists.append((type(c).__name__, k, len(v)))
    return n, cnt, lists


def gc_arrays():
    return [o for o in gc.get_objects() if isinstance(o, mx.array)]


def decode(model, cache, y, steps, hook=None):
    base = mx.get_active_memory() / MB
    samples = []
    for step in range(steps):
        logits = model(y[:, None], cache=cache)
        y = mx.argmax(logits[:, -1], axis=-1)
        mx.eval(y)
        if hook is not None:
            hook(step, cache)
        if step % 40 == 0 or step == steps - 1:
            samples.append((step, mx.get_active_memory() / MB - base))
    half = samples[len(samples) // 2:]
    (s0, g0), (s1, g1) = half[0], half[-1]
    slope = (g1 - g0) / max(s1 - s0, 1) * KB
    return slope, y


def fresh(model, tokenizer):
    prompt = tokenizer.encode("Count from one upward, one number word per line:\n")
    cache = make_prompt_cache(model)
    logits = model(mx.array(prompt)[None], cache=cache)
    y = mx.argmax(logits[:, -1], axis=-1)
    mx.eval(y)
    return cache, y


def main():
    t0 = time.time()
    model, tokenizer = load(MODEL)
    print(f"loaded in {time.time()-t0:.1f}s\n", flush=True)

    # ---- R1a: gc visibility ----
    probe = [mx.zeros((2, 2)) for _ in range(1000)]
    mx.eval(*probe)
    gc_visible = sum(1 for o in gc.get_objects() if isinstance(o, mx.array))
    del probe
    print(f"[R1a] mx.array visible to gc.get_objects(): {gc_visible}/1000 "
          f"-> R1b {'ENABLED' if gc_visible > 500 else 'DISABLED (rely on R1c)'}\n", flush=True)

    # ---- R1: full decode with per-sample gc + cache introspection ----
    print("[R1] full decode, sampling gc live-array count + cache introspection", flush=True)
    cache, y = fresh(model, tokenizer)
    prev_hist = None

    def r1_hook(step, cache):
        nonlocal prev_hist
        if step % 80 != 0 and step != STEPS - 1:
            return
        gc.collect()
        n_cache, ccnt, lists = cache_introspect(cache)
        line = f"  step {step:4d}: cache_arrays={n_cache}"
        if gc_visible > 500:
            arrs = gc_arrays()
            hist = Counter((tuple(o.shape), str(o.dtype)) for o in arrs)
            line += f"  gc_live_arrays={len(arrs)}  non_cache≈{len(arrs)-n_cache}"
            print(line, flush=True)
            # top growing buckets vs previous sample
            if prev_hist is not None:
                deltas = sorted(((hist[k] - prev_hist.get(k, 0), k) for k in hist),
                                reverse=True)[:6]
                for d, k in deltas:
                    if d > 0:
                        print(f"      +{d:5d}  shape={k[0]} {k[1]}", flush=True)
            prev_hist = hist
        else:
            print(line, flush=True)
        # cache buckets whose count > 1 or shapes (always show pooled-like growth)
        big = sorted(ccnt.items(), key=lambda kv: -kv[1])[:6]
        for (cls, attr, shape), c in big:
            print(f"      cache {cls}.{attr} shape={shape} x{c}", flush=True)
        if lists:
            print(f"      growing lists: {lists[:4]}", flush=True)

    slope_base, _ = decode(model, cache, y, STEPS, hook=r1_hook)
    print(f"[R1] baseline slope = {slope_base:.1f} KB/step\n", flush=True)

    # ---- R2a: force-eval ALL cache state ----
    def r2a_hook(step, cache):
        leaves = [v for _, v in tree_flatten([c.state for c in cache])
                  if isinstance(v, mx.array)]
        if leaves:
            mx.eval(*leaves)
    cache, y = fresh(model, tokenizer)
    slope_r2a, _ = decode(model, cache, y, STEPS, hook=r2a_hook)
    print(f"[R2a] force-eval ALL cache state: slope = {slope_r2a:.1f} KB/step "
          f"(baseline {slope_base:.1f})", flush=True)

    # ---- R2b: force-eval only PoolingCache.pooled ----
    def r2b_hook(step, cache):
        ps = [c.pooled for c in leaf_caches(cache)
              if type(c).__name__ == "PoolingCache" and getattr(c, "pooled", None) is not None]
        if ps:
            mx.eval(*ps)
    cache, y = fresh(model, tokenizer)
    slope_r2b, _ = decode(model, cache, y, STEPS, hook=r2b_hook)
    print(f"[R2b] force-eval pooled only:     slope = {slope_r2b:.1f} KB/step", flush=True)

    # ---- R2c: synchronize + gc.collect, no state eval ----
    def r2c_hook(step, cache):
        mx.synchronize()
        if step % 10 == 0:
            gc.collect()
    cache, y = fresh(model, tokenizer)
    slope_r2c, _ = decode(model, cache, y, STEPS, hook=r2c_hook)
    print(f"[R2c] synchronize+gc:             slope = {slope_r2c:.1f} KB/step", flush=True)

    print("\n=== R2 SUMMARY (KB/step) ===", flush=True)
    print(f"  baseline        {slope_base:7.1f}", flush=True)
    print(f"  R2a eval-all    {slope_r2a:7.1f}  ({slope_r2a/slope_base*100 if slope_base else 0:4.0f}% of base)", flush=True)
    print(f"  R2b eval-pooled {slope_r2b:7.1f}  ({slope_r2b/slope_base*100 if slope_base else 0:4.0f}% of base)", flush=True)
    print(f"  R2c sync+gc     {slope_r2c:7.1f}  ({slope_r2c/slope_base*100 if slope_base else 0:4.0f}% of base)", flush=True)


if __name__ == "__main__":
    main()
