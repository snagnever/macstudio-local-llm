# Task 7: Carga de agente de 4 h (2026-11-12)

**A 1.6.1 fica estável por 4 h.** A sonda curta de decode termina em 1.09 × a sonda antes da carga, então a regra de queda dá **estável**. O pool de KV chegou ao teto, então o teste exercitou a queda. As 86 sessões cumprem a tarefa, e nenhum request tem erro.

Para a regra "Trocar o launcher", a Task 7 **não mostra regressão**.

Carga: `agent_soak.sh --hours 4 --tag h161`, pares de sessões do Claude Code (tarefas c e d) com `--proxy 8686`, contexto 131072, um boot do `k2h` (Splash 1.6.1, PLE `auto`). A sonda `serving_load.py probe` roda 3 reps antes do primeiro par e depois de cada par. Fila `logs/chain-t7.sh`, das 13:19 às 17:24 (relógio do rig). O servidor do usuário na porta 8585 voltou no fim da fila.

## Resumo

As colunas da 1.6.0 e da 1.5.0 vêm da Task 7 da splash16, de 2026-11-08. Elas são referência e não dão veredito.

| métrica | `k2h`, 1.6.1 | `k2g`, 1.6.0 (splash16) | `k2f`, 1.5.0 (splash16) |
|---|---:|---:|---:|
| pares concluídos | 43 em 14642 s | 43 em 14680 s | 38 em 14624 s |
| requests | 1667 | 1791 | 1555 |
| erros HTTP | 0 | 0 | 0 |
| `task_done` | 86/86 | 85/86 | 75/76 |
| sonda antes da carga (p50) | 96.5 tok/s | 99.1 tok/s | 101.6 tok/s |
| sonda no fim (p50) | 105.5 tok/s | 90.3 tok/s | 97.8 tok/s |
| razão fim / antes | 1.09, **estável** | 0.91, estável | 0.96, estável |
| sonda mínima | 87.8 tok/s | 85.6 tok/s | 90.8 tok/s |
| maior gap da sonda | 0.05 s | 0.05 s | 0.06 s |
| prefill do servidor | 699 tok/s | 680 tok/s | 525 tok/s |
| decode do servidor | 127.5 tok/s | 125.6 tok/s | 123.0 tok/s |
| `denied_reservations` no fim | 7416 | 11203 | 71422 |
| máximo de páginas alocadas | 32512 | 22528 | – |

- **Sonda antes da carga:** as 3 reps dão 96.5, 95.8 e 103.2 tok/s. Depois dos pares, a mediana da sonda fica entre 100 e 114 tok/s. A razão acima de 1 vem de uma sonda inicial mais lenta, não de um ganho com o tempo.
- **Sessões:** nenhuma sessão tem `exit` diferente de 0. Nenhum `task_done` é falso.
- **Requests:** a 1.6.1 faz 7% menos requests que a 1.6.0 com o mesmo número de pares. As sessões são do mesmo perfil, mas o número de turnos por sessão varia de run para run.

## Por hora

A hora é a hora em que o par terminou, contada do início do soak. A hora 4 tem só o último par. `pages_cache`, `pages_free`, `denied_reservations` e `claim_wait` vêm do `/status` depois da sonda do último par da hora. O warm TTFT e o tok/s desta tabela contam como warm todo turno do modelo com `cached_tokens > 0`, como na splash16.

| hora | pares | requests | erros | warm tok/s p50 | warm TTFT p50 / p90 | sonda p50 | razão | `pages_cache` / alocadas | `pages_free` | `denied_reservations` | `claim_wait` máx | `task_done` |
|---|---:|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---|
| 0 | 10 | 404 | 0 | 95.0 | 1.1 / 10.0 s | 102.5 | 1.06 | 17151 / 17408 | 257 | 868 | 0.1 s | 20/20 |
| 1 | 10 | 379 | 0 | 92.7 | 1.2 / 10.9 s | 100.5 | 1.04 | 30335 / 30720 | 385 | 2396 | 3.6 s | 20/20 |
| 2 | 11 | 412 | 0 | 92.2 | 1.2 / 10.7 s | 113.6 | 1.18 | 32129 / 32512 | 383 | 4669 | 3.6 s | 22/22 |
| 3 | 11 | 437 | 0 | 88.0 | 1.1 / 9.8 s | 109.2 | 1.13 | 30577 / 30976 | 399 | 7249 | 4.9 s | 22/22 |
| 4 | 1 | 35 | 0 | 83.3 | 1.3 / 9.4 s | 105.5 | 1.09 | 30824 / 31232 | 408 | 7416 | 4.9 s | 2/2 |

Com a definição de warm do `claude_requests` (a mesma da Task 4), o warm TTFT p50 / p90 do soak inteiro fica em 0.91 / 2.27 s, e o warm tok/s p50 fica em 94.3. Na splash16, esses valores eram 0.90 / 2.53 s na 1.6.0 e 1.54 / 4.44 s na 1.5.0.

## O pool chegou ao teto

- `pages_free` desce a 257 já na hora 0 e volta a 257 em outros pontos do soak. As páginas alocadas sobem até 32512 na hora 2 e depois encolhem para 31232.
- As reservas negadas sobem desde a hora 0 até 7416. No fim, a folga do `memory_governor` é de 89 MB, com `system_pressure` normal.
- Com o pool no teto, a sonda não cai. O teste exercitou a condição da #644 e não reproduziu a queda.
- A 1.6.1 aloca até 32512 páginas, contra 22528 da 1.6.0. Com PLE `auto`, a tabela PLE fica no SSD e deixa mais memória para o KV.

## Espera por memória

- `claim_wait` chega a 4.9 s na hora 3. O total no fim é de 37.5 s em 1763 requests. Na 1.6.0, o máximo era 8.3 s e o total era 70.9 s.
- `decode_gap_causes` tem só `prefill_unit`: 3357 gaps, 2812 s no total. Nenhum gap vem de `claim_wait` nem de `ssd_read`.
- `capacity_failures` e `metal_failures` ficam em 0.

## Conclusão

- **Queda de decode:** estável, com razão fim / antes de 1.09. O pool chegou ao teto, então o teste exercitou a queda.
- **Contra a splash16:** a 1.6.1 conclui os mesmos 43 pares da 1.6.0 em 4 h, com warm TTFT igual e metade da espera por memória. As referências são de outro dia, então essa comparação não dá veredito.
- **Limite:** um run só, sem ordem invertida e sem controle no mesmo dia.
- Para a regra "Trocar o launcher", a Task 7 conta como **sem regressão**.

## Desvios

- **Arquivo vazio:** `k2h-131072-t1.0-soak-h161.jsonl` fica vazio, porque o `run-arm.sh` exige o arquivo. Os dados ficam em `soak-h161.jsonl`.
- **Cálculo:** o resumo foi feito ad hoc a partir dos arquivos de resultado, como na splash16. A hora de cada par vem do horário de gravação do `cc-*.json`.

Fonte: [soak-h161.jsonl](soak-h161.jsonl), `cc-soakh161p<N>-{c,d}.json` e `req-soakh161p<N>-{c,d}.jsonl`. Referência: [etapa7-agente-4h.md da splash16](../../splash16-2026-11/results/etapa7-agente-4h.md).
