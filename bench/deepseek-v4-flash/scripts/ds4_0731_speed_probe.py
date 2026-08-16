#!/usr/bin/env python3
"""
0731 + ds4 speed probe.

Mirrors the 3 questions of tools/local-llm-bench-m4-32gb/scripts/speed_probe.py
so the numbers are directly comparable to the llama.cpp baseline (10.3 t/s on
code_second_largest, 2026-07-12), but sweeps ds4's two thinking modes:

  deepseek-chat      -> non-thinking (matches the baseline methodology)
  deepseek-v4-flash  -> high-effort thinking (ds4's default for this model)

Non-thinking is the apples-to-apples read; the thinking row shows the reasoning
tax, which the llama.cpp path never had (0 reasoning tokens there).

Usage: python3 ds4_0731_speed_probe.py [out.json]
"""
import json, os, subprocess, sys, time
from datetime import datetime
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("DS4_URL", "http://127.0.0.1:8000/v1")
OUT = sys.argv[1] if len(sys.argv) > 1 else "bench/deepseek-v4-flash/results/0731-ds4-speed.json"

QUESTIONS = [
    ("trivial", "What is 2+2? Answer with just the number.", 256),
    ("mmlu_atmosphere",
     "Which of the following is the correct order of the layers of the Earth's "
     "atmosphere from lowest to highest?\n"
     "(A) Troposphere, Stratosphere, Mesosphere, Thermosphere\n"
     "(B) Stratosphere, Troposphere, Mesosphere, Thermosphere\n"
     "(C) Troposphere, Mesosphere, Stratosphere, Thermosphere\n"
     "(D) Mesosphere, Troposphere, Stratosphere, Thermosphere\n"
     "Answer with just the letter.", 512),
    ("code_second_largest",
     "Write a Python function that takes a list of integers and returns the "
     "second largest element. If fewer than 2 unique elements, return None. "
     "Just the function, no explanation.", 1024),
]

MODES = [("nothink", "deepseek-chat"), ("think_high", "deepseek-v4-flash")]


def rss_gb():
    try:
        pid = subprocess.run(["pgrep", "-f", "ds4-server"], capture_output=True,
                             text=True).stdout.split()[0]
        kb = subprocess.run(["ps", "-o", "rss=", "-p", pid], capture_output=True,
                            text=True).stdout.strip()
        return round(int(kb) / 1048576, 1)
    except Exception:
        return None


def ask(model, prompt, max_tokens):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": "You are a helpful assistant."},
                     {"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }).encode()
    req = Request(f"{BASE_URL}/chat/completions", data=payload,
                  headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urlopen(req, timeout=600) as r:
            d = json.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": str(e), "elapsed": round(time.time() - t0, 2)}
    el = time.time() - t0
    u = d.get("usage", {})
    ct = u.get("completion_tokens", 0)
    return {
        "ok": True,
        "elapsed": round(el, 2),
        "completion_tokens": ct,
        "reasoning_tokens": u.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
        "prompt_tokens": u.get("prompt_tokens", 0),
        "tok_s": round(ct / el, 1) if el > 0 else 0,
        "content": (d["choices"][0]["message"].get("content") or "")[:400],
    }


def main():
    print(f"ds4 0731 speed probe -> {BASE_URL}")
    # Warmup: first request after load pays page-in cost; don't score it.
    ask("deepseek-chat", "hi", 8)

    results = {"timestamp": datetime.now().isoformat(), "base_url": BASE_URL,
               "rss_gb": rss_gb(), "modes": {}}
    for mode, model in MODES:
        rows = []
        print(f"\n--- {mode} (model={model}) ---")
        for name, prompt, mt in QUESTIONS:
            r = ask(model, prompt, mt)
            r["question"] = name
            rows.append(r)
            if r["ok"]:
                print(f"  {name:22s} {r['completion_tokens']:5d} tok  "
                      f"{r['elapsed']:7.2f}s  {r['tok_s']:6.1f} t/s  "
                      f"(reasoning {r['reasoning_tokens']})")
            else:
                print(f"  {name:22s} FAIL {r['error'][:80]}")
        results["modes"][mode] = {"model": model, "rows": rows}

    results["rss_gb_after"] = rss_gb()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nRSS {results['rss_gb']} -> {results['rss_gb_after']} GB")
    print(f"wrote {OUT}")

    clean = results["modes"]["nothink"]["rows"][2]
    if clean.get("ok"):
        print(f"\nHEADLINE (code_second_largest, non-thinking): {clean['tok_s']} t/s "
              f"vs 10.3 t/s llama.cpp baseline "
              f"= {clean['tok_s'] / 10.3:.2f}x")


if __name__ == "__main__":
    main()
