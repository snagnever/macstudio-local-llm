# Etapa 0 — pré-voo (2026-10-17)

| item | valor |
| --- | --- |
| disco livre (`df -g /`) | 359 GB |
| driver diário antes da campanha | `mlx-serve` 26.10.1 órfão (PPID 1), Swift 1.5 `13839b7`, perfil diário 128K; sem cliente conectado; parado com `kill` |
| `--max-concurrent` no `--help` do 26.10.1 | **ausente** do texto de ajuda ([mlx-serve-26101-help.txt](mlx-serve-26101-help.txt)) |
| `--max-concurrent` no binário | presente; o boot com `--max-concurrent 2` imprime `Concurrency: --max-concurrent=2, batched decode on` |
| linhas de boot com 2 slots | `[batched] row-axis mtp verify engaged (slots=2, width=2)` e `[batched] row-axis mtp verify grouped MoE engaged (slots=2)` |
| `/props` | `total_slots: 1` (campo de compatibilidade, não muda com a flag); `batching: {supported: true, reason: ok, max_group: 32}`; sem campo `max_concurrent` |
| `--prefill-decode-share` | presente, default 0 |
| `--prefix-cache-entries` | presente, default 32 (o driver usa 64) |
| caminho no rig | `uv` e `macmon` em `/opt/homebrew/bin`, fora do `PATH` do `ssh` não interativo |

## Formato do log por requisição

O servidor escreve um bloco por requisição. A primeira linha tem rota e parâmetros, a última tem tokens e tempo:

```
POST /v1/messages (1 msgs, max_tokens=1, temp=1.00, top_p=0.95, top_k=20, stream=false, thinking=false, sys=0b, tools=0b, tool_msgs=0)
[admission] needed=651 MB available=38524 MB reclaimable=0 MB width=8192 verdict=admit
  [hot-cache] reused 12/13 tokens (matched 13; entry 1/1)
  <- 13+1 tokens (45ms) [prefill: 51.1 tok/s (12 cached / 13 total), decode: 0.0 tok/s] [max_tokens]
```

O log não grava o status HTTP. A contagem de requisições por rota sai das linhas `POST`. Os erros HTTP contam do lado do cliente (`aux_load.py`, `cache_probe.py`, JSON do `claude -p`).

## Leitura

A flag existe no 26.10.1 e liga o decode em lote para o Flash-Next, apesar de faltar no `--help`. A campanha segue. O Task 2 Step 3 confere a linha `Concurrency:` do log de boot em vez de um campo do `/props`.
