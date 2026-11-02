# Terminal-Bench 2.1 — `w1z` (2026-10-30)

O `w1z` é o Swift 1.5 MLX 4.7bpw (`Dankpaws` `13839b7`) no mlx-serve 26.10.3, o daily driver na porta 11234. O harbor rodou no MacBook (`run-tbench-remote.sh`, agente `terminus-2`, `-n 1`, timeout do agente 1.0×, build 3.0×), contra o rig. Perfil t1: `reasoning_effort` xhigh, `temperature` 1.0, `top_p` 0.95, `top_k` 20. As configurações são as mesmas do [`k2a`](tbench21-k2a.md).

## Resultado

**65.2% (58 de 89).**

| resultado | tarefas |
|---|---:|
| reward 1.0 | 49 |
| reward 1.0 com timeout do agente | 9 |
| reward 0 sem timeout | 2 |
| reward 0 com timeout do agente | 29 |
| erro de ambiente (Docker, build, rede) | 0 |

- Os 38 erros do harbor são todos `AgentTimeoutError`. Nenhuma tarefa da tabela falhou por causa do ambiente.
- Uma tarefa com timeout ainda passa quando o agente já deixou a solução pronta antes do corte: `circuit-fibsqrt`, `cobol-modernization`, `headless-terminal`, `mailman`, `model-extraction-relu-logits`, `path-tracing`, `path-tracing-reverse`, `pytorch-model-cli` e `torch-tensor-parallelism`.
- Reward 0 sem timeout: `count-dataset-tokens` e `video-processing`.

## Comparação pareada com o `k2a`

As 89 tarefas são as mesmas nos dois braços. O `k2a` passa 57 e o `w1z` passa 58.

| | tarefas |
|---|---|
| só o `k2a` passa | `caffe-cifar-10`, `crack-7z-hash`, `polyglot-rust-c`, `write-compressor` |
| só o `w1z` passa | `code-from-image`, `git-multibranch`, `mailman`, `sam-cell-seg`, `sanitize-git-repo` |

São 9 tarefas discordantes, 4 contra 5. Com `-n 1`, essa diferença de uma tarefa não separa os dois braços.

## Tempo

- Tempo ativo, somado por tarefa: 30.8 h (`k2a`: 30.0 h). Mediana de 15.6 min por tarefa, máximo de 84 min.
- O agente ocupa ~92% do tempo. As tarefas com timeout ocupam 62% do tempo do agente.
- A mediana da latência das chamadas, por tarefa, é 11.8 s (`k2a`: 9.8 s).
- De ponta a ponta, o job rodou de 28/10 13:19 a 30/10 13:48 (CET), com duas paradas. Ambas foram para a campanha de concorrência do Splash, de outra sessão:
  - **Primeira pausa**, de 29/10 09:54 a 23:47, a pedido da outra sessão. A tarefa em curso (`query-optimize`) foi descartada e rodou de novo.
  - **Segunda pausa**, de 30/10 00:59 a 04:30. A outra sessão parou o driver da 11234 às 00:58 sem aviso. A tarefa `install-windows-3.11` falhou com `ConnectionRefused` e a `polyglot-c-py` ficou incompleta. As duas foram movidas para `logs/tb21-w1z-partial/` e rodaram de novo com `harbor job resume`.

## Tokens

| métrica | total |
|---|---:|
| tokens de entrada | 72.7 M |
| dos quais lidos do cache | 70.0 M |
| tokens de saída | 2.83 M |
| chamadas à API | 2015 |

A tabela por tarefa fica em [tbench21-w1z-tasks.csv](tbench21-w1z-tasks.csv). Ela tem reward, timeout, minutos por fase, tokens, episódios e a mediana da latência das chamadas. O `scripts/export_tbench.py w1z` gera a tabela a partir do job do harbor. As três tarefas descartadas nas pausas não entram nela; as novas execuções delas entram.

## Memória do rig

O `w1z` rodou no daily driver, fora de um hold do `run-arm.sh`, e por isso não tem amostrador de memória. Não há medida de wired, compressor ou swap para este run.
