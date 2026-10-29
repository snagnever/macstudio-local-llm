# Etapa 1c — `--decode-share` a 128K (Splash 1.5.0)

Tag `e1`, 2026-10-29. Três reps por braço, 2 sessões com requests curtos ao lado, contexto 131072. O `--decode-share` reparte o tempo do servidor entre o decode do batch e o prefill do próximo request. O default é 0.5 (`k2c2a`).

| braço | contexto | stream | T_turno | razão ÷ w1 | warm TTFT tool | hit app / tool | decode | overlap | aux p50 / p95 / errs | wired peak | livre mín | swap Δ | HTTP errs | needles |
|---|---:|---|---:|---:|---:|---|---:|---|---|---:|---:|---:|---:|---|
| k2c2a | 131072 | s1 | 12.6 | 2.07 | 1.6 | 0.992 / 0.991 | 46.8 | 0.00 | 1.8 / 5.0 / 0 | 116.7 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2a | 131072 | s2 | 15.4 | 2.52 | 4.1 | 0.992 / 0.991 | 45.4 | 0.00 | 1.8 / 5.0 / 0 | 116.7 | 0.06 | 0.00 | 0 | 12/13 |
| k2c2ad1 | 131072 | s1 | 9.6 | 1.57 | 1.6 | 0.992 / 0.991 | 64.4 | 0.00 | 1.8 / 4.8 / 0 | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2ad1 | 131072 | s2 | 10.8 | 1.77 | 4.2 | 0.992 / 0.991 | 77.4 | 0.00 | 1.8 / 4.8 / 0 | 116.5 | 0.06 | 0.00 | 0 | 12/13 |
| k2c2ad0 | 131072 | s1 | 6.5 | 1.07 | 1.6 | 0.992 / 0.991 | 103.2 | 0.22 | 2.9 / 6.9 / 0 | 116.5 | 0.06 | 0.00 | 0 | 13/13 |
| k2c2ad0 | 131072 | s2 | 50.5 | 8.28 | 3.3 | 0.992 / 0.991 | 10.9 | 0.33 | 2.9 / 6.9 / 0 | 116.5 | 0.06 | 0.00 | 0 | 13/13 |

- **`--decode-share 1.0` (`k2c2ad1`):** melhor braço de 2 sessões no Splash. O pior stream cai de 15.4 para 10.8 s (1.77×), e a vazão total sobe para 1.24×. Reprova por 1 needle errado em 13 no s2 e pelo "no overlap", que aqui é efeito da medida (ver [Etapa 1](etapa1-sintetica.md)).
- **`--decode-share 0` (`k2c2ad0`):** o prefill tem prioridade. Um stream fica quase sozinho (1.07×), e o outro espera: 50.5 s, 8.28×.
- **`k2c2v`:** não rodou. As needles do `k2c2ad1` erram 1 em 13, como as do `k2c2a`. A diferença com o N = 1 é de 1 needle, dentro do ruído de 3 reps. O `k2c2v` fica como pergunta aberta.
- **Launcher:** o `--decode-share 1.0` não passa no gate e não entra no perfil diário. O `SPLASH_DECODE_SHARE` entra no launcher como opção, com default igual ao do Splash.
