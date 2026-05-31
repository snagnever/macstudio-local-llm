"""Quick tool-emission probe for the DeepSeek-V4-Flash tool template.
Sends a few clearly tool-requiring prompts with tools= and reports whether the
server returned parsed `tool_calls` (vs prose). Run against a server started with
the installed tool template. Before the template: 0 tool_calls (tools dropped)."""
import json, os, time, urllib.request

BASE = os.environ.get("BASE", "http://127.0.0.1:8765/v1")
MODEL = os.environ.get("MODEL", "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ")
TOOLS = [
    {"type": "function", "function": {"name": "get_weather",
        "description": "Get the current weather for a city",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "calculator",
        "description": "Evaluate an arithmetic expression and return the result",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}},
]
PROMPTS = [
    "What's the weather in Tokyo right now?",
    "Use the calculator to compute 4827 * 391.",
    "I need the current temperature in Paris.",
    "What is 19 squared plus 7?",
]

emitted = 0
for p in PROMPTS:
    body = {"model": MODEL, "messages": [{"role": "user", "content": p}],
            "tools": TOOLS, "temperature": 0, "max_tokens": 512, "stream": False}
    req = urllib.request.Request(f"{BASE}/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.loads(r.read())
        msg = d["choices"][0]["message"]
        tcs = msg.get("tool_calls") or []
        if tcs:
            emitted += 1
            names = ", ".join(tc.get("function", {}).get("name", "?") for tc in tcs)
            args = "; ".join(str(tc.get("function", {}).get("arguments", "")) for tc in tcs)
            print(f"[TOOL_CALL] {p!r}\n   -> {names}({args})  [{time.time()-t0:.0f}s]", flush=True)
        else:
            content = (msg.get("content") or "").replace("\n", " ")[:120]
            print(f"[prose    ] {p!r}\n   -> {content}  [{time.time()-t0:.0f}s]", flush=True)
    except Exception as e:
        print(f"[ERROR    ] {p!r}: {type(e).__name__}: {e}", flush=True)

print(f"\n=== tool_calls emitted on {emitted}/{len(PROMPTS)} tool-requiring prompts ===")
