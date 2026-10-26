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

## 3 reps (tag `lc`)

| braço | T_turno | cold TTFT | warm TTFT id/app/tool | hit id/app/tool | decode | wired peak | folga | swap Δ | needles | razão vs w1zq4 |
|---|---:|---:|---|---|---:|---:|---:|---:|---|---:|
| k2a | 6.7 s | 744.5 s | 0.1/1.8/1.9 s | 1.00/1.00/1.00 | 106.6 | 116.4 GB | 10.1 GB | 0 | 13/13 | 0.528 |
| k1a | 7.4 s | 784.4 s | 0.2/1.9/1.9 s | 1.00/1.00/1.00 | 94.3 | 116.7 GB | 9.2 GB | -0.03 GB | 8/13 (5 trunc) | 0.583 |
| w1zq4 | 12.7 s | 784.2 s | 1.4/4.0/3.7 s | 1.00/1.00/1.00 | 57.0 | 113.8 GB | 3.8 GB | 0 | 13/13 | — |

- `decide.py --mode le --threshold 0.97 --ctx 524288 --base w1zq4`: `k2a` pass, `k1a` pass.
- O `w1zq4` comprime ~9 GB de memória, como o `w1z`. Por isso a folga dele é a menor das três.
- O `k1a` esgotou as 4096 tokens de raciocínio em 5 de 13 turnos (`length`). O `k2a` e o `w1zq4` não truncaram nenhum. Isso repete o padrão do `k1a` a 8K (3 trunc) e indica que o Flash Next base pensa mais longe que o Swift em contexto longo.

## Veredito de velocidade e folga a 512K

A regra "aceitável a 512K" pede gates, folga ≥ 2 GB e `T_turno` ≤ 13.3 s. Ela vale aqui só para velocidade e folga. O critério de qualidade fecha no Task 4.

| braço | gates | folga ≥ 2 GB | T_turno ≤ 13.3 s | veredito parcial |
|---|---|---|---|---|
| k2a | passa | 10.1 GB | 6.7 s | aceitável |
| k1a | passa | 9.2 GB | 7.4 s | aceitável (needles 8/13 por truncamento) |
| w1zq4 | passa | 3.8 GB | 12.7 s | aceitável, perto do limite |
