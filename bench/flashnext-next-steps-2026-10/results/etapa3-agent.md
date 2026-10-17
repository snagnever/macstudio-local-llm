# Etapa 3 — bateria agêntica sem Docker (2026-10-14, mlx-serve 26.10.1)

## 3a, 3b, 3c, 3e

| probe | braço | effort | n | resultado |
|---|---|---|---:|---|
| 3a | n2 | xhigh | 40 | ok 40, invented 0, missing 0, empty 0, tool_call 0, length 0, error 0; sessão mediana 68 s |
| 3a | w1 | low | 40 | ok 40, invented 0, missing 0, empty 0, tool_call 0, length 0, error 0; sessão mediana 70 s |
| 3a | w1 | medium | 40 | ok 40, invented 0, missing 0, empty 0, tool_call 0, length 0, error 0; sessão mediana 65 s |
| 3a | w1 | xhigh | 40 | ok 40, invented 0, missing 0, empty 0, tool_call 0, length 0, error 0; sessão mediana 69 s |
| 3b | n2 | xhigh | 40 | loop 0; erros 0; tokens medianos 3949.5 |
| 3b | w1 | xhigh | 40 | loop 0; erros 0; tokens medianos 2328.5 |
| 3c | n2 | xhigh | 30 | turnos ≥140K 10; char_run 0; degenerate 0; vazio 4; código errado 4; prompt máx 201991; erros 0 |
| 3c | w1 | xhigh | 30 | turnos ≥140K 10; char_run 0; degenerate 0; vazio 0; código errado 0; prompt máx 203309; erros 0 |
| 3e | w1 | low | 2 | switch TTFT 166.87 s hit 0.00 |
| 3e | w1 | medium | 2 | switch TTFT 167.13 s hit 0.00 |
| 3e | w1 | xhigh | 12 | prime TTFT 83.48 s hit 0.50; control TTFT 1.34 s hit 1.00; back TTFT 0.88 s hit 1.00 |

## e3f-summary-r1

| suíte | métrica | n2-r1 | w1-r1 |
| --- | --- | ---: | ---: |
| jdhodges | acertos | 34/40 | 36/40 |
| jdhodges | truncadas | 0 | 0 |
| jdhodges | tempo mediano (s) | 2.2 | 2.2 |
| jdhodges | tempo total (s) | 135.2 | 134.4 |
| jdhodges | tokens medianos | 106.5 | 110.5 |
| jdhodges | reasoning mediano (chars) | 152.5 | 155.5 |
| veerman | acertos | 8/12 | 10/12 |
| veerman | truncadas | 0 | 0 |
| veerman | tempo mediano (s) | 3.3 | 3.1 |
| veerman | tempo total (s) | 72.3 | 65.2 |
| veerman | tokens medianos | 172.5 | 174.0 |
| veerman | reasoning mediano (chars) | 478.0 | 399.5 |

| gate | resultado |
| --- | --- |
| G1:jdhodges | passa |
| G1:veerman | passa |

## e3f-summary-r2

| suíte | métrica | n2-r2 | w1-r2 |
| --- | --- | ---: | ---: |
| jdhodges | acertos | 34/40 | 36/40 |
| jdhodges | truncadas | 0 | 0 |
| jdhodges | tempo mediano (s) | 2.4 | 2.3 |
| jdhodges | tempo total (s) | 144.7 | 132.7 |
| jdhodges | tokens medianos | 109.0 | 108.0 |
| jdhodges | reasoning mediano (chars) | 168.5 | 163.0 |
| veerman | acertos | 8/12 | 10/12 |
| veerman | truncadas | 0 | 0 |
| veerman | tempo mediano (s) | 3.2 | 3.1 |
| veerman | tempo total (s) | 60.2 | 63.7 |
| veerman | tokens medianos | 170.0 | 181.5 |
| veerman | reasoning mediano (chars) | 429.5 | 399.5 |

| gate | resultado |
| --- | --- |
| G1:jdhodges | passa |
| G1:veerman | passa |

## e3d-summary-low-r1

