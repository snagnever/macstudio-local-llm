#!/usr/bin/env python3
"""Consolida os JSONL da campanha flashnext-daily-driver em results/reports.json.

O JSON alimenta os dois reports no estilo da campanha densa:
render_overview.py (dashboard da campanha) e render_perf_lines.py (linhas por
contexto). Os números saem só de results/*.jsonl; o texto de glossário,
perfis e veredito fica nas constantes deste arquivo.

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
FILE_RE = re.compile(r"^(c\d)-(\d+)-t([\d.]+)(?:-(.+))?\.jsonl$")

# Etapa e modo por sufixo do arquivo. "canonical" = perfil do vendor (conta no
# veredito); "diag" = controle fora do ranking.
SUFFIX_STAGE = {
    None: ("A", "canonical", ""),
    "b": ("B", "canonical", ""),
    "yarn2": ("sonda", "canonical", "YaRN 2.0 + KV 8-bit"),
    "nomtp": ("diag", "diag", "temp 0 · MTP off"),
    "mem102g": ("diag", "diag", "MTPLX_MEMORY_LIMIT_BYTES=102G"),
}
STAGE_RANK = {"B": 3, "A": 2, "0": 2, "sonda": 2, "diag": 0}

CANDIDATES = [
    {
        "id": "c1", "name": "ddalcu mixed-4/8 · mlx-serve 26.9.2", "short": "c1 mlx-serve",
        "runtime": "mlx-serve", "runtime_version": "26.9.2",
        "model": "ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit", "revision": "ef5b919",
        "quant": "mixed 4/8-bit", "bpw": 4.85, "disk_gb": 107.3, "port": 11234,
        "cache": "hot cache em RAM 16 GB + disco 100 GB · 64 entradas · ssm-checkpoint 16",
        "spec": "MTP nativa depth 6 + PLD (n-gram) · aceitação 0.50–0.67",
        "ceiling": "512K com follow-up", "state": "pass", "status": "vencedor",
        "note": "Menor T_turno nas duas bandas: 11.03 s a 32K e 12.35 s a 128K (3 reps).",
    },
    {
        "id": "c2", "name": "oQ4e · oMLX 0.6.4", "short": "c2 oMLX 0.6.4",
        "runtime": "oMLX", "runtime_version": "0.6.4",
        "model": "Jundot/Qwen3.8-Flash-Next-oQ4e-mtp", "revision": "2615fc0",
        "quant": "oQ4e", "bpw": 5.97, "disk_gb": 132.2, "port": 8000,
        "cache": "paged SSD cache · PLE em mmap (qwen4_ple_ssd_offload)",
        "spec": "MTP do checkpoint · aceitação não exposta na telemetria",
        "ceiling": "262K (oMLX sem YaRN)", "state": "control", "status": "dominado",
        "note": "Passa nos gates, mas o c3 roda os mesmos pesos mais rápido em todas as bandas. Sai antes da Etapa B.",
    },
    {
        "id": "c3", "name": "oQ4e · oMLX 0.7.0.dev2", "short": "c3 oMLX dev2",
        "runtime": "oMLX", "runtime_version": "0.7.0.dev2",
        "model": "Jundot/Qwen3.8-Flash-Next-oQ4e-mtp", "revision": "2615fc0",
        "quant": "oQ4e", "bpw": 5.97, "disk_gb": 132.2, "port": 8000,
        "cache": "paged SSD cache · PLE em mmap via model_settings.json",
        "spec": "MTP do checkpoint · aceitação não exposta na telemetria",
        "ceiling": "262K (oMLX sem YaRN)", "state": "pass", "status": "2º lugar",
        "note": "Finalista: T_turno 13.48 s a 32K e 15.03 s a 128K (3 reps), +18% sobre o c1.",
    },
    {
        "id": "c4", "name": "MTPLX Optimized-Speed · MTPLX 2.11.2", "short": "c4 MTPLX",
        "runtime": "MTPLX", "runtime_version": "2.11.2",
        "model": "Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed", "revision": "6bc2f6e",
        "quant": "MTPLX Optimized-Speed", "bpw": 5.43, "disk_gb": 120.2, "port": 8000,
        "cache": "session bank em RAM + SSD session cache on",
        "spec": "MTP nativa · perfil turbo depth 3 · aceitação 0.24–0.46",
        "ceiling": "114.688 tokens (fit do memory plan)", "state": "fail", "status": "eliminado",
        "note": "Maior decode a 32K (~70 tok/s), mas recusa 128K e 256K com HTTP 507: o fit do memory plan é 114.688 tokens.",
    },
]

RIG = [
    {"lab": "Chip", "val": "Apple M4 Max"},
    {"lab": "CPU", "val": "16 cores (12P+4E)"},
    {"lab": "GPU", "val": "40 cores · Metal 4"},
    {"lab": "Memória unificada", "val": "128 GB"},
    {"lab": "macOS", "val": "26.6.2 (25G83)"},
    {"lab": "Wired limit", "val": "default (iogpu 0) · sem sudo"},
    {"lab": "Portas", "val": "mlx-serve :11234 · oMLX/MTPLX :8000"},
]

SAMPLING = "temperature 1.0 · top_p 0.95 · top_k 20 · reasoning xhigh · max_tokens 4096"

RUNTIME_PROFILES = [
    {"name": "mlx-serve 26.9.2", "tag": "incumbente", "arms": "c1",
     "goal": "Servir o Flash-Next com MTP nativa e cache de prefixo em dois níveis.",
     "how": "MTP depth 6 com PLD; hot cache em RAM mais disco; checkpoint do estado DeltaNet; YaRN via --config-overrides.",
     "cost": "Pina KV e hot cache em wired: opera a 106–108 GB a 128K/256K, sem swap."},
    {"name": "oMLX 0.6.4", "tag": "baseline oMLX", "arms": "c2",
     "goal": "Servidor MLX para agentes, com cache paginado que transborda para SSD.",
     "how": "Paged SSD cache; PLE do oQ4e em mmap por model_settings.json.",
     "cost": "Decode e prefill mais lentos que a dev2 nos mesmos pesos; sem YaRN (teto 262K)."},
    {"name": "oMLX 0.7.0.dev2", "tag": "dev", "arms": "c3",
     "goal": "Mesmo servidor, com kernels novos (prefill anunciado para M5).",
     "how": "Mesma config de cache e PLE da 0.6.4; muda só o runtime.",
     "cost": "Build de desenvolvimento; TTFT quente 2× o do mlx-serve; sem YaRN."},
    {"name": "MTPLX 2.11.2", "tag": "MTP no pack", "arms": "c4",
     "goal": "Decode máximo com MTP embutida no checkpoint quantizado.",
     "how": "Session bank em RAM + SSD session cache; memory plan calcula o contexto que cabe.",
     "cost": "Recusa prompts acima de 114.688 tokens (HTTP 507) no 128 GB."},
]

QUANT_PROFILES = [
    {"name": "ddalcu mixed-4/8", "bpw": "4.85", "runtime": "mlx-serve",
     "goal": "Experts em 4-bit e atenção em 8-bit, com tabela n-gram de 32 GB para o PLD.",
     "cost": "107 GB em disco; o menor dos três."},
    {"name": "Jundot oQ4e-mtp", "bpw": "5.97", "runtime": "oMLX",
     "goal": "Quant oQ do oMLX com cabeça MTP e PLE descarregável para SSD.",
     "cost": "132 GB em disco; sem o offload de PLE satura os 128 GB."},
    {"name": "Youssofal MTPLX Optimized-Speed", "bpw": "5.43", "runtime": "MTPLX",
     "goal": "Pack com MTP nativa e n-gram de 32 GB em sidecar, otimizado para decode.",
     "cost": "120 GB em disco; pesos de 77.3 GiB limitam o fit de contexto."},
]

GATES_GLOSSARY = [
    {"gate": "Cache", "desc": "hit ≥ 0.90 em append e tool_turn a 32K e 128K."},
    {"gate": "Correção", "desc": "needles 10/50/90 corretas a 32K e 128K; truncado (reasoning > 4096 tokens) não conta como falha."},
    {"gate": "Memória", "desc": "swap delta ≤ 0.5 GB em qualquer banda."},
    {"gate": "Servidor", "desc": "zero erro HTTP 4xx/5xx ou erro no stream a 32K e 128K."},
    {"gate": "Wired (alerta)", "desc": "pico acima de 102 GB gera alerta, não elimina: é o ponto de operação normal do mlx-serve."},
]

TEST_CATALOG = {
    "scenarios": [
        {"key": "cold", "eval": "Prompt inteiro sem cache. Mede o primeiro turno (cold TTFT) e o prefill; prima o cache."},
        {"key": "identical", "eval": "Mesmo prompt de novo. Melhor caso sintético do reuso."},
        {"key": "append", "eval": "Prompt anterior + sufixo novo. Turno de conversa."},
        {"key": "middle_mutation", "eval": "Edição no meio do prompt. Reuso esperado ~metade; fica fora do T_turno."},
        {"key": "tool_turn", "eval": "Prompt anterior + resultado de ferramenta. Turno de agente; entra no T_turno."},
    ],
    "modes": [
        {"key": "canônico", "eval": SAMPLING + ". Conta no veredito."},
        {"key": "diag temp 0", "eval": "temperature 0 a 32K. Compara resposta c2 × c3 e MTP on × off no c4. Fora do ranking."},
        {"key": "diag 102G", "eval": "c4 a 128K com MTPLX_MEMORY_LIMIT_BYTES=102G. Testa se o fit maior serve a banda."},
    ],
    "correctness": [
        {"key": "audit_retrieval", "eval": "Needles a 10%, 50% e 90% da fixture. Correto = as três na resposta."},
        {"key": "truncado", "eval": "finish_reason=length com 4096 tokens de reasoning. Registrado, não elimina."},
    ],
    "t_turno": "T_turno = TTFT do tool_turn + 512 / mediana do decode dos cenários quentes servidos "
               "(identical, append, tool_turn). É a espera de um turno de agente com resposta de 512 tokens. "
               "Menor é melhor.",
    "metrics": ["ttft_ms (TTFT)", "decode_tps (decode)", "prompt_tps (prefill)", "cache_hit_ratio",
                "cached_tokens", "mtp_acceptance", "ram_peak_gb (wired)", "mem_free_min_gb",
                "swap_delta_gb", "finish_reason", "needle_verdicts", "error / error_stage"],
}

QUEUE = [
    {"stage": "Etapa 0 — smoke a 8K, 4 candidatos", "status": "done"},
    {"stage": "Etapa A — triagem 1 rep a 32K, 128K e 256K", "status": "done"},
    {"stage": "Diagnóstico temp 0 a 32K (c2 × c3; c4 MTP on × off)", "status": "done"},
    {"stage": "c4 a 128K com budget de 102G", "status": "done"},
    {"stage": "Etapa B — 3 reps a 32K e 128K (c1, c3)", "status": "done"},
    {"stage": "Sonda de capacidade a 512K", "status": "done"},
    {"stage": "Registro do daily driver (c1)", "status": "done"},
]

VERDICTS = [
    {"gate": "Veredito", "arm": "c1 · mlx-serve 26.9.2", "state": "pass",
     "note": "Driver diário. Vence c3 por 18% nas duas bandas; o TTFT quente decide (2.1 × 4.8 s a 128K)."},
    {"gate": "Finalista", "arm": "c3 · oMLX 0.7.0.dev2", "state": "pass",
     "note": "Passa em todos os gates. Decode empata com o c1 (~50 tok/s a 128K); perde no TTFT."},
    {"gate": "Dominado", "arm": "c2 · oMLX 0.6.4", "state": "control",
     "note": "Passa nos gates. Mesmos pesos do c3, mais lento em todas as bandas: cold a 256K 1187 × 578 s."},
    {"gate": "Servidor a 128K", "arm": "c4 · MTPLX 2.11.2", "state": "fail",
     "note": "HTTP 507 a 128K e 256K. Com 102G o fit cobre 128K, mas middle_mutation e tool_turn falham por alocação."},
    {"gate": "Wired > 102 GB", "arm": "c1 @128K / 256K / 512K", "state": "control",
     "note": "Alerta, não elimina: 104–109 GB, swap 0, memória livre mínima 0.01–0.06 GB."},
    {"gate": "MTP lossless", "arm": "c4 · temp 0", "state": "pass",
     "note": "MTP on 5/5 needles e 1.8× de decode; MTP off 4/5 (um truncado). Sem sinal de MTP lossy."},
]

TAKEAWAYS = [
    ["T_turno quase plano", "o c1 vai de 11.0 s a 32K para 12.35 s a 128K e 14.2 s a 256K; o c3, de 13.5 a 16.7 s; o c2, de 17.1 a 28.8 s."],
    ["O TTFT decide, não o decode", "a 128K c1 e c3 decodificam ~50 tok/s; o turno quente responde em 2.1 s no c1 e 4.8 s no c3."],
    ["c4 não serve 128K", "melhor decode a 32K (~70 tok/s), mas o MTPLX 2.11.2 recusa acima de 114.688 tokens com HTTP 507."],
    ["dev2 × 0.6.4 nos mesmos pesos", "a 256K, cold 578 × 1187 s e decode 47.5 × 23.6 tok/s."],
    ["512K no c1", "cold 844.6 s, follow-up em 0.6 s com hit 1.00, wired 104.3 GB, memória livre mínima 0.01 GB, swap 0."],
]

# Ressalvas por grupo (candidato, contexto, etapa) que o número sozinho não mostra.
GROUP_NOTES = {
    ("c4", 8192, "0"): "telemetria de cache incoerente: hit 1.00 no cold e tool_turn de 75 s",
    ("c4", 131072, "diag"): "3/5 servidos: middle_mutation e tool_turn falham por alocação",
    ("c4", 131072, "A"): "recusa HTTP 507: fit do memory plan de 114.688 tokens",
    ("c4", 262144, "A"): "recusa HTTP 507: fit do memory plan de 114.688 tokens",
    ("c1", 524288, "sonda"): "sonda: só cold e identical; decode quente = identical; cold decode 42.6 tok/s",
}

DELTAS = [
    {"label": "c1 × c3 · 128K", "a": ["c1", 131072, "canonical"], "b": ["c3", 131072, "canonical"]},
    {"label": "c1 × c3 · 32K", "a": ["c1", 32768, "canonical"], "b": ["c3", 32768, "canonical"]},
    {"label": "dev2 × 0.6.4 · 256K", "a": ["c3", 262144, "canonical"], "b": ["c2", 262144, "canonical"]},
    {"label": "MTP on × off · c4 32K t0", "a": ["c4", 32768, "diag:temp 0"], "b": ["c4", 32768, "diag:temp 0 · MTP off"]},
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
        raise ValueError(f"nome de arquivo fora do padrão: {path.name}")
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
    # Um arquivo = um grupo (arm, contexto); o summarize_driver aplica gates e alertas.
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


def build(results_dir: Path) -> dict:
    groups = []
    for path in sorted(results_dir.glob("c*-*-t*.jsonl")):
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
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-dir", default=str(RESULTS))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    data = build(Path(a.results_dir))
    out = Path(a.out)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(data['groups'])} grupos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
