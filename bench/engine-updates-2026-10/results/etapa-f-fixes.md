# Etapa F — A/B das correções (2026-10-08)

**A perda de cache do MTPLX 2.12.x vinha do probe, não do memory guard.** O prime do `cache_probe.py` manda
`max_tokens: 1`, e o MTPLX trata um pedido assim como tarefa de background, sem sessão. Com o prime de 64 tokens, o
MTPLX reusa o cache: o Flash-Next passa nos gates a 32K (8.8 s, 1.07× o n2) e o 27B passa a 128K (30.2 s, empate com o
oMLX). No mlx-dspark, `--prefix-cache-rungs 1024` corrige o `append` a 32K. O `--draft-block-size 5` do mlx-serve
quase não muda o decode do 27B a 128K.

O veredito do Flash-Next não muda: o n2 segue driver. O ranking do 27B muda; ver "27B" abaixo.

Rig: M4 Max 128 GB. Probe e gates da campanha, 3 reps, tag `fx`. Um knob por braço. Pesquisa de origem:
[fixes-research.md](fixes-research.md). Dados: `*-t1.0-fx.jsonl`, `summary-fx.json`.

## Resultado por braço

| banda | braço | base | knob | T_turno | base T_turno | warm TTFT id / app / tool | hit app / tool | decode | gates |
| --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | --- |
| 32K | m1t | m1 | `MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S=0` | 52.8 s | 52.7 s | 44 / 46 / 46 s | 0.00 / 0.00 | 77.7 | hit |
| 32K | m1h | m1 | header `x-mtplx-session-id` | 52.5 s | 52.7 s | 0.2 / 2.5 / 46 s | 0.96 / 0.00 | 81.3 | hit, HTTP 503 |
| 32K | **m1p** | m1 | prime com `max_tokens` 64 | **8.8 s** | 52.7 s | 0.1 / 2.5 / 2.4 s | 0.96 / 0.96 | 79.6 | passa |
| 32K | m1hp | m1 | header + prime 64 | 9.0 s | 52.7 s | 0.2 / 6.6 / 2.5 s | 0.96 / 0.96 | 78.9 | passa |
| 128K | **m27f** | m27 | prime com `max_tokens` 64 | **30.2 s** | 834.2 s | 0.4 / 10 / 10 s | 0.99 / 0.99 | 25.5 | passa |
| 32K | s27g | s27 | `--no-memory-guard` | 16.5 s | 16.9 s | 0.1 / 17 / 5.1 s | 0.87 / 0.96 | 44.8 | hit_append |
| 32K | **s27r** | s27 | `--prefix-cache-rungs 1024` | **16.7 s** | 16.9 s | 0.1 / 8.4 / 5.4 s | 0.94 / 0.96 | 45.4 | passa |
| 32K | r27b | r27 | `--draft-block-size 5` | 20.3 s | 19.7 s | 0.6 / 5.8 / 5.9 s | 0.96 / 0.96 | 35.5 | passa |
| 128K | r27b | r27 | `--draft-block-size 5` | 42.1 s | 44.0 s | 1.5 / 11 / 11 s | 0.99 / 0.99 | 16.5 | passa |

Swap delta 0 em todos. O m1hp e o s27r truncaram 1 resposta a 4096 tokens de reasoning (`truncado`, não é falha de
gate). O m1th (pin TTL 0 + header) saiu da rodada: teria os mesmos 503 do m1h.

## Leitura por problema

