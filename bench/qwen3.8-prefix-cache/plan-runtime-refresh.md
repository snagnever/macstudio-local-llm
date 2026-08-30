# 2026-08-29 — Qwen3.8 no M4 Max: re-probe de runtimes atualizados e o modelo Flash-Next

> **Status:** planejado. Reusa o harness da campanha `qwen3.8-prefix-cache`
> (probes, config e drivers em `scripts/`). Nada rodado ainda.

## Contexto

A campanha anterior (ver [plan.md](plan.md)) fechou com dois achados em aberto:

1. **Cap do session-bank do MTPLX.** O miss de `tool_turn` a 128K foi artefato do
   cap de 48 GB, não da ordem. Cap de 100 GB recuperou o hit. Ver
   [memory: mtplx-session-bank-cap].
2. **Colapso de decode do MTPLX a 262K.** MTPLX caiu para ~7 tps a 262K, contra
   ~14–15 tps de oMLX e mlx-dspark. MTPLX liderava até 128K.

Desde o fim da campanha, os três runtimes lançaram versões novas, e a Alibaba
lançou um modelo de geração nova. Dois updates do MTPLX atacam exatamente os dois
achados acima. A lição [memory: runtime-gains-stale-baselines] diz para re-probar
o incumbente antes de declarar um vencedor. Este plano faz isso.

## Deltas de versão desde a campanha

| Runtime | Versão testada | Versão nova | Mudança relevante |
|---|---|---|---|
| oMLX | 0.6.3rc2 | 0.6.3 final | Ganhou MTP próprio ("Lightning MTP", 2.33–2.62x decode). ANE compile cache. Suporte a Flash-Next. |
| MTPLX | 2.9.2 | 2.10.0 | Decode +15–54%. **Memory planning automático por RAM.** **Decode denso melhorado além de 131k** (memory-aware ceiling + verify kernel estendido). |
| mlx-dspark | 0.15.0 | 0.17.2 | **DFlash cap dinâmico** medido na curva da máquina. CPU co-prefill. Prefix-cache hit reporting. |

Modelo novo: **Qwen3.8-Flash-Next 125B-A6B** (arquitetura "Qwen4"), MoE 125B total /
~6B ativos, 262K nativo (1M extensível), licença qwen-community. Os três runtimes já
declaram suporte.

Não verificado: se esses claims se confirmam neste M4 Max. São notas de release.

## Objetivo

Responder se as versões novas mudam o veredito da campanha, e se o Flash-Next
desloca a densa Qwen3.8-27B em uso de agente. Correção funcional continua sendo
gate eliminatório. Entre os braços corretos, prioriza tempo total, TTFT quente e
decode sustentado em agent loops.

Perguntas:

1. O MTPLX 2.10.0 recupera o decode a 262K sem tuning manual?
2. O memory planning automático do MTPLX 2.10.0 mata o cap-artifact de 128K sem o cap de 100 GB?
3. O Lightning MTP do oMLX 0.6.3 muda a posição das arms L e T frente ao MTPLX?
4. O DFlash cap dinâmico do mlx-dspark 0.17.2 muda o número da arm S sem esforço manual?
5. O Flash-Next 125B-A6B supera a densa 27B em velocidade real e em Terminal-Bench?

## Hardware e topologia

Mesmo rig e topologia da campanha anterior. Sem mudança.

| Papel | Sistema | Uso |
|---|---|---|
| Rig | Mac Studio M4 Max, 128 GB, GPU de 40 núcleos | Serve o modelo e coleta telemetria |
| Driver | MacBook Pro | Envia probes e executa Harbor com Docker |
| Endpoint do rig | `macstudio.local` | Acesso pelo driver na rede local |

O driver não executa o modelo. O rig não executa Docker durante as medições.

## Hipóteses

| ID | Hipótese | Evidência necessária |
|---|---|---|
| R1 | O MTPLX 2.10.0 recupera o decode a 262K para a faixa de oMLX/dspark. | Decode tps a 262K, mesma arm V, só a versão muda |
| R2 | O memory planning automático elimina o miss de cache a 128K sem cap manual. | `tool_turn` e `append` hit a 128K, cap default |
| R3 | O Lightning MTP do oMLX aproxima L/T do MTPLX no decode. | A/B oMLX 0.6.3 com MTP on/off contra MTPLX |
| R4 | O DFlash cap dinâmico mantém ou melhora a arm S sem regressão de correção. | Decode e correção da arm S, cap auto vs fixo antigo |
| R5 | O Flash-Next é mais rápido que a densa 27B, mas não vence em agente. | Velocidade ponta a ponta e Terminal-Bench dos dois |

## Escopo

### Incluído

- **Trilha A — re-probe MTPLX 2.10.0.** Arms V (4-bit Optimized-Speed) e Y (8-bit
  Optimized-Quality) a 128K e 262K. Cap default primeiro; só depois cap manual se
  precisar isolar. Fecha R1 e R2.
- **Trilha B — re-probe oMLX 0.6.3.** Arms L (AWQ 5bpw) e T (oQ8e 8.6bpw) com
  Lightning MTP on e off. A/B do MTP como variável isolada. Fecha R3.
- **Trilha C — re-probe mlx-dspark 0.17.2.** Arm S (8-bit + DFlash2) com cap
  dinâmico. Compara com o número antigo de cap fixo. Fecha R4.
