"""Isolate the real lever: does enable_thinking on/off control the degeneration?
Runs 'você executa código' at the user's exact temps (0.6/0.7/1.0), no tail
truncation. Prints verdict + head (to spot <think> traces) + tail per temp.
"""
import json, sys, time, urllib.request
from collections import Counter

BASE = "http://127.0.0.1:8765/v1"
MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
PROMPT = "você executa código"
MAXTOK = 2000
LABEL = sys.argv[1] if len(sys.argv) > 1 else "?"


def degenerate(text):
    w = text.split()
    if len(w) < 20:
        return False
    return Counter(w[-40:]).most_common(1)[0][1] >= 12 or len(set(w[-40:])) <= 5


for temp in (0.6, 0.7, 1.0):
    body = {"model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": MAXTOK, "stream": False, "temperature": temp}
    req = urllib.request.Request(f"{BASE}/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            d = json.loads(r.read())
        ch = d["choices"][0]
        content = ch["message"]["content"] or ""
        fr = ch.get("finish_reason")
        ct = d["usage"]["completion_tokens"]
        verdict = "DEGENERATE" if (degenerate(content) or fr == "length") else "CLEAN"
        head = content[:120].replace("\n", " ⏎ ")
        tail = content[-110:].replace("\n", " ⏎ ")
        print(f"[{verdict:10s}] {LABEL} temp={temp} finish={fr:7s} tokens={ct:4d} {time.time()-t0:4.0f}s",
              flush=True)
        print(f"   head: {head}", flush=True)
        print(f"   tail: …{tail}\n", flush=True)
    except Exception as e:
        print(f"[ERROR] {LABEL} temp={temp}: {type(e).__name__}: {e}\n", flush=True)
