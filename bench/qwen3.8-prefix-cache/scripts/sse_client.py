import json
import time
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Optional
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class StreamResult:
    text: str
    reasoning_text: str
    finish_reason: Optional[str]
    ttft_ms: float
    e2e_ms: float
    usage: dict[str, Any]
    raw_chunks: int


def normalize_mlx_dspark_metrics(
    extension: dict[str, Any], machine: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Map only v0.15.0 observed response fields; absent values remain null."""
    result = {
        "speculation_mode": None,
        "ttft_ms": None,
        "prefill_ms": None,
        "decode_ms": None,
        "cached_tokens": None,
        "accept_length": None,
        "draft_cap_resolved": None,
        "decode_tps": None,
        "machine_roofline_tps": None,
        "decode_roofline_ratio": None,
        "verification_steps": None,
        "accepted_tokens": None,
    }
    if not isinstance(extension, dict):
        return result
    result.update(
        {
            "speculation_mode": extension.get("mode"),
            "ttft_ms": _seconds_to_ms(extension.get("ttft_seconds")),
            "prefill_ms": _seconds_to_ms(extension.get("prefill_seconds")),
            "decode_ms": _seconds_to_ms(extension.get("decode_seconds")),
            "cached_tokens": extension.get("cached_tokens"),
            "accept_length": extension.get("accept_len"),
            "draft_cap_resolved": extension.get("cap"),
            "decode_tps": extension.get("decode_tokens_per_sec"),
            "machine_roofline_tps": extension.get("ceiling_tokens_per_sec"),
            "decode_roofline_ratio": extension.get("roofline_ratio"),
            "verification_steps": extension.get("target_forwards"),
        }
    )
    # `/machine` is only a fallback for an explicitly observed last-request verdict.
    if result["decode_tps"] is None and isinstance(machine, dict):
        verdict = machine.get("verdict")
        if isinstance(verdict, dict):
            result["decode_tps"] = verdict.get("decode_tps")
    return result


def _seconds_to_ms(value: Any) -> Optional[float]:
    return float(value) * 1000 if isinstance(value, (int, float)) else None


def iter_sse_json(lines: Iterable[bytes]) -> Iterator[dict[str, Any]]:
    for raw_line in lines:
        line = raw_line.decode("utf-8").strip()
        if not line or line.startswith(":") or not line.startswith("data:"):
            continue

        data = line[5:].strip()
        if data == "[DONE]":
            break
        yield json.loads(data)


def stream_delta_fields(chunks: Iterable[dict[str, Any]]) -> dict[str, Any]:
    content: list[str] = []
    reasoning: list[str] = []
    usage: dict[str, Any] = {}
    server_extensions: dict[str, Any] = {}
    finish_reason = None
    for chunk in chunks:
        if chunk.get("usage"):
            usage = dict(chunk["usage"])
        for name in ("x_mlx_dspark", "x_omlx"):
            if isinstance(chunk.get(name), dict):
                server_extensions[name] = chunk[name]
        choices = chunk.get("choices") or []
        if not choices:
            continue
        choice = choices[0]
        delta = choice.get("delta") or {}
        content.append(delta.get("content") or "")
        reasoning.append(delta.get("reasoning_content") or "")
        if choice.get("finish_reason") is not None:
            finish_reason = choice["finish_reason"]
    return {
        "content": "".join(content),
        "reasoning": "".join(reasoning),
        "finish_reason": finish_reason,
        "usage": {**usage, **server_extensions},
    }


def stream_chat(
    base_url: str, payload: dict[str, Any], timeout_s: int = 900
) -> StreamResult:
    body = dict(payload)
    body["stream"] = True
    body["stream_options"] = {"include_usage": True}
    request = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.perf_counter()
    first_content_at = None
    chunks: list[dict[str, Any]] = []

    with urlopen(request, timeout=timeout_s) as response:
        for chunk in iter_sse_json(response):
            chunks.append(chunk)

            choices = chunk.get("choices") or []
            delta = choices[0].get("delta", {}) if choices else {}
            piece = delta.get("content") or delta.get("reasoning_content") or ""
            if piece and first_content_at is None:
                first_content_at = time.perf_counter()

    finished = time.perf_counter()
    first = first_content_at or finished
    fields = stream_delta_fields(chunks)
    return StreamResult(
        text=fields["content"],
        reasoning_text=fields["reasoning"],
        finish_reason=fields["finish_reason"],
        ttft_ms=(first - started) * 1000,
        e2e_ms=(finished - started) * 1000,
        usage=fields["usage"],
        raw_chunks=len(chunks),
    )
