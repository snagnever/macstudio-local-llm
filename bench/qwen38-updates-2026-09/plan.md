# 2026-09-12 — Qwen: testar as atualizações de setembro

> **Status:** aberta. Campanha de teste do lote de atualizações que apareceu depois do
> refresh de 04/09 ([qwen38-flash-next/plan-refresh-20260904.md](../qwen38-flash-next/plan-refresh-20260904.md)).
> Escopo: só Qwen (Flash-Next, densa 27B, MoE 3.6). Inventário e procedência em
> [references.md](references.md); manifesto em [results/update-inventory-20260912.json](results/update-inventory-20260912.json).

## Baseline instalado (do refresh de 04/09)

- mlx-serve **26.9.1** (CLI padrão). Já traz contexto 1M e +10% decode no Flash-Next.
- MTPLX **2.11.1**.
- mlx-dspark **0.18.0**.
- oMLX **0.6.4** (estável).

Os quants do Qwen3.8 em uso estão congelados: `ddalcu/…mixed-4-8bit` (`ef5b919d`) e
`Jundot/…oQ4e-mtp` (`2615fc0e`) têm o mesmo SHA no `main` do HF. Nada a re-baixar nesse caminho.

## Deltas a testar

Ordenados por custo. P1 reusa os pesos já em disco, sem download.

| # | Delta | Baseline → candidato | Baixar? | Prioridade |
|---|---|---|---|---|
| 1 | mlx-serve runtime | 26.9.1 → **26.9.2** | Não | P1 |
| 2 | MTPLX runtime | 2.11.1 → **2.11.2** | Não | P1 |
| 3 | Config de 1M no mlx-serve (feature já na 26.9.1) | — | Não | P1 |
| 4 | oMLX runtime | 0.6.4 → **0.7.0.dev2** | Não | P2 |
| 5 | Trio 27B MTPLX (só `mtplx_runtime.json` mudou em 03/09) | re-pull do runtime json | Parcial | P2 |
| 6 | DFlash2 densa 27B (`incoai/Qwen3.8-27B-DFlash2`, GGUF `z-lab`) | draft head novo | Sim | P3 |
| 7 | ddalcu Qwen3.6-35B-A3B-MLX-Serve-4bit (08/09) | quant MoE 3.6 nova | Sim | P3 |

O que já é sabido e **não** entra: o +10% de decode e o 1M já estão na 26.9.1 instalada. Não
são delta. Qwen4 não saiu.

## O que cada delta declara (a validar, não a assumir)

- **26.9.2:** speculative decoding chega à velocidade cheia já na 1ª request (antes ~15ª); draft
  por shortlist; `--max-mtp-ctx`; `--prefix-cache-disk` (conversa longa de Flash-Next no SSD).
  Parte dos ganhos usa kernels NAX de M5 e **não** se aplica ao M4 Max.
- **MTPLX 2.11.2:** guard de memória recusa antes do swap em máquina de 128 GB; visão no Flash-Next.
  A rota flash-decoding verify é gated para M5+; o M4 Max não a usa.
- **oMLX 0.7.0.dev2:** +8–20% de prefill no Qwen3.8 com PLE via SSD. É pré-release.

## Protocolo

Harness existente [cache_probe.py](../qwen3.8-prefix-cache/scripts/cache_probe.py). Base HTTP
com sufixo `/v1` (sem ele, a tokenização falha com `content is required`). ID real via `/v1/models`.

- Contexto: 32768 para todos os deltas; mais 131072 e 262144 no Flash-Next (P1/P2).
- Cenários: `cold`, `identical`, `append`, `tool_turn`. Adicionar `middle_mutation` no P1.
- Repetições: **3 por cenário** (uma rep é smoke, não sustenta ganho). Temperatura 0, top-p 0.95,
  top-k 20, reasoning xhigh, limite 4096 tokens.
- Um knob por rodada ([[isolate-the-variable-when-measuring]]). Reprobar o baseline instalado na
  mesma sessão antes de declarar ganho ([[runtime-gains-stale-baselines]]).
- Coletar telemetria RAM/swap/temperatura (faltou no refresh de 04/09).

### Troca de versão

Ambientes isolados em `~/.local/opt/qwen38/{mlx-serve-v26.9.2,mtplx-v2.11.2,omlx-v0.7.0.dev2}`,
preservando os instalados. CLI padrão via symlink em `~/.local/bin/`. Rollback: restaurar o
symlink para `mlx-serve-v26.9.1` / `mtplx-v2.11.1` / oMLX 0.6.4. Verificar o arquivo baixado
contra o SHA256 publicado antes de ativar.

## Gates

- **Disco antes de qualquer pull** ([[check-disk-before-model-downloads]]): rodar `df -h`; o volume
  de boot já chegou a 0 livre. Vale para os itens 6 e 7.
- **Correção é eliminatória; velocidade sozinha não promove.** Um build que muda pesos ou qualidade
  (itens 6 e 7) passa pelo **Terminal-Bench** antes de qualquer veredito — foi o gate que deu NO-GO
  na densa 27B ([[qwen38-27b-nogo-verdict]]).
- P1/P2 são só runtime/config sobre os mesmos pesos: o gate é decode/prefill/cache + estabilidade,
  não qualidade.

## Fases

1. **P1 (sem download):** bump 26.9.2, bump MTPLX 2.11.2, config de 1M. Cada um isolado, A/B contra
   o baseline instalado. Saída: `results/p1-*.jsonl`.
2. **P2:** oMLX 0.7.0.dev2 — A/B isolado do PLE-SSD (prefill). Re-pull do runtime json do trio 27B.
3. **P3 (com download, atrás do gate de disco + T-Bench):** DFlash2 27B e ddalcu 3.6-35B.
4. **Veredito por delta:** promover, descartar ou adiar.

## Saídas

- Distilados em `results/` (≤ ~1 MB/arquivo); logs crus em `logs/` (ignorados pelo git).
- Scores canônicos por modelo continuam no submódulo `tools/local-llm-bench/results/`.
