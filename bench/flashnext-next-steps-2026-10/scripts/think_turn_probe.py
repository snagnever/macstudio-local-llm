#!/usr/bin/env python3
"""Tool turn that re-sends the previous turn's thinking, against the same turn without it.

cache_probe.py never re-sends thinking: its tool_turn assistant message only carries tool_calls. A real
harness with ``preserve_thinking`` (the Qwen card default) re-sends the reasoning of the previous turn, and
mlx-serve 26.10.2 declares "Qwen3.8 keeps its earlier reasoning". This probe measures the second turn of a
conversation in two modes, with the same fixture as cache_probe.py (audit_retrieval, needles 10/50/90):

  turn1      base prompt (system + fixture + question), streamed; its reasoning text R is kept
  tool_turn  base + assistant{tool_call read_fixture, reasoning_content=R (mode resend) or none (mode drop)}
             + tool result (1024-token suffix that repeats the question)

The first request after the server comes up is a short prompt (``first_after_load``), so its TTFT is the
"first prompt after load" that mlx-serve 26.10.2 says no longer stalls. Run it through
``run-arm.sh <arm> <ctx> --exec`` so it is the first request the server sees.

Every turn1 uses a system line with the repeat and mode, so each conversation starts cold, like
cache_probe.py's trial line.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[3] / "bench" / "qwen3.8-prefix-cache" / "scripts"
sys.path.insert(0, str(HARNESS))

SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 20, "presence_penalty": 0.0}
MAX_TOKENS = 4096
TOOL_CALL = {"id": "call_fixture_1", "type": "function",
             "function": {"name": "read_fixture", "arguments": '{"path":"audit.txt"}'}}


def base_messages(fixture_text: str, question: str, repeat: int, mode: str) -> list[dict]:
    return [{"role": "system",
             "content": f"You are a deterministic audit retrieval assistant. Thinking probe {mode} trial {repeat:03d}."},
            {"role": "user", "content": f"{fixture_text}\n\n{question}"}]


def tool_turn_messages(base: list[dict], reasoning: str, suffix: str, mode: str) -> list[dict]:
    assistant = {"role": "assistant", "content": "", "tool_calls": [TOOL_CALL]}
    if mode == "resend":
        assistant["reasoning_content"] = reasoning
    return [*base, assistant, {"role": "tool", "tool_call_id": TOOL_CALL["id"], "content": suffix}]


def payload(model: str, messages: list[dict], effort: str, max_tokens: int = MAX_TOKENS) -> dict:
    return {"model": model, "messages": messages, "max_tokens": max_tokens, "reasoning_effort": effort, **SAMPLING}


def record(arm: str, ctx: int, scenario: str, mode: str, repeat: int, result, needles, extra=None) -> dict:
    from cache_probe import cache_hit_ratio, cached_tokens_from_usage
    usage = result.usage
    prompt = int(usage.get("prompt_tokens") or 0)
    cached = cached_tokens_from_usage(usage)
    completion = int(usage.get("completion_tokens") or 0)
    decode_s = max(0.0, result.e2e_ms - result.ttft_ms) / 1000
    rec = {"arm": arm, "context_target": ctx, "scenario": scenario, "mode": mode, "repeat": repeat,
           "ttft_ms": round(result.ttft_ms, 1), "e2e_ms": round(result.e2e_ms, 1),
           "prompt_tokens": prompt, "cached_tokens": cached, "cache_hit_ratio": round(cache_hit_ratio(cached, prompt), 4),
           "completion_tokens": completion, "decode_tps": round(completion / decode_s, 2) if decode_s else 0.0,
           "finish_reason": result.finish_reason, "reasoning_chars": len(result.reasoning_text),
           "content_chars": len(result.text), "error": None}
    if needles:
        rec["needles_ok"] = result.finish_reason != "length" and all(n in result.text for n in needles)
    rec.update(extra or {})
    return rec


def run(a: argparse.Namespace) -> int:
    from cache_probe import RuntimeTokenizer, fixture_token_target
    from fixtures import build_fixture, build_suffix
    from sse_client import stream_chat

    tok = RuntimeTokenizer(a.base_url, a.model)
    out = a.output.open("a", encoding="utf-8")

    def emit(rec: dict) -> None:
        rec.update({"session_id": a.session_id, "reasoning_effort": a.reasoning_effort, **SAMPLING})
        out.write(json.dumps(rec, sort_keys=True) + "\n"); out.flush()
        print(json.dumps({k: rec.get(k) for k in ("scenario", "mode", "repeat", "ttft_ms", "cache_hit_ratio",
                                                  "decode_tps", "needles_ok", "error")}), flush=True)

    first = stream_chat(a.base_url, payload(a.model, [{"role": "user", "content": "Reply with OK."}],
                                            a.reasoning_effort, 64), timeout_s=a.timeout)
    emit(record(a.arm, a.context, "first_after_load", "-", 0, first, ()))

    fixture = build_fixture(fixture_token_target(a.context), tok)
    suffix, _ = build_suffix(1024, tok, f"Tool result confirms {fixture.needles[0]}. {fixture.question}")
    rc = 0
    for repeat in range(1, a.repeat + 1):
        for mode in a.modes:
            base = base_messages(fixture.text, fixture.question, repeat, mode)
            try:
                t1 = stream_chat(a.base_url, payload(a.model, base, a.reasoning_effort), timeout_s=a.timeout)
                emit(record(a.arm, a.context, "turn1", mode, repeat, t1, fixture.needles))
                msgs = tool_turn_messages(base, t1.reasoning_text, suffix, mode)
                t2 = stream_chat(a.base_url, payload(a.model, msgs, a.reasoning_effort), timeout_s=a.timeout)
                emit(record(a.arm, a.context, "tool_turn", mode, repeat, t2, fixture.needles,
                            {"resent_reasoning_chars": len(t1.reasoning_text) if mode == "resend" else 0}))
            except Exception as error:  # HTTP refusal or dropped connection: data, not a crash
                emit({"arm": a.arm, "context_target": a.context, "scenario": "tool_turn", "mode": mode,
                      "repeat": repeat, "error": f"{type(error).__name__}: {error}"[:300]})
                rc = 3
    return rc


def summary(paths: list[Path]) -> str:
    rows: dict[tuple, list[dict]] = {}
    for p in paths:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows.setdefault((r["arm"], r["context_target"], r["scenario"], r.get("mode", "-")), []).append(r)

    def med(rs, k, scale=1.0):
        xs = [r[k] * scale for r in rs if r.get(k) is not None and not r.get("error")]
        return f"{statistics.median(xs):.2f}" if xs else "—"

    lines = ["| braço | contexto | cenário | modo | n | TTFT s | hit | cached | prompt | decode | needles | erros |",
             "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|---:|"]
    for (arm, ctx, sc, mode), rs in sorted(rows.items()):
        ok = sum(1 for r in rs if r.get("needles_ok"))
        has = sum(1 for r in rs if "needles_ok" in r)
        lines.append(f"| {arm} | {ctx // 1024}K | {sc} | {mode} | {len(rs)} | {med(rs, 'ttft_ms', 0.001)} | "
                     f"{med(rs, 'cache_hit_ratio')} | {med(rs, 'cached_tokens')} | {med(rs, 'prompt_tokens')} | "
                     f"{med(rs, 'decode_tps')} | {f'{ok}/{has}' if has else '—'} | {sum(1 for r in rs if r.get('error'))} |")
    return "\n".join(lines)


def dry_run(a: argparse.Namespace) -> int:
    text = "\n".join(f"Record {i:06d} stores audit value." for i in range(20))
    for mode in a.modes:
        base = base_messages(text, "Return the keys.", 1, mode)
        msgs = tool_turn_messages(base, "previous reasoning text", "suffix text", mode)
        print(json.dumps({"mode": mode, "turn1_roles": [m["role"] for m in base],
                          "tool_turn_roles": [m["role"] for m in msgs],
                          "assistant_keys": sorted(msgs[2].keys()),
                          "sampling": {**SAMPLING, "reasoning_effort": a.reasoning_effort}}))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url")
    ap.add_argument("--model")
    ap.add_argument("--arm")
    ap.add_argument("--context", type=int)
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--modes", default="resend,drop")
    ap.add_argument("--reasoning-effort", default="xhigh", choices=("xhigh", "medium", "low"))
    ap.add_argument("--output", type=Path)
    ap.add_argument("--session-id", default=time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--summary", nargs="+", type=Path, help="print the table of these JSONL files and exit")
    a = ap.parse_args(argv)
    a.modes = [m for m in a.modes.split(",") if m]
    if any(m not in ("resend", "drop") for m in a.modes):
        ap.error("--modes takes resend and/or drop")
    if a.summary:
        print(summary(a.summary))
        return 0
    if a.dry_run:
        return dry_run(a)
    for k in ("base_url", "model", "arm", "context", "output"):
        if getattr(a, k) is None:
            ap.error(f"--{k.replace('_', '-')} is required")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
