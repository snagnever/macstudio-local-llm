import json
import time
from dataclasses import dataclass
from typing import Any, Iterable, Iterator
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class StreamResult:
    text: str
    ttft_ms: float
    e2e_ms: float
    usage: dict[str, Any]
    raw_chunks: int


def iter_sse_json(lines: Iterable[bytes]) -> Iterator[dict[str, Any]]:
    for raw_line in lines:
        line = raw_line.decode("utf-8").strip()
        if not line or line.startswith(":") or not line.startswith("data:"):
            continue

        data = line[5:].strip()
        if data == "[DONE]":
            break
        yield json.loads(data)


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
    content: list[str] = []
    usage: dict[str, Any] = {}
    chunk_count = 0

    with urlopen(request, timeout=timeout_s) as response:
        for chunk in iter_sse_json(response):
            chunk_count += 1
            if chunk.get("usage"):
                usage = chunk["usage"]

            choices = chunk.get("choices") or []
            delta = choices[0].get("delta", {}) if choices else {}
            piece = delta.get("content") or delta.get("reasoning_content") or ""
            if piece and first_content_at is None:
                first_content_at = time.perf_counter()
            content.append(piece)

    finished = time.perf_counter()
    first = first_content_at or finished
    return StreamResult(
        text="".join(content),
        ttft_ms=(first - started) * 1000,
        e2e_ms=(finished - started) * 1000,
        usage=usage,
        raw_chunks=chunk_count,
    )
