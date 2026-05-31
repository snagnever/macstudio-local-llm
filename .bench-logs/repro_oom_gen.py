"""Streaming forced-generation OOM probe.

The OOM is NOT a single-forward-pass / cache-length cap (prefill + a few decode
steps is clean even at 60K context). It accumulates across many DECODE STEPS in
the generation loop. This probe forces a long generation, streams the output,
and counts how many tokens are produced before the stream breaks (OOM) -- so we
learn the tokens-to-OOM count without a 20-min non-streaming hang.

Pass:  stream completes (reaches max_tokens or natural stop) -> prints CLEAN.
Fail:  stream breaks early (OOM / connection reset) -> prints OOM_AT with count.
"""
import argparse
import json
import sys
import time
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8765/v1"
DEFAULT_MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"

PROMPT = (
    "Count from 1 to 20000. Write each number as an English word on its own "
    "line (one, two, three, four, ...). Do not skip any number, do not "
    "summarize, and do not stop early. Continue until you reach twenty thousand."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=20000)
    ap.add_argument("--timeout", type=int, default=2400)
    args = ap.parse_args()

    payload = json.dumps(
        {
            "model": args.model,
            "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": args.max_tokens,
            "temperature": 0.0,
            "stream": True,
        }
    ).encode()
    req = urllib.request.Request(
        f"{args.base_url}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    n = 0
    t0 = time.time()
    last_report = 0
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as r:
            for raw in r:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    dt = time.time() - t0
                    print(f"CLEAN: streamed {n} tokens in {dt:.1f}s "
                          f"({n/max(dt,1):.1f} t/s)", flush=True)
                    sys.exit(0)
                try:
                    obj = json.loads(data)
                    delta = obj["choices"][0].get("delta", {})
                    if delta.get("content"):
                        n += 1
                        if n - last_report >= 1000:
                            last_report = n
                            print(f"  ...{n} tokens, {time.time()-t0:.0f}s",
                                  flush=True)
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass
    except Exception as e:
        dt = time.time() - t0
        print(f"OOM_AT: stream broke after {n} tokens in {dt:.1f}s -- "
              f"{type(e).__name__}: {e}", flush=True)
        sys.exit(1)
    dt = time.time() - t0
    print(f"CLEAN: stream ended after {n} tokens in {dt:.1f}s", flush=True)


if __name__ == "__main__":
    main()
