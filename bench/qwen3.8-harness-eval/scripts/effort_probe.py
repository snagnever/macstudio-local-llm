#!/usr/bin/env python3
"""Probe which reasoning_effort values a runtime honours.

Sends the same prompt once per effort level to /v1/chat/completions and reports
the reasoning tokens each one produced. The runtime does not have to validate
the string: an invalid value is part of the matrix on purpose, to show whether
a typo silently becomes a default-effort run.

Usage:
  python3 effort_probe.py --url http://mac-studio:11234/v1/chat/completions \
      --model <model-id> --prompt-file <file> [--max-tokens 16000] [--json out.json]
"""
import argparse
import json
import sys
import time
import urllib.request

EFFORTS = ["none", "minimal", "low", "medium", "high", "xhigh", "bogus"]


def probe(url, model, prompt, effort, max_tokens, timeout):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "reasoning_effort": effort,
        "temperature": 1.0,
        "top_p": 0.95,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    started = time.time()
    try:
        d = json.load(urllib.request.urlopen(req, timeout=timeout))
    except Exception as exc:  # noqa: BLE001 - the error is the result here
        return {"effort": effort, "error": f"{type(exc).__name__}: {exc}"}
    usage = d.get("usage", {})
    timings = d.get("timings", {})
    message = d["choices"][0]["message"]
    thinking = message.get("reasoning_content") or message.get("reasoning") or ""
    return {
        "effort": effort,
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
        "reasoning_chars": len(thinking),
        "decode_tps": timings.get("predicted_per_second"),
        "wall_s": round(time.time() - started, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt-file")
    ap.add_argument("--prompt")
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--efforts", default=",".join(EFFORTS))
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    if args.prompt_file:
        prompt = open(args.prompt_file).read()
    elif args.prompt:
        prompt = args.prompt
    else:
        ap.error("pass --prompt or --prompt-file")

    rows = []
    for effort in args.efforts.split(","):
        row = probe(args.url, args.model, prompt, effort, args.max_tokens, args.timeout)
        rows.append(row)
        print(json.dumps(row), flush=True)

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump({"url": args.url, "model": args.model, "max_tokens": args.max_tokens,
                       "prompt": prompt, "rows": rows}, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
