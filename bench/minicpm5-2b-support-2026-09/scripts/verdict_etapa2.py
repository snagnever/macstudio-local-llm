#!/usr/bin/env python3
"""Veredito da Etapa 2: penalidade de T_turno do driver por arranjo.

Compara cada arranjo (B/C/D, com modelo de suporte) contra A (driver sozinho) na
mesma banda, aplica os gates da campanha e imprime markdown.

O T_turno usa a mediana crua do TTFT de `tool_turn` e a mediana crua do decode
quente (identical/append/tool_turn): T = ttft_tool + 512 / decode.

usage:
    verdict_etapa2.py --results-dir results [--bands 32768 131072] \
        [--glob "*-{ctx}-t1.0.jsonl"]
"""

from __future__ import annotations

import argparse
import statistics as st
from collections import defaultdict
from pathlib import Path

import json

WARM = ("identical", "append", "tool_turn")
REPLY_TOKENS = 512
GATE_PENALTY_PCT = 15.0
GATE_SWAP_DELTA_GB = 0.5
FREE_WARN_GB = 2.0


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def served(r: dict) -> bool:
    if r.get("finish_reason") not in ("stop", "length"):
        return False
    err = r.get("error")
    return not err or str(err).startswith("finish_reason:length")


def median(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def summarize(records: list[dict]) -> dict:
    by = defaultdict(list)
    for r in records:
        by[r["scenario"]].append(r)
    warm_decode = median([r["decode_tps"] for s in WARM for r in by.get(s, []) if served(r)])
    tool_ttft = median([r["ttft_ms"] / 1000 for r in by.get("tool_turn", []) if served(r)])
    t_turno = round(tool_ttft + REPLY_TOKENS / warm_decode, 2) if tool_ttft and warm_decode else None
    hits = {s: median([r.get("cache_hit_ratio") for r in by.get(s, []) if served(r)]) for s in WARM}
    mtp = median([r.get("mtp_acceptance") for r in records if served(r)])
    wired = max((r.get("ram_peak_gb") or 0) for r in records) or None
    swap = max((r.get("swap_delta_gb") or 0) for r in records)
    free_min = min((r.get("mem_free_min_gb") for r in records if r.get("mem_free_min_gb") is not None),
                   default=None)
    return {
        "t_turno": t_turno,
        "decode": round(warm_decode, 1) if warm_decode else None,
        "tool_ttft": round(tool_ttft, 2) if tool_ttft else None,
        "hits": {s: (round(v, 3) if v is not None else None) for s, v in hits.items()},
        "mtp": round(mtp, 3) if mtp is not None else None,
        "wired": wired, "swap_delta": swap, "free_min": free_min,
        "n": len(records),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", type=Path, default=Path("results"))
    p.add_argument("--bands", nargs="+", type=int, default=[32768, 131072])
    p.add_argument("--arms", nargs="+", default=["A", "B", "C", "D"])
    p.add_argument("--labels", default="A=driver sozinho,B=+s1 OptiQ-4bit,C=+s2 8bit,D=+s3 gemma-e4b")
    args = p.parse_args()
    labels = dict(part.split("=", 1) for part in args.labels.split(","))

    print("# Etapa 2 — penalidade de T_turno do driver sob concorrência\n")
    print("Gate eliminatório: penalidade de T_turno vs A > 15%, ou swap delta > 0.5 GB.")
    print("`free min` e `wired` são avisos, não gates (ver mem-sampler).\n")
    for ctx in args.bands:
        print(f"\n## {ctx // 1024}K\n")
        print("| arranjo | modelo | T_turno s | Δ vs A | decode | tool TTFT | hit id/app/tool | MTP | wired GB | swap Δ | free min GB | gates | avisos |")
        print("|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|")
        base = None
        for arm in args.arms:
            variants = []
            main = args.results_dir / f"{arm}-{ctx}-t1.0.jsonl"
            if main.exists():
                variants.append(("base", main))
            for f in sorted(args.results_dir.glob(f"{arm}-{ctx}-t1.0-gap*.jsonl")):
                variants.append((f.stem.split(f"{ctx}-t1.0-")[-1], f))
            if not variants:
                print(f"| {arm} | {labels.get(arm,'')} | — | — | — | — | — | — | — | — | — | sem dados | — |")
                continue
            for variant, path in variants:
                rows = load(path)
                s = summarize(rows)
                pen = None
                if arm == "A":
                    base = s["t_turno"]
                elif base and s["t_turno"]:
                    pen = (s["t_turno"] - base) / base * 100
                gates = []
                if pen is not None and pen > GATE_PENALTY_PCT:
                    gates.append(f"penalidade>{GATE_PENALTY_PCT:g}%")
                if (s["swap_delta"] or 0) > GATE_SWAP_DELTA_GB:
                    gates.append("swap>0.5")
                # "Pages free" no macOS fica perto de zero mesmo com memoria
                # reclamavel de sobra (inactive), entao free baixo e aviso.
                warnings = []
                if s["free_min"] is not None and s["free_min"] < FREE_WARN_GB:
                    warnings.append("free<2")
                if s["wired"] and s["wired"] > 102:
                    warnings.append("wired>102")
                pen_s = "—" if pen is None else f"{pen:+.1f}%"
                hits = s["hits"]
                h = "/".join("—" if hits[ss] is None else f"{hits[ss]:.2f}" for ss in WARM)
                name = arm if variant == "base" else f"{arm} [{variant}]"
                print(f"| {name} | {labels.get(arm,'')} | {s['t_turno']} | {pen_s} | {s['decode']} | "
                      f"{s['tool_ttft']} | {h} | {s['mtp']} | {s['wired']} | {s['swap_delta']} | "
                      f"{s['free_min']} | {', '.join(gates) or 'passa'} | {', '.join(warnings) or '—'} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())