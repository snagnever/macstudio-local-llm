# Etapa 5 — Jundot oQ4e refit (c4ddfb5) no mlx-serve 26.10.2 × Swift 1.5 (2026-10-15)

Parte `o1rm` primeiro. Os braços oMLX (`o1x`, `o1r`) rodaram depois, no oMLX 0.7.1.dev2 (seções abaixo).

O `o1rm` roda no mlx-serve 26.10.2 e o `w1` no runtime do driver (26.10.1, Task 1). Smoke 8K do `o1rm`: OK, 15 linhas `[spec-stats]`.

## Driver: o1rm ≤ 0.97 × w1

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| o1rm | 32K | 8.6 s | 34.6 s | 1.80 s | 0.96/0.96 | 74.9 | 0.551 | 99.9 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| w1 | 32K | 8.0 s | 34.5 s | 1.80 s | 0.96/0.96 | 82.8 | 0.608 | 97.2 GB | -0.02 GB | 0 | 13/13 |
| o1rm | 128K | 9.1 s | 165.6 s | 2.00 s | 0.99/0.99 | 72.4 | 0.717 | 109.2 GB | 0.00 GB | 0 | 12/13 |
| w1 | 128K | 8.7 s | 165.6 s | 1.90 s | 0.99/0.99 | 76.1 | 0.779 | 110.8 GB | 0.00 GB | 0 | 13/13 |

- o1rm @ 32K: livre mínimo 0.05 GB; gates passa; alertas —
- w1 @ 32K: livre mínimo 0.02 GB; gates passa; alertas —
- o1rm @ 128K: livre mínimo 0.01 GB; gates needle; alertas wired>102
- w1 @ 128K: livre mínimo 0.01 GB; gates passa; alertas wired>102

| razão `T_turno(o1rm) / T_turno(w1)` | 32K | 128K |
|---|---:|---:|
| o1rm | 1.075 | 1.046 |

Regra: ≤ 0.97 em 32K, 128K, gates do candidato e da base, `[spec-stats]`.
VERDICT: fail (razão 1.075 @32K; razão 1.046 @128K; gates o1rm@128K: needle)

## Condição do Task 6: o1rm ≤ 1.03 × w1

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| o1rm | 32K | 8.6 s | 34.6 s | 1.80 s | 0.96/0.96 | 74.9 | 0.551 | 99.9 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| w1 | 32K | 8.0 s | 34.5 s | 1.80 s | 0.96/0.96 | 82.8 | 0.608 | 97.2 GB | -0.02 GB | 0 | 13/13 |
| o1rm | 128K | 9.1 s | 165.6 s | 2.00 s | 0.99/0.99 | 72.4 | 0.717 | 109.2 GB | 0.00 GB | 0 | 12/13 |
| w1 | 128K | 8.7 s | 165.6 s | 1.90 s | 0.99/0.99 | 76.1 | 0.779 | 110.8 GB | 0.00 GB | 0 | 13/13 |

- o1rm @ 32K: livre mínimo 0.05 GB; gates passa; alertas —
- w1 @ 32K: livre mínimo 0.02 GB; gates passa; alertas —
- o1rm @ 128K: livre mínimo 0.01 GB; gates needle; alertas wired>102
- w1 @ 128K: livre mínimo 0.01 GB; gates passa; alertas wired>102

| razão `T_turno(o1rm) / T_turno(w1)` | 32K | 128K |
|---|---:|---:|
| o1rm | 1.075 | 1.046 |

Regra: ≤ 1.03 em 32K, 128K, gates do candidato e da base, `[spec-stats]`.
VERDICT: fail (razão 1.075 @32K; razão 1.046 @128K; gates o1rm@128K: needle)

```
O1RM_DRIVER=0
RUN_TASK6=0
```

## Veredito (parte `o1rm`)

- **O `o1rm` não vira driver.** `T_turno` é 1.075× o do `w1` a 32K e 1.046× a 128K, acima de 0.97. A 128K ele também falha o gate de needles (12/13).
- **A Task 6 não roda** (`RUN_TASK6=0`): a razão também passa de 1.03 nas duas bandas. A Task 6 testa o oQ4e do Swift no mesmo caminho, e o pack base do Jundot já fica atrás do `w1`.
- Step 11 (bateria de qualidade `o1rm` × `w1`) pulado: só roda com `O1RM_DRIVER=1`.

## Leitura

