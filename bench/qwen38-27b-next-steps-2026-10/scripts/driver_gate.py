#!/usr/bin/env python3
"""Write P5_GO=<arm> (or 0) into gates.env: the fastest 27B arm whose T_turno is within --ratio of the
Flash-Next driver on both bands, computed from this campaign's medium-effort files (*-p?m.jsonl).
usage: driver_gate.py --results-dir DIR --w1 T32 T128 --ratio 1.25 [--skip-gates-arms k27,l27] --out gates.env
--skip-gates-arms: arms whose runtime may not report cached_tokens; their hit_append/hit_tool_turn gates
are ignored when deciding eligibility (every other gate still applies).
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "bench/qwen38-flashnext-daily-driver-2026-09/scripts"))
from summarize_driver import summarize  # noqa: E402


def load_records(files: list[Path]) -> list[dict]:
    records = []
    for f in files:
        records += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return records


HIT_GATES = ("hit_append", "hit_tool_turn")


def _failed(row: dict, arm: str, skip_hit_arms: set[str]) -> list[str]:
    gates = row.get("gates_failed") or []
    if arm in skip_hit_arms:
        gates = [g for g in gates if g.split("<", 1)[0] not in HIT_GATES]
    return gates


def pick(summary: dict, w1: tuple[float, float], ratio: float,
         skip_hit_arms: set[str] = frozenset()) -> tuple[str, float] | None:
    best = None
    for (arm, ctx), row in summary.items():
        if ctx != 32768 or not row.get("t_turno_s"):
            continue
        hi = summary.get((arm, 131072))
        if not hi or not hi.get("t_turno_s") or _failed(row, arm, skip_hit_arms) or _failed(hi, arm, skip_hit_arms):
            continue
        if row["t_turno_s"] <= ratio * w1[0] and hi["t_turno_s"] <= ratio * w1[1]:
            if best is None or hi["t_turno_s"] < best[1]:
                best = (arm, hi["t_turno_s"])
    return best


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--w1", type=float, nargs=2, required=True)
    ap.add_argument("--ratio", type=float, default=1.25)
    ap.add_argument("--skip-gates-arms", default="", help="comma list of arms whose hit gates are ignored")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    files = sorted(a.results_dir.glob("*-p?m.jsonl"))
    summary = summarize(load_records(files)) if files else {}
    best = pick(summary, tuple(a.w1), a.ratio, set(filter(None, a.skip_gates_arms.split(","))))
    lines = [l for l in (a.out.read_text().splitlines() if a.out.exists() else []) if not l.startswith("P5_GO=")]
    lines.append(f"P5_GO={best[0] if best else 0}")
    a.out.write_text("\n".join(lines) + "\n")
    print(lines[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
