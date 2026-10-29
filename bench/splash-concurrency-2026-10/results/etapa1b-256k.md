# Etapa 1b — 256K (Splash 1.5.0)

Tag `e1`, 2026-10-29. Três reps por braço, servidor com `--max-context 262144`, barreira de início nos braços de 2 sessões. A razão usa o `k2c1` a 256K (6.4 s) e, para o stream de 32K do `k2c2L`, o `k2c1` a 32K (5.8 s).

| braço | contexto | stream | T_turno | razão ÷ w1 | warm TTFT tool | hit app / tool | decode | overlap | aux p50 / p95 / errs | wired peak | livre mín | swap Δ | HTTP errs | needles |
|---|---:|---|---:|---:|---:|---|---:|---|---|---:|---:|---:|---:|---|
| k2c1 | 262144 | s1 | 6.4 | 0.58 | 1.7 | 0.996 / 0.996 | 108.6 | 0.00 | — | 116.5 | 0.06 | 0.00 | 0 | 12/13 |
| k2c2L | 262144 | s1 | 6.4 | 1.00 | 1.7 | 0.996 / 0.996 | 107.9 | 0.00 | 2.4 / 5.0 / 0 | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2L | 32768 | s2 | 14.4 | 2.48 | 4.3 | 0.962 / 0.961 | 50.7 | 0.00 | 2.4 / 5.0 / 0 | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2LL | 262144 | s1 | 12.1 | 1.89 | 6.9 | 0.996 / 0.996 | 97.3 | 0.33 | 1.9 / 8.3 / 0 | 116.6 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2LL | 262144 | s2 | 8.2 | 1.28 | 3.3 | 0.996 / 0.996 | 104.0 | 0.33 | 1.9 / 8.3 / 0 | 116.6 | 0.06 | 0.00 | 0 | 13/13 |

O summarizer reporta o `k2c2L` com a banda 256K só como "missing streams (1/2)": o stream de 32K grava com outra banda. Com `--context all`, o veredito é `fail (ratio>2.0, no overlap)`.

## Leitura

- **Memória.** Duas sessões de 256K cabem no Splash sem ajuste: wired peak 116.6 GB, swap 0, zero recusa. O `k2c2Ls` (`--state-format bf16`) não rodou. O mlx-serve 26.10.1 só cabia com o prefix cache em RAM reduzido a 4 GB (`w1c2m4`).
- **`k2c2LL`.** O pior stream fica em 12.1 s (1.89×), e a vazão total soma 1.85×. Reprova pelo stall: cada cold de 256K leva ~700 s de prefill, e o outro stream espera. O `w1c2m4` do mlx-serve dava 18.6 s (1.68× sobre 11.1 s), com 2 needles erradas no s1.
- **`k2c2L`.** A sessão de 256K fica igual à solo (6.4 s). A de 32K espera pelo prefill da longa: 14.4 s, 2.48× sobre o `k2c1` de 32K. O mlx-serve dava 15.5 s (1.96×) no rerun com barreira, com 1 recusa de prefill e needles 10/12 na sessão longa.
- **Needles.** 13/13 em todos os streams de 2 sessões; o `k2c1` sozinho errou 1 (12/13).

## Veredito

- **`MODE_256K=native`: reprovado pelo gate, com a melhor leitura absoluta.** Nenhum braço de 256K passa. O `k2c2LL` falha só pelo stall do cold. No tempo de turno ele fica abaixo do melhor braço do mlx-serve (12.1 contra 18.6 s), sem ajuste de memória e sem needle errado.
