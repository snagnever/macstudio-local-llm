# Splash 1.6.1 contra 1.5.0 — resumo da campanha (2026-11-11 a 12)

**O launcher do Splash no rig passa para a 1.6.1, com PLE `auto`.** As Tasks 1 a 6 passam no modo `auto`, e a Task 7 não mostra regressão. A regressão de duas sessões de 256K da 1.6.0 some: o pior stream fica 3.5% acima da 1.5.0, contra 65% na 1.6.0, e a espera por memória cai de 30 s para 0. A 1.6.1 também mantém os ganhos da 1.6.0 sob limite de memória e nas sessões do Claude Code, e libera de 22 a 29 GB de RAM.

Pesos: `k2` = Swift 1.5 `IQ4_XS` `0142554`. Braços: `k2f` = 1.5.0 (controle), `k2h` = 1.6.1 com PLE `auto`, `k2hp` = 1.6.1 com `--ple-memory off`. Regras de decisão: [plan.md](../plan.md#regras-de-decisão).

## Respostas

| # | pergunta | veredito | resultado | fonte |
|---|---|---|---|---|
| 1 | O pack carrega, e a troca de versão quebra algum cliente? | **passa** | Os 5 braços do smoke sobem. A 1.5.0 sobe com `--offline` depois da 1.6.1, sem perder o snapshot. C1 a C6, proxy e restart do engine passam. A C7 se comporta como na 1.5.0 e na 1.6.0. | [etapa0](etapa0-smoke.md), [etapa1](etapa1-contrato.md) |
| 2 | A 1.6.1 mantém o `T_turno` de um stream, nos dois modos de PLE? | **passa nos dois modos** | Razão de 1.000 a 1.017 com `auto` e 1.000 com `off`, a 32K, 128K e 256K. A 1M, o decode sobe para 102 tok/s, contra 71–77 tok/s na splash16. | [etapa2](etapa2-um-stream.md) |
| 3 | A regressão de duas sessões longas some? | **passa nos dois modos** | `k2c2LL` a 256K: razão 1.035 com `auto` e 0.998 com `off`. `k2c2a` a 128K: 1.080 e 1.034. `claim_wait` máximo de 0 s com `auto` e até 2.9 s com `off`, contra 30 s na 1.6.0. | [etapa3](etapa3-concorrencia.md) |
| 4 | As sessões do Claude Code mantêm o ganho da 1.6.0? | **passa** | Wall do par 0.967 × no `rc2` e 0.670 × no `rc2s`. Warm TTFT p50 0.64 × e 0.50 ×. As 20 sessões cumprem a tarefa. | [etapa4](etapa4-claude-code.md) |
| 5 | Sob limite de memória, a 1.6.1 continua sem stall? | **passa** | Com `--max-memory 64G`, o maior gap fica em 4.5 e 4.9 s, contra 60.8 e 87.8 s na 1.5.0. A 1.6.1 faz 35% mais requests e lê 3.3 vezes menos do SSD. | [etapa5](etapa5-pressao.md) |
| 6 | A qualidade continua igual? | **passa** | Bateria 300/336, contra 293 e 302 da 1.5.0 nas passadas W1 e W2. G1 passa nas 6 suítes. Tool calls 20/20 no `fp0` e 16/20 no `fp1`. Longctx 16/16. | [etapa6](etapa6-qualidade.md) |
| 7 | Uma carga de agente de 4 h continua estável? | **estável, sem regressão** | Sonda fim / antes de 1.09, com o pool de KV no teto. 43 pares, 86/86 `task_done`, 0 erros. | [etapa7](etapa7-agente-4h.md) |

## Modo de PLE

| regra | `auto` | `off` |
|---|---|---|
| Task 2, `T_turno` ≤ 1.03 | passa (1.000–1.017) | passa (1.000) |
| Task 3, pior stream ≤ 1.10 | passa (1.035; 1.080) | passa (0.998; 1.034) |
| pior stream no `k2c2LL` | 16.63 s | 16.03 s |
| wired peak a 256K, um stream | 82.2 GB | 111.0 GB |

Os dois modos passam, e a diferença no `k2c2LL` fica dentro do empate de 5%. Pela regra do plano, o modo escolhido é **`auto`**, o padrão da 1.6.1, que não precisa de flag.

## Regra "Trocar o launcher"

| condição | resultado |
|---|---|
| Tasks 1 a 6 passam num mesmo modo de PLE | **sim**, com `auto` |
| Task 7 sem regressão | **sim** |
| **Decisão** | **o launcher passa para a 1.6.1** |

- **Launcher:** `tools/scripts/serve-flashnext-splash.sh` agora usa `splash-v1.6.1` sem `--ple-memory`. O teste `test_launcher_defaults_to_161` fixa isso. Para voltar à 1.5.0, use `FLASHNEXT_SPLASH_BIN=$HOME/.local/opt/qwen38/splash-v1.5.0/bin/splash`.
- **Servidor do usuário:** a porta 8585 voltou com o launcher novo às 17:28 de 12/11 (relógio do rig). `/health` responde `ok`, e `/v1/models` lista o `k2`.
- **Driver diário:** o `serve-flashnext-daily-driver.sh` (mlx-serve, porta 11234) não muda nesta campanha. A troca do driver diário fica com o usuário.

## Comparação com a 1.6.0 (splash16)

| medida | 1.5.0 | 1.6.0 | 1.6.1 |
|---|---:|---:|---:|
| pior stream `k2c2LL` 256K, razão contra a 1.5.0 do dia | 1.00 | 1.65 | 1.035 |
| `claim_wait` máximo no `k2c2LL` | – | 30.1 s | 0 s |
| maior gap sob 64G | 60.8–87.8 s | 1.1–2.5 s | 4.5–4.9 s |
| pares no soak de 4 h | 38 | 43 | 43 |
| wired peak a 256K, um stream | 111.0 GB | 111.0 GB | 82.2 GB |

A coluna da 1.6.0 vem da splash16, de outro dia. Na coluna da 1.5.0, os pares do soak vêm da splash16, e os outros valores vêm desta campanha. A razão do `k2c2LL` sempre compara com a 1.5.0 da mesma fila.

## O que não rodou

- **512K na 1.6.1:** o perfil `512k` do launcher não foi medido nesta campanha. Os números do comentário vêm da 1.4.0.
- **Terminal-Bench 2.1 do `k2h`:** fora da fila, como o plano prevê. Leva de 12 a 24 h.
- **Perfil `p` da Task 3 da splash16** na 1.6.1: fora da fila, como o plano prevê.

## Desvios do plano

- **Tasks 1 a 3:** rodaram numa fila só (`chain-t123`), que só começou depois que o smoke terminou com os 5 braços em `rc=0`.
- **Tags:** as Tasks 2 a 4 usam a posição na fila na tag (`p<N>`, `a<N>`, `o<N>`, `f<N>`, `h<N>`, `q<N>`) para separar os modos de PLE.
- **Task 1:** a C7 falha na 1.6.1 com o mesmo reuso de 320 tokens da 1.5.0 e da 1.6.0. Isso não conta como regressão.
- **Task 3:** o gate "no overlap" do `summarize_parallel.py` falha em todos os boots, também nos da 1.5.0. A regra do plano usa só o pior stream.
- **Task 5:** as respostas 400 `context_length_exceeded` da 1.6.1 vêm do gerador de carga e não contam como falha do servidor.
- **Task 6:** o longctx rodou as duas bandas num servidor de 262144. Os gates G2 do `summarize_ab.py` falham em 3 comparações e ficam só como observação. O usuário pediu para manter só tool calls e longctx, mas a bateria já tinha terminado.
- **Task 7:** rodou numa fila separada, depois do veredito da Task 6. A tabela por hora foi calculada ad hoc, como na splash16.
- **Task 8:** o launcher novo foi copiado para o worktree do rig antes do push, para religar a porta 8585.

Ledger com todas as decisões: `.superpowers/sdd/plan-splash161-2026-11/progress.md` (fora do git).
