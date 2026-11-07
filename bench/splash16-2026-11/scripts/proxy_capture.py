#!/usr/bin/env python3
"""A fake HTTP proxy for the key-leak check: it records each request and whether it holds an API key, never the key.

usage: proxy_capture.py --port 9099 --out results/proxy-1.6.0.jsonl     Answers every request with 502.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def record(request_line: str, headers) -> dict:
    names = {k.lower() for k in headers.keys()}
    return {"request": request_line, "has_key": bool(names & {"authorization", "x-api-key"})}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def _handle(self):
            with args.out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record(self.requestline, self.headers)) + "\n")
            self.send_error(502)

        do_GET = do_POST = do_CONNECT = do_HEAD = _handle

        def log_message(self, *a):
            pass

    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
