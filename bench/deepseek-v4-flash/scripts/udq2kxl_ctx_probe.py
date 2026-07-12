#!/usr/bin/env python3
"""Decode-speed-vs-context-depth probe for deepseek-v4-flash-udq2kxl.

One llama-server at -c 32768; per target depth, send a synthetic prompt of
~depth tokens and generate 256 tokens at temp 0. Records llama-server's own
timings (prompt_per_second / predicted_per_second) plus process RSS.

Usage: .venv/bin/python bench/deepseek-v4-flash/scripts/udq2kxl_ctx_probe.py
"""
import json, subprocess, urllib.request

BASE = "http://127.0.0.1:1235/v1"
MODEL = "deepseek-v4-flash-udq2kxl"
DEPTHS = [512, 2048, 4096, 8192, 16384, 24576, 30720]  # ctx is 32768; leave gen headroom
OUT = "bench/deepseek-v4-flash/results/udq2kxl-ctxspeed.json"

# ~1 token per word for this filler; oversupply then rely on server-side truncation margin
FILLER_SENTENCE = ("The quick brown fox jumps over the lazy dog near the riverbank "
                   "while autumn leaves drift across the quiet meadow at dusk. ")

def rss_gb():
    out = subprocess.run(["ps", "-eo", "rss,comm"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if "llama-server" in line:
            return round(int(line.split()[0]) / 1024 / 1024, 1)
    return None

def probe(depth):
    words_needed = int(depth * 0.75)  # sentence above ≈ 1.33 words/token
    filler = (FILLER_SENTENCE * (words_needed // 20 + 1))
    prompt = (filler + "\n\nIgnore all text above. In one short paragraph, "
              "explain what a hash map is.")
    # cache_prompt=False: all prompts share the same filler prefix, so llama-server's
    # prompt-cache prefix reuse otherwise accumulates KV across requests and trips
    # "Context size has been exceeded" at the deep points. Disable it for clean per-depth reads.
    body = json.dumps({"model": MODEL,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 256, "temperature": 0, "cache_prompt": False}).encode()
    req = urllib.request.Request(BASE + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        d = json.load(r)
    t = d.get("timings", {})
    return {"depth": depth,
            "prompt_tokens": d.get("usage", {}).get("prompt_tokens"),
            "prefill_tps": round(t.get("prompt_per_second", 0), 1),
            "decode_tps": round(t.get("predicted_per_second", 0), 1),
            "rss_gb": rss_gb()}

if __name__ == "__main__":
    results = []
    for depth in DEPTHS:
        row = probe(depth)
        print(row, flush=True)
        results.append(row)
        with open(OUT, "w") as f:            # write-through: partial results survive a crash
            json.dump(results, f, indent=1)
    print(f"wrote {OUT}")
