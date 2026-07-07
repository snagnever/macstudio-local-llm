"""R3 — split the per-step leak between Compressor and Indexer.

Block ablation showed the leak is in attention; inner ablation showed ~83% is the
compressor+indexer together. This splits them. All modes route attention through the
CHEAP local path (so the growing-pooled dense-attention confound is removed); the only
difference is which machinery (+ which PoolingCache) runs:

  full           : real SparseCompressedAttention.__call__
  compressor_only: run self.compressor (comp_cache grows), SKIP indexer, local attn
  indexer_only   : SKIP compressor (pooled empty), run self.indexer (idx_cache), local attn
  neither        : core local attn only (== inner_ablation_probe local_only, ~34.5)

Read (vs full≈205, neither≈34.5 KB/step):
  compressor_only - neither  ≈ compressor's contribution
  indexer_only    - neither  ≈ indexer's contribution
  the two contributions should ≈ (full - neither), the 83%.
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


def _qkv(self, x, cache):
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
    return B, L, local_cache, offset, q_residual, q, kv


def _oproj(self, out, offset, B, L):
    out = self.rope(out, offset, inverse=True)
    out = out.reshape(B, self.o_groups, -1, L, self.head_dim)
    out = out.transpose(0, 1, 3, 2, 4).flatten(-2)
    out = self.wo_a(out)
    out = out.transpose(0, 2, 1, 3).flatten(-2)
    return self.wo_b(out)


def make_call(mode):
    def __call__(self, x, mask=None, cache=None):
        B, L, local_cache, offset, q_residual, q, kv = _qkv(self, x, cache)
        comp_cache = cache[1] if cache is not None else None
        idx_cache = cache[2] if cache is not None else None
        if mode == "compressor_only":
            _ = self.compressor(x, comp_cache, offset)          # exercise compressor
        elif mode == "indexer_only":
            _ = self.indexer(x, q_residual, self.rope, idx_cache, offset)  # exercise indexer
        sinks = self.attn_sink.astype(q.dtype)
        out = sdpa(q, kv, kv, cache=local_cache, scale=self.scale, mask=mask, sinks=sinks)
        return _oproj(self, out, offset, B, L)
    return __call__


def run_mode(model, tokenizer, mode):
    ds4.SparseCompressedAttention.__call__ = _orig if mode == "full" else make_call(mode)
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
    print(f"  MODE={mode:16s} slope={slope:7.1f} KB/step  total={samples[-1][1]:7.2f} MB",
          flush=True)
    return slope


def main():
    t0 = time.time()
    model, tokenizer = load(MODEL)
    print(f"loaded in {time.time()-t0:.1f}s\n", flush=True)
    modes = ["full", "compressor_only", "indexer_only", "neither"]
    res = {}
    for m in modes:
        try:
            res[m] = run_mode(model, tokenizer, m)
        except Exception as e:
            res[m] = None
            print(f"  MODE={m:16s} ERROR {type(e).__name__}: {e}", flush=True)
    ds4.SparseCompressedAttention.__call__ = _orig
    print("\n=== R3 SUMMARY (KB/step) ===", flush=True)
    full, neither = res.get("full"), res.get("neither")
    for m in modes:
        s = res[m]
        extra = ""
        if s is not None and neither is not None and m in ("compressor_only", "indexer_only"):
            extra = f"  contribution≈{s - neither:+.1f}"
        print(f"  {m:16s} {('ERR' if s is None else f'{s:7.1f}')}{extra}", flush=True)
    if full is not None and neither is not None:
        print(f"\n  full-neither (the 83% to split) = {full - neither:.1f} KB/step", flush=True)


if __name__ == "__main__":
    main()
