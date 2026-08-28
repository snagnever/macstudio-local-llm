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
    "A": "mlx-serve 8-bit, cache off — baseline sem cache.",
    "B": "mlx-serve 8-bit, cache on — isola o prefix cache.",
    "C": "mlx-serve 8-bit, cache + MTP auto — default do vendor.",
    "D": "llama.cpp GGUF Q4, cache off — baseline GGUF.",
    "E": "llama.cpp GGUF Q4, cache on.",
    "F": "llama.cpp GGUF Q4 + draft-mtp.",
    "G": "llama.cpp GGUF Q6 + draft-mtp.",
    "H": "llama.cpp GGUF Q8 + draft-mtp.",
    "I": "oMLX carregando o 8-bit MLX-Serve — check de loader (pode falhar).",
    "J": "oMLX AWQ 5bpw, cache off — smoke do loader AWQ.",
    "K": "oMLX AWQ, cache on, sem MTP — baseline do gate MTP.",
    "L": "oMLX AWQ, cache + MTP — candidato do gate MTP.",
    "M": "L + SpecPrefill com draft 2B.",
    "N": "L + SpecPrefill com draft 0.8B.",
    "O": "oMLX AWQ + prefill pela ANE.",
    "P": "mlx-dspark 8-bit, cache off — baseline sem especulação.",
    "Q": "mlx-dspark 8-bit, cache on — baseline com cache.",
    "R": "mlx-dspark cache + drafter DSpark (especulação no decode, cache preservado).",
    "S": "mlx-dspark cache + drafter DFlash2 (especulação no decode, cache preservado).",
    "T": "oMLX oQ8e 8.6bpw, cache + MTP — candidato de produção M4.",
    "U": "oMLX oQ8e-fp16 — controle fp16 do oQ8e.",
    "V": "MTPLX Optimized Speed (corpo 4-bit) — MVP runtime+checkpoint.",
    "W": "oMLX oQ4e 4.7bpw, cache off — baseline do par DFlash.",
    "X": "oMLX oQ4e + DFlash2 — teste causal do DFlash2.",
    "Y": "MTPLX Optimized Quality (8-bit) — fidelidade vs Speed.",
    "Z": "MTPLX Optimized Quality FP16 — controle fp16 da Quality.",
}

# Ordem canônica dos cenários do cache-probe.
SCENARIOS = ("cold", "identical", "append", "middle_mutation", "tool_turn")

# Catálogo estático: o que cada teste avalia (para a aba Testes).
TEST_CATALOG = {
    "scenarios": [
        {"key": "cold", "eval": "Prompt novo, sem cache prévio. Mede TTFT e prefill frios."},
        {"key": "identical", "eval": "Mesmo prompt repetido. Mede cache hit quente e TTFT quente."},
        {"key": "append", "eval": "Prompt estendido com um sufixo. Reuso parcial do prefixo."},
        {"key": "middle_mutation", "eval": "Muda um trecho no meio. Invalidação do cache a partir do ponto."},
        {"key": "tool_turn", "eval": "Anexa um turno estilo ferramenta ao prompt (cenário de cache, não o loop agêntico)."},
    ],
    "modes": [
        {"key": "canonical", "eval": "temp=1, sampling do vendor. Métrica de decisão (vale para veredito)."},
        {"key": "greedy", "eval": "temp=0, determinístico. Diagnóstico e equivalência greedy (hash de tokens). Não conta para veredito."},
    ],
    "correctness": [
        {"key": "code", "eval": "Checksum: o valor exato calculado precisa aparecer na saída (code_result_verdict)."},
        {"key": "audit_retrieval", "eval": "Needles em 3 profundidades (10/50/90). Correto = as três presentes e sem truncamento."},
    ],
    "tool_loop": {
        "eval": "Loop agêntico de 20 turnos, best-of-N. Passa se chamar as 4 ferramentas "
                "(read_fixture, search_fixture, run_fixture_test, record_result) e emitir os 4 "
                "identificadores verbatim no turno final; maioria das N repetições.",
    },
    "metrics": [
        "ttft_ms (TTFT)", "decode_tps (decode)", "e2e_ms (tempo total)", "prompt_tps (prefill)",
        "cache_hit_ratio", "cached_tokens", "accept_length / mtp_acceptance (spec)",
        "ram_peak_gb", "gpu_temp_peak_c",
    ],
}

