# Task 5: Pressão de memória (2026-11-12)

**A 1.6.1 passa e fica melhor que a 1.5.0 sob `--max-memory 64G`.** O maior gap da 1.6.1 é de 4.9 s, e nenhum gap passa de 5 s. A 1.5.0 tem 11 gaps acima de 5 s, com máximo de 87.8 s. A 1.6.1 faz 225 requests por run, 35% mais que a 1.5.0 no mesmo tempo.

Carga: `serving_load.py churn` de 15 min, 3 sessões, contexto 131072, `--max-memory 64G`, PLE `auto`, ordem `k2f`, `k2h`, `k2h`, `k2f`. Fila `logs/chain-t45.sh`, das 07:28 às 08:41 (relógio do rig). As quatro posições sobem com 64G (`MEM-FINAL 64G`). Resumo por rodada: `bench/splash16-2026-11/scripts/summarize_load.py results/churn-<run>.jsonl`.

## Resultado por run

| run | release | requests | sem resposta | maior gap | p99 gap | gaps > 5 s | TTFT mediano | decode mediano (cliente) | prefill (servidor) | decode (servidor) | rodadas |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `150-r1` | 1.5.0 | 168 | 0 | 60.8 s | 0.47 s | 4 | 9.4 s | 40.9 | 510 | 95.8 | 61 |
| `161-r1` | 1.6.1 | 225 | 3 (400) | 4.5 s | 0.49 s | 0 | 6.3 s | 44.4 | 718 | 106.0 | 75 |
| `161-r2` | 1.6.1 | 225 | 3 (400) | 4.9 s | 0.48 s | 0 | 5.8 s | 46.7 | 721 | 100.5 | 75 |
| `150-r2` | 1.5.0 | 165 | 0 | 87.8 s | 0.46 s | 7 | 9.8 s | 40.1 | 503 | 99.1 | 66 |

Throughput em tok/s. Prefill e decode do servidor vêm de `metrics` no `/status` final. Nenhum run tem `capacity_failures` nem `metal_failures`. O swap fica em 1.69 GB do início ao fim nos quatro runs, e o wired máximo fica entre 71.6 e 72.1 GB.

## Gate de stall

O gate G4 pede maior gap ≤ 10 s, p99 ≤ 5 s e todos os requests respondidos.

- **1.5.0:** falha nos dois runs, pelo maior gap (60.8 s e 87.8 s).
- **1.6.1:** o script marca `stall=fail` nos dois runs por causa de 3 respostas 400 (`prompt exceeds the context window`, `context_length_exceeded` no log do servidor) na rodada 75. O cliente aumenta o prompt a cada rodada. A 1.6.1 chega ao limite de 131072 tokens antes do fim dos 15 min, como a 1.6.0 na splash16. A 1.5.0 para nas rodadas 61 e 66 e não chega ao limite. Os gaps da 1.6.1 passam no gate.

## Comparação com a splash16

| release | maior gap | gaps > 5 s | requests por run |
|---|---:|---:|---:|
| 1.5.0 (splash16) | 36.2 e 48.8 s | 6 e 7 | 167 e 163 |
| 1.6.0 (splash16) | 2.5 e 1.1 s | 0 | 217 |
| 1.5.0 (esta campanha) | 60.8 e 87.8 s | 4 e 7 | 168 e 165 |
| 1.6.1 | 4.5 e 4.9 s | 0 | 225 |

O maior gap da 1.6.1 fica acima do da 1.6.0, mas abaixo do limite de 10 s. As causas estão na tabela de `decode_gap_causes`.

## Experts em stream

| release | slots no store | memória do store | PLE no SSD | leitura do SSD por run |
|---|---|---:|---:|---:|
| 1.5.0 | 21859 de 24576 (88%) | 55501 MiB | 27465 MiB, cache de 511 MiB | 841 e 842 GB |
| 1.6.1 | 21924 de 24576 (89%) | 55666 MiB, store de 56506 MiB | 27465 MiB, cache de 237 MiB | 258 e 246 GB |

As duas releases deixam cerca de 11% dos experts fora da memória. A 1.5.0 lê do SSD 3.3 vezes mais que a 1.6.1, a mesma relação da splash16.

## `memory_governor` e `decode_gap_causes` (só 1.6.1)

`memory_governor` no fim do `161-r1`: limite 64 GiB, 68.66 GB cobrados, folga de 64 MB, `denied_reservations` 4974, `system_pressure` normal. No `161-r2`: folga de 97 MB, `denied_reservations` 4910. Nenhum claim fica esperando no fim.

| conta | bytes atuais no `161-r1` |
|---|---:|
| `experts` | 59.25 GB (floor = cap) |
| `fixed` | 7.44 GB |
| `states` | 1.03 GB |
| `kv` | 0.52 GB |
| `hot_kv` | 0.41 GB, 281 shrinks |
| `kv_staging` | 0, 14 shrinks |

| causa do gap | `161-r1` gaps / ms | `161-r2` gaps / ms |
|---|---|---|
| `prefill_unit` | 263 / 148663 | 232 / 130791 |
| `claim_wait` | 2 / 4960 | 0 / 0 |
| `ssd_read` | 4 / 3125 | 4 / 8632 |
| `pool_release`, `replan`, `other` | 0 | 0 |

- **Gaps:** quase todo o tempo de gap vem de prefill de outra sessão intercalado com o decode. Esse é o mesmo padrão da 1.6.0.
- **`ssd_read`:** no `161-r2`, 4 gaps somam 8.6 s, cerca de 2 s cada. Esses gaps explicam o maior gap de 4.9 s junto com o prefill intercalado.
- **`claim_wait`:** o `161-r1` tem 2 gaps de espera por memória, com 2.5 s em média. No TTFT, 57 e 59 requests têm `claim wait` maior que 0 no log de boot, com máximo de 1.9 s e 1.0 s. O log do `161-r1` tem 2 linhas `pending`, e o do `161-r2` tem 0.

## Conclusão

- Para a regra "Trocar o launcher", a Task 5 **passa**: a 1.6.1 não tem stall e responde a todos os requests dentro do contexto.
- A 1.5.0 trava o decode por até 88 s sob 64G. A 1.6.1 não tem esse problema.

## Desvios

- **Respostas 400:** vêm do gerador de carga, que passa do contexto na rodada 75. Elas não contam como falha do servidor. A splash16 tomou a mesma decisão para a 1.6.0.
- **Sonda curta:** o `summarize_load.py` imprime `verdict=sem_sonda`, porque o modo `churn` não roda as sondas. A splash16 tem o mesmo caso.

Fontes: [churn-150-r1.jsonl](churn-150-r1.jsonl), [churn-161-r1.jsonl](churn-161-r1.jsonl), [churn-161-r2.jsonl](churn-161-r2.jsonl), [churn-150-r2.jsonl](churn-150-r2.jsonl). Referência da 1.6.0: [etapa5-pressao.md da splash16](../../splash16-2026-11/results/etapa5-pressao.md).
