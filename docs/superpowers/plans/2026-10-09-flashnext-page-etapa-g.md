# Etapa G (dados para a página perf-lines) — plano de execução

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** medir o que falta da stack de outubro do Flash-Next e regenerar `reports/qwen38-flashnext-perf-lines.html`
com as séries n2, o1, MTPLX 2.12.2, d1 e c1 (referência).

**Architecture:** o harness da campanha (`run-candidate.sh` → `cache_probe.py`) ganha os braços m1v, m1x, m1q e o
YaRN do ds4. Um orquestrador roda a fila e devolve o driver diário no fim. O consolidador ganha um perfil 2026-10
que lê as duas campanhas e grava um JSON próprio; o renderer da página lê esse JSON. A página de overview de setembro
não muda.

**Tech Stack:** bash, Python 3 (pytest/unittest), MTPLX 2.12.2, mlx-serve 26.10.1, oMLX 0.7.0, ds4 upstream @ `0aaea5a`.

**Spec:** `bench/engine-updates-2026-10/plan.md`, seção "Etapa G".

## Global Constraints

- Probe: `temperature=1.0`, `top_p=0.95`, `top_k=20`, reasoning `xhigh`, 4096 tokens; MTPLX com `--prime-max-tokens 64`.
- Gates: hit ≥ 0.90 em `append` e `tool_turn`; needles corretas; swap ≤ 0.5 GB; zero HTTP 4xx/5xx.
- Tag de saída `pg`. Um servidor por vez; `sleep 120` entre braços.
- Texto publicado em `reports/` sai em inglês.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Push e PR só com o pedido do usuário.
- Arquivos de script em execução são trocados por rename atômico (`os.replace`), nunca reescritos no lugar.

## Review Focus

- Um knob novo (`QWEN38_MTPLX_VENDOR_DEFAULT`, `QWEN38_MTPLX_MEMORY_LIMIT`, `QWEN38_MTPLX_KV_QUANT`, `DS4_QWEN4_YARN_FACTOR`) herdado do shell não pode vazar para m1, m27, c4 ou d1 sem `--yarn`.
- O perfil 2026-10 do consolidador não pode mudar o `reports.json` de setembro nem a página de overview.
- Uma banda recusada (HTTP 507, `PrefillDoesNotFit`) vira ponto "refused" com motivo, não some da tabela.
- Quando há mais de um grupo para série × banda, vale o de mais reps; empate → o mais recente.
- Pontos do MTPLX mostram a config (vendor default, memory max, KV q8) no rótulo.

---

### Task 1: braços m1v, m1x, m1q e YaRN do d1

**Files:** `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh`,
`bench/qwen3.8-prefix-cache/scripts/run-mtplx.sh`, `bench/qwen3.8-prefix-cache/scripts/run-ds4.sh`,
`bench/engine-updates-2026-10/tests/test_arms.py`

- [ ] Testes RED (`--print`):
  - `test_m1v_runs_vendor_default_command`: comando sem `--profile`, `--depth`, `--context-window`, `--ssd-session-cache`, `--reasoning*`; mantém `--model`, `--host`, `--port 8000`, `--no-auth`; revisão `v2.12.2-vendor`; `--prime-max-tokens 64`.
  - `test_m1x_sets_memory_limit_max`: `--memory-limit max`, revisão `v2.12.2-memmax`.
  - `test_m1q_sets_paged_kv_q8`: `--paged-kv-quantization q8`, revisão `v2.12.2-kvq8`.
  - `test_d1_yarn_sets_ds4_factor`: `d1 524288 --yarn 2.0` → `DS4_QWEN4_YARN_FACTOR=2.0` no comando e `-c 524288`; revisão termina em `-yarn2.0`.
  - `test_g_knobs_do_not_leak`: com os quatro envs no shell, m1, m27, c4 e `d1 32768` não mostram nenhum deles.
- [ ] Implementar: envs no `run-mtplx.sh` (comando mínimo quando `QWEN38_MTPLX_VENDOR_DEFAULT=1`; `--memory-limit`; `--paged-kv-quantization`) e `env DS4_QWEN4_YARN_FACTOR=…` no `run-ds4.sh`; `run-candidate.sh` faz `unset` dos quatro e exporta só no braço certo.
- [ ] GREEN: `uv run --no-project --with pytest pytest -q bench/engine-updates-2026-10/tests bench/qwen38-flashnext-daily-driver-2026-09/tests`. Commit.

### Task 2: orquestrador da Etapa G

