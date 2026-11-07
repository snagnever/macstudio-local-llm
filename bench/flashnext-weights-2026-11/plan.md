# Pesos do Flash-Next: Unsloth V3.1, GSQ-RCO e Swift — runbook da campanha (2026-11-07)

> **Status (2026-11-07): na fila.** O usuário pediu os testes em 07/11. Nada rodou. Esta campanha começa depois da Task 7 da [splash16-2026-11](../splash16-2026-11/plan.md). Branch: `bench/splash16-2026-11`.

## Perguntas

1. O `UD-IQ3_XXS` V3.1 substitui o Swift 1.5 (`k2`) em qualidade, tokens e tempo por tarefa?
2. O `UD-IQ4_XS` V3.1 ganha do Swift 1.5 e do arquivo anterior do mesmo modelo base?
3. O GSQ-RCO `Q2_0` confirma, nesta medida, a posição que o gráfico da Unsloth mostra?
4. O GSQ-RCO-Coder `IQ1_M` serve como controle de arquivo pequeno?

A Unsloth afirma até 50% menos tokens, cerca de 15% mais acurácia e até 7% mais velocidade. O gráfico publicado mostra só acurácia, com ruído de cerca de 4 pontos.

## Braços

O sufixo `R` é a release do Splash: `g` (1.6.0) se a regra "Trocar o launcher" da splash16 passar, `f` (1.5.0) se não passar. Todos os braços usam a mesma release e as flags padrão.

| braço | peso | revisão | GB (Hugging Face) | papel |
|---|---|---|---:|---|
| `k2R` | ukisai Swift 1.5 `IQ4_XS` | `0142554` | no rig | referência Swift |
| `k1R` | Unsloth `UD-IQ4_XS`, 06/10 | `766911a` | no rig | referência base, antes do V3.1 |
| `k6R` | Unsloth `UD-IQ4_XS` V3.1 | `084c631` | 93.7 | teste 2 |
| `k5R` | Unsloth `UD-IQ3_XXS` V3.1 | `084c631` | 83.6 | teste 1 |
| `k4R` | ISTA GSQ-RCO `Q2_0` | `ed59f92` | 66.4 | teste 3 |
| `k3R` | ISTA GSQ-RCO-Coder `IQ1_M` | `bba8885` | no rig | teste 4 |

Conferido na API do Hugging Face em 07/11: os arquivos `UD-IQ4_XS` e `UD-IQ3_XXS` têm hashes diferentes entre `766911a` e `084c631`. Os commits depois de `814db05` só mudam o README.

## O que cada comparação isola

| comparação | o que muda |
|---|---|
| `k6R` contra `k1R` | só a receita de quantização |
| `k5R` contra `k6R` | só o nível de quantização |
| `k6R` contra `k2R` | fine-tune e receita |
| `k5R` contra `k2R` | fine-tune, receita e nível |
| `k1R` contra `k2R` | fine-tune, com quantizadores diferentes |

Nenhum braço separa o fine-tune da receita, porque o Swift não tem arquivo V3.1.

## Regras

- **Candidato a substituir o `k2R`:** G1 de `summarize_ab.py` nas duas passadas, tool calls ≥ `k2R` − 1 de 20, e mediana de tokens ou de tempo em `gpqa` e `livecodebench` pelo menos 10% menor. O `T_turno` a 262144 fica ≤ 1.03 × `k2R`.
- **Afirmação do V3.1:** `k6R` contra `k1R`, com tokens, tempo e acertos lado a lado com os números da Unsloth.
- **Decisão:** esta campanha só recomenda. O driver diário e o launcher não mudam.
- **Parada:** disco < 150 GB, swap Δ > 2 GB ou kernel panic. Um braço que o Splash recusa sai da fila, com o erro no resultado.

## Tasks

A fila leva cerca de 25 h: a bateria do `k2a` levou 2.6 h na splash-longctx. O servidor do usuário fica parado até o fim desta campanha.

### Task W0: Preparação

- [ ] **Step 1:** Conferir o disco. Os três downloads somam 243.7 GB.
- [ ] **Step 2:** Baixar os três packs por `hf download`, com `--revision` e `--include` do pack. Conferir o tamanho.
- [ ] **Step 3:** Sincronizar `bench/flashnext-weights-2026-11/` e `run-candidate.sh` no rig. Rodar os testes de `tests/`.
- [ ] **Step 4:** Rodar `run-arm.sh <braço> 32768 --repeat 1 --tag smoke` nos seis braços. Registrar boot, memória e erros em `results/etapaW0-preparacao.md`.

### Task W1: Velocidade

- [ ] **Step 1:** Rodar `run-arm.sh <braço> 262144 --repeat 3 --tag w1` em `k6R`, `k5R`, `k1R`, `k4R`, `k3R`, um boot por braço, com `idle-gate.sh --minutes 10` e 120 s entre braços. O `k2R` reutiliza os números da Task 2 da splash16.
- [ ] **Step 2:** Escrever a tabela em `results/etapaW1-velocidade.md`.

### Task W2: Qualidade, tokens e tempo

- [ ] **Step 1:** Com `BATTERY_CAMPAIGN_DIR` nesta campanha, rodar `run-battery.sh <braço> w1 --suites "humaneval gpqa livecodebench if jdhodges veerman" --ctx 262144` na mesma ordem da W1. A referência `k2g` vem da Task 6 da splash16. Com `R = f`, rodar também `k2f` aqui.
- [ ] **Step 2:** Rodar `toolcall-probe.sh <braço> --sessions 20 --suffix w1 --max-tokens 2048`, com `TOOLCALL_CAMPAIGN_DIR` nesta campanha.
- [ ] **Step 3:** Rodar `summarize_ab.py` de cada braço contra `k2R`, e de `k6R` e `k5R` contra `k1R`.

### Task W3: Segunda passada

- [ ] **Step 1:** Repetir a bateria em ordem invertida, com `--label <braço>-r2`, no `k2R` e em cada braço que cumprir a regra de candidato na primeira passada. Se nenhum cumprir, repetir o `k6R` e o `k2R`, para medir o ruído.
- [ ] **Step 2:** Um resultado sem repetição não vira veredito.

### Task W4: Fechamento

- [ ] **Step 1:** Escrever `results/summary.md`: uma tabela por pergunta, o que não rodou e os desvios do plano.
- [ ] **Step 2:** Atualizar o teste 7 da nota `research/rig-stack-updates-20261103.md` com o link do resultado.
- [ ] **Step 3:** Continuar nos Steps finais da Task 8 da splash16: reiniciar o servidor do usuário e abrir o PR.