- **Trilha D — modelo novo Flash-Next 125B-A6B.** Braço novo no runtime de melhor
  suporte. Velocidade ponta a ponta mais Terminal-Bench. Fecha R5.

### Fora de escopo

- Novos runtimes fora dos três já medidos.
- Quants que não sejam os já catalogados, exceto o pack oficial do Flash-Next.
- Re-treino ou fine-tune de qualquer drafter.

## Regra de medição

Isolar uma variável por vez ([memory: isolate-the-variable-when-measuring]). Na
trilha de re-probe, o único fator que muda é a versão do runtime; modelo, quant,
contexto e sampling ficam fixos frente à campanha anterior. Na trilha do
Flash-Next, o modelo muda e o resto segue o catálogo.

Reusar o harness existente:

- Probe de cache: `scripts/cache_probe.py` (cenários cold, identical, append, middle_mutation, tool_turn).
- Drivers por runtime: `scripts/run-mtplx.sh`, `scripts/run-omlx.sh`, `scripts/run-mlx-dspark.sh`.
- Consolidação: `scripts/consolidate.py` → `scripts/render_overview.py`.
- Perfis de config: `scripts/omlx_config.py`, `scripts/mlx_dspark_config.py`.

## Gates

1. **Disco.** Checar `df` antes de baixar o Flash-Next. O pack 4-bit ~65 GB
   ([memory: check-disk-before-model-downloads]).
2. **Correção.** Braço que erra o needle ou perde tool state é eliminado antes de
   qualquer comparação de velocidade.
3. **Baseline vivo.** Re-medir o incumbente na versão nova antes de declarar
   qualquer regressão ou ganho.

## Fases

1. **Trilha A (MTPLX 2.10.0), 128K.** Mais barata, sem download. Testa R2 direto.
2. **Trilha A, 262K.** Testa R1, o colapso de decode.
3. **Trilhas B e C.** Re-probe oMLX e mlx-dspark.
4. **Trilha D.** Só depois do gate de disco. Baixar Flash-Next, smoke, velocidade, Terminal-Bench.
5. **Consolidação.** Atualizar `overview` e `perf-lines`; publicar no site gh-pages
   ([memory: qwen38-pages-site]).

## Saídas

- Distilados sob `bench/qwen3.8-prefix-cache/results/` (guideline ≤ ~1 MB por arquivo).
- Logs crus sob `bench/qwen3.8-prefix-cache/logs/` (ignorados pelo git).
- Dashboards atualizados em `results/overview.html` e `results/perf-lines.html`.
- Veredito por pergunta (R1–R5) neste plano, no fim.

## Veredito

**R2 — fechado (2026-08-30). Não confirmado no default; fix parcial via SSD.**
O planejamento automático da 2.10.0 reproduz o mesmo cap 48G/24G-por-sessão da 2.9.2 —
não conserta o artefato. No default (SSD off), V @128K erra `append` e `tool_turn` (0.00).
O fix de RAM da 2.9.2 (cap 100G) não transfere: pico de 119.8G a 128K não deixa espaço.
O caminho correto é `--ssd-session-cache on` (default-ON no vendor; nosso launcher tinha off),
seguro de memória (sem swap). Resultado V @128K SSD-on:

| Cenário | 2.10 default (SSD off) | 2.10 SSD on |
|---|---|---|
| append | 0.00 | 0.99 (recuperou) |
| tool_turn | 0.00 | 0.00 (não recuperou) |

O miss do `tool_turn` na rodada CHEIA 5×3 SSD-on é REPRODUTÍVEL (2 rodadas byte-idênticas) e foi
diagnosticado com `MTPLX_DEBUG_PREFIX_DIVERGENCE=1`. No `tool_turn` medido, o melhor match bancado
é a entrada do `append`: `matched=125610 prompt_len=126688` (99,2% do base compartilhado, diverge só
no sufixo). Mesmo assim: `store-on-prefill cached=0 restore=cold` = re-prefill cheio. Dois fatores:
(1) backlog de postcommit (27 `cross_session_foreground_preempted`, backlog 4) impede o prime do
tool_turn de bancar o base LIMPO a tempo — nos runs curtos existe `clean prefix (matched=126688)` ->
`exact-restore`; (2) o near-prefix não reusa os 125610 compartilhados quando só há entrada de sufixo
divergente. Não é evicção por cap nem SSD (refutados). oMLX/dspark não têm isso (reusam o base por bloco).
Implicação prática: reuso a 128K funciona para conversa única que cresce; quebra sob churn com tool turns.
Issue postável: `mtplx-cache-reuse-issue.md`.
Dados: `results/runtime-refresh/cache-probe-mtplx2100{,-ssd,-ssd-diag,-ssd-diag2,-ssd-pressure,-ssd-repro}.jsonl`.
Ver [[mtplx-session-bank-cap]].

**R1 — fechado (2026-08-30). Confirmado: o colapso de decode a 262K sumiu.**
V cold @262K, MTPLX 2.10.0, SSD-on: decode 7.25 -> **15.16 tps** (2,1×), empata com oMLX
(15.20) e passa o dspark (14.54). Causa do colapso na 2.9.2: pico de RAM 123.5G (perto do
teto de 128G) -> thrashing no decode. A 2.10.0 (memory-aware ceiling + spill SSD) segura o
pico em ~95G, sem swap -> decode recupera. Needles corretos, MTP aceitando 0.38.
Dado: `results/runtime-refresh/cache-probe-mtplx2100-262k.jsonl`.

**R3, R4, R5 — pendentes.**
