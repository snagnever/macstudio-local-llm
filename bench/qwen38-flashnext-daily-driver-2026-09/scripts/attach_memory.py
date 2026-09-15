#!/usr/bin/env python3
"""Anexa pico de memoria wired e delta de swap (sampler) aos registros do cache_probe."""
import argparse, json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def attach_memory(records: list[dict], samples: list[dict]) -> list[dict]:
    if not samples:
        return records
    wired = [s["wired_gb"] for s in samples]
    free = [s["free_gb"] for s in samples]
    swap_delta = round(samples[-1]["swap_used_gb"] - samples[0]["swap_used_gb"], 2)
    for r in records:
        r["ram_peak_gb"] = max(wired)
        r["swap_delta_gb"] = swap_delta
        r["mem_free_min_gb"] = min(free)
        r["mem_samples"] = len(samples)
    return records


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, type=Path)
    ap.add_argument("--sampler", required=True, type=Path)
    a = ap.parse_args()
    records = attach_memory(load_jsonl(a.results), load_jsonl(a.sampler) if a.sampler.exists() else [])
    a.results.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    print(f"{a.results}: {len(records)} registros, pico wired {records[0].get('ram_peak_gb') if records else None} GB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
