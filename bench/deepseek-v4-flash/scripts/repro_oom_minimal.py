"""Minimal OOM reproducer.

Hits a single long-lived mlx-lm server N times in one GROWING conversation
(prompt cache / pooled_seq grows monotonically across turns -- the warm-cache
scenario that trips Apple Metal's per-command-buffer resource_limit). Reports
the first failing turn. Faithful to the fix-plan 0.2 intent ("growing the
per-request context") which is more sensitive than independent short prompts.

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

# Each turn elaborates on the running thread so context accumulates (~250
# tok/turn -> ~6k tokens by turn 25, well past spicyneuron's ~4000 trip point).
FOLLOWUPS = [
    "Explain in detail how a CPU pipeline works.",
    "Now expand on hazards: structural, data, and control hazards.",
    "Add concrete examples of branch prediction strategies.",
    "Compare RISC and CISC with historical examples.",
    "Explain out-of-order execution and register renaming.",
    "Describe cache hierarchies and coherence protocols.",
    "Now cover SIMD and vector processing in depth.",
    "Explain how GPUs differ architecturally from CPUs.",
    "Describe memory consistency models.",
    "Explain virtual memory and the TLB.",
    "Now cover multi-core scaling and Amdahl's law.",
    "Describe speculative execution side-channel attacks.",
    "Explain how TPUs accelerate matrix multiplication.",
    "Cover the history of the transistor and Moore's law.",
    "Describe superscalar execution with examples.",
    "Explain how out-of-order retirement works.",
    "Now cover the von Neumann bottleneck.",
    "Describe interconnect topologies in multi-socket systems.",
    "Explain how prefetchers improve performance.",
    "Cover NUMA and its performance implications.",
    "Describe how instruction decoding works in x86.",
    "Explain micro-op fusion and macro-op fusion.",
    "Now summarize the key tradeoffs across the whole discussion.",
    "Add a section on neuromorphic computing.",
    "Finally, predict the next decade of CPU architecture.",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--turns", type=int, default=25)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    messages = [
        {
            "role": "user",
            "content": "Write a detailed technical essay on computer "
            "architecture history from ENIAC to today. Be thorough.",
        }
    ]
    n = min(args.turns, len(FOLLOWUPS) + 1)
    for i in range(1, n + 1):
        payload = json.dumps(
            {
                "model": args.model,
                "messages": messages,
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
            content = d["choices"][0]["message"]["content"]
            toks = d.get("usage", {}).get("completion_tokens", "?")
            print(f"{i:2d}/{n}  {dt:6.1f}s  {toks!s:>4}tok  OK", flush=True)
            messages.append({"role": "assistant", "content": content})
            if i - 1 < len(FOLLOWUPS):
                messages.append({"role": "user", "content": FOLLOWUPS[i - 1]})
        except Exception as e:
            dt = time.time() - t0
            print(f"{i:2d}/{n}  {dt:6.1f}s  FAIL  {type(e).__name__}: {e}", flush=True)
            sys.exit(1)
    print(f"REPRO_CLEAN: all {n} requests succeeded")


if __name__ == "__main__":
    main()
