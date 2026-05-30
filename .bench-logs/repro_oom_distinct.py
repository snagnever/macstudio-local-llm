"""Distinct-sequence OOM reproducer.

Sends N INDEPENDENT single-turn requests (no shared history) against one
long-lived mlx-lm server. Each distinct prompt registers a new cached
sequence; resource count scales with n_cached_sequences. This mirrors the
jdhodges failure mode (first Metal OOM observed at case ~20 on the unpatched
runtime) far better than a single growing conversation -- spicyneuron's long
single-prompt probe is clean on this rig, so the trigger is sequence COUNT,
not prompt length.

Pass:  prints "REPRO_CLEAN: all N requests succeeded" and exits 0.
Fail:  any request raises (HTTP 500 / OOM / timeout); prints FAIL, exits 1.
"""
import argparse
import json
import sys
import time
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8765/v1"
DEFAULT_MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"

TOPICS = [
    "the French Revolution", "photosynthesis", "the theory of relativity",
    "the Roman aqueducts", "quantum entanglement", "the printing press",
    "plate tectonics", "the human immune system", "the Silk Road",
    "black holes", "the Industrial Revolution", "DNA replication",
    "the stock market crash of 1929", "neural networks", "the Apollo program",
    "ocean currents", "the Renaissance", "antibiotics", "the internet's origins",
    "volcanic eruptions", "the cold war", "machine translation",
    "the water cycle", "the Byzantine Empire", "superconductors",
    "the French language", "coral reefs", "the Manhattan Project",
    "genetic engineering", "the Great Wall of China", "dark matter",
    "the Mongol Empire", "vaccines", "the transistor", "monsoons",
    "the Ottoman Empire", "enzymes", "the space shuttle", "tectonic faults",
    "the Enlightenment",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    n = min(args.n, len(TOPICS))
    for i in range(1, n + 1):
        topic = TOPICS[i - 1]
        prompt = (
            f"Write a detailed, multi-paragraph explanation of {topic}. "
            "Include historical context, key mechanisms, and significance."
        )
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
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as r:
                d = json.loads(r.read())
            dt = time.time() - t0
            toks = d.get("usage", {}).get("completion_tokens", "?")
            print(f"{i:2d}/{n}  {dt:6.1f}s  {toks!s:>4}tok  OK", flush=True)
        except Exception as e:
            dt = time.time() - t0
            print(f"{i:2d}/{n}  {dt:6.1f}s  FAIL  {type(e).__name__}: {e}", flush=True)
            sys.exit(1)
    print(f"REPRO_CLEAN: all {n} requests succeeded")


if __name__ == "__main__":
    main()
