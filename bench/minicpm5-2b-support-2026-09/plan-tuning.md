# Plano de tuning do s1 — ngram, KV misto e saída guiada (2026-09-16)

Objetivo: validar as recomendações dos docs do `mlx-optiq` para o papel de suporte do
MiniCPM5-2B-OptiQ-4bit (s1), com foco em **tokens** e **cache**, e checar o efeito no driver.
Curto: ~25 min no total, 1 rep por ponto.

## Fases

| # | o que | comparação | métrica | custo |
|---|---|---|---|---|
| 1 | **n-gram speculative** (solo) | fp16 sem ngram × `--ngram-draft 16` | decode tok/s em prompt genérico e em prompt "copy-heavy" | ~5 min |
| 2 | **saída guiada** | classificação livre × `guided_choice` | acerto da classificação (5/5?) | ~1 min |
| 3 | **KV misto** | fp16 × `--kv-config` (plano do quant) a 8K/32K | TTFT, decode, RSS | ~4 min |
| 4 | **efeito no driver** | B@32K atual (16,45 s) × B@32K com `--ngram-draft 16` | `T_turno` do driver | ~15 min |

## Hipóteses

1. `--ngram-draft 16` dá 1,3–1,6× no decode quando a saída copia o contexto (título/commit/
   reescrita); pouco ganho em prosa nova.
2. `guided_choice` elimina o erro de classificação da Etapa 3 (informação vs pedido).
3. `--kv-config` misto não custa decode a 8K/32K (docs: ±2% vs fp16) e encolhe o KV a longo
   contexto; uniforme 8-bit já mostramos que piora o prefill a 126K.
4. O n-gram muda pouco o `T_turno` do driver (ele muda o decode do **suporte**, não do driver).

## Critério de parada

- Se (1) não ganhar ≥20% no copy-heavy, não vale habilitar por padrão.
- Se (2) ficar <5/5, revisar a lista de classes.
- Se (3) perder >5% no decode, manter fp16 no papel curto.

Script: `scripts/run-s1-tuning.sh`. Resultados: `results/etapa-tuning*.jsonl` + `results/etapa-tuning.md`.
