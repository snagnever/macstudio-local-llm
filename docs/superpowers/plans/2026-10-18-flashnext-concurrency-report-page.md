# Página pública da campanha de concorrência — plano

> Execução inline (superpowers:executing-plans). Aguarda a revisão do usuário antes de começar.

**Goal:** gerar `reports/qwen38-flashnext-concurrency.html`, uma página autocontida para leitores de fora do repositório, com os resultados, os aprendizados e as issues upstream da campanha `bench/flashnext-concurrency-2026-10`.

**Arquitetura:** um script Python (`scripts/render_report.py`) lê os JSONL de `results/`, os `cc-*.json` e os `etapa*-verdict.env` com o `summarize_parallel.summarize()` que já existe, monta um dicionário de dados e renderiza o HTML com os números embutidos num payload JSON. Os gráficos são SVG inline gerados pelo script (sem CDN); as ilustrações didáticas são SVG estático escrito à mão dentro do template. O mesmo padrão da página `qwen38-flashnext-swift15.html`.

**Tech:** Python 3.9, biblioteca padrão; pytest; HTML/CSS/JS inline + SVG. Fonte: Google Fonts (único recurso externo), como nas páginas irmãs.

**Spec:** este plano é a especificação. A fonte dos números é `results/summary.md` e os quatro relatórios de etapa; a página não pode divergir deles.

## Global Constraints

- Texto da página em inglês (regra do `AGENTS.md` para `reports/`). O plano e o chat ficam em português.
- Vocabulário público. Cada termo interno ganha o nome público abaixo e o termo interno não aparece no corpo, só na tabela de referência do rodapé:

  | interno | público |
  | --- | --- |
  | braço / arm `w1c2a` etc. | **test configuration**, com um nome legível (ex.: "2 sessions + tool calls, 32K") e o código curto entre parênteses |
  | stream | **session** (one simulated agent session) |
  | aux / gerador de aux | **short side request** (a 1-second permission check, like an agent asking "may I run this?") |
  | `T_turno` | **turn time** (seconds from sending a tool result to receiving the full reply) |
  | razão ÷ w1 | **slowdown** (turn time ÷ the same session alone) |
  | needles | **recall check** (did the model find the planted fact?) |
  | prefill / decode | mantidos, com uma frase de definição na primeira vez e na ilustração |
  | `--max-concurrent`, `--prefix-cache-mem`, `--prefill-decode-share` | nomes das flags mantidos em `code`, com uma frase de efeito |
  | driver diário / daily driver | **the everyday server setup** |
  | rig | **the test machine** (Mac Studio M4 Max, 128 GB) |
  | etapa 1/1b/1c/2 | sem numeração; seções nomeadas pelo assunto |
  | gate / veredito | **pass rule** / **result** |
  | wired peak | **peak memory held by the server** |
  | hot cache / prefix cache | **prompt cache** (the server keeps old prompts in memory to skip re-reading them) |

- Faixas da regra de aprovação, iguais ao runbook: slowdown ≤ 1.5 pass; 1.5–2.0 pass with a warning; > 2.0 fail. O pior stream decide.
- Autocontida: sem Chart.js nem outro CDN. SVG gerado pelo script.
- Tema claro e escuro (`prefers-color-scheme` + `data-theme`), largura mínima 390 px.
- Testes: `python3 -m pytest bench/flashnext-concurrency-2026-10/tests -q`. Toda função nova entra por teste RED → GREEN.
- Nenhum número digitado à mão no HTML: tudo vem do `collect()`. Exceções (texto): as citações das mensagens de recusa do servidor e os links upstream.

## Estrutura da página (ordem de leitura)

