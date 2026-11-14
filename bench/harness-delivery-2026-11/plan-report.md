# Report público "entrega por harness" — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status (2026-11-14):** plano escrito; espera a revisão do usuário. Nada foi implementado.

**Goal:** Publicar uma página HTML em inglês, para leitores de fora do repositório (Reddit), que mostra com gráficos o que as campanhas `harness-delivery-2026-11` e `swift-uncensored-2026-11` mediram e concluíram.

**Architecture:** Um script `render_report.py` lê os resultados rastreados das duas campanhas, monta um dicionário de dados (`collect`) e escreve uma página estática (`render`). Os gráficos são SVG inline gerados em Python por um módulo pequeno (`svg_charts.py`). A página não carrega JavaScript de CDN e abre por `file://`.

**Tech Stack:** Python 3.9+ (só biblioteca padrão), HTML e CSS inline, SVG inline, pytest. Chrome headless para a imagem do card.

**Spec:** não existe. O usuário pediu o plano direto, sem a etapa de brainstorming. As decisões de conteúdo e de forma abaixo são minhas e estão marcadas em "Decisões minhas". O usuário revisa essas decisões neste plano.

## Decisões minhas (revisar antes de executar)

1. **Idioma:** inglês. O `AGENTS.md` manda os reports publicados ficarem em inglês, e o destino é o Reddit.
2. **Escopo:** as duas campanhas em uma página. A pergunta do leitor é uma só: "qual harness uso com um modelo local, e um peso uncensored custa alguma coisa?".
3. **Arquivo:** `reports/qwen38-flashnext-harness-delivery.html`, com card na seção `#agents` do `reports/index.html`.
4. **Gráficos:** SVG inline gerado em Python, sem Chart.js. Motivo: a página fica em 1 arquivo, abre sem rede e o texto dos gráficos entra nos testes.
5. **Tom:** conclusões com a margem de erro ao lado. A página diz "tie" onde 2 repetições não separam.
6. **Seção de erros de medição:** a página conta os 3 defeitos que a campanha achou no próprio benchmark. É o aprendizado mais útil para quem monta um benchmark de agentes.
7. **Sonda de recusa:** a página mostra só contagens. Nenhum prompt e nenhuma resposta aparecem.
8. **Nomes públicos dos pesos:** `k2` vira "Swift 1.5 IQ4_XS (ukisai)"; `z4` vira "Swift 1.5 Heretic v2 IQ4_XS (jackjusko, indexer recast to BF16)". Os rótulos `k2` e `z4` ficam só na seção de método.

## Global Constraints

- Texto da página em inglês. Sem emoji. Sem adjetivo de marketing.
- A página é 1 arquivo HTML sem `<script src>` e sem `<link rel="stylesheet">` externo.
- Nenhum texto de sessão, prompt da sonda de recusa ou resposta de modelo entra na página.
- Nenhum dado pessoal: sem hostname, sem `vitor@`, sem caminho `/Users/`.
- Todo número da página sai de `collect()`. Nenhum número fica escrito à mão no HTML, salvo as constantes da Task 1 que um teste confere contra o arquivo de origem.
- Fontes de dados, todas rastreadas no git:
  - `bench/harness-delivery-2026-11/results/sessions/*.json` (112 registros; `smoke-*` fica fora)
  - `bench/swift-uncensored-2026-11/results/refusal-<braço>-<conjunto>.jsonl` (braços `k2h`, `z2h`, `z3h`, `z4h`; conjuntos `advbench`, `jbb`)
  - `bench/swift-uncensored-2026-11/results/etapa2-um-stream.md` (tabela "Medidas" e tabela do veredito)
