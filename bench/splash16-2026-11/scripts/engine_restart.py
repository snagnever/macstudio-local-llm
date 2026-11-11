#!/usr/bin/env python3
"""Kill the Splash engine during a stream and record the recovery the 1.6.0 notes describe.

usage: engine_restart.py --base-url http://127.0.0.1:8585 --model ID --boot-seconds N --out results/engine-restart.json
Sends SIGKILL to the campaign server's serve-native process only, found by its parent on the port of --base-url.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LONG = "Write a detailed essay about the history of databases, at least two thousand words."


def verdict(attempts: list[dict], boot_s: float, context_before, context_after) -> dict:
    refused = [a for a in attempts if a["status"] == 503]
    served = [a for a in attempts if a["status"] == 200]
    checks = {
        "engine_recovering": bool(refused) and all(a.get("code") in ("engine_recovering", "runtime_unavailable") for a in refused),
        "retry_after": bool(refused) and all(a.get("retry_after") for a in refused),
        "served_in_2x_boot": bool(served) and served[0]["t"] <= 2 * boot_s,
        "context_kept": context_after is not None and context_after == context_before,
    }
    return {"pass": all(checks.values()), "checks": checks}


def _post(base: str, body: dict, timeout: float):
    req = urllib.request.Request(base + "/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def _context(base: str):
    try:
        with urllib.request.urlopen(base + "/status", timeout=10) as resp:
            status = json.load(resp)
        return (status.get("capabilities") or {}).get("max_context_tokens") or status.get("maximum_context_tokens")
    except Exception:  # noqa: BLE001 - /status may refuse during the restart
        return None


def engine_pid(port: int) -> int:
    """The serve-native child of the process that listens on the port, so that no other engine is touched."""
    listener = subprocess.check_output(["lsof", "-nP", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"], text=True).split()[0]
    for line in subprocess.check_output(["ps", "-axo", "pid=,ppid=,command="], text=True).splitlines():
        pid, ppid, command = line.split(None, 2)
        if ppid == listener and "serve-native" in command:
            return int(pid)
    raise RuntimeError(f"no serve-native child of {listener}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--boot-seconds", type=float, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    before = _context(base)
    stream = {"chunks": 0, "error": None, "done": False}
    first_chunk = threading.Event()

    def read_stream():
        try:
            with _post(base, {"model": args.model, "max_tokens": 4096, "stream": True, "frequency_penalty": 0,
                              "messages": [{"role": "user", "content": LONG}]}, 600) as resp:
                for raw in resp:
                    if raw.startswith(b"data:"):
                        stream["chunks"] += 1
                        first_chunk.set()
                        if b"[DONE]" in raw:
                            stream["done"] = True
                        if b'"error"' in raw:
                            stream["error"] = raw.decode("utf-8", "replace")[:500]
        except Exception as exc:  # noqa: BLE001 - the stream is expected to end with an error
            stream["error"] = stream["error"] or f"{type(exc).__name__}: {exc}"[:500]
        first_chunk.set()

    reader = threading.Thread(target=read_stream)
    reader.start()
    first_chunk.wait(300)
    port = urllib.parse.urlparse(base).port
    pid = engine_pid(port)
    os.kill(pid, signal.SIGKILL)
    t0 = time.time()
    attempts = []
    while time.time() - t0 < 4 * args.boot_seconds + 60:
        rec = {"t": round(time.time() - t0, 1)}
        try:
            with _post(base, {"model": args.model, "max_tokens": 8, "frequency_penalty": 0,
                              "messages": [{"role": "user", "content": "Say ok."}]}, 120) as resp:
                rec["status"] = resp.status
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            rec.update(status=exc.code, retry_after=exc.headers.get("Retry-After"))
            try:
                error = json.loads(raw).get("error") or {}
                rec["code"] = error.get("code") or error.get("type")
            except ValueError:
                rec["code"] = raw[:100]
        except Exception as exc:  # noqa: BLE001 - connection errors count as attempts
            rec.update(status=None, error=f"{type(exc).__name__}: {exc}"[:200])
        attempts.append(rec)
        if rec.get("status") == 200:
            break
        time.sleep(1)
    reader.join(60)
    after = _context(base)
    result = {"killed_pid": pid, "stream": stream, "attempts": attempts, "context_before": before, "context_after": after,
              "boot_seconds": args.boot_seconds, "verdict": verdict(attempts, args.boot_seconds, before, after)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result["verdict"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
