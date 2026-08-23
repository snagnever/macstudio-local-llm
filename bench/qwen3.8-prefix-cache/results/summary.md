# Qwen3.8 prefix-cache campaign summary

> Generated: 2026-08-23T20:11:01.363829+00:00

## Runtime gates

| Arm | Runtime | Records | Status | Complete | Failures |
|---|---|---:|---|---|---|
| A | mlx-serve | 15 | FAIL | no | correct, error |
| B | mlx-serve | 30 | FAIL | no | cache_hit_ratio, correct, error |
| C | mlx-serve | 15 | FAIL | no | correct, error |
| D | llama.cpp | 15 | FAIL | no | correct, error |
| E | llama.cpp | 30 | FAIL | no | cache_hit_ratio, correct, error |
| F | llama.cpp | 15 | FAIL | no | correct, error |
| G | llama.cpp | 15 | FAIL | no | correct, error |
| H | llama.cpp | 15 | FAIL | no | correct, error |
| I | oMLX | 15 | FAIL | no | correct, error |
| J | oMLX | 15 | FAIL | no | correct, error |
| K | oMLX | 15 | PASS | no | — |
| L | oMLX | 15 | PASS | no | — |

## Measurements

| Runtime | Arm | Context | Scenario | N | TTFT median ms | E2E median ms | Cache hit median | Failed records |
|---|---|---:|---|---:|---:|---:|---:|---:|
| llama.cpp | D | 8192 | append | 3 | 25268.47 | 123671.77 | 0.0000 | 3 |
| llama.cpp | D | 8192 | cold | 3 | 20619.68 | 58942.48 | 0.0000 | 0 |
| llama.cpp | D | 8192 | identical | 3 | 20575.77 | 58904.55 | 0.0000 | 0 |
| llama.cpp | D | 8192 | middle_mutation | 3 | 20713.33 | 118650.96 | 0.0000 | 3 |
| llama.cpp | D | 8192 | tool_turn | 3 | 25338.24 | 56949.55 | 0.0000 | 0 |
| llama.cpp | E | 32768 | append | 3 | 6129.29 | 115726.37 | 0.9659 | 2 |
| llama.cpp | E | 32768 | cold | 3 | 141517.42 | 207047.73 | 0.0000 | 0 |
| llama.cpp | E | 32768 | identical | 3 | 174.87 | 65187.48 | 0.9999 | 0 |
| llama.cpp | E | 32768 | middle_mutation | 3 | 141267.60 | 179745.99 | 0.0020 | 1 |
| llama.cpp | E | 32768 | tool_turn | 3 | 6208.84 | 61281.45 | 0.9647 | 0 |
| llama.cpp | E | 8192 | append | 3 | 4921.25 | 103298.83 | 0.8212 | 3 |
| llama.cpp | E | 8192 | cold | 3 | 20623.92 | 58895.63 | 0.0000 | 0 |
| llama.cpp | E | 8192 | identical | 3 | 150.16 | 38434.76 | 0.9992 | 0 |
| llama.cpp | E | 8192 | middle_mutation | 3 | 20423.27 | 118379.21 | 0.0123 | 3 |
| llama.cpp | E | 8192 | tool_turn | 3 | 4966.72 | 36432.49 | 0.8158 | 3 |
| llama.cpp | F | 32768 | append | 3 | 6337.18 | 127321.92 | 0.9659 | 1 |
| llama.cpp | F | 32768 | cold | 3 | 145224.89 | 216467.99 | 0.0000 | 0 |
| llama.cpp | F | 32768 | identical | 3 | 193.12 | 71834.76 | 0.9999 | 0 |
| llama.cpp | F | 32768 | middle_mutation | 3 | 144964.91 | 188283.09 | 0.0020 | 1 |
| llama.cpp | F | 32768 | tool_turn | 3 | 6427.95 | 75876.82 | 0.9647 | 0 |
| llama.cpp | G | 32768 | append | 3 | 6156.58 | 125754.72 | 0.9659 | 2 |
| llama.cpp | G | 32768 | cold | 3 | 140052.70 | 226811.40 | 0.0000 | 0 |
| llama.cpp | G | 32768 | identical | 3 | 197.04 | 86530.60 | 0.9999 | 0 |
| llama.cpp | G | 32768 | middle_mutation | 3 | 141167.69 | 199984.51 | 0.0020 | 0 |
| llama.cpp | G | 32768 | tool_turn | 3 | 6223.03 | 58412.51 | 0.9647 | 0 |
| llama.cpp | H | 32768 | append | 3 | 5929.04 | 93613.37 | 0.9659 | 0 |
| llama.cpp | H | 32768 | cold | 3 | 135794.73 | 172377.28 | 0.0000 | 0 |
| llama.cpp | H | 32768 | identical | 3 | 170.25 | 37163.47 | 0.9999 | 0 |
| llama.cpp | H | 32768 | middle_mutation | 3 | 135444.74 | 211255.97 | 0.0020 | 1 |
| llama.cpp | H | 32768 | tool_turn | 3 | 6041.59 | 50585.65 | 0.9647 | 0 |
| mlx-serve | A | 8192 | append | 3 | 20946.32 | 146865.16 | 0.0000 | 3 |
| mlx-serve | A | 8192 | cold | 3 | 17234.30 | 63826.77 | 0.0000 | 0 |
| mlx-serve | A | 8192 | identical | 3 | 17244.57 | 63989.39 | 0.0000 | 0 |
| mlx-serve | A | 8192 | middle_mutation | 3 | 17256.45 | 142559.39 | 0.0000 | 3 |
| mlx-serve | A | 8192 | tool_turn | 3 | 21116.01 | 53766.25 | 0.0000 | 0 |
| mlx-serve | B | 32768 | append | 3 | 5912.72 | 140916.98 | 0.9650 | 3 |
| mlx-serve | B | 32768 | cold | 3 | 116556.35 | 206288.23 | 0.0000 | 0 |
| mlx-serve | B | 32768 | identical | 3 | 584.91 | 69508.81 | 0.9989 | 0 |
| mlx-serve | B | 32768 | middle_mutation | 3 | 87526.02 | 171319.49 | 0.2789 | 1 |
| mlx-serve | B | 32768 | tool_turn | 3 | 6039.60 | 141074.38 | 0.9638 | 2 |
| mlx-serve | B | 8192 | append | 3 | 4735.43 | 130594.10 | 0.8165 | 3 |
| mlx-serve | B | 8192 | cold | 3 | 17103.39 | 63219.73 | 0.0000 | 0 |
| mlx-serve | B | 8192 | identical | 3 | 420.66 | 60193.53 | 0.9935 | 0 |
| mlx-serve | B | 8192 | middle_mutation | 3 | 17369.28 | 142714.89 | 0.0000 | 3 |
| mlx-serve | B | 8192 | tool_turn | 3 | 4862.09 | 39513.04 | 0.8112 | 3 |
| mlx-serve | C | 32768 | append | 3 | 5836.53 | 63050.34 | 0.9650 | 2 |
| mlx-serve | C | 32768 | cold | 3 | 116717.44 | 141154.32 | 0.0000 | 0 |
| mlx-serve | C | 32768 | identical | 3 | 511.35 | 26299.53 | 0.9989 | 0 |
| mlx-serve | C | 32768 | middle_mutation | 3 | 87636.87 | 144183.42 | 0.2789 | 2 |
| mlx-serve | C | 32768 | tool_turn | 3 | 5963.54 | 49246.04 | 0.9638 | 1 |
| oMLX | I | 8192 | append | 3 | 23402.04 | 149429.39 | 0.0000 | 3 |
| oMLX | I | 8192 | cold | 3 | 19163.47 | 60351.59 | 0.0000 | 0 |
| oMLX | I | 8192 | identical | 3 | 19180.46 | 60607.09 | 0.0000 | 0 |
| oMLX | I | 8192 | middle_mutation | 3 | 19308.02 | 144896.69 | 0.0000 | 3 |
| oMLX | I | 8192 | tool_turn | 3 | 23536.46 | 73921.12 | 0.0000 | 0 |
| oMLX | J | 8192 | append | 3 | 23264.57 | 87508.81 | 0.0000 | 1 |
| oMLX | J | 8192 | cold | 3 | 19054.19 | 53729.84 | 0.0000 | 0 |
| oMLX | J | 8192 | identical | 3 | 19051.35 | 53796.53 | 0.0000 | 0 |
| oMLX | J | 8192 | middle_mutation | 3 | 19180.19 | 97591.29 | 0.0000 | 2 |
| oMLX | J | 8192 | tool_turn | 3 | 23400.22 | 59676.59 | 0.0000 | 0 |
| oMLX | K | 32768 | append | 3 | 8322.18 | 26206.10 | 0.9456 | 0 |
| oMLX | K | 32768 | cold | 3 | 126119.43 | 136092.31 | 0.0000 | 0 |
| oMLX | K | 32768 | identical | 3 | 3450.32 | 13630.01 | 0.9789 | 0 |
| oMLX | K | 32768 | middle_mutation | 3 | 68068.63 | 79621.61 | 0.4887 | 0 |
| oMLX | K | 32768 | tool_turn | 3 | 8505.84 | 20088.61 | 0.9444 | 0 |
| oMLX | L | 32768 | append | 3 | 8575.45 | 16070.02 | 0.9456 | 0 |
| oMLX | L | 32768 | cold | 3 | 129076.17 | 134908.15 | 0.0000 | 0 |
| oMLX | L | 32768 | identical | 3 | 3567.02 | 10478.08 | 0.9789 | 0 |
| oMLX | L | 32768 | middle_mutation | 3 | 69821.61 | 75454.96 | 0.4887 | 0 |
| oMLX | L | 32768 | tool_turn | 3 | 8758.66 | 15764.58 | 0.9444 | 0 |

## SpecPrefill gate

| Arm | Baseline | Status | Advance to 65K | Failures |
|---|---|---|---|---|
| M | L | FAIL | no | missing_16384, missing_32768, prompt_work_mode, static_prefix, tool_loop |
| N | L | FAIL | no | missing_16384, missing_32768, prompt_work_mode, static_prefix, tool_loop |

## ANE prefill gate

| Arm | Baseline | Status | Confirmed operations | Failures |
|---|---|---|---:|---|
| O | J | INCONCLUSIVE | 0 | missing_16384, missing_32768, ttft |

## mlx-dspark Gate 8

| Arm | Status | 8K decode | 32K decode | 32K warm total | Failures |
|---|---|---:|---:|---:|---|
| R | INCONCLUSIVE | 0.000 | 0.000 | — | pairs, tool_loop |
| S | INCONCLUSIVE | 0.000 | 0.000 | — | pairs, tool_loop |