- A regra da T5 é a leitura do prompt (commit `031f63c`): 105 de 112 sessões prontas.
- Cores: 1 cor por harness e 1 cor por peso, fixas em toda a página, com contraste AA nos temas claro e escuro (`prefers-color-scheme`).
- Layout legível a 380 px de largura, sem rolagem horizontal da página. Tabelas largas rolam dentro do próprio bloco.
- Todo gráfico tem `<title>` e `<desc>` no SVG e uma tabela com os mesmos números logo abaixo, dentro de `<details>`.
- Commits terminam com `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. Sem push, PR ou post no Reddit sem pedido do usuário.

## Review Focus

1. **Um registro de sessão novo ou ausente.** A página deve falhar na geração com uma mensagem clara quando a matriz não tem as 112 combinações, e não desenhar uma célula vazia como zero. Teste na Task 1.
2. **Empate mostrado como vitória.** Com diferença de 1 ou 2 sessões, o texto não pode dizer que um harness "wins". Teste na Task 3.
3. **Tema escuro.** Um SVG com cor fixa some no fundo escuro. Teste na Task 2: nenhum `fill` ou `stroke` com cor literal fora de `var(--…)`.
4. **Rótulo longo de peso em tela estreita.** O nome público do `z4` tem mais de 50 caracteres. O gráfico usa o nome curto e a legenda traz o nome completo. Teste na Task 2.
5. **Página desatualizada.** O resumo muda e a página não. Teste na Task 4: o arquivo em `reports/` é igual à saída de `render(collect())`.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `bench/harness-delivery-2026-11/scripts/render_report.py` | `collect()`, `render()`, `main()`; texto e estrutura da página |
| `bench/harness-delivery-2026-11/scripts/svg_charts.py` | funções puras que devolvem uma string `<svg>` |
| `bench/harness-delivery-2026-11/tests/test_render_report.py` | testes de `collect`, `render` e do card do índice |
| `bench/harness-delivery-2026-11/tests/test_svg_charts.py` | testes dos gráficos |
| `reports/qwen38-flashnext-harness-delivery.html` | página gerada |
| `reports/assets/qwen38-flashnext-harness-delivery-card.html` e `.png` | imagem 1200×630 do link (Open Graph) |
| `reports/index.html` | card novo na seção `#agents` |
| `reports/README.md` | linha nova na tabela de páginas |

## Roteiro da página

A página responde 4 perguntas, nesta ordem. Cada pergunta abre com a resposta em 1 frase e depois mostra o gráfico.

| # | Seção | Mensagem | Elemento visual |
|---|---|---|---|
| 0 | Hero | 105 of 112 sessions done; the 4 harnesses tie; the uncensored pack costs 3 tasks of 56 and refuses nothing | 4 blocos de número grande |
| 1 | What I ran | 1 Mac Studio, 1 model, 4 harnesses, 7 tasks, 2 packs, 2 repetitions, sandbox per session | diagrama da matriz (4 × 7 × 2 × 2) em SVG |
| 2 | Does the harness matter? | Not at this sample size: 25 to 27 of 28 | mapa de calor harness × tarefa (0 a 4 prontas) e gráfico de pontos de tempo por tarefa |
| 3 | Does the uncensored pack code worse? | 51 against 54; the gap is 1 task type | barras pareadas por tarefa, `k2` contra `z4` |
| 4 | How uncensored is it? | 96% refusals become 0% | barras empilhadas (refused / empty / complied) por peso e conjunto |
| 5 | What does it cost in speed? | 2% to 5% slower per agent turn | gráfico de pontos da razão de tempo de turno a 32K, 128K e 256K, com a linha de 1.05 |
| 6 | How sessions fail | All 7 failures say "done" | lista das 7 falhas agrupadas por causa |
| 7 | Three times the benchmark was wrong | sandbox broke the linter (16 of 16 failed); a false cheat flag on 20 records; a rule the prompt never stated flipped the verdict | 3 cartões "what I saw / cause / fix", com o antes e o depois em números |
| 8 | Limits | 2 repetitions; 1 model family; harness versions; T5 rerun after the rest | lista |
| 9 | Method and data | versões, sandbox, links para `plan.md`, `summary.md`, `audit.md` e os JSON | tabela e glossário (`k2`, `z4`, T_turn) |

---

### Task 1: Camada de dados (`collect`)

**Files:**
- Create: `bench/harness-delivery-2026-11/scripts/render_report.py`
- Test: `bench/harness-delivery-2026-11/tests/test_render_report.py`

**Interfaces:**
- Consumes: `summarize.load(out) -> list[dict]`, `summarize.table`, `summarize.reserva`, `summarize.rank` (já existem).
- Produces: `collect(delivery_results: Path = RESULTS, swift_results: Path = SWIFT_RESULTS) -> dict` com as chaves:
  - `sessions`: `{"total": 112, "done": 105}`
  - `harness`: lista de `{"name", "label", "version", "done", "n", "median_s", "by_pack": {"k2": {"done", "n"}, "z4": {...}}}` na ordem de `summarize.rank`
  - `cells`: `{(harness, task): {"k2": done_de_2, "z4": done_de_2}}`
  - `tasks`: lista de `{"id", "label", "hard", "k2_done", "z4_done", "n", "median_s": {"k2", "z4"}}`
  - `times`: `{(harness, task): [wall_s das sessões prontas]}`
  - `reserva`: saída de `summarize.reserva`
  - `failures`: lista de `{"pack", "harness", "task", "rep", "cause"}`; `cause` vem da constante `FAILURE_CAUSES`
  - `refusal`: `{(arm, set): {"refused", "empty", "complied", "n"}}`
  - `speed`: `{arm: {ctx: {"t_turn_s", "ratio", "decode_tps", "wired_gb"}}}` e `speed_verdict: {arm: "pass"|"fail"}`
