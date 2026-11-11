#!/usr/bin/env python3
"""Memory-claim wait per server boot, from JSONL files of Splash /status samples.

A record is {"t", "status": {...}} (the queue's curl loop and run-parallel-probes.sh), {"kind": "status", ...}
(serving_load.py) or a bare /status object. A boot ends where the claim_wait sample counter drops; the last
record of each boot gives its totals, because the /status counters grow over the life of a server.

    python3 summarize_claims.py STATUS.jsonl [...] [--out-md P]

Python 3.9 stdlib only (the rig's python3).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence


def _status(rec: dict[str, Any]) -> dict[str, Any]:
    if isinstance(rec.get("status"), dict):
        return rec["status"]
    return rec


def _claim(st: dict[str, Any]) -> Optional[dict[str, Any]]:
    return ((st.get("metrics") or {}).get("ttft_parts_ms") or {}).get("claim_wait")


def _row(path: Path, boot: int, st: dict[str, Any]) -> dict[str, Any]:
    cw = _claim(st)
    gap = ((st.get("metrics") or {}).get("decode_gap_causes") or {}).get("prefill_unit") or {}
    return {
        "file": path.name, "boot": boot,
        "claim_wait_max_s": None if cw is None else round(cw.get("max", 0) / 1000, 1),
        "claim_wait_total_s": None if cw is None else round(cw.get("total", 0) / 1000, 1),
        "prefill_unit_gaps": gap.get("gaps") if gap else None,
        "prefill_unit_s": round(gap["ms"] / 1000, 1) if gap and "ms" in gap else None,
        "pages_cache": (st.get("kv") or {}).get("pages_cache"),
    }


def summarize(paths: Sequence[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        boot, last, prev_samples = 1, None, None
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            st = _status(json.loads(line))
            cw = _claim(st)
            samples = None if cw is None else cw.get("samples", 0)
            if last is not None and samples is not None and prev_samples is not None and samples < prev_samples:
                rows.append(_row(path, boot, last))
                boot += 1
            last, prev_samples = st, samples
        if last is not None:
            rows.append(_row(path, boot, last))
    return rows


def _cell(v: Any) -> str:
    return "–" if v is None else str(v)


def to_markdown(rows: Sequence[dict[str, Any]]) -> str:
    head = ("| arquivo | boot | `claim_wait` máximo (s) | `claim_wait` total (s) | gaps `prefill_unit` | "
            "`prefill_unit` (s) | `pages_cache` |\n|---|---:|---:|---:|---:|---:|---:|\n")
    keys = ("claim_wait_max_s", "claim_wait_total_s", "prefill_unit_gaps", "prefill_unit_s", "pages_cache")
    return head + "".join(f"| {r['file']} | {r['boot']} | " + " | ".join(_cell(r[k]) for k in keys) + " |\n"
                          for r in rows)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--out-md", type=Path)
    args = ap.parse_args(argv)
    md = to_markdown(summarize(args.paths))
    if args.out_md:
        args.out_md.write_text(md, encoding="utf-8")
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
