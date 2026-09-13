# Etapa 0 — smoke a 8K (2026-09-13)

Os 4 candidatos, `cold → identical → tool_turn`, 1 rep, perfil do vendor (`temperature=1.0`).
Fixture `audit_retrieval` a 8192 (prompt ~2.7K tokens). Smoke, não veredito.

| cand | runtime | cold decode / TTFT | identical decode / TTFT / hit | tool_turn decode / TTFT / hit | correção | wired pico | swap Δ |
|---|---|---|---|---|---|---:|---:|
| c1 ddalcu mixed-4/8 | mlx-serve 26.9.2 | 59.9 / 3.56 s | 71.2 / 0.08 s / 1.00 | 51.3 / 1.72 s / 0.72 | tool_turn falhou (ver nota) | 80.8 GB | 0 |
| c2 oQ4e | oMLX 0.6.4 | 40.2 / 7.47 s | 45.5 / 1.87 s / 0.75 | 39.7 / 4.27 s / 0.54 | tool_turn truncado | 93.5 GB | 0 |
| c3 oQ4e | oMLX 0.7.0.dev2 | 56.3 / 4.87 s | 68.8 / 1.78 s / 0.75 | 60.8 / 3.84 s / 0.54 | ok | 82.2 GB | 0 |
| c4 MTPLX Opt-Speed | MTPLX 2.11.2 | 61.1 / 14.6 s | 65.8 / 6.39 s / 1.00 | 68.4 / 75.0 s / 1.00 | ok | 93.4 GB | 0 |

## Os 4 carregam — todos seguem para a Etapa A

- **c3 (dev2) não está bloqueado.** O log confirma `Qwen4-Exp PLE mode … : mmap`. Wired 82 GB contra
  93 GB do c2. O bloqueio da campanha anterior era a falta do `model_settings.json` com a flag
  `qwen4_ple_ssd_offload`, não uma mudança de schema na 0.7 (ver `c3-dev2-ple-config.md`).
- **dev2 decodifica mais rápido que a 0.6.4 no mesmo quant:** 56/69/61 contra 40/45/40 tok/s (+40–50%).
  O anúncio falava de prefill para M5; no M4 o ganho aparece no decode e no prefill (561 contra 366).
- **MTP:** c1 depth 6 + PLD, aceitação 0.545 (do log `[spec-stats]`); c4 aceitação 0.30–0.38 (JSON do `/metrics`).

## Pontos para a triagem

1. **Telemetria de cache do MTPLX não é confiável.** O c4 reporta hit 1.00 até no `cold`, mas o TTFT
   contradiz (cold 14.6 s, identical 6.4 s, tool_turn 75 s). O gate de hit ≥ 0.90 passaria o c4 por um
   número que não reflete reuso. O `T_turno` usa TTFT, então o ranking continua honesto; o gate de hit do
   c4 deve ser lido junto do TTFT quente.
2. **Hit parcial do oMLX a 8K** (identical 0.75, tool_turn 0.54) nos dois oQ4e. Prefixo curto; conferir a 32K.
3. **tool_turn de c1 e c2 a 8K:** o reasoning passou de 4096 tokens (`finish_reason=length`) — truncado,
   não miss de needle.
4. **Higiene:** a porta 8000 é compartilhada entre oMLX e MTPLX. Um candidato por vez; nunca cadeia.

Dados: `c{1,2,3,4}-8192-t1.0.jsonl`.
