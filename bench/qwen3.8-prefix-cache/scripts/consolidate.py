#!/usr/bin/env python3
"""Consolidate canonical campaign results into one overview file.

Reads the raw JSONL and gate files once and writes results/overview.json so
overviews and the dashboard do not rescan everything each time.

Usage:
    python3 bench/qwen3.8-prefix-cache/scripts/consolidate.py
"""

from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


CAMPAIGN = Path(__file__).resolve().parents[1]
RESULTS = CAMPAIGN / "results"
CACHE_PROBE = RESULTS / "cache-probe.jsonl"
# Greedy (temperature=0) diagnostic evidence. Ingested and tagged mode="greedy"
# so the coverage is visible, but it never counts as a decision measurement.
GREEDY_PROBES = (
    RESULTS / "cache-probe-greedy-diagnostic.jsonl",
    RESULTS / "cache-probe-diagnostic-v1.jsonl",
)
TOOL_LOOP = RESULTS / "tool-loop.jsonl"
OVERVIEW = RESULTS / "overview.json"

# One human-readable line per campaign arm. Keep terms identical to the plan.
ARM_META = {
    "A": {"runtime": "mlx-serve", "model": "MLX-Serve 8-bit", "config": "no cache/spec"},
    "B": {"runtime": "mlx-serve", "model": "MLX-Serve 8-bit", "config": "cache"},
    "C": {"runtime": "mlx-serve", "model": "MLX-Serve 8-bit", "config": "cache+MTP auto"},
    "D": {"runtime": "llama.cpp", "model": "GGUF Q4", "config": "no cache"},
    "E": {"runtime": "llama.cpp", "model": "GGUF Q4", "config": "cache"},
    "F": {"runtime": "llama.cpp", "model": "GGUF Q4", "config": "cache+draft-mtp"},
    "G": {"runtime": "llama.cpp", "model": "GGUF Q6", "config": "cache+draft-mtp"},
    "H": {"runtime": "llama.cpp", "model": "GGUF Q8", "config": "cache+draft-mtp"},
    "I": {"runtime": "oMLX", "model": "MLX-Serve 8-bit", "config": "no cache"},
    "J": {"runtime": "oMLX", "model": "AWQ 5bpw", "config": "no cache"},
    "K": {"runtime": "oMLX", "model": "AWQ 5bpw", "config": "cache, no MTP"},
    "L": {"runtime": "oMLX", "model": "AWQ 5bpw", "config": "cache+MTP"},
    "M": {"runtime": "oMLX", "model": "AWQ 5bpw + draft-2B", "config": "cache+MTP+SpecPrefill"},
    "N": {"runtime": "oMLX", "model": "AWQ 5bpw + draft-0.8B", "config": "cache+MTP+SpecPrefill"},
    "O": {"runtime": "oMLX", "model": "AWQ 5bpw", "config": "ANE prefill"},
    "P": {"runtime": "mlx-dspark", "model": "8-bit g64", "config": "baseline, no cache"},
    "Q": {"runtime": "mlx-dspark", "model": "8-bit g64", "config": "baseline, cache"},
    "R": {"runtime": "mlx-dspark", "model": "8-bit + DSpark", "config": "cache + DSpark spec"},
    "S": {"runtime": "mlx-dspark", "model": "8-bit + DFlash2", "config": "cache + DFlash2 spec"},
    "T": {"runtime": "oMLX", "model": "oQ8e 8.6bpw", "config": "cache+MTP"},
    "U": {"runtime": "oMLX", "model": "oQ8e-fp16", "config": "cache+MTP"},
    "V": {"runtime": "MTPLX", "model": "MTPLX Optimized Speed", "config": "Turbo cache+MTP"},
    "Y": {"runtime": "MTPLX", "model": "MTPLX Optimized Quality", "config": "8-bit, Turbo cache+MTP"},
    "Z": {"runtime": "MTPLX", "model": "MTPLX Optimized Quality FP16", "config": "8-bit fp16 aux, Turbo cache+MTP"},
    "W": {"runtime": "oMLX", "model": "oQ4e 4.7bpw", "config": "baseline, no cache"},
    "X": {"runtime": "oMLX", "model": "oQ4e + DFlash2", "config": "DFlash2, no cache"},
}

