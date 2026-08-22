#!/usr/bin/env python3
import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fixtures import build_fixture, build_suffix, mutate_middle_tokens, sha256_tokens
from metrics import parse_prometheus
from sse_client import StreamResult, stream_chat


SCENARIOS = (
    "cold",
    "identical",
    "append",
    "middle_mutation",
    "tool_turn",
)

NEEDLE_QUESTION = (
    "Return only the verified key stored closest to 10% of the audit records."
)


def fixture_token_target(context_size: int) -> int:
    """Reserve room for the chat template and the bounded diagnostic output."""
    if context_size <= 2560:
        raise ValueError("context size must exceed the 2560-token request reserve")
    return context_size - 2560


def cache_hit_ratio(cached_tokens: int, prompt_tokens: int) -> float:
    if prompt_tokens <= 0:
        return 0.0
    return min(1.0, max(0.0, cached_tokens / prompt_tokens))


def cached_tokens_from_usage(usage: dict[str, Any]) -> int:
    details = usage.get("prompt_tokens_details") or {}
    return int(details.get("cached_tokens") or 0)


def token_ids_from_response(response: dict[str, Any]) -> list[int]:
    candidates = (
        response.get("tokens"),
        response.get("token_ids"),
        response.get("data"),
    )
    tokens = next((value for value in candidates if isinstance(value, list)), None)
    if tokens is None or not all(type(token) is int for token in tokens):
        raise ValueError("tokenize endpoint must return a list of integer token IDs")
    return tokens


def scenario_messages(
    name: str, base: list[dict[str, Any]], suffix: str
) -> list[dict[str, Any]]:
    messages = deepcopy(base)
    if name in {"identical", "cold"}:
        return messages
    if name == "append":
        messages.append({"role": "user", "content": suffix})
        return messages
    if name == "tool_turn":
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_fixture_1",
                            "type": "function",
                            "function": {
                                "name": "read_fixture",
                                "arguments": '{"path":"audit.txt"}',
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_fixture_1",
                    "content": suffix,
                },
            ]
        )
        return messages
    raise ValueError(f"scenario requires dedicated mutation path: {name}")


class RuntimeTokenizer:
    def __init__(self, base_url: str, model: str, timeout_s: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def __call__(self, text: str) -> list[int]:
        attempts = [
            (
                f"{self.base_url}/tokenize",
                {"model": self.model, "prompt": text},
            ),
        ]
        if self.base_url.endswith("/v1"):
            attempts.append(
                (
                    f"{self.base_url[:-3]}/tokenize",
                    {"content": text, "add_special": False},
                )
            )

        last_error: Optional[Exception] = None
        for url, payload in attempts:
            request = Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=self.timeout_s) as response:
                    body = json.load(response)
                return token_ids_from_response(body)
            except (HTTPError, ValueError, json.JSONDecodeError) as error:
                last_error = error

        raise RuntimeError("runtime tokenize endpoint is unavailable") from last_error


def _metrics_snapshot(url: Optional[str]) -> dict[str, float]:
    if not url:
        return {}
    with urlopen(url, timeout=10) as response:
        return parse_prometheus(response.read().decode("utf-8"))


def _metric_by_suffix(
    metrics: dict[str, float], suffix: str
) -> Optional[float]:
    for name, value in metrics.items():
        if name.split("{")[0].endswith(suffix):
            return value
    return None


def mtp_acceptance_from_snapshots(
    before: dict[str, float], after: dict[str, float]
) -> Optional[float]:
    accepted_before = _metric_by_suffix(before, "draft_tokens_accepted_total") or 0.0
    generated_before = _metric_by_suffix(before, "draft_tokens_generated_total") or 0.0
    accepted_after = _metric_by_suffix(after, "draft_tokens_accepted_total")
    generated_after = _metric_by_suffix(after, "draft_tokens_generated_total")
    if accepted_after is None or generated_after is None:
        return None
    accepted = accepted_after - accepted_before
    generated = generated_after - generated_before
    if generated <= 0:
        return None
    return min(1.0, max(0.0, accepted / generated))


def _quant_label(model: str) -> str:
    upper = model.upper()
    for label in ("UD-Q8_K_XL", "UD-Q6_K_XL", "UD-Q4_K_XL", "8BIT"):
        if label in upper:
            return label.lower()
    return "unknown"


def _base_messages(text: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": "You are a deterministic audit retrieval assistant.",
        },
        {"role": "user", "content": f"{text}\n\n{NEEDLE_QUESTION}"},
    ]


def _messages_for_scenario(
    name: str,
    fixture_text: str,
    mutated_text: str,
    suffix: str,
    repeat: int,
) -> list[dict[str, Any]]:
    if name == "middle_mutation":
        return _base_messages(mutated_text)
    messages = scenario_messages(name, _base_messages(fixture_text), suffix)
    if name == "cold":
        messages[0]["content"] = (
            f"Cold cache-buster {repeat:03d}. " + messages[0]["content"]
        )
    return messages


def _payload(model: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model": model,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0,
        "reasoning_effort": "xhigh",
    }


