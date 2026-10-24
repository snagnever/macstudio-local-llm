# Etapa 6 — GSQ-RCO-Coder-MLX no oMLX 0.7.2 × w1 (2026-10-23)

`r1` = `mbrown-uno/Qwen3.8-Flash-Next-GSQ-RCO-Coder-MLX` `50fa68c`, com 256 dos 512 experts e uma cabeça MTP Lightning enxertada, no oMLX 0.7.2 (arm `FG`, MLX 0.32.4). A referência é o `w1` (Swift 1.5 no mlx-serve 26.10.1). A velocidade do `w1` vem do Task 1. A bateria do `w1` rodou de novo nesta etapa, no mesmo dia do `r1`.

## Velocidade

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| r1 | 32K | 10.5 s | 51.0 s | 2.40 s | 0.94/0.96 | 63.0 | — | 60.1 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| w1 | 32K | 8.0 s | 34.5 s | 1.80 s | 0.96/0.96 | 83.1 | 0.689 | 96.9 GB | -0.01 GB | 0 | 12/13 (1 trunc) |
| r1 | 128K | 12.2 s | 250.3 s | 3.20 s | 0.99/0.99 | 57.0 | — | 68.0 GB | 0.00 GB | 0 | 13/13 |
| w1 | 128K | 8.7 s | 165.6 s | 2.00 s | 0.99/0.99 | 76.1 | 0.733 | 110.9 GB | 0.00 GB | 0 | 12/13 (1 trunc) |

| razão `T_turno(r1) / T_turno(w1)` | 32K | 128K |
|---|---:|---:|
| r1 | 1.312 | 1.402 |

`decide.py --mode le --threshold 0.97`: VERDICT: fail.

## Qualidade (`run-battery.sh`, perfil t1, xhigh, 131072)

| suíte | métrica | w1 | r1 |
|---|---|---:|---:|
| HumanEval | acertos | 141/164 | **154/164** |
| HumanEval | tempo mediano | 5.3 s | 6.9 s |
| HumanEval | reasoning mediano | 1098 chars | 1547 chars |
| LiveCodeBench | acertos | 46/50 | 45/50 |
| LiveCodeBench | tempo mediano | 19.7 s | 35.0 s |
| LiveCodeBench | reasoning mediano | 4435 chars | 8931 chars |

`summarize_ab.py`: G1 (qualidade) passa nas duas suítes. G2 (thinking) falha no LiveCodeBench, porque o `r1` raciocina cerca de 2 vezes mais.

## Tool calls (`toolcall-probe.sh`, 5 sessões × 4 turnos)

| `frequency_penalty` | turnos | sessões | mediana por turno |
|---:|---:|---:|---:|
| 0 | 20/20 | 5/5 | 1.45 s |
| 1 | 19/20 | 4/5 | 1.64 s |

## Veredito

Não adotar o `r1` como perfil "código". Ele passa na qualidade: HumanEval +8 pontos (93.9% contra 86.0%), LiveCodeBench −2 pontos (90% contra 92%, no limite da regra), e tool calls em 20/20 com penalidade 0. Mas é 31% mais lento que o `w1` a 32K e 40% mais lento a 128K, e a regra pedia `T_turno ≤ 0.97 ×`. O ganho é de memória: 60–68 GB wired contra 97–111 GB.

## Leitura

- O decode cai para 57–63 tok/s. O card mede 94.9 tok/s com MTP num M5 Max. O probe não registra a aceitação do MTP Lightning do oMLX.
- O prefill a frio é 50% mais lento a 128K (250 contra 166 s). Uma parte pode vir da tabela n-gram de 38 GB lida do SSD (`qwen4_ple_ssd_offload`). Isso não foi isolado.
- O `r1` deixa ~60 GB livres. Ele pode servir num perfil que roda ao lado de outro modelo, mas não como driver único.