# Quantização por braço: rótulo curto + bits-por-peso efetivos (aproximados).
QUANT = {
    "A": ("MLX 8-bit", 8.0), "B": ("MLX 8-bit", 8.0), "C": ("MLX 8-bit", 8.0),
    "D": ("GGUF Q4", 4.5), "E": ("GGUF Q4", 4.5), "F": ("GGUF Q4", 4.5),
    "G": ("GGUF Q6", 6.5), "H": ("GGUF Q8", 8.5), "I": ("MLX 8-bit", 8.0),
    "J": ("AWQ 5bpw", 5.0), "K": ("AWQ 5bpw", 5.0), "L": ("AWQ 5bpw", 5.0),
    "M": ("AWQ 5bpw", 5.0), "N": ("AWQ 5bpw", 5.0), "O": ("AWQ 5bpw", 5.0),
    "P": ("MLX 8-bit", 8.0), "Q": ("MLX 8-bit", 8.0), "R": ("MLX 8-bit", 8.0), "S": ("MLX 8-bit", 8.0),
    "T": ("oQ8e 8.6bpw", 8.6), "U": ("oQ8e 8.6bpw", 8.6),
    "V": ("MTPLX 4-bit", 4.5), "Y": ("MTPLX 8-bit", 8.0), "Z": ("MTPLX 8-bit", 8.0),
    "W": ("oQ4e 4.7bpw", 4.7), "X": ("oQ4e 4.7bpw", 4.7),
}

# Descrição curta do que cada braço isola.
ARM_DESC = {
    "A": "mlx-serve 8-bit, cache off — baseline no cache.",
    "B": "mlx-serve 8-bit, cache on — isolates the prefix cache.",
    "C": "mlx-serve 8-bit, cache + MTP auto — vendor default.",
    "D": "llama.cpp GGUF Q4, cache off — GGUF baseline.",
    "E": "llama.cpp GGUF Q4, cache on.",
    "F": "llama.cpp GGUF Q4 + draft-mtp.",
    "G": "llama.cpp GGUF Q6 + draft-mtp.",
    "H": "llama.cpp GGUF Q8 + draft-mtp.",
    "I": "oMLX loading the 8-bit MLX-Serve — loader check (may fail).",
    "J": "oMLX AWQ 5bpw, cache off — AWQ loader smoke.",
    "K": "oMLX AWQ, cache on, no MTP — MTP gate baseline.",
    "L": "oMLX AWQ, cache + MTP — MTP gate candidate.",
    "M": "L + SpecPrefill with draft 2B.",
    "N": "L + SpecPrefill with draft 0.8B.",
    "O": "oMLX AWQ + prefill via ANE.",
    "P": "mlx-dspark 8-bit, cache off — baseline no speculation.",
    "Q": "mlx-dspark 8-bit, cache on — baseline with cache.",
    "R": "mlx-dspark cache + DSpark drafter (speculation in decode, cache preserved).",
    "S": "mlx-dspark cache + DFlash2 drafter (speculation in decode, cache preserved).",
    "T": "oMLX oQ8e 8.6bpw, cache + MTP — M4 production candidate.",
    "U": "oMLX oQ8e-fp16 — oQ8e fp16 control.",
    "V": "MTPLX Optimized Speed (4-bit body) — MVP runtime+checkpoint.",
    "W": "oMLX oQ4e 4.7bpw, cache off — DFlash pair baseline.",
    "X": "oMLX oQ4e + DFlash2 — DFlash2 causal test.",
    "Y": "MTPLX Optimized Quality (8-bit) — fidelity vs Speed.",
    "Z": "MTPLX Optimized Quality FP16 — Quality fp16 control.",
}

# Ordem canônica dos cenários do cache-probe.
SCENARIOS = ("cold", "identical", "append", "middle_mutation", "tool_turn")

