# Etapa 13 — needles a 256K, Swift 1.5 × iQ (2026-10-16, mlx-serve 26.10.1, max_tokens 8192)

Runbook: [plan-effort-needles.md](../plan-effort-needles.md), Task 13. Ordem das subidas: `w1 n2 n2 w1 w1 n2`, 1 rep cada, KV sem quantização. Cada subida grava um arquivo `<braço>-262144-t1.0-e13r<N>.jsonl`.

## 256K, 3 reps alternados

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| n2 | 256K | 10.1 s | 344.2 s | 2.10 s | 1.00/1.00 | 63.9 | 0.687 | 112.7 GB | 0.00 GB | 0 | 14/15 (1 trunc) |
| w1 | 256K | 9.8 s | 344.2 s | 2.10 s | 1.00/1.00 | 66.3 | 0.690 | 111.9 GB | 0.00 GB | 0 | 15/15 |

- n2 @ 256K: livre mínimo 0.01 GB; gates passa; alertas wired>102
- w1 @ 256K: livre mínimo 0.01 GB; gates passa; alertas wired>102

`wired peak`, `swap Δ` e o livre mínimo vêm só da última subida de cada braço: o driver reescreve o `-mem.jsonl` a cada subida com o mesmo nome. Os JSONL das três subidas foram preservados (o driver guardou os dois primeiros como `.bak`, renomeados para `e13r1` e `e13r2`).

## Veredito

O `w1` acertou os needles nos 15 registros, e o `n2` acertou 14 de 15. O único registro sem acerto do `n2` é um `tool_turn` truncado em 8192 tokens, sem resposta. Pela regra do P3, os 2 erros do `w1` na Task 2 (11/13) eram variância, não perda de retrieval do Swift a 256K. Taxa somada do `w1` a 256K (Task 2 + Task 13): 26 de 28 registros. O Swift pode servir o perfil de 256K.

## Leitura

- Nenhum registro terminou com `finish_reason=stop` e needle errado. Não houve erro a classificar pelo `content_head`.
- A Task 2 usou `max_tokens` 4096, e esta usou 8192. A fixture reserva `max_tokens` + 1536 tokens, então o prompt desta etapa é ~4K tokens menor (252562 contra ~256.6K). Os erros da Task 2 terminaram com `stop`, então o limite de saída não os explica. A diferença de prompt é pequena, mas não está isolada.
- O `T_turno` do `w1` (9.8 s) ficou abaixo do da Task 2 (11.1 s). O decode subiu de 61.7 para 66.3 tok/s. O `n2` ficou em 10.1 s, contra 9.8 s da rodada de 2026-10-11 (1 rep).
- O `cold TTFT` (344 s) e o `warm TTFT` (2.1 s) são iguais nos dois braços em todas as subidas (desvio < 0.3 s). Os dois packs têm a mesma arquitetura, e a 256K o prefill domina o TTFT.
- O `n2` pensa mais nesta banda: o `tool_turn` truncado gastou 25915 chars de reasoning, e outro `tool_turn` chegou a 6514 tokens. O maior registro do `w1` foi um `append` com 4858 tokens.
- Os dois braços chegam a 0.01 GB livres. A 256K o perfil diário fica no limite de memória do rig.
