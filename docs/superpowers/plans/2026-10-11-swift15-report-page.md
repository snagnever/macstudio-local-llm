# Página do Swift 1.5 × n2 — plano

> Execução inline (executing-plans), autorizada pelo usuário em 2026-10-11 ("siga de forma autônoma").

**Goal:** gerar `reports/qwen38-flashnext-swift15.html` a partir dos resultados da campanha Swift e publicar o card.

**Spec:** [2026-10-11-swift15-report-page-design.md](../specs/2026-10-11-swift15-report-page-design.md)

**Tech:** Python 3.9, biblioteca padrão; pytest; HTML/CSS/JS inline com SVG.

## Global Constraints

- Texto da página em inglês. Autocontida; só Google Fonts externo.
- Reusar `summarize_ab` para ler e normalizar os registros.
- Testes rodam com `python3 -m pytest bench/swift15-flashnext-2026-10/tests -q`.

## Review Focus

1. Suíte ausente num braço ou perfil: a página mostra `n/d`, não esconde a linha.
2. Turno 2 do tool-calling: só casos multi-turno entram na mediana.
3. Velocidade: só grupos canônicos; o m1 a 32K é o m1p, a 128K é o m1x.
4. HTML: nenhum placeholder `__X__` sobra; o payload não fecha a tag `<script>` (`</` escapado).
5. Números da página batem com `results/summary.md`.

## Task 1: `collect()`

**Files:** create `scripts/render_page.py`, `tests/test_render_page.py`.

**Produces:** `collect(results_dir: Path, reports_json: Path) -> dict` com as chaves `arms`, `profiles`,
`quality[profile][arm][suite]` (`n`, `passed`, `missing`), `humaneval_regrade`, `time[profile][suite]`
(`arms[arm]` = stats + `points` [{`id`, `s`, `ok`, `trunc`}], `ratio`), `tool_latency[profile][suite][arm]`
(`turn1_median_s`, `turn2_median_s`, `turn2_n`, `passed`, `n`), `speed[ctx]` (lista de linhas), `legacy`,
`gates`, `rig`.

Testes (RED primeiro): acertos e stats por fixture; suíte ausente vira `missing`; turno 2 só multi-turno;
velocidade escolhe canônico e expõe `arm` real; fumaça sobre dados reais bate com o `summary.md`.

## Task 2: `render()` e `main()`

**Produces:** `render(data: dict) -> str`; `main(argv)` grava o JSON e o HTML.

Testes (RED primeiro): seções presentes por id; seletor t1/t0; payload JSON parseável; sem `__[A-Z_]+__`;
`</` escapado; `n/d` para suíte ausente; `main` grava os dois arquivos em `tmp_path`.

## Task 3: publicar

Gerar a página com os dados reais; conferir no navegador (claro, escuro, 390 px); card no `reports/index.html`;
linha no `reports/README.md`. Commit.

## Final

Revisão do branch por um revisor novo; Important → fix com teste; Minor → lista.
