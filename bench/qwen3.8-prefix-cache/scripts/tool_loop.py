#!/usr/bin/env python3
import argparse
import json
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from cache_probe import (
    SAMPLING_CONTROLS,
    _quant_label,
    cache_hit_ratio,
    cached_tokens_from_usage,
)
from metrics import normalize_server_measurements, parse_prometheus


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


def _flatten_json_metrics(
    value: Any, *, prefix: str, result: dict[str, float]
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _flatten_json_metrics(
                child, prefix=f"{prefix}.{key}" if prefix else key, result=result
            )
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        result[prefix] = float(value)


def _metrics_snapshot(
    url: Optional[str], runtime: Optional[str] = None
) -> dict[str, float]:
    if not url:
        return {}
    try:
        with urlopen(url, timeout=10) as response:
            text = response.read().decode("utf-8")
    except HTTPError as error:
        if error.code in (404, 405):
            return {}
        raise
    if runtime in {"mlx-dspark", "MTPLX"}:
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError(f"{runtime} /metrics must return a JSON object")
        if runtime == "MTPLX":
            payload = payload.get("latest") or {}
            if not isinstance(payload, dict):
                raise ValueError("MTPLX /metrics latest must be a JSON object")
        result: dict[str, float] = {}
        prefix = "mlx_dspark" if runtime == "mlx-dspark" else "mtplx"
        _flatten_json_metrics(payload, prefix=prefix, result=result)
        if runtime == "MTPLX":
            aliases = {
                "accepted_drafts": "accepted_tokens",
                "verify_calls": "verification_steps",
            }
            for source, target in aliases.items():
                value = payload.get(source)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    result[f"mtplx.{target}"] = float(value)
        return result
    return parse_prometheus(text)


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


def _tool_payload(
    model: str,
    messages: list[dict[str, Any]],
    *,
    specprefill: Optional[bool] = None,
    specprefill_keep_pct: Optional[float] = None,
    specprefill_threshold: Optional[int] = None,
    sampling_controls: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "tools": build_tools(),
        "tool_choice": "required",
        "max_tokens": 512,
        **(sampling_controls or SAMPLING_CONTROLS),
    }
    if specprefill is not None:
        payload["specprefill"] = specprefill
    if specprefill_keep_pct is not None:
        payload["specprefill_keep_pct"] = specprefill_keep_pct
    if specprefill_threshold is not None:
        payload["specprefill_threshold"] = specprefill_threshold
    return payload


def _final_payload(
    model: str,
    messages: list[dict[str, Any]],
    *,
    specprefill: Optional[bool] = None,
    specprefill_keep_pct: Optional[float] = None,
    specprefill_threshold: Optional[int] = None,
    sampling_controls: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
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
    payload = {
        "model": model,
        "messages": final_messages,
        "max_tokens": 1024,
        **(sampling_controls or SAMPLING_CONTROLS),
    }
    if specprefill is not None:
        payload["specprefill"] = specprefill
    if specprefill_keep_pct is not None:
        payload["specprefill_keep_pct"] = specprefill_keep_pct
    if specprefill_threshold is not None:
        payload["specprefill_threshold"] = specprefill_threshold
    return payload


def _write_record(output, record: dict[str, Any]) -> None:
    serialized = json.dumps(record, sort_keys=True)
    output.write(serialized + "\n")
    output.flush()
    print(serialized, flush=True)


def sampling_record_fields(controls: dict[str, Any]) -> dict[str, Any]:
    return {
        key: controls.get(key)
        for key in (
            "temperature",
            "top_p",
            "top_k",
            "min_p",
            "presence_penalty",
            "frequency_penalty",
            "repetition_penalty",
            "reasoning_effort",
        )
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic Qwen3.8 20-turn tool protocol."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-model")
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
    parser.add_argument("--specprefill", type=lambda value: value.lower() == "true")
    parser.add_argument("--specprefill-keep-pct", type=float)
    parser.add_argument("--specprefill-threshold", type=int)
    parser.add_argument("--specprefill-draft-model")
    parser.add_argument("--specprefill-draft-revision")
    parser.add_argument("--context", type=int, default=65536)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--warmup-id", default="tool-loop-warmup-v1")
    parser.add_argument(
        "--temperature", type=float, default=SAMPLING_CONTROLS["temperature"]
    )
    parser.add_argument("--top-p", type=float, default=SAMPLING_CONTROLS["top_p"])
    parser.add_argument("--top-k", type=int, default=SAMPLING_CONTROLS["top_k"])
    parser.add_argument(
        "--reasoning-effort", default=SAMPLING_CONTROLS["reasoning_effort"]
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.turns <= 0:
        raise SystemExit("--turns must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    api_model = args.api_model or args.model
    sampling_controls = {
        **SAMPLING_CONTROLS,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "reasoning_effort": args.reasoning_effort,
    }

    messages = _initial_messages()
    last_tool: Optional[str] = None
    consecutive = 0
    seen_tools: set[str] = set()
    run_failed = False

    with args.output.open("a", encoding="utf-8") as output:
        for turn in range(1, args.turns + 1):
            before = _metrics_snapshot(args.metrics_url, args.runtime)
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
                    _tool_payload(
                        api_model,
                        messages,
                        specprefill=args.specprefill,
                        specprefill_keep_pct=args.specprefill_keep_pct,
                        specprefill_threshold=args.specprefill_threshold,
                        sampling_controls=sampling_controls,
                    ),
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
            after = _metrics_snapshot(args.metrics_url, args.runtime)
            server = normalize_server_measurements(usage, before, after)
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
                "schema_version": 3,
                "record_type": "tool_turn",
                "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                "session_id": args.session_id,
                "runtime": args.runtime,
                "runtime_revision": args.runtime_revision,
                "model_id": args.model,
                "model_revision": args.model_revision,
                "quant": _quant_label(args.model),
                "arm": args.arm,
                "context_target": args.context,
                "cache_enabled": args.cache_enabled,
                "mtp_enabled": args.mtp_enabled,
                "specprefill_enabled": bool(args.specprefill),
                "specprefill_draft_model": args.specprefill_draft_model,
                "specprefill_draft_revision": args.specprefill_draft_revision,
                "specprefill_keep_pct": args.specprefill_keep_pct,
                "specprefill_threshold": args.specprefill_threshold,
                "specprefill_selected_tokens": server["specprefill_selected_tokens"],
                "specprefill_scored_tokens": server["specprefill_scored_tokens"],
                "specprefill_draft_ms": server["specprefill_draft_ms"],
                "specprefill_target_ms": server["specprefill_target_ms"],
                "static_prefix_cached_tokens": server["static_prefix_cached_tokens"],
                "ane_prefill_enabled": False,
                "ane_prefill_tuned": server["ane_prefill_tuned"],
                "content_class": "tool_loop",
                "prompt_identity": "tool-loop-v1",
                "concurrency": args.concurrency,
                "warmup_id": args.warmup_id,
                **sampling_record_fields(sampling_controls),
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
                "ane_compiled_mlp_layers": server["ane_compiled_mlp_layers"],
                "ane_compiled_gdn_layers": server["ane_compiled_gdn_layers"],
                "ane_executed_operations": server["ane_executed_operations"],
                "prompt_work_mode": server["prompt_work_mode"],
                "speculation_mode": server["speculation_mode"],
                "drafter_id": server["drafter_id"],
                "drafter_revision": server["drafter_revision"],
                "draft_cap_policy": server["draft_cap_policy"],
                "draft_cap_resolved": server["draft_cap_resolved"],
                "drafted_tokens": server["drafted_tokens"],
                "accepted_tokens": server["accepted_tokens"],
                "accept_length": server["accept_length"],
                "verification_steps": server["verification_steps"],
                "decode_speedup_vs_baseline": None,
                "machine_roofline_tps": server["machine_roofline_tps"],
                "decode_roofline_ratio": server["decode_roofline_ratio"],
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
                    _final_payload(
                        api_model,
                        messages,
                        specprefill=args.specprefill,
                        specprefill_keep_pct=args.specprefill_keep_pct,
                        specprefill_threshold=args.specprefill_threshold,
                        sampling_controls=sampling_controls,
                    ),
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
            "schema_version": 3,
            "record_type": "verdict",
            "session_id": args.session_id,
            "runtime": args.runtime,
            "runtime_revision": args.runtime_revision,
            "model_id": args.model,
            "model_revision": args.model_revision,
            "quant": _quant_label(args.model),
            "arm": args.arm,
            "context_target": args.context,
            "mtp_enabled": args.mtp_enabled,
            "specprefill_enabled": bool(args.specprefill),
            "specprefill_draft_model": args.specprefill_draft_model,
            "specprefill_draft_revision": args.specprefill_draft_revision,
            "specprefill_keep_pct": args.specprefill_keep_pct,
            "specprefill_threshold": args.specprefill_threshold,
            "specprefill_selected_tokens": None,
            "specprefill_scored_tokens": None,
            "specprefill_draft_ms": None,
            "specprefill_target_ms": None,
            "static_prefix_cached_tokens": None,
            "ane_prefill_enabled": False,
            "ane_prefill_tuned": None,
            "ane_compiled_mlp_layers": None,
            "ane_compiled_gdn_layers": None,
            "ane_executed_operations": None,
            "prompt_work_mode": None,
            "speculation_mode": None,
            "drafter_id": None,
            "drafter_revision": None,
            "draft_cap_policy": None,
            "draft_cap_resolved": None,
            "drafted_tokens": None,
            "accepted_tokens": None,
            "accept_length": None,
            "verification_steps": None,
            "decode_speedup_vs_baseline": None,
            "machine_roofline_tps": None,
            "decode_roofline_ratio": None,
            "content_class": "tool_loop",
            "prompt_identity": "tool-loop-v1",
            "concurrency": args.concurrency,
            "warmup_id": args.warmup_id,
            **sampling_record_fields(sampling_controls),
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
