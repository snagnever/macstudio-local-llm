# Parâmetros aceitáveis a 512K e 1M (2026-10-26)

A regra "aceitável" pede os gates do `decide.py`, folga ≥ 2 GB, `T_turno` ≤ 13.3 s, G1 contra o mesmo braço a 262144 e longctx ≥ 80%, no máximo 15 pontos abaixo da banda de 262144. Folga = 128 GB − wired peak − compressor peak.

| braço | contexto | flags | T_turno | folga | gates | G1 contra 262144 | longctx | aceitável |
|---|---:|---|---:|---:|---|---|---|---|
| k2a (Splash 1.4.0) | 524288 | `--max-context 524288 --verify-rows auto` (KV int8) | 6.7 s | 10.1 GB | passa | passa nas 6 | 100% | **sim** |
| k2a (Splash 1.4.0) | 1000000 | `--max-context 1000000 --verify-rows auto` (KV int8) | 9.3–9.4 s | 16.9 GB | passa | 5 de 6; HumanEval 1 abaixo da margem (ruído, decisão do usuário) | 100% a 1M | **sim** |
| k2ab (KV bf16) | 524288 | `k2a` + `--kv-format bf16` | 7.8 s | 16.7 GB | passa | — | — | não: 1.16 × o `T_turno` do `k2a` (regra ≤ 1.05 ×) |
| k1a (Flash Next base, Splash) | 524288 | `--verify-rows auto` | 7.4 s | 9.2 GB | passa | não medido | não medido | velocidade e folga sim; qualidade não medida |
| k1a | 1000000 | `--verify-rows auto` | 10.5 s | 14.8 GB | passa (1 rep) | não medido | não medido | velocidade e folga sim; qualidade não medida |
| w1zq4 (mlx-serve 26.10.3) | 524288 | `--kv-quant 4`, YaRN 2.0 | 12.7 s | 3.8 GB | passa | — | 100% | sim, perto do limite (perfil `512k` do driver diário) |
| w1zq4 / n2zq4 (mlx-serve 26.10.3) | 1000000 | `--kv-quant 4`, YaRN 3.815 | — | — | falha: 2 e 3 de 5 requisições com `PrefillDoesNotFit` | — | — | não ([etapa6](etapa6-n2z-1m.md)) |
| r1z / k3ma (GSQ) | > 262144 | — | — | — | — | — | — | fora do escopo (o usuário limitou o GSQ a 256K) |

O 1M passou, então a escada de recuo (`k2as`, 786432) não rodou.

O launcher `tools/scripts/serve-flashnext-splash.sh [256k|512k|1m]` serve o `k2a` com os flags acima, na porta 8585 e com `--idle-release off`. O driver diário (`serve-flashnext-daily-driver.sh`) não muda: a troca fica com o usuário.

Ressalvas para quem usa o perfil de 1M:
- um cold de 1M leva ~25 min;
- uma edição no meio do histórico ou uma ramificação antes do último estado salvo refaz o prefill inteiro ([etapa3](etapa3-1m.md), [etapa4](etapa4-quality.md));
- acima de 262144, o YaRN muda também as respostas a prompts curtos.