# Catálogo estático: o que cada teste avalia (para a aba Testes).
TEST_CATALOG = {
    "scenarios": [
        {"key": "cold", "eval": "New prompt, no prior cache. Measures cold TTFT and prefill."},
        {"key": "identical", "eval": "Same prompt repeated. Measures warm cache hit and warm TTFT."},
        {"key": "append", "eval": "Prompt extended with a suffix. Partial reuse of the prefix."},
        {"key": "middle_mutation", "eval": "Changes a segment in the middle. Cache invalidation from that point."},
        {"key": "tool_turn", "eval": "Appends a tool-style turn to the prompt (cache scenario, not the agentic loop)."},
    ],
    "modes": [
        {"key": "canonical", "eval": "temp=1, vendor sampling. Decision metric (counts for verdict)."},
        {"key": "greedy", "eval": "temp=0, deterministic. Diagnostic and greedy equivalence (token hash). Does not count for verdict."},
    ],
    "correctness": [
        {"key": "code", "eval": "Checksum: the exact computed value must appear in the output (code_result_verdict)."},
        {"key": "audit_retrieval", "eval": "Needles at 3 depths (10/50/90). Correct = all three present and no truncation."},
    ],
    "tool_loop": {
        "eval": "Agentic loop of 20 turns, best-of-N. Passes if it calls the 4 tools "
                "(read_fixture, search_fixture, run_fixture_test, record_result) and emits the 4 "
                "identifiers verbatim in the final turn; majority of the N repetitions.",
    },
    "metrics": [
        "ttft_ms (TTFT)", "decode_tps (decode)", "e2e_ms (total time)", "prompt_tps (prefill)",
        "cache_hit_ratio", "cached_tokens", "accept_length / mtp_acceptance (spec)",
        "ram_peak_gb", "gpu_temp_peak_c",
    ],
}

# Flags de cache/MTP e nota curta por braço, para a matriz de cobertura.
# Explícito (não parseado do config) para evitar ambiguidade.
ARM_FLAGS = {
    "A": ("✗", "✗", "baseline"),
    "B": ("✓", "✗", "isolates cache"),
    "C": ("✓", "auto", "vendor default"),
    "D": ("✗", "✗", "GGUF baseline"),
    "E": ("✓", "✗", "cache"),
    "F": ("✓", "draft", "draft-mtp"),
    "G": ("✓", "draft", "draft-mtp"),
    "H": ("✓", "draft", "draft-mtp"),
    "I": ("✗", "✗", "loader check"),
    "J": ("✗", "✗", "AWQ smoke"),
    "K": ("✓", "✗", "MTP gate baseline"),
    "L": ("✓", "✓", "MTP gate candidate"),
    "M": ("✓", "✓", "SpecPrefill 2B"),
    "N": ("✓", "✓", "SpecPrefill 0.8B"),
    "O": ("—", "—", "ANE prefill"),
    "P": ("✗", "✗", "baseline"),
    "Q": ("✓", "✗", "cache baseline"),
    "R": ("✓", "DSpark", "cache + spec DSpark"),
    "S": ("✓", "DFlash2", "cache + spec DFlash2"),
    "T": ("✓", "✓", "promoted G9"),
    "U": ("✓", "✓", "fp16 control"),
    "V": ("✓ Turbo", "✓", "Gate 10 PASS"),
    "Y": ("✓ Turbo", "✓", "quality"),
    "Z": ("✓ Turbo", "✓", "fp16 control"),
    "W": ("✗", "✗", "DFlash baseline"),
    "X": ("✗", "DFlash2", "failed G11"),
}

