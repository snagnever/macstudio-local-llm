"""Faithful jdhodges-shaped OOM reproducer.

Replicates the jdhodges request shape that is documented to trip Apple Metal's
resource_limit on the unpatched runtime: every request carries the full ~1000
token `tools` array (long prompt) AND each request is a distinct single-turn
conversation (accumulates distinct cached sequences). This is the combination
the plain reproducers miss -- long-prompt-but-few-sequences (spicyneuron) and
many-sequences-but-short-prompts (distinct) both stay clean; only the product
trips it.

Also prints prompt_tokens so we can confirm the server injects the tools array
into the prompt (vs. silently dropping it for a non-tool-calling model).

Pass:  prints "REPRO_CLEAN: all N requests succeeded" and exits 0.
Fail:  any request raises (HTTP 500 / OOM / timeout); prints FAIL, exits 1.
"""
import argparse
import json
import sys
import time
import urllib.request

import yaml

DEFAULT_BASE = "http://127.0.0.1:8765/v1"
DEFAULT_MODEL = "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
DEFAULT_TOOLS = (
    "/Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb/"
    "results/tool_calling/tool_definitions.yaml"
)

PROMPTS = [
    "What's the weather in Paris in Celsius?",
    "Convert 100 USD to EUR.",
    "What time is it in Tokyo right now?",
    "When was Python 3.12 released?",
    "Remind me to call the dentist tomorrow at 9am.",
    "Send a quick email to bob@example.com saying I'll be late.",
    "Create a calendar event for lunch on Friday at noon.",
    "What's on my calendar next week?",
    "Convert 5000 JPY to USD.",
    "What's the weather in Berlin?",
    "Set a reminder to water the plants this evening.",
    "What's the timezone in Sydney?",
    "Email alice@example.com the meeting notes.",
    "Convert 250 GBP to USD.",
    "What's the weather in Reykjavik in Celsius?",
    "Schedule a dentist appointment next Tuesday at 3pm.",
    "What time is it in Los Angeles?",
    "Remind me about the standup at 10am daily.",
    "Convert 1000 EUR to JPY.",
    "What's on my calendar this Thursday?",
    "Email the team about the deadline change.",
    "What's the weather in Cairo?",
    "Set a reminder to submit the report Friday.",
    "What's the timezone difference between NYC and London?",
    "Create an event for the project kickoff Monday 9am.",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--tools-yaml", default=DEFAULT_TOOLS)
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    tools = yaml.safe_load(open(args.tools_yaml))["tools"]
    n = min(args.n, len(PROMPTS))
    for i in range(1, n + 1):
        payload = json.dumps(
            {
                "model": args.model,
                "messages": [{"role": "user", "content": PROMPTS[i - 1]}],
                "tools": tools,
                "max_tokens": args.max_tokens,
                "temperature": 0.0,
            }
        ).encode()
        req = urllib.request.Request(
            f"{args.base_url}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as r:
                d = json.loads(r.read())
            dt = time.time() - t0
            usage = d.get("usage", {})
            ptoks = usage.get("prompt_tokens", "?")
            ctoks = usage.get("completion_tokens", "?")
            print(
                f"{i:2d}/{n}  {dt:6.1f}s  p={ptoks!s:>5} c={ctoks!s:>4}  OK",
                flush=True,
            )
        except Exception as e:
            dt = time.time() - t0
            print(f"{i:2d}/{n}  {dt:6.1f}s  FAIL  {type(e).__name__}: {e}", flush=True)
            sys.exit(1)
    print(f"REPRO_CLEAN: all {n} requests succeeded")


if __name__ == "__main__":
    main()
