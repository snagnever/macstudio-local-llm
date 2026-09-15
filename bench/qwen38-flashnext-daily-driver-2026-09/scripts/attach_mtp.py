#!/usr/bin/env python3
"""Anexa a aceitacao MTP (do log [spec-stats] do mlx-serve) aos registros do resultado."""
from __future__ import annotations

import argparse, json, re
from pathlib import Path

SPEC_STATS_RE = re.compile(r"^.*\[spec-stats\].*$", re.MULTILINE)
MODE_RE = re.compile(r"\bmode=(\S+)")
PER_DRAFT_PCT_RE = re.compile(r"\bper_draft_pct=([\d.]+)%")
AVG_PER_ROUND_RE = re.compile(r"\bavg_per_round=([\d.]+)")
DEPTH_RE = re.compile(r"\bdepth=(\d+)")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def parse_spec_stats(log_text: str) -> dict | None:
    lines = SPEC_STATS_RE.findall(log_text)
    if not lines:
        return None
    last = lines[-1]
    mode_m = MODE_RE.search(last)
    pct_m = PER_DRAFT_PCT_RE.search(last)
    avg_m = AVG_PER_ROUND_RE.search(last)
    depth_m = DEPTH_RE.search(last)
    return {
        "mtp_acceptance": round(float(pct_m.group(1)) / 100.0, 4) if pct_m else None,
        "mtp_avg_per_round": float(avg_m.group(1)) if avg_m else None,
        "mtp_depth": int(depth_m.group(1)) if depth_m else None,
        "mtp_mode": mode_m.group(1) if mode_m else None,
    }


def attach_mtp(records: list[dict], stats: dict | None) -> list[dict]:
    if stats is None:
        return records
    for r in records:
        if r.get("mtp_acceptance") is None:
            r["mtp_acceptance"] = stats["mtp_acceptance"]
        r["mtp_avg_per_round"] = stats["mtp_avg_per_round"]
        r["mtp_depth"] = stats["mtp_depth"]
        r["mtp_mode"] = stats["mtp_mode"]
    return records


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, type=Path)
    ap.add_argument("--log", required=True, type=Path)
    a = ap.parse_args()
    records = load_jsonl(a.results)
    log_text = a.log.read_text(encoding="utf-8") if a.log.exists() else ""
    stats = parse_spec_stats(log_text)
    records = attach_mtp(records, stats)
    a.results.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    if stats is None:
        print(f"{a.results}: no [spec-stats] in log")
    else:
        print(f"{a.results}: mtp_acceptance={stats['mtp_acceptance']} depth={stats['mtp_depth']} (run-level)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