# Comparação qualitativa dos runtimes: o que cada um busca, como, e o custo.
RUNTIME_PROFILES = [
    {
        "name": "mlx-serve", "arms": "A–C", "tag": "MLX reference",
        "goal": "Serve the standard MLX model as a performance floor and quality reference.",
        "how": "MLX 8-bit weights, prefix cache and MTP in the vendor's automatic mode.",
        "cost": "No own quant or speculative prefill; moderate decode. Answers 'does the simple path work?'.",
    },
    {
        "name": "llama.cpp", "arms": "D–H", "tag": "GGUF + draft",
        "goal": "Leverage the GGUF ecosystem and speculate with a draft model (draft-mtp).",
        "how": "GGUF Q4/Q6/Q8 quants on the Metal backend; size ladder against quality.",
        "cost": "Lower decode on this machine; draft-mtp speeds up but does not reach native MTP.",
    },
    {
        "name": "oMLX", "arms": "I–O, T–U, W–X", "tag": "production candidate",
        "goal": "Bring together in a single runtime cache, native MTP, SpecPrefill and prefill via ANE.",
        "how": "Integrated MTP plus own exl-style quants (oQ8e, oQ4e) and AWQ 5bpw.",
        "cost": "Most complete runtime; runs gates 6, 7, 9 and 11.",
    },
    {
        "name": "mlx-dspark", "arms": "P–S", "tag": "DSpark/DFlash2 drafters",
        "goal": "Speculate in decode with separate draft checkpoints (DSpark, DFlash2), preserving the prefix cache.",
        "how": "8-bit body plus a dedicated drafter that proposes tokens for the target to verify; warm cache ~1.0 maintained.",
        "cost": "Gate 8 PASSES (decode +90%/+154% vs baseline), but the peak (S 38 @32K) falls below MTPLX and is 8-bit.",
    },
    {
        "name": "MTPLX", "arms": "V, Y, Z", "tag": "forge, higher decode",
        "goal": "Forge a model plus MTP heads with its own quant recipe for the highest sustained decode.",
        "how": "Forge pipeline with Turbo cache and MTP; one generation model per daemon.",
        "cost": "Unverified checkpoints (flag --unsafe); serves one model at a time.",
    },
]

# Comparação qualitativa das quantizações: o alvo de cada uma e o custo.
QUANT_PROFILES = [
    {
        "name": "MLX 8-bit", "bpw": "8.0", "runtime": "mlx-serve / mlx-dspark",
        "goal": "Quality close to fp as a reference.",
        "cost": "Larger footprint; moderate decode. Base of the baselines.",
    },
    {
        "name": "GGUF Q4/Q6/Q8", "bpw": "4.5–8.5", "runtime": "llama.cpp",
        "goal": "Size ladder against quality in the GGUF ecosystem.",
        "cost": "k-quants on Metal; slower decode here. Q4 is the gate to Q6/Q8.",
    },
    {
        "name": "AWQ 5bpw", "bpw": "5.0", "runtime": "oMLX",
        "goal": "Activation-aware quant: good quality at 5 bpw, compatible with MTP.",
        "cost": "Medium size; base of the MTP gate (K/L) and SpecPrefill.",
    },
    {
        "name": "oQ8e 8.6bpw", "bpw": "8.6", "runtime": "oMLX",
        "goal": "Production fidelity on M4 with MTP (exl 8-bit style).",
        "cost": "Large, but promoted in Gate 9 (arm T).",
    },
    {
        "name": "oQ4e 4.7bpw", "bpw": "4.7", "runtime": "oMLX",
        "goal": "Smallest oMLX quant, to pair with DFlash2.",
        "cost": "In the test it ran cache-off; prefill dominates the total time (Gate 11 failed).",
    },
    {
        "name": "MTPLX 4-/8-bit", "bpw": "4.5 / 8.0", "runtime": "MTPLX",
        "goal": "Recipe co-designed with the MTP heads: Speed 4-bit, Quality 8-bit.",
        "cost": "Maximum decode; unverified checkpoints. Y/Z still under measurement.",
    },
]

