# Terminal-Bench 2.1 — `k3f` (2026-11-01)

O `k3f` é o GSQ-RCO-Coder GGUF IQ1_M (`ISTA-DASLab` `bba8885`) no Splash 1.5.0, com `--verify-rows auto`, KV int8 e `--max-context 262144`. É o `k3a` no release 1.5.0. Ele substitui o `r1z` (emenda de 30/10 no [plan.md](../plan.md)), porque o 1.5.0 recusa o pack MLX do Flash-Next. O harbor rodou no MacBook (`run-tbench-remote.sh`, agente `terminus-2`, `-n 1`, timeout do agente 1.0×, build 3.0×), contra o rig na porta 8585. Perfil t1: `reasoning_effort` xhigh, `temperature` 1.0, `top_p` 0.95, `top_k` 20. As configurações são as mesmas do [`k2a`](tbench21-k2a.md) e do [`w1z`](tbench21-w1z.md).

## Resultado

**58.4% (52 de 89).**

| resultado | tarefas |
|---|---:|
| reward 1.0 | 45 |
| reward 1.0 com timeout do agente | 7 |
| reward 0 sem timeout | 4 |
| reward 0 com timeout do agente | 33 |
| erro de ambiente (Docker, build, rede) | 0 |

- Os 40 erros do harbor são todos `AgentTimeoutError`. Nenhuma tarefa da tabela falhou por causa do ambiente.
- Uma tarefa com timeout ainda passa quando o agente já deixou a solução pronta antes do corte: `cobol-modernization`, `financial-document-processor`, `headless-terminal`, `llm-inference-batching-scheduler`, `mailman`, `path-tracing` e `torch-tensor-parallelism`.
- Em `adaptive-rejection-sampler` e `polyglot-rust-c`, nenhuma chamada terminou. A primeira chamada raciocinou sem parar: 53,302 e 49,728 tokens de saída em 10 min, a 83–89 tok/s, segundo o log do Splash. O cliente cancelou a chamada e a enviou de novo, e o timeout do agente cortou a segunda. O servidor não travou.
- Reward 0 sem timeout: `bn-fit-modify`, `filter-js-from-html`, `nginx-request-logging` e `query-optimize`.

## Comparação pareada

As 89 tarefas são as mesmas nos três braços.

| braço | aprovadas |
|---|---:|
| `k2a` (Swift 1.5 GGUF IQ4_XS, Splash 1.4.0) | 57 |
| `w1z` (Swift 1.5 MLX 4.7bpw, mlx-serve 26.10.3) | 58 |
| `k3f` (GSQ-RCO-Coder IQ1_M, Splash 1.5.0) | 52 |

Contra o `k2a`:

| | tarefas |
|---|---|
| só o `k2a` passa (10) | `bn-fit-modify`, `circuit-fibsqrt`, `dna-insert`, `nginx-request-logging`, `path-tracing-reverse`, `polyglot-rust-c`, `protein-assembly`, `pytorch-model-cli`, `sqlite-db-truncate`, `write-compressor` |
| só o `k3f` passa (5) | `count-dataset-tokens`, `git-multibranch`, `mailman`, `rstan-to-pystan`, `sam-cell-seg` |

Contra o `w1z`, são 10 tarefas só do `w1z` e 4 só do `k3f` (`caffe-cifar-10`, `count-dataset-tokens`, `crack-7z-hash`, `rstan-to-pystan`).

- Os três braços passam 45 tarefas, e nenhum passa 25.
- Contra o `k2a`, a diferença é 10 contra 5. No teste exato de McNemar, p ≈ 0.30. Com `-n 1`, o `k3f` fica abaixo dos dois braços Swift, mas a amostra não separa os braços com confiança.

## Tempo

- Tempo ativo, somado por tarefa: 31.2 h (`k2a`: 30.0 h, `w1z`: 30.8 h). Mediana de 15.7 min por tarefa, máximo de 79 min.
- O agente ocupa ~93% do tempo. As tarefas com timeout ocupam 62% do tempo do agente.
- A mediana da latência das chamadas, por tarefa, é 12.2 s nas 87 tarefas com chamadas completas (`k2a`: 9.8 s, `w1z`: 11.8 s).
- De ponta a ponta, o job rodou de 30/10 13:51 a 01/11 04:00 (CET), com uma parada:
  - **Pausa**, de 30/10 15:10 a 22:06, para a janela de rig da campanha `claude-code-concurrency` de outra sessão, a pedido do usuário. O harbor parou logo depois que a `schemelike-metacircular-eval` terminou. A `kv-store-grpc` tinha começado 14 s antes do corte e gravou um `result.json` com `CancelledError`. Ela foi movida para `logs/tb21-k3f-partial/` e rodou de novo com `harbor job resume`, numa nova hold do `k3f`.

## Tokens

| métrica | total |
|---|---:|
| tokens de entrada | 86.1 M |
| dos quais lidos do cache | 80.7 M |
| tokens de saída | 3.73 M |
| chamadas à API | 1999 |

O `k3f` gera mais tokens de saída que o `k2a` (2.91 M) e o `w1z` (2.83 M), com um número parecido de chamadas.

A tabela por tarefa fica em [tbench21-k3f-tasks.csv](tbench21-k3f-tasks.csv). Ela tem reward, timeout, minutos por fase, tokens, episódios e a mediana da latência das chamadas. O `scripts/export_tbench.py k3f` gera a tabela a partir do job do harbor. A tarefa cancelada na pausa não entra nela; a nova execução dela entra.

## Memória do rig

O amostrador da segunda hold (`logs/k3f-262144-t1.0-hold-mem.jsonl`, 30/10 18:08 a 01/11 00:01, hora do rig) cobre as 86 tarefas depois da pausa. A primeira hold gravou no mesmo arquivo, e esse arquivo foi sobrescrito.

| métrica | pico |
|---|---:|
| wired | 116.9 GB |
| compressor | 2.6 GB |
| folga (128 − wired − compressor) | 9.1 GB |
| swap usado | 1.95 GB (sem mudança durante o run) |
| RSS do servidor | 78.0 GB |

A folga fica acima do mínimo de 2 GB.