**MTPLX sem reuso de cache (m1, m1b, m27).** No 2.12.2, `engine_session.is_background_request` marca como tarefa de
background um pedido com `max_tokens` ≤ 48, sem histórico e com system prompt diferente do da sessão principal (o
formato de um job de título do Open WebUI). O prime do probe tem `max_tokens` 1 e um system prompt novo a cada rep
("Cache probe trial 00N"), então cai nessa regra. Sem header, o prime roda sem sessão e não grava no bank; o pedido
medido não acha prefixo reusável, e o guard registra `prefill_admission_shed` com `reusable_prefix_tokens: 0`. O shed
era sintoma, não causa. O efeito depende da memória livre: o m27 a 32K (27B, ~62 GB wired) reusou o cache com o
prime de 1 token; o Flash-Next (77 GB de pesos) e o 27B a 128K não reusaram. Sob pressão, o MTPLX descarta primeiro o
prefixo de uma sessão `anon`. Com header, o prime recebe HTTP 503 `session_busy` enquanto o turno anterior grava. O pin TTL 0
(issue #567) não muda nada. Um cliente de agente real manda `max_tokens` grande e histórico, então não cai nessa regra.

**MTPLX a 128K no Flash-Next (HTTP 507).** Fora da Etapa F; o teto de 114 688 tokens continua.

**mlx-dspark `append` com hit 0.87 (s27).** O Qwen3.8-27B é híbrido (camadas recorrentes). O mlx-dspark só reusa o
estado recorrente até um snapshot. O memory guard não é a causa (s27g igual ao s27). Com snapshot a cada 1024 tokens
(`--prefix-cache-rungs 1024`), o `append` reusa 0.94 e o TTFT cai de 17 s para 8.4 s. O cold sobe 7% (102 → 110 s).
O s27r a 128K não foi medido.

**mlx-serve + DFlash2 perde decode a 128K (r27).** Com bloco 5, a aceitação por draft sobe (~50% → 65–77%), mas cada
rodada aceita menos tokens: decode 35.5 tok/s a 32K (contra 37.0) e 16.5 tok/s a 128K (contra 15.5). A queda com o
contexto continua. A correção do PR #754 ainda não tem release.

**r27 errou 1 needle a 128K.** O r27b acertou todas a 128K. Leitura: ruído de amostragem a `temperature=1.0`.

## Efeito no veredito

- **Flash-Next:** o n2 segue driver. O m1p fica em 2º a 32K (8.8 s contra 10.1 s do o1), mas 1.07× o n2 não passa o
  critério (≤ 0.97×), e o MTPLX ainda recusa 128K.
- **27B:** três runtimes passam nas duas bandas com a config de servidor da campanha: oMLX 0.7.0 (18.0 / 29.8 s),
  MTPLX 2.12.2 (17.8 / 30.2 s; 32K do m27, 128K do m27f) e mlx-serve 26.10.1 (19.7 / 44.0 s; r27b nas duas bandas
  20.3 / 42.1 s). oMLX e MTPLX empatam (±3%). O mlx-dspark com `--prefix-cache-rungs 1024` é o mais rápido a 32K
  (16.7 s) e o s27 sem rungs é o mais rápido a 128K (25.0 s); falta medir o s27r a 128K para fechar o mlx-dspark como
  líder.

## Auditoria dos vereditos antigos do MTPLX (2026-10-09)

A regra de background existe em todas as versões instaladas (2.10.0, 2.11.1, 2.11.2, 2.12.2), e o probe sempre usou o
prime de 1 token. A auditoria leu os registros e os logs de todo run MTPLX com turno quente abaixo de 0.90:

| dados | versão | o que os registros mostram | memória / relatório | veredito |
| --- | --- | --- | --- | --- |
| `c4-131072`, `c4-262144` (Flash-Next) | 2.11.2 | HTTP 507 no cold e em todos os primes | `mtplx-flashnext-128k-fit` (teto 114 688) | **vale**: recusa de memória, não reuso |
| `c4-131072-mem102g` | 2.11.2 | `identical` 1.00, `append` 0.99, `tool_turn` 0.00 com `allocation_failure_shed` | `mtplx-flashnext-128k-fit` ("102G admite mas re-prefill falha") | **vale**: falha de alocação real |
| `cache-probe.jsonl` (27B V/Y/Z) | 2.9.1 | misses a ~3K (esperados) e `tool_turn` a 126K | `mtplx-session-bank-cap` | **vale**: A/B isolado com o mesmo prime (cap 24G → 48G: hit 0.00 → 0.99) |
| `runtime-refresh/cache-probe-mtplx2100*` (27B, 128K) | 2.10.0 | `tool_turn` 0.00 depois do `middle_mutation`; `append` 0.00 sem SSD | `mtplx-cache-reuse-issue.md` (rascunho, nunca publicado) | **incerto**: rodou com o cap auto de 24G (causa já confirmada na memória acima), mas o "prime preempted" do rascunho tem a assinatura do prime sem sessão |

As páginas de `reports/` usam os dados do 2.9.x (27B, já com o cap do bank corrigido) e do c4 2.11.2; nenhuma usa
os runs do 2.10.0. O rascunho de issue do 2.10.0 ganhou uma nota: não publicar sem re-medir com o prime de 64 tokens.

## Limitações

- O m27 a 32K usou o prime antigo e passou; o m27f mediu só 128K.
- Os braços oMLX, mlx-serve e mlx-dspark da campanha usaram o prime de 1 token. Eles reusaram o cache, então a regra
  de background do MTPLX não os afeta.
- A causa do 503 com header vem da leitura do código do 2.12.2, não de uma issue do MTPLX.
