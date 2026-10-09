#!/usr/bin/env python3
"""Compara dois braços item a item (HumanEval ou tool-calling): totais, delta e itens discordantes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(paths, key: str, field: str) -> dict:
    out = {}
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if key in r and field in r:
                out[r[key]] = bool(r[field])  # a última ocorrência vence (re-run com --only)
    return out


def compare(a: dict, b: dict) -> dict:
    keys = sorted(a.keys() & b.keys(), key=str)
    return {
        "n": len(keys),
        "pass_a": sum(a[k] for k in keys),
        "pass_b": sum(b[k] for k in keys),
        "only_a": [k for k in keys if a[k] and not b[k]],
        "only_b": [k for k in keys if b[k] and not a[k]],
        "missing_a": sorted(b.keys() - a.keys(), key=str),
        "missing_b": sorted(a.keys() - b.keys(), key=str),
    }


def markdown(title: str, name_a: str, name_b: str, c: dict) -> str:
    fmt = lambda xs: ", ".join(str(x) for x in xs) or "—"
    return "\n".join([
        f"## {title}",
        "",
        "| braço | passa |",
        "|---|---:|",
        f"| {name_a} | {c['pass_a']}/{c['n']} |",
        f"| {name_b} | {c['pass_b']}/{c['n']} |",
        "",
        f"{name_b} − {name_a}: **{c['pass_b'] - c['pass_a']:+d}**".replace("+0", "0"),
        "",
        f"- só {name_a} passa: {fmt(c['only_a'])}",
        f"- só {name_b} passa: {fmt(c['only_b'])}",
        f"- faltam em {name_a}: {fmt(c['missing_a'])}; faltam em {name_b}: {fmt(c['missing_b'])}",
        "",
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--name-a", required=True)
    ap.add_argument("--name-b", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--field", required=True)
    ap.add_argument("--a", nargs="+", required=True, type=Path)
    ap.add_argument("--b", nargs="+", required=True, type=Path)
    x = ap.parse_args(argv)
    c = compare(load(x.a, x.key, x.field), load(x.b, x.key, x.field))
    print(markdown(x.title, x.name_a, x.name_b, c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
