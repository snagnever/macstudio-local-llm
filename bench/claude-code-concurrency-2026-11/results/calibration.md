# Campanha B — smoke e calibração no rig (30/10/2026)

Rig: Mac Studio M4 Max 128 GB. Claude Code 2.1.292 (`/opt/homebrew/bin/claude`), `CLAUDE_CODE_EFFORT_LEVEL=xhigh`.
Splash 1.5.0 (ukisai Swift 1.5 IQ4_XS, flags do `k2c1`, `--max-context 131072`) e mlx-serve 26.10.3 (Dankpaws
Swift 1.5 MLX 4.7bpw, flags do `w1zc1`, `--max-context 131072`). Os arquivos desta etapa estão em
`results/calibration/`. Os `cc-*.json` (turnos, contexto, tempo, `task_done`) valem para todas as corridas; os
`req-*.jsonl` das corridas marcadas valem só a partir da correção do proxy (ver "Proxy").

## Proxy (`request_log.py`)

Três correções saíram do smoke, todas com teste:

1. **`input_tokens` da API é só a parte não cacheada.** O log do Splash (dados `kcc` de 29/10) informa o total.
   O proxy passou a gravar `input_tokens = input + cache_read + cache_creation`. Antes da correção o resumo dava
   `new_tokens_p50` negativo (`req-rc1smoke-a.jsonl`, `req-rm1smoke-a.jsonl`).
2. **TTFT no primeiro `content_block_delta` de qualquer tipo.** Um turno só de tool call não tem `text_delta` nem
   `thinking_delta`; o primeiro token dele é o `input_json_delta`.
3. **`read(4096)` esperava 4 KB antes de repassar.** Numa resposta chunked isso atrasa cada evento em um buffer:
   o TTFT quente saía 1–2.5 s (log do Splash: 0.6–0.8 s) e o tok/s 2–5× alto. Com `read1` o proxy repassa o que
   chegou. Validação (`rc1smoke2-a`, Splash): proxy × log do Splash, request a request, TTFT 23.73/23.7 s,
   0.82/0.8 s, 1.22/1.2 s; tok/s 140.0/138.9, 170.9/170.1, 163.0/162.7; `input` e `cached` iguais.
   Os `req-*` de `rc1smoke-a`, `rm1smoke-a`, `rc1cal1-c`, `rc1cal1-d` têm TTFT e tok/s inflados por isso.

## Smoke (tarefa a, uma sessão)

| corrida | servidor | wall_s | turnos | task_done | requests | 1º prompt TTFT | TTFT quente | `cached_tokens` |
|---|---|---:|---:|---|---:|---:|---|---|
| `rc1smoke-a` | Splash | 39.5 | 10 | sim | 7 | 24.1 s | 0.96–2.5 s (inflado) | numérico |
| `rc1smoke2-a` | Splash | 39.4 | 10 | sim | 7 | 23.7 s | 0.49–1.22 s | numérico |
| `rm1smoke-a` | mlx-serve | 51.6 | 12 | sim | 8 | 26.8 s | 0.6–2.8 s (inflado) | **nulo** |

mlx-serve 26.10.3 não manda `cache_read_input_tokens` no `message_start` (Review Focus 1): `cached_tokens`
fica nulo e o `summarize_requests` classifica prefill por `ttft_s > 5 s`. O `input_tokens` do `message_start`
dele é o prompt inteiro (19 353 no primeiro request, contra 19 428 no Splash). O SSE bruto do `rm1smoke3-a`
mostrou onde o mlx-serve informa o cache: no `usage` do `message_delta` final (`input_tokens` 411 +
`cache_read_input_tokens` 19 496 = 19 907, o total do `message_start`). O parser passou a preferir o `usage` do
`message_delta` quando ele traz `cache_read_input_tokens`; com isso `cached_tokens` é numérico nos dois servidores
e a regra de prefill por TTFT > 5 s fica só como reserva. O `req-rm1smoke3-a.jsonl` foi gravado antes dessa
correção (`cached_tokens` nulo); as filas já rodam com ela.

| corrida | servidor | wall_s | turnos | task_done | requests | 1º prompt TTFT | TTFT quente | tok/s quente |
|---|---|---:|---:|---|---:|---:|---|---|
| `rm1smoke3-a` | mlx-serve | 46.5 | 11 | sim | 6 | 25.0 s | 0.32–0.94 s | 67–110 |

## Calibração das tarefas c e d (Splash, uma sessão)

Faixa alvo: 20–40 turnos, 60–120K de contexto final, `task_done`, sem timeout.

| corrida | tarefa | prompt | turnos | contexto final | wall_s | task_done |
|---|---|---|---:|---:|---:|---|
| `rc1cal1-c` | c | `--group-by` no pacote `ledger` | 28 | 66K | 163.8 | sim |
| `rc1cal1-d` | d | 3 bugs + refactor nos 5 scripts | 49 | 84K | 382.1 | sim |
| `rc1cal2-d` | d | 2 bugs + refactor nos 5 scripts | 48 | 66K | 340.7 | sim |
| `rc1cal3-d` | d | 2 bugs + refactor em `rotate.sh` e `verify.sh` | 29 | 50K | 241.6 | sim |

Decisões:

- **Tarefa c entrou na faixa de primeira.** Fica como está.
- **Tarefa d: cortar o bug 3 não mudou nada** (49 → 48 turnos): o custo está no refactor, não nos bugs. A rodada
  3 limita o refactor aos dois scripts que os bugs tocam: 29 turnos e 242 s, dentro da faixa de turnos; o
  contexto final (50K) fica abaixo do piso de 60K. Com as três rodadas usadas, a tarefa d entra nas filas com
  esse prompt: a faixa obtida é 29 turnos / 50K / 242 s no Splash. O par c+d continua com `--max-turns 60`.
- `num_turns` conta turnos da sessão principal (assistente + usuário); os `req-*` têm ~0.65 request por turno.

## Smoke dos subagentes (`rc2s`, par c+d, Splash)

| sessão | wall_s | turnos (principal) | contexto final | task_done | `parallel_agent_calls` | `subagents_spawned` |
|---|---:|---:|---:|---|---:|---:|
| c | 668.9 | 17 | 40K | sim | 1 | 2 |
| d (prompt da rodada 3) | 789.1 | 24 | 52K | sim | 1 | 2 |

Par: 65 requests, **`max_concurrent` 6** (duas sessões + dois Explore cada), 25 turnos de prefill (cada subagente
começa frio), TTFT quente p50 1.7 s / p90 5.6 s, tok/s quente p50 96.6 / mín 14.3, zero erros HTTP. O N real
com subagentes é 6 streams (Review Focus 3); o report escreve esse número. A sessão principal faz menos turnos e
termina com menos contexto que a solo porque a exploração vai para os subagentes.

`parallel_agent_calls` precisou de correção: o stream-json do Claude Code emite um evento `assistant` por bloco
de conteúdo, então os dois `Agent` de uma mesma mensagem chegam em dois eventos com o mesmo `message.id`. A
contagem agrupa por `message.id` e ignora as mensagens dos próprios subagentes (`parent_tool_use_id`). Os
`cc-rc2scal1-*.json` foram recontados com a mesma lógica (0 → 1).
