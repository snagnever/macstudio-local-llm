#!/usr/bin/env python3
"""Summarize support-load JSONL output.

Groups turns by measured prompt-token bucket (to separate 1K / 8K runs that
share one file) and prints medians for TTFT, decode, and total. Also reports
errors and the memory/swap snapshot if an .mem.json from the sampler is given.

Usage:
    summarize_support.py results/etapa1-s1-solo.jsonl [--bucket 1000]
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from collections import defaultdict
from pathlib import Path


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def median(values):
    values = [v for v in values if v is not None]
    return st.median(values) if values else None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("results", type=Path)
    p.add_argument("--bucket", type=int, default=1000,
                   help="token bucket size for grouping prompts")
    args = p.parse_args()

    rows = load(args.results)
    errors = [r for r in rows if not r.get("ok")]
    good = [r for r in rows if r.get("ok")]

    print(f"file: {args.results}")
    print(f"turns: {len(rows)}  ok: {len(good)}  errors: {len(errors)}")
    for err in errors[:5]:
        print(f"  error turn {err.get('turn')}: {err.get('error')}")

    buckets: dict[int, list[dict]] = defaultdict(list)
    for r in good:
        pt = r.get("prompt_tokens")
        key = int(pt // args.bucket * args.bucket) if pt else -1
        buckets[key].append(r)

    for key in sorted(buckets):
        v = buckets[key]
        label = f"prompt~{key}-{key + args.bucket}" if key >= 0 else "prompt unknown"
        ttft = median([x.get("ttft_s") for x in v])
        dec = median([x.get("decode_tps") for x in v])
        tot = median([x.get("total_s") for x in v])
        ct = median([x.get("completion_tokens") for x in v])
        print(f"{label}: n={len(v)}")
        print(f"  ttft_med={ttft:.3f}s  decode_med={dec:.1f} tok/s"
              f"  total_med={tot:.3f}s  completion_med={ct:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())