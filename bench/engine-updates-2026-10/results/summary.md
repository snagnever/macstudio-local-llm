# Engines atualizadas 2026-10 — resumo

**Flash-Next: o n2 (mlx-serve 26.10.1 + iQ-MLX-4.7bpw) continua como driver diário; nenhum runtime atualizado
chega a 0.97 × o `T_turno` dele. Qwen3.8-27B: o oMLX 0.7.0 (oQ8e-mtp) lidera entre os braços que passam nos
gates, 9% à frente do mlx-serve 26.10.1 a 32K e 32% a 128K.**

Rig: M4 Max 128 GB, 2026-10-07 e 2026-10-08. Sem leitura de qualidade.

## Flash-Next

| braço | runtime | `T_turno` 32K | `T_turno` 128K | resultado |
| --- | --- | ---: | ---: | --- |
| **n2** | mlx-serve 26.10.1 | **8.2 s** | **8.8 s** | referência; passa em tudo |
| o1 | oMLX 0.7.0 | 10.1 s | 12.1 s | passa; 1.23× / 1.38× o n2 |
| m1 | MTPLX 2.12.2 | 52.7 s | HTTP 507 | sem reuso de cache; teto de 114 688 tokens |
| m1b | MTPLX 2.12.2 + limite 96G | 10.4 s | HTTP 507 | reuso só no `tool_turn` |
| d1 | ds4 upstream | 12.6 s (gate) | — | decode 53.5 tok/s < 70: fora |

256K: n2 9.8 s, o1 14.5 s. 512K (n2, YaRN 2.0 + KV 8-bit): 4 de 5 cenários; o `identical` recebeu
`PrefillDoesNotFit`. Detalhe em [flashnext-summary.md](flashnext-summary.md).

## Qwen3.8-27B

| braço | runtime | `T_turno` 32K | `T_turno` 128K | gates |
| --- | --- | ---: | ---: | --- |
| **o27** | oMLX 0.7.0 | 18.0 s | 29.8 s | passa nas duas bandas |
| s27 | mlx-dspark 0.20.3 + DFlash2 | 16.9 s | 25.0 s | falha `append` a 32K (hit 0.87) |
| r27 | mlx-serve 26.10.1 + DFlash2 | 19.7 s | 44.0 s | falha needle a 128K (1 de 39) |
| m27 | MTPLX 2.12.2 | 17.8 s | 834.2 s | sem reuso de cache a 128K |

A parte 27B fechou em 128K por decisão do usuário. Detalhe em [27b-summary.md](27b-summary.md).

## Achados que valem para os dois modelos

- **MTPLX 2.12.x no M4 Max 128 GB:** o memory guard reescrito no 2.12.1 descarta o prefixo reusável
  (`prefill_admission_shed`) e o turno re-prefila tudo. No Flash-Next isso acontece já a 32K; no 27B, a 128K.
  O teto de contexto do Flash-Next continua em 114 688 tokens, mesmo com `MTPLX_MEMORY_LIMIT_BYTES=96G`.
- **oMLX 0.7.0** é a maior melhora da rodada: Flash-Next de 13.5 / 15.0 s (0.7.0.dev2) para 10.1 / 12.1 s, e
  lidera o 27B.
- **mlx-serve com drafter DFlash (27B)** perde decode com contexto longo (37.0 → 15.5 tok/s de 32K a 128K); com a
  MTP nativa do Flash-Next ele segue o mais rápido.
- **ds4 upstream** suporta o Flash-Next com GGUF próprio (`qwen38-q4k`, 165 GiB) e reusa cache com
  `--kv-disk-dir`, mas o decode (53.5 tok/s) fica longe do n2.

## Instalação e pesos

[install-runtimes.md](install-runtimes.md), [weights.md](weights.md), [etapa0-smoke.md](etapa0-smoke.md),
[etapa0-27b-smoke.md](etapa0-27b-smoke.md).

## O que não foi medido

- Qualidade (HumanEval, tool-calling, Terminal-Bench) em qualquer braço.
- 27B acima de 128K.
- mlx-vlm 0.7.6, LM Studio 0.4.25, llama.cpp b11461 e o fork ivanfioravanti do ds4.
- O modo DSpark do mlx-dspark no 27B (o braço rodou em DFlash para casar com o r27).
- A causa do teto de 114 688 tokens do MTPLX não mudar com o limite de 96G (não li o código do MTPLX).
