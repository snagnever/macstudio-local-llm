# Etapa 2 — duas sessões de Claude Code no Splash 1.5.0

Rig: Mac Studio M4 Max 128 GB, 2026-10-29. Servidor: braço `k2c1` (Swift 1.5 GGUF `IQ4_XS` `0142554` no Splash 1.5.0, `--max-context 131072`, `--decode-share` no default 0.5). O servidor sobe de novo a cada rep. Claude Code 2.1.292 com `claude -p`, `CLAUDE_CODE_EFFORT_LEVEL=xhigh`, e o mesmo modelo como modelo principal e modelo rápido. As tarefas são as da campanha anterior: `task-a` (flag nova num CLI Python, com teste) e `task-b` (2 bugs num script bash, com 2 testes).

O smoke (`claude -p ping`) respondeu com HTTP 200. O `/v1/models` lista os efforts aceitos ([splash-150-models.json](splash-150-models.json)); `xhigh` está na lista.

## Resultado

As duas sessões juntas funcionam: zero erros, zero recusas, swap Δ 0 e todas as tarefas feitas. Cada sessão leva 1.36–1.60× o tempo dela sozinha. Cinco de seis sessões ficam no gate de 1.5×; a `task-b` da rep 1 fica em 1.60×. O par termina em 61.7 s em média. As duas tarefas em sequência, uma sessão de cada vez, levam 81.5 s. Rodar as duas sessões juntas ganha 24% do tempo total.

## Tabela

| braço | tarefa | rep | wall_s | ÷ controle | num_turns | tokens de entrada | is_error | task_done | erros no log | swap Δ |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|
| kcc1 | a | 1 | 41.4 | — | 10 | 146K | false | true | 0 | 0.00 |
| kcc1 | a | 2 | 40.5 | — | 10 | 146K | false | true | 0 | 0.00 |
| kcc1 | b | 1 | 40.5 | — | 6 | 82K | false | true | 0 | 0.00 |
| kcc1 | b | 2 | 40.5 | — | 6 | 102K | false | true | 0 | 0.00 |
| kcc2 | a | 1 | 55.6 | 1.36 | 10 | 146K | false | true | 0 | 0.00 |
| kcc2 | b | 1 | 64.7 | 1.60 | 6 | 104K | false | true | 0 | 0.00 |
| kcc2 | a | 2 | 60.7 | 1.48 | 10 | 146K | false | true | 0 | 0.00 |
| kcc2 | b | 2 | 57.6 | 1.42 | 6 | 103K | false | true | 0 | 0.00 |
| kcc2 | a | 3 | 59.7 | 1.46 | 11 | 124K | false | true | 0 | 0.00 |
| kcc2 | b | 3 | 57.6 | 1.42 | 6 | 102K | false | true | 0 | 0.00 |

Controle: média do `kcc1` por tarefa (a: 41.0 s; b: 40.5 s). "Erros no log" conta linhas de erro, recusa ou `streaming error` no log do Splash. Wired peak: 105.7–106.0 GB com uma sessão, 106.8–107.0 GB com duas. O Splash reserva a memória do KV no boot, por isso o pico quase não muda com a segunda sessão.

## Comparação com o mlx-serve 26.10.1 (campanha anterior, 2026-10-18)

| | mlx-serve 26.10.1 | Splash 1.5.0 |
|---|---:|---:|
| `task-a` sozinha | 75.4 s | 41.0 s |
| `task-b` sozinha | 62.2 s | 40.5 s |
| cada sessão do par ÷ sozinha | 1.84–2.36× | 1.36–1.60× |
| par (média, as duas terminam) | ~148 s | 61.7 s |
| as duas em sequência | ~138 s | 81.5 s |
| par ÷ sequência | 1.07 (perde) | 0.76 (ganha) |

O número de turnos e de tokens de cada tarefa fica igual nos dois servidores (a: 10–11 turnos; b: 6 turnos). O Claude Code manda prompts de ~20K tokens com quase tudo em cache. No log do Splash, 8 dos 59 requests leem 17–19K tokens novos (o começo de uma sessão). A mediana é 575 tokens novos por request. Com prefill curto, o batch do decode ganha, como no `k2c2` a 32K (Etapa 1).

## Veredito

**Aprovado no funcional, aprovado com aviso no gate de tempo.** Cinco de seis sessões ficam em até 1.5× o controle; uma fica em 1.60×. No uso real de Claude Code, o Splash 1.5.0 é o primeiro servidor deste rig em que duas sessões juntas terminam antes das duas em sequência. Cada tarefa sozinha também leva ~40% menos tempo que no mlx-serve 26.10.1.

A Etapa 1 sintética reprova as duas sessões no Splash. A diferença é o tamanho do prefill: a Etapa 1 lê 32K–128K de prompt frio ou mutado por turno, e o Claude Code lê poucas centenas de tokens novos por turno, fora o primeiro.

## Sessão interativa

Não rodou. Para testar: `bash ../flashnext-concurrency-2026-10/scripts/run-claude-pair.sh --interactive-env` imprime o `export` para colar em duas janelas de `claude`, com o Splash na 8585.
