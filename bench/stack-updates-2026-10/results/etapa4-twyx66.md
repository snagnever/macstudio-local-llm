# Etapa 4 — twyx iQ-MLX-6.6bpw × iQ 4.7bpw no mlx-serve 26.10.3 (2026-10-22)

`n2z` = ddalcu iQ-MLX-4.7bpw `dafff5c`. `t6z` = twyx iQ-MLX-6.6bpw `884894d`. Os dois rodam no mlx-serve 26.10.3 com as flags do `n2`. Só a banda de 32K rodou, com 3 reps.

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| n2z | 32K | 8.1 s | 34.5 s | 1.80 s | 0.96/0.96 | 80.6 | 0.674 | 100.6 GB | 0.00 GB | 0 | 13/13 |
| t6z | 32K | 10.2 s | 42.8 s | 2.10 s | 0.96/0.96 | 63.4 | 0.628 | 118.0 GB | 0.91 GB | 0 | 13/13 |

- n2z @ 32K: livre mínimo 0.06 GB; gates passa.
- t6z @ 32K: livre mínimo 0.01 GB; gate **swap > 0.5 GB** falha; alerta wired > 102 GB.

| razão `T_turno(t6z) / T_turno(n2z)` | 32K |
|---|---:|
| t6z | 1.259 |

## Veredito

Não adotar o twyx 6.6bpw. Já a 32K ele falha no gate de swap (Δ 0.91 GB, wired 118 GB) e fica 26% mais lento que o iQ 4.7bpw (`T_turno` 10.2 contra 8.1 s; decode 63.4 contra 80.6 tok/s). A regra pedia gates nas três bandas e `T_turno ≤ 1.10 ×` o `n2z` a 128K.

## Leitura

- As bandas de 128K e 256K e a bateria de qualidade não rodaram. A decisão já estava tomada a 32K, e o KV maior das bandas longas só aumentaria o swap. A regra de parada da campanha é swap Δ > 2 GB.
- O mlx-serve limita os modelos residentes a 107.5 GB e o wired a 110100 MB. O pack carrega os pesos e mais a tabela n-gram de 29.8 GB no page cache. A soma passa da memória livre do rig de 128 GB.
- O ganho de qualidade (KLD 0.0023 contra 0.0041, do card do pack) não foi medido no rig. O bf16 do Flash-Next não cabe em 128 GB, e a bateria foi cortada.
- O pack foi apagado do disco depois da banda de 32K. O recibo do download está em `results/downloads.json`.
