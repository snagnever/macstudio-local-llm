"""Last knob: does repetition_penalty actually rescue the degenerate draws?
thinking=OFF server. Tests rep_penalty {1.15, 1.3} x temp {0.6,0.7,1.0}
(0.7/1.0 degenerated WITHOUT penalty; 0.6 was clean). repetition_context_size=256.
"""
import json, time, urllib.request
from collections import Counter

BASE = "http://127.0.0.1:8765/v1"
MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
PROMPT = "você executa código"
MAXTOK = 2000


def degenerate(text):
    w = text.split()
    if len(w) < 20:
        return False
    return Counter(w[-40:]).most_common(1)[0][1] >= 12 or len(set(w[-40:])) <= 5


for rep in (1.15, 1.3):
    for temp in (0.6, 0.7, 1.0):
        body = {"model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
                "max_tokens": MAXTOK, "stream": False, "temperature": temp,
                "repetition_penalty": rep, "repetition_context_size": 256}
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
            tail = content[-110:].replace("\n", " ⏎ ")
            print(f"[{verdict:10s}] rep={rep} temp={temp} finish={fr:7s} tokens={ct:4d} {time.time()-t0:4.0f}s",
                  flush=True)
            print(f"   tail: …{tail}\n", flush=True)
        except Exception as e:
            print(f"[ERROR] rep={rep} temp={temp}: {type(e).__name__}: {e}\n", flush=True)
