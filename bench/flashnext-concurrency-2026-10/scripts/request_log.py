#!/usr/bin/env python3
"""HTTP proxy in front of a local Anthropic-compatible server that writes one record per request.

    python3 request_log.py --listen PORT --upstream http://HOST:PORT --out FILE.jsonl --stream LABEL [--t0 EPOCH]

Every request is forwarded unchanged (method, path, headers, body) and the response is streamed back to the
client chunk by chunk. For a text/event-stream response the proxy parses the SSE events as they pass and
appends one JSON line to --out in the schema of claude_requests.py:
    {"t_start_s", "ttft_s", "t_end_s", "input_tokens", "cached_tokens", "output_tokens", "tps", "status", "stream"}
ttft_s is the time to the first content_block_delta with text_delta or thinking_delta (message_start arrives
before the prefill, so it is not the first token). t_start_s and t_end_s are relative to --t0, a clock shared
by all the proxies of one rep. cached_tokens is null when the server does not report cache_read_input_tokens.
A response without a content delta (HTTP error, aborted stream) is logged with ttft_s null and its real status.

Python 3.9 stdlib only (the rig's python3).
"""
from __future__ import annotations

import argparse
import http.client
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional, Sequence
from urllib.parse import urlsplit

CONTENT_DELTAS = ("text_delta", "thinking_delta")
HOP_HEADERS = {"host", "content-length", "transfer-encoding", "connection", "keep-alive"}


def _usage_tokens(usage: dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    """(input_tokens, cached_tokens) from a usage block; cached is None when the server does not report it."""
    inp = usage.get("input_tokens")
    cached = usage.get("cache_read_input_tokens")
    return (int(inp) if inp is not None else None, int(cached) if cached is not None else None)


def parse_sse(events: list[tuple[str, dict[str, Any]]], t_start: float, times: list[float], t0: float,
              stream: Optional[str], status: int) -> dict[str, Any]:
    """One request record from the SSE events of a response, each with the instant it was received."""
    input_tokens: Optional[int] = None
    cached: Optional[int] = None
    output_tokens = 0
    t_first: Optional[float] = None
    for (name, data), t in zip(events, times):
        kind = data.get("type") or name
        if kind == "message_start":
            input_tokens, cached = _usage_tokens((data.get("message") or {}).get("usage") or {})
        elif kind == "content_block_delta" and t_first is None:
            if (data.get("delta") or {}).get("type") in CONTENT_DELTAS:
                t_first = t
        elif kind == "message_delta" and data.get("usage"):
            out = data["usage"].get("output_tokens")
            if out is not None:
                output_tokens = int(out)
    t_end = times[-1] if times else t_start
    tps: Optional[float] = None
    if t_first is not None and t_end - t_first > 0:
        tps = round(output_tokens / (t_end - t_first), 1)
    return {"t_start_s": round(t_start - t0, 3),
            "ttft_s": round(t_first - t_start, 3) if t_first is not None else None,
            "t_end_s": round(t_end - t0, 3),
            "input_tokens": input_tokens if input_tokens is not None else 0,
            "cached_tokens": cached, "output_tokens": output_tokens, "tps": tps, "status": status, "stream": stream}


class _SSEParser:
    """Accumulates raw chunks and yields (event_name, data) per blank-line-terminated event."""

    def __init__(self) -> None:
        self.buf = b""
        self.events: list[tuple[str, dict[str, Any]]] = []
        self.times: list[float] = []

    def feed(self, chunk: bytes, now: float) -> None:
        self.buf += chunk
        while b"\n\n" in self.buf:
            block, self.buf = self.buf.split(b"\n\n", 1)
            self._event(block.decode("utf-8", errors="replace"), now)

    def _event(self, block: str, now: float) -> None:
        name = ""
        data_lines = []
        for line in block.replace("\r\n", "\n").split("\n"):
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if not data_lines:
            return
        try:
            data = json.loads("\n".join(data_lines))
        except ValueError:
            return
        if isinstance(data, dict):
            self.events.append((name, data))
            self.times.append(now)


def _record_from_json(body: bytes, t_start: float, t_end: float, t0: float, stream: Optional[str],
                      status: int) -> dict[str, Any]:
    """Non-streaming response: tokens from its usage block if the body is JSON, ttft_s null."""
    input_tokens: Optional[int] = None
    cached: Optional[int] = None
    output_tokens = 0
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
    except ValueError:
        data = None
    if isinstance(data, dict) and isinstance(data.get("usage"), dict):
        input_tokens, cached = _usage_tokens(data["usage"])
        output_tokens = int(data["usage"].get("output_tokens") or 0)
    return {"t_start_s": round(t_start - t0, 3), "ttft_s": None, "t_end_s": round(t_end - t0, 3),
            "input_tokens": input_tokens if input_tokens is not None else 0, "cached_tokens": cached,
            "output_tokens": output_tokens, "tps": None, "status": status, "stream": stream}


class _ProxyServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr: tuple[str, int], handler: type, upstream: str, out: Path, stream: Optional[str],
                 t0: float) -> None:
        super().__init__(addr, handler)
        u = urlsplit(upstream)
        self.upstream_host = u.hostname or "127.0.0.1"
        self.upstream_port = u.port or 80
        self.out = Path(out)
        self.stream = stream
        self.t0 = t0
        self.lock = threading.Lock()

    def write_record(self, rec: dict[str, Any]) -> None:
        line = json.dumps(rec) + "\n"
        with self.lock:
            with open(self.out, "a", encoding="utf-8") as fh:
                fh.write(line)


