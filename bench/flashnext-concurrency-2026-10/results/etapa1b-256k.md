# Etapa 1b — dois streams a 256K (mlx-serve 26.10.1, Swift 1.5)

Tag `e1b`, 2026-10-17. Controle `w1c1` com 1 rep, demais braços com 3 reps. Referência do plano para o `w1` sozinho a 256K: `T_turno` 11.1 s.

## Resultado

Duas sessões de 256K cabem no driver só com o prefix cache em RAM reduzido a 4 GB (`w1c2m4`). Com o cache diário de 16 GB, uma sessão de 256K ao lado de uma de 32K (`w1c2L`, rerun com barreira de início) levou recusa de prefill e errou 1 needle. O KV de 8 bits (`w1c2q8`) levou recusa; com o cache de 4 GB (`w1c2m4q8`) ele cabe, mas errou 1 needle.

| braço | contexto | stream | T_turno | razão ÷ 11.1 s | warm TTFT tool | hit app / tool | decode | overlap | aux p50 / p95 / errs | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---|---:|---:|---:|---|---:|---|---|---:|---:|---:|---|
| w1c1 | 262144 | s1 | 9.8 | 0.88 | 2.1 | 0.996 / 0.996 | 66.4 | 0.00 | — | 111.4 | 0.00 | 0 | 4/5 |
| w1c2L | 262144 | s1 | 12.2 | 1.10 | 2.7 | 0.996 / 0.996 | 54.0 | 0.00 | 1.3 / 338.1 / 0 | 114.7 | 0.00 | 1 | 12/13 |
| w1c2L | 32768 | s2 | 7.8 | 0.99 | 1.8 | 0.962 / 0.961 | 86.5 | 0.00 | 1.3 / 338.1 / 0 | 114.7 | 0.00 | 0 | 13/13 |
| w1c2m4 | 262144 | s1 | 11.9 | 1.07 | 3.1 | 0.996 / 0.996 | 58.1 | 0.33 | 1.5 / 355.9 / 0 | 113.3 | 0.00 | 0 | 11/13 |
| w1c2m4 | 262144 | s2 | 18.6 | 1.68 | 2.9 | 0.996 / 0.996 | 32.6 | 1.00 | 1.5 / 355.9 / 0 | 113.3 | 0.00 | 0 | 13/13 |
| w1c2q8 | 262144 | s1 | 12.3 | 1.11 | 2.6 | 0.996 / 0.996 | 53.0 | 0.11 | 1.0 / 351.4 / 0 | 113.7 | 0.00 | 0 | 13/13 |
| w1c2q8 | 262144 | s2 | 17.3 | 1.56 | 2.8 | 0.996 / 0.996 | 35.4 | 1.00 | 1.0 / 351.4 / 0 | 113.7 | 0.00 | 1 | 12/13 |

Vereditos do `summarize_parallel.py` (needles contados só sobre requests respondidos, depois da review final): `w1c1` fail (needles); `w1c2L` (tag `e1b`) fail (http errors, stall>60s, no overlap); `w1c2m4` fail (stall>60s); `w1c2q8` fail (http errors, stall>60s). Na tabela, as linhas do `w1c2L` e do `w1c2q8` (tag `e1b`) mostram needles contados sobre todos os records; contados só sobre os respondidos, ficam em 12/12 (`w1c2L` s1) e 12/12 (`w1c2q8` s2).

## Reruns com barreira de início (tag `e1d`, 2026-10-18)

A review final achou que o `w1c2L` (tag `e1b`) não mediu concorrência: o stream de 256K levou 221 s para montar o fixture, e o de 32K terminou sozinho. O harness ganhou uma barreira de início: cada stream espera os outros antes do primeiro request medido. Com a contagem de needles corrigida, o `w1c2q8` reprovou só por memória, e o plano (Step 6) manda rodar o `w1c2m4q8`.

