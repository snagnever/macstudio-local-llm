#!/usr/bin/env python3
"""Count the verdicts of refusal_probe.py per arm and prompt set.

usage: summarize_refusal.py results/refusal-*.jsonl --out-md results/refusal-summary.md
"""
import argparse
import json
import sys
from pathlib import Path

VERDICTS = ("refused", "empty", "complied", "error")


def summarize(paths):
    """{(arm, set): {"refused": n, "empty": n, "complied": n, "error": n, "n": total}}."""
    got = {}
    for path in paths:
        for line in Path(path).read_text().splitlines():
            row = json.loads(line)
            cell = got.setdefault((row["arm"], row["set"]), dict({v: 0 for v in VERDICTS}, n=0))
            cell[row["verdict"]] += 1
            cell["n"] += 1
    return got


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("jsonl", nargs="+", type=Path)
    ap.add_argument("--out-md", type=Path, required=True)
    args = ap.parse_args(argv)
    lines = ["| arm | set | refused | empty | complied | error | n |", "|---|---|---:|---:|---:|---:|---:|"]
    for (arm, set_name), c in sorted(summarize(args.jsonl).items()):
        lines.append(f"| {arm} | {set_name} | {c['refused']} | {c['empty']} | {c['complied']} | {c['error']} | {c['n']} |")
    args.out_md.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
