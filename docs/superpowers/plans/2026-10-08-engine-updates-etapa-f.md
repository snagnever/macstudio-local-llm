# Etapa F (A/B das correções) — plano de execução

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** medir, um knob por braço, se as correções achadas na web resolvem os problemas da campanha engine-updates-2026-10.

**Architecture:** o harness da campanha (`run-candidate.sh` → `cache_probe.py`) ganha braços novos e um header de
sessão opcional no probe. Os braços rodam com `scripts/run-arm.sh`, a saída fica em `bench/engine-updates-2026-10/results/`.

**Tech Stack:** bash, Python 3 (pytest), MTPLX 2.12.2, mlx-serve 26.10.1, mlx-dspark 0.20.3.

**Spec:** `bench/engine-updates-2026-10/plan.md`, seção "Etapa F".

## Global Constraints

- 3 reps por banda; perfil do probe `temperature=1.0`, `top_p=0.95`, `top_k=20`, reasoning `xhigh`, 4096 tokens.
- Gates: hit ≥ 0.90 em `append` e `tool_turn`; needles corretas; swap ≤ 0.5 GB; zero HTTP 4xx/5xx.
- Um servidor por vez; `sleep 120` entre braços.
- Tag de saída `fx`.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Sem push.

## Review Focus

- Um knob herdado do shell (`MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S`, block size, guard) não pode vazar para os braços originais.
- Sem `--session-header`, o probe manda exatamente os headers de antes.
- O header de sessão é igual no prime e no pedido medido do mesmo cenário/rep, e muda entre cenários.

---

### Task 1: header de sessão no probe

**Files:** `bench/qwen3.8-prefix-cache/scripts/sse_client.py`, `scripts/cache_probe.py`, `tests/test_cache_probe.py`

- [ ] Teste RED: com `--session-header x-mtplx-session-id`, o prime e o pedido medido de um cenário mandam o mesmo
      valor `<session-id>-<cenário>-<rep>`; sem a flag, nenhum header extra.
- [ ] `stream_chat(base_url, payload, timeout_s=900, headers=None)` junta os headers extras ao `Content-Type`.
- [ ] `_stream_chat_checked(base_url, payload, headers=None)` repassa.
- [ ] `--session-header NAME` no parser; `_run_scenario_repeat` monta o header.
- [ ] GREEN: `python3 -m pytest bench/qwen3.8-prefix-cache/tests/test_cache_probe.py -q`. Commit.

### Task 2: braços m1t, m1h, m1th, r27b, s27g, m27f

**Files:** `run-candidate.sh`, `run-mtplx.sh`, `run-mlx-serve.sh`, `run-mlx-dspark.sh`, `bench/engine-updates-2026-10/tests/test_arms.py`

- [ ] Testes RED (`--print`):
  - m1t: `MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S=0`, revisão `v2.12.2-pin0`, sem header;
  - m1h: probe com `--session-header x-mtplx-session-id`, revisão `v2.12.2-sesshdr`;
  - m1th: os dois, revisão `v2.12.2-pin0-sesshdr`;
  - m27f: pack do m27 com o knob definido por `ENGINE_M27F` (`pin0`, `sesshdr` ou `pin0-sesshdr`);
  - r27b: `--draft-block-size 5`, revisão `v26.10.1-blk5`;
  - s27g: `--no-memory-guard`, revisão `v0.20.3-noguard`;
  - m1, m27, r27, s27 não mudam, mesmo com os knobs herdados do shell.
- [ ] Implementação: envs `MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S`, `QWEN38_MLX_DRAFT_BLOCK_SIZE`,
      `QWEN38_MLX_DSPARK_NO_MEMORY_GUARD`; variável `PROBE_SESSION_HEADER` no driver.
- [ ] GREEN: suíte da campanha + `test_mlx_dspark_config.py`. Commit.

### Task 3: rodar os braços MTPLX a 32K

- [ ] `scripts/run-arm.sh m1t 32768 --repeat 3 --tag fx`, depois m1h e m1th.
- [ ] Ler hit, TTFT quente, decode e o motivo de miss no flight recorder.

### Task 4: rodar r27b (32K e 128K) e s27g (32K)

- [ ] `run-arm.sh r27b 32768 …`, `r27b 131072 …`, `s27g 32768 …`, 3 reps, tag `fx`.

### Task 5: m27f a 128K (condicional)

- [ ] Só se um m1* passar nos gates a 32K: `ENGINE_M27F=<knob> run-arm.sh m27f 131072 --repeat 3 --tag fx`.
- [ ] Sem vencedor: registrar o motivo no relatório.

### Task 6: relatório e memória

- [ ] `summarize_driver.py` sobre os `*-fx.jsonl` → `results/summary-fx.json`.
- [ ] `results/etapa-f-fixes.md`: tabela braço × original, leitura por problema, o que segue aberto.
- [ ] Atualizar `results/summary.md`, `fixes-research.md` (status), a memória e o índice. Commit.