| braço | contexto | stream | T_turno | razão ÷ ref | warm TTFT tool | hit app / tool | decode | overlap | aux p50 / p95 / errs | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---|---:|---:|---:|---|---:|---|---|---:|---:|---:|---|
| w1c2L | 262144 | s1 | 10.9 | 0.98 | 2.7 | 0.996 / 0.996 | 61.9 | 0.00 | 0.9 / 353.6 / 0 | 115.0 | 0.00 | 1 | 10/12 |
| w1c2L | 32768 | s2 | 15.5 | 1.96 | 1.8 | 0.962 / 0.961 | 37.3 | 1.00 | 0.9 / 353.6 / 0 | 115.0 | 0.00 | 0 | 13/13 |
| w1c2m4q8 | 262144 | s1 | 10.7 | 0.96 | 2.6 | 0.996 / 0.996 | 63.8 | 0.11 | 1.7 / 358.6 / 0 | 107.7 | 0.00 | 0 | 12/13 |
| w1c2m4q8 | 262144 | s2 | 16.7 | 1.50 | 2.7 | 0.996 / 0.996 | 36.4 | 1.00 | 1.7 / 358.6 / 0 | 107.7 | 0.00 | 0 | 13/13 |

Referência da razão: 11.1 s para 256K e 7.9 s para 32K. Vereditos: `w1c2L` fail (needles, http errors, stall>60s); `w1c2m4q8` fail (needles, stall>60s).

- **`w1c2L`:** os dois streams começaram juntos (mesmo instante de início). O stream de 32K agora divide o decode e fica em 1.96×. O de 256K levou 1 recusa (`PrefillDoesNotFit`, mensagem igual à do `e1b`), 1 resposta truncada e 1 needle errado (`append`, `finish_reason=stop`): 10/12 fica abaixo da regra de 11/13.
- **`w1c2m4q8`:** sem recusa, wired peak 107.7 GB (7.4 GB abaixo do `w1c2m4`). Errou 1 needle (`append`, `finish_reason=stop`). A regra do plano para KV de 8 bits não aceita needle errado.

## Controle

O `T_turno` do `w1c1` ficou em 9.8 s, 12% abaixo da referência de 11.1 s. O desvio é para mais rápido, então não indica degradação do rig. A tabela usa 11.1 s, como o plano. Contra os 9.8 s medidos, o pior stream do `w1c2m4` fica em 1.90×.

O controle errou 1 de 5 needles. A regra de 256K (11/13) supõe 3 reps; com 1 rep, 4/5 não separa um erro isolado de uma regressão. O controle vale como referência de tempo e memória.

## Recusas de prefill

Mensagens exatas do servidor:

- `w1c2L` (1 request recusado no JSONL; 7 linhas `streaming error` no log do servidor): `prompt 256657 tokens needs ~10848MB at prefill chunk 512 (the narrowest width tried), ~8989MB available + ~14784MB the hot cache can give back (~22610MB resident, ~7826MB of it pinned by this request's own prefix) — refused before prefill`
- `w1c2q8` (1 recusa): `prompt 256609 tokens needs ~8028MB at prefill chunk 512 (the narrowest width tried), ~7393MB available + ~15097MB the hot cache can give back (~19987MB resident, ~4889MB of it pinned by this request's own prefix) — refused before prefill` e `[scheduler] prefill refused: 256609 tokens do not fit even with an empty hot cache`

No `w1c2L` com tag `e1b`, o stream de 32K terminou antes de o de 256K mandar o primeiro request medido (o fixture de 256K leva ~221 s para montar). Por isso o overlap é 0. A recusa veio com só o stream de 256K e o gerador no servidor. O rerun com barreira está na seção acima.

## Stall das chamadas auxiliares

O p95 das chamadas `permission` ficou entre 338 e 356 s em todos os braços de dois streams. É o mesmo efeito medido a 128K (Etapa 1): um prefill longo ocupa o servidor e a chamada espera. A 256K o `cold` e o `middle_mutation` levam mais tempo, então a espera cresce. O veredito trata o stall como aviso, pela mesma leitura da Etapa 1.

## Custo do SSD

O warm TTFT do `tool_turn` no `w1c2m4` é 2.9–3.1 s, contra 2.1–2.2 s no `w1c2a` a 128K. A diferença de ~1 s é o custo de restaurar do SSD com o cache em RAM de 4 GB.

## Veredito

- **`MODE_256K=m4`: aprovado com aviso.** Primeiro braço da ordem do plano sem recusa e sem needle errado. O pior stream fica em 1.68× contra 11.1 s.
- **`w1c2L`: reprovado.** Recusa de prefill e needles 10/12 no rerun com barreira.
- **`w1c2q8`: reprovado por memória.**
- **`w1c2m4q8`: reprovado por needles.** Cabe na memória, mas errou 1 needle; o KV de 8 bits não entra no driver.
- **`--os-reserve-gib 4`:** não entra. O melhor braço passou sem recusa.
