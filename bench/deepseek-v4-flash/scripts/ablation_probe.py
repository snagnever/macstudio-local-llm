"""Localize the per-decode-step residency leak to a block sub-module.

Monkeypatches DeepseekV4Block.__call__ to bypass attention / MoE-FFN / both,
and reports the active-memory growth slope (KB/step) for each mode. Whichever
bypass drives the slope to ~0 contains the leak. Shapes stay valid in every
mode (HyperConnection collapses H->1 to (B,L,D); hc_expand re-expands), so the
decode loop runs end-to-end without correctness (irrelevant for slope).

One model load; slope is measured WITHIN each mode against a per-mode baseline,
so cross-mode residency drift does not affect the per-mode slope.
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
MODES = ["full", "no_attn", "no_ffn", "hc_only"]

_orig_call = ds4.DeepseekV4Block.__call__
_hc_expand = ds4.hc_expand


def make_call(mode):
    def __call__(self, h, mask, cache, input_ids):
        residual = h
        x, post, comb = self.attn_hc(h)
        if mode not in ("no_attn", "hc_only"):
            x = self.attn(self.attn_norm(x), mask=mask, cache=cache)
        h = _hc_expand(x, residual, post, comb)

        residual = h
        x, post, comb = self.ffn_hc(h)
        if mode not in ("no_ffn", "hc_only"):
            x = self.ffn(self.ffn_norm(x), input_ids)
        return _hc_expand(x, residual, post, comb)
    return __call__


def run_mode(model, tokenizer, mode):
    ds4.DeepseekV4Block.__call__ = make_call(mode)
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
    slope_kb = (g1 - g0) / max(s1 - s0, 1) * KB
    print(f"  MODE={mode:8s} slope={slope_kb:7.1f} KB/step  "
          f"total={samples[-1][1]:7.2f} MB over {STEPS} steps", flush=True)
    return slope_kb


def main():
    t0 = time.time()
    model, tokenizer = load(MODEL)
    print(f"loaded in {time.time()-t0:.1f}s; running ablations "
          f"({STEPS} steps each)\n", flush=True)
    results = {}
    for mode in MODES:
        results[mode] = run_mode(model, tokenizer, mode)
    ds4.DeepseekV4Block.__call__ = _orig_call

    print("\n=== SUMMARY (KB/step) ===", flush=True)
    full = results["full"]
    for mode in MODES:
        s = results[mode]
        frac = (s / full * 100) if full else 0
        print(f"  {mode:8s} {s:7.1f}  ({frac:5.0f}% of full)", flush=True)
    print("\nInterpretation: the mode whose slope drops toward ~0 removed the "
          "leaking sub-module. hc_only = leak from HyperConnections alone.",
          flush=True)


if __name__ == "__main__":
    main()
