# Report "Can one Mac Studio serve Claude Code?" e a campanha de Claude Code realista — design (2026-10-30)

## Objetivo

Responder, numa página pública e nos docs do repo, a duas perguntas de uso:

1. Um LLM local no rig dá uma experiência de código satisfatória num harness como o Claude Code?
2. O que muda quando mais de uma sessão roda ao mesmo tempo, como acontece no uso diário?

As campanhas `bench/flashnext-concurrency-2026-10` (mlx-serve 26.10.1, 18/10) e
`bench/splash-concurrency-2026-10` (Splash 1.5.0, 29/10) já medem velocidade sob concorrência. O report atual,
`reports/qwen38-flashnext-concurrency.html`, organiza esses dados por campanha e por gate de harness, e não
pelas duas perguntas. Este design cobre três entregas:

- **A. Report novo**, na mesma URL, organizado por cenário de uso, em segundos que a pessoa espera, com um
  gráfico por seção.
- **B. Campanha nova**, `bench/claude-code-concurrency-2026-11`, que preenche os buracos do report: par de
  Claude Code no mlx-serve 26.10.3, tarefa realista (60–120K de contexto, 20–40 turnos), subagentes, e
  métricas por request nos dois servidores.
- **C. Docs**: `docs/models/qwen3.8-flash-next.md`, o card em `reports/index.html` e `reports/README.md`.

A qualidade do agente (Terminal-Bench) fica fora deste design. O report mostra "não medido" ou "em execução"
até que a campanha de Terminal-Bench do `w1z` (sessão "Atualizações de stack preferidas") e uma equivalente
no Splash existam.

## Decisões do usuário

| tema | decisão |
| --- | --- |
| veredito no corpo do report | faixas de experiência em segundos; o gate de razão (1.5× / 2.0×) vai para o apêndice |
| colunas de servidor | Splash 1.5.0 (GGUF `IQ4_XS`) e mlx-serve 26.10.3 (MLX 4.7bpw); o 26.10.1 fica no apêndice |
| faixas | as propostas abaixo servem |
| estrutura e gráficos | o mockup v2 ([2026-10-30-coding-concurrency-report-mockup.html](2026-10-30-coding-concurrency-report-mockup.html)) foi aprovado; nenhum gráfico foi removido |
| idioma | página e código em inglês; runbook, resultados e este documento em pt-BR |

## Faixas de experiência

Escolha minha, aprovada pelo usuário. Cada faixa tem ícone e rótulo; a cor nunca carrega o sentido sozinha.

| métrica | boa | aceitável | ruim |
| --- | --- | --- | --- |
| resposta começa (TTFT de turno quente) | ≤ 2 s | 2–5 s | > 5 s |
| geração (tok/s) | ≥ 60 | 30–60 | < 30 |
| primeiro prompt de uma sessão (~20K tokens) | ≤ 30 s | 30–60 s | > 60 s |
| chamada curta ao lado (permissão, título), p95 | ≤ 5 s | 5–60 s | > 60 s |

Leitura fria de 128K ou 256K e tempo de tarefa não têm faixa: são custos únicos ou dependem da tarefa.

## Restrições

- Página autocontida, em inglês, mesma URL e mesmos tokens de tema (claro/escuro) do report atual. Sem
  biblioteca de gráficos: SVG inline gerado em Python, como hoje. Cada gráfico com ≥ 2 séries tem legenda; todo
  gráfico tem tooltip no hover e uma vista em tabela (`<details>`), como a skill `dataviz` pede.
- Uma cor por servidor em toda a página: Splash = série 1 (`--s1`, azul), mlx-serve = série 2 (`--s2`, laranja).
  Hachura = não medido. Sem eixo duplo. Escalas separadas quando os valores diferem em ordem de grandeza.
- Toda célula de servidor declara pesos e versão uma vez, no cabeçalho da coluna. Nenhuma coluna mistura
  versões: um dado do 26.10.1 aparece com marcador próprio (ponto vazio) e nota, ou fica no apêndice.
- Python 3.9 do rig, só biblioteca padrão. Testes com `uv run --no-project --with pytest`. bash 3.2 no rig.
- O rig serve um modelo por vez. A fila para o daily driver da 11234 e o religa no fim (`logs/chain.sh`). **Antes
  de parar a 11234, avisar a sessão "Atualizações de stack preferidas"** (regra dela, 30/10): o Terminal-Bench
  do `w1z` usa o driver.
- Não alterar `splash-v1.4.0` e `splash-v1.4.1`. Não tocar no checkout principal do rig
  (`~/LocalProjects/macstudio-local-llm`); usar o worktree `~/LocalProjects/macstudio-local-llm-splashconc` ou um
  novo para a campanha.
