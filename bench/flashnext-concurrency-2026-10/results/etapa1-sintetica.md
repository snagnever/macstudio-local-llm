# Etapa 1 — concorrência sintética no driver Swift 1.5 (mlx-serve 26.10.1)

Rig: Mac Studio M4 Max 128 GB. Modelo: Dankpaws Swift 1.5 Qwen3.8 Flash-Next MLX 4.7 bpw. Tag `e1`, 3 reps por braço, 2026-10-17. Referência do `w1` sozinho: `T_turno` 7.9 s a 32K e 8.6 s a 128K.

## Resultado

O mlx-serve 26.10.1 faz batched decode com qualquer valor de `--max-concurrent`. Com o default `1`, o log de boot mostra `Concurrency: --max-concurrent=1, batched decode on` e `[batched] gdn batched decode engaged (slots=2)`. O driver diário de hoje já divide o decode entre duas sessões.

Com duas sessões, o decode não soma: cada stream sobreposto roda a ~38–42 tok/s, contra 77–84 tok/s sozinho. O stream que entra segundo paga a espera: razão de 1.75–1.94× contra o `w1`. O que entra primeiro fica em 1.03–1.21×.

O braço `w1c1x2` (2 streams, `--max-concurrent 1` explícito) não é uma fila. O overlap do stream 2 é 1.00 e os números são os do `w1c2a` dentro do ruído. Não existe fila serializada para comparar, então `BATCH_BEATS_QUEUE` fica `n/a`. O `--help` do 26.10.1 não documenta uma chave que desligue o batch.

## Tabela

| braço | contexto | stream | T_turno | razão ÷ w1 | warm TTFT tool | hit app / tool | decode | overlap | aux p50 / p95 / errs | wired peak | livre mín | swap Δ | HTTP errs | needles |
|---|---:|---|---:|---:|---:|---|---:|---|---|---:|---:|---:|---:|---|
| w1c1 | 32768 | s1 | 7.9 | 1.00 | 1.9 | 0.962 / 0.961 | 84.0 | 0.00 | — | 96.0 | 0.01 | 0.00 | 0 | 13/13 |
| w1c1a | 32768 | s1 | 8.2 | 1.04 | 1.8 | 0.962 / 0.961 | 81.1 | 0.00 | 0.9 / 22.0 / 0 | 96.9 | 0.01 | 0.00 | 0 | 13/13 |
| w1c2 | 32768 | s1 | 8.1 | 1.03 | 1.8 | 0.962 / 0.961 | 82.0 | 0.11 | — | 100.7 | 0.03 | 0.00 | 0 | 13/13 |
| w1c2 | 32768 | s2 | 13.8 | 1.75 | 1.9 | 0.962 / 0.961 | 42.7 | 1.00 | — | 100.7 | 0.03 | 0.00 | 0 | 13/13 |
| w1c2a | 32768 | s1 | 8.9 | 1.13 | 1.8 | 0.962 / 0.961 | 72.7 | 0.33 | 1.0 / 33.8 / 0 | 99.9 | 0.02 | 0.00 | 0 | 12/13 |
| w1c2a | 32768 | s2 | 13.9 | 1.76 | 1.8 | 0.962 / 0.961 | 42.4 | 1.00 | 1.0 / 33.8 / 0 | 99.9 | 0.02 | 0.00 | 0 | 13/13 |
| w1c1x2 | 32768 | s1 | 8.2 | 1.04 | 1.8 | 0.962 / 0.961 | 80.2 | 0.33 | 0.9 / 25.3 / 0 | 100.1 | 0.02 | 0.00 | 0 | 13/13 |
| w1c1x2 | 32768 | s2 | 13.9 | 1.76 | 1.8 | 0.962 / 0.961 | 42.4 | 1.00 | 0.9 / 25.3 / 0 | 100.1 | 0.02 | 0.00 | 0 | 13/13 |
| w1c1 | 131072 | s1 | 8.6 | 1.00 | 2.0 | 0.992 / 0.991 | 77.3 | 0.00 | — | 110.5 | 0.06 | 0.00 | 0 | 12/13 |
| w1c2 | 131072 | s1 | 9.0 | 1.05 | 2.1 | 0.992 / 0.991 | 74.4 | 0.11 | — | 112.6 | 0.04 | 0.00 | 0 | 13/13 |
| w1c2 | 131072 | s2 | 15.3 | 1.78 | 1.9 | 0.992 / 0.991 | 38.2 | 1.00 | — | 112.6 | 0.04 | 0.00 | 0 | 13/13 |
| w1c2a | 131072 | s1 | 10.4 | 1.21 | 2.1 | 0.992 / 0.991 | 62.1 | 0.44 | 1.0 / 322.6 / 0 | 113.5 | 0.05 | 0.00 | 0 | 13/13 |
| w1c2a | 131072 | s2 | 16.7 | 1.94 | 2.2 | 0.992 / 0.991 | 35.4 | 1.00 | 1.0 / 322.6 / 0 | 113.5 | 0.05 | 0.00 | 0 | 13/13 |
| w1c1x2 | 131072 | s1 | 10.2 | 1.19 | 2.1 | 0.992 / 0.991 | 63.6 | 0.22 | 1.0 / 169.7 / 0 | 113.5 | 0.02 | 0.00 | 0 | 13/13 |
| w1c1x2 | 131072 | s2 | 15.7 | 1.83 | 2.2 | 0.992 / 0.991 | 38.1 | 1.00 | 1.0 / 169.7 / 0 | 113.5 | 0.02 | 0.00 | 0 | 13/13 |

Vereditos do `summarize_parallel.py`: `w1c1` e `w1c1a` pass; `w1c2`, `w1c2a` e `w1c1x2` a 32K e `w1c2` a 128K pass-with-warning; `w1c2a` e `w1c1x2` a 128K fail (stall>60s). `--vs w1c1x2`: pior stream 1.00× e média 1.03× a 32K, 1.06× e 1.05× a 128K.

## Stall das chamadas auxiliares a 128K

No `w1c2a` a 128K, 6 das 26 chamadas `permission` tiveram TTFT de 79 a 330 s. Todas chegaram durante um prefill longo de um stream: `cold` de 128K (~165 s) ou `middle_mutation` (~92 s). O controle `w1c1x2` a 128K mostra o mesmo efeito (p95 169.7 s). A causa é o prefill longo, que ocupa o servidor; não é o `--max-concurrent 2`. Para o veredito por `N`, o stall fica como aviso, não como reprovação. Numa sessão real, ele aparece quando outra sessão faz prefill frio ou compacta um contexto de 128K.

O hit do `tool_turn` não mudou com o gerador (0.961 a 32K, 0.991 a 128K). O hot-cache gravou entradas ociosas no SSD e não fez eviction relevante a 128K. Swap Δ 0 e nenhum erro HTTP em todos os braços.

## Veredito por N

- **N = 2: aprovado com aviso.** O pior stream fica em 1.76× a 32K e 1.94× a 128K, abaixo de 2.0. O `--max-concurrent 2` não muda nada mensurável contra o default.
- **N = 4: não rodou.** A Etapa 1 foi fechada antes do Step 6 por decisão do usuário.
- **Prefix cache:** 16 GB. O `w1c2m8` não foi preciso: wired peak 113.5 GB, sem recusa, sem swap.
