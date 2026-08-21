#!/usr/bin/env python3
import argparse
import json
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.request import Request, urlopen

from cache_probe import cache_hit_ratio, cached_tokens_from_usage
from metrics import parse_prometheus


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_fixture",
            "description": "Read a deterministic campaign fixture.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_fixture",
            "description": "Search the deterministic campaign fixture.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_fixture_test",
            "description": "Run a named deterministic fixture test.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_result",
            "description": "Record one deterministic result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
                "additionalProperties": False,
            },
        },
    },
]

REQUIRED_ARGUMENTS = {
    "read_fixture": ("path",),
    "search_fixture": ("query",),
    "run_fixture_test": ("name",),
    "record_result": ("key", "value"),
}

EXPECTED_FINAL_VALUES = (
    "XENON-7592-FALCON",
    "ARGON-1844-EMBER",
    "NEON-6301-ORBIT",
    "RECORDED",
)


def build_tools() -> list[dict[str, Any]]:
    return deepcopy(TOOLS)


def append_tool_exchange(
    messages: list[dict[str, Any]],
    assistant_message: dict[str, Any],
    tool_result: str,
) -> list[dict[str, Any]]:
    updated = deepcopy(messages)
    preserved = deepcopy(assistant_message)
    updated.append(preserved)
    tool_call = preserved["tool_calls"][0]
    updated.append(
        {
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": tool_result,
        }
    )
    return updated


def parse_tool_arguments(name: str, raw_arguments: str) -> dict[str, str]:
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError as error:
        raise ValueError("tool arguments must be a valid JSON object") from error
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must be a valid JSON object")

    required = REQUIRED_ARGUMENTS.get(name)
    if required is None:
        raise ValueError(f"unknown tool: {name}")
    missing = [key for key in required if key not in arguments]
    if missing:
        raise ValueError(f"{name} requires: {', '.join(missing)}")
    unexpected = sorted(set(arguments) - set(required))
    if unexpected:
        raise ValueError(f"unexpected arguments: {', '.join(unexpected)}")
    if not all(isinstance(arguments[key], str) for key in required):
        raise ValueError("tool argument values must be strings")
    return arguments


def execute_fixture_tool(name: str, arguments: dict[str, str], turn: int) -> str:
    if name == "read_fixture":
        return f"read:{arguments['path']}:XENON-7592-FALCON:turn-{turn:02d}"
    if name == "search_fixture":
        return f"search:{arguments['query']}:ARGON-1844-EMBER:turn-{turn:02d}"
    if name == "run_fixture_test":
        return f"test:{arguments['name']}:NEON-6301-ORBIT:PASS:turn-{turn:02d}"
    if name == "record_result":
        return (
            f"RECORDED:{arguments['key']}={arguments['value']}:turn-{turn:02d}"
        )
    raise ValueError(f"unknown tool: {name}")


def _chat_once(
    base_url: str, payload: dict[str, Any], timeout_s: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    request = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout_s) as response:
        body = json.load(response)
    choices = body.get("choices") or []
    if not choices or not isinstance(choices[0].get("message"), dict):
        raise ValueError("chat response must contain choices[0].message")
    return choices[0]["message"], body.get("usage") or {}


def _metrics_snapshot(url: Optional[str]) -> dict[str, float]:
    if not url:
        return {}
    with urlopen(url, timeout=10) as response:
        return parse_prometheus(response.read().decode("utf-8"))


def _initial_messages() -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": (
                "You are running a deterministic 20-turn tool protocol. "
                "Call exactly one tool per turn. Cycle in this exact order: "
                "read_fixture, search_fixture, run_fixture_test, record_result. "
                "Use short string arguments and never call the same tool twice in a row. "
                "Preserve all prior reasoning and tool results."
            ),
        },
        {
            "role": "user",
            "content": (
                "Begin the protocol. Use audit.txt, query verified key, test cache, "
                "and record key=cache with value=pass."
            ),
        },
    ]


def _tool_payload(model: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model": model,
        "messages": messages,
        "tools": build_tools(),
        "tool_choice": "required",
        "max_tokens": 512,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "reasoning_effort": "xhigh",
    }


