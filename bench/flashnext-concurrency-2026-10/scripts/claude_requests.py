#!/usr/bin/env python3
"""Per-request records of a Claude Code session against a local server.

One record per request, the same schema whatever the source (today the Splash server log; the campaign-B proxy
writes the same records):
    {"t_start_s": float, "ttft_s": float, "t_end_s": float, "input_tokens": int, "cached_tokens": int,
     "output_tokens": int, "tps": float, "status": int, "stream": str | None}
t_start_s and t_end_s are seconds on one common origin (the first request of the log). A warm request has
cached_tokens > 0; the first prompt of a session has cached_tokens == 0.

    python3 claude_requests.py --splash-log LOG --out OUT.jsonl

Python 3.9 stdlib only (the rig's python3).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

STARTED = re.compile(r"^(\d\d:\d\d:\d\d) Started · input ([\d,]+) · cached ([\d,]+)")
DONE = re.compile(r"^(\d\d:\d\d:\d\d) Done · input ([\d,]+) · cached ([\d,]+)(?: · deduplicated [\d,]+)?"
                  r" · output ([\d,]+) .*? TTFT ([\d.]+)s · ([\d.]+) tok/s")


def _int(s: str) -> int:
    return int(s.replace(",", ""))


def _clock_s(hms: str) -> float:
    h, m, s = (int(x) for x in hms.split(":"))
    return h * 3600 + m * 60 + s


def parse_splash_log(text: str) -> list[dict[str, Any]]:
    """Pair each Done line with the oldest open Started line of the same input size; drop orphans."""
    reqs: list[dict[str, Any]] = []
    open_: list[tuple[float, int, int]] = []
    origin: Optional[float] = None
    last_clock: Optional[float] = None
    day_offset = 0.0

    def rel(hms: str) -> float:
        nonlocal origin, last_clock, day_offset
        clock = _clock_s(hms)
        if last_clock is not None and clock < last_clock:
            day_offset += 86400.0
        last_clock = clock
        t = clock + day_offset
        if origin is None:
            origin = t
        return t - origin

    for line in text.splitlines():
        m = STARTED.match(line)
        if m:
            open_.append((rel(m[1]), _int(m[2]), _int(m[3])))
            continue
        m = DONE.match(line)
        if not m:
            continue
        inp = _int(m[2])
        idx = next((i for i, o in enumerate(open_) if o[1] == inp), None)
        if idx is None:
            continue
        t_start, _, cached = open_.pop(idx)
        reqs.append({"t_start_s": t_start, "ttft_s": float(m[5]), "t_end_s": rel(m[1]), "input_tokens": inp,
                     "cached_tokens": cached, "output_tokens": _int(m[4]), "tps": float(m[6]), "status": 200,
                     "stream": None})
    return reqs


def max_concurrent(reqs: list[dict[str, Any]]) -> int:
    """Largest number of requests open at once; an end and a start at the same instant count the end first."""
    events = sorted([(r["t_start_s"], 1) for r in reqs] + [(r["t_end_s"], -1) for r in reqs])
    cur = peak = 0
    for _, d in events:
        cur += d
        peak = max(peak, cur)
    return peak


def _p90(xs: list[float]) -> float:
    return sorted(xs)[int(0.9 * (len(xs) - 1))]


PREFILL_NEW_TOKENS = 2000  # above this many new tokens a request is a prefill turn (a session start), not a warm turn
PREFILL_TTFT_S = 5.0  # without a cached_tokens field (mlx-serve) a request is a prefill turn when its TTFT is this long


def _new_tokens(r: dict[str, Any]) -> Optional[int]:
    return None if r.get("cached_tokens") is None else r["input_tokens"] - r["cached_tokens"]


def is_prefill(r: dict[str, Any]) -> bool:
    """A cold prompt or one with a big new block (the second session of a pair starts with the shared system
    prompt cached but a new task prompt). Without a cached_tokens field, a long TTFT is the only sign."""
    new = _new_tokens(r)
    if new is None:
        return r.get("ttft_s") is not None and r["ttft_s"] > PREFILL_TTFT_S
    return r["cached_tokens"] == 0 or new > PREFILL_NEW_TOKENS


def summarize_requests(reqs: list[dict[str, Any]]) -> dict[str, Any]:
    """Warm = cached prompt and few new tokens. Records without a ttft_s (no content delta: HTTP error, aborted
    stream) are neither warm nor cold samples; errors counts the records whose status is not 200."""
    samples = [r for r in reqs if r.get("ttft_s") is not None]
    warm = [r for r in samples if not is_prefill(r)]
    cold = [r["ttft_s"] for r in samples if is_prefill(r)]
    warm_summary = None
    if warm:
        ttfts = [r["ttft_s"] for r in warm]
        tps = [r["tps"] for r in warm if r.get("tps") is not None]
        warm_summary = {"n": len(warm), "ttft_p50": statistics.median(ttfts), "ttft_p90": _p90(ttfts),
                        "tps_p50": statistics.median(tps) if tps else None, "tps_min": min(tps) if tps else None,
                        "tps_max": max(tps) if tps else None}
    new_tokens = [n for n in (_new_tokens(r) for r in reqs) if n is not None]
    return {"n": len(reqs), "max_concurrent": max_concurrent(reqs), "prefill_turns": len(cold),
            "first_prompt_ttft_s": statistics.median(cold) if cold else None,
            "new_tokens_p50": statistics.median(new_tokens) if new_tokens else None,
            "warm": warm_summary, "errors": sum(1 for r in reqs if r.get("status", 200) != 200)}


def read_requests(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Extract per-request records from a Splash server log.")
    p.add_argument("--splash-log", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    reqs = parse_splash_log(Path(args.splash_log).read_text(encoding="utf-8", errors="replace"))
    Path(args.out).write_text("".join(json.dumps(r) + "\n" for r in reqs), encoding="utf-8")
    print(f"{args.out}: {len(reqs)} requests, max concurrent {max_concurrent(reqs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
