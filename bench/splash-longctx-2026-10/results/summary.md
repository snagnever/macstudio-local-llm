# Splash até 1M — resumo da campanha (2026-11-01)

**O Swift 1.5 GGUF IQ4_XS no Splash 1.4.0 (`k2a`) serve 512K e 1M com velocidade, folga e qualidade aceitáveis.** O launcher é `tools/scripts/serve-flashnext-splash.sh [256k|512k|1m]`. No Terminal-Bench 2.1, o `k2a` empata com o driver diário (`w1z`, Swift 1.5 MLX no mlx-serve 26.10.3): 57/89 contra 58/89. O driver diário não mudou: a troca fica com o usuário.

Rig: Mac Studio M4 Max 128 GB. Runbook: [plan.md](../plan.md). Contexto 1M = 1000000 tokens.

## Como o `T_turno`, o cache e o prefill do Splash crescem de 8K a 1M?

`T_turno` (decode em tok/s), 3 reps, exceto onde a nota diz outra coisa:

| banda | w1z (mlx-serve) | k1a (Flash Next base, Splash) | k2a (Swift, Splash) | k3r (GSQ, Splash 1.4.1) |
|---|---:|---:|---:|---:|
| 8K | 7.7 s (84) | 7.2 s (89) | 6.2 s (107) | 5.9 s (113) |
| 32K | 8.0 s (82) | 6.8 s (98) | 6.0 s (113) | — |
| 128K | 8.9 s (74) | 6.8 s (99) | 6.3 s (108) | — |
| 256K | 9.2 s (74), 1 rep | 7.0 s (99) | 6.6 s (106) | 6.1 s (112) |
| 512K | 12.7 s (57), `w1zq4` | 7.4 s (94) | 6.7 s (107) | fora do escopo |
| 1M | falha (`PrefillDoesNotFit`) | 10.5 s (65), 1 rep | 9.3–9.4 s (75–77), 2 reps | fora do escopo |

- O ganho do Splash vem do decode. O cold TTFT empata com o mlx-serve: 351 s a 256K, 745 s a 512K e 25.5 min a 1M no `k2a`.
- O hit do cache fica em 0.99–1.00 de 128K para cima, nos dois runtimes.
- **Mutação no meio do prompt:** o Splash refaz o prefill inteiro (hit 0) em todas as bandas. O mlx-serve reaproveita o prefixo (hit 0.44–0.45). A 1M, isso custa 25 min no Splash.
- **Ramificação:** um pedido que diverge antes do último estado GDN salvo também refaz o prefill no Splash ([etapa4](etapa4-quality.md)).
- O mlx-serve 26.10.3 sobe a 1M, mas recusa 2 a 3 das 5 requisições seguintes com `PrefillDoesNotFit` ([etapa6-n2z-1m](etapa6-n2z-1m.md)).

Fontes: [etapa1](etapa1-native.md), [etapa2](etapa2-512k.md), [etapa3](etapa3-1m.md), [etapa5](etapa5-gsq-mlx-serve.md).

## Que parâmetros do Splash dão 512K e 1M com folga de memória?

| perfil | flags | T_turno | folga | aceitável |
|---|---|---:|---:|---|
| `k2a` 524288 | `--max-context 524288 --verify-rows auto` (KV int8) | 6.7 s | 10.1 GB | **sim** |
| `k2a` 1000000 | `--max-context 1000000 --verify-rows auto` (KV int8) | 9.3–9.4 s | 16.9 GB | **sim** |
| `k2ab` 524288 | `k2a` + `--kv-format bf16` | 7.8 s | 16.7 GB | não: 1.16 × o `k2a` |
| `w1zq4` 524288 (mlx-serve) | `--kv-quant 4`, YaRN 2.0 | 12.7 s | 3.8 GB | sim, perto do limite |

- A 1M, o Splash põe parte do KV no cache em SSD. A folga sobe, mas o decode cai de 107 para 76 tok/s.
- O 1M passou, então a escada de recuo (`k2as`, 786432) não rodou.

Fonte: [params-512k-1m](params-512k-1m.md).

## O YaRN do Splash a 512K e a 1M mantém a qualidade do contexto nativo?

Sim, dentro do ruído de uma rodada. Bateria t1, `reasoning_effort` xhigh, HumanEval com os imports do prompt:

