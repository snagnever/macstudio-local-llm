# Etapa 2 — 512K (524288 tokens) e escolha do KV (2026-10-24)

## Varredura, 1 rep (tag `sw`)

| braço | T_turno | cold TTFT | warm TTFT id/app/tool | hit id/app/tool | decode | wired peak | folga | swap Δ | gates |
|---|---:|---:|---|---|---:|---:|---:|---:|---|
| k2a (KV int8) | 6.7 s | 743.3 s | 0.1/1.7/1.8 s | 1.00/1.00/1.00 | 105.6 | 116.1 GB | 10.5 GB | 0 | passa |
| k2ab (KV bf16) | 7.8 s | 770.7 s | 1.9/2.0/2.0 s | 1.00/1.00/1.00 | 88.8 | 110.0 GB | 16.7 GB | 0 | passa |
| w1zq4 (mlx-serve, KV 4-bit, YaRN 2.0) | 11.8 s | 782.6 s | 0.8/2.7/2.7 s | 1.00/1.00/1.00 | 56.6 | 113.6 GB | 5.0 GB | 0 | passa |

- **Folga** = 128 GB − wired peak − compressor peak (ruling do Task 1).
- O Splash guarda o KV dos pedidos longos no cache em SSD (`--max-context` 524288). Com KV bf16, parte do KV fica fora da memória residente. Isso explica o wired menor, o warm TTFT identical de 1.9 s e o decode menor do `k2ab`.
- O `k2a` montou o fixture de 512K em 47 min, com o `build_fixture` antigo. A partir do `k2ab`, a versão por bisseção montou o fixture em 22 s, com o mesmo texto e os mesmos tokens. A medida de velocidade não muda, porque o fixture fica pronto antes da primeira requisição.

## Escolha: `kv512 = int8`, braço Swift `k2a`

O `k2ab` passa nos gates e no gate de folga, mas o `T_turno` dele é 1.16 × o do `k2a` (7.8 contra 6.7 s). A regra pede ≤ 1.05 ×. Os Tasks 2 (3 reps), 3 e 4 usam o `k2a`.

## 3 reps

Pendente (fila `t2b`: `k2a`, `w1zq4`, `k1a`).
