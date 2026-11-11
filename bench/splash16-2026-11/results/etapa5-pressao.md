# Task 5: Pressão de memória (2026-11-07/08)

**A 1.6.0 passa e fica melhor que a 1.5.0 sob `--max-memory 64G`.** Nenhum gap passou de 2.5 s na 1.6.0. A 1.5.0 teve 13 gaps acima de 5 s, com máximo de 48.8 s. A 1.6.0 fez cerca de 30% mais requests no mesmo tempo.

Carga: `serving_load.py churn` de 15 min, 3 sessões, contexto 131072, `--max-memory 64G`, ordem `k2f`, `k2g`, `k2g`, `k2f`. As quatro posições subiram com 64G (`MEM-FINAL 64G`). Resumo por rodada: `scripts/summarize_load.py results/churn-<run>.jsonl`.

## Resultado por run

| run | release | requests | sem resposta | maior gap | p99 gap | gaps > 5 s | TTFT mediano | decode mediano (cliente) | prefill (servidor) | decode (servidor) | rodadas |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `150-r1` | 1.5.0 | 167 | 0 | 36.2 s | 0.52 s | 6 | 10.4 s | 40.3 | 510 | 96.9 | 62 |
| `160-r1` | 1.6.0 | 217 | 2 (400) | 2.5 s | 0.48 s | 0 | 6.1 s | 42.6 | 686 | 101.3 | 75 |
| `160-r2` | 1.6.0 | 217 | 2 (400) | 1.1 s | 0.48 s | 0 | 7.0 s | 41.0 | 686 | 100.7 | 75 |
| `150-r2` | 1.5.0 | 163 | 0 | 48.8 s | 0.50 s | 7 | 11.3 s | 37.6 | 495 | 96.3 | 57 |

Throughput em tok/s. Prefill e decode do servidor vêm de `metrics` no `/status` final. Nenhum run teve `capacity_failures` nem `metal_failures`.

## Gate de stall

O gate G4 pede maior gap ≤ 10 s, p99 ≤ 5 s e todos os requests respondidos.

- **1.5.0:** falha nos dois runs, pelo maior gap (36.2 s e 48.8 s).
- **1.6.0:** o script marca `stall=fail` nos dois runs por causa de 2 respostas 400 `context_length_exceeded` na rodada 75. O cliente aumenta o prompt a cada rodada. A 1.6.0 andou mais rápido e chegou ao limite de 131072 tokens antes do fim dos 15 min. A 1.5.0 parou na rodada 57–62 e não chegou ao limite. Os gaps da 1.6.0 passam no gate.

## Experts em stream

| release | slots no store | memória do store | PLE no SSD |
|---|---|---:|---:|
| 1.5.0 | 21859 de 24576 (88%) | 55501 MiB | 27465 MiB, cache de 511 MiB |
| 1.6.0 | 21967 de 24576 (89%) | 55775 MiB, store de 56615 MiB | 27465 MiB, cache de 237 MiB |

As duas releases deixam cerca de 11% dos experts fora da memória. A 1.6.0 leu cerca de 235 GB do SSD por run. A 1.5.0 leu cerca de 765 GB, 3.2 vezes mais.

## `memory_governor` e `decode_gap_causes` (só 1.6.0)

`memory_governor` no fim do `160-r1`: limite 64 GiB, 68.70 GB cobrados, folga de 20 MB, `denied_reservations` 3842, `system_pressure` normal.

| conta | bytes atuais |
|---|---:|
| `experts` | 59.37 GB (floor = cap) |
| `fixed` | 7.33 GB |
| `states` | 1.39 GB |
| `hot_kv` | 0.41 GB, 264 shrinks |
| `kv` | 0.21 GB |
| `kv_staging` | 0, 12 shrinks |

| causa do gap | `160-r1` gaps / ms | `160-r2` gaps / ms |
|---|---|---|
| `prefill_unit` | 224 / 119432 | 219 / 116272 |
| `claim_wait` | 2 / 2932 | 0 / 0 |
| `ssd_read` | 1 / 2481 | 2 / 1715 |
| `pool_release`, `replan`, `other` | 0 | 0 |

Quase todo o tempo de gap vem de prefill de outra sessão intercalado com o decode. A espera por memória (`claim_wait`) quase não aparece aqui, ao contrário do `k2c2LL` da Task 4.

## Conclusão

- Para a regra "Trocar o launcher", a Task 5 **passa**: a 1.6.0 não tem stall e responde a todos os requests dentro do contexto.
- A 1.5.0 trava o decode por até 49 s sob 64G. Esse problema sai na 1.6.0.
- Ruling: as respostas 400 da 1.6.0 vêm do gerador de carga, que passa do contexto, e não contam como falha do servidor.
