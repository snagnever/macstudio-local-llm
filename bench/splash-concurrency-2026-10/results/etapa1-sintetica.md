# Etapa 1 — concorrência sintética a 32K e 128K (Splash 1.5.0)

Tag `e1`, 2026-10-29. Três reps por braço. Os braços `k2c*` usam o Splash 1.5.0 na porta 8585. A razão de cada stream é o `T_turno` dele dividido pelo do `k2c1` na mesma banda. Os braços `w1zc*` usam o mlx-serve 26.10.3 no mesmo dia, com razão sobre o `w1zc1`.

## 32K

| braço | contexto | stream | T_turno | razão ÷ w1 | warm TTFT tool | hit app / tool | decode | overlap | aux p50 / p95 / errs | wired peak | livre mín | swap Δ | HTTP errs | needles |
|---|---:|---|---:|---:|---:|---|---:|---|---|---:|---:|---:|---:|---|
| k2c1 | 32768 | s1 | 5.8 | 0.73 | 1.5 | 0.963 / 0.962 | 119.3 | 0.00 | — | 108.0 | 0.06 | 0.00 | 0 | 13/13 |
| k2c1a | 32768 | s1 | 6.3 | 1.09 | 1.5 | 0.963 / 0.962 | 105.9 | 0.00 | 1.4 / 2.6 / 0 | 109.8 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2 | 32768 | s1 | 12.0 | 2.07 | 1.5 | 0.963 / 0.962 | 48.9 | 0.33 | — | 111.4 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2 | 32768 | s2 | 11.4 | 1.97 | 4.3 | 0.962 / 0.961 | 72.3 | 0.89 | — | 111.4 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2a | 32768 | s1 | 6.2 | 1.07 | 1.5 | 0.963 / 0.962 | 107.8 | 0.22 | 1.2 / 2.8 / 0 | 113.7 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2a | 32768 | s2 | 14.1 | 2.43 | 4.3 | 0.962 / 0.961 | 52.2 | 0.44 | 1.2 / 2.8 / 0 | 113.7 | 0.06 | 0.00 | 0 | 13/13 |
| k2c3a | 32768 | s1 | 12.5 | 2.16 | 1.5 | 0.963 / 0.962 | 46.6 | 0.56 | 1.4 / 2.8 / 0 | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c3a | 32768 | s2 | 17.1 | 2.95 | 4.4 | 0.962 / 0.961 | 40.5 | 0.44 | 1.4 / 2.8 / 0 | 116.5 | 0.06 | 0.00 | 0 | 12/13 |
| k2c3a | 32768 | s3 | 15.8 | 2.72 | 3.2 | 0.963 / 0.962 | 40.7 | 0.78 | 1.4 / 2.8 / 0 | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4 | 32768 | s1 | 21.6 | 3.72 | 3.2 | 0.963 / 0.962 | 27.9 | 1.00 | — | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4 | 32768 | s2 | 17.1 | 2.95 | 5.2 | 0.962 / 0.961 | 43.2 | 0.44 | — | 116.5 | 0.06 | 0.00 | 0 | 12/13 |
| k2c4 | 32768 | s3 | 18.2 | 3.14 | 1.5 | 0.963 / 0.962 | 30.6 | 0.67 | — | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4 | 32768 | s4 | 25.5 | 4.40 | 4.1 | 0.962 / 0.961 | 23.9 | 0.67 | — | 116.5 | 0.06 | 0.00 | 0 | 11/13 |
| k2c4a | 32768 | s1 | 15.5 | 2.67 | 1.5 | 0.963 / 0.962 | 36.5 | 0.56 | 1.9 / 15.9 / 0 | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4a | 32768 | s2 | 24.3 | 4.19 | 7.3 | 0.962 / 0.961 | 30.2 | 0.89 | 1.9 / 15.9 / 0 | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4a | 32768 | s3 | 17.0 | 2.93 | 3.9 | 0.963 / 0.962 | 39.2 | 0.44 | 1.9 / 15.9 / 0 | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4a | 32768 | s4 | 20.9 | 3.60 | 4.1 | 0.962 / 0.961 | 30.6 | 0.56 | 1.9 / 15.9 / 0 | 116.5 | 0.06 | 0.00 | 0 | 11/13 |
| k2c1x2 | 32768 | s1 | 6.3 | 1.09 | 1.6 | 0.963 / 0.962 | 110.2 | 0.00 | 10.1 / 80.5 / 0 | 112.1 | 0.06 | 0.00 | 0 | 13/13 |
| k2c1x2 | 32768 | s2 | 19.6 | 3.38 | 15.2 | 0.962 / 0.961 | 116.9 | 0.00 | 10.1 / 80.5 / 0 | 112.1 | 0.06 | 0.00 | 0 | 12/13 |
| w1zc1 | 32768 | s1 | 7.9 | 1.00 | 1.8 | 0.962 / 0.961 | 83.2 | 0.00 | — | 100.7 | 0.05 | 0.00 | 0 | 12/13 |
| w1zc2a | 32768 | s1 | 8.5 | 1.08 | 1.8 | 0.962 / 0.961 | 76.1 | 0.33 | 0.9 / 51.9 / 0 | 103.0 | 0.05 | 0.01 | 0 | 13/13 |
| w1zc2a | 32768 | s2 | 13.8 | 1.75 | 1.8 | 0.962 / 0.961 | 42.4 | 1.00 | 0.9 / 51.9 / 0 | 103.0 | 0.05 | 0.01 | 0 | 13/13 |