- O decode explica a diferença: 74.9 contra 82.8 tok/s a 32K e 72.4 contra 76.1 a 128K. O TTFT frio e o quente são iguais nos dois braços. A aceitação MTP do `o1rm` é menor (0.551 contra 0.608 a 32K; 0.717 contra 0.779 a 128K).
- O needle que falhou a 128K é o primeiro dos 3 `tool_turn`: o modelo achou o needle de 10% e errou os de 50% e 90%, com `finish_reason=stop`. As outras 12 respostas acertaram os três.
- A 32K, o `(1 trunc)` é um `append` que bateu `max_tokens` 4096 sem conteúdo; não conta como erro de needle.
- O wired do `o1rm` a 32K é 2.7 GB maior que o do `w1` (99.9 contra 97.2 GB). A 128K os dois passam de 102 GB e chegam a 0.01 GB livres.
- A comparação mistura runtime e pesos (26.10.2 + refit contra 26.10.1 + Swift). Na Task 1, o 26.10.2 deu 1.038× e 1.000× o 26.10.1 no `n2`; o runtime explica parte da diferença a 32K, mas não a de 128K.

# Parte oMLX: `o1x` (oQ4e `2615fc0`) × `o1r` (refit `c4ddfb5`) no oMLX 0.7.1.dev2 (2026-10-15/16)

Os braços rodaram no oMLX 0.7.1.dev2, lançado em 2026-10-15 (ruling Task R2 do ledger), e não no dev1 do plano.

## Pesos no oMLX: paridade |r−1| ≤ 0.03

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| o1r | 32K | 10.3 s | 52.6 s | 2.50 s | 0.94/0.96 | 65.4 | — | 91.5 GB | 0.00 GB | 0 | 13/13 |
| o1x | 32K | 10.3 s | 52.6 s | 2.50 s | 0.94/0.96 | 65.3 | — | 91.5 GB | -0.01 GB | 0 | 12/13 (1 trunc) |
| o1r | 128K | 12.3 s | 257.4 s | 3.30 s | 0.99/0.99 | 56.7 | — | 99.2 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| o1x | 128K | 11.9 s | 257.4 s | 3.30 s | 0.99/0.99 | 59.1 | — | 99.5 GB | 0.00 GB | 0 | 10/13 (2 trunc, 1 erro) |
| o1r | 256K | 15.0 s | 560.4 s | 4.50 s | 0.99/1.00 | 48.5 | — | 99.6 GB | -0.01 GB | 0 | 5/5 |
| o1x | 256K | 14.7 s | 560.0 s | 4.50 s | 0.99/1.00 | 50.0 | — | 99.5 GB | -0.04 GB | 0 | 5/5 |

- o1r @ 32K: livre mínimo 0.04 GB; gates passa; alertas —
- o1x @ 32K: livre mínimo 0.01 GB; gates passa; alertas —
- o1r @ 128K: livre mínimo 0.06 GB; gates passa; alertas —
- o1x @ 128K: livre mínimo 0.06 GB; gates needle; alertas —
- o1r @ 256K: livre mínimo 0.05 GB; gates passa; alertas —
- o1x @ 256K: livre mínimo 0.04 GB; gates passa; alertas —

| razão `T_turno(o1r) / T_turno(o1x)` | 32K | 128K |
|---|---:|---:|
| o1r | 1.000 | 1.034 |

Regra: |r−1| ≤ 0.03 em 32K, 128K, gates do candidato e da base, `[spec-stats]`.
VERDICT: fail (razão 1.034 @128K; gates o1x@128K: needle)

## 256K (1 rep)

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| o1r | 256K | 15.0 s | 560.4 s | 4.50 s | 0.99/1.00 | 48.5 | — | 99.6 GB | -0.01 GB | 0 | 5/5 |
| o1x | 256K | 14.7 s | 560.0 s | 4.50 s | 0.99/1.00 | 50.0 | — | 99.5 GB | -0.04 GB | 0 | 5/5 |
| x1 | 256K | 14.6 s | 563.2 s | 4.50 s | 0.99/1.00 | 50.4 | — | 107.2 GB | 0.00 GB | 0 | 5/5 |

- o1r @ 256K: livre mínimo 0.05 GB; gates passa; alertas —
- o1x @ 256K: livre mínimo 0.04 GB; gates passa; alertas —
- x1 @ 256K: livre mínimo 0.05 GB; gates passa; alertas wired>102

## Qualidade (t1, reasoning xhigh)