- Dados brutos em `bench/<campanha>/results/` (rastreados) e logs em `bench/<campanha>/logs/` (ignorados), como o
  `AGENTS.md` manda. O que o report precisa dos logs (TTFT por request, tok/s) vai para um JSONL em `results/`.

## Entrega A: report novo

### Arquivos

- `bench/flashnext-concurrency-2026-10/scripts/render_report.py`: reescrever `render()` e as seções; manter
  `collect()` e acrescentar a leitura da campanha nova. `collect()` continua devolvendo um dict serializado em
  `results/report-data.json`.
- `bench/flashnext-concurrency-2026-10/tests/test_render_report.py`: testes das seções novas, das faixas e do
  comportamento com dados ausentes.
- `reports/qwen38-flashnext-concurrency.html` (gerado).

### Estrutura da página

1. **Header.** Título "Can one Mac Studio serve Claude Code? And two sessions at once?", linha de rig, modelo,
   pesos e versão de cada servidor, datas, botão de tema.
2. **Três tiles de veredito.** Uma sessão: "Yes" (resposta em 0.8 s; primeiro prompt 24 s). Duas sessões: "Yes,
   at a cost" (1.8 s em vez de 0.8 s; o par termina 24% antes das duas tarefas em sequência). Três ou mais:
   "No" (2.4×–4.6× mais lento). A métrica do par é "tempo poupado" = 1 − par ÷ sequência (0.24 no Splash,
   −0.07 no 26.10.1), a mesma dos summaries; o mockup escreve "+24% work per hour", que seria +32%, e o
   renderer usa o rótulo "finishes 24% sooner".
   Os números vêm do payload, não de texto fixo. **Regra (escolha minha):** a palavra do veredito e o número
   grande vêm do servidor recomendado, fixado numa constante do renderer (`RECOMMENDED = "splash"`); o outro
   servidor aparece numa segunda linha do tile ("mlx-serve 26.10.3: 1.9 s"), hachurada quando não medido. A
   frase sobre subagentes só entra no tile quando a campanha B tiver medido o N real (ver `rc2s`).
3. **Faixas** (legenda com ícone e rótulo) e **aviso de qualidade**: Terminal-Bench não medido ou em execução.
4. **One session.** Painéis pequenos, um por métrica, barras horizontais Splash × mlx-serve com o fundo das
   faixas: resposta começa (turno quente), primeiro prompt de 20K, leitura fria de 128K (sem faixa), geração em
   tok/s (barra de intervalo). Tabela: tempo das tarefas, uma linha por perfil ("small task, 4–7 turns": a/b;
   "realistic task, 20–40 turns": c/d), Terminal-Bench.
5. **Two sessions, daily use.** Halteres "sozinho → par" por servidor: resposta começa (mediana e p90), geração
   (mediana e pior request), tempo de tarefa. Barra divergente "tempo poupado pelo par" (1 − par ÷ sequência). Barras da
   chamada curta (p95) com a linha de 60 s. Nota com o cenário medido (tarefa, contexto, tokens novos por
   turno, subagentes). **Regra (escolha minha):** os halteres de TTFT e geração juntam os requests de todas as
   tarefas do mesmo servidor; o tempo de tarefa e o tempo poupado têm uma linha por perfil (a/b e c/d).
   Os dois servidores mostram os mesmos perfis, porque a campanha B roda a/b e c/d nos dois.
6. **Worst case: both sessions read a big prompt at once.** Linha do tempo esquemática (sessão A, sessão B, a
   chamada curta nos dois servidores). Barras "sozinho dentro de par" do tempo do turno sintético a 128K.
   Tabela: chamadas curtas acima de 60 s, geração total, melhor ajuste do Splash (`--decode-share 1.0`).
7. **Three and four sessions, and subagents.** Gráfico de linha: tempo do pior turno por número de sessões
   (1–4) a 128K, duas séries; pontos do 26.10.1 vazios, com nota. Tabela com N = 3, 4, chamada curta p95 e a
   linha "2 sessões + 1 subagente cada" (medida pela campanha B).
8. **Long sessions: two at 256K.** Barras do pior turno e nota da leitura fria de ~12 min.
9. **Recommendation.** Tabela uso → servidor → motivo.
10. **What was measured.** Matriz cenário × servidor com ● medido, ◐ em execução, ○ não medido.
11. **Appendix** (`<details>`): método, gates da campanha e seus vereditos, needles, glossário, tabela
    completa de configurações, resultados do 26.10.1, runbooks, comando de regeneração.

### Fontes de dados por seção

