# Task 4: Sessões do Claude Code (2026-11-12)

**A 1.6.1 passa na regra "Claude Code". Contra a 1.5.0 na mesma fila, o wall do par cai 3% no `rc2` e 33% no `rc2s`. O warm TTFT p50 cai 36% no `rc2` e 50% no `rc2s`. As 20 sessões cumprem a tarefa.**

Tarefas c e d, contexto 131072, Claude Code 2.1.292 (`CLAUDE_BIN=/opt/homebrew/bin/claude`), PLE `auto`. Fila `logs/chain-t45.sh`, das 05:34 às 07:17 (relógio do rig), na ordem f, h, h, f, h para cada perfil. A 1.5.0 tem 2 reps por perfil (tags `f1`, `f4`), e a 1.6.1 tem 3 (tags `h2`, `h3`, `h5`).

## Regra "Claude Code"

O limite é 1.10 × o controle da 1.5.0.

| perfil | métrica | 1.5.0 | 1.6.1 | razão |
|---|---|---:|---:|---:|
| par (`rc2`) | wall do par | 347.6 s | 336.1 s | **0.967** |
| par (`rc2`) | warm TTFT p50 | 1.4 s | 0.9 s | **0.64** |
| subagents (`rc2s`) | wall | 848.1 s | 568.4 s | **0.670** |
| subagents (`rc2s`) | warm TTFT p50 | 3.2 s | 1.6 s | **0.50** |

**Veredito:** passa.

## Outras métricas

| perfil | métrica | 1.5.0 | 1.6.1 |
|---|---|---|---|
| par (`rc2`) | warm TTFT p90 | 4.0 s | 2.3 s |
| par (`rc2`) | warm tok/s p50 / mín | 100.5 / 56.2 | 92.2 / 39.9 |
| par (`rc2`) | requests | 74 | 135 |
| subagents (`rc2s`) | warm TTFT p90 | 10.1 s | 9.1 s |
| subagents (`rc2s`) | warm tok/s p50 / mín | 89.4 / 19.0 | 86.3 / 21.1 |
| subagents (`rc2s`) | requests, concorrência máxima | 109, 5 | 158, 6 |
| subagents (`rc2s`) | subagents criados, chamadas paralelas | 8, 4 | 12, 6 |

- **Wall por rep** (o maior das duas sessões):
  - `rc2`: 1.5.0 306.3 e 389.0 s; 1.6.1 308.2, 349.6 e 350.6 s.
  - `rc2s`: 1.5.0 833.5 e 862.7 s; 1.6.1 651.5, 596.0 e 457.7 s.
- **Tok/s:** no par, o p50 cai 8% e o mínimo cai 29% na 1.6.1. O mínimo vem de um único request. A regra registra o tok/s mínimo só como observação, como na splash16.
- **Requests:** as contagens são somas das reps. A 1.6.1 tem 3 reps e a 1.5.0 tem 2.
- **Tarefas cumpridas:** 8 de 8 sessões na 1.5.0 e 12 de 12 na 1.6.1, todas com exit 0.
- **Erros HTTP:** nenhum.
- **Espera por memória:** os 10 logs de boot não têm linhas `pending` nem `claim wait` maior que 0.

## Comparação com a splash16

Na splash16, a 1.6.0 também ficou mais rápida que a 1.5.0 nas sessões do Claude Code: 321.4 s contra 398.6 s no par e 724.4 s contra 969.9 s nos subagents. A 1.6.1 mantém esse ganho nos subagents. No par, o ganho fica menor (3% contra 19%), mas o controle da 1.5.0 deste dia é mais rápido que o da splash16 (347.6 s contra 398.6 s).

## Parser do log

O teste `test_parse_splash_log_counts_match_proxy` usa a primeira rep da 1.6.1 (`rc2` `h2`). O log do servidor tem 44 linhas `Done`. O `request_log.py` gravou 45 requests, e um deles tem 0 tokens de entrada e não é um turno do modelo. Os 44 restantes têm os mesmos tamanhos de entrada do log. Com o parser de antes do Task 0, o teste falha, porque o log da 1.6.1 tem `request N` nas linhas.

## Desvios

- **Nomes dos arquivos:** o `summarize_claude.py` espera `cc-rc2r<rep>-<tarefa>.json`, e esta fila grava `cc-rc2<tag>-<tarefa>.json`. O resumo roda sobre links com nomes de rep (`f1`→r1, `f4`→r2; `h2`→r1, `h3`→r2, `h5`→r3). Os arquivos originais ficam com os nomes da fila.

Fontes: `cc-rc2{,s}<tag>-{c,d}.json`, `req-rc2{,s}<tag>-{c,d}.jsonl`, [claude-summary-150.json](claude-summary-150.json), [claude-summary-161.json](claude-summary-161.json). Referência da 1.6.0: [etapa4-concorrencia.md da splash16](../../splash16-2026-11/results/etapa4-concorrencia.md).
