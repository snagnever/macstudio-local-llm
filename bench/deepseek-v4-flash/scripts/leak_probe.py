"""Localize the per-decode-step residency leak: is it mx.compile retention?

Runs a short decode loop and reports the active-memory growth slope (MB/step),
which extrapolates to the ~499000 live-buffer residency cap. Toggle
--disable-compile to test whether @mx.compile buffer retention is the source.
"""
import argparse
import time

import mlx.core as mx

MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
MB = 1024 ** 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disable-compile", action="store_true")
    ap.add_argument("--steps", type=int, default=320)
    args = ap.parse_args()

    if args.disable_compile:
        mx.disable_compile()
        print("mx.disable_compile() ACTIVE", flush=True)

    from mlx_lm import load
    from mlx_lm.models.cache import make_prompt_cache

    t0 = time.time()
    model, tokenizer = load(MODEL)
    print(f"loaded in {time.time()-t0:.1f}s", flush=True)

    prompt = tokenizer.encode("Count from one upward, one number word per line:\n")
    cache = make_prompt_cache(model)
    logits = model(mx.array(prompt)[None], cache=cache)
    y = mx.argmax(logits[:, -1], axis=-1)
    mx.eval(y)

    samples = []  # (step, active_MB)
    base = mx.get_active_memory() / MB
    for step in range(args.steps):
        logits = model(y[:, None], cache=cache)
        y = mx.argmax(logits[:, -1], axis=-1)
        mx.eval(y)
        if step % 40 == 0 or step == args.steps - 1:
            a = mx.get_active_memory() / MB
            samples.append((step, a - base))
            print(f"[step {step:4d}] active_growth={a-base:+8.2f} MB", flush=True)

    # crude slope over the back half (steady state)
    half = samples[len(samples) // 2:]
    if len(half) >= 2:
        (s0, g0), (s1, g1) = half[0], half[-1]
        slope = (g1 - g0) / max(s1 - s0, 1)
        print(f"STEADY-STATE SLOPE: {slope*1000:.1f} KB/step "
              f"(=> {slope*1024/ (499000):.3g} ... ) ; total {samples[-1][1]:.1f}MB "
              f"over {args.steps} steps", flush=True)
        # extrapolate steps to 2.3GB-equiv is not the cap; report buffers proxy:
        print(f"EXTRAPOLATED MB at 11300 steps: {slope*11300:.0f} MB", flush=True)


if __name__ == "__main__":
    main()