| seção | Splash 1.5.0 | mlx-serve 26.10.3 | 26.10.1 (apêndice) |
| --- | --- | --- | --- |
| resposta começa, geração, primeiro prompt (uma sessão e par) | campanha B (`kcc*` realista); até lá, os `kcc*` de 29/10 reprocessados dos logs do Splash | campanha B | `cc*` de 18/10 só por `wall_s` |
| leitura fria de 128K | `k2c1` a 131072 (`cold` TTFT) | `w1zc1` a 131072 | `w1c1` |
| tempo de tarefa, tempo poupado pelo par | `kcc1`, `kcc2` (29/10) e campanha B | campanha B | `cc1`, `cc2` |
| chamada curta p95 | `k2c2a` 131072 `aux` | `w1zc2a` 131072 `aux` | `w1c2a` |
| pior caso sintético | `k2c2a`, `k2c2ad1` | `w1zc2a` | `w1c2a`, `w1c2ap*` |
| N = 3, 4 | `k2c3a`, `k2c4a` | não medido (hachura) | `w1c3a`, `w1c4a` |
| 256K | `k2c2LL`, `k2c2Ls` | não medido | `w1c2m4` |
| subagentes | campanha B | campanha B | — |
| Terminal-Bench | não medido | `bench/stack-updates-2026-10/results/tbench-status.json` (ver abaixo) | — |

**Status do Terminal-Bench (escolha minha).** O `collect()` lê, se existir, um JSON rastreado com `{"server",
"weights", "done", "total", "score", "updated"}` em `bench/stack-updates-2026-10/results/tbench-status.json`. Quem
escreve é a sessão "Atualizações de stack preferidas", a pedido desta; se ela não escrever, o renderer mostra
"not measured" e nada fica fixo no código. O mesmo arquivo serve para o `k3f` no Splash quando ele rodar.

### Comportamento com dados ausentes

Uma célula sem dado aparece hachurada com `n/m` (gráfico) ou `n/m` (tabela) e entra na matriz como ○. A
página renderiza com qualquer subconjunto das campanhas; os testes cobrem "só 29/10", "com a campanha B" e
"sem a campanha B".

## Entrega B: campanha `bench/claude-code-concurrency-2026-11`

### Perguntas

1. Com uma tarefa realista, quanto a segunda sessão custa em cada servidor: TTFT quente (mediana, p90), tok/s
   (mediana, pior), tempo de tarefa e tempo poupado pelo par?
2. Subagentes mudam o custo? Duas sessões com um subagente Explore cada se comportam como N = 4?
3. `--decode-share 1.0` ajuda o par real no Splash?

### Braços

| braço | sessões | servidor | tarefas | subagentes | flag extra |
| --- | ---: | --- | --- | --- | --- |
| `rc1` | 1 | Splash 1.5.0 | a, b, c, d em sequência | não | — |
| `rc2` | 2 | Splash 1.5.0 | par a+b e par c+d | não | — |
| `rc2s` | 2 | Splash 1.5.0 | par c+d | 2 Explore em paralelo por sessão | — |
| `rc2d` | 2 | Splash 1.5.0 | par c+d | não | `--decode-share 1.0` |
| `rm1` | 1 | mlx-serve 26.10.3 (flags do driver diário) | a, b, c, d em sequência | não | — |
| `rm2` | 2 | mlx-serve 26.10.3 | par a+b e par c+d | não | — |
| `rm2s` | 2 | mlx-serve 26.10.3 | par c+d | 2 Explore em paralelo por sessão | — |

3 reps por par; o solo (`rc1`, `rm1`) roda cada tarefa 2 vezes. As tarefas a e b entram de novo (1–2 min por
rep) para que os dois servidores tenham o mesmo perfil pequeno na mesma versão. Pesos: os mesmos das
campanhas de outubro (Swift 1.5 GGUF `IQ4_XS` `0142554`; Swift 1.5 MLX 4.7bpw `13839b7`).

**Subagentes (escolha minha).** Em `claude -p`, um `Agent` em foreground bloqueia a sessão-mãe; um subagente
por sessão daria N = 2 de novo. O prompt das tarefas c e d, na variante `--subagents`, pede duas passadas de
Explore em paralelo (duas chamadas `Agent` na mesma mensagem) antes de editar, e a tool `Agent` entra no
`--allowedTools`. O número de requests concorrentes é medido pelo proxy e reportado como N real; o report
escreve "two sessions with subagents ran as N streams", com o N medido, e não afirma "quatro" de antemão.

### Tarefas

Duas tarefas novas, `task-c` e `task-d`, em repositórios de exemplo próprios (`scripts/claude-tasks/repo-c`,
`repo-d`), com estes requisitos:

- cada tarefa leva 20–40 turnos e chega a 60–120K de contexto numa sessão sozinha;
- cada tarefa exige ler ≥ 5 arquivos, dos quais ≥ 2 com mais de 5K tokens (rajadas de prefill);
- resultado checável por script (`task_done`), como as tarefas A e B;
- `--max-turns 60`, timeout de 30 min por sessão.