# Flags de cache/MTP e nota curta por braço, para a matriz de cobertura.
# Explícito (não parseado do config) para evitar ambiguidade.
ARM_FLAGS = {
    "A": ("✗", "✗", "baseline"),
    "B": ("✓", "✗", "isola cache"),
    "C": ("✓", "auto", "default vendor"),
    "D": ("✗", "✗", "baseline GGUF"),
    "E": ("✓", "✗", "cache"),
    "F": ("✓", "draft", "draft-mtp"),
    "G": ("✓", "draft", "draft-mtp"),
    "H": ("✓", "draft", "draft-mtp"),
    "I": ("✗", "✗", "check loader"),
    "J": ("✗", "✗", "smoke AWQ"),
    "K": ("✓", "✗", "baseline MTP gate"),
    "L": ("✓", "✓", "candidato MTP gate"),
    "M": ("✓", "✓", "SpecPrefill 2B"),
    "N": ("✓", "✓", "SpecPrefill 0.8B"),
    "O": ("—", "—", "ANE prefill"),
    "P": ("✗", "✗", "baseline"),
    "Q": ("✓", "✗", "baseline cache"),
    "R": ("✓", "DSpark", "cache + spec DSpark"),
    "S": ("✓", "DFlash2", "cache + spec DFlash2"),
    "T": ("✓", "✓", "promovido G9"),
    "U": ("✓", "✓", "controle fp16"),
    "V": ("✓ Turbo", "✓", "Gate 10 PASS"),
    "Y": ("✓ Turbo", "✓", "quality"),
    "Z": ("✓ Turbo", "✓", "controle fp16"),
    "W": ("✗", "✗", "baseline DFlash"),
    "X": ("✗", "DFlash2", "reprovou G11"),
}

# Comparação qualitativa dos runtimes: o que cada um busca, como, e o custo.
RUNTIME_PROFILES = [
    {
        "name": "mlx-serve", "arms": "A–C", "tag": "referência MLX",
        "goal": "Servir o modelo MLX padrão como piso de desempenho e referência de qualidade.",
        "how": "Pesos MLX 8-bit, prefix cache e MTP no modo automático do vendor.",
        "cost": "Sem quant própria nem prefill especulativo; decode moderado. Responde 'o caminho simples funciona?'.",
    },
    {
        "name": "llama.cpp", "arms": "D–H", "tag": "GGUF + draft",
        "goal": "Aproveitar o ecossistema GGUF e especular com um modelo rascunho (draft-mtp).",
        "how": "Quants GGUF Q4/Q6/Q8 no backend Metal; escada de tamanho contra qualidade.",
        "cost": "Decode mais baixo nesta máquina; o draft-mtp acelera, mas não alcança o MTP nativo.",
    },
    {
        "name": "oMLX", "arms": "I–O, T–U, W–X", "tag": "candidato de produção",
        "goal": "Reunir num só runtime cache, MTP nativo, SpecPrefill e prefill pela ANE.",
        "how": "MTP integrado mais quants próprias estilo exl (oQ8e, oQ4e) e AWQ 5bpw.",
        "cost": "Runtime mais completo; roda os gates 6, 7, 9 e 11.",
    },
    {
        "name": "mlx-dspark", "arms": "P–S", "tag": "drafters DSpark/DFlash2",
        "goal": "Especular no decode com checkpoints rascunho separados (DSpark, DFlash2), preservando o prefix cache.",
        "how": "Corpo 8-bit mais um drafter dedicado que propõe tokens para o alvo verificar; cache quente ~1,0 mantido.",
        "cost": "Gate 8 PASSA (decode +90%/+154% vs baseline), mas o pico (S 38 @32K) fica abaixo do MTPLX e é 8-bit.",
    },
    {
        "name": "MTPLX", "arms": "V, Y, Z", "tag": "forge, maior decode",
        "goal": "Forjar modelo mais cabeças MTP com receita de quant própria para o maior decode sustentado.",
        "how": "Pipeline de forge com cache Turbo e MTP; um modelo de geração por daemon.",
        "cost": "Checkpoints não verificados (flag --unsafe); serve um modelo por vez.",
    },
]

