# Braços extras — `--prefill-decode-share` e controle de 256K (2026-10-18)

Pedido do usuário depois da Etapa 2. Mesmos gates do `w1c2a` (Etapa 1). Referências: `T_turno` do `w1` sozinho 8.6 s a 128K e 11.1 s a 256K.

## `--prefill-decode-share` a 128K

O [PR #568](https://github.com/ddalcu/mlx-serve/pull/568) do mlx-serve (no 26.10.1) faz o decode guardar a fração `S` do tempo enquanto outro request faz prefill, e estreita os chunks de prefill para 1024 tokens. O PR diz que o request que espera recebe o primeiro token mais tarde pelo mesmo tempo. O [PR #884](https://github.com/ddalcu/mlx-serve/pull/884), que admite requests pequenos nos limites de chunk, exclui o `qwen4_exp` (Flash-Next) e não está em release.

| braço | stream | T_turno | razão ÷ w1 | decode | overlap | aux p50 / p95 | needles | veredito |
|---|---|---:|---:|---:|---|---|---|---|
| w1c2a (Etapa 1) | s1 | 10.4 | 1.21 | 62.1 | 0.44 | 1.0 / 322.6 | 13/13 | fail (stall>60s) |
| w1c2a (Etapa 1) | s2 | 16.7 | 1.94 | 35.4 | 1.00 | | 13/13 | |
| w1c2ap3 | s1 | 15.1 | 1.76 | 39.6 | 0.67 | 1.0 / 176.4 | 13/13 | fail (ratio>2.0, stall>60s) |
| w1c2ap3 | s2 | 17.4 | 2.02 | 33.8 | 1.00 | | 13/13 | |
| w1c2ap5 | s1 | 10.5 | 1.22 | 60.8 | 0.56 | 1.2 / 175.4 | 13/13 | fail (stall>60s) |
| w1c2ap5 | s2 | 16.5 | 1.92 | 35.7 | 1.00 | | 13/13 | |

Chamadas aux e prefill, por braço (os dois streams somados):

| braço | aux n | aux > 60 s | aux máx | cold TTFT mediana / máx | middle_mutation |
|---|---:|---:|---:|---|---|
| w1c2a | 26 | 6 | 330 s | 168 / 340 s | 92, 96 s |
| w1c1x2 | 28 | 8 | 170 s | 169 / 287 s | 92, 97 s |
| w1c2ap3 | 24 | 8 | 178 s | 319 / 342 s | 92, 115 s |
| w1c2ap5 | 23 | 8 | 174 s | 327 / 340 s | 92, 107 s |

A flag não tira o stall. O número de chamadas aux acima de 60 s fica igual ao do controle `w1c1x2` (8), e o máximo também (~175 s contra 170 s). O p95 cai de 322.6 s para ~176 s só porque o `w1c2a` teve uma chamada de 330 s. Em troca, a mediana do cold TTFT dobra (168 → ~320 s): o prefill estreito é mais lento. O `T_turno` do `w1c2ap5` fica igual ao do `w1c2a`; o `w1c2ap3` piora e passa de 2.0×.

**Veredito: `--prefill-decode-share` não entra no launcher.** O stall de uma chamada nova durante um prefill longo não tem remédio no 26.10.1 para este modelo.

## Controle `w1c1` a 256K, 3 reps (tag `e1c`)

| braço | contexto | T_turno | razão ÷ 11.1 s | warm TTFT tool | hit app / tool | decode | wired peak | needles | veredito |
|---|---:|---:|---:|---:|---|---:|---:|---|---|
| w1c1 | 262144 | 10.3 | 0.93 | 2.7 | 0.996 / 0.996 | 67.0 | 113.9 | 12/13 | pass |

Com 3 reps, o `T_turno` fica em 10.3 s, 7% abaixo da referência do plano. Needles 12/13 passa a regra de 256K. Contra os 10.3 s, o pior stream do `w1c2m4` (Etapa 1b, 18.6 s) fica em 1.81×, ainda abaixo de 2.0×. O `MODE_256K=m4` não muda.
