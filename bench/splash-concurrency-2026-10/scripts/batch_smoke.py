#!/usr/bin/env python3
"""Task 0 batch smoke: send N cold chat requests at once and record whether their decode windows overlap.

Runs as the --exec of run-arm.sh (BASE_URL and MODEL_ID come from the environment). Each request gets its own
prompt (a distinct salt), so no prefix is shared. Samples GET <server>/status every 5 s while the requests run.
Writes one JSON line per request and one per status sample, then a verdict line:
{"kind": "verdict", "overlap": true|false, "decode_tps": [...]}. Exit 0 always; the verdict carries the result.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Optional


def prompt(tokens: int, salt: str) -> str:
    # ~4 characters per token; numbered lines keep the prompt from compressing into a repeated pattern.
    lines = [f"{salt} line {i}: the quick brown fox jumps over the lazy dog." for i in range(tokens // 14)]
    return "\n".join(lines) + "\n\nSummarize the text above in one sentence."


def one_request(base_url: str, model: str, text: str, max_tokens: int, out: dict[str, Any]) -> None:
    body = {"model": model, "stream": True, "max_tokens": max_tokens, "temperature": 1.0,
            "messages": [{"role": "user", "content": text}],
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    out["t_start"] = time.time()
    chunks = 0
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            out["status"] = resp.status
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:") or line[5:].strip() == "[DONE]":
                    continue
                try:
                    delta = (json.loads(line[5:]).get("choices") or [{}])[0].get("delta") or {}
                except ValueError:
                    continue
                if delta.get("content") or delta.get("reasoning_content"):
                    chunks += 1
                    out.setdefault("t_first_token", time.time())
    except Exception as exc:  # recorded, the verdict reports it
        out["error"] = str(exc)
    out["t_end"] = time.time()
    out["chunks"] = chunks
    first = out.get("t_first_token")
    out["decode_tps"] = (chunks / (out["t_end"] - first)) if first and out["t_end"] > first else None


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--requests", type=int, default=2)
    p.add_argument("--prompt-tokens", type=int, default=16000)
    p.add_argument("--max-tokens", type=int, default=1024)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args(argv)
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:8585/v1")
    model = os.environ.get("MODEL_ID", "MODEL_ID")
    server = base_url[:-3] if base_url.endswith("/v1") else base_url
    results: list[dict[str, Any]] = [{"kind": "request", "index": i} for i in range(a.requests)]
    threads = [threading.Thread(target=one_request, args=(base_url, model, prompt(a.prompt_tokens, f"salt{i}"),
                                                         a.max_tokens, results[i])) for i in range(a.requests)]
    for t in threads:
        t.start()
    samples = []
    while any(t.is_alive() for t in threads):
        try:
            with urllib.request.urlopen(server + "/status", timeout=5) as resp:
                samples.append({"kind": "status", "t": time.time(), "status": json.load(resp)})
        except Exception as exc:
            samples.append({"kind": "status", "t": time.time(), "error": str(exc)})
        time.sleep(5)
    windows = [(r["t_first_token"], r["t_end"]) for r in results if r.get("t_first_token")]
    overlap = any(a0 < b1 and b0 < a1 for i, (a0, a1) in enumerate(windows) for (b0, b1) in windows[i + 1:])
    verdict = {"kind": "verdict", "overlap": overlap, "decode_tps": [r.get("decode_tps") for r in results],
               "errors": [r.get("error") for r in results if r.get("error")]}
    with a.output.open("w", encoding="utf-8") as fh:
        for row in results + samples + [verdict]:
            fh.write(json.dumps(row) + "\n")
    print(json.dumps(verdict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