def _final_payload(model: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    final_messages = deepcopy(messages)
    final_messages.append(
        {
            "role": "user",
            "content": (
                "Finish without calling a tool. State the four observed result markers: "
                "XENON, ARGON, NEON, and RECORDED."
            ),
        }
    )
    return {
        "model": model,
        "messages": final_messages,
        "max_tokens": 1024,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "reasoning_effort": "xhigh",
    }


def _write_record(output, record: dict[str, Any]) -> None:
    serialized = json.dumps(record, sort_keys=True)
    output.write(serialized + "\n")
    output.flush()
    print(serialized, flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic Qwen3.8 20-turn tool protocol."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--runtime-revision", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metrics-url")
    parser.add_argument("--turns", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--cache-enabled", action="store_true")
    parser.add_argument("--mtp-enabled", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.turns <= 0:
        raise SystemExit("--turns must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    messages = _initial_messages()
    last_tool: Optional[str] = None
    consecutive = 0
    seen_tools: set[str] = set()
    run_failed = False

    with args.output.open("a", encoding="utf-8") as output:
        for turn in range(1, args.turns + 1):
            before = _metrics_snapshot(args.metrics_url)
            started = time.perf_counter()
            error: Optional[str] = None
            assistant_message: dict[str, Any] = {}
            usage: dict[str, Any] = {}
            arguments_valid = False
            reasoning_preserved = False
            tool_name: Optional[str] = None

            try:
                assistant_message, usage = _chat_once(
                    args.base_url,
                    _tool_payload(args.model, messages),
                    args.timeout,
                )
                tool_calls = assistant_message.get("tool_calls") or []
                if len(tool_calls) != 1:
                    raise ValueError("each turn must contain exactly one tool call")
                function = tool_calls[0].get("function") or {}
                tool_name = function.get("name")
                if not isinstance(tool_name, str):
                    raise ValueError("tool call must contain a function name")
                arguments = parse_tool_arguments(
                    tool_name, function.get("arguments") or ""
                )
                arguments_valid = True
                tool_result = execute_fixture_tool(tool_name, arguments, turn)
                updated = append_tool_exchange(messages, assistant_message, tool_result)
                reasoning_preserved = (
                    updated[-2].get("reasoning_content")
                    == assistant_message.get("reasoning_content")
                )
                messages = updated
            except Exception as caught:
                error = f"{type(caught).__name__}: {caught}"

            elapsed_ms = (time.perf_counter() - started) * 1000
            _metrics_snapshot(args.metrics_url)
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            cached_tokens = cached_tokens_from_usage(usage)
            if tool_name == last_tool:
                consecutive += 1
            elif tool_name:
                consecutive = 1
            else:
                consecutive = 0
            if tool_name:
                seen_tools.add(tool_name)
            last_tool = tool_name
            response_empty = not (
                assistant_message.get("content")
                or assistant_message.get("reasoning_content")
                or assistant_message.get("tool_calls")
            )
            correct = (
                error is None
                and arguments_valid
                and reasoning_preserved
                and not response_empty
                and consecutive <= 3
            )
            record = {
                "schema_version": 1,
                "record_type": "tool_turn",
                "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                "session_id": args.session_id,
                "runtime": args.runtime,
                "runtime_revision": args.runtime_revision,
                "model_id": args.model,
                "model_revision": args.model_revision,
                "arm": args.arm,
                "context_target": 65536,
                "cache_enabled": args.cache_enabled,
                "mtp_enabled": args.mtp_enabled,
                "turn": turn,
                "tool_name": tool_name,
                "tool_arguments_valid": arguments_valid,
                "consecutive_same_tool": consecutive,
                "prompt_tokens": prompt_tokens,
                "cached_tokens": cached_tokens,
                "cache_hit_ratio": cache_hit_ratio(cached_tokens, prompt_tokens),
                "elapsed_ms": elapsed_ms,
                "reasoning_preserved": reasoning_preserved,
                "response_empty": response_empty,
                "correct": correct,
                "metrics_available": bool(before),
                "ram_peak_gb": None,
                "swap_delta_gb": None,
                "gpu_temp_start_c": None,
                "gpu_temp_peak_c": None,
                "error": error,
            }
            _write_record(output, record)
            if not correct:
                run_failed = True
                break

        final_text = ""
        final_error: Optional[str] = None
        if not run_failed:
            try:
                final_message, _ = _chat_once(
                    args.base_url,
                    _final_payload(args.model, messages),
                    args.timeout,
                )
                final_text = (
                    final_message.get("content")
                    or final_message.get("reasoning_content")
                    or ""
                )
            except Exception as caught:
                final_error = f"{type(caught).__name__}: {caught}"

        missing_values = [
            value for value in EXPECTED_FINAL_VALUES if value not in final_text
        ]
        missing_tools = sorted(set(REQUIRED_ARGUMENTS) - seen_tools)
        verdict_passed = not run_failed and not final_error and not missing_values and not missing_tools
        verdict = {
            "schema_version": 1,
            "record_type": "verdict",
            "session_id": args.session_id,
            "runtime": args.runtime,
            "runtime_revision": args.runtime_revision,
            "model_id": args.model,
            "model_revision": args.model_revision,
            "arm": args.arm,
            "context_target": 65536,
            "ram_peak_gb": None,
            "swap_delta_gb": None,
            "gpu_temp_start_c": None,
            "gpu_temp_peak_c": None,
            "turns_requested": args.turns,
            "tools_seen": sorted(seen_tools),
            "missing_tools": missing_tools,
            "missing_final_values": missing_values,
            "correct": verdict_passed,
            "error": final_error,
        }
        _write_record(output, verdict)

    return 0 if verdict_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
