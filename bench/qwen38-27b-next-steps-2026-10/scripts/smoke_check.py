#!/usr/bin/env python3
"""8K smoke check of a speculative-decoding arm: fail fast before a full phase.

Passes when the JSONL has records, every record has reasoning_chars > 0, the boot log has a
`[spec-stats] mode=<x>` line with the expected mode, and the median decode_tps is at least --min-decode.
Prints one reason line; exit 0 = pass, 1 = fail.
usage: smoke_check.py --jsonl F --boot-log F --mode dflash|mtp --min-decode N
"""
import argparse, json, re, statistics, sys
from pathlib import Path


def check(jsonl: Path, boot_log: Path, mode: str, min_decode: float) -> tuple[bool, str]:
    recs = []
    if jsonl.is_file():
        recs = [json.loads(l) for l in jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not recs:
        return False, f"no records in {jsonl.name}"
    empty = sum(1 for r in recs if not r.get("reasoning_chars"))
    if empty:
        return False, f"reasoning_chars == 0 in {empty}/{len(recs)} records"
    if not boot_log.is_file():
        return False, f"boot log missing: {boot_log.name}"
    modes = re.findall(r"\[spec-stats\] mode=(\S+)", boot_log.read_text(encoding="utf-8", errors="replace"))
    if not modes:
        return False, "no [spec-stats] mode= line in the boot log"
    if mode not in modes:
        return False, f"spec-stats mode {modes[-1]}, expected {mode}"
    decodes = [r["decode_tps"] for r in recs if isinstance(r.get("decode_tps"), (int, float))]
    if not decodes:
        return False, "no decode_tps in the records"
    med = statistics.median(decodes)
    if med < min_decode:
        return False, f"median decode {med:.1f} tok/s below {min_decode:g}"
    return True, f"ok: mode {mode}, median decode {med:.1f} tok/s, {len(recs)} records"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", required=True, type=Path)
    ap.add_argument("--boot-log", required=True, type=Path)
    ap.add_argument("--mode", required=True)
    ap.add_argument("--min-decode", required=True, type=float)
    a = ap.parse_args(argv)
    ok, msg = check(a.jsonl, a.boot_log, a.mode, a.min_decode)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
