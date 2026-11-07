#!/usr/bin/env python3
"""Summarize serving_load.py runs: a table per round, the decode verdict and the stall gate of the campaign plan.

usage: summarize_load.py <run.jsonl> [...]   Prints Markdown, then "verdict=... stall=..." for each run.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def verdict(ratio: float) -> str:
    if ratio >= 0.85:
        return "estavel"
    return "degradado" if ratio >= 0.50 else "queda"


def stall(requests: list[dict]) -> str:
    """G4 of Splash 1.6.0 on the client's chunk gaps: largest <= 10 s, p99 <= 5 s, and every request answered."""
    if any(r.get("status") != 200 or r.get("error") for r in requests):
        return "fail"
    gaps = sorted(g for r in requests for g in r.get("gaps_s") or [])
    if not gaps:
        return "pass"
    p99 = gaps[min(len(gaps) - 1, int(0.99 * len(gaps)))]
    return "pass" if gaps[-1] <= 10 and p99 <= 5 else "fail"


def _median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def _fmt(value, digits=1):
    return "—" if value is None else f"{value:.{digits}f}"


def _probe(records, label):
    return _median(r.get("decode_tok_s") for r in records if r["kind"] == "probe" and r["label"] == label)


def summarize(path: Path) -> str:
    records = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    requests = [r for r in records if r["kind"] == "request"]
    status = [r for r in records if r["kind"] == "status"]
    lines = [f"### {path.name}", "",
             "| rodada | requests | erros | prompt | cached | TTFT mediano s | decode mediano | última lane | maior gap s | sonda curta |",
             "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for rnd in sorted({r["round"] for r in requests}):
        row = [r for r in requests if r["round"] == rnd]
        decode = [r["decode_tok_s"] for r in row if r.get("decode_tok_s")]
        gaps = [r["max_gap_s"] for r in row if r.get("max_gap_s") is not None]
        lines.append(f"| {rnd} | {len(row)} | {sum(1 for r in row if r.get('status') != 200 or r.get('error'))} "
                     f"| {_fmt(_median(r.get('prompt_tokens') for r in row), 0)} "
                     f"| {_fmt(_median(r.get('cached_tokens') for r in row), 0)} "
                     f"| {_fmt(_median(r.get('ttft_s') for r in row))} | {_fmt(_median(decode))} "
                     f"| {_fmt(max(decode) if decode else None)} | {_fmt(max(gaps) if gaps else None, 2)} "
                     f"| {_fmt(_probe(records, f'round{rnd}'))} |")
    pre, end, idle = _probe(records, "pre"), _probe(records, "fim"), _probe(records, "ocioso")
    lines += ["", f"Sonda curta (tok/s): pre {_fmt(pre)}, fim {_fmt(end)}, ocioso {_fmt(idle)}."]
    if status:
        kv, gov, state, disk = (status[-1].get(k) or {} for k in ("kv", "memory_governor", "state", "disk"))
        lines.append(f"`/status` final: schema {status[-1].get('schema_version')}, "
                     f"pages_cache {kv.get('pages_cache')}, pages_free {kv.get('pages_free')}, "
                     f"allocated_bytes {kv.get('allocated_bytes')}, pages_moved {kv.get('pages_moved')}, "
                     f"denied_reservations {gov.get('denied_reservations')}, state_bytes {state.get('bytes')}, "
                     f"disk_used {disk.get('used_bytes')}.")
    if pre and end:
        lines.append(f"verdict={verdict(end / pre)} ratio={end / pre:.2f}")
    else:
        lines.append("verdict=sem_sonda")
    lines.append(f"stall={stall(requests)}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for name in sys.argv[1:]:
        print(summarize(Path(name)))