# Comparação qualitativa das quantizações: o alvo de cada uma e o custo.
QUANT_PROFILES = [
    {
        "name": "MLX 8-bit", "bpw": "8.0", "runtime": "mlx-serve / mlx-dspark",
        "goal": "Qualidade próxima do fp como referência.",
        "cost": "Maior footprint; decode moderado. Base dos baselines.",
    },
    {
        "name": "GGUF Q4/Q6/Q8", "bpw": "4.5–8.5", "runtime": "llama.cpp",
        "goal": "Escada de tamanho contra qualidade no ecossistema GGUF.",
        "cost": "k-quants no Metal; decode mais lento aqui. Q4 é o portão para Q6/Q8.",
    },
    {
        "name": "AWQ 5bpw", "bpw": "5.0", "runtime": "oMLX",
        "goal": "Quant activation-aware: boa qualidade a 5 bpw, compatível com MTP.",
        "cost": "Tamanho médio; base do gate de MTP (K/L) e do SpecPrefill.",
    },
    {
        "name": "oQ8e 8.6bpw", "bpw": "8.6", "runtime": "oMLX",
        "goal": "Fidelidade de produção no M4 com MTP (estilo exl 8-bit).",
        "cost": "Grande, mas promovido no Gate 9 (braço T).",
    },
    {
        "name": "oQ4e 4.7bpw", "bpw": "4.7", "runtime": "oMLX",
        "goal": "Menor quant do oMLX, para parear com o DFlash2.",
        "cost": "No teste rodou cache-off; o prefill domina o tempo total (Gate 11 reprovado).",
    },
    {
        "name": "MTPLX 4-/8-bit", "bpw": "4.5 / 8.0", "runtime": "MTPLX",
        "goal": "Receita co-desenhada com as cabeças MTP: Speed 4-bit, Quality 8-bit.",
        "cost": "Máximo decode; checkpoints não verificados. Y/Z ainda em medição.",
    },
]

# Glossário curto dos gates (eliminatórios; ver plan.md para os limiares completos).
GATES_GLOSSARY = [
    {"gate": "1 · Correção do cache", "desc": "Reaproveita o prefixo certo: hit >=0,95 idêntico; sem reuso após mutação."},
    {"gate": "2 · Latência", "desc": "Cache dá >=5x no tempo quente; TTFT reflete só o sufixo novo."},
    {"gate": "3 · Estabilidade", "desc": "Sem crash/corrupção; swap <=0,5GB; RAM <=80GB; 20 tool turns corretos."},
    {"gate": "4 · MTP", "desc": "MTP reduz o tempo total sem baixar cache hit nem mudar o resultado."},
    {"gate": "5 · Q6/Q8", "desc": "Só roda se o Q4 passar; adota Q6/Q8 se recuperar falha ou ganho de qualidade."},
    {"gate": "6 · SpecPrefill", "desc": "M ou N reduz TTFT >=20% vs L em 16K e 32K, mantendo correção."},
    {"gate": "7 · ANE", "desc": "O reduz TTFT >=5% vs J com programas ANE realmente compilados."},
    {"gate": "8 · DSpark/DFlash2", "desc": "Decode +25%/+15% e tempo total +10% vs Q, com equivalência greedy."},
    {"gate": "9 · oQ8e", "desc": "T vs U sem crash; promove T se a diferença for <5%."},
    {"gate": "10 · MTPLX", "desc": "Carrega e roda sem perda funcional; cache, MTP ativo e aceitação confirmados."},
    {"gate": "11 · oQ4e+DFlash", "desc": "X só permanece se cortar >=10% no tempo total mediano vs W."},
]

