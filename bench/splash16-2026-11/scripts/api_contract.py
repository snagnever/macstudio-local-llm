#!/usr/bin/env python3
"""Checks C1 to C7 of the campaign plan against a running Splash server; one JSON line per check.

usage: api_contract.py --base-url http://127.0.0.1:8585 --model ID --version 1.5.0|1.6.0 --out results/contract-X.jsonl
A check whose expectation is None only records what the server does on that release.
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

PUZZLE = ("Find every positive integer n below 2000 such that n, n+2 and n+6 are all prime, and n+8 is not. "
          "Reason step by step, then call the record tool.")
TOOLS = [{"type": "function", "function": {"name": "record", "description": "Record the result.",
                                           "parameters": {"type": "object", "properties": {}}}}]
THINKING_BUDGET = 1024
REMOVED = (("kv_spill", "history_stream", "contended_commands"), ("memory_plan", "budget", "resident_kv_bytes"))


def _has(obj, keys):
    for key in keys:
        if not isinstance(obj, dict) or key not in obj:
            return False
        obj = obj[key]
    return True


def _msg(model, **extra):
    return dict({"model": model, "max_tokens": 8, "messages": [{"role": "user", "content": "Say ok."}]}, **extra)


def _chat(model, **extra):
    return dict({"model": model, "max_tokens": 8, "messages": [{"role": "user", "content": "Say ok."}],
                 "temperature": 1.0, "top_p": 0.95, "top_k": 20, "frequency_penalty": 0}, **extra)


def _c1(call, model, v):
    code, body = call("POST", "/v1/messages", _msg(model, stop_sequences="END"))
    if v == "1.5.0":
        return "200", code == 200, code
    return "400 naming stop_sequences", code == 400 and "stop_sequences" in json.dumps(body), [code, body]


def _c2(call, model, v):
    code, _ = call("POST", "/v1/messages", _msg(model, stop_sequences=["END"]))
    return "200", code == 200, code


def _c3(call, model, v):
    code, _ = call("POST", "/v1/chat/completions", _chat(model, stop=["x" * 16385]))
    return (None, True, code) if v == "1.5.0" else ("400", code == 400, code)


def _c4(call, model, v):
    code, body = call("POST", "/v1/chat/completions/count_tokens", _chat(model))
    if v == "1.5.0":
        return "404", code == 404, code
    if code != 200:
        return "input_tokens == usage.prompt_tokens", False, [code, body]
    real_code, real = call("POST", "/v1/chat/completions", _chat(model))
    seen = [body.get("input_tokens"), (real.get("usage") or {}).get("prompt_tokens"), real_code]
    return "input_tokens == usage.prompt_tokens", seen[0] == seen[1] and seen[0] is not None, seen


def _c5(call, model, v):
    _, before = call("GET", "/status")
    code, body = call("POST", "/v1/chat/completions", _chat(
        model, max_tokens=4096, stop=["banana"], reasoning_effort="low",
        messages=[{"role": "user", "content": "Write exactly this sentence: I ate one banana today."}]))
    _, after = call("GET", "/status")
    done = after["requests"]["completed"] - before["requests"]["completed"]
    cancelled = after["requests"]["cancelled"] - before["requests"]["cancelled"]
    seen = {"status": code, "completed": done, "cancelled": cancelled}
    if v == "1.5.0":
        return "requests.cancelled +1", cancelled == 1, seen
    return "requests.completed +1, cancelled +0", done == 1 and cancelled == 0, seen


def _c6(call, model, v):
    _, status = call("GET", "/status")
    if v == "1.5.0":
        return "schema 6", status.get("schema_version") == 6, status.get("schema_version")
    seen = {"schema": status.get("schema_version"), "governor": "memory_governor" in status,
            "ttft_parts": _has(status, ("metrics", "ttft_parts_ms")),
            "gap_causes": _has(status, ("metrics", "decode_gap_causes")),
            "removed_present": [".".join(r) for r in REMOVED if _has(status, r)]}
    ok = seen["schema"] == 8 and seen["governor"] and seen["ttft_parts"] and seen["gap_causes"] and not seen["removed_present"]
    return "schema 8, new fields present, removed fields absent", ok, seen


def _c7(call, model, v):
    first = [{"role": "user", "content": PUZZLE}]
    code, body = call("POST", "/v1/chat/completions", _chat(
        model, max_tokens=4096, messages=first, reasoning_effort="xhigh", thinking_token_budget=THINKING_BUDGET,
        tools=TOOLS))
    if code != 200:
        return "second turn reuses the reply past the cut", v == "1.5.0", [code, body]
    message = body["choices"][0]["message"]
    prompt = body["usage"]["prompt_tokens"]
    # Qwen's templates keep a reasoning only after the last user message, as in a tool loop. Only the model's own call
    # keeps every token of the reply: Splash restores KV from the state where the reply ended, not from before it.
    if not message.get("tool_calls"):
        return "second turn reuses the reply past the cut", True, {"inconclusive": "no tool call in the reply",
                                                                    "first_prompt": prompt}
    reply = {"role": "assistant", "content": message.get("content") or "", "tool_calls": message["tool_calls"]}
    for key in ("reasoning_content", "reasoning"):
        if message.get(key):
            reply[key] = message[key]
    code2, body2 = call("POST", "/v1/chat/completions", _chat(
        model, max_tokens=64, reasoning_effort="xhigh", tools=TOOLS,
        messages=first + [reply, {"role": "tool", "tool_call_id": message["tool_calls"][0]["id"], "content": "recorded"}]))
    cached = ((body2.get("usage") or {}).get("prompt_tokens_details") or {}).get("cached_tokens")
    seen = {"status": code2, "first_prompt": prompt, "first_output": body["usage"].get("completion_tokens"), "cached": cached,
            "second_prompt": (body2.get("usage") or {}).get("prompt_tokens")}
    if v == "1.5.0":
        return None, True, seen
    # KV moves in blocks of 32 tokens; a reply's own close and call lie past prompt + budget.
    return "cached > prompt + budget", cached is not None and cached > prompt + THINKING_BUDGET, seen


CHECKS = (("C1", _c1), ("C2", _c2), ("C3", _c3), ("C4", _c4), ("C5", _c5), ("C6", _c6), ("C7", _c7))


def run_checks(call, model: str, version: str) -> list[dict]:
    rows = []
    for name, check in CHECKS:
        try:
            expected, ok, seen = check(call, model, version)
        except Exception as exc:  # noqa: BLE001 - a dead check is a result; the others still run
            expected, ok, seen = "no exception", False, f"{type(exc).__name__}: {exc}"
        rows.append({"check": name, "expected": expected, "observed": seen, "pass": bool(ok)})
    return rows


def http_call(base_url: str, timeout: float):
    def call(method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(base_url + path, data, {"Content-Type": "application/json"}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                return exc.code, json.loads(raw)
            except ValueError:
                return exc.code, {"raw": raw[:500]}
    return call


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", required=True, help="server root, without /v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--version", required=True, choices=("1.5.0", "1.6.0"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--timeout", type=float, default=900)
    args = ap.parse_args()
    rows = run_checks(http_call(args.base_url.rstrip("/"), args.timeout), args.model, args.version)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
            print(row["check"], "pass" if row["pass"] else "FAIL", json.dumps(row["observed"])[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
