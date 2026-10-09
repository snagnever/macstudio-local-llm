# Veredito — Flash-Next updates 2026-10 (mlx-serve 26.10.1 × pack iQ-MLX-4.7bpw)

**O driver diário troca de runtime e de pesos.** O mlx-serve 26.10.1 corta o `T_turno` em 27% contra o
26.9.2 com os mesmos pesos, nas duas bandas. O pack `iQ-MLX-4.7bpw` empata com o `mixed-4-8bit` em
velocidade (±1%) e não perde na qualidade barata. O par novo é **mlx-serve 26.10.1 + ddalcu iQ-MLX-4.7bpw**.

Máquina: Mac Studio M4 Max 128 GB. Data: 2026-10-07. Perfil do probe: `temperature=1.0`, `top_p=0.95`,
`top_k=20`, reasoning `xhigh`, limite 4096 tokens, 3 reps. Config igual nos três braços: `--mtp`,
`--ssm-checkpoint-max 16`, prefix cache 16 GB / 100 GB / 64, KV sem quantização.

| braço | runtime | pesos |
| --- | --- | --- |
| c1 | 26.9.2 | `mixed-4-8bit` @ ef5b919 |
| n1 | 26.10.1 | `mixed-4-8bit` @ ef5b919 |
| n2 | 26.10.1 | `iQ-MLX-4.7bpw` @ dafff5c |

## Velocidade (Etapa 1)

| banda | braço | T_turno | cold TTFT | warm TTFT tool_turn | hit append / tool_turn | decode quente | MTP aceitação | wired pico | needles |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |
| 32K | c1 | 11.4 s | 37.1 s | 1.9 s | 0.96 / 0.96 | 48.8–58.7 | 0.504 | 98.1 GB | 39/39 |
| 32K | n1 | 8.3 s | 34.6 s | 1.9 s | 0.96 / 0.96 | 76.7–84.4 | 0.813 | 96.8 GB | 39/39 |
| 32K | n2 | 8.3 s | 34.8 s | 1.9 s | 0.96 / 0.96 | 72.3–91.3 | 0.807 | 97.7 GB | 39/39 |
| 128K | c1 | 12.1 s | 178.0 s | 2.1 s | 0.99 / 0.99 | 45.0–59.0 | 0.572 | 109.0 GB | 39/39 |
| 128K | n1 | 8.8 s | 165.7 s | 1.9 s | 0.99 / 0.99 | 69.3–77.1 | 0.649 | 110.5 GB | 39/39 |
| 128K | n2 | 8.9 s | 165.1 s | 1.9 s | 0.99 / 0.99 | 69.5–84.7 | 0.696 | 111.6 GB | 39/39 |

| razão de `T_turno` | 32K | 128K | critério | resultado |
| --- | ---: | ---: | --- | --- |
| n1 / c1 (runtime) | 0.73 | 0.73 | ≤ 1.03 | promove 26.10.1 |
| n2 / n1 (pesos) | 1.00 | 1.01 | \|r − 1\| ≤ 0.03 | paridade |

O ganho do runtime vem do decode. A aceitação do MTP sobe de 0.50 para 0.81 a 32K e de 0.57 para 0.65 a 128K.
O prefill sobe só 7%, e o cold TTFT cai 7% a 128K.

## Qualidade barata (Etapa 2)

Mesmo runtime 26.10.1, perfil `daily`, temp 0. Detalhe por item em [quality-n1-n2.md](quality-n1-n2.md).

| bateria | n1 | n2 | n2 − n1 | limite |
| --- | ---: | ---: | ---: | --- |
| HumanEval (164) | 151 | 154 | +3 | ≥ −2 |
| Tool-calling jdhodges + Veerman | 47/52 | 47/52 | 0 | ≥ −1 |

164 problemas não separam a diferença publicada de 0.7 pp de top-1. Este teste só pega regressão grande.

## Gates

Os três braços passam em todos os gates nas duas bandas: zero erro HTTP, todas as needles corretas,
hit ≥ 0.90 em `append` e `tool_turn`, swap delta 0 e `[spec-stats]` no log. O alerta `wired>102` aparece
nos três braços a 128K, inclusive no c1. Ele não muda a comparação.

O smoke de 8K (`etapa0-smoke.md`) registrou um erro de needles do n2 no `tool_turn`. Esse erro não se repetiu
nas 6 amostras de `tool_turn` do n2 a 32K e 128K.

## O que não foi medido

- O efeito do 26.9.6 sobre o thinking de turnos anteriores num agente real (Terminal-Bench, OpenCode).
- A fidelidade do pack `iQ` contra os pesos de referência (KL, top-1). Só a qualidade barata acima.
- Contexto acima de 128K. O perfil `512k` do launcher foi medido no 26.9.2 e não foi re-medido.
- O `--ple-gpu`: o servidor recusa a flag nesta máquina por falta de memória ([etapa-p.md](etapa-p.md)).

Dados: `{c1,n1,n2}-{32768,131072}-t1.0-ab.jsonl`, `summary-etapa1.json`, `quality-n1-n2.md`.
