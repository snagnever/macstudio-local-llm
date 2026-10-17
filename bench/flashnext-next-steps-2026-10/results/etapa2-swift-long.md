# Etapa 2 — Swift 1.5 a 256K e 512K no mlx-serve 26.10.1 (2026-10-14)

## 256K (KV sem quantização) e 512K (YaRN 2.0 + KV 4-bit), 3 reps

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| w1 | 256K | 11.1 s | 350.8 s | 2.80 s | 1.00/1.00 | 61.7 | 0.686 | 114.9 GB | 0.00 GB | 0 | 11/13 |
| w1q4 | 512K | 13.3 s | 783.9 s | 3.80 s | 1.00/1.00 | 53.8 | 0.698 | 113.5 GB | 0.00 GB | 0 | 13/13 |

- w1 @ 256K: livre mínimo 0.02 GB; gates passa; alertas wired>102
- w1q4 @ 512K: livre mínimo 0.01 GB; gates passa; alertas wired>102

Referência iQ no 26.10.1: 256K 9.8 s (1 rep); 512K 13.0 s, wired 113.9 GB, livre mínimo 0.05 GB (n2q4, 3 reps).

Telemetria do boot log:

- `w1-262144-t1.0-e2-boot.log`: spec-stats=62 refused=0 oom=0
- `w1q4-524288-t1.0-e2-boot.log`: spec-stats=62 refused=0 oom=0

## Veredito

O perfil `512k` passa a usar o Swift 1.5. A banda de 512K (YaRN 2.0 + KV 4-bit) passou em todos os gates: 0 erros HTTP, needles 13/13, swap Δ 0.00 GB, 62 linhas `[spec-stats]`, nenhuma recusa e nenhum OOM. O `T_turno` foi 13.3 s, contra 13.0 s do iQ no mesmo perfil. A banda de 256K com KV sem quantização errou needles em 2 de 13 registros. Ela mede o perfil diário além do contexto configurado (131072), então não decide o perfil `512k`. Decisão registrada como ruling no ledger da campanha: a letra do plano pedia as duas bandas limpas.

## Leitura

- **256K, needles.** Os erros caíram num `cold` (needle de 50%) e num `append` (needles de 50% e 90%). Todos terminaram com `finish_reason=stop`, então não houve truncamento: o modelo respondeu errado. Os outros 11 registros acertaram os três needles. A amostragem é a do vendor (`temperature 1.0`), e o erro não se repetiu nos `identical` nem nos `tool_turn`. **medido-no-rig**
- **256K, velocidade.** `T_turno` 11.1 s, cold 350.8 s, decode 61.7 tok/s, wired 114.9 GB, livre mínimo 0.02 GB. O iQ no 26.10.1 tinha 9.8 s com 1 rep. **medido-no-rig**
- **512K.** `T_turno` 13.3 s, cold 783.9 s, decode 53.8 tok/s, wired 113.5 GB, livre mínimo 0.01 GB. Com o iQ foram 13.0 s, 113.9 GB e 0.05 GB. O Swift fica no mesmo limite de memória que o iQ. Feche apps pesados antes de usar o perfil. **medido-no-rig**
- **Qualidade com KV 4-bit.** Os needles são a única checagem de qualidade desta task. Pelo card, o YaRN estático degrada texto curto, por isso o perfil `512k` continua separado do diário.
- **Tempo.** A 256K, 3 reps levaram 33 min. A 512K levaram 67 min.
