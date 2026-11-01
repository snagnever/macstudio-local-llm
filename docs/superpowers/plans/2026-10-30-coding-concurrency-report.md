# Report "Can one Mac Studio serve Claude Code?" — Implementation Plan (Entregas A e C)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reescrever `reports/qwen38-flashnext-concurrency.html` por cenário de uso, em segundos e faixas de experiência, com os dados das campanhas de 18/10 e 29/10, e atualizar os docs. A campanha nova (Entrega B do spec) tem runbook próprio, escrito depois deste plano; este report já lê os arquivos que ela vai produzir.

**Architecture:** O `render_report.py` mantém o `collect()` e ganha um payload normalizado por cenário e servidor (`scenarios`). Três módulos novos ao lado dele separam responsabilidades: `claude_requests.py` (requests por sessão de Claude Code: parser do log do Splash hoje, mesmo schema do proxy da campanha B amanhã), `report_charts.py` (builders SVG das formas novas) e `report_sections.py` (as seções da página nova). As seções antigas do 26.10.1 vão para o apêndice sem reescrita.

**Tech Stack:** Python 3.9 (stdlib), pytest via `uv run --no-project --with pytest`, bash 3.2 no rig, SVG inline, CSS com os tokens do report atual.

**Spec:** `docs/superpowers/specs/2026-10-30-coding-concurrency-report-design.md` (mockup aprovado: `docs/superpowers/specs/2026-10-30-coding-concurrency-report-mockup.html`).

## Global Constraints

- Página em inglês, autocontida, mesma URL, mesmos tokens de tema do report atual (`--s1` Splash azul, `--s2` mlx-serve laranja). Sem biblioteca de gráficos.
- Faixas (spec): resposta começa ≤ 2 s boa, 2–5 s aceitável, > 5 s ruim; geração ≥ 60 tok/s boa, 30–60 aceitável, < 30 ruim; primeiro prompt ≤ 30 s boa, 30–60 aceitável, > 60 ruim; chamada curta p95 ≤ 5 s boa, 5–60 aceitável, > 60 ruim. Limites inclusivos na faixa melhor (2.0 s é boa; 5.0 s é aceitável).
- Servidor recomendado fixo: `RECOMMENDED = "splash"`. Colunas: `splash` (Splash 1.5.0, ukisai Swift 1.5 GGUF IQ4_XS + DFlash2) e `mlx` (mlx-serve 26.10.3, Dankpaws Swift 1.5 MLX 4.7 bpw). O 26.10.1 só no apêndice, chave `legacy`.
- Todo gráfico com ≥ 2 séries tem legenda; todo gráfico tem `<title>` nas marcas (tooltip) e uma vista em tabela (`<details class="tbl">`). Hachura (`url(#hatch)`) e o texto `n/m` para dado ausente. Nenhum eixo duplo.
- Nenhum número da página vem de texto fixo: tudo sai do payload (`results/report-data.json`), que os testes comparam com os summaries.
- Dados brutos rastreados em `bench/<campanha>/results/`; logs só no rig. Não tocar no checkout principal do rig; ler logs em `~/LocalProjects/macstudio-local-llm-splashconc/bench/splash-concurrency-2026-10/logs/`.
- Idioma: código, commits e página em inglês; prosa de resultados em pt-BR. Commits terminam com `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Testes: `uv run --no-project --with pytest python -m pytest bench/flashnext-concurrency-2026-10/tests -q` (hoje 111 passam) e `bench/splash-concurrency-2026-10/tests`.

## Review Focus

1. Um `req-*.jsonl` sem request quente (só o primeiro prompt) → `summarize_requests` devolve `None` nos campos quentes e a página mostra `n/m`, sem exceção. Teste no Task 1.
2. Log do Splash truncado: `Done` sem `Started` correspondente, ou `Started` sem `Done` → o parser ignora a linha órfã e segue. Teste no Task 1.
3. Página sem a campanha do Splash e sem `claude-summary.json` (só os dados de 18/10) → renderiza com hachuras e a matriz de cobertura toda ○ na coluna `splash`. Teste no Task 5.
4. Par mais rápido que sozinho num halter (pair < alone) → a linha do halter não tem largura negativa e o rótulo não se sobrepõe. Teste no Task 4.
5. Valores exatamente no limite da faixa (2.0 s, 60 tok/s, 30 s, 5 s) caem na faixa melhor. Teste no Task 3.

---

### Task 1: `claude_requests.py` — requests por sessão de Claude Code

**Files:**
- Create: `bench/flashnext-concurrency-2026-10/scripts/claude_requests.py`
- Test: `bench/flashnext-concurrency-2026-10/tests/test_claude_requests.py`

**Interfaces:**
- Produces:
  - `parse_splash_log(text: str) -> list[dict]`: uma linha por request pareado `Started`/`Done`, no schema de request: `{"t_start_s": float, "ttft_s": float, "t_end_s": float, "input_tokens": int, "cached_tokens": int, "output_tokens": int, "tps": float, "status": 200, "stream": None}`. `t_start_s` e `t_end_s` em segundos desde o primeiro `Started` do log (`HH:MM:SS` do log; vira o dia se o horário recuar). O `Done` casa com o `Started` aberto mais antigo de mesmo `input`; um `Done` sem par e um `Started` sem `Done` são ignorados.
  - `max_concurrent(reqs: list[dict]) -> int`: maior número de requests abertos ao mesmo tempo (varredura de eventos; um fim e um início no mesmo instante contam o fim primeiro).
  - `summarize_requests(reqs: list[dict]) -> dict`: `{"n", "max_concurrent", "first_prompt_ttft_s", "new_tokens_p50", "warm": {"n", "ttft_p50", "ttft_p90", "tps_p50", "tps_min"} | None}`. Quente = `cached_tokens > 0`; primeiro prompt = mediana do `ttft_s` dos requests com `cached_tokens == 0`. Sem requests quentes, `"warm": None`; sem requests frios, `"first_prompt_ttft_s": None`. p90 = `sorted(x)[int(0.9 * (len(x) - 1))]`.
  - `read_requests(path: Path) -> list[dict]` lê um JSONL; `main(argv)`: `claude_requests.py --splash-log LOG --out OUT.jsonl` grava o JSONL.

- [ ] **Step 1: Escrever os testes que falham**

```python
LOG = """19:02:07 Started · input 19,296 · cached 0 · effort xhigh · thinking on
19:02:32 Done · input 19,296 · cached 0 · output 112 · tools 23·d2a9ad50 · TTFT 23.7s · 133.8 tok/s · 4.8 tok/cycle
19:02:32 Started · input 19,622 · cached 19,264 · effort xhigh · thinking on
19:02:34 Done · input 19,622 · cached 19,264 · deduplicated 128 · output 204 · tools 23·d2a9ad50 · TTFT 0.6s · 161.3 tok/s · 4.1 tok/cycle
"""