# Glossário curto dos gates (eliminatórios; ver plan.md para os limiares completos).
GATES_GLOSSARY = [
    {"gate": "1 · Cache correctness", "desc": "Reuses the right prefix: hit >=0.95 identical; no reuse after mutation."},
    {"gate": "2 · Latency", "desc": "Cache gives >=5x on warm time; TTFT reflects only the new suffix."},
    {"gate": "3 · Stability", "desc": "No crash/corruption; swap <=0.5GB; RAM <=80GB; 20 tool turns correct."},
    {"gate": "4 · MTP", "desc": "MTP reduces the total time without lowering cache hit or changing the result."},
    {"gate": "5 · Q6/Q8", "desc": "Only runs if Q4 passes; adopts Q6/Q8 if it recovers a failure or a quality gain."},
    {"gate": "6 · SpecPrefill", "desc": "M or N reduces TTFT >=20% vs L at 16K and 32K, keeping correctness."},
    {"gate": "7 · ANE", "desc": "O reduces TTFT >=5% vs J with ANE programs actually compiled."},
    {"gate": "8 · DSpark/DFlash2", "desc": "Decode +25%/+15% and total time +10% vs Q, with greedy equivalence."},
    {"gate": "9 · oQ8e", "desc": "T vs U no crash; promotes T if the difference is <5%."},
    {"gate": "10 · MTPLX", "desc": "Loads and runs without functional loss; cache, active MTP and acceptance confirmed."},
    {"gate": "11 · oQ4e+DFlash", "desc": "X only stays if it cuts >=10% in the median total time vs W."},
]

# Headline gate verdicts (editorial; edit as gates resolve). state in
# {"pass","fail","control","running","pending"}.
VERDICTS = [
    {"gate": "Gate 9 — oQ8e", "arm": "T", "state": "pass",
     "note": "T promoted (M4 production); U just control, no advantage >5%."},
    {"gate": "Gate 10 — MTPLX", "arm": "V", "state": "pass",
     "note": "Best decode 32K; tool loop 2/3 with corrected prompt."},
    {"gate": "Gate 11 — oQ4e+DFlash", "arm": "X", "state": "fail",
     "note": "DFlash2 +14-24% decode, but no 10% of total time (cache-off)."},
    {"gate": "MTP gate — AWQ5", "arm": "L", "state": "pass",
     "note": "L beats K on total time; MTP acceptance ~0.8; tool loop 2/3."},
    {"gate": "Gate 6 — SpecPrefill", "arm": "M/N", "state": "fail",
     "note": "Cuts cold TTFT ~-55%, but zeroes the warm cache (hit 0%); warm TTFT 6-17x worse than L. None advances."},
    {"gate": "Gate 7 — ANE", "arm": "O", "state": "blocked",
     "note": "Blocked: 'Private ANE procedure-bank compiler is unavailable' in this omlx build. ANE kernels do not compile. External, not fixable in the campaign."},
    {"gate": "Gate 8 — DSpark/DFlash2", "arm": "R/S", "state": "pass",
     "note": "Speculation delivers: decode +90%/+154% and total time -57%/-70% vs Q; tool loop 2/3. But the peak (S 38 @32K) falls below MTPLX (44.5) and is 8-bit."},
    {"gate": "MTPLX Quality — Y/Z vs Speed", "arm": "Y/Z", "state": "control",
     "note": "Speed ~23-31% faster in decode. Among Quality, Z(fp16) dominates Y(8-bit): same decode, tool loop 3/5 vs 1/5. Quality only for fidelity (not measured)."},
    {"gate": "Ceiling 262K — decode", "arm": "L/T/S vs V/Y", "state": "pass",
     "note": "At the native maximum (262K) the MTPLX MTP collapses: decode V 6.1 / Y 8.7 tps. oMLX (L 15.4 / T 14.1) and dspark/DFlash2 (S 14.2) hold ~14-15 tps. Cause: the MTP verify re-reads the 262K KV per step; DFlash2 does not scale that way. Speed verdict at the ceiling: oMLX and dspark; MTPLX loses the advantage it had up to 128K."},
    {"gate": "Ceiling 262K — cache", "arm": "L/T/S/V/Y", "state": "pass",
     "note": "All reuse the prefix at the ceiling: identical ~1.0, append 0.95-1.0, tool_turn 0.99-1.0; middle_mutation partial (0.38-0.49). CONFIRMED by variable isolation: the MTPLX tool_turn that zeroed at 128K/cap 48G reuses 0.99 at 128K/cap 100G (same worst-case order) -> the miss was session-bank under-provisioning, not order. Rule: size the per-session cap for the context KV + tool footprint (48G is too little already at 128K; 100G suffices at 262K)."},
]

