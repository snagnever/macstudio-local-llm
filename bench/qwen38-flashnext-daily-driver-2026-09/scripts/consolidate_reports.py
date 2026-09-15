#!/usr/bin/env python3
"""Consolidate the flashnext-daily-driver campaign JSONL files into results/reports.json.

The JSON feeds the two reports built in the style of the dense campaign:
render_overview.py (campaign dashboard) and render_perf_lines.py (lines by
context). The numbers come only from results/*.jsonl; the glossary, profile
and verdict text lives in the constants of this file.

    python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/consolidate_reports.py
    python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_overview.py
    python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_perf_lines.py
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import summarize_driver as sd  # noqa: E402

CAMPAIGN = Path(__file__).resolve().parents[1]
RESULTS = CAMPAIGN / "results"
OUT = RESULTS / "reports.json"

SCENARIOS = ("cold", "identical", "append", "middle_mutation", "tool_turn")
WARM = sd.WARM
FILE_RE = re.compile(r"^([cu]\d)-(\d+)-t([\d.]+)(?:-(.+))?\.jsonl$")

# Stage and mode by file suffix. "canonical" = vendor profile (counts toward the
# verdict); "diag" = control outside the ranking.
SUFFIX_STAGE = {
    None: ("A", "canonical", ""),
    "b": ("B", "canonical", ""),
    "yarn2": ("probe", "canonical", "YaRN 2.0 + KV 8-bit"),
    "nomtp": ("diag", "diag", "temp 0 · MTP off"),
    "mem102g": ("diag", "diag", "MTPLX_MEMORY_LIMIT_BYTES=102G"),
    "c": ("C", "canonical", ""),
    "yarn2-c": ("C", "canonical", "YaRN 2.0 + KV 8-bit"),
}
STAGE_RANK = {"B": 3, "C": 3, "A": 2, "0": 2, "probe": 2, "diag": 0}

CANDIDATES = [
    {
        "id": "c1", "name": "ddalcu mixed-4/8 · mlx-serve 26.9.2", "short": "c1 mlx-serve",
        "runtime": "mlx-serve", "runtime_version": "26.9.2",
        "model": "ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit", "revision": "ef5b919",
        "quant": "mixed 4/8-bit", "bpw": 4.85, "disk_gb": 107.3, "port": 11234,
        "cache": "hot cache in RAM 16 GB + disk 100 GB · 64 entries · ssm-checkpoint 16",
        "spec": "native MTP depth 6 + PLD (n-gram) · acceptance 0.50–0.67",
        "ceiling": "512K with follow-up", "state": "pass", "status": "winner",
        "note": "Lowest T_turn in both bands: 11.03 s at 32K and 12.35 s at 128K (3 reps).",
    },
    {
        "id": "c2", "name": "oQ4e · oMLX 0.6.4", "short": "c2 oMLX 0.6.4",
        "runtime": "oMLX", "runtime_version": "0.6.4",
        "model": "Jundot/Qwen3.8-Flash-Next-oQ4e-mtp", "revision": "2615fc0",
        "quant": "oQ4e", "bpw": 5.97, "disk_gb": 132.2, "port": 8000,
        "cache": "paged SSD cache · PLE in mmap (qwen4_ple_ssd_offload)",
        "spec": "checkpoint MTP · acceptance not exposed in telemetry",
        "ceiling": "262K (oMLX has no YaRN)", "state": "control", "status": "dominated",
        "note": "Passes the gates, but c3 runs the same weights faster in every band. Dropped before Stage B.",
    },
    {
        "id": "c3", "name": "oQ4e · oMLX 0.7.0.dev2", "short": "c3 oMLX dev2",
        "runtime": "oMLX", "runtime_version": "0.7.0.dev2",
        "model": "Jundot/Qwen3.8-Flash-Next-oQ4e-mtp", "revision": "2615fc0",
        "quant": "oQ4e", "bpw": 5.97, "disk_gb": 132.2, "port": 8000,
        "cache": "paged SSD cache · PLE in mmap via model_settings.json",
        "spec": "checkpoint MTP · acceptance not exposed in telemetry",
        "ceiling": "262K (oMLX has no YaRN)", "state": "pass", "status": "2nd place",
        "note": "Finalist: T_turn 13.48 s at 32K and 15.03 s at 128K (3 reps), +18% over c1.",
    },
    {
        "id": "c4", "name": "MTPLX Optimized-Speed · MTPLX 2.11.2", "short": "c4 MTPLX",
        "runtime": "MTPLX", "runtime_version": "2.11.2",
        "model": "Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed", "revision": "6bc2f6e",
        "quant": "MTPLX Optimized-Speed", "bpw": 5.43, "disk_gb": 120.2, "port": 8000,
        "cache": "session bank in RAM + SSD session cache on",
        "spec": "native MTP · turbo profile depth 3 · acceptance 0.24–0.46",
        "ceiling": "114,688 tokens (memory plan fit)", "state": "fail", "status": "eliminated",
        "note": "Highest decode at 32K (~70 tok/s), but refuses 128K and 256K with HTTP 507: the memory plan fit is 114,688 tokens.",
    },
    {
        "id": "u1", "name": "Uncensored (abliterated) · mlx-serve 26.9.2", "short": "u1 uncensored",
        "runtime": "mlx-serve", "runtime_version": "26.9.2",
        "model": "ARC4NUM/Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit", "revision": "9ebf999",
        "quant": "mixed 4/8-bit", "bpw": 4.85, "disk_gb": 107.3, "port": 11234,
        "cache": "hot cache in RAM 16 GB + disk 100 GB · 64 entries · ssm-checkpoint 16",
        "spec": "native MTP depth 6 + PLD (n-gram) · acceptance 0.58",
        "ceiling": "same pack as c1 (not re-probed above 128K)", "state": "pass", "status": "alt driver",
        "note": "Abliterated weights (orcarouter), same config.json as c1. Matches c1's T_turn within 1% at 32K and 128K; MTP acceptance 0.58.",
        "chart": False,
    },
]

RIG = [
    {"lab": "Chip", "val": "Apple M4 Max"},
    {"lab": "CPU", "val": "16 cores (12P+4E)"},
    {"lab": "GPU", "val": "40 cores · Metal 4"},
    {"lab": "Unified memory", "val": "128 GB"},
    {"lab": "macOS", "val": "26.6.2 (25G83)"},
    {"lab": "Wired limit", "val": "default (iogpu 0) · no sudo"},
    {"lab": "Ports", "val": "mlx-serve :11234 · oMLX/MTPLX :8000"},
]

SAMPLING = "temperature 1.0 · top_p 0.95 · top_k 20 · reasoning xhigh · max_tokens 4096"

RUNTIME_PROFILES = [
    {"name": "mlx-serve 26.9.2", "tag": "incumbent", "arms": "c1",
     "goal": "Serves Flash-Next with native MTP and a two-tier prefix cache.",
     "how": "MTP depth 6 with PLD; hot cache in RAM plus disk; DeltaNet state checkpoints; YaRN via --config-overrides.",
     "cost": "Pins KV and hot cache as wired memory: runs at 106–108 GB at 128K/256K, no swap."},
    {"name": "oMLX 0.6.4", "tag": "oMLX baseline", "arms": "c2",
     "goal": "MLX server for agents, with a paged cache that spills over to SSD.",
     "how": "Paged SSD cache; oQ4e PLE in mmap via model_settings.json.",
     "cost": "Slower decode and prefill than dev2 on the same weights; no YaRN (262K ceiling)."},
    {"name": "oMLX 0.7.0.dev2", "tag": "dev", "arms": "c3",
     "goal": "Same server with new kernels (prefill announced for M5).",
     "how": "Same cache and PLE config as 0.6.4; only the runtime changes.",
     "cost": "Development build; warm TTFT 2× that of mlx-serve; no YaRN."},
    {"name": "MTPLX 2.11.2", "tag": "MTP in the pack", "arms": "c4",
     "goal": "Maximum decode with MTP built into the quantized checkpoint.",
     "how": "Session bank in RAM + SSD session cache; a memory plan computes the context that fits.",
     "cost": "Refuses prompts above 114,688 tokens (HTTP 507) on the 128 GB machine."},
]

QUANT_PROFILES = [
    {"name": "ddalcu mixed-4/8", "bpw": "4.85", "runtime": "mlx-serve",
     "goal": "Experts in 4-bit and attention in 8-bit, with a 32 GB n-gram table for PLD.",
     "cost": "107 GB on disk; the smallest of the three."},
    {"name": "Jundot oQ4e-mtp", "bpw": "5.97", "runtime": "oMLX",
     "goal": "oMLX oQ quant with an MTP head and PLE that can be offloaded to SSD.",
     "cost": "132 GB on disk; without PLE offload it saturates the 128 GB."},
    {"name": "Youssofal MTPLX Optimized-Speed", "bpw": "5.43", "runtime": "MTPLX",
     "goal": "Pack with native MTP and a 32 GB n-gram sidecar, tuned for decode.",
     "cost": "120 GB on disk; 77.3 GiB of weights limit the context fit."},
]

GATES_GLOSSARY = [
    {"gate": "Cache", "desc": "hit ≥ 0.90 on append and tool_turn at 32K and 128K."},
    {"gate": "Correctness", "desc": "needles at 10/50/90 correct at 32K and 128K; a truncated answer (reasoning > 4096 tokens) does not count as a failure."},
    {"gate": "Memory", "desc": "swap delta ≤ 0.5 GB in every band."},
    {"gate": "Server", "desc": "zero HTTP 4xx/5xx errors or stream errors at 32K and 128K."},
    {"gate": "Wired (warning)", "desc": "a peak above 102 GB raises a warning and does not eliminate: it is the normal operating point of mlx-serve."},
]

TEST_CATALOG = {
    "scenarios": [
        {"key": "cold", "eval": "Full prompt with no cache. Measures the first turn (cold TTFT) and prefill; primes the cache."},
        {"key": "identical", "eval": "Same prompt again. Best synthetic case for reuse."},
        {"key": "append", "eval": "Previous prompt + new suffix. A conversation turn."},
        {"key": "middle_mutation", "eval": "Edit in the middle of the prompt. Expected reuse is ~half; excluded from T_turn."},
        {"key": "tool_turn", "eval": "Previous prompt + tool result. An agent turn; included in T_turn."},
    ],
    "modes": [
        {"key": "canonical", "eval": SAMPLING + ". Counts toward the verdict."},
        {"key": "diag temp 0", "eval": "temperature 0 at 32K. Compares c2 vs c3 answers and MTP on vs off on c4. Outside the ranking."},
        {"key": "diag 102G", "eval": "c4 at 128K with MTPLX_MEMORY_LIMIT_BYTES=102G. Tests whether the larger fit serves the band."},
    ],
    "correctness": [
        {"key": "audit_retrieval", "eval": "Needles at 10%, 50% and 90% of the fixture. Correct = all three in the answer."},
        {"key": "truncated", "eval": "finish_reason=length with 4096 reasoning tokens. Recorded, does not eliminate."},
    ],
    "t_turno": "T_turn = tool_turn TTFT + 512 / median decode of the served warm scenarios "
               "(identical, append, tool_turn). It is the wait for one agent turn with a 512-token reply. "
               "Lower is better.",
    "metrics": ["ttft_ms (TTFT)", "decode_tps (decode)", "prompt_tps (prefill)", "cache_hit_ratio",
                "cached_tokens", "mtp_acceptance", "ram_peak_gb (wired)", "mem_free_min_gb",
                "swap_delta_gb", "finish_reason", "needle_verdicts", "error / error_stage"],
}

QUEUE = [
    {"stage": "Stage 0: smoke test at 8K, 4 candidates", "status": "done"},
    {"stage": "Stage A: 1-rep triage at 32K, 128K and 256K", "status": "done"},
    {"stage": "Diagnostic temp 0 at 32K (c2 vs c3; c4 MTP on vs off)", "status": "done"},
    {"stage": "c4 at 128K with a 102G budget", "status": "done"},
    {"stage": "Stage B: 3 reps at 32K and 128K (c1, c3)", "status": "done"},
    {"stage": "Capacity probe at 512K", "status": "done"},
    {"stage": "Stage C: 3 reps at 256K (c1, c3, c2) and 2 reps at 512K (c1) with tool_turn", "status": "done"},
    {"stage": "Stage U: uncensored u1 at 8K/32K/128K + refusal probe (c1 vs u1)", "status": "done"},
    {"stage": "Daily driver record (c1)", "status": "done"},
]

VERDICTS = [
    {"gate": "Verdict", "arm": "c1 · mlx-serve 26.9.2", "state": "pass",
     "note": "Daily driver. Beats c3 by 18% in both bands; warm TTFT decides it (2.1 vs 4.8 s at 128K)."},
    {"gate": "Finalist", "arm": "c3 · oMLX 0.7.0.dev2", "state": "pass",
     "note": "Passes every gate. Decode ties with c1 (~50 tok/s at 128K); loses on TTFT."},
    {"gate": "Dominated", "arm": "c2 · oMLX 0.6.4", "state": "control",
     "note": "Passes the gates. Same weights as c3, slower in every band: cold at 256K 1187 vs 578 s."},
    {"gate": "Server at 128K", "arm": "c4 · MTPLX 2.11.2", "state": "fail",
     "note": "HTTP 507 at 128K and 256K. With 102G the fit covers 128K, but middle_mutation and tool_turn fail on allocation."},
    {"gate": "Wired > 102 GB", "arm": "c1 @128K / 256K / 512K", "state": "control",
     "note": "Warning, does not eliminate: 104–109 GB, swap 0, minimum free memory 0.01–0.06 GB."},
    {"gate": "MTP lossless", "arm": "c4 · temp 0", "state": "pass",
     "note": "MTP on 5/5 needles and 1.8× decode; MTP off 4/5 (one truncated). No sign of lossy MTP."},
    {"gate": "Uncensored alt", "arm": "u1 · mlx-serve 26.9.2", "state": "pass",
     "note": "Abliterated pack, same config.json as c1. T_turn within 1% at 32K/128K, MTP acceptance 0.58, zero stream failures. Refuses 0/50 legitimate prompts, same as c1 — no over-refusal to fix on this set."},
]

TAKEAWAYS = [
    ["T_turn nearly flat", "c1 goes from 11.0 s at 32K to 12.35 s at 128K, 13.9 s at 256K and 13.6 s at 512K; c3 from 13.5 to 17.7 s; c2 from 17.1 to 27.3 s (3 reps, Stage C at 256K/512K)."],
    ["TTFT decides, not decode", "at 128K c1 and c3 both decode ~50 tok/s; the warm turn responds in 2.1 s on c1 and 4.8 s on c3. At 256K the tool turn is 2.2 s on c1 vs 5.8 s on c3."],
    ["c4 does not serve 128K", "best decode at 32K (~70 tok/s), but MTPLX 2.11.2 refuses anything above 114,688 tokens with HTTP 507."],
    ["dev2 vs 0.6.4 on the same weights", "at 256K, cold 578 vs 1186 s and decode 43.2 vs 24.8 tok/s (3 reps)."],
    ["512K on c1", "T_turn 13.6 s with a tool turn in 3.1 s and hit 1.00 (2 reps, YaRN 2.0 + KV 8-bit); cold 845 s, decode 48.5 tok/s, wired 104 GB, swap 0."],
    ["uncensored matches c1", "u1 (abliterated, same runtime and quant) lands T_turn within 1% of c1 at 32K and 128K, MTP acceptance 0.58, zero stream failures. Both c1 and u1 refuse 0/50 legitimate prompts."],
]

# Per-group caveats (candidate, context, stage) that the number alone does not show.
GROUP_NOTES = {
    ("c4", 8192, "0"): "incoherent cache telemetry: hit 1.00 on cold and a 75 s tool_turn",
    ("c4", 131072, "diag"): "3/5 served: middle_mutation and tool_turn fail on allocation",
    ("c4", 131072, "A"): "refused with HTTP 507: memory plan fit of 114,688 tokens",
    ("c4", 262144, "A"): "refused with HTTP 507: memory plan fit of 114,688 tokens",
    ("c1", 524288, "probe"): "probe: only cold and identical; warm decode = identical; cold decode 42.6 tok/s",
}

DELTAS = [
    {"label": "c1 vs c3 · 128K", "a": ["c1", 131072, "canonical"], "b": ["c3", 131072, "canonical"]},
    {"label": "c1 vs c3 · 32K", "a": ["c1", 32768, "canonical"], "b": ["c3", 32768, "canonical"]},
    {"label": "dev2 vs 0.6.4 · 256K", "a": ["c3", 262144, "canonical"], "b": ["c2", 262144, "canonical"]},
    {"label": "MTP on vs off · c4 32K t0", "a": ["c4", 32768, "diag:temp 0"], "b": ["c4", 32768, "diag:temp 0 · MTP off"]},
]


def _median(xs: list) -> float | None:
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def _round(v: float | None, digits: int) -> float | None:
    return None if v is None else round(v, digits)


def stage_for(ctx: int, temperature: str, suffix: str | None) -> tuple[str, str, str]:
    if temperature not in ("1.0", "1"):
        return ("diag", "diag", "temp 0" if suffix is None else SUFFIX_STAGE.get(suffix, ("", "", suffix))[2])
    stage, mode, tag = SUFFIX_STAGE.get(suffix, ("diag", "diag", suffix or ""))
    if stage == "A" and ctx == 8192:
        stage = "0"
    return stage, mode, tag


def build_group(path: Path, records: list[dict]) -> dict:
    m = FILE_RE.match(path.name)
    if not m:
        raise ValueError(f"file name does not match the expected pattern: {path.name}")
    cand, ctx, temperature, suffix = m.group(1), int(m.group(2)), m.group(3), m.group(4)
    stage, mode, tag = stage_for(ctx, temperature, suffix)

    served = [r for r in records if sd._is_served(r)]
    by: dict[str, list[dict]] = {}
    for r in served:
        by.setdefault(r["scenario"], []).append(r)
    ran = sorted({r["scenario"] for r in records}, key=SCENARIOS.index)

    ttft = {s: _round(_median([r["ttft_ms"] / 1000 for r in by.get(s, [])]), 2) for s in SCENARIOS}
    hit = {s: _round(_median([r.get("cache_hit_ratio") for r in by.get(s, [])]), 3) for s in SCENARIOS}
    warm_decode = [r["decode_tps"] for s in WARM for r in by.get(s, []) if r.get("decode_tps")]
    decode_raw = _median(warm_decode)
    tool_ttft_raw = _median([r["ttft_ms"] / 1000 for r in by.get("tool_turn", [])])
    t_turno = (round(tool_ttft_raw + 512 / decode_raw, 2)
               if tool_ttft_raw is not None and decode_raw else None)

    truncated = sum(1 for r in records if not r.get("correct") and r.get("finish_reason") == "length")
    correct = sum(1 for r in records if r.get("correct"))
    errors = [r for r in records if not sd._is_served(r)]
    http = sorted({str(r.get("error") or "").split(":")[0] for r in errors if r.get("error")})
    refused = bool(errors) and not served
    # One file = one group (arm, context); summarize_driver applies gates and warnings.
    summary = next(iter(sd.summarize(records).values()))
    reps = max((sum(1 for r in records if r["scenario"] == s) for s in ran), default=0)

    return {
        "cand": cand, "context": ctx, "stage": stage, "mode": mode, "tag": tag,
        "file": path.name, "reps": reps, "n": len(records), "served_n": len(served),
        "scenarios_run": ran,
        "scenarios_served": sorted(by, key=SCENARIOS.index),
        "t_turno_s": t_turno,
        "cold_ttft_s": ttft["cold"], "ttft_s": ttft, "hit": hit,
        "decode_tps": _round(decode_raw, 1),
        "decode_range": [round(min(warm_decode), 1), round(max(warm_decode), 1)] if warm_decode else None,
        "prefill_tps": _round(_median([r.get("prompt_tps") for r in by.get("cold", [])]), 0),
        "wired_peak_gb": _round(max((r.get("ram_peak_gb") or 0) for r in records) or None, 1),
        "mem_free_min_gb": _round(min((r.get("mem_free_min_gb") for r in records
                                       if r.get("mem_free_min_gb") is not None), default=None), 2),
        "swap_delta_gb": _round(max((r.get("swap_delta_gb") or 0) for r in records), 2),
        "mtp_acceptance": _round(_median([r.get("mtp_acceptance") for r in served]), 2),
        "correct": correct, "truncated": truncated, "failed": len(records) - correct - truncated,
        "refused": refused, "error_kinds": [h for h in http if h and h != "finish_reason"],
        "stream_failures": sum(1 for r in errors if r.get("finish_reason") == "error"),
        "gates_failed": summary["gates_failed"] if mode == "canonical" else [],
        "warnings": summary["warnings"],
        "note": GROUP_NOTES.get((cand, ctx, stage), ""),
        "canonical": False,
    }


def mark_canonical(groups: list[dict]) -> None:
    best: dict[tuple, dict] = {}
    for g in groups:
        if g["mode"] != "canonical":
            continue
        key = (g["cand"], g["context"])
        if key not in best or STAGE_RANK[g["stage"]] > STAGE_RANK[best[key]["stage"]]:
            best[key] = g
    for g in best.values():
        g["canonical"] = True


REFUSAL_CATEGORIES = ["security", "medical", "harm_reduction", "fiction", "control"]
STAGE_U_BANDS = [8192, 32768, 131072]


def _refusal_summary(path: Path) -> dict | None:
    """Read a refusal-<arm>.jsonl into per-category counts, or None if absent."""
    if not path.exists():
        return None
    cats = {c: {"n": 0, "refused": 0, "no_answer": 0} for c in REFUSAL_CATEGORIES}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        c = cats.setdefault(r["category"], {"n": 0, "refused": 0, "no_answer": 0})
        c["n"] += 1
        c["refused"] += int(bool(r.get("refused")))
        c["no_answer"] += int(bool(r.get("no_answer")))
    total = {
        "n": sum(c["n"] for c in cats.values()),
        "refused": sum(c["refused"] for c in cats.values()),
        "no_answer": sum(c["no_answer"] for c in cats.values()),
    }
    return {"by_category": cats, "total": total}


def build_stage_u(groups: list[dict], results_dir: Path) -> dict:
    """Head-to-head of the uncensored variant u1 against its reference c1:
    responsiveness per band and the refusal-probe counts."""
    canon = {(g["cand"], g["context"]): g for g in groups if g["canonical"]}

    def cell(cand: str, ctx: int) -> dict | None:
        g = canon.get((cand, ctx))
        if g is None:
            return None
        return {"t_turno": g["t_turno_s"], "ttft_tool": g["ttft_s"]["tool_turn"],
                "decode": g["decode_tps"], "mtp": g["mtp_acceptance"],
                "hit_tool": g["hit"]["tool_turn"], "reps": g["reps"]}

    bands = []
    for ctx in STAGE_U_BANDS:
        c1, u1 = cell("c1", ctx), cell("u1", ctx)
        if c1 or u1:
            bands.append({"context": ctx, "c1": c1, "u1": u1})
    return {
        "bands": bands,
        "refusal": {"c1": _refusal_summary(results_dir / "refusal-c1.jsonl"),
                    "u1": _refusal_summary(results_dir / "refusal-u1.jsonl"),
                    "categories": REFUSAL_CATEGORIES},
        "note": ("u1 is the abliterated pack on the same runtime and quant as c1 "
                 "(identical config.json). The refusal probe scores 40 legitimate prompts "
                 "in four categories that aligned models often over-refuse, plus 10 neutral "
                 "controls; it stores only the verdict and 200 characters per answer."),
    }


def build(results_dir: Path) -> dict:
    groups = []
    for path in sorted(list(results_dir.glob("c*-*-t*.jsonl")) + list(results_dir.glob("u*-*-t*.jsonl"))):
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if records:
            groups.append(build_group(path, records))
    mark_canonical(groups)
    groups.sort(key=lambda g: (g["cand"], g["context"], -STAGE_RANK[g["stage"]], g["file"]))
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "campaign": "bench/qwen38-flashnext-daily-driver-2026-09",
        "rig": RIG, "sampling": SAMPLING,
        "candidates": CANDIDATES, "groups": groups,
        "runtime_profiles": RUNTIME_PROFILES, "quant_profiles": QUANT_PROFILES,
        "gates_glossary": GATES_GLOSSARY, "test_catalog": TEST_CATALOG,
        "queue": QUEUE, "verdicts": VERDICTS, "takeaways": TAKEAWAYS, "deltas": DELTAS,
        "stage_u": build_stage_u(groups, results_dir),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-dir", default=str(RESULTS))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    data = build(Path(a.results_dir))
    out = Path(a.out)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(data['groups'])} groups)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