def test_parse_splash_log_pairs_started_and_done():
    reqs = parse_splash_log(LOG)
    assert [r["input_tokens"] for r in reqs] == [19296, 19622]
    assert reqs[0] == {"t_start_s": 0.0, "ttft_s": 23.7, "t_end_s": 25.0, "input_tokens": 19296, "cached_tokens": 0,
                       "output_tokens": 112, "tps": 133.8, "status": 200, "stream": None}
    assert reqs[1]["t_start_s"] == 25.0 and reqs[1]["cached_tokens"] == 19264

def test_parse_splash_log_ignores_orphans():
    orphan_done = LOG.splitlines()[1] + "\n"
    orphan_start = LOG.splitlines()[0] + "\n"
    assert parse_splash_log(orphan_done) == [] and parse_splash_log(orphan_start) == []

def test_parse_splash_log_wraps_midnight():
    text = LOG.replace("19:02:07", "23:59:50").replace("19:02:32", "00:00:10").replace("19:02:34", "00:00:12")
    assert parse_splash_log(text)[0]["t_end_s"] == 20.0

def test_max_concurrent_counts_overlap():
    reqs = [dict(t_start_s=0, t_end_s=10), dict(t_start_s=5, t_end_s=15), dict(t_start_s=15, t_end_s=20)]
    assert max_concurrent(reqs) == 2

def test_summarize_requests_warm_and_cold():
    s = summarize_requests(parse_splash_log(LOG))
    assert s["n"] == 2 and s["max_concurrent"] == 1
    assert s["first_prompt_ttft_s"] == 23.7 and s["new_tokens_p50"] == pytest.approx(9827)
    assert s["warm"] == {"n": 1, "ttft_p50": 0.6, "ttft_p90": 0.6, "tps_p50": 161.3, "tps_min": 161.3}

def test_summarize_requests_without_warm_is_none():
    s = summarize_requests(parse_splash_log("\n".join(LOG.splitlines()[:2]) + "\n"))
    assert s["warm"] is None and s["first_prompt_ttft_s"] == 23.7

def test_main_writes_jsonl(tmp_path):
    log = tmp_path / "boot.log"; log.write_text(LOG); out = tmp_path / "req.jsonl"
    assert main(["--splash-log", str(log), "--out", str(out)]) == 0
    assert len(read_requests(out)) == 2
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `uv run --no-project --with pytest python -m pytest bench/flashnext-concurrency-2026-10/tests/test_claude_requests.py -q`
Expected: FAIL com `ModuleNotFoundError: claude_requests`

- [ ] **Step 3: Implementar `claude_requests.py`** com as assinaturas acima. Regex do `Started`: `^(\d\d:\d\d:\d\d) Started · input ([\d,]+) · cached ([\d,]+)`; do `Done`: `^(\d\d:\d\d:\d\d) Done · input ([\d,]+) · cached ([\d,]+)(?: · deduplicated [\d,]+)? · output ([\d,]+) .*? TTFT ([\d.]+)s · ([\d.]+) tok/s`. Docstring de módulo em inglês com o schema de request.

- [ ] **Step 4: Rodar os testes**

