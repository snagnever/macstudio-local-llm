# Página do Swift 1.5 × n2 — design (2026-10-11)

## Objetivo

Publicar os achados da campanha `bench/swift15-flashnext-2026-10` numa página do site, no layout de
`reports/qwen38-flashnext-perf-lines.html`. A página compara velocidade, qualidade, tool turn e tempo por task
das stacks do Flash-Next que têm esses dados. Ela entra no branch da campanha antes do PR e fica no ar depois
do merge no `main` (o workflow `publish-pages.yml` monta o site a partir de `reports/` do `main`).

## Decisões do usuário

| tema | decisão |
| --- | --- |
| stacks na qualidade e no tempo por task | n2 × w1 na comparação principal; o1, m1x, n1 e o n2 de 07/10 numa seção legada, marcada como não comparável |
| formato | página nova `reports/qwen38-flashnext-swift15.html`, gerada por um renderer com teste |
| velocidade | 32K e 128K de todas as stacks com dados; 256K e 512K ficam no perf-lines (link) |
| tempo por task | distribuição por questão (strip plot), mais mediana, total, tokens e truncadas |
| tool turn | duas seções: o cenário `tool_turn` do `T_turno` e a latência por turno do tool-calling |
| perfis | seletor t1/t0, t1 por padrão; a tabela de acertos mostra sempre as 4 colunas |
| extras | gates e veredito, limites, setup por braço, tokens e truncadas |

## Restrições

- Texto da página em inglês (todo conteúdo publicado do site sai em inglês).
- Página autocontida: CSS e JS inline, só a fonte do Google Fonts como recurso externo. Sem Chart.js; os
  gráficos são SVG gerado em JS, como no perf-lines. Tema claro/escuro com o mesmo botão e os mesmos tokens.
- `reports/index.html` ganha um card e `reports/README.md` ganha uma linha (regra do `AGENTS.md`).
- Python 3.9 do sistema, só biblioteca padrão.

## Arquivos

- `bench/swift15-flashnext-2026-10/scripts/render_page.py`
  - `collect(results_dir, reports_json) -> dict`: lê os dados e devolve o payload da página.
  - `render(data) -> str`: devolve o HTML.
  - `main(argv)`: grava `results/page-data.json` e `reports/qwen38-flashnext-swift15.html`. Opções `--data`
    (reusa um `page-data.json`), `--out` e `--json-out`.
  - Reusa `summarize_ab.load_arm`, `view`, `suite_stats`, `SUITES`, `QUALITY_MARGIN`.
- `bench/swift15-flashnext-2026-10/tests/test_render_page.py`.
- `reports/qwen38-flashnext-swift15.html` (gerado), `results/page-data.json` (gerado).

## Fontes de dados

| seção | fonte |
| --- | --- |
| acertos | `results/ab/{t1,t0}/{n2,w1}/*.jsonl` via `summarize_ab`; HumanEval com imports de `humaneval-regrade.json` (`with_imports`, `strict`) |
| tempo por task | `elapsed_s` por questão (bench2 e IF); tool suites: `turn_1_elapsed_s + turn_2_elapsed_s` (o `view()` já soma) |
| tokens e truncadas | `completion_tokens`, `reasoning_chars` (n/d quando ausente), `finish_reason == "length"` |
| latência do tool-calling | `turn_1_elapsed_s` de todos os casos; `turn_2_elapsed_s` só dos casos multi-turno |
| velocidade n2 e w1 | `results/tturno-summary.json` (`n2@32768`, `n2@131072`, `w1@…`) |
| velocidade o1, m1, d1, c1 | grupos `canonical: true` de `engine-updates-2026-10/results/reports-2026-10.json` a 32768 e 131072; o m1 é o m1p a 32K e o m1x a 128K (o rótulo mostra o braço real) |
| seção legada | constantes no script, citando `engine-updates-2026-10/results/quality-o1-mtplx.md` e `qwen38-flashnext-updates-2026-10/results/quality-n1-n2.md` |

## Estrutura da página

1. Header: eyebrow, título "Swift 1.5 vs iQ-MLX on mlx-serve", veredito em uma frase, botão de tema.
2. Notice: Terminal-Bench não medido (precisa de outra máquina para os containers Docker).
3. Rig (faixa de cards, do `reports-2026-10.json`) e setup por braço (pesos, revisão, runtime, flags, sampling
   t1 e t0).
4. Gates: G1/G2/G3 com o limite, o valor em t1 e em t0, passa/falha, e a regra de decisão.
5. Seletor de perfil t1/t0 (controla as seções 6–8).
6. Quality: tabela fixa com as 4 colunas e a margem do G1 (HumanEval com imports e estrito); barras pareadas
   n2 × w1 por suíte, em porcentagem, para o perfil escolhido.
7. Time per task: um strip plot por suíte (uma bolinha por questão, escala log de tempo, mediana marcada,
   bolinha vazia = falhou, contorno de aviso = truncada) e uma tabela com mediana, total, razão w1/n2, tokens
   medianos, caracteres de reasoning medianos e truncadas.
8. Tool-calling latency: tabela por suíte e braço com mediana do turno 1, mediana do turno 2 (n de casos
   multi-turno) e acertos.
9. Agent turn speed (`tool_turn`): tabela das stacks a 32K e 128K com `T_turno`, TTFT quente do `tool_turn`,
   hit do `tool_turn`, TTFT frio, decode, prefill, aceitação da MTP e wired pico. Linhas n2 e w1 da mesma sessão
   primeiro; nota com o `T_turno` do n2 medido na Etapa G (8.23 / 8.84 s) como medida da deriva entre sessões.
   Link para o perf-lines.
10. Earlier quality batteries (not comparable): HumanEval estrito e com imports, truncadas, jdhodges, Veerman,
    tokens médios e tempo total do HumanEval para n2 (07/10), n1, o1 e m1x; aviso de que o n2 e o n1 rodaram
    sem `reasoning_effort` (~200 tokens por questão) e o o1 e o m1x pensaram.
11. Limits e footer com as fontes e o comando de regeneração.

## Comportamento em dados ausentes

- Uma suíte que falta num braço ou perfil aparece como `n/d` na tabela e como painel vazio com a razão; ela não
  some da página.
- `reasoning_chars` ausente em todos os registros vira `n/d`.
- Uma stack sem grupo canônico numa banda aparece com `—` e a razão.

## Testes

- `collect()` sobre fixtures pequenas: acertos, mediana, total, truncadas e razão w1/n2 por suíte e perfil.
- Suíte ausente num braço: `collect()` marca `missing`, e o HTML mostra `n/d`.
- Latência do tool-calling: turno 2 só conta casos multi-turno.
- Velocidade: escolhe só grupos canônicos e expõe o braço real (m1p/m1x).
- `render()`: contém cada seção, o seletor t1/t0, o payload JSON válido e nenhum placeholder `__X__` sobrando.
- Fumaça: `collect()` sobre os dados reais reproduz os números do `summary.md` (HumanEval com imports 158/158/155/157,
  GPQA 45/43/39/42, mediana GPQA t1 63.9 / 22.3 s).

## Fora do escopo

- Novos runs (256K/512K do w1, Terminal-Bench).
- Mudanças no perf-lines ou em outras páginas além do card no índice.
