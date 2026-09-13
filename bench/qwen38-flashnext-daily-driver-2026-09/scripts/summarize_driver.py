#!/usr/bin/env python3
"""Consolida os JSONL da campanha flashnext-daily-driver: medianas, T_turno, gates."""
from __future__ import annotations

import argparse, glob, json, statistics, sys
from pathlib import Path

WARM = ("identical", "append", "tool_turn")
GATE_CTX = (32768, 131072)
WIRED_WARN_GB = 102


def t_turno(ttft_tool_turn_s: float, decode_tps: float, reply_tokens: int = 512) -> float:
    return round(ttft_tool_turn_s + reply_tokens / decode_tps, 1)


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def _median_raw(xs):
    """Like _median but without rounding — gate comparisons and t_turno must
    use this, never the display-rounded value (rounding a 0.86 hit to 0.9
    would let it pass a >=0.90 gate that should have failed; rounding the
    decode median before dividing 512 by it skews T_turno)."""
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def _is_http_error(error) -> bool:
    """cache_probe writes `"error": "finish_reason:length"` on truncated
    records — that is a correctness/truncation signal (already captured by
    `correctness`), not an HTTP/transport error, so it must not count here.
    An in-stream error (`"stream_error:..."`) IS a real error and must count
    (it doesn't start with the finish_reason:length marker, so it already
    falls through to `True` here without any special-casing)."""
    return bool(error) and not str(error).startswith("finish_reason:length")


def _is_served(record: dict) -> bool:
    """A record counts toward timing/speed medians only if the request
    actually completed: `finish_reason` in {"stop","length"} AND (`error`
    is null/empty OR it is the finish_reason:length truncation marker).

    HTTP refusals, connection errors, and in-stream errors (finish_reason
    "error"/None with error="stream_error:...") fail this: their `ttft_ms`
    is a time-to-failure and their decode/prefill is 0.0, so leaving them
    in would quietly drag every median toward the failure's shape (e.g. a
    256K band that only ever got refused showing a "cold_ttft_s" of 0.2s
    instead of no data at all)."""
    finish_reason = record.get("finish_reason")
    if finish_reason not in ("stop", "length"):
        return False
    error = record.get("error")
    return not error or str(error).startswith("finish_reason:length")


def summarize(records: list[dict]) -> dict:
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        groups.setdefault((r["arm"], int(r["context_target"])), []).append(r)
    out = {}
    for key, rs in groups.items():
        session_ids = sorted({r.get("session_id") for r in rs if r.get("session_id") is not None})
        if len(session_ids) > 1:
            print(
                f"summarize_driver: aviso: {key[0]}@{key[1]} mistura session_id "
                f"{session_ids} (execucoes diferentes no mesmo grupo)",
                file=sys.stderr,
            )
        by = {}
        served_by = {}
        for r in rs:
            by.setdefault(r["scenario"], []).append(r)
            if _is_served(r):
                served_by.setdefault(r["scenario"], []).append(r)
        served = [r for r in rs if _is_served(r)]

        warm_ttft = {s: _median([r["ttft_ms"] / 1000 for r in served_by.get(s, [])]) for s in WARM}
        hit_raw = {s: _median_raw([r.get("cache_hit_ratio") for r in served_by.get(s, [])]) for s in WARM}
        hit = {s: (round(v, 3) if v is not None else None) for s, v in hit_raw.items()}
        warm_decode_records = [r["decode_tps"] for s in WARM for r in served_by.get(s, [])]
        warm_decode_raw = _median_raw(warm_decode_records)
        decode = _median(warm_decode_records)
        mtp_raw = _median_raw([r.get("mtp_acceptance") for r in served])
        mtp_acceptance = round(mtp_raw, 3) if mtp_raw is not None else None
        fins = [r.get("finish_reason") for r in rs]
        if all(r.get("correct") for r in rs):
            correctness = "ok"
        elif all(r.get("correct") or f == "length" for r, f in zip(rs, fins)):
            correctness = "truncado"
        else:
            correctness = "falha"

        # T_turno must come from the RAW (unrounded) tool_turn TTFT median and
        # the RAW warm-decode median, rounding only once at the very end —
        # rounding either input first before dividing 512 by it skews the
        # result. No fallback to "decode over all records" when there is no
        # served warm decode or no served tool_turn: t_turno_s is just None.
        tool_turn_ttft_raw = _median_raw([r["ttft_ms"] / 1000 for r in served_by.get("tool_turn", [])])
        t_turno_s = (
            t_turno(tool_turn_ttft_raw, warm_decode_raw)
            if tool_turn_ttft_raw is not None and warm_decode_raw
            else None
        )

        row = {
            "cold_ttft_s": _median([r["ttft_ms"] / 1000 for r in served_by.get("cold", [])]),
            "warm_ttft_s": warm_ttft, "hit": hit,
            "prefill_tps": _median([r.get("prompt_tps") for r in served_by.get("cold", [])]),
            "decode_tps": decode,
            "t_turno_s": t_turno_s,
            "correctness": correctness,
            "wired_peak_gb": max((r.get("ram_peak_gb") or 0) for r in rs) or None,
            "swap_delta_gb": max((r.get("swap_delta_gb") or 0) for r in rs),
            "mtp_acceptance": mtp_acceptance,
            "errors": sum(1 for r in rs if _is_http_error(r.get("error"))),
            "n": len(rs),
        }
        gate_row = dict(row)
        gate_row["hit"] = hit_raw
        gate_row["served_n"] = len(served)
        row["gates_failed"] = apply_gates(gate_row, key[1])
        row["warnings"] = apply_warnings(gate_row, key[1])
        out[key] = row
    return out


