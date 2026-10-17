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
