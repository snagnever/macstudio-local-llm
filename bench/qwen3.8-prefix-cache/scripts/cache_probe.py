#!/usr/bin/env python3
import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fixtures import (
    build_code_fixture,
    build_fixture,
    build_suffix,
    mutate_middle_tokens,
    sha256_tokens,
)
from metrics import normalize_server_measurements, parse_prometheus
from sse_client import StreamResult, normalize_mlx_dspark_metrics, stream_chat


SCENARIOS = (
    "cold",
    "identical",
    "append",
    "middle_mutation",
    "tool_turn",
)

NEEDLE_QUESTION = (
    "Return only the three verified keys stored closest to 10%, 50%, and 90% "
    "of the audit records, in that order."
)

SAMPLING_CONTROLS = {
    "temperature": 0,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "repetition_penalty": 1.0,
    "reasoning_effort": "xhigh",
}
WARMUP_ID = "cache-probe-independent-v2"
MAX_TOKENS = 2048
REQUEST_RESERVE_TOKENS = MAX_TOKENS + 1024 + 512


def fixture_token_target(context_size: int) -> int:
    """Reserve room for the chat template and the bounded diagnostic output."""
    if context_size <= REQUEST_RESERVE_TOKENS:
        raise ValueError(
            f"context size must exceed the {REQUEST_RESERVE_TOKENS}-token request reserve"
        )
    return context_size - REQUEST_RESERVE_TOKENS


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


class LocalTokenizer:
    def __init__(self, model_path: Path):
        try:
            from transformers import AutoTokenizer
        except ImportError as error:
            raise RuntimeError(
                "local tokenization requires the runtime's Python environment"
            ) from error
        self._tokenizer = AutoTokenizer.from_pretrained(
            str(model_path), local_files_only=True, trust_remote_code=True
        )

    def __call__(self, text: str) -> list[int]:
        return list(self._tokenizer.encode(text, add_special_tokens=False))


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
        if runtime == "MTPLX":
            payload = json.loads(text)
            latest = payload.get("latest") if isinstance(payload, dict) else None
            if not isinstance(latest, dict):
                return {}
            metrics: dict[str, float] = {}
            _flatten_json_metrics(latest, prefix="mtplx", result=metrics)
            aliases = {
                "accepted_drafts": "accepted_tokens",
                "verify_calls": "verification_steps",
            }
            for source, target in aliases.items():
                value = latest.get(source)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    metrics[f"mtplx.{target}"] = float(value)
            return metrics
        return parse_prometheus(text)
    except HTTPError as error:
        if error.code in (404, 405):
            return {}
        raise


def _json_snapshot(url: Optional[str]) -> dict[str, Any]:
    if not url:
        return {}
    with urlopen(url, timeout=10) as response:
        payload = json.load(response)
    return payload if isinstance(payload, dict) else {}


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
    if "OQ4E" in upper:
        return "oq4e"
    if "MTPLX-OPTIMIZED-SPEED" in upper:
        return "mtplx-speed"
    if "AWQ" in upper:
        return "awq5"
    for label in ("UD-Q8_K_XL", "UD-Q6_K_XL", "UD-Q4_K_XL", "8BIT"):
        if label in upper:
            return label.lower()
    return "unknown"


def _base_messages(
    text: str, question: str = NEEDLE_QUESTION, repeat: Optional[int] = None
) -> list[dict[str, Any]]:
    trial = f" Cache probe trial {repeat:03d}." if repeat is not None else ""
    return [
        {
            "role": "system",
            "content": f"You are a deterministic audit retrieval assistant.{trial}",
        },
        {"role": "user", "content": f"{text}\n\n{question}"},
    ]


def _priming_messages(
    fixture_text: str,
    repeat: int,
    question: str = NEEDLE_QUESTION,
) -> list[dict[str, Any]]:
    return _base_messages(fixture_text, question, repeat)


def _messages_for_scenario(
    name: str,
    fixture_text: str,
    mutated_text: str,
    suffix: str,
    repeat: int,
    question: str = NEEDLE_QUESTION,
) -> list[dict[str, Any]]:
    if name == "middle_mutation":
        return _base_messages(mutated_text, question, repeat)
    return scenario_messages(
        name, _base_messages(fixture_text, question, repeat), suffix
    )


def _payload(
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
        "max_tokens": MAX_TOKENS,
        **(sampling_controls or SAMPLING_CONTROLS),
    }
    if specprefill is not None:
        payload["specprefill"] = specprefill
    if specprefill_keep_pct is not None:
        payload["specprefill_keep_pct"] = specprefill_keep_pct
    if specprefill_threshold is not None:
        payload["specprefill_threshold"] = specprefill_threshold
    return payload


