# Swift 1.5 × n2 — veredito (2026-10-11)

**O w1 (Swift 1.5, pack Dankpaws MLX-4.7bpw) passa nos três gates e é promovido a driver diário do Flash-Next.**
Com o mesmo runtime e as mesmas flags, ele mantém a qualidade do n2 (todas as suítes dentro da margem do G1,
nos dois perfis) e chega à resposta final 2–3× mais rápido nas suítes de raciocínio, com `T_turno` igual ou
menor. A qualidade de agente (Terminal-Bench) segue sem medida nos dois braços: o run ficou suspenso porque
depende de outra máquina para os containers Docker.

Rig: Mac Studio M4 Max 128 GB. Runtime: mlx-serve 26.10.1 nos dois braços. Runbook: [plan.md](../plan.md).

| braço | pesos |
| --- | --- |
| n2 | `ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw` @ `dafff5c` |
| w1 | `Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw` @ `13839b7` |

## Qualidade e tempo (bateria A/B, `reasoning_effort` xhigh)

Perfis de sampling: **t1** = sampling do vendor (`temperature 1.0`, `top_p 0.95`, `top_k 20`, `min_p 0`,
`presence_penalty 0`, `repetition_penalty 1.0`); **t0** = `temperature 0`. Uma rodada por braço e perfil.

### Acertos

| suíte | n2 t1 | w1 t1 | n2 t0 | w1 t0 | margem G1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HumanEval (164), com imports do prompt | 158 | 158 | 155 | 157 | 3 |
| HumanEval (164), estrito | 144 | 147 | 138 | 143 | — |
| GPQA-Diamond (50, seed 42) | 45 | 43 | 39 | 42 | 3 |
| LiveCodeBench v6 (50, seed 42)¹ | 45 | 47 | 45 | 45 | 3 |
| jdhodges (40) | 35 | 36 | 38 | 39 | 2 |
| Veerman (12) | 10 | 10 | 10 | 9 | 1 |
| IF, estilo IFEval (20) | 20 | 19 | 20 | 19 | 2 |

¹ Reavaliado em 2026-10-14 com o prelúdio de imports do harness oficial
([bench/lcb-regrade-2026-10](../../lcb-regrade-2026-10/results/regrade-summary.md)). Antes: 41, 42, 41, 41. O gate G1
continua passando nos dois perfis.

O G1 do HumanEval usa a nota com os imports do prompt
([humaneval-regrade.json](humaneval-regrade.json)): o grader estrito do `bench2.py` reprova respostas certas
que não trazem `from typing import List`, e isso afeta os dois braços.

### Tempo até a resposta final

| suíte | perfil | n2 mediano | w1 mediano | razão | n2 total | w1 total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| GPQA | t1 | 63,9 s | 22,3 s | **0,35** | 158 min | 95 min |
| LiveCodeBench | t1 | 39,1 s | 19,1 s | **0,49** | 144 min | 81 min |
| HumanEval | t1 | 6,8 s | 5,7 s | 0,84 | 54 min | 38 min |
| GPQA | t0 | 18,3 s | 14,9 s | 0,81 | 140 min | 56 min |
| LiveCodeBench | t0 | 23,9 s | 16,0 s | 0,67 | 100 min | 62 min |

Tokens medianos por questão em t1: GPQA 5 124 (n2) contra 1 689 (w1); LCB 2 985 contra 1 449. Com
`max_tokens` 65 536, o n2 truncou 4 GPQA em t1 e 7 em t0; o w1 truncou 2 e 0. Tabelas completas:
[ab-summary-t1.md](ab-summary-t1.md), [ab-summary-t0.md](ab-summary-t0.md).

## Velocidade de turno (`T_turno`, perfil t1, 3 reps)

| contexto | n2 | w1 | razão | decode n2 / w1 | aceitação MTP n2 / w1 | wired pico n2 / w1 |
| --- | ---: | ---: | ---: | --- | --- | --- |
| 32K | 8,1 s | 7,9 s | 0,98 | 82,3 / 84,6 tok/s | 0,84 / 0,77 | 96,1 / 96,1 GB |
| 128K | 8,9 s | 8,6 s | 0,97 | 73,2 / 76,7 tok/s | 0,79 / 0,67 | 110,6 / 111,2 GB |

Prefill e TTFT são iguais nos dois braços (mesmo runtime, mesmo layout). O w1 aceita menos tokens da MTP, mas
decodifica um pouco mais rápido. Swap Δ 0 em todos os runs. Fonte: [tturno-summary.json](tturno-summary.json).

## Gates

| gate | t1 | t0 |
| --- | --- | --- |
| G1 qualidade (todas as suítes) | passa | passa |
| G2 thinking (GPQA ≤ 0,8×) | passa (0,35) | falha (0,81) |
| G2 thinking (LCB ≤ 0,8×) | passa (0,49) | passa (0,67) |
| G3 velocidade (`T_turno` ≤ 1,03× a 32K e 128K) | passa (0,98 / 0,97) | — |

Regra de decisão do runbook: promover se G1 e G2 passam em t1, G1 passa em t0 e G3 passa. As quatro condições
valem. O G2 do GPQA em t0 fica em 0,81, logo acima do limite; a regra usa o t1 para o G2.

## Leitura

- **O ganho do Swift é o que o card declara: menos thinking.** Nas suítes de raciocínio, o w1 gasta um terço
  dos tokens do n2 no GPQA e metade no LCB, com a mesma nota. O card declara −63% de thinking no GPQA-Diamond;
  aqui, em t1, a mediana de tokens por questão caiu 67% e a de caracteres de reasoning caiu 78%.
- **A regressão de instruction-following do card aparece pouco.** O w1 erra o mesmo caso nos dois perfis
  (`if08`: dois parágrafos separados por `***`). O preview gravado (300 caracteres) não chega ao separador, então
  não verifiquei se o modelo ignorou a instrução ou se usou uma forma que o checker não aceita.
- **GPQA em t1: −2 para o w1 (43 contra 45); em t0: +3 (42 contra 39).** Com 50 questões e uma rodada, essas
  diferenças ficam dentro do ruído de amostragem.
- **Um `tool_turn` do n2 a 32K errou as 3 needles** (1 de 13 registros; 932 tokens, `finish_reason=stop`). As
  outras requisições dos dois braços acertaram. Leio como variância do sampling t1, não como falha do runtime.

## Limites

- Uma rodada por braço e perfil. GPQA e LCB usam amostras de 50 questões, não os conjuntos completos.
- A sonda IF é uma checagem no estilo IFEval; ela não reproduz o IFBench do card do Swift.
- Tool-calling (jdhodges, Veerman): o `tool_call_bench.py` mandou `reasoning_effort` e o sampling por
  `extra_body`, mas não gravava o texto de reasoning nesta campanha (`n/d` nas tabelas). Não há evidência de que
  esses dois braços pensaram nessas suítes; a mediana de ~110 tokens por resposta sugere pouco ou nenhum
  thinking. O runner grava `reasoning_chars` a partir do submódulo `a4a95bb`.
- Os dois packs têm o mesmo layout, mas a tabela n-gram difere (hashes LFS diferentes): o A/B compara os packs,
  não só o fine-tune.
- O A/B pausou duas vezes para runs de 512K de outra sessão (fronteiras de perfil; nenhum dado perdido). O t1 e o
  t0 de cada braço rodaram em subidas diferentes do servidor.
- Terminal-Bench: suspenso. Script pronto em `bench/terminal-bench/scripts/run-tbench-flashnext.sh`.
- Licença do Swift 1.5: Swift Open License v1.0 (uso confirmado pelo usuário em 2026-10-10).
