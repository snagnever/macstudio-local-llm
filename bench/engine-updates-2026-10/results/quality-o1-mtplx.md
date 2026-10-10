# Qualidade barata — o1 e m1x contra o n2 (Etapa G, 2026-10-09)

**Com os imports do prompt, o o1 empata com o n2 no HumanEval (157 contra 156 de 164), e o m1x fica 5 abaixo
(151), quase tudo por truncamento.** Na nota estrita do `bench2.py`, o n2 lidera com folga (154 contra 140 e 132),
mas a diferença vem do formato da resposta: o o1 e o m1x escrevem a função sem `from typing import List`, e o
grader executa só o código da resposta. No tool-calling, os três ficam a 1–3 casos um do outro.

O veredito não muda: o n2 segue driver. Ele é o mais rápido em todas as bandas, e nenhum braço fica claramente acima
dele em qualidade (diferenças de 1–5 casos). O run do n2 provavelmente usou outro modo de reasoning (ver Leitura),
então esta bateria é uma checagem de sanidade, não um ranking.

Rig: M4 Max 128 GB. Temperatura 0, `max_tokens` 32 768. o1 e m1x serviram com janela de 128K (tag `qual`); o n2
vem do run de 2026-10-07 da campanha flashnext-updates (`humaneval_*iQ-MLX-4.7bpw*_20261007_081345`,
`toolcall_fnupd_n2_*`). Runners: `bench2.py humaneval --examples 164` e `tool_call_bench.py` (suítes jdhodges e
Veerman), no submódulo `tools/local-llm-bench-m4-32gb`.

## Resultado

| suíte | n2 (mlx-serve 26.10.1) | o1 (oMLX 0.7.0) | m1x (MTPLX 2.12.2, memory max) |
| --- | ---: | ---: | ---: |
| HumanEval 164, estrito | **154** | 140 | 132 |
| HumanEval 164, com imports do prompt | 156 | **157** | 151 |
| HumanEval, respostas truncadas | 0 | 5 | 10 |
| jdhodges 40 | **38** | 36 | 35 |
| Veerman 12 | 9 | **10** | **10** |
| tokens médios por resposta do HumanEval | 201 | 1 807 | 3 345 |
| tempo total do HumanEval | 8 min | 64 min | 100 min |

## Leitura

- **HumanEval estrito vs com imports.** O `bench2.py` junta o código extraído da resposta com o teste e executa.
  Ele não junta o prompt. O o1 perde 17 questões e o m1x 19 só pela falta desses imports: com as linhas de import
  do prompt na frente, elas passam. O n2 escreve a função completa num bloco cercado, com imports,
  e perde só 2 assim. Re-avaliação: `scripts/regrade_humaneval.py` →
  [quality-humaneval-regrade.json](quality-humaneval-regrade.json).
- **Truncamento do m1x.** As 10 respostas truncadas do m1x gastaram os 32 768 tokens em reasoning e não escreveram
  código. O o1 truncou 5. Fora das truncadas, o m1x acerta 151 de 154 com imports.
- **Tamanho das respostas.** O n2 responde com ~200 tokens por questão; o o1 com ~1 800 e o m1x com ~3 300 (o
  MTPLX reporta ~3 260 deles como reasoning). Não verifiquei se o n2 pensou e o mlx-serve não contou o reasoning,
  ou se o run de 2026-10-07 rodou com reasoning menor. Se o modo de reasoning foi outro, a comparação mistura modos; para um ranking, o n2 precisa rodar de novo a 128K
  com a tag `qual`.
- **Tool-calling.** jdhodges: o o1 perde `arg_reminder_iso_time`, `edge_vague_reminder` e
  `multi_email_after_calendar_read` e ganha `multi_weather_two_cities_holdout`; o m1x perde os mesmos três e
  `multi_usd_eur_sequential`. Veerman: o1 e m1x passam `veerman_p9_code_trick`, que o n2 erra. Com 12 casos, 1 caso
  vale 8 pontos: fica dentro do ruído.

## Limites

- Uma rodada por braço, temperatura 0. Os pesos são diferentes (iQ-MLX 4.7 bpw, oQ4e, pack do MTPLX), então o teste
  não separa runtime de quantização.
- O n2 rodou em outra sessão (2026-10-07). Não confirmei o contexto do servidor nem o modo de reasoning daquele run.
- O d1 (ds4) ficou fora: a Etapa G4 cobriu o o1 e o melhor MTPLX.
- Esta bateria não mede agente em várias rodadas. Ver o aviso da página (teste da comunidade no zenn.dev).
