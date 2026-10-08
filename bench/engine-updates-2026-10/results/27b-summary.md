# Qwen3.8-27B — ranking (2026-10-08)

**Líder: o27 (oMLX 0.7.0 + oQ8e-mtp), o único braço que passa nos gates a 32K e a 128K.** Ele bate a referência
r27 (mlx-serve 26.10.1 + DFlash2) em 9% a 32K (18.0 contra 19.7 s) e em 32% a 128K (29.8 contra 44.0 s). O s27
(mlx-dspark 0.20.3 + DFlash2) tem o menor `T_turno` nas duas bandas (16.9 / 25.0 s), mas falha no gate de hit do
`append` a 32K (0.87). O MTPLX 2.12.2 perde o cache a 128K.

Sem leitura de qualidade: o ranking não decide papel de agente.

Rig: M4 Max 128 GB. Probe: `temperature=1.0`, `top_p=0.95`, `top_k=20`, reasoning `xhigh`, limite 4096 tokens,
3 reps. Por decisão do usuário, a parte 27B fechou em 128K: sem funil de 256K e 512K.

## 32K e 128K

| banda | braço | runtime | T_turno | cold TTFT | warm TTFT id / app / tool | hit app / tool | decode | wired pico | gates |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- |
| 32K | s27 | mlx-dspark 0.20.3 + DFlash2 | 16.9 s | 102.3 s | 0.1 / 17 / 5.1 s | **0.87** / 0.96 | 43.5 | 42.2 GB | hit_append |
| 32K | m27 | MTPLX 2.12.2 | 17.8 s | 117.2 s | 0.2 / 5.7 / 5.5 s | 0.96 / 0.96 | 41.4 | 62.1 GB | passa |
| 32K | **o27** | oMLX 0.7.0 | **18.0 s** | 119.3 s | 0.4 / 5.7 / 5.9 s | 0.96 / 0.96 | 42.2 | 48.2 GB | passa |
| 32K | r27 | mlx-serve 26.10.1 + DFlash2 | 19.7 s | 108.7 s | 0.6 / 5.7 / 5.9 s | 0.96 / 0.96 | 37.0 | 58.9 GB | passa |
| 128K | s27 | mlx-dspark 0.20.3 + DFlash2 | 25.0 s | 699.3 s | 0.1 / 31 / 9.2 s | 0.97 / 0.99 | 32.4 | 60.9 GB | passa |
| 128K | **o27** | oMLX 0.7.0 | **29.8 s** | 808.9 s | 1.1 / 11 / 12 s | 0.99 / 0.99 | 28.2 | 67.7 GB | passa |
| 128K | r27 | mlx-serve 26.10.1 + DFlash2 | 44.0 s | 717.0 s | 1.7 / 11 / 11 s | 0.99 / 0.99 | 15.5 | 70.9 GB | needle |
| 128K | m27 | MTPLX 2.12.2 | 834.2 s | 802.6 s | 0.7 / 814 / 814 s | **0.00 / 0.00** | 25.2 | 97.8 GB | hit |

Swap delta 0 em todos os braços.

| razão `T_turno(braço) / T_turno(r27)` | 32K | 128K |
| --- | ---: | ---: |
| s27 | 0.86 | 0.57 |
| o27 | 0.91 | 0.68 |
| m27 | 0.90 | 18.96 |

## Por braço

- **o27 (oMLX 0.7.0).** Passa em tudo e é o 2º mais rápido nas duas bandas. Usa a MTP nativa do pack oQ8e.
  Truncou 1 resposta a 32K (4096 tokens de reasoning), sem falha de needle.
- **s27 (mlx-dspark 0.20.3).** O decode mais alto do 27B (43.5 / 32.4 tok/s) e o menor cold. O `append` a 32K
  reusa só 87% do prefixo (TTFT quente de 17 s); a 128K o reuso volta a 0.97. O `doctor` sugere o modo DSpark para
  esta máquina; o braço rodou em DFlash para casar com o r27.
- **r27 (mlx-serve 26.10.1).** Reusa o cache bem (0.99), mas o decode cai de 37.0 tok/s a 32K para 15.5 tok/s a
  128K. O drafter DFlash2 aceita ~47–49% por draft (`[spec-stats] mode=dflash … per_draft_pct=46.7%–49.2%`). Errou a
  needle de 10% num `middle_mutation` a 128K (1 de 39), sem truncamento.
- **m27 (MTPLX 2.12.2).** A 32K empata com o o27. A 128K o memory guard descarta o prefixo, como no Flash-Next, e
  cada `append` e `tool_turn` re-prefila os ~125K tokens (~814 s). O 27B cabe a 128K, ao contrário do Flash-Next,
  mas fica inutilizável sem cache.

## Contra o mlx-serve

O r27 e o s27 usam os mesmos pesos (mlx-community 8bit) e o mesmo drafter (DFlash2). Esse par isola o runtime: o
mlx-dspark 0.20.3 dá 2.1× o decode do mlx-serve 26.10.1 a 128K. No 27B com drafter DFlash, o mlx-serve não é o
runtime mais rápido, ao contrário do Flash-Next com MTP nativa.

Dados: `*-t1.0-d27.jsonl`, `summary-27b.json`, `etapa0-27b-smoke.md`.
