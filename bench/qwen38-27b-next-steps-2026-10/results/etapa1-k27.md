## Etapa 1: k27 vs s27r (xhigh)

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| k27 | 32K | 13.3 s | 76.3 s | 3.90 s | 0.96/0.96 | 54.7 | — | 42.2 GB | -0.03 GB | 0 | 12/13 (1 trunc) |
| s27r | 32K | 17.0 s | 109.9 s | 5.40 s | 0.94/0.96 | 44.0 | — | 43.3 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| k27 | 128K | 17.7 s | 535.1 s | 7.40 s | 0.99/0.99 | 49.8 | — | 53.8 GB | -0.03 GB | 0 | 13/13 |
| s27r | 128K | 25.7 s | 712.6 s | 9.80 s | 0.97/0.99 | 32.3 | — | 55.4 GB | -0.04 GB | 0 | 13/13 |

- k27 @ 32K: livre mínimo 13.66 GB; gates passa; alertas —
- s27r @ 32K: livre mínimo 0.06 GB; gates passa; alertas —
- k27 @ 128K: livre mínimo 0.81 GB; gates passa; alertas —
- s27r @ 128K: livre mínimo 0.06 GB; gates passa; alertas —

| razão `T_turno(k27) / T_turno(s27r)` | 128K |
|---|---:|
| k27 | 0.689 |

Regra: ≤ 0.75 em 128K, gates do candidato e da base, `[spec-stats]`, ignorando hit_append, hit_tool_turn.
VERDICT: pass

## Etapa 1: k27 (xhigh)

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| k27 | 32K | 13.3 s | 76.3 s | 3.90 s | 0.96/0.96 | 54.7 | — | 42.2 GB | -0.03 GB | 0 | 12/13 (1 trunc) |
| k27 | 128K | 17.7 s | 535.1 s | 7.40 s | 0.99/0.99 | 49.8 | — | 53.8 GB | -0.03 GB | 0 | 13/13 |

- k27 @ 32K: livre mínimo 13.66 GB; gates passa; alertas —
- k27 @ 128K: livre mínimo 0.81 GB; gates passa; alertas —

## Etapa 1: k27 (medium)

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| k27 | 32K | 10.4 s | 76.1 s | 3.90 s | 0.96/0.96 | 79.3 | — | 42.0 GB | 0.00 GB | 0 | 13/13 |
| k27 | 128K | 15.9 s | 534.4 s | 7.40 s | 0.99/0.99 | 60.5 | — | 53.5 GB | 0.00 GB | 0 | 13/13 |

- k27 @ 32K: livre mínimo 14.73 GB; gates passa; alertas —
- k27 @ 128K: livre mínimo 1.04 GB; gates passa; alertas —


## Respostas vazias (think_turn_probe)
empty=0 of 20 stop records
