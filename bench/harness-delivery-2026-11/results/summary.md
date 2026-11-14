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
| lint_config_changed | 7 |
| tests_modified | 1 |

## Regras

- **Reserva** (`z4` contra `k2`): falha. Prontas 47 contra 51, tolerância 3; razão de tempo 0.739 (limite 1.25).
- **Harness**, da melhor para a pior: claude (25 prontas, mediana 56.6 s); pi (25 prontas, mediana 51.1 s); opencode (25 prontas, mediana 60.2 s); dsh (23 prontas, mediana 58.2 s).
- **Válido**: sim. O peso base fecha pelo menos 1 tarefa difícil.

Com 2 repetições por combinação, uma diferença de 1 tarefa entre dois harnesses não dá veredito.

## Auditoria das falhas

As 14 sessões que falham declaram a tarefa pronta: o harness sai com código 0 e sem estourar o limite. Li a cópia do repositório de cada uma. Contagem por causa:

| tarefa | causa | sessões |
|---|---|---:|
| T5 | passa `SERVICE_NAME` pelo `Makefile`; a tarefa proíbe mudar o `Makefile` | 7 |
| T5 | sai sem corrigir o lint | 2 |
| T5 | corrige o lint e deixa o teste falhar por falta de `SERVICE_NAME` | 1 |
| d | deixa 1 dos 2 bugs sem correção | 2 |
| d | não cumpre a estrutura pedida (`lib/common.sh` ou 8 checks) | 1 |
| b | apaga um teste original | 1 |

As 2 sessões que saem sem corrigir o lint são do OpenCode com o peso `z4`. Nenhuma sessão estoura o limite de tempo.

## Como a matriz rodou

- A matriz rodou no rig em 2026-11-14, de 01:55 a 04:48. As 16 sessões da T5 rodaram de novo de 04:57 a 05:16.
- **T5 repetida.** Na primeira rodada, as 16 sessões da T5 falharam por defeito do sandbox: ele esconde o `.git` do repositório que contém a cópia, e o `ruff` falha com `E902`. O commit `4715df3` move as cópias para fora do repositório. Os 16 registros antigos ficam em `logs/t5-invalid/`, fora do git.
- **Check refeito.** O mesmo commit deixa de marcar `tests_modified` quando a sessão só muda uma linha de import. O check rodou de novo nas 96 cópias das outras tarefas: 20 registros perderam a marca, e nenhum `task_done` mudou.
- As sessões da T5 rodaram depois das outras 96, e não intercaladas com elas.
- O OpenCode do rig é o 1.15.10; o do MacBook é o 1.18.31.

Este arquivo sai do `summarize.py`, e as duas seções acima foram escritas à mão. Uma nova execução do script apaga as duas.
