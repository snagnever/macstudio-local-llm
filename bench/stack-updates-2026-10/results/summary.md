# Stack updates 2026-10-22 — resumo da campanha

Rig: Mac Studio M4 Max 128 GB. Referência: `w1` = Swift 1.5 MLX "4.7" (Dankpaws `13839b7`) no mlx-serve 26.10.1, o driver diário. Métrica: `T_turno` do `cache_probe.py`, 3 reps a 32K e 128K e 1 rep a 256K. Runbook em [`plan.md`](../plan.md). Nota de origem: [`research/rig-stack-updates-20261022.md`](../../../research/rig-stack-updates-20261022.md).

| teste | braço | `T_turno` / `w1` (32K · 128K · 256K) | qualidade (HumanEval · LCB) | tool calls (fp 0) | veredito | detalhe |
|---|---|---|---|---|---|---|
| 1 | `w1z` Swift 1.5 MLX, mlx-serve 26.10.3 | 1.00 · 1.02 · 0.93 | — | 20/20 | **passa** | [etapa1](etapa1-mlx-serve-26103.md) |
| 4 | `t6z` twyx iQ-MLX-6.6bpw, mlx-serve 26.10.3 | 1.26 × `n2z` (32K) | — | — | não adotar: swap 0.91 GB a 32K | [etapa4](etapa4-twyx66.md) |
| 5 | `k1a` Flash-Next base UD-IQ4_XS, Splash 1.4.0 | 0.85 · 0.78 · — | — | — | passa na velocidade; pesos diferentes do `w1` | [etapa5](etapa5-splash140.md) |
| 6 | `r1` GSQ-RCO-Coder, oMLX 0.7.2 | 1.31 · 1.40 · — | 154 · 45 (`w1` 141 · 46) | 20/20 | não adotar: lento | [etapa6](etapa6-gsq-coder.md) |
| 8 | `k2a` Swift 1.5 IQ4_XS, Splash 1.4.0 | **0.75 · 0.72 · 0.64** | 142 · 47 | **16/17** | não trocar ainda: falha nas tool calls | [etapa8](etapa8-splash-swift.md) |
| 9 | `r1z` GSQ-RCO-Coder, mlx-serve 26.10.3 | 1.10 · 1.12 · — | 154 · 45 (pesos do `r1`) | 20/20 | não adotar: 10% mais lento | [etapa9](etapa9-gsq-coder-mlx-serve.md) |

## Recomendações

1. **mlx-serve 26.10.3 no driver diário.** Ele empata com a 26.10.1 a 32K e 128K e é 7% mais rápido a 256K. Corrige a #912. Um harness que mande `frequency_penalty 1` (o Crush) recebe respostas finais degeneradas nas duas versões testadas da 26.10.3 (`w1z` 3/5 e `r1z` 5/5 sessões). A troca de `FLASHNEXT_BIN` em `tools/scripts/serve-flashnext-daily-driver.sh` fica com o usuário.
2. **Splash 1.4.0 com o Swift 1.5 GGUF é o próximo candidato a driver.** Ele é 25–36% mais rápido com a mesma qualidade, mas falhou em 1 de 5 sessões do probe de tool calls (turno 1 sem tool call). Antes de trocar, medir a taxa de falha com mais sessões, no `k2` e no `k2a`, e ler as respostas que vieram sem tool call.
3. **GSQ-RCO-Coder** só vale num perfil que precise de memória livre (68–78 GB no mlx-serve), não como driver.

## Desvios do plano

- O gh do rig não autentica numa sessão ssh. Os assets do mlx-serve e do Splash foram baixados no laptop, conferidos contra o digest publicado e copiados.
- O probe de tool calls passou de 1 sessão de 20 turnos para 5 sessões de 4 turnos. A versão de 20 turnos falha no turno 5 também na 26.10.1.
- Task 4: só a banda de 32K rodou. Swap e lentidão já decidiam o veredito.
- Task 5: o Splash 1.4.0 não carrega o GGUF dividido do ggml-org (shards na raiz). O teste usou o UD-IQ4_XS da Unsloth.
- Tasks 8 e 9 foram adicionados durante a campanha, a pedido do usuário.
- O driver diário ficou parado durante as filas e voltou com o mesmo comando (`results/daily-driver-cmd.txt`).
