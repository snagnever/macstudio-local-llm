# Task 7: Carga de agente de 4 h (2026-11-08)

**As duas releases ficam estáveis por 4 h, e a 1.6.0 termina mais trabalho.** A sonda curta de decode não cai em nenhuma release. O pool de KV chegou ao teto nas duas, então o teste exercitou a queda da #644. No mesmo tempo, a 1.6.0 concluiu 43 pares de sessões, e a 1.5.0 concluiu 38. O warm TTFT p50 da 1.6.0 é cerca de metade do da 1.5.0.

Para a regra "Trocar o launcher", a Task 7 **não mostra regressão**. A regra já falha na Task 4.

Carga: `agent_soak.sh --hours 4`, pares de sessões do Claude Code (tarefas c e d) com `--proxy 8686`, contexto 131072, um boot por release. A sonda `serving_load.py probe` roda 3 reps antes do primeiro par e depois de cada par. Ordem: `k2g` (1.6.0) das 06:30 às 10:35, depois `k2f` (1.5.0) das 10:47 às 14:51.

## Resumo

| métrica | `k2g`, 1.6.0 | `k2f`, 1.5.0 |
|---|---:|---:|
| pares concluídos | 43 em 14680 s | 38 em 14624 s |
| requests | 1791 | 1555 |
| erros HTTP | 0 | 0 |
| `task_done` | 85/86 | 75/76 |
| sonda antes da carga (p50) | 99.1 tok/s | 101.6 tok/s |
| sonda no fim (p50) | 90.3 tok/s | 97.8 tok/s |
| razão fim / antes | 0.91, **estável** | 0.96, **estável** |
| sonda mínima | 85.6 tok/s | 90.8 tok/s |
| maior gap da sonda | 0.05 s | 0.06 s |
| prefill do servidor | 680 tok/s | 525 tok/s |
| decode do servidor | 125.6 tok/s | 123.0 tok/s |
| `denied_reservations` no fim | 11203 | 71422 |

- A sessão que falhou em cada release é um `d`, pela checagem oculta do trabalho: o par 3 no `k2g` e o par 12 no `k2f`. O `exit 1` do par no log da chain vem dessa falha. Nenhuma sessão teve `exit` diferente de 0.
- A sonda no fim tem só um conjunto de 3 reps. Nas horas 0 a 3, a mediana da sonda do `k2g` fica entre 99.8 e 101.4 tok/s, com razão de 1.01 a 1.02.

## Por hora

A hora é a hora em que o par terminou, contada do início do soak. A hora 4 tem só o último par. `pages_cache`, `pages_free`, `denied_reservations` e `claim_wait` vêm do `/status` depois da sonda do último par da hora. O warm TTFT e o tok/s vêm dos requests com prefixo em cache.

### `k2g`, 1.6.0

| hora | pares | requests | erros | warm tok/s p50 | warm TTFT p50 / p90 | sonda p50 | razão | `pages_cache` / alocadas | `pages_free` | `denied_reservations` | `claim_wait` máx | `task_done` |
|---|---:|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---|
| 0 | 10 | 399 | 0 | 86.9 | 1.1 / 10.6 s | 100.1 | 1.01 | 13960 / 14336 | 376 | 1594 | 2.2 s | 19/20 |
| 1 | 11 | 458 | 0 | 94.3 | 1.2 / 10.4 s | 101.4 | 1.02 | 19238 / 19712 | 474 | 4841 | 8.3 s | 22/22 |
| 2 | 11 | 479 | 0 | 92.8 | 1.1 / 10.1 s | 99.8 | 1.01 | 16789 / 17152 | 363 | 8415 | 8.3 s | 22/22 |
| 3 | 10 | 415 | 0 | 90.2 | 1.1 / 10.5 s | 100.2 | 1.01 | 22015 / 22272 | 257 | 10875 | 8.3 s | 20/20 |
| 4 | 1 | 40 | 0 | 94.6 | 1.3 / 9.4 s | 90.3 | 0.91 | 21806 / 22272 | 466 | 11203 | 8.3 s | 2/2 |

