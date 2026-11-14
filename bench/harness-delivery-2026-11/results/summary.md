# Entrega por harness — resumo

Sessões: 112. Pesos: `k2`, `z4`. Cada célula mostra tarefas prontas / sessões e a mediana de tempo das sessões prontas.

## Harness × peso

| harness | `k2` prontas | `k2` mediana (s) | `z4` prontas | `z4` mediana (s) |
|---|---:|---:|---:|---:|
| claude | 13/14 | 56.6 | 12/14 | 51.4 |
| dsh | 12/14 | 63.5 | 11/14 | 44.5 |
| opencode | 13/14 | 60.2 | 12/14 | 46.2 |
| pi | 13/14 | 51.1 | 12/14 | 40.5 |

## Por tarefa

| tarefa | `k2` prontas | `z4` prontas | mediana (s) |
|---|---:|---:|---:|
| a | 8/8 | 8/8 | 28.7 |
| b | 7/8 | 8/8 | 28.6 |
| c | 8/8 | 8/8 | 138.4 |
| d | 8/8 | 5/8 | 186.1 |
| T1 | 8/8 | 8/8 | 27.4 |
| T5 | 4/8 | 2/8 | 60.7 |
| T7 | 8/8 | 8/8 | 62.8 |

## Motivos de falha

| motivo | sessões |
|---|---:|
| declarou pronto sem estar | 14 |
| makefile_changed | 7 |
| tests_modified | 1 |

## Regras

- **Reserva** (`z4` contra `k2`): falha. Prontas 47 contra 51, tolerância 3; razão de tempo 0.739 (limite 1.25); por tarefa, de 0.78 a 0.99.
- **Harness**, da melhor para a pior: pi (25 prontas, mediana 51.1 s); claude (25 prontas, mediana 56.6 s); opencode (25 prontas, mediana 60.2 s); dsh (23 prontas, mediana 58.2 s).
- **Válido**: sim. O peso base fecha pelo menos 1 tarefa difícil.

Com 2 repetições por combinação, uma diferença de 1 tarefa entre dois harnesses ou entre dois pesos não dá veredito. A razão de tempo junta todas as tarefas: o peso que falha uma tarefa lenta fica com a mediana menor.
