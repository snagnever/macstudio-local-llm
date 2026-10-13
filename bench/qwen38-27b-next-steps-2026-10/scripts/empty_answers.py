#!/usr/bin/env python3
"""Count empty final answers (finish_reason stop with no visible content) in campaign JSONL files.

Handles three record shapes: think_turn_probe (content_chars), bench2 / if_probe (raw_response,
content_preview) and tool_call_bench (raw_message.content). Any other record is not empty.
usage: empty_answers.py [--json] [--fail-on-any] FILE...
"""
import argparse, json, sys
from pathlib import Path


def is_empty(rec: dict) -> bool:
    if rec.get("finish_reason") != "stop":
        return False
    if "content_chars" in rec:
        return rec["content_chars"] == 0
    if "raw_response" in rec:
        return not (rec.get("raw_response") or "").strip()
    if "content_preview" in rec:
        return not (rec.get("content_preview") or "").strip()
    if isinstance(rec.get("raw_message"), dict):
        return not (rec["raw_message"].get("content") or "").strip()
    return False


def count(files) -> tuple[int, int]:
    empty = stops = 0
    for f in files:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("finish_reason") == "stop":
                stops += 1
                empty += is_empty(rec)
    return empty, stops


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-any", action="store_true")
    a = ap.parse_args(argv)
    empty, stops = count(a.files)
    if a.json:
        print(json.dumps({"empty": empty, "stop_records": stops}))
    else:
        print(f"empty={empty} of {stops} stop records")
    return 1 if (a.fail_on_any and empty) else 0


if __name__ == "__main__":
    sys.exit(main())
