# Etapa 7 — umixer oQ4e-mix6-mtp v2 × Jundot oQ4e refit no oMLX 0.7.1.dev2 (2026-10-16)

O `x1` usa `umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp` em `73d2cd0`: o umixer aposentou o repo `-v2` em 2026-10-14, e os 24 shards, o config, o template e o índice têm o mesmo SHA de LFS do `-v2` em `ed5c722`. Os braços rodaram no oMLX 0.7.1.dev2.

## 256K (1 rep): wired e swap

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| o1r | 256K | 15.0 s | 560.4 s | 4.50 s | 0.99/1.00 | 48.5 | — | 99.6 GB | -0.01 GB | 0 | 5/5 |
| o1x | 256K | 14.7 s | 560.0 s | 4.50 s | 0.99/1.00 | 50.0 | — | 99.5 GB | -0.04 GB | 0 | 5/5 |
| x1 | 256K | 14.6 s | 563.2 s | 4.50 s | 0.99/1.00 | 50.4 | — | 107.2 GB | 0.00 GB | 0 | 5/5 |

- o1r @ 256K: livre mínimo 0.05 GB; gates passa; alertas —
- o1x @ 256K: livre mínimo 0.04 GB; gates passa; alertas —
- x1 @ 256K: livre mínimo 0.05 GB; gates passa; alertas wired>102

## Qualidade (t1, reasoning xhigh)

| suíte | métrica | o1r | x1 |
| --- | --- | ---: | ---: |
| humaneval | acertos | 144/164 | 142/164 |
| humaneval | truncadas | 1 | 1 |
| humaneval | tempo mediano (s) | 5.6 | 6.2 |
| humaneval | tempo total (s) | 5010.8 | 3169.1 |
| humaneval | tokens medianos | 456.5 | 470.5 |
| humaneval | reasoning mediano (chars) | 1419.5 | 1439.0 |
| gpqa | acertos | 41/50 | 41/50 |
| gpqa | truncadas | 7 | 7 |
| gpqa | tempo mediano (s) | 41.0 | 39.8 |
| gpqa | tempo total (s) | 11111.8 | 10273.7 |
| gpqa | tokens medianos | 3551.5 | 3186.0 |
| gpqa | reasoning mediano (chars) | 8978.5 | 11492.5 |
| livecodebench | acertos | 42/50 | 43/50 |
| livecodebench | truncadas | 2 | 1 |
| livecodebench | tempo mediano (s) | 42.2 | 39.1 |
| livecodebench | tempo total (s) | 7401.8 | 7303.1 |
| livecodebench | tokens medianos | 3459.5 | 3149.5 |
| livecodebench | reasoning mediano (chars) | 11744.0 | 8901.5 |
| jdhodges | acertos | 36/40 | 35/40 |
| jdhodges | truncadas | 0 | 0 |
| jdhodges | tempo mediano (s) | 3.0 | 3.0 |
| jdhodges | tempo total (s) | 154.1 | 180.4 |
| jdhodges | tokens medianos | 115.0 | 102.0 |
| jdhodges | reasoning mediano (chars) | 178.0 | 146.0 |
| veerman | acertos | 7/12 | 8/12 |
| veerman | truncadas | 0 | 0 |
| veerman | tempo mediano (s) | 2.9 | 2.4 |
| veerman | tempo total (s) | 98.4 | 47.1 |
| veerman | tokens medianos | 168.0 | 117.0 |
| veerman | reasoning mediano (chars) | 514.0 | 339.0 |
| if | acertos | 19/20 | 19/20 |
| if | truncadas | 0 | 0 |
| if | tempo mediano (s) | 2.4 | 2.5 |
| if | tempo total (s) | 59.6 | 67.0 |
| if | tokens medianos | 175.0 | 173.5 |
| if | reasoning mediano (chars) | 428.5 | 372.5 |

| gate | resultado |
| --- | --- |
| G1:humaneval | passa |
| G1:gpqa | passa |
| G1:livecodebench | passa |
| G1:jdhodges | passa |
| G1:veerman | passa |
| G1:if | passa |
| G2:gpqa | falha |
| G2:livecodebench | falha |

LiveCodeBench reavaliado: `o1r` 46/50, `x1` 47/50 (`e5-lcb-regrade.md`).

## Taxa de loop

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

## Veredito

**O mix6 v2 não substitui o refit como pack padrão do oMLX.** A regra pede três coisas. O `x1` passa G1 em todas as suítes contra o `o1r` e tem swap Δ 0.00 GB a 256K. Mas não supera o `o1r` além da margem em nenhuma suíte: LCB +1 (bruto e reavaliado, margem 3), Veerman +1 (margem 1, empata no limite), HumanEval −2, jdhodges −1, GPQA e IF iguais.

## Leitura

- O mix6 ocupa mais memória: wired de 107.2 GB a 256K contra 99.6 GB do `o1r` (+7.6 GB). O card declara 75.49 GB residentes contra 69.53 GB do oQ4e (+5.96 GB, **terceiro**). Ele passa o alerta de 102 GB, mas sem swap.
- A velocidade a 256K é igual: `T_turno` 14.6 s contra 15.0 s, decode 50.4 contra 48.5 tok/s, 1 rep.
- O card cita tg de 70.5 contra 58.0 tok/s a 122K num M5 Max (**terceiro**). No M4 Max a 256K a diferença ficou em 4%, dentro do ruído de 1 rep.
- O autor não publicou KLD contra BF16; a bateria não mostra ganho de qualidade.
- `PLE forced to SSD`: 2 linhas no boot do `x1` a 8K e a 256K, contra 3 nos packs do Jundot.
- Loops: 5/8 no `story_en`, a mesma taxa dos packs do Jundot; são respostas que bateram 16384 tokens sem EOS.