| suíte | métrica | w1-xhigh-r1 | w1-low-r1 |
| --- | --- | ---: | ---: |
| gpqa | acertos | 42/50 | 39/50 |
| gpqa | truncadas | 1 | 0 |
| gpqa | tempo mediano (s) | 14.5 | 11.6 |
| gpqa | tempo total (s) | 4278.2 | 691.7 |
| gpqa | tokens medianos | 1035.0 | 945.0 |
| gpqa | reasoning mediano (chars) | 3129.0 | 2725.5 |
| livecodebench | acertos | 43/50 | 26/50 |
| livecodebench | truncadas | 0 | 0 |
| livecodebench | tempo mediano (s) | 25.6 | 13.8 |
| livecodebench | tempo total (s) | 4433.1 | 883.0 |
| livecodebench | tokens medianos | 1964.5 | 1201.5 |
| livecodebench | reasoning mediano (chars) | 5021.0 | 2131.0 |

| gate | resultado |
| --- | --- |
| G1:gpqa | passa |
| G1:livecodebench | falha |
| G2:gpqa | passa |
| G2:livecodebench | passa |

## e3d-summary-low-r2

| suíte | métrica | w1-xhigh-r2 | w1-low-r2 |
| --- | --- | ---: | ---: |
| gpqa | acertos | 43/50 | 36/50 |
| gpqa | truncadas | 2 | 0 |
| gpqa | tempo mediano (s) | 21.1 | 10.7 |
| gpqa | tempo total (s) | 5841.0 | 668.0 |
| gpqa | tokens medianos | 1691.0 | 895.0 |
| gpqa | reasoning mediano (chars) | 5027.0 | 2377.0 |
| livecodebench | acertos | 43/50 | 25/50 |
| livecodebench | truncadas | 1 | 0 |
| livecodebench | tempo mediano (s) | 16.6 | 14.0 |
| livecodebench | tempo total (s) | 4303.2 | 837.0 |
| livecodebench | tokens medianos | 1233.5 | 1168.0 |
| livecodebench | reasoning mediano (chars) | 4066.0 | 2453.0 |

| gate | resultado |
| --- | --- |
| G1:gpqa | falha |
| G1:livecodebench | falha |
| G2:gpqa | passa |
| G2:livecodebench | falha |

## e3d-summary-medium-r1

| suíte | métrica | w1-xhigh-r1 | w1-medium-r1 |
| --- | --- | ---: | ---: |
| gpqa | acertos | 42/50 | 40/50 |
| gpqa | truncadas | 1 | 0 |
| gpqa | tempo mediano (s) | 14.5 | 11.3 |
| gpqa | tempo total (s) | 4278.2 | 1147.2 |
| gpqa | tokens medianos | 1035.0 | 1026.5 |
| gpqa | reasoning mediano (chars) | 3129.0 | 2728.0 |
| livecodebench | acertos | 43/50 | 27/50 |
| livecodebench | truncadas | 0 | 0 |
| livecodebench | tempo mediano (s) | 25.6 | 15.5 |
| livecodebench | tempo total (s) | 4433.1 | 1440.8 |
| livecodebench | tokens medianos | 1964.5 | 1365.0 |
| livecodebench | reasoning mediano (chars) | 5021.0 | 2525.5 |

| gate | resultado |
| --- | --- |
| G1:gpqa | passa |
| G1:livecodebench | falha |
| G2:gpqa | passa |
| G2:livecodebench | passa |

## e3d-summary-medium-r2

| suíte | métrica | w1-xhigh-r2 | w1-medium-r2 |
| --- | --- | ---: | ---: |
| gpqa | acertos | 43/50 | 43/50 |
| gpqa | truncadas | 2 | 0 |
| gpqa | tempo mediano (s) | 21.1 | 12.2 |
| gpqa | tempo total (s) | 5841.0 | 1133.4 |
| gpqa | tokens medianos | 1691.0 | 976.5 |
| gpqa | reasoning mediano (chars) | 5027.0 | 2616.0 |
| livecodebench | acertos | 43/50 | 25/50 |
| livecodebench | truncadas | 1 | 0 |
| livecodebench | tempo mediano (s) | 16.6 | 14.9 |
| livecodebench | tempo total (s) | 4303.2 | 1328.7 |
| livecodebench | tokens medianos | 1233.5 | 1332.5 |
| livecodebench | reasoning mediano (chars) | 4066.0 | 2640.5 |

