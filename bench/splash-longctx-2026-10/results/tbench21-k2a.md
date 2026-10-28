# Terminal-Bench 2.1 — `k2a` (2026-10-28)

O `k2a` é o Swift 1.5 GGUF IQ4_XS (`ukisai` `0142554`) no Splash 1.4.0, com `--verify-rows auto`, KV int8 e `--max-context 262144`. O harbor rodou no MacBook (`run-tbench-remote.sh`, agente `terminus-2`, `-n 1`, timeout do agente 1.0×, build 3.0×), contra o rig na porta 8585. Perfil t1: `reasoning_effort` xhigh, `temperature` 1.0, `top_p` 0.95, `top_k` 20.

## Resultado

**64.0% (57 de 89).**

| resultado | tarefas |
|---|---:|
| reward 1.0 | 50 |
| reward 1.0 com timeout do agente | 7 |
| reward 0 sem timeout | 6 |
| reward 0 com timeout do agente | 26 |
| erro de ambiente (Docker, build, rede) | 0 |

- Os 33 erros do harbor são todos `AgentTimeoutError`. Nenhuma tarefa falhou por causa do ambiente.
- Uma tarefa com timeout ainda passa quando o agente já deixou a solução pronta antes do corte: `build-pmars`, `cobol-modernization`, `financial-document-processor`, `headless-terminal`, `path-tracing-reverse`, `pytorch-model-recovery` e `write-compressor`.
- Reward 0 sem timeout: `dna-assembly`, `filter-js-from-html`, `git-multibranch`, `raman-fitting`, `sam-cell-seg` e `sanitize-git-repo`.

## Tempo

- Tempo ativo, somado por tarefa: 30.0 h. Mediana de 15.5 min por tarefa, máximo de 102 min.
- O agente ocupa ~90% do tempo. As tarefas com timeout ocupam metade do tempo do agente.
- De ponta a ponta, o job rodou de 26/10 14:11 a 28/10 13:15 (CET), com duas paradas:
  - **Queda da rede**, de ~21:20Z em 26/10 até 08:49 em 27/10. A VPN NordVPN ligada no MacBook derrubou o Tailscale, e 28 tarefas falharam sem chegar ao modelo. Essas tarefas foram movidas para `logs/tb21-k2a-outage/` e rodaram de novo com `harbor job resume`. O rig não caiu.
  - **Pausa**, de 10:23 a 15:51 em 27/10, a pedido do usuário, para os testes t6 e t7 de outra sessão. A tarefa em curso (`cobol-modernization`) foi descartada e rodou de novo.

## Tokens

| métrica | total |
|---|---:|
| tokens de entrada | 89.2 M |
| dos quais lidos do cache | 84.6 M |
| tokens de saída | 2.91 M |
| chamadas à API | 2120 |

A tabela por tarefa fica em [tbench21-k2a-tasks.csv](tbench21-k2a-tasks.csv). Ela tem reward, timeout, minutos por fase, tokens, episódios e a mediana da latência das chamadas. O `scripts/export_tbench.py <arm>` gera a tabela a partir do job do harbor. As 28 tarefas da queda da rede não entram nela.

## Memória do rig

O amostrador do segundo hold (27/10 11:49 a 28/10 09:18, hora do rig) cobre as 68 tarefas finais. O primeiro hold gravou no mesmo arquivo, e esse arquivo foi sobrescrito.

| métrica | pico |
|---|---:|
| wired | 116.7 GB |
| compressor | 1.5 GB |
| folga (128 − wired − compressor) | 9.8 GB |
| swap usado | 2.05 GB (sem mudança durante o run) |

A folga fica acima do mínimo de 2 GB.