Run: o mesmo comando. Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add bench/flashnext-concurrency-2026-10/scripts/claude_requests.py bench/flashnext-concurrency-2026-10/tests/test_claude_requests.py
git commit -m "bench(flashnext-concurrency): per-request parser for Claude Code sessions"
```

### Task 2: requests dos `kcc*` de 29/10 e `summarize_claude.py`

**Files:**
- Create: `bench/flashnext-concurrency-2026-10/scripts/summarize_claude.py`
- Create: `bench/splash-concurrency-2026-10/results/req-kcc1r{1,2}-{a,b}.jsonl`, `req-kcc2r{1,2,3}.jsonl` (gerados no rig)
- Create: `bench/splash-concurrency-2026-10/results/claude-summary.json`, `bench/flashnext-concurrency-2026-10/results/claude-summary.json` (gerados)
- Test: `bench/flashnext-concurrency-2026-10/tests/test_summarize_claude.py`

**Interfaces:**
- Consumes: `claude_requests.read_requests`, `summarize_requests`.
- Produces: `summarize_claude(results_dir: Path, prefix: str) -> dict` com
  ```
  {"prefix": "kcc", "profiles": {"small": {"tasks": ["a","b"], "alone_s": {"a": 41.0, "b": 40.5},
     "pair_s": {"a": 58.7, "b": 60.0}, "pair_wall_s": 61.7, "serial_sum_s": 81.5, "time_saved": 0.24,
     "turns": {"a": 10, "b": 6}, "task_done": true, "errors": 0}},
   "requests": {"alone": <summarize_requests>|None, "pair": <summarize_requests>|None}}
  ```
  `time_saved = 1 - pair_wall_s / serial_sum_s` (0.24 = 1 − 61.7 / 81.5; a página mostra "finishes 24% sooner";
  o 26.10.1 dá −0.07, "finishes 7% later"). O spec e o mockup escrevem "+24% de trabalho por hora"; o número
  certo para essa frase seria +32% (81.5 / 61.7). O plano usa `time_saved`, que coincide com os summaries das
  campanhas, e a seção 2 chama o gráfico de "Time saved by running the pair together". Perfil `small` = tarefas a e b; perfil `realistic` = c e d (presente só quando existe `cc-<prefix>1r*-c.json`). `requests.alone` junta todos os `req-<prefix>1r*-*.jsonl`; `requests.pair` junta os `req-<prefix>2r*.jsonl` e `req-<prefix>2r*-*.jsonl`. `main(argv)`: `summarize_claude.py --results-dir DIR --prefix kcc --out DIR/claude-summary.json [--markdown]`.

- [ ] **Step 1: Testes que falham** (fixture: `_cc(results, name, wall, task, turns)` grava `cc-<name>.json` com `wall_s`, `task`, `num_turns`, `is_error`, `task_done`; `_req(results, name, reqs)` grava o JSONL)

```python
def test_summarize_claude_small_profile(tmp_path):
    for r, w in ((1, 40.0), (2, 42.0)): _cc(tmp_path, f"kcc1r{r}-a", w, "a", 10); _cc(tmp_path, f"kcc1r{r}-b", 40.0, "b", 6)
    for r in (1, 2, 3): _cc(tmp_path, f"kcc2r{r}-a", 60.0, "a", 10); _cc(tmp_path, f"kcc2r{r}-b", 50.0, "b", 6)
    s = summarize_claude(tmp_path, "kcc")
    p = s["profiles"]["small"]
    assert p["alone_s"] == {"a": 41.0, "b": 40.0} and p["pair_s"] == {"a": 60.0, "b": 50.0}
    assert p["pair_wall_s"] == 60.0 and p["serial_sum_s"] == 81.0 and p["time_saved"] == pytest.approx(0.259, abs=0.001)
    assert "realistic" not in s["profiles"] and s["requests"] == {"alone": None, "pair": None}

def test_summarize_claude_requests_split_alone_and_pair(tmp_path):
    _req(tmp_path, "kcc1r1-a", [COLD, WARM]); _req(tmp_path, "kcc2r1", [COLD, WARM, WARM])
    s = summarize_claude(tmp_path, "kcc")
    assert s["requests"]["alone"]["n"] == 2 and s["requests"]["pair"]["n"] == 3

