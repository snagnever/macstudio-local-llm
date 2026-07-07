"""Find a sampling config that makes the 'você executa código' prompt terminate
cleanly instead of degenerating into a repetition loop. Non-streaming so we get
finish_reason + completion_tokens. CLEAN = emits EOS (finish=stop), bounded length,
and no repeated-token tail; DEGENERATE = hits max_tokens (finish=length) or the tail
collapses to a few repeated words.
"""
import json, time, urllib.request
from collections import Counter

BASE = "http://127.0.0.1:8765/v1"
MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
PROMPT = "você executa código"
MAXTOK = 1500

CONFIGS = [
    ("baseline temp0.6",              {"temperature": 0.6}),
    ("rep_penalty1.2 ctx64",          {"temperature": 0.6, "repetition_penalty": 1.2, "repetition_context_size": 64}),
    ("min_p0.05 top_p0.95",           {"temperature": 0.6, "top_p": 0.95, "min_p": 0.05}),
    ("frequency_penalty0.8",          {"temperature": 0.6, "frequency_penalty": 0.8}),
    ("combo t0.7 top_p0.95 rep1.15",  {"temperature": 0.7, "top_p": 0.95, "repetition_penalty": 1.15, "repetition_context_size": 64}),
]


def degenerate(text):
    w = text.split()
    if len(w) < 20:
        return False
    tail = w[-40:]
    return Counter(tail).most_common(1)[0][1] >= 12 or len(set(tail)) <= 5


def main():
    for name, params in CONFIGS:
        body = {"model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
                "max_tokens": MAXTOK, "stream": False}
        body.update(params)
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
            dg = degenerate(content)
            verdict = "DEGENERATE" if (dg or fr == "length") else "CLEAN"
            tail = content[-150:].replace("\n", " ⏎ ")
            print(f"[{verdict:10s}] {name:30s} finish={fr:7s} tokens={ct:4d} {time.time()-t0:5.0f}s",
                  flush=True)
            print(f"             tail …{tail}\n", flush=True)
        except Exception as e:
            print(f"[ERROR     ] {name:30s} {type(e).__name__}: {e}\n", flush=True)


if __name__ == "__main__":
    main()