| suíte | métrica | o1x | o1r |
| --- | --- | ---: | ---: |
| humaneval | acertos | 140/164 | 144/164 |
| humaneval | truncadas | 3 | 1 |
| humaneval | tempo mediano (s) | 6.6 | 5.6 |
| humaneval | tempo total (s) | 4289.8 | 5010.8 |
| humaneval | tokens medianos | 538.5 | 456.5 |
| humaneval | reasoning mediano (chars) | 1642.5 | 1419.5 |
| gpqa | acertos | 42/50 | 41/50 |
| gpqa | truncadas | 6 | 7 |
| gpqa | tempo mediano (s) | 61.0 | 41.0 |
| gpqa | tempo total (s) | 10944.8 | 11111.8 |
| gpqa | tokens medianos | 4990.5 | 3551.5 |
| gpqa | reasoning mediano (chars) | 14496.0 | 8978.5 |
| livecodebench | acertos | 41/50 | 42/50 |
| livecodebench | truncadas | 3 | 2 |
| livecodebench | tempo mediano (s) | 34.2 | 42.2 |
| livecodebench | tempo total (s) | 7987.7 | 7401.8 |
| livecodebench | tokens medianos | 2865.0 | 3459.5 |
| livecodebench | reasoning mediano (chars) | 9269.5 | 11744.0 |
| jdhodges | acertos | 38/40 | 36/40 |
| jdhodges | truncadas | 0 | 0 |
| jdhodges | tempo mediano (s) | 2.8 | 3.0 |
| jdhodges | tempo total (s) | 131.0 | 154.1 |
| jdhodges | tokens medianos | 101.0 | 115.0 |
| jdhodges | reasoning mediano (chars) | 123.0 | 178.0 |
| veerman | acertos | 10/12 | 7/12 |
| veerman | truncadas | 0 | 0 |
| veerman | tempo mediano (s) | 2.6 | 2.9 |
| veerman | tempo total (s) | 62.2 | 98.4 |
| veerman | tokens medianos | 164.0 | 168.0 |
| veerman | reasoning mediano (chars) | 290.0 | 514.0 |
| if | acertos | 19/20 | 19/20 |
| if | truncadas | 0 | 0 |
| if | tempo mediano (s) | 2.2 | 2.4 |
| if | tempo total (s) | 54.1 | 59.6 |
| if | tokens medianos | 182.0 | 175.0 |
| if | reasoning mediano (chars) | 453.0 | 428.5 |

| gate | resultado |
| --- | --- |
| G1:humaneval | passa |
| G1:gpqa | passa |
| G1:livecodebench | passa |
| G1:jdhodges | passa |
| G1:veerman | falha |
| G1:if | passa |
| G2:gpqa | passa |
| G2:livecodebench | falha |

LiveCodeBench reavaliado com `scripts/lcb_regrade.py` (ver Task 3):

| arquivo | original | reavaliado | viradas para ok | viradas para falha |
|---|---:|---:|---:|---:|
| o1r/livecodebench.jsonl | 42/50 | 46/50 | 4 | 0 |
| o1x/livecodebench.jsonl | 41/50 | 45/50 | 4 | 0 |
| x1/livecodebench.jsonl | 43/50 | 47/50 | 4 | 0 |

## Taxa de loop (vendor_t1_xhigh, 8 seeds)

| arquivo | prompt | loops | n | erros | tokens médios |
|---|---|---:|---:|---:|---:|
| e5-o1x | exec_pt | 0 | 8 | 0 | 329 |
| e5-o1x | list_en | 1 | 8 | 0 | 12993 |
| e5-o1x | qa_fact | 0 | 8 | 0 | 101 |
| e5-o1x | story_en | 5 | 8 | 0 | 13645 |
| e5-o1r | exec_pt | 0 | 8 | 0 | 566 |
| e5-o1r | list_en | 0 | 8 | 0 | 12416 |
| e5-o1r | qa_fact | 0 | 8 | 0 | 97 |
| e5-o1r | story_en | 5 | 8 | 0 | 15541 |
| e5-x1 | exec_pt | 0 | 8 | 0 | 241 |
| e5-x1 | list_en | 0 | 8 | 0 | 13019 |
| e5-x1 | qa_fact | 0 | 8 | 0 | 119 |
| e5-x1 | story_en | 5 | 8 | 0 | 13522 |

## Veredito (parte oMLX)

