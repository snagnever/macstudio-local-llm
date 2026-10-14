# Etapa 1 — mlx-serve 26.10.2 × 26.10.1 no n2 (2026-10-14)

## 32K e 128K, 3 reps

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| n2 | 32K | 7.9 s | 34.5 s | 1.80 s | 0.96/0.96 | 84.3 | 0.651 | 96.7 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| n2x | 32K | 8.2 s | 34.6 s | 1.80 s | 0.96/0.96 | 80.0 | 0.645 | 99.7 GB | 0.00 GB | 0 | 13/13 |
| n2 | 128K | 8.9 s | 165.4 s | 2.00 s | 0.99/0.99 | 74.1 | 0.642 | 110.6 GB | 0.00 GB | 0 | 13/13 |
| n2x | 128K | 8.9 s | 165.7 s | 2.00 s | 0.99/0.99 | 74.0 | 0.775 | 106.4 GB | -0.02 GB | 0 | 13/13 |
| n2x | 256K | — | 350.8 s | — | 1.00/— | 61.9 | 0.000 | 113.7 GB | 0.00 GB | 1 | 4/5 |

- n2 @ 32K: livre mínimo 0.02 GB; gates passa; alertas —
- n2x @ 32K: livre mínimo 0.06 GB; gates passa; alertas —
- n2 @ 128K: livre mínimo 0.03 GB; gates passa; alertas wired>102
- n2x @ 128K: livre mínimo 0.01 GB; gates passa; alertas wired>102
- n2x @ 256K: livre mínimo 0.03 GB; gates passa; alertas wired>102

| razão `T_turno(n2x) / T_turno(n2)` | 32K | 128K |
|---|---:|---:|
| n2x | 1.038 | 1.000 |

Regra: ≤ 0.97 em 32K, 128K, gates do candidato e da base, `[spec-stats]`.
VERDICT: fail (razão 1.038 @32K; razão 1.000 @128K)

## 256K informativo (n2@26.10.1: 9.8 s)

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| n2x | 256K | — | 350.8 s | — | 1.00/— | 61.9 | 0.000 | 113.7 GB | 0.00 GB | 1 | 4/5 |

- n2x @ 256K: livre mínimo 0.03 GB; gates passa; alertas wired>102

## Thinking reenviado e 1º prompt pós-load

| braço | contexto | cenário | modo | n | TTFT s | hit | cached | prompt | decode | needles | erros |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| n2 | 32K | first_after_load | - | 1 | 0.73 | 0.00 | 0.00 | 56.00 | 74.06 | — | 0 |
| n2 | 32K | tool_turn | drop | 3 | 1.86 | 0.96 | 27272.00 | 28373.00 | 81.59 | 3/3 | 0 |
| n2 | 32K | tool_turn | resend | 3 | 3.15 | 0.93 | 27272.00 | 29302.00 | 79.08 | 3/3 | 0 |
| n2 | 32K | turn1 | drop | 3 | 34.51 | 0.00 | 0.00 | 27303.00 | 83.23 | 3/3 | 0 |
| n2 | 32K | turn1 | resend | 3 | 34.54 | 0.00 | 0.00 | 27303.00 | 81.93 | 3/3 | 0 |
| n2 | 128K | first_after_load | - | 1 | 0.23 | 0.00 | 0.00 | 56.00 | 84.43 | — | 0 |
| n2 | 128K | tool_turn | drop | 3 | 2.39 | 0.99 | 125587.00 | 126688.00 | 76.62 | 3/3 | 0 |
| n2 | 128K | tool_turn | resend | 3 | 3.65 | 0.98 | 125587.00 | 127539.00 | 73.36 | 3/3 | 0 |
| n2 | 128K | turn1 | drop | 3 | 165.87 | 0.00 | 0.00 | 125618.00 | 74.40 | 3/3 | 0 |
| n2 | 128K | turn1 | resend | 3 | 165.88 | 0.00 | 0.00 | 125618.00 | 73.92 | 3/3 | 0 |
| n2x | 32K | first_after_load | - | 1 | 0.23 | 0.00 | 0.00 | 56.00 | 83.67 | — | 0 |
| n2x | 32K | tool_turn | drop | 3 | 1.84 | 0.96 | 27272.00 | 28373.00 | 80.94 | 3/3 | 0 |
| n2x | 32K | tool_turn | resend | 3 | 4.06 | 0.91 | 27272.00 | 30120.00 | 80.80 | 3/3 | 0 |
| n2x | 32K | turn1 | drop | 3 | 34.55 | 0.00 | 0.00 | 27303.00 | 85.98 | 3/3 | 0 |
| n2x | 32K | turn1 | resend | 3 | 34.56 | 0.00 | 0.00 | 27303.00 | 80.42 | 3/3 | 0 |

## Veredito

O mlx-serve 26.10.2 estável não substitui o 26.10.1 no driver secundário. A razão de `T_turno` foi 1.038 a 32K e 1.000 a 128K. O resultado reprova pela regra do plano (≤ 0.97×) e também pela regra de runtime estável do repo (≤ 1.03×). O driver principal `w1` fica no 26.10.1 sem smoke no 26.10.2 (Step 9 pulado). `driver-arms.env` fixa `RT=26.10.1` para as tasks seguintes.

## Leitura

- **Decode e memória.** O 26.10.2 decodifica 5% mais devagar a 32K (80.0 contra 84.3 tok/s) e usa 3 GB a mais de wired. A 128K o decode empata (74.0 contra 74.1), e o wired do 26.10.2 fica abaixo (106.4 contra 110.6 GB). TTFT frio, TTFT quente e hit são iguais nas duas bandas. **medido-no-rig**
- **MTP.** A aceitação a 128K sobe de 0.642 para 0.775 no 26.10.2, sem ganho de decode. A 32K as duas ficam em ~0.65. **medido-no-rig**
- **256K.** O 26.10.2 recusou o prefill do `tool_turn` (`PrefillDoesNotFit`: ~11.1 GB pedidos, ~10.0 GB livres). Os outros quatro cenários passaram, com cold de 350.8 s. O `n2` no 26.10.1 passou os cinco cenários a 256K em 2026-10-11 (9.8 s). A causa provável é o estado GDN em f32 do 26.10.2 (#815), que ocupa o dobro desse estado. **medido-no-rig**
- **Thinking reenviado.** Nenhum dos dois runtimes reaproveita o thinking do `turn1`: o `cached` do `tool_turn` fica na base nos modos `resend` e `drop`. Reenviar o thinking só aumenta o TTFT: 1.86 → 3.15 s (26.10.1) e 1.84 → 4.06 s (26.10.2) a 32K; 2.39 → 3.65 s no 26.10.1 a 128K. Clientes que reenviam `reasoning_content` pagam esse custo. **medido-no-rig**
- **1º prompt pós-load.** O TTFT ficou em 0.23 s em três loads e em 0.73 s no primeiro load do `n2` a 32K. Não há diferença consistente entre os runtimes. **medido-no-rig**
- **Tempo de banda.** A 128K cada braço levou ~15 min, com 3 reps. As ~3 h por banda da campanha 27B não se repetem no Flash-Next.
- **Smoke do pre-release.** O smoke de 8K do pre-release.1, feito em 13/10, saiu dos resultados e está em `logs/prerelease-smoke/`, no rig.
