#!/usr/bin/env python3
"""Summarize one flashnext-concurrency arm: per-stream T_turno, ratio against the solo w1 reference, hit,
needles, overlap between streams, auxiliary calls, memory, gates and a VERDICT line.

Inputs (written by run-parallel-probes.sh and run-candidate.sh):
  <results>/<arm>-<ctx>-<tag>-s<k>.jsonl   cache_probe.py records of stream k
  <results>/<arm>-<ctx>-<tag>-aux.jsonl    aux_load.py records (optional)
  <logs>/<arm>-<ctx>-t<temp>-<tag>-mem.jsonl  mem-sampler.sh samples (optional)
Python 3.9 stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Optional, Union

DRIVER = Path(__file__).resolve().parents[2] / "qwen38-flashnext-daily-driver-2026-09" / "scripts"
sys.path.insert(0, str(DRIVER))
from summarize_driver import _is_http_error, _is_served, _median_raw, t_turno  # noqa: E402

WARM = ("identical", "append", "tool_turn")
RATIO_PASS = 1.5
RATIO_FAIL = 2.0
HIT_MIN = 0.95
STALL_S = 60.0
SWAP_MAX_GB = 0.5
# No free-memory gate: vm_stat "Pages free" drops to ~0.01 GB during every model load (file cache), and the
# 2026-10 solo runs logged 0.01-0.06 GB at 32K-256K. Memory failure shows up as swap, HTTP refusals
# (PrefillDoesNotFit) or a stream that dies; free_min_gb stays in the table for reading.
NEEDLES_256K = 11 / 13  # the solo 256K reference got 11/13
HEADER = ("| braço | contexto | stream | T_turno | razão ÷ w1 | warm TTFT tool | hit app / tool | decode | overlap "
          "| aux p50 / p95 / errs | wired peak | livre mín | swap Δ | HTTP errs | needles |")
ALIGN = "|---|---:|---|---:|---:|---:|---|---:|---|---|---:|---:|---:|---:|---|"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _stream_files(results_dir: Path, arm: str, context: Union[int, str], tag: str) -> list[tuple[int, int, Path]]:
    ctx_pat = r"(\d+)" if context == "all" else f"({int(context)})"
    pat = re.compile(rf"^{re.escape(arm)}-{ctx_pat}-{re.escape(tag)}-s(\d+)\.jsonl$")
    found = []
    for path in results_dir.iterdir():
        m = pat.match(path.name)
        if m:
            found.append((int(m.group(2)), int(m.group(1)), path))
    return sorted(found)


def _overlaps(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _ttft_s(r: dict[str, Any]) -> float:
    """Client-measured TTFT (includes queue wait) when the record has it, else the record's ttft_ms."""
    ms = r.get("client_ttft_ms")
    return (ms if ms is not None else r.get("ttft_ms") or 0.0) / 1000


def _wall(r: dict[str, Any]) -> Optional[tuple[float, float]]:
    """Decode window [first token, end]. Queue wait and prefill are left out, so a request that waited for
    another stream's request to finish never overlaps it."""
    ws, we = r.get("wall_first_token"), r.get("wall_end")
    if ws is None:
        ws = r.get("wall_start")
    if isinstance(ws, (int, float)) and isinstance(we, (int, float)):
        return (float(ws), float(we))
    return None


def _overlap_fraction(mine: list[dict[str, Any]], others: list[dict[str, Any]]) -> Optional[float]:
    """Fraction of this stream's served warm records whose wall interval crosses a record of another stream."""
    warm = [w for w in (_wall(r) for r in mine if r.get("scenario") in WARM and _is_served(r)) if w]
    other = [w for w in (_wall(r) for r in others if _is_served(r)) if w]
    if not warm:
        return None
    return sum(1 for w in warm if any(_overlaps(w, o) for o in other)) / len(warm)


def _needles_failed(records: list[dict[str, Any]], arm: str, ctx: int) -> bool:
    # Only answered requests grade a needle; a refused or broken request fails the http-errors gate instead.
    records = [r for r in records if _is_served(r)]
    good = sum(1 for r in records if r.get("correct"))
    n = len(records)
    if arm.endswith("q8"):
        # --kv-quant 8 must not lose a needle: every non-truncated record correct.
        return any(not r.get("correct") and r.get("finish_reason") != "length" for r in records)
    if ctx >= 262144:
        return n == 0 or good / n < NEEDLES_256K - 1e-9
    return any(not r.get("correct") and r.get("finish_reason") != "length" for r in records)


def _ref(ctx: int, refs: dict[int, float]) -> Optional[float]:
    return refs.get(ctx)


