# Etapa 9 — GSQ-RCO-Coder no mlx-serve 26.10.3 (`r1z` × `r1`, `w1`) (2026-10-23)

`r1z` = o pack do `r1` (`mbrown-uno/Qwen3.8-Flash-Next-GSQ-RCO-Coder-MLX` `50fa68c`, formato oMLX) no mlx-serve 26.10.3, com as flags do `n2`. O mlx-serve carregou o pack nativamente. O boot log mostra a tabela n-gram de 5 bits (35.8 GB, em mmap) e a cabeça MTP ("1 hyper-connected QSA+MoE layer"), com `[spec-stats]` presentes. A qualidade vem da bateria do `r1` (Task 6), porque os pesos são os mesmos.

## Velocidade

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| w1 | 32K | 8.0 s | 34.5 s | 1.80 s | 0.96/0.96 | 83.1 | 0.689 | 96.9 GB | -0.01 GB | 0 | 12/13 (1 trunc) |
| r1 | 32K | 10.5 s | 51.0 s | 2.40 s | 0.94/0.96 | 63.0 | — | 60.1 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| r1z | 32K | 8.8 s | 34.0 s | 1.70 s | 0.96/0.96 | 72.0 | 0.612 | 68.3 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| w1 | 128K | 8.7 s | 165.6 s | 2.00 s | 0.99/0.99 | 76.1 | 0.733 | 110.9 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| r1 | 128K | 12.2 s | 250.3 s | 3.20 s | 0.99/0.99 | 57.0 | — | 68.0 GB | 0.00 GB | 0 | 13/13 |
| r1z | 128K | 9.7 s | 170.0 s | 2.00 s | 0.99/0.99 | 65.8 | 0.785 | 77.9 GB | 0.00 GB | 0 | 13/13 |

| razão `T_turno(cand) / T_turno(w1)` | 32K | 128K |
|---|---:|---:|
| r1 (oMLX 0.7.2) | 1.312 | 1.402 |
| r1z (mlx-serve 26.10.3) | 1.100 | 1.115 |

`decide.py --mode le --threshold 0.97`: VERDICT: fail (`r1z`).

## Tool calls (`toolcall-probe.sh r1z`)

| `frequency_penalty` | turnos | sessões | mediana por turno |
|---:|---:|---:|---:|
| 0 | 20/20 | 5/5 | 1.64 s |
| 1 | 12/14 | **0/5** | 2.00 s |

Com penalidade 1, as respostas finais perdem os valores dos tool results em todas as sessões. Em dois primeiros turnos, o nome ou os argumentos da tool chegam errados (`read_Fixtre`, falta `path`). É o mesmo efeito que o `w1z` mostrou no Task 1: a 26.10.3 aplica a penalidade, e um raciocínio longo degenera. O `tool_loop.py` saiu com 2, e a fila registrou `rc=2`.

## Veredito

Não adotar o `r1z` como perfil "código". O mlx-serve corta o atraso do pack de 31–40% para 10–12% contra o `w1`. O prefill a frio fica igual ao do `w1`, e o MTP funciona (aceitação 0.61–0.79). Mas a regra pedia `T_turno ≤ 0.97 ×` o `w1`. O ganho continua sendo memória: 68–78 GB wired contra 97–111 GB, com a qualidade do Task 6 (HumanEval 154/164 contra 141).

## Leitura

- A maior parte da lentidão do `r1` vinha do oMLX 0.7.2, não do modelo. O prefill a frio a 128K cai de 250 s (oMLX) para 170 s (mlx-serve).
- Mesmo com metade dos experts, o decode fica 13% abaixo do `w1` (72 contra 83 tok/s a 32K). Esse pack raciocina cerca de 2 vezes mais no LiveCodeBench (Task 6), e o `T_turno` usa 512 tokens fixos. Então essa métrica não captura o custo real por tarefa.
