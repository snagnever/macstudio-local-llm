# Etapa 3 — 1M (1000000 tokens) (2026-10-24)

O Splash 1.4.0 aceita `--max-context` até 1010000, e a banda usa 1000000. Acima de 262144 o Splash liga o YaRN sozinho. Com KV int8, o plano de memória do boot mantém residentes até ~860K tokens e manda o resto para o cache em SSD (32 GiB), ver [etapa0-splash-1m-boot](etapa0-splash-1m-boot.md). O fixture do `cache_probe` tem 994,527 tokens.

## Resultados

| braço | rep | T_turno | cold TTFT | warm TTFT id/app/tool | hit id/app/tool | decode | wired peak | folga | swap Δ | needles |
|---|---|---:|---:|---|---|---:|---:|---:|---:|---|
| k2a | 1 (`lc`) | 9.4 s | 1532.1 s | 2.5/2.6/2.7 s | 1.00/1.00/1.00 | 75.3 | 109.7 GB | 16.9 GB | 0 | 5/5 |
| k2a | 2 (`lc2`) | 9.3 s | 1532.3 s | 2.6/2.6/2.6 s | 1.00/1.00/1.00 | 76.7 | 109.7 GB | 16.9 GB | -0.01 GB | 4/5 (1 trunc) |
| k1a | 1 (`lc`) | 10.5 s | 1607.7 s | 2.5/2.6/2.6 s | 1.00/1.00/1.00 | 64.6 | 111.9 GB | 14.8 GB | 0 | 4/5 |
| w1z / w1zq4 | — | não rodou | | | | | | | | |

- **Folga** = 128 GB − wired peak − compressor peak (ruling do Task 1).
- O `w1z` não roda a 1M. O perfil 512k do mlx-serve (`w1zq4`) já fica com 3.8 GB de folga e `T_turno` de 12.7 s a 512K.
- A 1M, parte do KV fica no cache em SSD. O wired cai (110 contra 116 GB a 512K) e a folga sobe. Mas o warm TTFT sobe de 0.1–1.9 s para 2.5–2.7 s, e o decode cai de 106 para 75–77 tok/s.
- Um cold de 1M leva 25.5 min no `k2a` e 26.8 min no `k1a`. A estimativa do plano era 25–30 min.

## Mutação no meio do prompt

O cenário `middle_mutation` troca um trecho no meio do fixture. No Splash, o hit é 0 em todas as bandas, e o TTFT é igual ao cold. O log do Splash mostra o prefixo deduplicado ("deduplicated 497,248" a 1M), mas o prefill recomeça do zero.

| braço | contexto | cold TTFT | middle_mutation TTFT | hit |
|---|---:|---:|---:|---:|
| k2a | 256K | 351.1 s | 351.6 s | 0 |
| k2a | 512K | 744.5 s | 743.5 s | 0 |
| k2a | 1M | 1532.1 s | 1531.6 s | 0 |
| w1z | 256K | 350.7 s | 205.9 s | 0.45 |
| w1zq4 | 512K | 784.2 s | 587.8 s | 0.44 |

O mlx-serve reaproveita o prefixo antes do ponto trocado. Para um agente que compacta ou edita o histórico, uma mudança no meio custa 25 min de prefill no Splash a 1M.

## Escada de recuo

Não rodou. O `k2a` a 1000000 passa nos gates e no gate de folga, então o `k2as` e o 786432 não são necessários.

## Veredito de velocidade e folga a 1M

| braço | gates | folga ≥ 2 GB | T_turno ≤ 13.3 s | veredito parcial |
|---|---|---|---|---|
| k2a | passa (2 reps) | 16.9 GB | 9.3–9.4 s | aceitável |
| k1a | passa (1 rep) | 14.8 GB | 10.5 s | aceitável |

O critério de qualidade (G1 contra 262144 e longctx) fecha no Task 4.