def _stream_row(k: int, ctx: int, records: list[dict[str, Any]], others: list[dict[str, Any]],
                arm: str, refs: dict[int, float]) -> dict[str, Any]:
    served = [r for r in records if _is_served(r)]
    tool = _median_raw([_ttft_s(r) for r in served if r.get("scenario") == "tool_turn"])
    decode = _median_raw([r.get("decode_tps") for r in served if r.get("scenario") in WARM])
    tt = t_turno(tool, decode) if tool is not None and decode else None
    ref = _ref(ctx, refs)
    hit_app = _median_raw([r.get("cache_hit_ratio") for r in served if r.get("scenario") == "append"])
    hit_tool = _median_raw([r.get("cache_hit_ratio") for r in served if r.get("scenario") == "tool_turn"])
    return {
        "stream": f"s{k}", "context": ctx, "t_turno_s": tt,
        "ratio": (tt / ref) if tt is not None and ref else None,
        "warm_ttft_tool_s": tool, "hit_append": hit_app, "hit_tool": hit_tool, "decode_tps": decode,
        "overlap": _overlap_fraction(records, others),
        "needles": f"{sum(1 for r in served if r.get('correct'))}/{len(served)}",
        "needles_failed": _needles_failed(records, arm, ctx),
        "http_errors": sum(1 for r in records if _is_http_error(r.get("error"))
                           and not str(r.get("error")).startswith("finish_reason:")),
        # cold and middle_mutation are prefill-bound by design (solo w1 middle_mutation is 92 s at 128K).
        "stall": any(r.get("scenario") in WARM and _ttft_s(r) > STALL_S for r in records),
        "served_n": len(served), "n": len(records),
    }


def _aux_summary(path: Optional[Path]) -> Optional[dict[str, Any]]:
    if path is None or not path.exists():
        return None
    rows = _read_jsonl(path)
    totals = sorted(r["total_s"] for r in rows if r.get("total_s") is not None)
    p95 = totals[min(len(totals) - 1, int(round(0.95 * (len(totals) - 1))))] if totals else None
    return {
        "n": len(rows),
        "p50": statistics.median(totals) if totals else None,
        "p95": p95,
        "errors": sum(1 for r in rows if r.get("error") or r.get("status") != 200),
        "stall": any((r.get("ttft_s") if r.get("ttft_s") is not None else r.get("total_s") or 0) > STALL_S
                     for r in rows),
    }


def _memory_summary(logs_dir: Path, arm: str, context: Union[int, str], tag: str) -> Optional[dict[str, Any]]:
    if not logs_dir.is_dir():
        return None
    ctx_pat = r"\d+" if context == "all" else str(int(context))
    pat = re.compile(rf"^{re.escape(arm)}-{ctx_pat}-t[\d.]+-{re.escape(tag)}-mem\.jsonl$")
    files = sorted(p for p in logs_dir.iterdir() if pat.match(p.name))
    samples = [s for f in files for s in _read_jsonl(f)]
    if not samples:
        return None
    swaps = [s.get("swap_used_gb", 0.0) for s in samples]
    return {
        "wired_peak_gb": max(s.get("wired_gb", 0.0) for s in samples),
        "free_min_gb": min(s.get("free_gb", 0.0) for s in samples),
        "swap_delta_gb": max(swaps) - swaps[0],
    }


def _is_serialized(arm: str) -> bool:
    """w1c1x2: the serialized control (2 streams on one slot); overlap is expected to be 0 there."""
    return arm.endswith("x2")


def _vs(streams: list[dict[str, Any]], other: list[dict[str, Any]], other_arm: str) -> Optional[dict[str, Any]]:
    """Compare this arm with another arm of the same band, stream by stream (batch against the queue)."""
    mine = [s["t_turno_s"] for s in streams if s["t_turno_s"] is not None]
    theirs = [s["t_turno_s"] for s in other if s["t_turno_s"] is not None]
    if not mine or not theirs:
        return None
    worst = max(mine) / max(theirs)
    mean = (sum(mine) / len(mine)) / (sum(theirs) / len(theirs))
    return {"arm": other_arm, "worst_ratio": worst, "mean_ratio": mean,
            "batch_beats_queue": worst <= 1.0 and mean <= 1.0}