def _prime_payload(
    model: str,
    messages: list[dict[str, Any]],
    *,
    specprefill: Optional[bool] = None,
    specprefill_keep_pct: Optional[float] = None,
    specprefill_threshold: Optional[int] = None,
    sampling_controls: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload = _payload(
        model,
        messages,
        specprefill=specprefill,
        specprefill_keep_pct=specprefill_keep_pct,
        specprefill_threshold=specprefill_threshold,
        sampling_controls=sampling_controls,
    )
    payload["max_tokens"] = 1
    return payload


def _warmup_payload(
    model: str,
    warmup_text: str,
    *,
    sampling_controls: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "This is an unrelated warmup request."},
            {"role": "user", "content": warmup_text},
        ],
        "max_tokens": 64,
        **(sampling_controls or SAMPLING_CONTROLS),
    }


def needle_verdicts(
    result: StreamResult, expected_needles: Union[str, tuple[str, ...]]
) -> dict[str, bool]:
    if isinstance(expected_needles, str):
        expected_needles = (expected_needles,)
    return {
        position: result.finish_reason != "length" and needle in result.text
        for position, needle in zip(("10", "50", "90"), expected_needles)
    }


def result_correct(
    result: StreamResult, expected_needle: Union[str, tuple[str, ...]]
) -> bool:
    needles = (expected_needle,) if isinstance(expected_needle, str) else expected_needle
    return all(needle_verdicts(result, needles).values())


def code_result_verdict(
    result: StreamResult, expected_result: int
) -> tuple[bool, Optional[int]]:
    """Validate the derived code result as the one-field JSON response contract."""
    if result.finish_reason == "length":
        return False, None
    try:
        payload = json.loads(result.text.strip())
    except (json.JSONDecodeError, AttributeError):
        return False, None
    if (
        not isinstance(payload, dict)
        or set(payload) != {"rolling_checksum"}
        or isinstance(payload["rolling_checksum"], bool)
        or not isinstance(payload["rolling_checksum"], int)
    ):
        return False, None
    value = payload["rolling_checksum"]
    return value == expected_result, value