def apply_gates(row: dict, ctx: int) -> list[str]:
    """Failing one of these eliminates the candidate. Wired memory above
    WIRED_WARN_GB is NOT here — mlx-serve's normal operating point (KV +
    a 16 GB prefix cache pinned in wired) can sit above it with no swap
    growth and correct output, so it is a warning (see apply_warnings),
    not an elimination criterion."""
    failed = []
    if ctx in GATE_CTX:
        for s in ("append", "tool_turn"):
            h = row["hit"].get(s)
            if h is not None and h < 0.90:
                failed.append(f"hit_{s}<0.90")
        if row["correctness"] == "falha":
            failed.append("needle")
    if row.get("swap_delta_gb", 0) > 0.5:
        failed.append("swap>0.5")
    if row.get("errors", 0) and ctx in GATE_CTX:
        failed.append("http_errors")
    return failed


def apply_warnings(row: dict, ctx: int) -> list[str]:
    """Non-eliminating flags. `wired_peak_gb` here is the raw (unrounded)
    value already stored on the row — never re-derive it from a rounded
    display figure. `served_n == 0` means every record in the group failed
    (refusal/connection/stream error): every timing/speed median is None,
    so flag it instead of leaving a silently empty-looking row."""
    warnings = []
    if row.get("wired_peak_gb") and row["wired_peak_gb"] > WIRED_WARN_GB:
        warnings.append("wired>102")
    if not row.get("served_n"):
        warnings.append("sem_dados")
    return warnings


def markdown(summary: dict) -> str:
    lines = []
    for ctx in sorted({k[1] for k in summary}):
        lines.append(f"\n### {ctx // 1024}K\n\n| cand | T_turno s | cold TTFT s | warm TTFT id/app/tool s | hit id/app/tool | prefill | decode | MTP acc | correção | wired GB | swap Δ | gates | alertas |")
        lines.append("|---|---:|---:|---|---|---:|---:|---:|---|---:|---:|---|---|")
        for (cand, c), r in sorted(summary.items()):
            if c != ctx:
                continue
            w = r["warm_ttft_s"]; h = r["hit"]
            f = lambda d: "/".join("—" if d[s] is None else f"{d[s]:.2f}" if d[s] < 10 else f"{d[s]:.0f}" for s in WARM)
            lines.append(f"| {cand} | {r['t_turno_s']} | {r['cold_ttft_s']} | {f(w)} | {f(h)} | {r['prefill_tps']} | {r['decode_tps']} | {r['mtp_acceptance']} | {r['correctness']} | {r['wired_peak_gb']} | {r['swap_delta_gb']} | {', '.join(r['gates_failed']) or 'passa'} | {', '.join(r.get('warnings') or []) or '—'} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="bench/qwen38-flashnext-daily-driver-2026-09/results")
    ap.add_argument(
        "--glob",
        default="c*-*-t1.0.jsonl",
        help="Glob relativo a --results-dir. Default = Etapa A apenas "
             "('c*-*-t1.0.jsonl'). Etapa B usa 'c*-*-t1.0-b.jsonl'; a sonda "
             "512K e os diagnosticos t0 tem os proprios sufixos e ficam de "
             "fora por padrao — passe --glob explicitamente para incluir.",
    )
    ap.add_argument(
        "--out",
        default=None,
        help="Se omitido, so imprime o markdown (nao escreve summary.json). "
             "Passe explicitamente para gravar o JSON consolidado.",
    )
    a = ap.parse_args(argv)
    records = []
    for f in sorted(glob.glob(str(Path(a.results_dir) / a.glob))):
        records += [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
    summary = summarize(records)
    if a.out:
        out = Path(a.out)
        out.write_text(json.dumps({f"{k[0]}@{k[1]}": v for k, v in summary.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
