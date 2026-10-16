# Etapa 12 — `medium` em tarefas que não são de código (2026-10-16, `w1`, mlx-serve 26.10.1)

Runbook: [plan-effort-needles.md](../plan-effort-needles.md), Task 12. O `xhigh` do 3f vem da Task 3 (`e3f/t1/w1-r{1,2}`, 2026-10-13/14). O IF em `xhigh` e todo o `medium` rodaram em 2026-10-16. `e12/t1x/` junta os dois por symlinks.

## Resumo

| suíte | `xhigh` (r1 + r2) | `medium` (r1 + r2) | margem G1 × 2 | tempo total `xhigh` → `medium` |
| --- | ---: | ---: | ---: | --- |
| jdhodges (40) | 72/80 | 73/80 | 4 | 267 s → 205 s (−23%) |
| Veerman (12) | 20/24 | 20/24 | 2 | 129 s → 93 s (−28%) |
| IF (20) | 39/40 | 40/40 | 4 | 104 s → 161 s (+55%) |
| GPQA (50, Task 3d) | 85/100 | 83/100 | 6 | 10119 s → 2281 s (−77%) |

| 3c, sessão até ~200K | `xhigh` | `medium` |
| --- | --- | --- |
| turnos | 30 | 30 |
| `char_run` / `degenerate` | 0 / 0 | 0 / 0 |
| vazio (e código errado nos mesmos turnos) | 0 | 2 |
| reasoning mediano por turno (chars) | 252 | 167 |
| tempo das 2 sessões | 1335 s | 1303 s |

## e12-summary-r1

| suíte | métrica | w1-xhigh-r1 | w1-medium-r1 |
| --- | --- | ---: | ---: |
| jdhodges | acertos | 36/40 | 37/40 |
| jdhodges | truncadas | 0 | 0 |
| jdhodges | tempo mediano (s) | 2.2 | 1.9 |
| jdhodges | tempo total (s) | 134.4 | 98.2 |
| jdhodges | tokens medianos | 110.5 | 81.0 |
| jdhodges | reasoning mediano (chars) | 155.5 | 97.0 |
| veerman | acertos | 10/12 | 10/12 |
| veerman | truncadas | 0 | 0 |
| veerman | tempo mediano (s) | 3.1 | 2.8 |
| veerman | tempo total (s) | 65.2 | 45.0 |
| veerman | tokens medianos | 174.0 | 168.0 |
| veerman | reasoning mediano (chars) | 399.5 | 268.0 |
| if | acertos | 20/20 | 20/20 |
| if | truncadas | 0 | 0 |
| if | tempo mediano (s) | 1.7 | 3.9 |
| if | tempo total (s) | 55.9 | 81.1 |
| if | tokens medianos | 148.0 | 307.0 |
| if | reasoning mediano (chars) | 296.5 | 508.0 |

| gate | resultado |
| --- | --- |
| G1:jdhodges | passa |
| G1:veerman | passa |
| G1:if | passa |

## e12-summary-r2

| suíte | métrica | w1-xhigh-r2 | w1-medium-r2 |
| --- | --- | ---: | ---: |
| jdhodges | acertos | 36/40 | 36/40 |
| jdhodges | truncadas | 0 | 0 |
| jdhodges | tempo mediano (s) | 2.3 | 2.0 |
| jdhodges | tempo total (s) | 132.7 | 106.8 |
| jdhodges | tokens medianos | 108.0 | 82.0 |
| jdhodges | reasoning mediano (chars) | 163.0 | 100.5 |
| veerman | acertos | 10/12 | 10/12 |
| veerman | truncadas | 0 | 0 |
| veerman | tempo mediano (s) | 3.1 | 2.9 |
| veerman | tempo total (s) | 63.7 | 47.6 |
| veerman | tokens medianos | 181.5 | 168.0 |
| veerman | reasoning mediano (chars) | 399.5 | 268.0 |
| if | acertos | 19/20 | 20/20 |
| if | truncadas | 0 | 0 |
| if | tempo mediano (s) | 2.0 | 4.0 |
| if | tempo total (s) | 48.4 | 79.8 |
| if | tokens medianos | 152.0 | 271.5 |
| if | reasoning mediano (chars) | 306.0 | 412.5 |

| gate | resultado |
| --- | --- |
| G1:jdhodges | passa |
| G1:veerman | passa |
| G1:if | passa |

## 3c

| probe | braço | effort | n | resultado |
|---|---|---|---:|---|
| 3c | w1 | medium | 30 | turnos ≥140K 10; char_run 0; degenerate 0; vazio 2; código errado 2; prompt máx 202648; erros 0 |
| 3c | w1 | xhigh | 30 | turnos ≥140K 10; char_run 0; degenerate 0; vazio 0; código errado 0; prompt máx 203309; erros 0 |

## Veredito

- **Chat e tool-calling curtos: `medium` passa.** jdhodges, Veerman, IF e GPQA ficam dentro da margem G1 do `xhigh` (somas de 2 rodadas: +1, 0, +1, −2). O 3a da Task 3 também passa (40/40). No tool-calling, o `medium` gasta 23–28% menos tempo.
- **Sessão longa: `medium` falha a regra do 3c.** A regra pedia vazio + código errado ≤ o do `xhigh` + 1. O `medium` teve 2 turnos vazios contra 0 do `xhigh`, a 67K e a 107K tokens de prompt, nos dois casos com `finish_reason=tool_calls`. Contando cada turno uma vez, fica 2 > 1. Não houve `char_run` nem degeneração.
- **Recomendação ao harness:** `medium` em chat e em tool-calling de sessões curtas; `xhigh` em código e em sessões longas. Com o template oficial, a escolha é por sessão, porque a troca zera o cache (3e). Se o `w1t` for adotado (Task 11), a troca pode ser por turno.

## Leitura

- Os 2 turnos vazios do `medium` no 3c são o mesmo padrão dos 4 turnos vazios do `n2` em `xhigh` na Task 3: o modelo chama uma tool em vez de responder. O `código errado` conta os mesmos turnos, porque o conteúdo vazio não tem o código. Com 30 turnos por braço, 2 contra 0 é um sinal fraco, mas a regra foi definida antes da medição.
- No IF, o `medium` pensa mais que o `xhigh` (reasoning mediano 412–508 contra 296–306 chars) e demora mais. As 20 questões do IF saturam (39/40 e 40/40), então a suíte não separa os efforts.
- No 3c, o tempo das sessões quase não muda (−2%): a sessão longa é dominada por prefill, e o reasoning por turno já é curto (252 contra 167 chars).
- No GPQA, a economia de tempo do `medium` (−77%) vem quase toda da cauda: o `xhigh` teve 3 respostas truncadas em 65536 tokens.