# Campaign queue with completion state; edit as stages land.
QUEUE = [
    {"stage": "8K smoke + 32K cache/MTP (greedy)", "status": "done"},
    {"stage": "oQ8e smoke T/U (Gate 9)", "status": "done"},
    {"stage": "oQ4e+DFlash W/X (Gate 11)", "status": "done"},
    {"stage": "MTPLX V (Gate 10)", "status": "done"},
    {"stage": "MTPLX Quality Y/Z vs Speed (8K + 32K)", "status": "done"},
    {"stage": "oMLX K + L canonical (MTP gate)", "status": "done"},
    {"stage": "SpecPrefill 16K (Gate 6)", "status": "done"},
    {"stage": "SpecPrefill 32K (Gate 6) — failed", "status": "done"},
    {"stage": "ANE 16K/32K (Gate 7) — blocked (ANE compiler absent)", "status": "blocked"},
    {"stage": "mlx-dspark smoke + 8K/32K + tool loop (Gate 8) — pass", "status": "done"},
    {"stage": "cache 65K", "status": "done"},
    {"stage": "cache 128K (L/T/V/Y/S)", "status": "done"},
    {"stage": "native 262K (L/T/V/S full, Y partial)", "status": "done"},
    {"stage": "tool-loop survivors", "status": "pending"},
    {"stage": "confirmatory tool_turn V@128K/cap 100G", "status": "pending"},
    {"stage": "re-run T/U at max_tokens=4096", "status": "pending"},
]


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _median(records: list[dict], key: str):
    values = [r[key] for r in records if isinstance(r.get(key), (int, float))]
    return st.median(values) if values else None


