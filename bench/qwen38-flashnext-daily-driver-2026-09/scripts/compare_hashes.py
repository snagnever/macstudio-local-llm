#!/usr/bin/env python3
"""Compara o hash dos tokens de saida (temp 0) entre dois JSONL do cache_probe, por cenario."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ORDER = ("cold", "identical", "append", "middle_mutation", "tool_turn")


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def compare(a: list[dict], b: list[dict]) -> list[dict]:
    ha = {(r["scenario"], r.get("repeat", 1)): r.get("greedy_tokens_hash") for r in a}
    hb = {(r["scenario"], r.get("repeat", 1)): r.get("greedy_tokens_hash") for r in b}
    rows = []
    # Use union of keys to catch missing scenarios
    all_keys = sorted(ha.keys() | hb.keys(), key=lambda k: (ORDER.index(k[0]) if k[0] in ORDER else 99, k[1]))
    for key in all_keys:
        hash_a = ha.get(key)
        hash_b = hb.get(key)
        # Determine same: True only if both hashes are non-empty strings and equal
        # None if either hash is missing/None, or if one is None and the other isn't
        if hash_a is None or hash_b is None:
            same = None
        else:
            same = hash_a == hash_b
        rows.append({"scenario": key[0], "same": same, "hash_a": hash_a, "hash_b": hash_b})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    args = ap.parse_args()
    rows = compare(load(args.a), load(args.b))
    print("| cenário | iguais | hash A | hash B |\n|---|---|---|---|")
    for r in rows:
        if r["same"] is None:
            # Determine if hash is missing on A or B
            if r["hash_a"] is None:
                status = "**ausente em A**"
            elif r["hash_b"] is None:
                status = "**ausente em B**"
            else:
                # Both present but one is None, shouldn't happen but mark as undetermined
                status = "**indeterminado**"
        elif r["same"]:
            status = "sim"
        else:
            status = "**não**"
        print(f"| {r['scenario']} | {status} | `{(r['hash_a'] or '')[:12]}` | `{(r['hash_b'] or '')[:12]}` |")
    # Exit 1 if any row has same not True (False or None)
    return 0 if all(r["same"] is True for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