O `k2c1x2` a 32K desta tabela é o rerun com o fix `27c48ff` (a espera pelo lock conta no TTFT), feito no fim da fila da Etapa 2. A primeira rodada, sem o fix, está em `results/superseded-k2c1x2-32768/` no rig.

## 128K

| braço | contexto | stream | T_turno | razão ÷ w1 | warm TTFT tool | hit app / tool | decode | overlap | aux p50 / p95 / errs | wired peak | livre mín | swap Δ | HTTP errs | needles |
|---|---:|---|---:|---:|---:|---|---:|---|---|---:|---:|---:|---:|---|
| k2c1 | 131072 | s1 | 6.1 | 0.71 | 1.6 | 0.992 / 0.991 | 113.9 | 0.00 | — | 112.7 | 0.06 | 0.00 | 0 | 13/13 |
| k2c1a | 131072 | s1 | 6.2 | 1.02 | 1.6 | 0.992 / 0.991 | 110.0 | 0.00 | 1.6 / 3.1 / 0 | 116.2 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2 | 131072 | s1 | 13.9 | 2.28 | 1.6 | 0.992 / 0.991 | 41.8 | 0.00 | — | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2 | 131072 | s2 | 15.7 | 2.57 | 4.2 | 0.992 / 0.991 | 44.4 | 0.00 | — | 116.5 | 0.06 | 0.00 | 0 | 12/13 |
| k2c2a | 131072 | s1 | 12.6 | 2.07 | 1.6 | 0.992 / 0.991 | 46.8 | 0.00 | 1.8 / 5.0 / 0 | 116.7 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2a | 131072 | s2 | 15.4 | 2.52 | 4.1 | 0.992 / 0.991 | 45.4 | 0.00 | 1.8 / 5.0 / 0 | 116.7 | 0.06 | 0.00 | 0 | 12/13 |
| k2c3a | 131072 | s1 | 14.6 | 2.39 | 4.1 | 0.992 / 0.991 | 48.9 | 0.89 | 2.3 / 9.3 / 0 | 116.7 | 0.06 | 0.00 | 0 | 13/13 |
| k2c3a | 131072 | s2 | 13.7 | 2.25 | 5.0 | 0.992 / 0.991 | 59.0 | 0.67 | 2.3 / 9.3 / 0 | 116.7 | 0.06 | 0.00 | 0 | 13/13 |
| k2c3a | 131072 | s3 | 10.4 | 1.70 | 1.8 | 0.992 / 0.991 | 59.5 | 0.78 | 2.3 / 9.3 / 0 | 116.7 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4 | 131072 | s1 | 13.7 | 2.25 | 3.6 | 0.992 / 0.991 | 50.5 | 0.89 | — | 116.8 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4 | 131072 | s2 | 18.0 | 2.95 | 5.1 | 0.992 / 0.991 | 39.8 | 0.67 | — | 116.8 | 0.06 | 0.00 | 0 | 11/13 |
| k2c4 | 131072 | s3 | 13.7 | 2.25 | 3.7 | 0.992 / 0.991 | 51.6 | 1.00 | — | 116.8 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4 | 131072 | s4 | 19.3 | 3.16 | 9.2 | 0.992 / 0.991 | 51.1 | 0.78 | — | 116.8 | 0.06 | 0.00 | 0 | 12/13 |
| k2c4a | 131072 | s1 | 20.3 | 3.33 | 11.5 | 0.992 / 0.991 | 58.0 | 1.00 | 3.0 / 158.9 / 0 | 116.6 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4a | 131072 | s2 | 28.0 | 4.59 | 21.0 | 0.992 / 0.991 | 73.6 | 0.89 | 3.0 / 158.9 / 0 | 116.6 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4a | 131072 | s3 | 15.5 | 2.54 | 5.2 | 0.992 / 0.991 | 49.7 | 1.00 | 3.0 / 158.9 / 0 | 116.6 | 0.06 | 0.00 | 0 | 13/13 |
| k2c4a | 131072 | s4 | 15.8 | 2.59 | 7.4 | 0.992 / 0.991 | 61.2 | 0.89 | 3.0 / 158.9 / 0 | 116.6 | 0.06 | 0.00 | 0 | 11/13 |
| k2c1x2 | 131072 | s1 | 6.4 | 1.05 | 1.9 | 0.992 / 0.991 | 114.3 | 0.00 | 87.5 / 343.9 / 0 | 116.8 | 0.06 | 0.00 | 0 | 13/13 |
| k2c1x2 | 131072 | s2 | 14.5 | 2.38 | 9.9 | 0.992 / 0.991 | 110.9 | 0.00 | 87.5 / 343.9 / 0 | 116.8 | 0.06 | 0.00 | 0 | 13/13 |
| w1zc1 | 131072 | s1 | 9.0 | 1.05 | 2.0 | 0.992 / 0.991 | 72.8 | 0.00 | — | 110.7 | 0.02 | 0.00 | 0 | 13/13 |
| w1zc2a | 131072 | s1 | 9.4 | 1.04 | 2.1 | 0.992 / 0.991 | 70.4 | 0.33 | 0.9 / 183.0 / 0 | 113.5 | 0.01 | 0.00 | 0 | 13/13 |
| w1zc2a | 131072 | s2 | 15.6 | 1.73 | 2.2 | 0.992 / 0.991 | 38.0 | 1.00 | 0.9 / 183.0 / 0 | 113.5 | 0.01 | 0.00 | 0 | 13/13 |