def build_arm_rows(records: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("decode_tps") is None or not r.get("arm"):
            continue
        mode = "canonical" if r.get("temperature") == 1 else "greedy"
        groups[(r["arm"], r.get("context_target"), r.get("content_class"), mode)].append(r)

    rows = []
    for (arm, ctx, cls, mode), rs in sorted(groups.items()):
        ident = [r for r in rs if r.get("scenario") == "identical"]
        cold = [r for r in rs if r.get("scenario") == "cold"]
        meta = ARM_META.get(arm, {"runtime": "?", "model": arm, "config": ""})
        quant, bpw = QUANT.get(arm, (None, None))
        rows.append(
            {
                "arm": arm,
                "runtime": meta["runtime"],
                "model": meta["model"],
                "config": meta["config"],
                "quant": quant,
                "bpw": bpw,
                "context": ctx,
                "content_class": cls,
                "mode": mode,
                "records": len(rs),
                "decode_tps": _median(rs, "decode_tps"),
                "ttft_identical_ms": _median(ident, "ttft_ms"),
                "e2e_identical_ms": _median(ident, "e2e_ms"),
                "cache_hit_identical": _median(ident, "cache_hit_ratio"),
                "ttft_cold_ms": _median(cold, "ttft_ms"),
                "e2e_cold_ms": _median(cold, "e2e_ms"),
                "prefill_tps_cold": _median(cold, "prompt_tps"),
                "correct": sum(1 for r in rs if r.get("correct")),
                "total": len(rs),
            }
        )
    return rows


def build_test_coverage(records: list[dict], tool_loop: dict[str, dict]) -> list[dict]:
    """Por braço: quais cenários rodaram e em qual modo (canonical > greedy > —)."""
    seen: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for r in records:
        arm = r.get("arm")
        scen = r.get("scenario")
        if not arm or not scen:
            continue
        mode = "canonical" if r.get("temperature") == 1 else "greedy"
        seen[arm][scen].add(mode)
    rows = []
    for arm, meta in ARM_META.items():
        scenarios = {}
        for s in SCENARIOS:
            modes = seen.get(arm, {}).get(s, set())
            scenarios[s] = "canonical" if "canonical" in modes else (
                "greedy" if "greedy" in modes else None)
        tl = tool_loop.get(arm)
        rows.append({
            "arm": arm,
            "runtime": meta["runtime"],
            "model": meta["model"],
            "scenarios": scenarios,
            "tool": f"{tl['passed']}/{tl['total']}" if tl else None,
            "measured": any(scenarios.values()),
        })
    return rows


def build_coverage(arm_rows: list[dict], tool_loop: dict[str, dict]) -> list[dict]:
    """Per-arm coverage: cache/MTP flags + measured contexts by mode."""
    ctx = defaultdict(lambda: {"canon": set(), "greedy": set()})
    for a in arm_rows:
        mode = "canon" if a["mode"] == "canonical" else "greedy"
        if a.get("context") is not None:
            ctx[a["arm"]][mode].add(a["context"] // 1024)
    rows = []
    for arm, meta in ARM_META.items():
        cache, mtp, note = ARM_FLAGS.get(arm, ("?", "?", ""))
        c = sorted(ctx[arm]["canon"])
        g = sorted(ctx[arm]["greedy"])
        tl = tool_loop.get(arm)
        rows.append({
            "arm": arm,
            "runtime": meta["runtime"],
            "model": meta["model"],
            "quant": QUANT.get(arm, (None, None))[0],
            "cache": cache,
            "mtp": mtp,
            "note": note,
            "canon_ctx": [f"{v}K" for v in c],
            "greedy_ctx": [f"{v}K" for v in g],
            "measured": bool(c or g),
            "tool": f"{tl['passed']}/{tl['total']}" if tl else None,
        })
    return rows


def build_tool_loop(records: list[dict]) -> dict[str, dict]:
    """Per (arm, session) best-of-N pass fraction from verdict records."""
    by_session: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("record_type") == "verdict" and r.get("arm"):
            by_session[(r["arm"], r.get("session_id"))].append(r)
    latest: dict[str, dict] = {}
    for (arm, session), verdicts in by_session.items():
        passed = sum(1 for v in verdicts if v.get("correct"))
        total = len(verdicts)
        # Keep the newest session per arm (session ids are UTC timestamps).
        if arm not in latest or (session or "") > latest[arm]["session"]:
            latest[arm] = {"session": session, "passed": passed, "total": total}
    return latest


def build_gates() -> dict[str, dict]:
    gates = {}
    for path in sorted(RESULTS.glob("*gate*.json")):
        try:
            gates[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    for name in ("specprefill-selection", "mlx-dspark-selection", "runtime-survivors"):
        for path in RESULTS.glob(f"{name}*.json"):
            try:
                gates[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
    return gates


def main() -> int:
    cache_records = _load_jsonl(CACHE_PROBE)
    for greedy_path in GREEDY_PROBES:
        cache_records.extend(_load_jsonl(greedy_path))
    tool_records = _load_jsonl(TOOL_LOOP)
    arm_rows = build_arm_rows(cache_records)
    tool_loop = build_tool_loop(tool_records)
    overview = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "arms": arm_rows,
        "tool_loop": tool_loop,
        "coverage": build_coverage(arm_rows, tool_loop),
        "test_catalog": TEST_CATALOG,
        "test_coverage": build_test_coverage(cache_records, tool_loop),
        "gates": build_gates(),
        "verdicts": VERDICTS,
        "queue": QUEUE,
        "arm_glossary": {
            arm: {
                "runtime": meta["runtime"],
                "model": meta["model"],
                "quant": QUANT.get(arm, (None, None))[0],
                "bpw": QUANT.get(arm, (None, None))[1],
                "desc": ARM_DESC.get(arm, ""),
            }
            for arm, meta in ARM_META.items()
        },
        "gates_glossary": GATES_GLOSSARY,
        "runtime_profiles": RUNTIME_PROFILES,
        "quant_profiles": QUANT_PROFILES,
    }
    OVERVIEW.write_text(json.dumps(overview, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    canonical = sum(1 for a in overview["arms"] if a["mode"] == "canonical")
    print(f"wrote {OVERVIEW} — {len(overview['arms'])} arm groups ({canonical} canonical)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
