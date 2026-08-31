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
divergente. Não é evicção por cap nem SSD (refutados). JÁ MAPEADO no vendor: #121 (CLOSED, `tool_call_history_rewrite`)
e #383 (OPEN, cross-session preemption). O knob que o app usa (`MTPLX_POSTCOMMIT_WAIT_TIMEOUT_S=30`) NÃO
resolve (A/B 5×3 byte-idêntico). Causa-raiz no postcommit: `unsafe_reason=stop_token_boundary_mismatch` —
o markup do tool desalinha o boundary; append reusa 125440 via block-clone, tool_turn vai cold (0).
Novo vs #121: fechado como corrigido (block-overlap salvage), mas a 128K o tool_turn tem cached=0 (sem
salvage). Ação: COMENTAR no #121/#383 com o repro, não issue nova. Implicação: agente com tool calls a
128K paga re-prefill cheio (~870s) por turno. oMLX/dspark não têm isso.
Dados: `results/runtime-refresh/cache-probe-mtplx2100{,-ssd,-ssd-diag,-ssd-diag2,-ssd-pressure,-ssd-repro,-ssd-waitfix}.jsonl`.
Ver [[mtplx-session-bank-cap]].

**R1 — fechado (2026-08-30). Confirmado: o colapso de decode a 262K sumiu.**
V cold @262K, MTPLX 2.10.0, SSD-on: decode 7.25 -> **15.16 tps** (2,1×), empata com oMLX
(15.20) e passa o dspark (14.54). Causa do colapso na 2.9.2: pico de RAM 123.5G (perto do
teto de 128G) -> thrashing no decode. A 2.10.0 (memory-aware ceiling + spill SSD) segura o
pico em ~95G, sem swap -> decode recupera. Needles corretos, MTP aceitando 0.38.
Dado: `results/runtime-refresh/cache-probe-mtplx2100-262k.jsonl`.

**R3 — fechado (2026-08-31, teste mínimo). Ganho modesto.**
Arm T (oQ8e-mtp) @32K, cold, oMLX **0.6.4** (via git tag; a 0.6.4 é mais nova que a 0.6.3,
checado antes) com `mtp_enabled:true`. Decode 30.57 -> **31.95 tps (+4.5%)**, prefill
211.9 -> 226.1 (+6.7%), correto, MTP acc 0.83. Os ganhos grandes de Lightning MTP das
notas (2.3-2.6x) são do Flash-Next (MoE), não do denso oQ8e. Só um ponto (32K); não
A/B-ei MTP on/off. Nota: o record sai rotulado `runtime-revision v0.6.3rc2` (label fixo no
arm_metadata), mas rodou na 0.6.4 (nome do arquivo `-v064`). Dado: `results/runtime-refresh/refresh-omlx-t-32k-v064.jsonl`.

**R4 — fechado (2026-08-31, teste mínimo). Ganho modesto.**
Arm S (8bit + DFlash2, `--max-draft auto` = cap dinâmico) @32K, cold, mlx-dspark **0.17.2**
(latest, checado). Decode 39.9 -> **41.80 tps (+4.8%)**, prefill 252 -> 276 (+9.4%), correto,
cap auto-resolveu para 7. Sem regressão. Dado: `results/runtime-refresh/refresh-dspark-s-32k-v0172.jsonl`.

Resumo R3/R4: as versões novas dão ganho pequeno (+4-5% decode) a 32K, sem regressão; nenhuma
vira o jogo neste ponto. Harness: guards de versão do oMLX/dspark agora env-overridable
(`QWEN38_OMLX_EXPECTED_VERSION`, `QWEN38_MLX_DSPARK_EXPECTED_VERSION`); stages `refresh-omlx-t-32k`
e `refresh-dspark-s-32k`.

## R5 — Flash-Next: stacks e quants (pesquisa 2026-08-31)

O Flash-Next completo é MoE 125B-A6B. O desafio num M4 Max 128GB é caber com folga para
o KV. Stacks e quants levantados (web + Reddit r/LocalLLaMA):

| # | Stack | Quant | Disco | Residente | Cabe 128G | Spec |
|---|---|---|---|---|---|---|
| 1 | oMLX 0.6.4 | `Jundot/Qwen3.8-Flash-Next-oQ4e-mtp` | 106GB | ~87GB (SSD-map PLE) | Sim (vendor validou M5 Max 128GB) | Lightning MTP + sparse prefill |
| 2 | llama.cpp / LM Studio | `unsloth/Qwen3.8-Flash-Next-GGUF` UD IQ4_XS/Q4 | ~93GB | ~54GB (n-gram no SSD) | Sim, folgado | MTP + SSD n-gram + vision |
| 3 | MLX (mlx-vlm/LM Studio) | `Vontra/…-MLX-4bit` (~65G), `pipenetwork/…-MLX-6bit`, `Youssofal/…-MTPLX-Optimized-Speed` (115G) | 65–115GB | varia | 4-bit sim; 6-bit/MTPLX apertado | MTPLX = MTP nativo |

