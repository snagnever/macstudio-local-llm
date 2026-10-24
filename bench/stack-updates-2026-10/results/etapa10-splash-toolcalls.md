# Etapa 10 — probe de tool calls ampliado no Splash (`k2`, `k2a`, `k2ab`) (2026-10-24)

O Task 8 deixou uma dúvida: o `k2a` respondeu sem tool call no turno 1 de 1 das 5 sessões, com `tool_choice: required`. Esta etapa repete o probe com 20 sessões de 4 turnos por penalidade, em três braços do Splash 1.4.0 com o Swift 1.5 IQ4_XS:
- `k2`: `--verify-rows all`;
- `k2a`: `auto`;
- `k2ab`: `auto` com `--kv-format bf16`.

O `tool_loop.py` passou a gravar `finish_reason` e `completion_tokens` por turno, e a resposta completa de cada turno que falha (em `logs/tool-loop/`). Comando: `toolcall-probe.sh <braço> --sessions 20 --suffix x20`. O probe limita cada turno a `max_tokens` 512.

## Resultado

| braço | `frequency_penalty` | sessões | turnos | mediana por turno | falhas de turno | falhas só na resposta final |
|---|---:|---:|---:|---:|---|---:|
| `k2` | 0 | **20/20** | **80/80** | 0.84 s | — | 0 |
| `k2a` | 0 | **20/20** | **80/80** | 0.78 s | — | 0 |
| `k2ab` | 0 | **20/20** | **80/80** | 0.74 s | — | 0 |
| `k2` | 1 | 10/20 | 44/53 | 0.92 s | 9 × turno 1, `length` | 1 |
| `k2a` | 1 | 13/20 | 60/65 | 0.95 s | 5 × turno 1, `length` | 2 |
| `k2ab` | 1 | 9/20 | 48/56 | 0.86 s | 8 × turno 1, `length` | 3 |

- Todas as 22 falhas de turno têm `finish_reason: length` e 512 tokens. O raciocínio esgotou o `max_tokens` do probe antes de chegar à tool call. O content veio vazio, e não houve tool call parcial. O Splash não ignorou o `tool_choice: required`.
- Com penalidade 1, o raciocínio do turno 1 fica mais longo e repetitivo, e por isso bate no limite com mais frequência. É o mesmo efeito da #912 no mlx-serve 26.10.3: a penalidade aditiva degrada um raciocínio longo.
- O KV bf16 (`k2ab`) não muda o resultado com penalidade 0 e não melhora com penalidade 1.

## Veredito

O Splash com o Swift 1.5 passa no probe de tool calls com penalidade 0: 60/60 sessões e 240/240 turnos nos três braços. A falha do Task 8 (1 sessão de 5, turno 1 sem tool call) foi provavelmente o mesmo corte por `max_tokens`. Aquela run não guardou a resposta, então isso não está provado. A regra de tool calls do Task 8 passa a valer para o `k2a`. Com penalidade 1, nenhum runtime testado serve um raciocínio longo sem degenerar. Os clientes devem mandar `frequency_penalty` 0.

## Próximo passo

A campanha [`bench/splash-longctx-2026-10`](../../splash-longctx-2026-10/plan.md) mede o Splash até 1M, com qualidade e Terminal-Bench 2.1. O probe de lá roda com `--max-tokens 2048`.