O `k2c4` e o `k2c4a` a 128K rodaram depois, a pedido, na fila `q-e3` (2026-10-29, 21:08–23:04 do rig). A fila da Etapa 1 pulou os dois, porque o N = 3 reprovou. Os dois reprovam: o `k2c4` fica em 3.16× (19.3 s) e o `k2c4a` em 4.59× (28.0 s), com needles erradas e stall. A vazão total soma 1.69× e 2.13× do `k2c1`. Zero recusa e swap 0, com wired peak de 116.8 GB. O `w1c4a` do mlx-serve 26.10.1 dava 3.85× a 128K, com 3 recusas `PrefillDoesNotFit`.

## Batch contra fila

O `--vs k2c1x2` compara o `k2c2` com o controle serializado (um request por vez, mesma carga). A 32K o batch ganha: o pior stream do `k2c2` fica em 0.61× o pior stream da fila (12.0 contra 19.6 s), média 0.90×. A 128K o batch perde: pior stream 1.08×, média 1.42×. A 128K o prefill de cada turno é longo, e o batch não esconde a espera.

## Overlap e `/status`

O gate "no overlap" conta só as janelas de decode que se cruzam. No Splash o decode de um turno dura ~5 s (512 tokens a ~100 tok/s), e o prefill de um request bloqueia o outro. Por isso as janelas de decode quase nunca se cruzam. O `/status`, com uma amostra a cada 10 s, mostra que as sessões disputam o servidor ao mesmo tempo:

| braço | banda | amostras | decode + prefill | 2 em prefill | 2 em decode |
|---|---:|---:|---:|---:|---:|
| `k2c2` | 32K | 48 | 19 | 2 | 0 |
| `k2c2` | 128K | 183 | 27 | 6 | 0 |
| `k2c2a` | 128K | 189 | 27 | 81 | 6 |
| `k2c2ad1` | 128K | 186 | 20 | 92 | 0 |

"2 em prefill" quer dizer um request lendo o prompt e outro esperando na fase de prefill. O "no overlap" do Splash não quer dizer que as sessões rodaram em sequência.

## Veredito

- **`N_APPROVED=1`.** Nenhum braço com N ≥ 2 passa no Splash. O pior stream fica acima de 2.0× em todos: 2.07–2.43× a 32K e 2.52–2.57× a 128K com 2 sessões.
- **Needles.** Caem com N ≥ 3 a 32K (`k2c3a`, `k2c4`, `k2c4a`), com N = 4 a 128K e com N = 2 a 128K (1 erro em 13 no s2 do `k2c2` e do `k2c2a`). O `k2c2v` (`--verify-rows all`) separa o efeito do batch; ver a [Etapa 1c](etapa1c-extras.md).
- **Vazão total.** Com 2 sessões e requests curtos ao lado, a vazão total fica 1.34× a 32K e 0.81× a 128K. O mlx-serve 26.10.3 no mesmo dia dá 1.43× e 1.49×.
- **`T_turno` absoluto.** O `k2c1` sozinho é mais rápido que o `w1zc1` (5.8 / 6.1 s contra 7.9 / 9.0 s). Com 2 sessões, o pior turno fica igual nos dois servidores: 14.1 contra 13.8 s a 32K e 15.4 contra 15.6 s a 128K.
- **mlx-serve 26.10.3.** O `w1zc2a` passa com aviso a 32K (1.75×). A 128K o pior stream fica em 1.73×, mas reprova pelo stall: o p95 das chamadas `permission` passa de 60 s.
