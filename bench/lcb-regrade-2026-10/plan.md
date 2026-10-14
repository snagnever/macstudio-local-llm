# Reavaliação do LiveCodeBench com o runner corrigido (2026-10-14)

## Objetivo

Reavaliar todas as respostas de LiveCodeBench salvas no repositório com um runner de testes corrigido, e
medir quanto cada nota publicada muda.

## Os dois defeitos

O runner de `tools/local-llm-bench-m4-32gb/scripts/bench2.py` (submódulo `a4a95bb`, funções
`_run_lcb_functional_test` e `_run_lcb_stdin_test`) conta menos acertos do que o harness oficial:

1. Ele executa a resposta sem o prelúdio de imports do harness oficial
   (`lcb_runner/evaluation/testing_util.py`, `import_string`: `from typing import *`,
   `from collections import *`, itertools, functools, heapq, bisect, math e outros, mais
   `sys.setrecursionlimit(50000)`). Uma solução correta que usa `List[int]` sem
   `from typing import List` falha com `NameError` no teste 0 (`fail_test0:rc=1`).
2. Ele passa o programa, com as entradas do teste embutidas, para `python -c`. Uma entrada funcional grande
   falha com `[Errno 7] Argument list too long`.

A correção do submódulo está no PR
[snagnever/local-llm-bench-m4-32gb#3](https://github.com/snagnever/local-llm-bench-m4-32gb/pull/3). Ela não
está mesclada; o ponteiro do submódulo aqui continua em `a4a95bb`.

## Método

- [`scripts/lcb_regrade.py`](scripts/lcb_regrade.py) é a cópia do regrader da campanha
  `bench/flashnext-next-steps-2026-10` (branch `bench/flashnext-next-steps-2026-10`). Ele mantém a extração de
  código, a decodificação dos testes e a comparação do `bench2`, e troca só os dois runners: cada programa
  recebe o prelúdio e roda a partir de um arquivo temporário.
- [`scripts/regrade_all.py`](scripts/regrade_all.py) aplica o regrader a qualquer JSONL do `bench2`. Ele busca
  cada resposta pelo `lcb_question_id` no dataset completo, porque execuções parciais e retomadas usaram
  amostras de tamanhos diferentes de 50. Uma resposta truncada (`finish_reason == "length"`) continua errada.
- [`scripts/summarize.py`](scripts/summarize.py) junta os arquivos de cada modelo e fica com a resposta mais
  recente por questão. É a mesma regra das notas publicadas, que somam a rodada de 50 questões e as
  reexecuções de truncadas.
- Execução no rig (`~/LocalProjects/local-llms/.venv`, com `huggingface_hub` e o dataset
  `livecodebench/code_generation_lite` em cache), com o `bench2.py` de `a4a95bb`.

Comando:

```bash
python -I bench/lcb-regrade-2026-10/scripts/regrade_all.py --json verdicts.json FILE.jsonl ...
python3 bench/lcb-regrade-2026-10/scripts/summarize.py verdicts.json
```

## Entradas

- Os 4 JSONL do A/B do Swift 1.5 em `bench/swift15-flashnext-2026-10/results/ab/`.
- Os 36 JSONL de LiveCodeBench rastreados no submódulo, em
  `tools/local-llm-bench-m4-32gb/benchmarks/runs/` (fonte das notas dos cards em `docs/models/`).

## Resultados

Ver [`results/regrade-summary.md`](results/regrade-summary.md).