def summarize(results_dir: Union[str, Path], arm: str, context: Union[int, str], tag: str,
              ref_32k: float = 7.9, ref_128k: float = 8.6, ref_256k: float = 11.1,
              logs_dir: Optional[Union[str, Path]] = None, vs_arm: Optional[str] = None) -> dict[str, Any]:
    results_dir = Path(results_dir)
    logs_dir = Path(logs_dir) if logs_dir is not None else results_dir.parent / "logs"
    refs = {32768: ref_32k, 131072: ref_128k, 262144: ref_256k}
    files = _stream_files(results_dir, arm, context, tag)
    data = [(k, ctx, _read_jsonl(path)) for k, ctx, path in files]
    streams = []
    for k, ctx, recs in data:
        others = [r for k2, _, rs in data if k2 != k for r in rs]
        streams.append(_stream_row(k, ctx, recs, others, arm, refs))

    if context == "all":
        aux_files = sorted(results_dir.glob(f"{arm}-*-{tag}-aux.jsonl"))
        aux = _aux_summary(aux_files[0] if aux_files else None)
    else:
        aux = _aux_summary(results_dir / f"{arm}-{int(context)}-{tag}-aux.jsonl")
    memory = _memory_summary(logs_dir, arm, context, tag)

    failed: list[str] = []
    expected = max([int(r.get("concurrency") or 1) for _, _, rs in data for r in rs] or [1])
    if len(streams) < expected:
        failed.append(f"missing streams ({len(streams)}/{expected})")
    if aux is not None and aux["n"] == 0:
        failed.append("aux no data")
    ratios = [s["ratio"] for s in streams if s["ratio"] is not None]
    if not streams or any(s["t_turno_s"] is None for s in streams):
        failed.append("no data")
    if ratios and max(ratios) > RATIO_FAIL:
        failed.append(f"ratio>{RATIO_FAIL}")
    if any((h is not None and h < HIT_MIN) for s in streams for h in (s["hit_append"], s["hit_tool"])):
        failed.append(f"hit<{HIT_MIN}")
    if any(s["needles_failed"] for s in streams):
        failed.append("needles")
    if sum(s["http_errors"] for s in streams) + (aux["errors"] if aux else 0) > 0:
        failed.append("http errors")
    if any(s["stall"] for s in streams) or (aux and aux["stall"]):
        failed.append(f"stall>{int(STALL_S)}s")
    if len(streams) >= 2 and not _is_serialized(arm) and not any((s["overlap"] or 0) > 0 for s in streams):
        failed.append("no overlap")
    if memory and memory["swap_delta_gb"] > SWAP_MAX_GB:
        failed.append(f"swap>{SWAP_MAX_GB}")

    if failed:
        verdict = f"fail ({', '.join(failed)})"
    elif ratios and max(ratios) > RATIO_PASS:
        verdict = "pass-with-warning"
    else:
        verdict = "pass"
    vs = None
    if vs_arm:
        vs = _vs(streams, summarize(results_dir, vs_arm, context, tag, ref_32k, ref_128k, ref_256k,
                                    logs_dir)["streams"], vs_arm)
    return {"arm": arm, "context": context, "tag": tag, "streams": streams, "aux": aux, "memory": memory,
            "gates_failed": failed, "verdict": verdict, "vs": vs}


def _f(x: Optional[float], fmt: str = "{:.1f}") -> str:
    return "—" if x is None else fmt.format(x)


def markdown(summary: dict[str, Any]) -> str:
    aux, mem = summary["aux"], summary["memory"] or {}
    aux_cell = "—" if not aux else f"{_f(aux['p50'])} / {_f(aux['p95'])} / {aux['errors']}"
    lines = [HEADER, ALIGN]
    for s in summary["streams"]:
        lines.append("| " + " | ".join([
            summary["arm"], str(s["context"]), s["stream"], _f(s["t_turno_s"]), _f(s["ratio"], "{:.2f}"),
            _f(s["warm_ttft_tool_s"]), f"{_f(s['hit_append'], '{:.3f}')} / {_f(s['hit_tool'], '{:.3f}')}",
            _f(s["decode_tps"]), _f(s["overlap"], "{:.2f}"), aux_cell,
            _f(mem.get("wired_peak_gb")), _f(mem.get("free_min_gb"), "{:.2f}"), _f(mem.get("swap_delta_gb"), "{:.2f}"),
            str(s["http_errors"]), s["needles"],
        ]) + " |")
    lines.append("")
    lines.append(f"gates failed: {', '.join(summary['gates_failed']) or 'none'}")
    vs = summary.get("vs")
    if vs:
        lines.append(f"vs {vs['arm']}: worst stream {vs['worst_ratio']:.2f}x, mean {vs['mean_ratio']:.2f}x, "
                     f"batch beats queue: {'yes' if vs['batch_beats_queue'] else 'no'}")
    lines.append(f"VERDICT: {summary['verdict']}")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--results-dir", required=True, type=Path)
    p.add_argument("--logs-dir", type=Path)
    p.add_argument("--arm", required=True)
    p.add_argument("--context", required=True, help="context size, or 'all' for asymmetric arms")
    p.add_argument("--tag", required=True)
    p.add_argument("--ref-32k", type=float, default=7.9)
    p.add_argument("--ref-128k", type=float, default=8.6)
    p.add_argument("--ref-256k", type=float, default=11.1)
    p.add_argument("--vs", help="compare with another arm of the same band and tag (e.g. w1c1x2)")
    p.add_argument("--markdown", action="store_true")
    a = p.parse_args(argv)
    context: Union[int, str] = "all" if a.context == "all" else int(a.context)
    s = summarize(a.results_dir, a.arm, context, a.tag, a.ref_32k, a.ref_128k, a.ref_256k, a.logs_dir, a.vs)
    print(markdown(s) if a.markdown else json.dumps(s, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
