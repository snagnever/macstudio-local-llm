# Etapa 6 — Terminal-Bench 2.1, três braços

O harbor rodou no MacBook contra o rig, com as mesmas configurações nos três braços: agente `terminus-2`, `-n 1`, timeout do agente 1.0×, build 3.0×, perfil t1 (`reasoning_effort` xhigh, `temperature` 1.0, `top_p` 0.95, `top_k` 20). Cada braço rodou as 89 tarefas do Terminal-Bench 2.1 com contexto de 262144.

| braço | pesos | runtime | aprovadas | taxa | tempo ativo | report |
|---|---|---|---:|---:|---:|---|
| `k2a` | Swift 1.5 GGUF IQ4_XS (`ukisai` `0142554`) | Splash 1.4.0 | 57/89 | **64.0%** | 30.0 h | [tbench21-k2a.md](tbench21-k2a.md) |
| `w1z` | Swift 1.5 MLX 4.7bpw (`Dankpaws` `13839b7`) | mlx-serve 26.10.3 | 58/89 | **65.2%** | 30.8 h | [tbench21-w1z.md](tbench21-w1z.md) |
| `k3f` | GSQ-RCO-Coder GGUF IQ1_M (`ISTA-DASLab` `bba8885`) | Splash 1.5.0 | 52/89 | **58.4%** | 31.2 h | [tbench21-k3f.md](tbench21-k3f.md) |

- Nenhuma tarefa das tabelas falhou por causa do ambiente. Todas as falhas do harbor são `AgentTimeoutError`. As tarefas que caíram por rede ou por parada do driver rodaram de novo (ver "Paradas").
- O `k3f` substitui o `r1z` (emenda de 30/10 no [plan.md](../plan.md)): o Splash 1.5.0 recusa o pack MLX do Flash-Next.
- O gate antigo de 32.6% vem do Terminal-Bench 2.0, não do 2.1. Ele não compara 1:1 com estes números. Os três braços ficam bem acima dele.

## Comparação pareada

| par | só o primeiro passa | só o segundo passa | p (McNemar exato) |
|---|---:|---:|---:|
| `k2a` × `w1z` | 4 | 5 | 1.00 |
| `k2a` × `k3f` | 10 | 5 | 0.30 |
| `w1z` × `k3f` | 10 | 4 | 0.18 |

Os três braços passam 45 tarefas, e nenhum passa 25.

- Os dois braços Swift empatam: GGUF IQ4_XS no Splash e MLX 4.7bpw no mlx-serve dão o mesmo resultado.
- O GSQ-RCO-Coder fica 5–6 tarefas abaixo dos braços Swift. Com `-n 1`, essa diferença não tem significância estatística, mas a direção é a mesma contra os dois.

## Paradas

- `k2a`: uma queda da rede (VPN no MacBook, 28 tarefas rodaram de novo) e uma pausa para os testes t6 e t7 de outra sessão.
- `w1z`: duas pausas para a campanha de concorrência do Splash. Uma tarefa caiu com `ConnectionRefused` quando a outra sessão parou o driver sem aviso. Ela rodou de novo.
- `k3f`: uma pausa para a janela de rig da campanha `claude-code-concurrency`. A tarefa cancelada no corte rodou de novo.

O `bench/stack-updates-2026-10/results/tbench-status.json` e o `tbench-status-mlx.json` guardam o placar final do `k3f` e do `w1z` para a página da campanha `flashnext-concurrency`, que os lê.

Em todos os casos, as tarefas incompletas ou inválidas saíram do job e rodaram de novo com `harbor job resume`. As tabelas por tarefa só têm execuções completas.