- Constantes: `HARNESS_LABEL`, `PACK_LABEL` (nome curto e nome completo), `TASK_LABEL` (1 linha em inglês por tarefa), `FAILURE_CAUSES` (as 7 falhas, copiadas do `audit.md`), `SPEED` (copiada da tabela "Medidas" do `etapa2-um-stream.md`).

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_collect_counts_match_the_summary(rr):
    d = rr.collect()
    assert d["sessions"] == {"total": 112, "done": 105}
    assert {h["name"]: h["done"] for h in d["harness"]} == {"pi": 27, "claude": 27, "dsh": 26, "opencode": 25}
    assert (d["reserva"]["done_base"], d["reserva"]["done_cand"], d["reserva"]["pass"]) == (54, 51, True)

def test_collect_has_one_cause_per_failed_session(rr):
    d = rr.collect()
    assert len(d["failures"]) == 7 and all(f["cause"] for f in d["failures"])

def test_collect_refuses_an_incomplete_matrix(rr, tmp_path):
    # copia os registros menos 1; espera ValueError com o nome da sessão que falta
    ...
    with pytest.raises(ValueError, match="k2-pi-a-r1"):
        rr.collect(delivery_results=tmp_path)

def test_refusal_counts_recomputed_from_jsonl(rr):
    r = rr.collect()["refusal"]
    assert r[("k2h", "advbench")] == {"refused": 96, "empty": 1, "complied": 3, "n": 100}
    assert r[("z4h", "jbb")] == {"refused": 0, "empty": 4, "complied": 96, "n": 100}

def test_speed_constants_match_the_stage_report(rr):
    # lê a tabela "Medidas" e a tabela do veredito de etapa2-um-stream.md e compara com rr.SPEED
    d = rr.collect()
    assert d["speed"]["z4h"][131072]["ratio"] == 1.051 and d["speed_verdict"] == {"z4h": "fail", "z2h": "fail", "z3h": "pass"}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest bench/harness-delivery-2026-11/tests/test_render_report.py -q`
Expected: FAIL, `render_report` não existe.

- [ ] **Step 3: Implementar `collect` e as constantes.** O veredito `vazio` do JSONL de recusa é o valor de `verdict` que não é `refused` nem `complied`; conferir os 3 valores reais do campo antes de mapear.
- [ ] **Step 4: Rodar os testes.** Expected: PASS.
- [ ] **Step 5: Commit.**

### Task 2: Gráficos em SVG (`svg_charts.py`)

**Files:**
- Create: `bench/harness-delivery-2026-11/scripts/svg_charts.py`
- Test: `bench/harness-delivery-2026-11/tests/test_svg_charts.py`

**Interfaces:**
- Produces, todas devolvem `str` com 1 elemento `<svg viewBox=… role="img">` que tem `<title>` e `<desc>`:
  - `heatmap(rows: list[str], cols: list[str], values: dict[tuple[str, str], int], vmax: int, title: str, desc: str) -> str` — célula com o número escrito e 5 níveis de cor (`--heat-0` a `--heat-4`)
  - `paired_bars(groups: list[str], series: list[tuple[str, str]], values: dict[tuple[str, str], float], vmax: float, title: str, desc: str) -> str` — `series` é `(rótulo, variável de cor)`
  - `stacked_bars(rows: list[str], parts: list[tuple[str, str]], values: dict[tuple[str, str], int], title: str, desc: str) -> str` — barras horizontais de 100%
  - `dot_plot(rows: list[str], series: list[tuple[str, str]], points: dict[tuple[str, str], list[float]], xmax: float, unit: str, ref: float | None, title: str, desc: str) -> str` — 1 ponto por medida, traço na mediana, linha vertical em `ref`
  - `matrix_diagram(factors: list[tuple[str, list[str]]], title: str, desc: str) -> str` — os 4 fatores da matriz e o produto
- Toda cor é `var(--nome)`. O texto usa `fill="var(--ink)"`.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_every_chart_is_one_svg_with_title_and_desc(charts):
    for svg in charts.values():
        assert svg.count("<svg") == 1 and "<title>" in svg and "<desc>" in svg and 'role="img"' in svg

def test_charts_use_only_theme_colors(charts):
    for svg in charts.values():
        assert not re.search(r'(fill|stroke)="(?!var\(|none|currentColor)', svg)

def test_heatmap_writes_each_value_once(sc):
    svg = sc.heatmap(["pi"], ["a", "b"], {("pi", "a"): 4, ("pi", "b"): 0}, 4, "t", "d")
    assert svg.count(">4<") == 1 and svg.count(">0<") == 1

def test_stacked_bars_sum_to_full_width(sc):
    # as larguras dos 3 retângulos de uma linha somam a largura da área do gráfico, com erro < 0.5
    ...

def test_dot_plot_draws_the_reference_line(sc):
    svg = sc.dot_plot(["128K"], [("z4", "--pack-b")], {("128K", "z4"): [1.051]}, 1.1, "×", 1.05, "t", "d")
    assert 'class="ref"' in svg

def test_long_labels_are_cut_with_an_ellipsis(sc):
    svg = sc.paired_bars(["x" * 60], [("s", "--pack-a")], {("x" * 60, "s"): 1}, 1, "t", "d")
    assert "x" * 60 not in svg and "…" in svg
```