1. **Hero.** Título "How many agent sessions fit on one local Flash-Next server?". Três tiles: **2 sessions** (the maximum that passes), **~2× slower each** (each session, when two run together), **0 s saved** (two sessions together finish 7% later than one after the other). Uma frase de contexto: modelo, servidor, máquina, datas.
2. **How the test works** (ilustração didática 1). SVG com duas linhas do tempo: "one session alone" e "two sessions together". Caixas de prefill (longas) e decode (curtas, intercaladas). Uma seta marcando a chegada de um *short side request* que espera o prefill terminar. Legenda com as três palavras: prefill, decode, prompt cache. Ao lado, um parágrafo que explica o que é uma *test configuration*: N sessions × context size × with/without side requests, 3 repetitions each, measured by turn time.
3. **Glossary card** curto (6 termos) logo abaixo da ilustração: session, turn time, slowdown, context size (32K / 128K / 256K tokens), prefill, decode.
4. **Sessions vs slowdown** (gráfico 1). Barras agrupadas: eixo X = 1, 2, 3, 4 sessions; séries = 32K e 128K; valor = pior slowdown. Linhas horizontais em 1.5 e 2.0 com rótulos "pass" / "warning" / "fail". Fonte: `w1c1`, `w1c2a`, `w1c3a`, `w1c4a` (com side requests) e nota de rodapé para `w1c2`/`w1c4` sem side requests.
5. **Why it does not add up** (gráfico 2). Barras: generation speed per session (tokens/s) para 1, 2, 3, 4 sessions a 32K e 128K, mais uma linha pontilhada "total" (N × per-session). Mostra que o total fica em ~80 tok/s qualquer que seja N. Nota: o benchmark independente (drowzeys) mostra o mesmo a partir de 32K.
6. **Short side requests wait for long prefills** (gráfico 3). Dot plot ou barras: p50 e p95 do tempo de resposta das side requests por configuração (2, 3, 4 sessions × 32K / 128K; 256K). Anotação: "a 128K cold prompt takes ~165 s to read; a 256K one ~350 s; a side request that arrives then waits". Inclui `w1c1x2` para mostrar que o efeito existe também com `--max-concurrent 1`.
7. **Does `--max-concurrent` matter?** Card de texto com a tabela 2 colunas: default (1) vs 2 — turn time, slowdown, side-request p95 iguais dentro do ruído. Conclusão: o servidor 26.10.1 já faz batched decode com o default; a flag não é uma fila.
8. **256K: two long sessions** (gráfico 4 + tabela). Barras do pior slowdown das 4 configurações de 256K (`L`, `m4`, `q8`, `m4q8`) com marcador de "refused" e "recall miss". Tabela: prompt cache in RAM, KV precision, peak memory, refused?, recall, result. Resultado: só `m4` (4 GB cache) passa, com aviso.
9. **Two real Claude Code sessions** (gráfico 5). Barras pareadas por tarefa: wall time alone vs together (média das reps), com a soma serial (137.6 s) contra o par (147.6 s). Frase: functional pass, time fail.
10. **`--prefill-decode-share` 0.3 / 0.5** (tabela pequena). side requests > 60 s (igual ao controle), cold first-token time (dobra). Not adopted.
11. **What we learned** — lista de 6 itens, uma frase cada, numerada, a partir de `summary.md` → Decisões e Notas.
12. **Related upstream work** — tabela: link, tipo (PR/issue/bench), estado (merged in 26.10.1 / merged, unreleased / open / external), o que tem a ver com esta campanha. Itens: PR #568, PR #884, issue #528, PR #621, issue #567, benchmark drowzeys. Nota em itálico: a recusa de admissão vista aqui não tem issue aberta por nós.
13. **Admission refusals** — card com a mensagem exata do servidor (uma citação), a leitura ("the message itself lists more reclaimable memory than the request needs") e o aviso "cause not confirmed".
14. **Not measured** — lista curta de `summary.md` → "O que não foi medido".
15. **Reproduce / data** — comando do servidor para o perfil de 256K e o `daily`; link para o runbook e para `results/` no GitHub; tabela completa de todas as configurações (dobrável, `<details>`), com código curto, nome público, N, contexto, side requests, pior slowdown, result.
16. **Rodapé** com a tabela interno → público e a data de geração.

## Review Focus

