# 2026-08-31 — Qwen3.8-Flash-Next no M4 Max: campanha dedicada

> **Status:** aberta. O smoke inicial (velocidade + cache) já rodou como a Trilha D/R5 da
> campanha `qwen3.8-prefix-cache` (ver [runtime-refresh R5](../qwen3.8-prefix-cache/plan-runtime-refresh.md#r5--resultado-2026-08-31)).
> Esta campanha aprofunda: build certo + qualidade de agente. Research e procedência completas em
> [references.md](references.md) (o card do modelo, consolidado aqui).

## Por que uma campanha própria

Flash-Next é modelo novo (MoE 125B-A6B, arquitetura "Qwen4"), não uma variante de runtime. O
smoke R5 respondeu "o runtime-refresh achou um modelo mais rápido?" (sim). Falta o veredito
profundo: qual build, e se a qualidade desloca a densa 27B em agente (o gate que deu NO-GO no 27B).

## O que já sabemos (do smoke R5, oMLX 0.6.4 + build Jundot oQ4e)

- **Mais rápido que a densa** em todo contexto: decode ~40 @32K, ~33 @128K, ~27 @256K (dense
  a 256K colapsava para ~7-14). Cache reusa `tool_turn` até 0.993 @256K (o session-bank do MTPLX não).
- **Cabe até 256K nativo sem swap** COM o setting `qwen4_ple_ssd_offload: true` (PLE/n-gram em mmap
  no SSD → residente 99.6GB → 69.6GB). Sem ele, satura a 32K. Custo: ~15% decode (paginação).
- Dados: `results/refresh-flashnext-*.jsonl`.

## Perguntas em aberto

1. **Build certo:** o `ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit` (75GB, n-gram mmap por
   design, ~78 tok/s com MTP por terceiro) supera o oQ4e (106GB, ~40 com offload) em decode e folga?
2. **Prefill:** o offload de n-gram no oMLX custa prefill (PR #3235 aberta). O MTPLX pack ou a
   llama.cpp GGUF (`--override-tensor ...=CPU`) dão prefill melhor?
3. **Qualidade (o gate decisivo):** Flash-Next passa o **Terminal-Bench** acima do 27B denso?
4. **Cadeias longas:** a fraqueza declarada (declara "done", não gera) aparece no T-Bench de trilha longa?
5. **Veredito:** desloca o 27B denso e os front-runners do runtime-refresh?

## Fases

1. Baixar e rodar o build **ddalcu MLX-Serve** — cache_probe 32K/128K/256K, A/B decode vs o oQ4e.
2. Comparar caminhos de cache/prefill: oMLX vs MTPLX pack vs llama.cpp GGUF.
3. **Terminal-Bench** (do driver com Docker, mesmo protocolo do 27B) — o gate de qualidade.
4. Veredito por pergunta.

## Gates

- Disco antes do pull ([[check-disk-before-model-downloads]]).
- Suporte `qwen4_exp`: MTPLX ≥2.10.0, oMLX ≥0.6.4, llama.cpp mainline (PR #27742). mlx-dspark 0.17.2 NÃO suporta.
- Correção é eliminatório; **qualidade (T-Bench) é o gate decisivo** (foi o NO-GO do 27B).

## Saídas

- Distilados em `results/` (≤ ~1 MB/arquivo); logs crus em `logs/` (ignorados pelo git).
- Veredito no fim deste plano. Card do modelo atualizado com os resultados.

## Veredito

Pendente. Smoke R5: mais rápido + cache melhor, mas qualidade (T-Bench) ainda não medida — promoção
condicional até lá.