| gate | resultado |
| --- | --- |
| G1:gpqa | passa |
| G1:livecodebench | falha |
| G2:gpqa | passa |
| G2:livecodebench | falha |

## LiveCodeBench reavaliado

O avaliador do submódulo (`bench2.py`, `a4a95bb`) roda as respostas sem o preâmbulo de imports do LiveCodeBench oficial e passa o programa por `python -c`. Uma resposta certa que usa `List[int]` sem `from typing import List` falha, e uma entrada grande falha com `[Errno 7] Argument list too long`. `scripts/lcb_regrade.py` troca só a execução (preâmbulo oficial, programa em arquivo) e reavalia as respostas gravadas. Nenhuma resposta aprovada passou a reprovada. Detalhe por questão em `e3d-lcb-regrade.json`.

| rótulo | GPQA | LCB bruto | LCB reavaliado | tempo GPQA + LCB (s) |
| --- | ---: | ---: | ---: | ---: |
| w1-xhigh-r1 | 42/50 | 43/50 | 47/50 | 8711 |
| w1-xhigh-r2 | 43/50 | 43/50 | 47/50 | 10144 |
| w1-medium-r1 | 40/50 | 27/50 | 41/50 | 2588 |
| w1-medium-r2 | 43/50 | 25/50 | 40/50 | 2462 |
| w1-low-r1 | 39/50 | 26/50 | 42/50 | 1575 |
| w1-low-r2 | 36/50 | 25/50 | 41/50 | 1505 |

## Veredito

- **3a/3b:** `w1` − `n2` = 0 casos em 20 nas duas sondas (3a: 0 `invented`, 0 `missing`, 0 `empty` nos dois braços; 3b: 0 loops nos dois). O driver não volta a revisão.
- **3c:** nenhum `char_run` em nenhum braço, até ~203K de prompt. Sessão longa liberada no `w1`.
- **3d:** o effort default do harness fica `xhigh`. `medium` passa no GPQA (−2 e 0) e no 3a (40/40), mas fica 6 e 7 abaixo no LCB reavaliado. `low` fica 3 e 7 abaixo no GPQA e 5 e 6 abaixo no LCB. Os dois ficam fora da margem G1 (3). Com as notas brutas a conclusão é a mesma (−16 a −18 no LCB). `medium` gasta ~27% do tempo do `xhigh` e `low` ~16%.
- **3e:** a troca de effort tem hit 0.00 (TTFT ~167 s a 128K, contra 1.3 s no controle). O harness deve fixar o effort por sessão. A causa é o template oficial: a instrução de effort fica no início do system prompt (ver P1 em `plan.md`).
- **3f:** `w1` acerta jdhodges 36/40 e Veerman 10/12 nas duas rodadas, contra 34/40 e 8/12 do `n2`. O reasoning chega nos dois braços (152–478 chars medianos).

## Leitura

- 3a: nenhum turno `invented` em nenhum braço ou effort; não há exemplo a citar.
- 3b: o `w1` chega à resposta com menos tokens (mediana 2328.5 contra 3949.5 do `n2`).
- 3c: os 4 turnos vazios do `n2` são os mesmos 4 de código errado. Em todos, o modelo chama uma tool em vez de responder (`finish_reason=tool_calls`, content vazio), com prompt de 66.9K, 93.6K, 161.1K e 174.5K tokens. Não é degeneração de texto. O `w1` não teve nenhum caso.
- 3d: a perda do `medium` e do `low` está no código. No LCB o `xhigh` gasta ~2× os chars de reasoning do `medium` (4066–5021 contra 2525–2640). No GPQA a diferença de reasoning é menor, e o acerto fica na margem.
- 3d: o tempo total do `xhigh` no GPQA (4278 s e 5841 s) vem de uma cauda longa: 1 e 2 respostas truncadas a 65536 tokens. A mediana por questão é só 14.5–21.1 s.