1. Configuração sem dados (arquivo JSONL ausente): a página mostra `n/a`, não omite a linha nem quebra.
2. Needles: contados só sobre requests respondidos (regra da review final), igual ao `summarize_parallel`.
3. 256K: razão contra 11.1 s (referência do plano) com a razão contra 10.3 s em nota, igual ao `etapa1b-256k.md`.
4. HTML: nenhum placeholder `__X__` sobra; `</` escapado dentro do payload JSON; nenhum termo da coluna "interno" fora do rodapé (teste com regex sobre o corpo).
5. Números da página batem com `results/summary.md`: 1.76 / 1.94 / 2.37 / 2.36 / 2.84 / 3.85 / 1.68 / 1.81 / 147.6 / 137.6.

## Task 1: `collect()`

**Files:** create `bench/flashnext-concurrency-2026-10/scripts/render_report.py`, `tests/test_render_report.py`.

**Consumes:** `summarize_parallel.summarize(results_dir, arm, context, tag, logs_dir=None, refs=...)` → dict com `streams[]` (`T_turno`, `ratio`, `decode_tps`, `overlap`, `needles`), `aux` (`p50`, `p95`, `n`, `errs`), `memory`, `verdict`.

**Produces:** `collect(results_dir: Path) -> dict` com as chaves:
- `rig`, `model`, `server`, `dates`;
- `configs[]`: `{code, public_name, n, ctx, aux, tag, worst_ratio, worst_stream, decode_per_session, decode_total, aux_p50, aux_p95, aux_over_60, refused, needles, needles_ok, wired_peak, result}` para `w1c1, w1c1a, w1c2, w1c2a, w1c1x2, w1c3a, w1c4, w1c4a` (32K e 128K), `w1c2ap3, w1c2ap5` (128K), `w1c1, w1c2L, w1c2m4, w1c2q8, w1c2m4q8` (256K; `L` e `m4q8` da tag `e1d`, `w1c1` da `e1c`);
- `by_n`: `{ctx: {n: worst_ratio}}` para o gráfico 1 e `{ctx: {n: decode_per_session}}` para o 2;
- `claude_code`: `{tasks: {a: {alone_mean, together_mean, together_reps[]}, b: ...}, serial_sum, pair_wall}`;
- `verdicts`: lido dos dois `.env`;
- `refs`: `{32768: 7.9, 131072: 8.6, 262144: 11.1, 262144_measured: 10.3}`.

Testes (RED primeiro, fixtures mínimos em `tmp_path` com 2–3 records por stream):
- `test_collect_worst_stream_decides`: dois streams com razões 1.1 e 1.9 → `worst_ratio == 1.9`, `result == "warning"`.
- `test_collect_result_bands`: 1.4 → pass; 1.9 → warning; 2.1 → fail.
- `test_collect_missing_config_is_na`: arm sem arquivo → entrada com `worst_ratio is None`, `result == "n/a"`.
- `test_collect_decode_total`: `decode_total == n × mean(decode_per_session)`.
- `test_collect_claude_code_means`: `cc-*.json` fictícios → `alone_mean`, `together_mean`, `serial_sum`, `pair_wall`.
- `test_collect_real_matches_summary` (fumaça sobre `results/`): `w1c2a@32K worst 1.76`, `w1c2a@128K 1.94`, `w1c3a 2.37/2.36`, `w1c4a 3.85@128K`, `w1c2m4 1.68`, `claude_code.pair_wall ≈ 147.6`, `serial_sum ≈ 137.6`.

Commit: `bench(flashnext-concurrency): collect() for the public report page`.

## Task 2: gráficos SVG

**Files:** modify `render_report.py`; `tests/test_render_report.py`.

**Produces:** `svg_grouped_bars(groups: list[dict], series: list[str], ymax: float, bands: list[tuple[float, str]] = ()) -> str`; `svg_dots(rows: list[dict]) -> str` (p50/p95 por linha); `svg_paired_bars(pairs: list[dict]) -> str`.