- **O refit não vira pack padrão do oMLX.** A regra pede G1 em todas as suítes e swap Δ 0 a 256K. O swap passa (−0.01 GB), mas o Veerman falha: 7/12 contra 10/12 do `o1x`, com margem de 1. As outras cinco suítes passam (HumanEval +4, LCB reavaliado +1, GPQA −1, jdhodges −2, IF igual).
- **A velocidade é igual.** A paridade falha por 1.034 a 128K, mas é ruído do decode: o TTFT é igual nas 3 reps, o desvio padrão do decode por resposta é 5–8 tok/s, e sem as respostas truncadas a mediana fica 55.6 (`o1x`) contra 56.7 (`o1r`). O needle errado do `o1x` a 128K é de `tool_turn` (`stop` com os 3 needles errados).
- `O1RM_DRIVER=0` e `RUN_TASK6=0`, da parte `o1rm` acima.

## Leitura (parte oMLX)

- O Veerman tem 12 casos e uma rodada. Na Task 3, o `w1` e o `n2` repetiram o mesmo placar nas duas rodadas (10/12 e 8/12), então o placar é estável por modelo, mas 3 casos em 12 ainda é pouco para separar dois packs com o mesmo tamanho. Uma segunda rodada do Veerman no `o1r` decide se a diferença é real.
- `PLE forced to SSD` aparece no boot dos dois braços em todas as bandas: 3 linhas no smoke de 8K e 3 a 256K, sem crescer com o contexto. O swap Δ fica em 0 nas três bandas.
- Loops: os 5 casos de `story_en` em cada braço (e o `list_en` do `o1x`) são respostas que bateram 16384 tokens sem EOS; na maioria o conteúdo veio vazio, ou seja, o raciocínio em `xhigh` consumiu todo o limite. A taxa é a mesma nos três packs oMLX (5/8). A campanha não tem a mesma bateria de loops no `w1`, então não há base no mlx-serve.
- O KLD que o card do refit declara (código 0.0877 → 0.0776, **terceiro**) não aparece como ganho na bateria: o placar fica dentro da margem em cinco suítes e abaixo no Veerman.
- A 32K, o oMLX fica 1.29× o `w1` no mlx-serve (10.3 s contra 8.0 s, Task 5 parte `o1rm`).

# Rodadas extras (2026-10-16)

Pedidas pelo usuário depois do veredito: uma segunda rodada do Veerman no `o1r` e no `o1x` (oMLX 0.7.1.dev2) e a bateria de loops no `w1` (mlx-serve 26.10.1), para ter base.

| braço | Veerman r1 | Veerman r2 | total |
| --- | ---: | ---: | ---: |
| `o1x` (oQ4e `2615fc0`) | 10/12 | 8/12 | 18/24 |
| `o1r` (refit `c4ddfb5`) | 7/12 | 9/12 | 16/24 |

Fonte: `e5/t1/o1x-r2/veerman.jsonl` e `e5/t1/o1r-r2/veerman.jsonl`. Na rodada 2 o G1 do Veerman passa (`o1r` 9 contra `o1x` 8).

Taxa de loop (`vendor_t1_xhigh`, 8 seeds), `w1` contra `o1r`:

| prompt | `w1` loops | `w1` tokens médios | `o1r` loops | `o1r` tokens médios |
| --- | ---: | ---: | ---: | ---: |
| exec_pt | 0/8 | 336 | 0/8 | 566 |
| list_en | 0/8 | 4154 | 0/8 | 12416 |
| qa_fact | 0/8 | 84 | 0/8 | 97 |
| story_en | 3/8 | 12911 | 5/8 | 15541 |

Fonte: `loops/e5-w1.jsonl`.

## Veredito (rodadas extras)

- **A falha de G1 no Veerman era ruído.** A rodada 2 inverte a ordem, e o total fica 16/24 contra 18/24. O refit tem a mesma qualidade e a mesma velocidade do oQ4e antigo. O `2615fc0` foi apagado do rig em 2026-10-16, então o refit fica como pack do oMLX.
- **O Swift bate o limite de tokens menos vezes que os packs oMLX.** No `story_en`, 3/8 contra 5/8, e no `list_en` usa ~1/3 dos tokens. Os 3 casos do `w1` também são respostas que bateram 16384 tokens sem EOS, 2 delas com o conteúdo vazio: é raciocínio longo em `xhigh`, não repetição de texto. A comparação mistura runtime e pack (mlx-serve × oMLX).