**Files:** `bench/engine-updates-2026-10/scripts/run-etapa-g.sh`, `bench/engine-updates-2026-10/tests/test_band.py`

- [ ] Teste RED `test_etapa_g_dry_run_lists_queue`: com `ENGINE_BAND_DRY=1`, imprime a fila na ordem
  G1 (n2, o1, m1, d1 a 8K, 3 reps) → G2 (m1v a 128K, 1 rep) → G3 (d1 128K 3 reps, 256K 1 rep, 512K `--yarn 2.0` 1 rep),
  todos com `--tag pg`, e a linha final de relançar o driver diário.
- [ ] Implementar. A G2 tem ramos: o script roda m1v 1 rep; se a saída tiver HTTP 507, roda m1x 1 rep; se m1x recusar,
  roda m1q. O primeiro que passar ganha 3 reps a 128K; o m1q ganha também 256K 1 rep.
- [ ] GREEN e commit.

### Task 3: rodar G1 e G2

- [ ] Parar o driver diário (porta 11234). Rodar `scripts/run-etapa-g.sh` em background com monitor.
- [ ] Ler cada braço ao terminar (`summarize_driver.py --glob '*-pg.jsonl'`). Registrar no ledger o ramo que a G2 tomou e o teto que o memory plan do MTPLX reportou no log.

### Task 4: rodar G3 (ds4)

- [ ] Continua na mesma fila. Se o d1 recusar 256K ou 512K, o ponto fica "refused" com o motivo do log.
- [ ] Ao fim, confirmar que o driver diário voltou (`curl :11234/v1/models`).

### Task 5: perfil 2026-10 no consolidador

**Files:** `bench/qwen38-flashnext-daily-driver-2026-09/scripts/consolidate_reports.py`,
`bench/qwen38-flashnext-daily-driver-2026-09/tests/test_consolidate_reports.py`

- [ ] Testes RED:
  - `test_profile_2026_10_reads_both_campaigns`: com dirs fixture de setembro e outubro, o JSON tem as séries n2, o1, m1, d1 e c1.
  - `test_profile_2026_10_picks_most_reps`: n2 a 32K com `-ab` (3 reps) e `-fn` (3 reps) → vale o mais recente; `-smoke` (1 rep) perde para `-pg` (3 reps).
  - `test_refused_band_stays_as_refused_point`: um grupo só com HTTP 507 vira ponto com `refused` e motivo.
  - `test_mtplx_point_carries_config_label`: m1q gera rótulo "KV q8".
  - `test_default_profile_unchanged`: o perfil default produz o mesmo `reports.json` de antes (comparar com o arquivo commitado).
- [ ] Implementar: `--profile {2026-09,2026-10}`; o 2026-10 lê `bench/engine-updates-2026-10/results`, `bench/qwen38-flashnext-updates-2026-10/results` e o c1 de setembro; grava `bench/engine-updates-2026-10/results/reports-2026-10.json`.
- [ ] GREEN e commit.

### Task 6: renderer e página

**Files:** `bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_perf_lines.py`,
`reports/qwen38-flashnext-perf-lines.html`, `reports/index.html`, `reports/README.md`

- [ ] Teste RED `test_render_2026_10_has_notes`: o HTML gerado do JSON 2026-10 contém o chip, as versões, a nota do prime do MTPLX, o aviso "speed, cache and memory only" e a nota de chip (issue #658); séries n2, o1, MTPLX, d1, c1.
- [ ] Implementar: `--data` aponta para o JSON 2026-10; cores e `ABSENT` das séries novas; cards de runtime das versões de outubro (mlx-serve, oMLX, MTPLX, ds4); takeaways e textos dos painéis escritos com os números medidos, em inglês.
- [ ] Regenerar a página; abrir no Chromium (Playwright) e conferir que os gráficos renderizam sem erro de console.
- [ ] Atualizar a data e a descrição em `reports/index.html` e `reports/README.md`. Commit.

### Task 7 (opcional, só com aprovação): qualidade barata

- [ ] HumanEval 164 + jdhodges 40 + Veerman 12, temp 0, para o1 e o melhor MTPLX, com o `compare_quality.py` da
  campanha flashnext-updates. Resultado em `results/quality-o1-mtplx.md` e uma linha na página.

### Task 8: relatório e fechamento

- [ ] `results/etapa-g-page.md`: o que cada bloco mediu, o ramo da G2, recusas e limites.
- [ ] Atualizar `results/summary.md` e a memória (veredito e teto do MTPLX, se mudar).
- [ ] Suítes completas; revisão final da branch; apresentar o menu de fechamento (PR separado do #48).