O conteúdo das tarefas fica a cargo do builder. Sugestão: um pacote Python de ~1.5K linhas com uma
funcionalidade para adicionar com testes (c) e um conjunto de scripts shell com bugs e um refactor (d).

### Medição por request

Um proxy HTTP em Python (`scripts/request_log.py`, stdlib, no rig) fica entre o Claude Code e o servidor e
grava um JSONL por sessão com, por request: `t_start`, `ttft_s`, `t_end`, status,
`input_tokens`, `cached_tokens` e `output_tokens` quando o servidor informa, e `stream` (a sessão). O proxy
vale para os dois servidores e dispensa o parser de log de cada um. Escolha minha: o log do mlx-serve 26.10.3
não dá TTFT por request, e o do Splash dá, mas em formato próprio.

**Definição de TTFT (escolha minha).** `ttft_s` é o tempo até o primeiro `content_block_delta` com texto ou
thinking, não até o primeiro byte: o `message_start` sai antes do prefill (`ttft_stream_ms: 60` contra
`first_content_frame_ms: 31811` num `cc-kcc2r1-a.json`). Essa definição coincide com o `TTFT` server-side do
log do Splash, que é a fonte dos `kcc*` de 29/10 reprocessados; as duas fontes medem a mesma coisa.

`run-claude-pair.sh` ganha `--task c|d`, `--subagents` (libera a tool `Agent` e pede uma passada de Explore no
prompt) e `--proxy PORT`. O JSONL do proxy vai para `results/req-<tag>-<task>.jsonl`.

### Métricas e leitura

Por braço: TTFT quente mediana e p90, tok/s mediana e mínimo, TTFT do primeiro prompt, `wall_s` por tarefa,
"tempo poupado" = 1 − tempo do par ÷ soma dos solos, número de requests concorrentes máximo (medido, para
confirmar N real com subagentes), `task_done`, erros HTTP, swap Δ. Sem gate de razão: o resultado é a posição
nas faixas de experiência, mais o funcional (tarefas feitas, zero erros).

### Arquivos

- `bench/claude-code-concurrency-2026-11/plan.md` (runbook), `results/`, `logs/`, `tests/`.
- `bench/flashnext-concurrency-2026-10/scripts/run-claude-pair.sh` (flags novas), `scripts/claude-tasks/` (tarefas
  c e d), `scripts/request_log.py` (novo), `scripts/summarize_claude.py` (novo: lê `cc-*.json` e
  `req-*.jsonl`, imprime a tabela e grava `results/claude-summary.json` para o `collect()` do report).
- `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh`: braços `rc*` e `rm*`.

### Custo estimado

~14 h de rig: 7 braços × 3 reps × ~6–10 min por rep (tarefas de 20–40 turnos), mais os pares a+b, boots e
idle gates. O rig está reservado pela sessão "Atualizações de stack preferidas" a partir de 30/10 à tarde
(Terminal-Bench do `k3f`, 26–30 h, depois o `t5r`); a campanha B pede uma janela depois disso.

## Entrega C: docs

- `docs/models/qwen3.8-flash-next.md`: a seção "Concurrent sessions" passa a ter a tabela por cenário (uma
  sessão, duas no uso diário, pior caso, N ≥ 3, 256K) com as duas colunas de servidor, em segundos, e o link
  para o report. Os parágrafos do 26.10.1 saem para o summary da campanha de 18/10.
- `reports/index.html`: card do report com título e descrição novos. `reports/README.md`: linha atualizada.
- `bench/splash-concurrency-2026-10/results/summary.md` e o summary de 18/10: nota "report reorganizado em
  2026-11" com link.

## Ordem de execução

1. Entrega A com os dados existentes (os `kcc*` de 29/10 reprocessados dos logs do Splash dão TTFT e tok/s
   do par real). O report publica com hachuras onde a campanha B ainda não rodou.
2. Entrega B no rig; o `collect()` lê `claude-summary.json` e as hachuras somem.
3. Entrega C.

## O que fica para o builder

- O desenho exato de cada SVG (posições, escalas), dentro das regras da skill `dataviz`.
- O conteúdo das tarefas c e d e dos repositórios de exemplo.
- A ordem dos braços na fila do rig e os idle gates.
- O prompt exato da variante `--subagents` e a checagem de que as duas chamadas `Agent` saíram em paralelo.

## Fora de escopo

- Terminal-Bench no Splash e a decisão de trocar o daily driver.
- Sessão interativa de Claude Code (com permissões e títulos reais): fica como pergunta aberta no apêndice.
- 512K e 1M. Mais de 4 streams. Outros modelos.