# Headline gate verdicts (editorial; edit as gates resolve). state in
# {"pass","fail","control","running","pending"}.
VERDICTS = [
    {"gate": "Gate 9 — oQ8e", "arm": "T", "state": "pass",
     "note": "T promovido (produção M4); U só controle, sem vantagem >5%."},
    {"gate": "Gate 10 — MTPLX", "arm": "V", "state": "pass",
     "note": "Melhor decode 32K; tool loop 2/3 com prompt corrigido."},
    {"gate": "Gate 11 — oQ4e+DFlash", "arm": "X", "state": "fail",
     "note": "DFlash2 +14-24% decode, mas sem 10% de tempo total (cache-off)."},
    {"gate": "MTP gate — AWQ5", "arm": "L", "state": "pass",
     "note": "L vence K em tempo total; MTP aceitação ~0,8; tool loop 2/3."},
    {"gate": "Gate 6 — SpecPrefill", "arm": "M/N", "state": "fail",
     "note": "Corta TTFT frio ~-55%, mas zera o cache quente (hit 0%); TTFT quente 6-17x pior que L. Nenhum avança."},
    {"gate": "Gate 7 — ANE", "arm": "O", "state": "blocked",
     "note": "Bloqueado: 'Private ANE procedure-bank compiler is unavailable' neste build do omlx. Kernels da ANE não compilam. Externo, não corrigível na campanha."},
    {"gate": "Gate 8 — DSpark/DFlash2", "arm": "R/S", "state": "pass",
     "note": "Especulação entrega: decode +90%/+154% e tempo total -57%/-70% vs Q; tool loop 2/3. Mas o pico (S 38 @32K) fica abaixo do MTPLX (44,5) e é 8-bit."},
    {"gate": "MTPLX Quality — Y/Z vs Speed", "arm": "Y/Z", "state": "control",
     "note": "Speed ~23-31% mais rápido no decode. Entre Quality, Z(fp16) domina Y(8-bit): mesmo decode, tool loop 3/5 vs 1/5. Quality só por fidelidade (não medida)."},
    {"gate": "Teto 262K — decode", "arm": "L/T/S vs V/Y", "state": "pass",
     "note": "No máximo nativo (262K) o MTP do MTPLX colapsa: decode V 6,1 / Y 8,7 tps. oMLX (L 15,4 / T 14,1) e dspark/DFlash2 (S 14,2) seguram ~14-15 tps. Causa: o verify do MTP re-lê o KV de 262K por passo; o DFlash2 não escala assim. Veredito de velocidade no teto: oMLX e dspark; MTPLX perde a vantagem que tinha até 128K."},
    {"gate": "Teto 262K — cache", "arm": "L/T/S/V/Y", "state": "pass",
     "note": "Todos reusam prefixo no teto: identical ~1,0, append 0,95-1,0, tool_turn 0,99-1,0; middle_mutation parcial (0,38-0,49). CONFIRMADO por isolamento de variável: o tool_turn do MTPLX que zerava a 128K/cap 48G reusa 0,99 a 128K/cap 100G (mesma ordem pior-caso) -> o miss era sub-provisão do session-bank, não ordem. Regra: dimensione o cap por-sessão p/ KV do contexto + pegada de tool (48G é pouco já a 128K; 100G basta a 262K)."},
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
    {"stage": "SpecPrefill 32K (Gate 6) — reprovado", "status": "done"},
    {"stage": "ANE 16K/32K (Gate 7) — bloqueado (compilador ANE ausente)", "status": "blocked"},
    {"stage": "mlx-dspark smoke + 8K/32K + tool loop (Gate 8) — pass", "status": "done"},
    {"stage": "cache 65K", "status": "done"},
    {"stage": "cache 128K (L/T/V/Y/S)", "status": "done"},
    {"stage": "native 262K (L/T/V/S full, Y parcial)", "status": "done"},
    {"stage": "tool-loop survivors", "status": "pending"},
    {"stage": "confirmatório tool_turn V@128K/cap 100G", "status": "pending"},
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