### `k2f`, 1.5.0

| hora | pares | requests | erros | warm tok/s p50 | warm TTFT p50 / p90 | sonda p50 | razão | `pages_cache` / alocadas | `pages_free` | `denied_reservations` | `task_done` |
|---|---:|---:|---:|---:|---|---:|---:|---|---:|---:|---|
| 0 | 9 | 372 | 0 | 88.0 | 2.1 / 12.1 s | 100.6 | 0.99 | 15103 / 15360 | 257 | 14626 | 18/18 |
| 1 | 8 | 340 | 0 | 75.7 | 2.3 / 12.6 s | 102.7 | 1.01 | 18942 / 19200 | 258 | 36000 | 15/16 |
| 2 | 10 | 392 | 0 | 86.2 | 1.9 / 13.8 s | 102.4 | 1.01 | 17407 / 17664 | 257 | 55276 | 20/20 |
| 3 | 10 | 406 | 0 | 88.7 | 1.9 / 12.2 s | 102.3 | 1.01 | 16895 / 17152 | 257 | 70027 | 20/20 |
| 4 | 1 | 45 | 0 | 97.9 | 1.4 / 11.2 s | 97.8 | 0.96 | 16383 / 16640 | 257 | 71422 | 2/2 |

A 1.5.0 não grava `ttft_parts_ms` nem `decode_gap_causes`, então a coluna `claim_wait` não existe nela.

## O pool chegou ao teto

- **1.5.0:** `pages_free` fica em 257 desde a hora 0. No fim, a folga do `memory_governor` é de 56 MB, e as reservas negadas sobem até 71422. O pool trabalhou no teto quase todo o soak.
- **1.6.0:** `pages_free` desce a 257 na hora 3, e o máximo de páginas alocadas é 22528. As reservas negadas sobem até 11203. O pool encheu, mas com cerca de 6 vezes menos reservas negadas que na 1.5.0.
- Nas duas releases, o pool encolhe e cresce de novo entre as horas: as páginas alocadas não sobem sempre. Isso mostra que as duas devolvem páginas de cache sob pressão.
- Com o pool no teto, nenhuma release teve queda de decode. O teste exercitou a condição da #644 e não reproduziu a queda neste rig, com este perfil.

## Espera por memória na 1.6.0

- `claim_wait` chega a 8.3 s na hora 1 e não passa disso. O total no fim é de 70.9 s em 1880 requests.
- `decode_gap_causes` tem só `prefill_unit`: 3705 gaps, 3143 s no total. Nenhum gap vem de `claim_wait` nem de `ssd_read`.
- Com sessões de até cerca de 60K tokens, a espera fica bem abaixo dos 30 s da Task 4, que usou duas sessões de 256K.

## Conclusão

- **Queda de decode:** estável nas duas releases, com razão fim / antes de 0.91 na 1.6.0 e 0.96 na 1.5.0. Pelas regras do plano, o resultado é **fix sem prova**: a 1.5.0 também fica estável. Ele não mostra regressão.
- **Trabalho feito:** a 1.6.0 conclui 13% mais pares e 15% mais requests em 4 h. O warm TTFT p50 cai de cerca de 2.0 s para 1.1 s, e o p90 cai de cerca de 12.5 s para 10.4 s. Isso repete o resultado das sessões do Claude Code na Task 4.
- **Limite:** cada release rodou uma vez, em sequência (`k2g` e depois `k2f`), sem ordem invertida. O ganho de trabalho e de TTFT pode ter efeito de ordem e de hora. A Task 4 mostrou uma variação entre dias sem causa encontrada.
- Para a regra "Trocar o launcher", a Task 7 conta como **sem regressão**.

Fonte: `results/soak-g.jsonl`, `results/soak-f.jsonl`, `results/cc-soak<tag>p<N>-*.json` e `results/req-soak<tag>p<N>-*.jsonl`. A hora de cada par vem do horário de gravação do `cc-*.json`. O cálculo foi feito ad hoc a partir desses arquivos e não está em `scripts/`.
