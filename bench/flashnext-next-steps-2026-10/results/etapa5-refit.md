# Etapa 5 — Jundot oQ4e refit (c4ddfb5) no mlx-serve 26.10.2 × Swift 1.5 (2026-10-15)

Parte `o1rm`. Os braços oMLX (`o1x`, `o1r`) esperam o oMLX 0.7.1.dev2 até 2026-10-21 (ruling da Task R); este arquivo ganha essas seções depois.

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
- O needle que falhou a 128K é de um `tool_turn` (rep 1): o modelo achou o needle de 10% e errou os de 50% e 90%, com `finish_reason=stop`. As outras 12 respostas acertaram os três.
- A 32K, o `(1 trunc)` é um `append` que bateu `max_tokens` 4096 sem conteúdo; não conta como erro de needle.
- O wired do `o1rm` a 32K é 2.7 GB maior que o do `w1` (99.9 contra 97.2 GB). A 128K os dois passam de 102 GB e chegam a 0.01 GB livres.
- A comparação mistura runtime e pesos (26.10.2 + refit contra 26.10.1 + Swift). Na Task 1, o 26.10.2 deu 1.038× e 1.000× o 26.10.1 no `n2`; o runtime explica parte da diferença a 32K, mas não a de 128K.