class _ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: _ProxyServer

    def log_message(self, *args: Any) -> None:
        pass

    def _forward(self) -> None:
        t_start = time.time()
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_HEADERS}
        if body:
            headers["Content-Length"] = str(len(body))
        conn = http.client.HTTPConnection(self.server.upstream_host, self.server.upstream_port, timeout=3600)
        try:
            conn.request(self.command, self.path, body=body or None, headers=headers)
            resp = conn.getresponse()
        except OSError as exc:
            self.send_error(502, f"upstream unreachable: {exc}")
            self.server.write_record(_record_from_json(b"", t_start, time.time(), self.server.t0,
                                                       self.server.stream, 502))
            conn.close()
            return
        status = resp.status
        ctype = resp.getheader("Content-Type") or ""
        is_sse = "text/event-stream" in ctype
        self.send_response(status)
        for k, v in resp.getheaders():
            if k.lower() in HOP_HEADERS and k.lower() != "content-length":
                continue
            if k.lower() == "content-length" and is_sse:
                continue
            self.send_header(k, v)
        if is_sse:
            self.send_header("Connection", "close")
        self.end_headers()
        parser = _SSEParser()
        raw = b""
        try:
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                now = time.time()
                self.wfile.write(chunk)
                self.wfile.flush()
                if is_sse:
                    parser.feed(chunk, now)
                else:
                    raw += chunk
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            conn.close()
        t_end = time.time()
        if is_sse:
            rec = parse_sse(parser.events, t_start, parser.times, self.server.t0, self.server.stream, status)
            rec["t_end_s"] = round(t_end - self.server.t0, 3)
        else:
            rec = _record_from_json(raw, t_start, t_end, self.server.t0, self.server.stream, status)
        self.server.write_record(rec)
        self.close_connection = True

    do_POST = _forward
    do_GET = _forward
    do_PUT = _forward
    do_DELETE = _forward


def make_server(host: str, port: int, upstream: str, out: Path, stream: Optional[str], t0: float) -> ThreadingHTTPServer:
    return _ProxyServer((host, port), _ProxyHandler, upstream, out, stream, t0)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Record one line per request while proxying a local LLM server.")
    p.add_argument("--listen", type=int, required=True, help="port on 127.0.0.1")
    p.add_argument("--upstream", required=True, help="http://HOST:PORT of the real server")
    p.add_argument("--out", required=True, help="JSONL file, one record appended per request")
    p.add_argument("--stream", default=None, help="label written in every record (one per Claude Code session)")
    p.add_argument("--t0", type=float, default=None, help="epoch seconds of the common clock (default: now)")
    args = p.parse_args(argv)
    t0 = args.t0 if args.t0 is not None else time.time()
    server = make_server("127.0.0.1", args.listen, args.upstream, Path(args.out), args.stream, t0)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
