"""Metal-capture + residency-growth probe for the DeepSeek V4 Flash decode OOM.

Goal: pin the per-decode-step allocation that grows the Metal residency-set
resource COUNT (the ~499000 live-buffer cap, see fix-plan "Mechanism revision").

Two artifacts in one run:
  1. A .gputrace Metal frame capture of a few CONSECUTIVE decode steps at steady
     state (the per-step allocation pattern is constant, so a capture at step
     ~WARMUP is representative of the pattern at step 11,000 but far cheaper).
     Open in Xcode's Metal debugger to inspect what each step allocates / retains.
  2. A per-step memory trend (active / cache / peak GB) printed to stdout, so the
     live-byte growth rate is analyzable immediately without Xcode.

Run with MTL_CAPTURE_ENABLED=1 (required, else start_capture fails with
"Capture layer is not inserted").
"""
import argparse
import time

import mlx.core as mx
from mlx_lm import load
from mlx_lm.models.cache import make_prompt_cache

MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
GB = 1024 ** 3


def mem():
    return (
        mx.metal.get_active_memory() / GB,
        mx.metal.get_cache_memory() / GB,
        mx.metal.get_peak_memory() / GB,
    )


def cache_bytes(cache):
    """Sum nbytes across all leaf caches (recurses CacheList)."""
    total = 0
    for c in cache:
        subs = getattr(c, "caches", None)  # CacheList holds .caches
        items = subs if subs is not None else [c]
        for it in items:
            nb = getattr(it, "nbytes", None)
            if isinstance(nb, (int, float)):
                total += nb
    return total / GB


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--warmup", type=int, default=300,
                    help="decode steps before capture")
    ap.add_argument("--capture-steps", type=int, default=2,
                    help="consecutive decode steps to capture")
    ap.add_argument("--total", type=int, default=340,
                    help="total decode steps to run")
    ap.add_argument("--log-every", type=int, default=20)
    ap.add_argument("--capture-path",
                    default="/Users/vitor/LocalProjects/local-llms/bench/deepseek-v4-flash/logs/ds4_decode.gputrace")
    args = ap.parse_args()

    print(f"loading {MODEL} ...", flush=True)
    t0 = time.time()
    model, tokenizer = load(MODEL)
    print(f"loaded in {time.time()-t0:.1f}s; active={mem()[0]:.2f}GB", flush=True)

    prompt = tokenizer.encode("Count from one upward, one number word per line:\n")
    x = mx.array(prompt)[None]
    cache = make_prompt_cache(model)

    # Prefill
    logits = model(x, cache=cache)
    y = mx.argmax(logits[:, -1], axis=-1)
    mx.eval(y)
    a, c, p = mem()
    print(f"prefill done ({len(prompt)} tok): active={a:.2f} cache={c:.2f} "
          f"peak={p:.2f} cache_tensors={cache_bytes(cache):.3f}GB", flush=True)

    base_active = a
    captured = False
    for step in range(args.total):
        if step == args.warmup:
            print(f"[step {step}] START CAPTURE -> {args.capture_path}", flush=True)
            mx.metal.start_capture(args.capture_path)

        logits = model(y[:, None], cache=cache)
        y = mx.argmax(logits[:, -1], axis=-1)
        mx.eval(y)

        if step == args.warmup + args.capture_steps - 1:
            mx.metal.stop_capture()
            captured = True
            print(f"[step {step}] STOP CAPTURE (captured {args.capture_steps} steps)",
                  flush=True)

        if step % args.log_every == 0 or step == args.total - 1:
            a, c, p = mem()
            ct = cache_bytes(cache)
            print(f"[step {step:4d}] active={a:6.2f}GB cache={c:5.2f}GB "
                  f"peak={p:6.2f}GB cache_tensors={ct:6.3f}GB "
                  f"active_growth_vs_prefill={a-base_active:+.3f}GB", flush=True)

    print(f"DONE. capture_written={captured}", flush=True)


if __name__ == "__main__":
    main()
