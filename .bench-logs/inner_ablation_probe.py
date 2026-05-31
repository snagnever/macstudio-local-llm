"""Drill the attention leak: core local-attention path vs sparse machinery.

The block ablation localized the per-step residency leak to attention. This
splits SparseCompressedAttention into:
  - full        : the real forward (compressor + indexer + sparse/compressed/local)
  - local_only  : ONLY core q/kv/rope/sdpa/o-proj (skips compressor + indexer)

If local_only's slope -> ~0, the leak is in the compressor/indexer (the pooled
sparse path unique to DeepSeek V4). If it persists, it's the core attention path.
"""
import time

import mlx.core as mx
import mlx_lm.models.deepseek_v4 as ds4
from mlx_lm import load
from mlx_lm.models.cache import make_prompt_cache

MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
KB = 1024
MB = 1024 ** 2
STEPS = 320
sdpa = ds4.scaled_dot_product_attention

_orig = ds4.SparseCompressedAttention.__call__


def local_only_call(self, x, mask=None, cache=None):
    B, L, _ = x.shape
    local_cache = cache[0] if cache is not None else None
    offset = local_cache.offset if local_cache is not None else 0
    offset = mx.array(offset) if isinstance(offset, mx.array) else offset

    q_residual = self.q_norm(self.wq_a(x))
    q = self.wq_b(q_residual).reshape(B, L, self.n_heads, self.head_dim)
    q = mx.fast.rms_norm(q, None, self.config.rms_norm_eps)
    q = q.transpose(0, 2, 1, 3)
    q = self.rope(q, offset)

    kv = self.kv_norm(self.wkv(x)).reshape(B, 1, L, self.head_dim)
    kv = self.rope(kv, offset)
    if local_cache is not None:
        kv, _ = local_cache.update_and_fetch(kv, mx.zeros((B, 1, L, 0)))

    sinks = self.attn_sink.astype(q.dtype)
    out = sdpa(q, kv, kv, cache=local_cache, scale=self.scale, mask=mask, sinks=sinks)
    out = self.rope(out, offset, inverse=True)
    out = out.reshape(B, self.o_groups, -1, L, self.head_dim)
    out = out.transpose(0, 1, 3, 2, 4).flatten(-2)
    out = self.wo_a(out)
    out = out.transpose(0, 2, 1, 3).flatten(-2)
    out = self.wo_b(out)
    return out


def run_mode(model, tokenizer, mode):
    ds4.SparseCompressedAttention.__call__ = (
        local_only_call if mode == "local_only" else _orig
    )
    prompt = tokenizer.encode("Count from one upward, one number word per line:\n")
    cache = make_prompt_cache(model)
    logits = model(mx.array(prompt)[None], cache=cache)
    y = mx.argmax(logits[:, -1], axis=-1)
    mx.eval(y)
    base = mx.get_active_memory() / MB
    samples = []
    for step in range(STEPS):
        logits = model(y[:, None], cache=cache)
        y = mx.argmax(logits[:, -1], axis=-1)
        mx.eval(y)
        if step % 40 == 0 or step == STEPS - 1:
            samples.append((step, mx.get_active_memory() / MB - base))
    half = samples[len(samples) // 2:]
    (s0, g0), (s1, g1) = half[0], half[-1]
    slope = (g1 - g0) / max(s1 - s0, 1) * KB
    print(f"  MODE={mode:11s} slope={slope:7.1f} KB/step  total={samples[-1][1]:7.2f} MB",
          flush=True)
    return slope


def main():
    t0 = time.time()
    model, tokenizer = load(MODEL)
    print(f"loaded in {time.time()-t0:.1f}s\n", flush=True)
    res = {m: run_mode(model, tokenizer, m) for m in ("full", "local_only")}
    ds4.SparseCompressedAttention.__call__ = _orig
    full = res["full"]
    print("\n=== SUMMARY ===", flush=True)
    for m, s in res.items():
        print(f"  {m:11s} {s:7.1f} KB/step  ({(s/full*100) if full else 0:5.0f}% of full)",
              flush=True)
    print("\nlocal_only ~0 => leak is in compressor/indexer (sparse pooled path).",
          flush=True)


if __name__ == "__main__":
    main()
