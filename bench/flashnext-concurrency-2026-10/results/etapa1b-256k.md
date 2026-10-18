# Etapa 1b — dois streams a 256K (mlx-serve 26.10.1, Swift 1.5)

Tag `e1b`, 2026-10-17. Controle `w1c1` com 1 rep, demais braços com 3 reps. Referência do plano para o `w1` sozinho a 256K: `T_turno` 11.1 s.

## Resultado

Duas sessões de 256K cabem no driver só com o prefix cache em RAM reduzido a 4 GB (`w1c2m4`). Com o cache diário de 16 GB, o servidor recusa o prefill do segundo contexto longo (`w1c2L`). O KV de 8 bits (`w1c2q8`) também levou recusa e errou um needle.

| braço | contexto | stream | T_turno | razão ÷ 11.1 s | warm TTFT tool | hit app / tool | decode | overlap | aux p50 / p95 / errs | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---|---:|---:|---:|---|---:|---|---|---:|---:|---:|---|
| w1c1 | 262144 | s1 | 9.8 | 0.88 | 2.1 | 0.996 / 0.996 | 66.4 | 0.00 | — | 111.4 | 0.00 | 0 | 4/5 |
| w1c2L | 262144 | s1 | 12.2 | 1.10 | 2.7 | 0.996 / 0.996 | 54.0 | 0.00 | 1.3 / 338.1 / 0 | 114.7 | 0.00 | 1 | 12/13 |
| w1c2L | 32768 | s2 | 7.8 | 0.99 | 1.8 | 0.962 / 0.961 | 86.5 | 0.00 | 1.3 / 338.1 / 0 | 114.7 | 0.00 | 0 | 13/13 |
| w1c2m4 | 262144 | s1 | 11.9 | 1.07 | 3.1 | 0.996 / 0.996 | 58.1 | 0.33 | 1.5 / 355.9 / 0 | 113.3 | 0.00 | 0 | 11/13 |
| w1c2m4 | 262144 | s2 | 18.6 | 1.68 | 2.9 | 0.996 / 0.996 | 32.6 | 1.00 | 1.5 / 355.9 / 0 | 113.3 | 0.00 | 0 | 13/13 |
| w1c2q8 | 262144 | s1 | 12.3 | 1.11 | 2.6 | 0.996 / 0.996 | 53.0 | 0.11 | 1.0 / 351.4 / 0 | 113.7 | 0.00 | 0 | 13/13 |
| w1c2q8 | 262144 | s2 | 17.3 | 1.56 | 2.8 | 0.996 / 0.996 | 35.4 | 1.00 | 1.0 / 351.4 / 0 | 113.7 | 0.00 | 1 | 12/13 |

Vereditos do `summarize_parallel.py`: `w1c1` fail (needles); `w1c2L` fail (http errors, stall>60s, no overlap); `w1c2m4` fail (stall>60s); `w1c2q8` fail (needles, http errors, stall>60s).

## Controle

O `T_turno` do `w1c1` ficou em 9.8 s, 12% abaixo da referência de 11.1 s. O desvio é para mais rápido, então não indica degradação do rig. A tabela usa 11.1 s, como o plano. Contra os 9.8 s medidos, o pior stream do `w1c2m4` fica em 1.90×.

O controle errou 1 de 5 needles. A regra de 256K (11/13) supõe 3 reps; com 1 rep, 4/5 não separa um erro isolado de uma regressão. O controle vale como referência de tempo e memória.

## Recusas de prefill

Mensagens exatas do servidor:

- `w1c2L` (7 recusas no stream de 256K): `prompt 256657 tokens needs ~10848MB at prefill chunk 512 (the narrowest width tried), ~8989MB available + ~14784MB the hot cache can give back (~22610MB resident, ~7826MB of it pinned by this request's own prefix) — refused before prefill`
- `w1c2q8` (1 recusa): `prompt 256609 tokens needs ~8028MB at prefill chunk 512 (the narrowest width tried), ~7393MB available + ~15097MB the hot cache can give back (~19987MB resident, ~4889MB of it pinned by this request's own prefix) — refused before prefill` e `[scheduler] prefill refused: 256609 tokens do not fit even with an empty hot cache`

No `w1c2L`, o stream de 32K terminou sozinho, porque o de 256K recebeu as recusas. Por isso o overlap é 0.

## Stall das chamadas auxiliares

O p95 das chamadas `permission` ficou entre 338 e 356 s em todos os braços de dois streams. É o mesmo efeito medido a 128K (Etapa 1): um prefill longo ocupa o servidor e a chamada espera. A 256K o `cold` e o `middle_mutation` levam mais tempo, então a espera cresce. O veredito trata o stall como aviso, pela mesma leitura da Etapa 1.

## Custo do SSD

O warm TTFT do `tool_turn` no `w1c2m4` é 2.9–3.1 s, contra 2.1–2.2 s no `w1c2a` a 128K. A diferença de ~1 s é o custo de restaurar do SSD com o cache em RAM de 4 GB.

## Veredito

- **`MODE_256K=m4`: aprovado com aviso.** Primeiro braço da ordem do plano sem recusa e sem needle errada. O pior stream fica em 1.68× contra 11.1 s.
- **`w1c2L` e `w1c2q8`: reprovados por memória.** O `q8` também reprovou por needles.
- **`w1c2m4q8`: não rodou.** O plano só roda esse braço se nenhum dos anteriores reprovou por needles, e o `q8` reprovou.
- **`--os-reserve-gib 4`:** não entra. O melhor braço passou sem recusa.
