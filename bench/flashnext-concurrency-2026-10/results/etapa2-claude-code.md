# Etapa 2 — duas sessões de Claude Code num driver

Rig: Mac Studio M4 Max 128 GB, 2026-10-18. Driver: braço `w1c1` (Swift 1.5 no mlx-serve 26.10.1, `--ctx-size 131072`, `--max-concurrent` no default 1, prefix cache 16 GB). O servidor sobe de novo a cada rep. Claude Code 2.1.292 com `claude -p`, `CLAUDE_CODE_EFFORT_LEVEL=xhigh`, e o mesmo modelo como modelo principal e modelo rápido. Tarefas fixas: `task-a` (flag nova num CLI Python, com teste) e `task-b` (2 bugs num script bash, com 2 testes).

## Resultado

As duas sessões juntas funcionam: zero erros, zero recusas, swap Δ 0 e todas as tarefas feitas. Mas cada sessão leva 1.84–2.36× o tempo dela sozinha, acima do gate de 1.5×. O par termina em ~148 s em média. As duas tarefas em sequência, uma sessão de cada vez, levam ~138 s. Rodar as duas sessões juntas não ganha tempo total; perde ~7%.

## Tabela

| braço | tarefa | rep | wall_s | ÷ controle | num_turns | is_error | task_done | http errs | swap Δ |
|---|---|---:|---:|---:|---:|---|---|---:|---:|
| cc1 | a | 1 | 78.9 | — | 10 | false | true | 0 | 0.00 |
| cc1 | a | 2 | 71.9 | — | 9 | false | true | 0 | 0.00 |
| cc1 | b | 1 | 62.7 | — | 6 | false | true | 0 | 0.00 |
| cc1 | b | 2 | 61.7 | — | 6 | false | true | 0 | 0.00 |
| cc2 | a | 1 | 145.6 | 1.93 | 8 | false | true | 0 | 0.00 |
| cc2 | b | 1 | 127.3 | 2.05 | 6 | false | true | 0 | 0.00 |
| cc2 | a | 2 | 138.5 | 1.84 | 9 | false | true | 0 | 0.00 |
| cc2 | b | 2 | 146.6 | 2.36 | 6 | false | true | 0 | 0.00 |
| cc2 | a | 3 | 150.7 | 2.00 | 10 | false | true | 0 | 0.00 |
| cc2 | b | 3 | 139.5 | 2.24 | 6 | false | true | 0 | 0.00 |

Controle: média do `cc1` por tarefa (a: 75.4 s; b: 62.2 s). `http errs` conta `PrefillDoesNotFit`, `streaming error` e `error.` no log do servidor; o log do 26.10.1 não registra o status HTTP. Wired peak: 85–87 GB com uma sessão, 90–91 GB com duas.

O número de turnos e de tokens de cada tarefa não muda com a concorrência (a: 8–10 turnos, ~125–146K tokens de entrada; b: 6 turnos, ~102K). O tempo a mais vem só da divisão do decode e da espera de prefill, como na Etapa 1.

## Sessão interativa

Não rodou nesta execução. Fica para o usuário: `bash scripts/run-claude-pair.sh --interactive-env` imprime o `export` para colar em duas janelas de `claude`.

## Veredito

**Reprovado no gate de tempo (≤ 1.5× o controle), aprovado no funcional.** Duas sessões de Claude Code dividem o driver sem erro, mas cada uma fica ~2× mais lenta, e o par não termina antes da soma das duas em sequência. O driver aceita duas sessões; não há ganho em rodar as duas juntas.
