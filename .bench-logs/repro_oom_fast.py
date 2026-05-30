"""Fast OOM probe for DeepSeek V4 Flash on Apple Metal.

The OOM is in the *forward pass* at large cache length (confirmed: it surfaces
at hyper_connection.py during a single-token decode step, generate.py _step).
Long prompts alone are clean because prefill is chunked; long *generation* OOMs
because each decode step is one unchunked forward pass over the full cache.

To trigger fast WITHOUT generating thousands of tokens slowly, send one large
prompt (~CTX tokens) with a tiny max_tokens. The late prefill chunks + first
decode steps then run the forward pass at cache length ~CTX, hitting the
resource_limit in seconds rather than after a 20-min generation.

Pass:  request returns HTTP 200 cleanly  -> prints OK, exits 0.
Fail:  request errors (HTTP 500 / OOM) or times out -> prints FAIL, exits 1.
"""
import argparse
import json
import sys
import time
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8765/v1"
DEFAULT_MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"

# Distinct-ish filler so tokenization isn't degenerate. ~6 tokens/segment.
_SEG = (
    "In section {n}, the system processes data block number {n} using "
    "pipeline stage {n} and records metric {n} for later analysis. "
)


def build_prompt(target_tokens):
    # Measured ~29 tokens per formatted segment on this tokenizer.
    segs = max(1, target_tokens // 29)
    body = "".join(_SEG.format(n=i) for i in range(segs))
    return (
        "Read the following log carefully, then answer in one word: how many "
        "sections are described?\n\n" + body
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--ctx", type=int, default=12000, help="approx prompt tokens")
    ap.add_argument("--max-tokens", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=240)
    args = ap.parse_args()

    prompt = build_prompt(args.ctx)
    payload = json.dumps(
        {
            "model": args.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": args.max_tokens,
            "temperature": 0.0,
        }
    ).encode()
    req = urllib.request.Request(
        f"{args.base_url}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    print(f"ctx~={args.ctx} chars={len(prompt)} timeout={args.timeout}s", flush=True)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as r:
            d = json.loads(r.read())
        dt = time.time() - t0
        ptoks = d.get("usage", {}).get("prompt_tokens", "?")
        ctoks = d.get("usage", {}).get("completion_tokens", "?")
        print(f"{dt:6.1f}s  p={ptoks} c={ctoks}  OK", flush=True)
        sys.exit(0)
    except Exception as e:
        dt = time.time() - t0
        print(f"{dt:6.1f}s  FAIL  {type(e).__name__}: {e}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
