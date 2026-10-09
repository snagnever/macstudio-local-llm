# Etapa 0 — smoke 8K do Flash-Next e gate do d1

`cold → identical → tool_turn`, 1 rep, `temperature=1.0`, reasoning `xhigh`, limite 4096 tokens. Os quatro
braços carregaram e responderam sem erro HTTP.

| braço | runtime | cold decode / TTFT | identical decode / TTFT / hit | tool_turn decode / TTFT / hit | needles | MTP | wired pico |
| --- | --- | --- | --- | --- | --- | --- | --- |
| n2 | mlx-serve 26.10.1 | 84.7 / 3.37 s | 88.9 / 0.13 s / 0.99 | 80.4 / 1.62 s / 0.71 | 9/9 | aceitação 0.613 (log) | 82.5 GB |
| m1 | MTPLX 2.12.2 | 80.2 / 3.92 s | 79.4 / 0.08 s / 1.00 | 80.3 / 1.67 s / 0.72 | 6/9 (tool_turn truncado) | `/metrics`: 0.04–0.06 | 93.6 GB |
| o1 | oMLX 0.7.0 | 61.5 / 5.00 s | 68.7 / 0.09 s / 1.00 | 63.7 / 2.32 s / 0.72 | 9/9 | log `accept=x/y` por request | 80.6 GB |
| d1 | ds4 upstream | 53.2 / 4.9 s | 53.0 / 1.6 s / 0.75 | 56.8 / 2.9 s / 0.54 | 9/9 | 86.8% (`--mtp-timing`) | 84.7 GB |

## Gate do d1 (32K, 1 rep)

`T_turno` 12.6 s, cold TTFT 41.4 s, hit 0.97 / 0.94 / 0.94, decode **53.5 tok/s**, needles ok, wired 86.0 GB,
swap 0. O decode fica abaixo dos 70 tok/s do gate: **o d1 sai das bandas**. Contra o fork de setembro
(decode ~40 tok/s a 32K, hit 0 sem `--kv-disk-dir`), o upstream ganha ~33% de decode e reusa cache.

## Notas

1. **m1 truncou o `tool_turn`** (`finish_reason=length` em 4096 tokens de reasoning). O c1 fez o mesmo a 8K em 2026-09.
2. **Telemetria de MTP do MTPLX:** o harness lê de `/metrics` um valor de 0.04–0.06, que não é a taxa de
   aceitação comparável à do mlx-serve. O MTP está ligado (banner `turbo MTP`). A coluna "MTP acc" do MTPLX
   não entra na comparação.
3. **oMLX 0.7.0** expõe a aceitação só no log (`MTP[0] ... accept=4/7`); o harness não a anexa.
4. **ds4 upstream:** precisou de `MODEL_ID_PREF` no driver, porque o servidor expõe três aliases
   (`qwen3.8-flash-next`, `-chat`, `-reasoner`). Hit de 0.54 no `tool_turn` a 8K é estrutural (prefixo curto).
5. O hit de ~0.71 no `tool_turn` a 8K é estrutural nos outros braços também.

Dados: `{n2,m1,o1,d1}-8192-t1.0-smoke.jsonl`, `d1-32768-t1.0-gate.jsonl`.