Testes (RED primeiro): a string começa com `<svg`; um `<rect>` por valor; valores `None` viram um `<text>` "n/a" e nenhum `<rect>`; as faixas 1.5 e 2.0 viram duas `<line>` com `class="band"`; largura via `viewBox`, sem `width` fixo.

Commit: `bench(flashnext-concurrency): SVG bar and dot builders for the report page`.

## Task 3: `render()` e `main()`

**Files:** modify `render_report.py`; `tests/test_render_report.py`.

**Produces:** `render(data: dict) -> str`; `main(argv) -> int` com `--results-dir`, `--out-html`, `--out-json`.

Testes (RED primeiro):
- seções presentes por id (`hero`, `how-it-works`, `glossary`, `sessions`, `throughput`, `side-requests`, `max-concurrent`, `long-context`, `claude-code`, `pds`, `learned`, `upstream`, `refusals`, `not-measured`, `reproduce`, `terms`);
- `test_render_no_insider_terms`: nenhum match de `\b(w1c\w+|T_turno|braço|aux|needle|stream|rig|daily driver|etapa)\b` fora de `<footer>`/`<details>`; `stream` permitido só dentro de `code`;
- `test_render_no_placeholders`: sem `__[A-Z_]+__`;
- `test_render_payload_escaped`: `</` não aparece cru dentro do `<script id="data">`;
- `test_render_na_for_missing`: config ausente → célula `n/a`;
- `test_render_numbers_match_summary`: `1.76×`, `1.94×`, `2.37×`, `3.85×`, `1.68×`, `147.6 s`, `137.6 s` aparecem;
- `test_main_writes_files` em `tmp_path`.

Commit: `bench(flashnext-concurrency): render() and main() for the report page`.

## Task 4: ilustrações didáticas

**Files:** modify `render_report.py` (SVG estático em constantes `ILLUSTRATION_TIMELINE`, `ILLUSTRATION_BATCH`).

- Timeline (seção 2): descrita acima.
- Batch split (seção 5): uma barra de 80 tok/s dividida em 1, 2, 3, 4 fatias iguais, com a legenda "the server's generation speed is shared, not multiplied".

Teste: os dois SVG têm `role="img"` e `<title>`; o `render()` os inclui uma vez cada.

Commit: `bench(flashnext-concurrency): didactic SVG illustrations for the report page`.

## Task 5: publicar

- Rodar `python3 bench/flashnext-concurrency-2026-10/scripts/render_report.py --results-dir bench/flashnext-concurrency-2026-10/results --out-html reports/qwen38-flashnext-concurrency.html --out-json bench/flashnext-concurrency-2026-10/results/report-data.json`.
- Conferir no navegador do app: claro, escuro, 390 px; ler os números contra `summary.md`.
- Card em `reports/index.html`, seção `#flashnext`, depois do card do guia M4 Max, com `c-desc` em inglês e a frase em negrito "2 sessions is the maximum; each runs ~2× slower; no total time saved".
- Linha em `reports/README.md`.
- Nota em `bench/flashnext-concurrency-2026-10/results/summary.md`: link para a página.
- Commit: `reports: public page for the Flash-Next concurrency campaign`. Push.

## Final

Revisão da branch por um revisor novo (modelo mais capaz); Important → fix com teste RED → GREEN; Minor → lista. Depois, menu de integração (a branch já tem ~20 commits sem PR).

## Decisões tomadas neste plano (o usuário pode trocar)

- **Destino:** `reports/` com card no índice, porque a página é externa e o repositório publica `reports/` no GitHub Pages.
- **Idioma da página:** inglês, pela regra do `AGENTS.md`. Se preferir português, a regra do repositório precisa mudar junto.
- **Gráficos:** SVG gerado pelo script, não Chart.js, para a página ficar autocontida e igual à página do Swift 1.5.
- **Fonte dos números:** recálculo a partir dos JSONL, com teste de fumaça contra `summary.md`, em vez de digitar os números no HTML.
