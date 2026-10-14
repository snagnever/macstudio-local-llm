## Etapa 3: r27d vs s27r (xhigh)

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| r27d | 32K | 19.9 s | 109.0 s | 5.80 s | 0.96/0.96 | 36.3 | 0.461 | 59.3 GB | 0.00 GB | 0 | 13/13 |
| s27r | 32K | 17.0 s | 109.9 s | 5.40 s | 0.94/0.96 | 44.0 | — | 43.3 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| r27d | 128K | 44.7 s | 717.8 s | 10.80 s | 0.99/0.99 | 15.1 | 0.538 | 70.4 GB | 0.00 GB | 0 | 13/13 |
| s27r | 128K | 25.7 s | 712.6 s | 9.80 s | 0.97/0.99 | 32.3 | — | 55.4 GB | -0.04 GB | 0 | 13/13 |

- r27d @ 32K: livre mínimo 0.06 GB; gates passa; alertas —
- s27r @ 32K: livre mínimo 0.06 GB; gates passa; alertas —
- r27d @ 128K: livre mínimo 0.06 GB; gates passa; alertas —
- s27r @ 128K: livre mínimo 0.06 GB; gates passa; alertas —

| razão `T_turno(r27d) / T_turno(s27r)` | 32K | 128K |
|---|---:|---:|
| r27d | 1.171 | 1.739 |

Regra: ≤ 1.0 em 32K, 128K, gates do candidato e da base, `[spec-stats]`.
VERDICT: fail (razão 1.171 @32K; razão 1.739 @128K)

## Etapa 3: r27d (xhigh)

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| r27d | 32K | 19.9 s | 109.0 s | 5.80 s | 0.96/0.96 | 36.3 | 0.461 | 59.3 GB | 0.00 GB | 0 | 13/13 |
| r27d | 128K | 44.7 s | 717.8 s | 10.80 s | 0.99/0.99 | 15.1 | 0.538 | 70.4 GB | 0.00 GB | 0 | 13/13 |

- r27d @ 32K: livre mínimo 0.06 GB; gates passa; alertas —
- r27d @ 128K: livre mínimo 0.06 GB; gates passa; alertas —

## Etapa 3: r27d (medium)

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| r27d | 32K | 15.7 s | 108.4 s | 5.80 s | 0.96/0.96 | 51.9 | 0.792 | 63.0 GB | 0.00 GB | 0 | 13/13 |
| r27d | 128K | 34.8 s | 716.8 s | 10.80 s | 0.99/0.99 | 21.3 | 0.767 | 69.5 GB | 0.00 GB | 0 | 13/13 |

- r27d @ 32K: livre mínimo 0.06 GB; gates passa; alertas —
- r27d @ 128K: livre mínimo 0.06 GB; gates passa; alertas —

empty=0 of 5 stop records
