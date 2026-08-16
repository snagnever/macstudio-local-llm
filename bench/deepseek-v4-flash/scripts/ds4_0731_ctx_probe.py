#!/usr/bin/env python3
"""Decode/prefill-speed-vs-context-depth probe for DeepSeek-V4-Flash-0731 on ds4.

The llama.cpp baseline probe (udq2kxl_ctx_probe.py) read llama-server's own
`timings` field. ds4-server emits no such field, so this times the client side
via SSE streaming:

  TTFT (time to first streamed token) ≈ prefill time
  prefill t/s = prompt_tokens / TTFT
  decode  t/s = (completion_tokens - 1) / (total_elapsed - TTFT)

Depths mirror the baseline [512..30720] for a direct overlay, then extend past
32k (49k / 65k / 131k) — territory the llama.cpp -c 32768 config could not reach.

Each depth uses a UNIQUE filler prefix so ds4's prompt cache cannot reuse a
shared prefix and inflate a deep read (the baseline's cache_prompt:false trap,
handled here without relying on a server flag). Thinking OFF via model
deepseek-chat.

Usage: .venv/bin/python bench/deepseek-v4-flash/scripts/ds4_0731_ctx_probe.py
"""
import json, subprocess, time, urllib.request

BASE = "http://127.0.0.1:8000/v1"
MODEL = "deepseek-chat"  # thinking OFF
DEPTHS = [512, 2048, 4096, 8192, 16384, 24576, 30720,   # overlay range (baseline)
          49152, 65536, 131072]                          # extension past 32k
GEN = 256
OUT = "bench/deepseek-v4-flash/results/0731-ds4-ctxspeed.json"

FILLER = ("The quick brown fox jumps over the lazy dog near the riverbank "
          "while autumn leaves drift across the quiet meadow at dusk. ")


def rss_gb():
    out = subprocess.run(["ps", "-eo", "rss,comm"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if "ds4-server" in line:
            return round(int(line.split()[0]) / 1024 / 1024, 1)
    return None


def probe(depth, idx):
    words = int(depth * 0.75)
    # Unique per-depth marker defeats prompt-cache prefix reuse.
    filler = f"[probe-{idx}-{depth}] " + (FILLER * (words // 20 + 1))
    prompt = (filler + "\n\nIgnore all text above. In one short paragraph, "
              "explain what a hash map is.")
    body = json.dumps({"model": MODEL,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": GEN, "temperature": 0, "stream": True,
                       "stream_options": {"include_usage": True}}).encode()
    req = urllib.request.Request(BASE + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    ttft = None
    ntok = 0
    prompt_tokens = None
    with urllib.request.urlopen(req, timeout=3600) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                d = json.loads(payload)
            except json.JSONDecodeError:
                continue
            ch = (d.get("choices") or [{}])[0]
            delta = ch.get("delta", {})
            if delta.get("content"):
                if ttft is None:
                    ttft = time.time() - t0
                ntok += 1
            if d.get("usage"):
                prompt_tokens = d["usage"].get("prompt_tokens", prompt_tokens)
    total = time.time() - t0
    decode_tps = round((ntok - 1) / (total - ttft), 1) if (ttft and ntok > 1 and total > ttft) else None
    prefill_tps = round(prompt_tokens / ttft, 1) if (ttft and prompt_tokens) else None
    return {"depth": depth, "prompt_tokens": prompt_tokens, "gen_tokens": ntok,
            "ttft_s": round(ttft, 2) if ttft else None,
            "prefill_tps": prefill_tps, "decode_tps": decode_tps,
            "total_s": round(total, 2), "rss_gb": rss_gb()}


if __name__ == "__main__":
    results = []
    for i, depth in enumerate(DEPTHS):
        row = probe(depth, i)
        print(row, flush=True)
        results.append(row)
        with open(OUT, "w") as f:
            json.dump(results, f, indent=1)
    print(f"wrote {OUT}")
