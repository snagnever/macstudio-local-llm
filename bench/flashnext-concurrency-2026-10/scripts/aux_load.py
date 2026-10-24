#!/usr/bin/env python3
"""Auxiliary load generator: short calls like the ones a Claude Code session makes beside its main turn.

Alternates two kinds every --period seconds while --duration-file exists:
  permission  a bash-command permission classifier (fixed system prompt, varying command)
  title       a session-title generator (fixed system prompt, varying conversation excerpt)
Each call streams, has thinking off and max_tokens 64. One JSON record per call goes to --output:
  {kind, t_start, ttft_s, total_s, status, error}
Python 3.9 stdlib only (the rig's python3).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

KINDS = ("permission", "title")

PERMISSION_SYSTEM = (
    "You are a security classifier for a coding agent. You receive one shell command that the agent "
    "wants to run inside the user's repository, plus the recent conversation. Decide if the command is "
    "safe to run without asking the user. Unsafe means: it deletes or overwrites files outside the "
    "working tree, sends data to the network, changes system settings, installs software, or uses "
    "credentials. Reply with one JSON object and nothing else: "
    '{"decision": "allow" | "ask", "reason": "<at most 12 words>"}.'
)
TITLE_SYSTEM = (
    "You write titles for coding sessions. You receive the first user message and the first assistant "
    "reply of a session. Write a title of three to six words in sentence case that names the task, not "
    "the tools. No quotes, no trailing period, no emoji. Reply with the title only."
)
COMMANDS = (
    "uv run --no-project --with pytest python -m pytest tests/test_cli.py -q",
    "git diff --stat HEAD~1 -- src/",
    "sed -n 1,80p src/report/render.py",
    "rm -rf build/ dist/ && python -m build",
    "curl -s https://example.invalid/api/v1/status",
    "grep -rn 'def parse_args' src/ | head -20",
)
EXCERPT = (
    "User: the nightly export job writes duplicate rows when the upstream API retries a page. Find where "
    "the pager keeps its cursor, make the write idempotent, and add a test that replays the same page twice. "
    "Keep the public CLI flags unchanged.\n"
    "Assistant: I read src/export/pager.py and src/export/writer.py. The pager advances the cursor only "
    "after the writer returns, so a retried page is written twice. I will key each row by (page_id, row_id), "
    "skip keys already written in this run, and add tests/test_writer_replay.py with a fake API that "
    "returns the same page on the first retry. The CLI keeps --since, --until and --out as they are."
)


def build_request(kind: str, model: str = "MODEL_ID", index: int = 0) -> dict[str, Any]:
    if kind == "permission":
        command = COMMANDS[index % len(COMMANDS)]
        messages = [
            {"role": "system", "content": PERMISSION_SYSTEM},
            {"role": "user", "content": f"Recent conversation:\n{EXCERPT}\n\nCommand #{index}: {command}"},
        ]
    elif kind == "title":
        messages = [
            {"role": "system", "content": TITLE_SYSTEM},
            {"role": "user", "content": f"Session #{index}.\n{EXCERPT}"},
        ]
    else:
        raise ValueError(f"unknown kind: {kind}")
    return {
        "model": model,
        "messages": messages,
        "max_tokens": 64,
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "chat_template_kwargs": {"enable_thinking": False},
    }


def record(kind: str, t_start: float, ttft_s: Optional[float], total_s: float,
           status: int, error: Optional[str]) -> dict[str, Any]:
    return {"kind": kind, "t_start": t_start, "ttft_s": ttft_s, "total_s": total_s,
            "status": status, "error": error}


def send(base_url: str, request: dict[str, Any], timeout: float = 300.0):
    """POST one streaming chat request. Returns (ttft_s, total_s, status, error)."""
    url = base_url.rstrip("/") + "/chat/completions"
    data = json.dumps(request).encode()
    req = urllib.request.Request(url, data=data, headers={"content-type": "application/json"})
    t0 = time.time()
    ttft = None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                body = line[5:].strip()
                if body == "[DONE]":
                    break
                if ttft is None:
                    try:
                        chunk = json.loads(body)
                    except ValueError:
                        continue
                    if chunk.get("error"):
                        return ttft, time.time() - t0, status, f"stream_error:{chunk['error']}"
                    choices = chunk.get("choices") or []
                    delta = (choices[0].get("delta") or {}) if choices else {}
                    if delta.get("content") or delta.get("reasoning_content"):
                        ttft = time.time() - t0
        return ttft, time.time() - t0, status, None
    except urllib.error.HTTPError as exc:
        return ttft, time.time() - t0, exc.code, f"http_{exc.code}"
    except (urllib.error.URLError, OSError) as exc:
        return ttft, time.time() - t0, 0, f"connection:{exc}"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--period", type=float, default=20.0)
    parser.add_argument("--duration-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    index = 0
    while args.duration_file.exists():
        kind = KINDS[index % len(KINDS)]
        t_start = time.time()
        ttft, total, status, error = send(args.base_url, build_request(kind, args.model, index))
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record(kind, t_start, ttft, total, status, error)) + "\n")
        index += 1
        while args.duration_file.exists() and time.time() < t_start + args.period:
            time.sleep(min(1.0, max(0.0, t_start + args.period - time.time())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