def _prompt_identity(messages: list[dict[str, Any]]) -> str:
    canonical = json.dumps(messages, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _static_prefix_hash(messages: list[dict[str, Any]]) -> str:
    prefix = [
        message
        for message in messages
        if message.get("role") == "system"
        or message.get("role") == "tool"
        or message.get("tool_calls")
    ]
    canonical = json.dumps(prefix, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
    expected_needles: Union[str, tuple[str, ...]],
    fixture_hash: str,
    metrics_before: dict[str, float],
    metrics_after: dict[str, float],
    suffix_tokens: int,
    mutation_prefix_tokens: int,
    mutation_tokens: int,
    code_expected_result: Optional[int] = None,
    dspark_machine: Optional[dict[str, Any]] = None,
    dspark_metrics: Optional[dict[str, Any]] = None,
    drafter_id: Optional[str] = None,
    drafter_revision: Optional[str] = None,
    sampling_controls: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    usage = result.usage
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    cached_tokens = cached_tokens_from_usage(usage)
    performance = _performance(result, prompt_tokens, cached_tokens)
    server = normalize_server_measurements(usage, metrics_before, metrics_after)
    dspark_extension = {**(dspark_metrics or {}), **(usage.get("x_mlx_dspark") or {})}
    dspark = normalize_mlx_dspark_metrics(dspark_extension, dspark_machine)
    if dspark["cached_tokens"] is not None:
        cached_tokens = int(dspark["cached_tokens"])
        performance = _performance(result, prompt_tokens, cached_tokens)
    needles = needle_verdicts(result, expected_needles)
    code_result_ok, code_result_value = (
        code_result_verdict(result, code_expected_result)
        if code_expected_result is not None
        else (None, None)
    )
    now = datetime.now(timezone.utc)
    controls = sampling_controls or SAMPLING_CONTROLS
    mtp_acceptance = mtp_acceptance_from_snapshots(metrics_before, metrics_after)
    if (
        mtp_acceptance is None
        and isinstance(server["drafted_tokens"], (int, float))
        and server["drafted_tokens"] > 0
        and isinstance(server["accepted_tokens"], (int, float))
    ):
        mtp_acceptance = min(
            1.0, max(0.0, server["accepted_tokens"] / server["drafted_tokens"])
        )
    return {
        "schema_version": 3,
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
        "content_class": getattr(args, "content_class", "audit_retrieval"),
        "prompt_identity": _prompt_identity(getattr(args, "messages", [])),
        "concurrency": 1,
        "warmup_id": WARMUP_ID,
        "suffix_tokens": suffix_tokens if scenario in {"append", "tool_turn"} else 0,
        "mutation_prefix_tokens": (
            mutation_prefix_tokens if scenario == "middle_mutation" else None
        ),
        "mutation_tokens": mutation_tokens if scenario == "middle_mutation" else 0,
        "repeat": repeat,
        "cache_enabled": args.cache_enabled,
        "mtp_enabled": args.mtp_enabled,
        "specprefill_enabled": bool(getattr(args, "specprefill", False)),
        "specprefill_draft_model": getattr(args, "specprefill_draft_model", None),
        "specprefill_draft_revision": getattr(args, "specprefill_draft_revision", None),
        "specprefill_keep_pct": getattr(args, "specprefill_keep_pct", None),
        "specprefill_threshold": getattr(args, "specprefill_threshold", None),
        "specprefill_selected_tokens": server["specprefill_selected_tokens"],
        "specprefill_scored_tokens": server["specprefill_scored_tokens"],
        "specprefill_draft_ms": server["specprefill_draft_ms"],
        "specprefill_target_ms": server["specprefill_target_ms"],
        "static_prefix_cached_tokens": server["static_prefix_cached_tokens"],
        "static_prefix_boundary_tokens": server["static_prefix_boundary_tokens"],
        "static_prefix_hash": getattr(args, "static_prefix_hash", None),
        "static_prefix_prior_match": getattr(args, "static_prefix_prior_match", False),
        "ane_prefill_enabled": bool(getattr(args, "ane_prefill_enabled", False)),
        "ane_prefill_tuned": server["ane_prefill_tuned"],
        "ane_compiled_mlp_layers": server["ane_compiled_mlp_layers"],
        "ane_compiled_gdn_layers": server["ane_compiled_gdn_layers"],
        "ane_executed_operations": server["ane_executed_operations"],
        "prompt_work_mode": server["prompt_work_mode"],
        "prompt_tokens": prompt_tokens,
        "cached_tokens": cached_tokens,
        "cache_hit_ratio": cache_hit_ratio(cached_tokens, prompt_tokens),
        "ttft_ms": dspark["ttft_ms"] if dspark["ttft_ms"] is not None else result.ttft_ms,
        "e2e_ms": result.e2e_ms,
        **{**performance, "decode_tps": dspark["decode_tps"] if dspark["decode_tps"] is not None else performance["decode_tps"]},
        "mtp_acceptance": mtp_acceptance,
        "speculation_mode": dspark["speculation_mode"] or server["speculation_mode"],
        "drafter_id": drafter_id or server["drafter_id"],
        "drafter_revision": drafter_revision or server["drafter_revision"],
        "draft_cap_policy": server["draft_cap_policy"],
        "draft_cap_resolved": dspark["draft_cap_resolved"] if dspark["draft_cap_resolved"] is not None else server["draft_cap_resolved"],
        "drafted_tokens": server["drafted_tokens"],
        "accepted_tokens": server["accepted_tokens"],
        "accept_length": dspark["accept_length"] if dspark["accept_length"] is not None else server["accept_length"],
        "verification_steps": dspark["verification_steps"] if dspark["verification_steps"] is not None else server["verification_steps"],
        "decode_speedup_vs_baseline": None,
        "machine_roofline_tps": dspark["machine_roofline_tps"] if dspark["machine_roofline_tps"] is not None else server["machine_roofline_tps"],
        "decode_roofline_ratio": dspark["decode_roofline_ratio"] if dspark["decode_roofline_ratio"] is not None else server["decode_roofline_ratio"],
        "finish_reason": result.finish_reason,
        "reasoning_chars": len(result.reasoning_text),
        "needle_verdicts": needles,
        "code_result_expected": code_expected_result,
        "code_result_value": code_result_value,
        "code_result_verdict": code_result_ok,
        "static_prefix_correct": (
            scenario != "cold"
            and cached_tokens > 0
            and all(needles.values())
            and getattr(args, "static_prefix_matches", False)
            and getattr(args, "static_prefix_prior_match", False)
            and isinstance(server["static_prefix_boundary_tokens"], int)
            and server["static_prefix_boundary_tokens"] > 0
            and isinstance(server["static_prefix_cached_tokens"], (int, float))
            and server["static_prefix_cached_tokens"] >= server["static_prefix_boundary_tokens"]
        ),
        "correct": code_result_ok if code_expected_result is not None else all(needles.values()),
        "ram_peak_gb": None,
        "swap_delta_gb": None,
        "gpu_temp_start_c": None,
        "gpu_temp_peak_c": None,
        "fixture_token_hash": fixture_hash,
        "greedy_tokens_hash": getattr(args, "greedy_tokens_hash", None),
        "logit_tie_evidence": None,
        "temperature": controls["temperature"],
        "top_p": controls["top_p"],
        "top_k": controls["top_k"],
        "min_p": controls["min_p"],
        "presence_penalty": controls["presence_penalty"],
        "frequency_penalty": controls["frequency_penalty"],
        "repetition_penalty": controls["repetition_penalty"],
        "reasoning_effort": controls["reasoning_effort"],
        "max_tokens": MAX_TOKENS,
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
    parser.add_argument("--api-model")
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--runtime-revision", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--context", required=True, type=int)
    parser.add_argument("--content-class", default="audit_retrieval")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--cache-enabled", action="store_true")
    parser.add_argument("--mtp-enabled", action="store_true")
    parser.add_argument("--specprefill", type=lambda value: value.lower() == "true")
    parser.add_argument("--specprefill-keep-pct", type=float)
    parser.add_argument("--specprefill-threshold", type=int)
    parser.add_argument("--specprefill-draft-model")
    parser.add_argument("--specprefill-draft-revision")
    parser.add_argument("--ane-prefill-enabled", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metrics-url")
    parser.add_argument("--mlx-dspark-metrics-url")
    parser.add_argument("--machine-url")
    parser.add_argument("--drafter-id")
    parser.add_argument("--drafter-revision")
    parser.add_argument("--tokenizer-path", type=Path)
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
    sampling_controls = {
        **SAMPLING_CONTROLS,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "reasoning_effort": args.reasoning_effort,
    }
    api_model = args.api_model or args.model
    tokenizer = (
        LocalTokenizer(args.tokenizer_path)
        if args.tokenizer_path
        else RuntimeTokenizer(args.base_url, api_model)
    )
    if args.content_class == "code":
        fixture = build_code_fixture(fixture_token_target(args.context), tokenizer)
    else:
        fixture = build_fixture(fixture_token_target(args.context), tokenizer)
    fixture_hash = sha256_tokens(fixture.token_ids)
    suffix_trailer = (
        f"Tool result confirms {fixture.needles[0]}. {fixture.question}"
        if fixture.needles
        else f"Tool result confirms the deterministic program completed. {fixture.question}"
    )
    suffix, suffix_token_ids = build_suffix(
        1024,
        tokenizer,
        suffix_trailer,
    )
    mutated_text, mutation_prefix_tokens, mutation_tokens = mutate_middle_tokens(
        fixture.text, 64, tokenizer
    )
    warmup_text, _ = build_suffix(512, tokenizer, "Warmup complete.")
    stream_chat(
        args.base_url,
        _warmup_payload(
            api_model, warmup_text, sampling_controls=sampling_controls
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as output:
        for scenario in SCENARIOS:
            for repeat in range(1, args.repeat + 1):
                prime_messages = (
                    None
                    if scenario == "cold"
                    else _priming_messages(fixture.text, repeat, fixture.question)
                )
                if prime_messages is not None:
                    stream_chat(
                        args.base_url,
                        _prime_payload(
                            api_model,
                            prime_messages,
                            specprefill=args.specprefill,
                            specprefill_keep_pct=args.specprefill_keep_pct,
                            specprefill_threshold=args.specprefill_threshold,
                            sampling_controls=sampling_controls,
                        ),
                    )
                messages = _messages_for_scenario(
                    scenario,
                    fixture.text,
                    mutated_text,
                    suffix,
                    repeat,
                    fixture.question,
                )
                args.messages = messages
                args.static_prefix_hash = _static_prefix_hash(
                    prime_messages if prime_messages is not None else messages
                )
                args.static_prefix_prior_match = prime_messages is not None
                args.static_prefix_matches = prime_messages is not None
                metrics_before = _metrics_snapshot(args.metrics_url, args.runtime)
                result = stream_chat(
                    args.base_url,
                    _payload(
                        api_model,
                        messages,
                        specprefill=args.specprefill,
                        specprefill_keep_pct=args.specprefill_keep_pct,
                        specprefill_threshold=args.specprefill_threshold,
                        sampling_controls=sampling_controls,
                    ),
                )
                metrics_after = _metrics_snapshot(args.metrics_url, args.runtime)
                dspark_machine = _json_snapshot(args.machine_url)
                dspark_metrics = _json_snapshot(args.mlx_dspark_metrics_url)
                args.greedy_tokens_hash = sha256_tokens(tokenizer(result.text))
                record = _record(
                    args,
                    scenario,
                    repeat,
                    result,
                    fixture.needles,
                    fixture_hash,
                    metrics_before,
                    metrics_after,
                    len(suffix_token_ids),
                    mutation_prefix_tokens,
                    mutation_tokens,
                    fixture.expected_result,
                    dspark_machine,
                    dspark_metrics,
                    args.drafter_id,
                    args.drafter_revision,
                    sampling_controls,
                )
                output.write(json.dumps(record, sort_keys=True) + "\n")
                output.flush()
                print(json.dumps(record, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
