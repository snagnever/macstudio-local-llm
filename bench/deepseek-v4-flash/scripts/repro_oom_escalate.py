"""Escalating cache-length OOM probe.

Sends single requests with increasing prompt sizes (max_tokens small) against
one server, until one OOMs. Pinpoints the decode/forward-pass cache-length
threshold where DeepSeek V4 Flash trips Apple Metal's resource_limit. Clean
requests don't wedge the server, so we can escalate in one session; the OOM
request hangs (post-OOM wedge) so it trips the per-request timeout -> we report
the failing size and stop.

Reports prompt_tokens per step. If all sizes pass clean, the trigger is NOT
cache-length (likely generation-step-count); fall back to forced long gen.
"""
import argparse
import json
import sys
import time
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8765/v1"
DEFAULT_MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"

_SEG = (
    "In section {n}, the system processes data block number {n} using "
    "pipeline stage {n} and records metric {n} for later analysis. "
)


def build_prompt(target_tokens):
    segs = max(1, target_tokens // 29)
    body = "".join(_SEG.format(n=i) for i in range(segs))
    return (
        "Read the following log carefully, then answer in one word: how many "
        "sections are described?\n\n" + body
    )


def one(base, model, target, max_tokens, timeout):
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": build_prompt(target)}],
            "max_tokens": max_tokens,
            "temperature": 0.0,
        }
    ).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    dt = time.time() - t0
    return dt, d.get("usage", {}).get("prompt_tokens", "?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--sizes", default="14000,16000,18000,20000,24000,28000,32000")
    ap.add_argument("--max-tokens", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=220)
    args = ap.parse_args()

    sizes = [int(s) for s in args.sizes.split(",")]
    for target in sizes:
        try:
            dt, ptoks = one(args.base_url, args.model, target, args.max_tokens, args.timeout)
            print(f"ctx~={target:6d}  p={ptoks!s:>6}  {dt:6.1f}s  OK", flush=True)
        except Exception as e:
            dt = "?"
            print(f"ctx~={target:6d}  FAIL  {type(e).__name__}: {e}", flush=True)
            print(f"OOM_THRESHOLD: first failure at ctx~={target}", flush=True)
            sys.exit(1)
    print("ALL_CLEAN: no size tripped the cap (trigger is not cache-length)")


if __name__ == "__main__":
    main()
