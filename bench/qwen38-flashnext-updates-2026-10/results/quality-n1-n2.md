# Qualidade barata n1 × n2 (mlx-serve 26.10.1, temp 0, 2026-10-07)

## HumanEval (164)

| braço | passa |
|---|---:|
| n1 | 151/164 |
| n2 | 154/164 |

n2 − n1: **+3**

- só n1 passa: 142, 46, 51
- só n2 passa: 131, 3, 67, 82, 84, 90
- faltam em n1: —; faltam em n2: —

## Tool-calling jdhodges

| braço | passa |
|---|---:|
| n1 | 39/40 |
| n2 | 38/40 |

n2 − n1: **-1**

- só n1 passa: multi_weather_two_cities_holdout
- só n2 passa: —
- faltam em n1: —; faltam em n2: —

## Tool-calling veerman

| braço | passa |
|---|---:|
| n1 | 8/12 |
| n2 | 9/12 |

n2 − n1: **+1**

- só n1 passa: —
- só n2 passa: veerman_p10_implicit_weather
- faltam em n1: —; faltam em n2: —


## Leitura

- **HumanEval:** n2 − n1 = +3 (154 contra 151). O limite do plano é ≥ −2. Passa.
- **Tool-calling:** n2 − n1 = 0 somando jdhodges (−1) e Veerman (+1). O limite do plano é ≥ −1 caso. Passa.
- 164 problemas não separam a diferença publicada de 0.7 pp de top-1; este teste só pega regressão grande.
- **Ruído do harness:** o grader do `bench2.py` executa só o código da resposta, sem os `import` do
  enunciado. Uma resposta que usa `List` sem `from typing import List` falha. Quatro das nove divergências
  (`below_zero`, `parse_nested_parens`, `rolling_max`, `rescale_to_unit`) são funções com `List` no
  enunciado. O defeito vale igual nos dois braços, mas aumenta o ruído da diferença.
- Os dois braços usam o mesmo sorteio de problemas: `question_num` aponta para o mesmo `dataset_idx` nos dois.
- Os runners rodaram a partir do submódulo do checkout principal (mesmo commit `7a37fe1`). O `bench2.py`
  rodou com `uv run --with datasets --with requests --with openai`, porque o Python do sistema não tem `datasets`.