| suíte | w1z 262144 | k2a 262144 | k2a 524288 | k2a 1000000 |
|---|---:|---:|---:|---:|
| HumanEval | 158/164 | 158 · 159/164 | 156/164 | 155 · 158/164 |
| GPQA | 43/50 | 41/50 | 43/50 | 43/50 |
| LiveCodeBench | 47/50 | 47/50 | 47/50 | 47/50 |
| IF | 19/20 | 19/20 | 18/20 | 19/20 |
| jdhodges | 34/40 | 37/40 | 37/40 | 36/40 |
| veerman | 10/12 | 10/12 | 10/12 | 9/12 |
| longctx (banda do servidor) | 8/8 | 8/8 | 8/8 | 8/8 |

- A 1M, a regra G1 falhou no HumanEval estrito por 1 questão (média de 2 rodadas). O usuário aceitou o resultado como ruído.
- Tool calls com `frequency_penalty` 0: 20/20 sessões no `w1z` e no `k2a`.

Fonte: [etapa4](etapa4-quality.md).

## O Splash com o Swift passa no Terminal-Bench 2.1 como o `w1z`?

Sim. 89 tarefas, agente `terminus-2`, uma tentativa por tarefa, contexto 262144:

| braço | runtime | aprovadas |
|---|---|---:|
| `w1z` (Swift 1.5 MLX 4.7bpw) | mlx-serve 26.10.3 | 58/89 (65.2%) |
| `k2a` (Swift 1.5 GGUF IQ4_XS) | Splash 1.4.0 | 57/89 (64.0%) |
| `k3f` (GSQ-RCO-Coder GGUF IQ1_M) | Splash 1.5.0 | 52/89 (58.4%) |

Nenhum par tem diferença significante no McNemar exato (p ≥ 0.18). Fonte: [etapa6-tbench21](etapa6-tbench21.md).

## GSQ-RCO-Coder

| braço | runtime | T_turno 256K | wired 256K | GPQA | código (HE / LCB) |
|---|---|---:|---:|---:|---|
| `r1z` (pack MLX) | mlx-serve 26.10.3 | 11.0 s | 89.3 GB | 31/50 | 152 / 46 |
| `k3ma` (GGUF IQ1_M) | Splash do `main` `3135ab4` | 6.3 s | 79.9 GB | — | — |
| `k3r` (GGUF IQ1_M) | Splash 1.4.1 | 6.1 s | 79.8 GB | 25/50 | 149 / 48 |

O GSQ é o braço mais rápido e o de menor memória da campanha, mas falha no G1 do GPQA (43/50 no `w1z`). No Terminal-Bench 2.1, ele fica 5–6 tarefas abaixo dos braços Swift. Fonte: [etapa5](etapa5-gsq-mlx-serve.md).

## Recomendações

1. **512K e 1M:** usar o `k2a` com `serve-flashnext-splash.sh 512k` ou `1m`. O mlx-serve não serve 1M neste rig.
2. **Driver diário:** o `k2a` a 262144 tem `T_turno` 0.72 × o do `w1z` e a mesma qualidade, mas refaz o prefill numa mutação no meio do histórico. A troca fica com o usuário.
3. **GSQ-RCO-Coder:** só para código, quando a memória importa. Não serve como driver geral, por causa do GPQA.

## Desvios do plano

| plano | o que rodou | motivo |
|---|---|---|
| `k3`, `k3a`, `k3ab` nos Tasks 1 a 4 | não rodaram | o Splash 1.4.0 recusa o GGUF do GSQ (#527) ([etapa0-k3-load](etapa0-k3-load.md)) |
| GSQ até 1M (`r1zy`) | GSQ só até 256K | decisão do usuário (25/10) |
| Task 5b com Tasks 1 a 4 e controle do `k2a` na release nova | `k3ma` (build do `main`) e `k3r` (1.4.1) só a 8K e 256K, e a bateria do `k3r` a 262144; o controle do `k2a` não rodou | pedidos do usuário; o `k3r` repete o `k3ma` |
| "não instalar outra versão no meio" | Splash 1.4.1 e 1.5.0 instalados ao lado da 1.4.0 | os braços GSQ precisavam da #561; os braços Swift continuaram na 1.4.0 |
| `k3a` no Terminal-Bench 2.1 | `k3f` (GSQ no Splash 1.5.0); o `r1z` saiu | emenda de 30/10 (pedido do usuário) |
| — | `k2m`: o Splash recusa o Swift 1.5 MLX | pedido do usuário; Flash-Next só carrega de GGUF |
| — | `t6`, `t7`: iQ no mlx-serve 26.10.3 e 1M no mlx-serve | pedidos do usuário (27/10) |
| G1 do HumanEval a 1M | aceito como ruído | decisão do usuário |

As pausas do Terminal-Bench para outras campanhas estão nos reports de cada braço.
