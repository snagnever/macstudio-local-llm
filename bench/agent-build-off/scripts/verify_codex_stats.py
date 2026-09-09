#!/usr/bin/env python3
"""Cross-check a Codex arm's self-reported token totals against its rollout logs.

Usage: verify_codex_stats.py <cwd-to-match> <rollout.jsonl> [...]
Prints the totals the logs support. Stdlib only.
"""
import json, sys, collections

def main(argv):
    want_cwd, files = argv[1], argv[2:]
    sessions, tool_calls, prompts = [], collections.Counter(), 0
    first_ts = last_ts = None
    model = None
    totals = collections.Counter()
    for path in files:
        last_tc = None
        matched = False
        with open(path) as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                p = rec.get("payload") or {}
                if rec.get("type") == "session_meta":
                    if p.get("cwd") != want_cwd:
                        break
                    matched = True
                    sessions.append({"id": p.get("session_id"),
                                     "cli_version": p.get("cli_version"),
                                     "started": rec.get("timestamp")})
                if not matched:
                    continue
                ts = rec.get("timestamp")
                if ts:
                    first_ts = ts if first_ts is None or ts < first_ts else first_ts
                    last_ts = ts if last_ts is None or ts > last_ts else last_ts
                if p.get("type") == "token_count":
                    last_tc = p.get("info", {}).get("total_token_usage")
                if p.get("type") in ("custom_tool_call", "function_call"):
                    tool_calls[p.get("name") or p.get("type")] += 1
                if rec.get("type") == "response_item" and p.get("role") == "user":
                    prompts += 1
                m = p.get("model") or (p.get("info") or {}).get("model")
                if m:
                    model = m
        if last_tc:
            # Codex reports cumulative totals per session; sum across sessions.
            for k, v in last_tc.items():
                totals[k] += v
    print(json.dumps({
        "sessions": sessions, "session_count": len(sessions),
        "model": model, "first_timestamp": first_ts, "last_timestamp": last_ts,
        "tokens": dict(totals), "user_prompts": prompts,
        "tool_calls_by_type": dict(tool_calls),
        "tool_calls_total": sum(tool_calls.values()),
    }, indent=2))

if __name__ == "__main__":
    main(sys.argv)