def test_main_writes_json_and_markdown(tmp_path): ...  # exit 0, arquivo existe, "--markdown" imprime uma tabela com "time_saved"
```

- [ ] **Step 2: Rodar e confirmar a falha.** Expected: `ModuleNotFoundError: summarize_claude`.

- [ ] **Step 3: Implementar `summarize_claude.py`.** Reusar a lógica de `render_report._claude_code` (médias por tarefa, `pair_wall` = média do `max(a, b)` por rep) e apagar `_claude_code` do `render_report.py` no Task 3.

- [ ] **Step 4: Rodar os testes.** Expected: 3 passed.

- [ ] **Step 5: Gerar os JSONL no rig** (só leitura dos logs; não para nenhum servidor):

```bash
ssh vitor@100.110.87.118 'cd ~/LocalProjects/macstudio-local-llm-splashconc && git fetch -q && git checkout -q <branch-deste-plano> && cd bench/splash-concurrency-2026-10 && for f in logs/k2c1-131072-t1.0-kcc*-boot.log; do t=$(basename $f -boot.log); t=${t#k2c1-131072-t1.0-}; [ "$t" = kccsmoke ] && continue; python3 ../flashnext-concurrency-2026-10/scripts/claude_requests.py --splash-log $f --out results/req-$t.jsonl; done && ls results/req-*.jsonl'
```
Expected: 7 arquivos (`req-kcc1r1-a`, `req-kcc1r1-b`, `req-kcc1r2-a`, `req-kcc1r2-b`, `req-kcc2r1`, `req-kcc2r2`, `req-kcc2r3`). Copiar para o checkout local com `scp` (ou commit no rig e `git pull`).

- [ ] **Step 6: Gerar os summaries**

```bash
python3 bench/flashnext-concurrency-2026-10/scripts/summarize_claude.py --results-dir bench/splash-concurrency-2026-10/results --prefix kcc --out bench/splash-concurrency-2026-10/results/claude-summary.json --markdown
python3 bench/flashnext-concurrency-2026-10/scripts/summarize_claude.py --results-dir bench/flashnext-concurrency-2026-10/results --prefix cc --out bench/flashnext-concurrency-2026-10/results/claude-summary.json --markdown
```
Expected: o Splash mostra `alone.warm.ttft_p50` ≈ 0.8, `pair.warm.ttft_p50` ≈ 1.8, `pair.max_concurrent` = 2, `time_saved` ≈ 0.24; o 26.10.1 mostra `requests` = `{"alone": None, "pair": None}` e `time_saved` ≈ −0.07.

- [ ] **Step 7: Commit**

```bash
git add bench/flashnext-concurrency-2026-10/scripts/summarize_claude.py bench/flashnext-concurrency-2026-10/tests/test_summarize_claude.py bench/splash-concurrency-2026-10/results/req-*.jsonl bench/*/results/claude-summary.json
git commit -m "results(splash-concurrency): per-request data of the Claude Code pair and claude-summary.json"
```

### Task 3: payload por cenário, faixas e status do Terminal-Bench

**Files:**
- Modify: `bench/flashnext-concurrency-2026-10/scripts/render_report.py` (`collect()`, constantes; remover `_claude_code`)
- Create: `bench/stack-updates-2026-10/results/tbench-status.json` (pedido à sessão de stack; se não existir, nada quebra)
- Test: `bench/flashnext-concurrency-2026-10/tests/test_render_report.py` (novos testes; ajustar `test_collect_claude_code_means` para o `claude-summary.json`)

**Interfaces:**
- Produces, em `render_report.py`:
  - `BANDS = {"ttft": (2.0, 5.0), "first_prompt": (30.0, 60.0), "side": (5.0, 60.0)}` (menor é melhor) e `BANDS_HIGH = {"tps": (60.0, 30.0)}` (maior é melhor); `band(metric: str, value: Optional[float]) -> Optional[str]` → `"good" | "ok" | "poor" | None`.
  - `SERVERS = [{"key": "splash", "label": "Splash 1.5.0", "weights": "ukisai Swift 1.5 Qwen3.8 Flash-Next GGUF IQ4_XS + DFlash2 draft"}, {"key": "mlx", "label": "mlx-serve 26.10.3", "weights": "Dankpaws Swift 1.5 Qwen3.8 Flash-Next MLX 4.7 bpw"}]`, `LEGACY = {"key": "legacy", "label": "mlx-serve 26.10.1", ...}`, `RECOMMENDED = "splash"`.
  - `read_tbench_status(path: Path) -> Optional[dict]`: lê `{"server","weights","done","total","score","updated"}`; `None` se o arquivo não existe ou não parseia.
  - `collect_scenarios(data: dict, claude: dict[str, Optional[dict]], tbench: Optional[dict]) -> dict` — função pura sobre o `data` já coletado (`configs`, `splash`) e os `claude-summary.json` por chave de servidor (`{"splash": ..., "mlx": None, "legacy": ...}`). Devolve:
    ```
    {"one_session": {key: {"warm_ttft_s", "warm_ttft_source": "claude"|"synthetic"|None, "tps_lo", "tps_hi",
                           "first_prompt_s", "cold_128k_s", "tasks": {"small": {"a": s, "b": s}, "realistic": {...}}, "tbench": {...}|None}},
     "two_sessions": {key: {"ttft_alone_p50", "ttft_pair_p50", "ttft_alone_p90", "ttft_pair_p90",
                            "tps_alone_p50", "tps_pair_p50", "tps_pair_min", "tasks": {profile: {task: {"alone_s", "pair_s"}}},
                            "time_saved", "side_p95_s", "max_concurrent", "new_tokens_p50"}},
     "worst_case": {key: {"turn_alone_s", "turn_pair_s", "side_p95_s", "side_over_60", "gain", "best_setting": {"label", "turn_s", "note"}|None}},
     "by_n": {key: {1: {"turn_s", "side_p95_s", "legacy": bool}, 2: ..., 3: ..., 4: ...}},
     "long_256k": {key: {"turn_s", "note"}},
     "coverage": [{"scenario": str, "cells": {key: "measured"|"running"|"missing"}}],
     "verdict": {"one": {"word", "ttft_s", "first_prompt_s"}, "two": {"word", "ttft_pair_p50", "time_saved"}, "many": {"word", "slow_lo", "slow_hi"}}}
    ```
    Fontes por célula seguem a tabela do spec: `splash` lê `k2c*`/`w1zc*` do bloco `splash` e `claude["splash"]`; `mlx` lê `w1zc1`/`w1zc2a` e `claude["mlx"]`; `by_n[mlx][3,4]` e `long_256k[mlx]` vêm do `legacy` com `"legacy": True`. `warm_ttft_source` é `"claude"` quando vem do `claude-summary`, senão `"synthetic"` (`warm_ttft_tool_s` do solo). `verdict.one.word` = `"Yes"` se `band("ttft", ttft) == "good"` e `band("first_prompt", fp) != "poor"`, `"Yes, with waits"` se nenhum é `poor`, senão `"No"`; `verdict.two.word` = `"Yes"` se `band("ttft", pair_p50) == "good"` e `time_saved >= 0`, `"Yes, at a cost"` se `band != "poor"`, senão `"No"`; `verdict.many.word` = `"No"` quando o pior `turn_s` de N = 3 ou 4 é ≥ 2× o de N = 1, senão `"Maybe"`. Tudo calculado para o servidor `RECOMMENDED`.
  - `collect()` ganha os parâmetros `claude_dirs: dict[str, Path]` e `tbench_status: Path` e inclui `"servers"`, `"recommended"`, `"scenarios"` e `"tbench"` no dict devolvido; `main()` passa os defaults (`bench/splash-concurrency-2026-10/results`, `bench/claude-code-concurrency-2026-11/results` para `mlx` e `splash` quando existirem, `bench/flashnext-concurrency-2026-10/results` para `legacy`).

- [ ] **Step 1: Testes que falham**

```python
@pytest.mark.parametrize("metric,value,expected", [("ttft", 2.0, "good"), ("ttft", 2.01, "ok"), ("ttft", 5.0, "ok"),
    ("ttft", 5.01, "poor"), ("tps", 60.0, "good"), ("tps", 59.9, "ok"), ("tps", 29.9, "poor"),
    ("first_prompt", 30.0, "good"), ("side", 60.0, "ok"), ("side", 61.0, "poor"), ("ttft", None, None)])
def test_band_boundaries(metric, value, expected): assert R.band(metric, value) == expected

def test_read_tbench_status_missing_and_bad(tmp_path):
    assert R.read_tbench_status(tmp_path / "none.json") is None
    (tmp_path / "bad.json").write_text("{"); assert R.read_tbench_status(tmp_path / "bad.json") is None

def test_collect_scenarios_real_splash_and_legacy():
    data = R.collect(REAL_RESULTS, SPLASH_RESULTS, claude_dirs={...}, tbench_status=Path("/none"))
    sc = data["scenarios"]
    assert sc["two_sessions"]["splash"]["ttft_pair_p50"] == pytest.approx(1.8, abs=0.1)
    assert sc["two_sessions"]["splash"]["max_concurrent"] == 2
    assert sc["one_session"]["splash"]["warm_ttft_source"] == "claude"
    assert sc["one_session"]["mlx"]["warm_ttft_source"] == "synthetic"
    assert sc["by_n"]["mlx"][4]["legacy"] is True and sc["by_n"]["splash"][4]["legacy"] is False
    assert sc["two_sessions"]["mlx"]["ttft_pair_p50"] is None
    assert sc["verdict"]["one"]["word"] == "Yes" and sc["verdict"]["two"]["word"].startswith("Yes")
    assert sc["two_sessions"]["splash"]["time_saved"] == pytest.approx(0.24, abs=0.01)

def test_collect_scenarios_without_splash_is_all_missing(tmp_path):
    sc = R.collect(REAL_RESULTS, None, claude_dirs={"legacy": REAL_RESULTS}, tbench_status=Path("/none"))["scenarios"]
    assert all(row["cells"]["splash"] == "missing" for row in sc["coverage"])
    assert sc["verdict"]["one"]["word"] is None

def test_collect_scenarios_with_campaign_b_fixture(tmp_path):
    # Um claude-summary.json de mentira para "mlx" (perfil small e realistic, requests alone e pair) preenche
    # two_sessions["mlx"], one_session["mlx"]["warm_ttft_source"] == "claude" e a cobertura vira "measured".
    (tmp_path / "claude-summary.json").write_text(json.dumps(FAKE_MLX_SUMMARY))
    sc = R.collect(REAL_RESULTS, SPLASH_RESULTS, claude_dirs={"splash": SPLASH_RESULTS, "mlx": tmp_path}, tbench_status=Path("/none"))["scenarios"]
    assert sc["two_sessions"]["mlx"]["ttft_pair_p50"] == FAKE_MLX_SUMMARY["requests"]["pair"]["warm"]["ttft_p50"]
    assert "realistic" in sc["one_session"]["mlx"]["tasks"]
    assert next(r for r in sc["coverage"] if r["scenario"] == "Two Claude Code sessions")["cells"]["mlx"] == "measured"

def test_coverage_marks_running_tbench(tmp_path):
    (tmp_path / "tb.json").write_text(json.dumps({"server": "mlx-serve 26.10.3", "done": 51, "total": 89}))
    sc = R.collect(REAL_RESULTS, SPLASH_RESULTS, claude_dirs={}, tbench_status=tmp_path / "tb.json")["scenarios"]
    row = next(r for r in sc["coverage"] if r["scenario"].startswith("Agent quality"))
    assert row["cells"] == {"splash": "missing", "mlx": "running", "legacy": "missing"}
```

- [ ] **Step 2: Rodar e confirmar a falha.** Expected: `AttributeError: band` e `TypeError` no `collect`.

- [ ] **Step 3: Implementar** `band`, `SERVERS`, `read_tbench_status`, `collect_scenarios` e os parâmetros novos do `collect()`; trocar `_claude_code` por leitura de `claude-summary.json` (`json.load`, `None` se ausente). Manter os campos antigos do payload (`configs`, `by_n`, `splash`, `claude_code` agora vindo do summary) para o apêndice.

- [ ] **Step 4: Rodar a pasta inteira de testes.** Expected: tudo passa (os testes antigos de `_claude_code` ajustados para `claude_code["tasks"]["a"]["alone_mean"]` lidos do summary).

- [ ] **Step 5: Pedir o `tbench-status.json`** à sessão "Atualizações de stack preferidas" (`SendMessage` para `local_c66a0c2c-2e01-4be6-9205-af8c5824a877`): caminho `bench/stack-updates-2026-10/results/tbench-status.json`, schema `{"server","weights","done","total","score","updated"}`, atualizado quando o TB do `w1z` terminar e quando o do `k3f` rodar. Não esperar a resposta.

- [ ] **Step 6: Commit**

```bash
git add bench/flashnext-concurrency-2026-10/scripts/render_report.py bench/flashnext-concurrency-2026-10/tests/test_render_report.py
git commit -m "report(flashnext-concurrency): scenario payload, experience bands and Terminal-Bench status"
```

### Task 4: `report_charts.py` — builders SVG das formas novas

**Files:**
- Create: `bench/flashnext-concurrency-2026-10/scripts/report_charts.py`
- Test: `bench/flashnext-concurrency-2026-10/tests/test_report_charts.py`

**Interfaces:**
- Produces (todas puras, devolvem `str` SVG com `viewBox`, `role="img"`, `aria-label`, texto escapado com `html.escape`, cores só por `var(--s1)`, `var(--s2)`, `var(--good)`, `var(--warn-s)`, `var(--crit)`, `var(--ink)`, `var(--ink-2)`, `var(--grid)`; `None` desenha `<rect fill="url(#hatch)">` e o texto `n/m`):
  - `svg_band_bars(title: str, rows: list[dict], vmax: float, unit: str, metric: Optional[str]) -> str`. `rows = [{"label", "series": "s1"|"s2", "value": float|None, "lo": float|None, "hi": float|None, "note": str}]`; `metric` escolhe as faixas de fundo de `BANDS`/`BANDS_HIGH` (nenhuma quando `None`; `tps` inverte a ordem das cores). Barra de intervalo quando `lo`/`hi` existem.
  - `svg_dumbbell(title: str, rows: list[dict], vmax: float, unit: str, metric: Optional[str], series: str) -> str`. `rows = [{"label", "alone": float|None, "pair": float|None}]`; dois círculos (r = 5, `fill` claro e cheio da série) ligados por linha de 2 px; `pair < alone` desenha a linha de `min` a `max`, rótulos nas pontas externas.
  - `svg_diverging(title: str, rows: list[dict], vmax_pct: float) -> str`. `rows = [{"label", "series", "pct": float|None}]`; eixo zero central; `pct` positivo à direita.
  - `svg_lines(title: str, series: list[dict], xs: list[int], ymax: float, unit: str) -> str`. `series = [{"key": "s1"|"s2", "label", "points": {x: {"y": float|None, "legacy": bool}}}]`; círculos cheios, ou vazios (`fill` da superfície, `stroke` da série) quando `legacy`; rótulo direto no último ponto.
  - `svg_timeline(server_labels: tuple[str, str]) -> str`: o esquema fixo da seção 3 (A, B, chamada curta nos dois servidores), sem dados.
  - `table_view(head: list[str], rows: list[list[str]]) -> str`: `<details class="tbl"><summary>Table view</summary><table>…</table></details>`.
  - Cada marca com valor tem `<title>label: value unit</title>` (tooltip nativo).

- [ ] **Step 1: Testes que falham** (reusar `_opening_tag` e o contrato de marcadores de `test_render_report.py`)

```python
def test_band_bars_rect_per_value_and_hatch_for_none():
    svg = C.svg_band_bars("t", [{"label": "Splash", "series": "s1", "value": 0.8}, {"label": "mlx", "series": "s2", "value": None}], 6, "s", "ttft")
    assert svg.count('fill="var(--s1)"') == 1 and 'url(#hatch)' in svg and "n/m" in svg
    assert svg.count("<title>") == 1 and 'var(--good)' in svg and 'var(--crit)' in svg

def test_band_bars_without_metric_has_no_band_fills(): ...
def test_band_bars_range_bar_uses_lo_hi(): ...  # x do rect = scale(lo), width = scale(hi) - scale(lo)
def test_dumbbell_pair_faster_than_alone_has_positive_width():
    svg = C.svg_dumbbell("t", [{"label": "x", "alone": 3.0, "pair": 1.0}], 5, "s", "ttft", "s1")
    x1, x2 = _line_x(svg); assert x2 > x1
def test_dumbbell_none_side_draws_one_circle_and_nm(): ...
def test_diverging_negative_left_of_axis_and_none_hatched(): ...
def test_lines_legacy_points_are_hollow(): ...  # circle com fill="var(--surface)" e stroke="var(--s2)"
def test_lines_missing_point_breaks_polyline(): ...  # y None: dois <polyline> em vez de um
def test_timeline_names_both_servers(): ...
def test_table_view_escapes(): ...
def test_svg_contract_all_builders():  # viewBox, role="img", aria-label, nenhum "#" de cor literal
```

- [ ] **Step 2: Rodar e confirmar a falha.** Expected: `ModuleNotFoundError: report_charts`.
- [ ] **Step 3: Implementar `report_charts.py`.** Reusar `_scale`, `_text`, `_svg` de `render_report.py` movendo-os para `report_charts.py` e importando de volta (sem duplicar).
- [ ] **Step 4: Rodar a pasta de testes.** Expected: tudo passa.
- [ ] **Step 5: Commit** — `report(flashnext-concurrency): SVG builders for band bars, dumbbells, diverging bars and lines`.

### Task 5: `report_sections.py`, `render()` novo e apêndice

**Files:**
- Create: `bench/flashnext-concurrency-2026-10/scripts/report_sections.py`
- Modify: `bench/flashnext-concurrency-2026-10/scripts/render_report.py` (`render()`, `CSS`: tokens `--good`, `--warn-s`, `--crit`, `--hatch`, classes `.tiles`, `.tile`, `.bands`, `.tbl`, `.cov`; `TITLE`, `H1`, `desc`; `<defs>` do padrão `hatch` logo após `<body>`)
- Modify: `bench/flashnext-concurrency-2026-10/tests/test_render_report.py` (seções novas; remover os testes das seções antigas que saem do corpo)

**Interfaces:**
- Consumes: `data["scenarios"]`, `data["servers"]`, `report_charts.*`.
- Produces, em `report_sections.py`, cada uma `(data: dict) -> str` devolvendo um `<section id="…">`: `hero` (`#verdict`), `one_session` (`#one`), `two_sessions` (`#two`), `worst_case` (`#worst`), `many_sessions` (`#many`), `long_context` (`#long`), `recommendation` (`#recommend`), `coverage` (`#coverage`), `appendix` (`#appendix`, um `<details>` com `_how`, `_glossary`, as seções antigas do 26.10.1 e a tabela completa do Splash, `_reproduce`). Textos fixos em inglês, números só do payload via `_num`/`_sec`/`_x`.
- `render(data, generated)` compõe: header → `hero` → `one_session` → `two_sessions` → `worst_case` → `many_sessions` → `long_context` → `recommendation` → `coverage` → `appendix` → footer. `TITLE = "Can one Mac Studio serve Claude Code?"`, `H1 = "Can one Mac Studio serve Claude Code? And two sessions at once?"`, `desc` = uma frase com os três vereditos lidos do payload.
- Tile de veredito: palavra e número do `RECOMMENDED`; segunda linha `<small>` com o outro servidor (`n/m` hachurado via classe `.nm` quando ausente). A frase de subagentes só aparece quando `two_sessions[key]["max_concurrent"]` existe para um braço com subagentes (campanha B); até lá o tile "Three or more" não a cita.

- [ ] **Step 1: Testes que falham**

```python
def test_render_sections_in_order(real_html):
    ids = re.findall(r'<section id="([a-z]+)"', real_html)
    assert ids == ["verdict", "one", "two", "worst", "many", "long", "recommend", "coverage", "appendix"]

def test_hero_words_and_numbers_from_payload(real_html):
    sc = _payload(real_html)["scenarios"]
    assert sc["verdict"]["one"]["word"] in real_html and f'{sc["two_sessions"]["splash"]["ttft_pair_p50"]:.1f} s' in real_html

def test_every_chart_has_legend_title_and_table_view(real_html):
    body = _public_body(real_html)
    n_svg = body.count('role="img"'); assert n_svg >= 10
    assert body.count('class="tbl"') >= n_svg - 1  # o timeline não tem tabela
    assert body.count("<title>") >= 20

def test_mlx_pair_cells_are_hatched_until_campaign_b(real_html):
    two = re.search(r'<section id="two".*?</section>', real_html, re.S).group(0)
    assert 'url(#hatch)' in two and "n/m" in two

def test_render_without_splash_or_claude(tmp_path):
    page = R.render(R.collect(REAL_RESULTS, None, claude_dirs={}, tbench_status=tmp_path / "none"))
    assert '<section id="coverage"' in page and page.count("○") >= 8 and "Traceback" not in page

def test_render_no_insider_terms(real_html):  # manter; acrescentar "k2c", "w1zc", "kcc", "T_turno", "needle" à lista proibida no corpo
def test_render_no_placeholders(real_html):   # manter
def test_render_payload_is_collect_output(real_html):  # manter
def test_legacy_only_in_appendix(real_html):
    body = _public_body(real_html).split('<section id="appendix"')[0]
    assert "26.10.1" not in body.replace("(26.10.1)", "")  # no corpo, só como marcador de ponto vazio
```

- [ ] **Step 2: Rodar e confirmar a falha.** Expected: `test_render_sections_in_order` falha com a lista antiga de ids.
- [ ] **Step 3: Implementar `report_sections.py` e o `render()` novo.** Mover `_hero`, `_splash`, `_sessions`, `_throughput`, `_side_requests`, `_max_concurrent`, `_long_context`, `_claude_code_section`, `_pds`, `_learned`, `_upstream`, `_refusals`, `_not_measured` para dentro de `appendix()` (chamadas, não cópias), cada uma num `<details>` com o título antigo. `_how` e `_glossary` entram no apêndice com os seis termos. `CSS`: tokens novos nos dois temas (`--good:#0ca30c`, `--warn-s:#fab219`, `--crit:#d03b3b`; no escuro os mesmos), `.tile .big{font-size:30px}`, `.bands span{padding:2px 8px;border-radius:4px}`, `.tbl summary{color:var(--ink-2)}`; `<svg width="0" height="0"><defs><pattern id="hatch" …></defs></svg>` após `<div class="wrap">`.
- [ ] **Step 4: Regenerar e rodar os testes**

```bash
python3 bench/flashnext-concurrency-2026-10/scripts/render_report.py
uv run --no-project --with pytest python -m pytest bench/flashnext-concurrency-2026-10/tests -q
```
Expected: `reports/qwen38-flashnext-concurrency.html` e `results/report-data.json` regravados; todos os testes passam.
- [ ] **Step 5: Commit** — `report(flashnext-concurrency): page by use scenario with experience bands`.

### Task 6: conferência visual

**Files:** nenhum novo; correções em `report_sections.py`, `report_charts.py` ou `CSS` se a conferência achar problema.

- [ ] **Step 1: Abrir a página** no browser pane (`preview_start` com `file://` do HTML gerado, ou `python3 -m http.server` na pasta `reports/`). Conferir no tema claro e escuro e a 375 px: tiles em coluna; nenhum rótulo cortado; hachura visível nos dois temas; pontos vazios do 26.10.1 distinguíveis; `<details>` abrem.
- [ ] **Step 2: Screenshot** de cada seção nos dois temas, guardados em `/private/tmp/claude-501/.../scratchpad/report-check/`. Corrigir e regenerar até limpar.
- [ ] **Step 3: Checar o anti-patterns da skill `dataviz`** (`references/anti-patterns.md`): eixo duplo (não há), cor no texto (texto só em tokens de tinta), legenda ausente, escala truncada sem aviso.
- [ ] **Step 4: Commit** das correções — `report(flashnext-concurrency): visual fixes after browser check`.

### Task 7: docs (Entrega C)

**Files:**
- Modify: `docs/models/qwen3.8-flash-next.md` (seção "Concurrent sessions", linhas ~89–118)
- Modify: `reports/index.html` (card do report), `reports/README.md` (linha do report)
- Modify: `bench/splash-concurrency-2026-10/results/summary.md`, `bench/flashnext-concurrency-2026-10/results/summary.md` (nota "report reorganizado")

- [ ] **Step 1: Doc do modelo.** Trocar a seção por: um parágrafo de resumo (as três respostas), a tabela por cenário com as colunas Splash 1.5.0 e mlx-serve 26.10.3 em segundos (linhas: resposta começa sozinho e em par; geração; primeiro prompt; chamada curta p95; tarefa pequena sozinha e em par; tempo poupado pelo par; pior turno N = 3, 4; duas sessões de 256K; Terminal-Bench), `n/m` onde falta, e o link do report. Os parágrafos do 26.10.1 saem; o summary de 18/10 fica linkado como fonte histórica. Os números copiam `results/report-data.json` (`scenarios`).
- [ ] **Step 2: Card e README.** Título "Can one Mac Studio serve Claude Code?", descrição: uma sessão sim, duas com custo (os números), três não; data de hoje. `reports/README.md`: a linha correspondente.
- [ ] **Step 3: Notas nos summaries.** Uma linha no topo de cada `summary.md`: "Report público reorganizado por cenário de uso em 2026-11; os gates desta campanha estão no apêndice da página."
- [ ] **Step 4: Teste de consistência**: em `test_render_report.py`, `test_model_doc_numbers_match_payload` lê o doc do modelo e confere três números (TTFT par Splash, tempo poupado do par, pior turno N = 4 Splash) contra `report-data.json`.
- [ ] **Step 5: Rodar os testes e commit** — `docs(flash-next): concurrency section by use scenario, report card`.

### Task 8: PR

- [ ] **Step 1:** `git push -u origin <branch>`; `gh pr create` com título "report(flashnext-concurrency): page by use scenario, experience bands, Claude Code per-request data" e corpo: as três respostas, o que mudou na página, o que a campanha B vai preencher, link do spec e do mockup. Terminar com `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 2:** `mcp__ccd_pr__get_status` / `bind_pr`; ler o CI; oferecer Auto-fix. Merge só com o "sim" do usuário.

## Depois deste plano

- Runbook da campanha B: `bench/claude-code-concurrency-2026-11/plan.md` (tarefas c e d, `request_log.py`, flags `--task c|d`, `--subagents`, `--proxy`, braços `rc*`/`rm*`, fila no rig). Escrever com superpowers:writing-plans quando este plano estiver mergeado e o rig tiver janela (depois do `k3f` e do `t5r`).
