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
    for key in sorted(ha.keys() & hb.keys(), key=lambda k: (ORDER.index(k[0]) if k[0] in ORDER else 99, k[1])):
        rows.append({"scenario": key[0], "same": ha[key] == hb[key], "hash_a": ha[key], "hash_b": hb[key]})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    args = ap.parse_args()
    rows = compare(load(args.a), load(args.b))
    print("| cenário | iguais | hash A | hash B |\n|---|---|---|---|")
    for r in rows:
        print(f"| {r['scenario']} | {'sim' if r['same'] else '**não**'} | `{(r['hash_a'] or '')[:12]}` | `{(r['hash_b'] or '')[:12]}` |")
    return 0 if all(r["same"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
