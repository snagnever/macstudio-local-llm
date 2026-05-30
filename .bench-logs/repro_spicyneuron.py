#!/usr/bin/env python3
"""Standalone DeepSeek V4 loop repro for an OpenAI-compatible mlx-lm server."""

import argparse
import json
import re
import ssl
import sys
import urllib.request
from collections import Counter

PROMPTS = [
    (
        "Write a long, detailed technical essay on the history of computer "
        "architecture from the 1940s to today. Cover ENIAC, von Neumann "
        "architecture, the transistor, integrated circuits, microprocessors, "
        "RISC vs CISC, pipelining, superscalar execution, out-of-order "
        "execution, branch prediction, caches, multi-core, SIMD, GPUs, TPUs, "
        "and neuromorphic computing. Be thorough and technical."
    ),
    (
        "Continue from the previous answer. Expand the RISC vs CISC, "
        "pipelining, superscalar execution, out-of-order execution, and branch "
        "prediction sections with concrete historical examples and design "
        "tradeoffs. Do not summarize; add substantial new detail."
    ),
]


def post_chat(base_url, model, messages, min_p):
    body = {
        "model": model,
        "messages": messages,
        "temperature": 1.0,
        "max_tokens": 4000,
        "seed": 0,
        "top_p": 1.0,
        "top_k": 0,
        "min_p": min_p,
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=900, context=ctx) as resp:
        data = json.loads(resp.read())
    return (
        data["choices"][0]["message"]["content"],
        data.get("usage", {}).get("completion_tokens", "?"),
    )


def find_loop(text, n=8, min_repeats=4):
    tokens = re.findall(r"\S+", text)
    counts = Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))
    hits = [(ngram, count) for ngram, count in counts.items() if count >= min_repeats]
    if not hits:
        return None
    ngram, count = max(hits, key=lambda item: item[1])
    return f"{' '.join(ngram)!r} x{count}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="default_model")
    parser.add_argument("--min-p", type=float, default=0.0)
    args = parser.parse_args()

    messages = []
    print(f"seed=0 min_p={args.min_p}")
    for turn, prompt in enumerate(PROMPTS, start=1):
        messages.append({"role": "user", "content": prompt})
        text, tokens = post_chat(args.base_url, args.model, messages, args.min_p)
        loop = find_loop(text)
        print(f"turn={turn} tokens={tokens} status={'LOOP' if loop else 'ok'}")
        if loop:
            print(f"loop={loop}")
            print(f"tail={text[-300:]!r}")
            sys.exit(0)
        messages.append({"role": "assistant", "content": text})

    print("no loop reproduced")
    sys.exit(2)


if __name__ == "__main__":
    main()
