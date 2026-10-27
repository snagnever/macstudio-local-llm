# t6 e t7 — iQ 4.7bpw no mlx-serve 26.10.3 e 1M no mlx-serve (2026-10-27)

Pedido do usuário: o m4max-guide comparava o iQ no mlx-serve 26.10.1 (`n2`) com o Swift 1.5 no 26.10.3 (`w1z`). A fila rodou de 06:24 a 11:44 (hora do rig), numa pausa do Terminal-Bench do `k2a` combinada com a sessão dele.

- `n2z` = ddalcu iQ-MLX-4.7bpw `dafff5c` no 26.10.3, com as flags do `n2`.
- `n2zq4` = `n2z` com YaRN e KV 4-bit, o perfil do `n2q4` no 26.10.3.
- `w1zq4` = Swift 1.5 com o mesmo perfil.

## t6: as bandas do guia no 26.10.3

`summarize_driver.py`, `T_turno` (decode tok/s). Os `n2` vêm da `engine-updates-2026-10`; os `w1z` de 32K a 256K vêm da `stack-updates-2026-10`.

| banda | n2 · 26.10.1 | n2z · 26.10.3 | w1z · 26.10.3 |
|---|---:|---:|---:|
| 8K | 7.8 s (84) | 7.9 s (81) | 7.7 s (84) |
| 32K | 8.2 s (80) | 8.0 s (82) | 8.0 s (82) |
| 128K | 8.8 s (74) | 8.9 s (74) | 8.9 s (74) |
| 256K | 9.8 s (67), 1 rep | 11.9 s (57) | 9.2 s (74), 1 rep |
| 512K (YaRN 2.0 + KV 4-bit) | 13.0 s (56) | 14.5 s (49) | 12.7 s (57) |

- Todos os gates passam em todas as bandas. O alerta wired > 102 GB aparece de 128K em diante, como no `n2`.
- Até 128K, o iQ e o Swift empatam no 26.10.3.
- A partir de 256K, o iQ fica mais lento no 26.10.3 do que no 26.10.1: o decode cai de 67 para 57 tok/s a 256K e de 56 para 49 a 512K. Com o Swift acontece o contrário (etapa1 da stack-updates). No mesmo build, o Swift é o quant mais rápido a 256K e a 512K.
- O `n2z` a 32K bate com a rodada da stack-updates (`n2z-32768-t1.0-e4`: 8.1 s).

## t7: 1M no mlx-serve 26.10.3

YaRN 3.815 (1000000 / 262144) com KV 4-bit, 1 rep. Os dois braços sobem a 1M e servem o prompt frio (994,527 tokens) em 1,718 a 1,719 s (28.6 min), com decode de 42 tok/s. Nos cenários seguintes, o servidor recusa o prefill:

| braço | cold | identical | append | middle_mutation | tool_turn |
|---|---|---|---|---|---|
| w1zq4 | ok | PrefillDoesNotFit | ok (hit 1.00) | ok (hit 0.44) | PrefillDoesNotFit |
| n2zq4 | ok | PrefillDoesNotFit | ok (hit 1.00) | PrefillDoesNotFit | PrefillDoesNotFit |

O log do servidor mostra: `prompt 994527 tokens needs ~18057MB at prefill chunk 512 ... ~6784MB available`, com `[admission] needed=20066 MB available=8903 MB verdict=refuse`. O pico de wired fica em 109–113 GB.

Veredito: o mlx-serve 26.10.3 não serve 1M em uso real neste rig. Ele aceita o primeiro prompt, mas falha em 2 de 5 (`w1zq4`) e em 3 de 5 (`n2zq4`) das requisições seguintes. Como a fila de carga passou, o recuo para 786432 não rodou. As páginas ficam sem `T_turno` de 1M para o mlx-serve e mostram o motivo.

## Relatórios

- `consolidate_reports.py`: a série `n3` (`n2z`, `n2zq4`) entra no perfil 2026-10. As bandas de 1M do mlx-serve ficam fora das séries (`SPLASH_SKIP`).
- O m4max-guide ganha a tabela "iQ-MLX and Swift 1.5 on the same mlx-serve build" na seção 9 e o texto do 1M no mlx-serve.
- O perf-lines ganha a série `n3` e o motivo da falta de 1M em `w1` e `n3`.
- O overview e a página do Swift 1.5 não foram regenerados: o overview estava parado desde 11/10, e regenerá-lo muda o daily driver para o `k2`, o que fica fora deste pedido.