O fixture `charts` chama as 5 funções com dados pequenos.

- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL, `svg_charts` não existe.
- [ ] **Step 3: Implementar as 5 funções.** Largura base do `viewBox`: 720. Rótulo de eixo com mais de 28 caracteres é cortado com `…`.
- [ ] **Step 4: Rodar os testes.** Expected: PASS.
- [ ] **Step 5: Commit.**

### Task 3: Página (`render`)

**Files:**
- Modify: `bench/harness-delivery-2026-11/scripts/render_report.py`
- Test: `bench/harness-delivery-2026-11/tests/test_render_report.py`

**Interfaces:**
- Consumes: `collect()` da Task 1; as 5 funções da Task 2.
- Produces: `render(data: dict, generated: str | None = None) -> str` (documento HTML completo) e `main(argv) -> int` com `--out` (padrão `reports/qwen38-flashnext-harness-delivery.html`).
- Uma função por seção do roteiro: `_hero`, `_setup`, `_q_harness`, `_q_pack`, `_q_refusal`, `_q_speed`, `_failures`, `_benchmark_bugs`, `_limits`, `_method`. Cada uma recebe `data` e devolve `str`.
- `<head>`: `<title>`, `description`, `og:title`, `og:description`, `og:type`, `og:url`, `og:image` (1200×630), `twitter:card`. URL base: `https://snagnever.github.io/macstudio-local-llm/`.
- CSS inline com variáveis de cor em `:root` e de novo em `@media (prefers-color-scheme: dark)`.

Texto fixo que os testes conferem:
- Título: `Four coding harnesses, one local model`
- Subtítulo: `Claude Code, OpenCode, pi and dsh on a Mac Studio M4 Max, with a standard and an uncensored Qwen3.8 Flash-Next pack`
- Respostas curtas das perguntas 2 a 5: `No measurable difference`, `Three tasks fewer out of 56`, `Refusals drop from 96% to 0%`, `2% to 5% slower per agent turn`

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_page_answers_the_four_questions(page):
    t = text_of(page)
    for s in ("No measurable difference", "Three tasks fewer out of 56", "Refusals drop from 96% to 0%",
              "2% to 5% slower per agent turn"):
        assert s in t

def test_page_never_names_a_winner_inside_the_noise(page):
    t = text_of(page).lower()
    assert "wins" not in t and "best harness" not in t and "two repetitions" in t

def test_page_numbers_come_from_the_data(rr, page):
    d = rr.collect()
    t = text_of(page)
    assert f"{d['sessions']['done']} of {d['sessions']['total']}" in t
    assert all(f"{h['done']} of {h['n']}" in t for h in d["harness"])

def test_page_is_self_contained(page):
    assert "<script src" not in page and 'rel="stylesheet"' not in page and "http://" not in page

def test_page_has_no_private_data_and_no_probe_text(page):
    assert not re.search(r"/Users/|vitor@|MBPro", page)
    # nenhum id de prompt da sonda aparece
    assert not re.search(r"\b(advbench|jbb)-\d+", page)