Descartados: `wtdcode/…-AWQ-W4A16` (180GB, não cabe); `sh0wie/…-REAP-288` (73GB mas PODADO,
não é o modelo completo — confunde a comparação vs densa).

Datapoints de Mac (poucos, modelo é recente): oMLX oQ4e num M5 Max 128GB TG ~46 tok/s @32K,
262K cold 355s @87GB pico; GGUF IQ1_S num M1 Ultra 128GB PP ~400 / TG ~20 (1-bit, qualidade baixa).

**Veredito de qualidade (comunidade, incl. teste próprio NVFP4-vs-densa em vLLM):** Flash-Next é
mais rápido e impecável em JSON estrito/injeção/SLA e vence raciocínio alto/code-gen; a densa 27B
ainda vence trabalho simbólico multi-step sustentado (bug-fix, provas, puzzles). Flash-Next tem
falha nova: promete o entregável, declara "done", não gera nada. Não é drop-in; promoção condicional.

**Escolha para rodar o R5:** stack **#1 (oMLX 0.6.4 + oQ4e-mtp)** — único caminho do modelo COMPLETO
que cabe em 128GB, vendor-validado, integra com o harness (`run-omlx.sh`). Custo: download 106GB +
memória apertada para KV longo.

### Próximos passos para avaliar (após o #1)
- **#2 GGUF Unsloth (IQ4_XS/Q4) via llama.cpp/LM Studio** — residente menor (~54GB), mais folga p/ KV;
  comparar velocidade e qualidade vs o oMLX.
- **#3 MLX 4-bit (`Vontra`)** — o mais leve (~65GB), stack MLX puro; e `pipenetwork` 6-bit se sobrar RAM.
- **MTPLX Flash-Next pack (115GB)** — MTP nativo, mas apertado em 128GB; testar se carrega residente sem swap.
- Em todos: velocidade ponta a ponta + Terminal-Bench vs a densa 27B (fecha o R5).
- Referência: [[qwen38-flash-next-stacks]].

### R5 — resultado do smoke (2026-08-31)

Flash-Next @32K, oMLX 0.6.4, arm FN (oQ4e-mtp, Lightning MTP + sparse prefill), 5 cenários × 1 rep,
todos corretos. **Precisou `--memory-guard off`** (parametrizado por `QWEN38_OMLX_MEMORY_GUARD` no
run-omlx.sh): no default (balanced) o preflight rejeita — os pesos carregam 99.6GB e o safety cap
(90% de 107.5GB = 96.8GB) é menor que os pesos.

| Cenário | cache hit | decode tps | prefill tps |
|---|---|---|---|
| cold | 0.000 | 49.2 | 331 |
| identical | 0.975 | 47.1 | 229 |
| append | 0.940 | 45.4 | 283 |
| middle_mutation | 0.449 | 48.2 | 307 |
| tool_turn | 0.938 | 46.7 | 284 |

**Velocidade:** decode ~47 tps — mais rápido que TODAS as densas @32K (L 42.5, S 41.8, T 32.0), como
esperado de um MoE A6B. Cache reusa bem, incluindo `tool_turn` 0.938 (o cache content-addressed do
oMLX resolve o tool turn, ao contrário do session-bank do MTPLX). Needles corretos.

**Memória (limite real):** pico 128.87GB + **6.3GB de swap** — o oQ4e (99.6GB de pesos) já raspa o
teto de 128GB a 32K. **128K não foi rodado**: KV +~3.6GB estouraria o metal cap (107.5GB) / swap
catastrófico. Rodar contexto longo exige subir `iogpu.wired_limit_mb` (sudo, ação do usuário) ou
um quant menor (MLX-4bit ~65GB — próxima stack a avaliar).

**Qualidade** (do teste próprio NVFP4-vs-densa + comunidade, [[qwen38-flash-next-stacks]]): Flash-Next
mais rápido e impecável em JSON/injeção/SLA e vence raciocínio alto/code-gen; a densa 27B ainda vence
simbólico multi-step sustentado; falha nova "declara done, não gera nada". Não é drop-in.

**Veredito R5:** Flash-Next é mais rápido que a densa (decode +12-47%) e reusa cache melhor no
`tool_turn`, MAS a stack oQ4e satura os 128GB já a 32K (swap), e em qualidade não desloca a densa em
trabalho de agente sustentado. Promoção condicional, não substituto. Próximo: quant menor (MLX-4bit)
para ganhar folga de contexto, + Terminal-Bench para o veredito de agente.
Dado: `results/runtime-refresh/refresh-flashnext-32k-v064.jsonl`.
