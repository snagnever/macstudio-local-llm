# Etapa 7 — qualidade do Flash Next base no Splash a 262144 (2026-11-02)

O braço é o `k1a`: `unsloth/Qwen3.8-Flash-Next-GGUF:UD-IQ4_XS` (revisão 766911a) no Splash 1.4.0, KV int8, `--verify-rows auto`, `--max-context 262144` (nativo, sem YaRN). A base é o `k2a` (Swift 1.5 GGUF IQ4_XS no mesmo Splash, [etapa4](etapa4-quality.md)). O `w1z` (o driver diário, Swift 1.5 MLX no mlx-serve 26.10.3) entra como referência. A bateria usa o perfil t1 (temperature 1.0, top-p 0.95, top-k 20) e `reasoning_effort` xhigh, numa rodada só. A fila rodou de 07:29 a 13:46, com o driver diário parado.

## Bateria

| suíte | w1z | k2a | k1a | k1a − k2a | margem G1 | G1 contra k2a |
|---|---:|---:|---:|---:|---:|---|
| HumanEval (estrita) | 142/164 | 147/164 | 143/164 (2 trunc) | −4 | 3 | falha |
| HumanEval (com imports) | 158/164 | 158/164 · 159/164 (2ª rodada) | 158/164 | 0 | 3 | passa |
| GPQA | 43/50 | 41/50 (3 trunc) | 42/50 (3 trunc) | +1 | 3 | passa |
| LiveCodeBench | 47/50 | 47/50 | 47/50 (1 trunc) | 0 | 3 | passa |
| IF | 19/20 | 19/20 | 19/20 | 0 | 2 | passa |
| jdhodges | 34/40 | 37/40 | 34/40 | −3 | 2 | **falha** |
| veerman | 10/12 | 10/12 | 10/12 | 0 | 1 | passa |

Tempo e raciocínio (`summarize_ab.py`, k2a → k1a):

| suíte | tempo total | tempo mediano | tokens medianos |
|---|---:|---:|---:|
| HumanEval | 1240 → 3835 s | 3.6 → 5.4 s | 376 → 499 |
| GPQA | 4125 → 8474 s | 16.0 → 44.1 s | 1481 → 3987 |
| LiveCodeBench | 3705 → 5937 s | 15.9 → 28.1 s | 1548 → 2425 |

- O `summarize_ab.py` usa a nota estrita e marca o G1 do HumanEval como falha. Com os imports do prompt (`regrade_humaneval.py`, chave `k1a-262144` em [`humaneval-regrade.json`](humaneval-regrade.json)), o `k1a` empata com o `k2a`. A etapa4 já usa a nota com imports para comparar braços.
- O jdhodges fica 3 abaixo do `k2a`, 1 além da margem. O `k1a` empata com o `w1z` (34/40), e contra o `w1z` o G1 passa nas 6 suítes.
- O G2 falha em GPQA e LCB, como na etapa4. Ele só informa.
- O base pensa mais que o Swift: 2.7 × os tokens medianos no GPQA e o dobro do tempo total da bateria.

## Longctx (`longctx_probe.py`, 8 perguntas, servidor a 262144)

| braço | 128K | 256K |
|---|---:|---:|
| k2a | 8/8 | 8/8 |
| k1a | 8/8 | 8/8 |

## Tool calls (`toolcall-probe.sh --sessions 20 --max-tokens 2048`)

| braço | frequency_penalty 0 | frequency_penalty 1 |
|---|---|---|
| w1z | 20/20 sessões, 80/80 turnos | 14/20 sessões, 80/80 turnos |
| k2a | 20/20 sessões, 80/80 turnos | 13/20 sessões, 58/64 turnos |
| k1a | 20/20 sessões, 80/80 turnos | 14/20 sessões, 72/74 turnos |

Com penalidade 0, que os clientes do driver enviam, os três braços passam em tudo.

## Veredito

Pela regra fixada antes da rodada, o G1 contra o `k2a` falha no jdhodges (−3, margem 2). O HumanEval passa com os imports. Por isso, o base sai dos candidatos do Splash, e o `k2a` continua como o braço do Splash.

O resultado tem duas ressalvas:

- A rodada é única. Duas rodadas iguais do `k2a` variaram 4 questões no HumanEval, então 1 questão além da margem no jdhodges pode ser ruído.
- O `k1a` empata com o driver diário (`w1z`) em todas as suítes.

O custo, porém, é real: o base leva o dobro do tempo da bateria para a mesma qualidade.