def test_every_chart_has_a_data_table(page):
    assert page.count("<svg") >= 6 and page.count("<details") >= page.count('<figure class="chart"')

def test_page_tells_the_three_benchmark_defects(page):
    t = text_of(page)
    assert "16 of 16" in t and "E902" in t and "Makefile" in t and "import" in t

def test_page_uses_public_pack_names_outside_the_method_section(page):
    body = page.split('id="method"')[0]
    assert "z4" not in text_of(body) and "Heretic v2" in body
```

- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL, `render` não existe.
- [ ] **Step 3: Implementar `render`, as 10 funções de seção e `main`.** Seguir a forma de `bench/splash161-2026-11/scripts/render_page.py`: resposta em destaque, depois o gráfico, depois 2 a 4 frases.
- [ ] **Step 4: Rodar os testes.** Expected: PASS.
- [ ] **Step 5: Gerar a página e conferir no navegador.**

Run: `python3 bench/harness-delivery-2026-11/scripts/render_report.py`
Conferir com o navegador embutido, em `file://`: largura 1280 e 375, temas claro e escuro. Expected: nenhum gráfico cortado, nenhuma rolagem horizontal da página, nenhum erro no console.

- [ ] **Step 6: Commit.**

### Task 4: Publicação no site

**Files:**
- Create: `reports/qwen38-flashnext-harness-delivery.html`, `reports/assets/qwen38-flashnext-harness-delivery-card.html`, `reports/assets/qwen38-flashnext-harness-delivery-card.png`
- Modify: `reports/index.html` (seção `#agents`), `reports/README.md` (tabela de páginas)
- Test: `bench/harness-delivery-2026-11/tests/test_render_report.py`

**Interfaces:**
- Consumes: `render`, `collect`, `main` da Task 3.
- Produces: `card_html(data: dict) -> str` em `render_report.py` (página 1200×630 com o título e os 4 números do hero) e a opção `--card` de `main`, que grava o HTML do card.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_published_page_is_the_current_render(rr):
    published = (REPO / "reports/qwen38-flashnext-harness-delivery.html").read_text()
    strip = lambda s: re.sub(r'<span id="generated">[^<]*</span>', "", s)
    assert strip(published) == strip(rr.render(rr.collect()))

def test_index_has_a_card_for_the_page():
    index = (REPO / "reports/index.html").read_text()
    agents = index.split('id="agents"')[1].split('<section class="block"')[0]
    assert 'href="qwen38-flashnext-harness-delivery.html"' in agents

def test_readme_lists_the_page():
    assert "qwen38-flashnext-harness-delivery.html" in (REPO / "reports/README.md").read_text()

def test_card_image_exists_and_matches_the_og_tag(page):
    assert 'assets/qwen38-flashnext-harness-delivery-card.png' in page
    assert (REPO / "reports/assets/qwen38-flashnext-harness-delivery-card.png").stat().st_size > 10_000
```

- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL, os arquivos não existem.
- [ ] **Step 3: Gerar a página e o HTML do card.** Run: `python3 bench/harness-delivery-2026-11/scripts/render_report.py --card`
- [ ] **Step 4: Gerar o PNG do card** com Chrome headless, na forma de `render_m4max_guide.py:2102` (`--screenshot`, janela 1200×630).
- [ ] **Step 5: Adicionar o card ao `reports/index.html`** (`c-title`, `c-desc` em inglês com a conclusão em `<b>`, `c-meta` com `2026-11-14` e o nome do arquivo) e a linha ao `reports/README.md`.
- [ ] **Step 6: Rodar a suíte inteira da campanha.** Run: `uv run --no-project --with pytest python -m pytest bench/harness-delivery-2026-11/tests -q`. Expected: PASS.
- [ ] **Step 7: Commit.** Sem push nem PR sem pedido do usuário.

### Task 5: Texto para o Reddit (rascunho)

**Files:**
- Create: `bench/harness-delivery-2026-11/results/reddit-post.md`

- [ ] **Step 1: Escrever o rascunho em inglês:** título, 5 a 7 frases com as 4 respostas e os 3 defeitos do benchmark, a lista de limites e o link da página. Os números saem de `collect()`.
- [ ] **Step 2: Conferir** que todo número do rascunho aparece na página.
- [ ] **Step 3: Commit.** O post no Reddit é do usuário; o plano não posta nada.

## Fora do escopo

- Rodar mais repetições ou outros modelos.
- Gráficos interativos (filtro, hover). A página é estática.
- Tradução para português.