def _warmup_payload(model: str, warmup_text: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "This is an unrelated warmup request."},
            {"role": "user", "content": warmup_text},
        ],
        "max_tokens": 64,
        "temperature": 0,
        "reasoning_effort": "xhigh",
    }


def result_correct(result: StreamResult, expected_needle: str) -> bool:
    return result.finish_reason != "length" and expected_needle in result.text


def _performance(result: StreamResult, prompt_tokens: int, cached_tokens: int):
    prefill_tokens = max(0, prompt_tokens - cached_tokens)
    prompt_seconds = result.ttft_ms / 1000
    decode_seconds = max(0.0, result.e2e_ms - result.ttft_ms) / 1000
    completion_tokens = int(result.usage.get("completion_tokens") or 0)
    return {
        "prefill_tokens": prefill_tokens,
        "prompt_tps": prefill_tokens / prompt_seconds if prompt_seconds else 0.0,
        "decode_tps": completion_tokens / decode_seconds if decode_seconds else 0.0,
        "completion_tokens": completion_tokens,
    }


def _record(
    args: argparse.Namespace,
    scenario: str,
    repeat: int,
    result: StreamResult,
    expected_needle: str,
    fixture_hash: str,
    metrics_before: dict[str, float],
    metrics_after: dict[str, float],
    suffix_tokens: int,
    mutation_prefix_tokens: int,
    mutation_tokens: int,
) -> dict[str, Any]:
    usage = result.usage
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    cached_tokens = cached_tokens_from_usage(usage)
    performance = _performance(result, prompt_tokens, cached_tokens)
    now = datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "run_id": (
            f"{now.strftime('%Y%m%dT%H%M%SZ')}-{args.arm}-"
            f"{args.context}-{scenario}-r{repeat}"
        ),
        "session_id": args.session_id,
        "runtime": args.runtime,
        "runtime_revision": args.runtime_revision,
        "model_id": args.model,
        "model_revision": args.model_revision,
        "quant": _quant_label(args.model),
        "arm": args.arm,
        "context_target": args.context,
        "scenario": scenario,
        "suffix_tokens": suffix_tokens if scenario in {"append", "tool_turn"} else 0,
        "mutation_prefix_tokens": (
            mutation_prefix_tokens if scenario == "middle_mutation" else None
        ),
        "mutation_tokens": mutation_tokens if scenario == "middle_mutation" else 0,
        "repeat": repeat,
        "cache_enabled": args.cache_enabled,
        "mtp_enabled": args.mtp_enabled,
        "prompt_tokens": prompt_tokens,
        "cached_tokens": cached_tokens,
        "cache_hit_ratio": cache_hit_ratio(cached_tokens, prompt_tokens),
        "ttft_ms": result.ttft_ms,
        "e2e_ms": result.e2e_ms,
        **performance,
        "mtp_acceptance": mtp_acceptance_from_snapshots(
            metrics_before, metrics_after
        ),
        "finish_reason": result.finish_reason,
        "reasoning_chars": len(result.reasoning_text),
        "correct": result_correct(result, expected_needle),
        "ram_peak_gb": None,
        "swap_delta_gb": None,
        "gpu_temp_start_c": None,
        "gpu_temp_peak_c": None,
        "fixture_token_hash": fixture_hash,
        "error": (
            "finish_reason:length" if result.finish_reason == "length" else None
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure Qwen3.8 prefix-cache scenarios through an OpenAI API."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--runtime-revision", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--context", required=True, type=int)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--cache-enabled", action="store_true")
    parser.add_argument("--mtp-enabled", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metrics-url")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    tokenizer = RuntimeTokenizer(args.base_url, args.model)
    fixture = build_fixture(fixture_token_target(args.context), tokenizer)
    fixture_hash = sha256_tokens(fixture.token_ids)
    suffix, suffix_token_ids = build_suffix(
        1024,
        tokenizer,
        f"Tool result confirms {fixture.needles[0]}. {NEEDLE_QUESTION}",
    )
    mutated_text, mutation_prefix_tokens, mutation_tokens = mutate_middle_tokens(
        fixture.text, 64, tokenizer
    )
    warmup_text, _ = build_suffix(512, tokenizer, "Warmup complete.")
    stream_chat(args.base_url, _warmup_payload(args.model, warmup_text))
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("a", encoding="utf-8") as output:
        for scenario in SCENARIOS:
            for repeat in range(1, args.repeat + 1):
                messages = _messages_for_scenario(
                    scenario, fixture.text, mutated_text, suffix, repeat
                )
                metrics_before = _metrics_snapshot(args.metrics_url)
                result = stream_chat(args.base_url, _payload(args.model, messages))
                metrics_after = _metrics_snapshot(args.metrics_url)
                record = _record(
                    args,
                    scenario,
                    repeat,
                    result,
                    fixture.needles[0],
                    fixture_hash,
                    metrics_before,
                    metrics_after,
                    len(suffix_token_ids),
                    mutation_prefix_tokens,
                    mutation_tokens,
                )
                output.write(json.dumps(record, sort_keys=True) + "\n")
                output.flush()
                print(json.dumps(record, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
