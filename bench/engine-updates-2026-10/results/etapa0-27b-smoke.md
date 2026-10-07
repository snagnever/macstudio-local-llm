# Etapa 0 — smoke 8K do Qwen3.8-27B

`cold → identical → tool_turn`, 1 rep, `temperature=1.0`, reasoning `xhigh`, limite 4096 tokens. Os quatro
braços carregaram e responderam sem erro HTTP.

| braço | runtime | cold decode / TTFT | identical decode / TTFT / hit | tool_turn decode / TTFT / hit | nota |
| --- | --- | --- | --- | --- | --- |
| r27 | mlx-serve 26.10.1 + DFlash2 | 62.5 / 10.0 s | 55.0 / 0.17 s / 0.99 | 50.3 / 4.47 s / 0.71 | tool_turn truncado em 4096 |
| m27 | MTPLX 2.12.2 (pack @ 1d5087d) | 52.4 / 10.9 s | 50.5 / 0.12 s / 1.00 | 48.8 / 4.49 s / 0.72 | — |
| o27 | oMLX 0.7.0 (oQ8e-mtp) | 47.0 / 10.9 s | 49.0 / 0.25 s / 1.00 | 42.8 / 4.48 s / 0.72 | — |
| s27 | mlx-dspark 0.20.3 + DFlash2 | 47.9 / 9.8 s | 47.1 / 0.07 s / 1.00 | 42.9 / 4.19 s / 0.72 | tool_turn truncado em 4096 |

## Drafter

- **r27:** o boot log mostra `[args] drafter: …DFlash2… (block_size=4, auto)` e `[dflash] loaded 5 layers …
  block_size=8`. O drafter carregou; aceitação 0.452 no log. O par r27 × s27 isola o runtime.
- **s27:** `loading dflash engine` e calibração do cap DFlash. O `doctor` sugere DSpark (`dspark wins`), mas o
  braço fica em `--mode dflash` para casar com o r27.
- **m27 / o27:** MTP nativa. A telemetria do MTPLX via `/metrics` (0.04–0.06) não é comparável; o oMLX loga
  `accept=x/y` só no boot log.

O hit de ~0.71 no `tool_turn` a 8K é estrutural (prefixo curto).

Dados: `{r27,m27,o27,s27}-8192-t1.0-smoke.jsonl`.
