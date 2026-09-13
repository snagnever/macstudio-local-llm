#!/usr/bin/env python3
"""Consolida os JSONL da campanha flashnext-daily-driver: medianas, T_turno, gates."""
import argparse, glob, json, statistics
from pathlib import Path

WARM = ("identical", "append", "tool_turn")
GATE_CTX = (32768, 131072)


def t_turno(ttft_tool_turn_s: float, decode_tps: float, reply_tokens: int = 512) -> float:
    return round(ttft_tool_turn_s + reply_tokens / decode_tps, 1)


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def summarize(records: list[dict]) -> dict:
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        groups.setdefault((r["arm"], int(r["context_target"])), []).append(r)
    out = {}
    for key, rs in groups.items():
        by = {}
        for r in rs:
            by.setdefault(r["scenario"], []).append(r)
        warm_ttft = {s: _median([r["ttft_ms"] / 1000 for r in by.get(s, [])]) for s in WARM}
        hit = {s: _median([r.get("cache_hit_ratio") for r in by.get(s, [])]) for s in WARM}
        warm_decode = [r["decode_tps"] for s in WARM for r in by.get(s, [])]
        decode = _median(warm_decode) or _median([r["decode_tps"] for r in rs])
        fins = [r.get("finish_reason") for r in rs]
        if all(r.get("correct") for r in rs):
            correctness = "ok"
        elif all(r.get("correct") or f == "length" for r, f in zip(rs, fins)):
            correctness = "truncado"
        else:
            correctness = "falha"
        row = {
            "cold_ttft_s": _median([r["ttft_ms"] / 1000 for r in by.get("cold", [])]),
            "warm_ttft_s": warm_ttft, "hit": hit,
            "prefill_tps": _median([r.get("prompt_tps") for r in by.get("cold", [])]),
            "decode_tps": decode,
            "t_turno_s": t_turno(warm_ttft["tool_turn"], decode) if warm_ttft["tool_turn"] is not None and decode else None,
            "correctness": correctness,
            "wired_peak_gb": max((r.get("ram_peak_gb") or 0) for r in rs) or None,
            "swap_delta_gb": max((r.get("swap_delta_gb") or 0) for r in rs),
            "mtp_acceptance": _median([r.get("mtp_acceptance") for r in rs]),
            "errors": sum(1 for r in rs if r.get("error")),
            "n": len(rs),
        }
        row["gates_failed"] = apply_gates(row, key[1])
        out[key] = row
    return out


def apply_gates(row: dict, ctx: int) -> list[str]:
    failed = []
    if ctx in GATE_CTX:
        for s in ("append", "tool_turn"):
            h = row["hit"].get(s)
            if h is not None and h < 0.90:
                failed.append(f"hit_{s}<0.90")
        if row["correctness"] == "falha":
            failed.append("needle")
    if row.get("wired_peak_gb") and row["wired_peak_gb"] > 102:
        failed.append("wired>102")
    if row.get("swap_delta_gb", 0) > 0.5:
        failed.append("swap>0.5")
    if row.get("errors", 0) and ctx in GATE_CTX:
        failed.append("http_errors")
    return failed


def markdown(summary: dict) -> str:
    lines = []
    for ctx in sorted({k[1] for k in summary}):
        lines.append(f"\n### {ctx // 1024}K\n\n| cand | T_turno s | cold TTFT s | warm TTFT id/app/tool s | hit id/app/tool | prefill | decode | MTP acc | correção | wired GB | swap Δ | gates |")
        lines.append("|---|---:|---:|---|---|---:|---:|---:|---|---:|---:|---|")
        for (cand, c), r in sorted(summary.items()):
            if c != ctx:
                continue
            w = r["warm_ttft_s"]; h = r["hit"]
            f = lambda d: "/".join("—" if d[s] is None else f"{d[s]:.2f}" if d[s] < 10 else f"{d[s]:.0f}" for s in WARM)
            lines.append(f"| {cand} | {r['t_turno_s']} | {r['cold_ttft_s']} | {f(w)} | {f(h)} | {r['prefill_tps']} | {r['decode_tps']} | {r['mtp_acceptance']} | {r['correctness']} | {r['wired_peak_gb']} | {r['swap_delta_gb']} | {', '.join(r['gates_failed']) or 'passa'} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="bench/qwen38-flashnext-daily-driver-2026-09/results")
    ap.add_argument("--glob", default="c*-*-t1.0*.jsonl")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    records = []
    for f in sorted(glob.glob(str(Path(a.results_dir) / a.glob))):
        records += [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
    summary = summarize(records)
    out = Path(a.out or Path(a.results_dir) / "summary.json")
    out.write_text(json.dumps({f"{k[0]}@{k[1]}": v for k, v in summary.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
