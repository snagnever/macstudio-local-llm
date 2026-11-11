# Pesos do Flash-Next: Unsloth V3.1, ThinkingCap, GSQ-RCO e Swift — runbook da campanha (2026-11-07)

> **Status (2026-11-07): na fila, aprovada pelo usuário.** Nada rodou nem foi baixado. Esta campanha começa depois da Task 7 da [splash16-2026-11](../splash16-2026-11/plan.md). Branch: `bench/splash16-2026-11`.

## Ordem de execução

O usuário definiu esta ordem em 07/11. O item 1 é a campanha Splash 1.6. Os itens 2 a 6 são esta campanha. `scripts/run-queue.sh` fixa a ordem, e `tests/test_queue.py` a verifica.

| # | Teste | Braços | Pergunta |
|---:|---|---|---|
| 1 | Splash 1.6 contra 1.5, Tasks 3 a 7 | `k2f`, `k2g`, `k3f`, `k3g` | Qual release os pesos usam? |
| 2 | `UD-IQ4_XS` V3.1 contra base e Swift | `k6R`, `k1R` | O V3.1 melhora o base e ganha do Swift? |
| 3 | ThinkingCap `IQ4_XS` contra Swift | `k7R` | Qual fine-tune gasta menos com a mesma qualidade? |
| 4 | `UD-IQ3_XXS` V3.1 contra `k2R` e `k6R` | `k5R` | Quanto se perde com o arquivo menor? |
| 5 | Swift GSQ-RCO `Q2_0` contra GSQ-RCO `Q2_0` | `k8R`, `k4R` | Quanto o fine-tune Swift muda com quase a mesma quantização? |
| 6 | Pacote `k4R` e controle pequeno | `k4R`, `k3R` | O gráfico da Unsloth se repete? O `IQ1_M` serve de controle? |

A fila executa `k6`, `k1`, `k7`, `k5`, `k8`, `k4`, `k3`. O `k4` roda logo depois do `k8` porque é a referência do item 5, e o item 6 usa esse resultado.

A Unsloth afirma até 50% menos tokens, cerca de 15% mais acurácia e até 7% mais velocidade. O gráfico publicado mostra só acurácia, com ruído de cerca de 4 pontos. A BottleCap afirma 38.5% menos thinking, e a UkisAI afirma 63.4% menos na mediana. Os três números vêm dos vendors.

## Braços

O sufixo `R` é a release do Splash: `g` (1.6.0) se a regra "Trocar o launcher" da splash16 passar, `f` (1.5.0) se não passar. Todos os braços usam a mesma release e as flags padrão.

| braço | peso | revisão | GB (Hugging Face) | tipo | local dos arquivos |
|---|---|---|---:|---|---|
| `k2R` | ukisai Swift 1.5 `IQ4_XS` | `0142554` | no rig | fine-tune | pasta |
| `k1R` | Unsloth `UD-IQ4_XS`, 06/10 | `766911a` | no rig | base | pasta |
| `k6R` | Unsloth `UD-IQ4_XS` V3.1 | `084c631` | 93.7 | base | pasta |
| `k7R` | BottleCap ThinkingCap `IQ4_XS` | `2a053f7` | 95.5 | fine-tune | raiz |
| `k5R` | Unsloth `UD-IQ3_XXS` V3.1 | `084c631` | 83.6 | base | pasta |
| `k8R` | ukisai Swift 1.5 GSQ-RCO `Q2_0` | `99bb8f7` | 66.6 | fine-tune | raiz |
| `k4R` | ISTA GSQ-RCO `Q2_0` | `ed59f92` | 66.4 | base | pasta |
| `k3R` | ISTA GSQ-RCO-Coder `IQ1_M` | `bba8885` | no rig | variante Coder | pasta |

Conferido na API do Hugging Face em 07/11: os arquivos `UD-IQ4_XS` e `UD-IQ3_XXS` têm hashes diferentes entre `766911a` e `084c631`. Os commits depois de `814db05` só mudam o README.

## O que cada comparação isola

| comparação | o que muda |
|---|---|
| `k6R` contra `k1R` | só a receita de quantização |
| `k5R` contra `k6R` | só o nível de quantização |
| `k8R` contra `k4R` | o fine-tune, com receita parecida; o imatrix é outro |
| `k7R` contra `k2R` | o fine-tune, com o mesmo nível; a receita é outra |
| `k7R` contra `k6R` e `k1R` | o fine-tune e a receita |
| `k6R` contra `k2R` | o fine-tune e a receita |
| `k5R` contra `k2R` | o fine-tune, a receita e o nível |

Nenhum braço separa por completo o fine-tune da receita.

## Regras

- **Candidato a substituir o `k2R`:** G1 de `summarize_ab.py` nas duas passadas, tool calls ≥ `k2R` − 1 de 20, e mediana de tokens ou de tempo em `gpqa` e `livecodebench` pelo menos 10% menor. O `T_turno` a 262144 fica ≤ 1.03 × `k2R`.
- **Afirmações dos vendors:** tokens, tempo e acertos lado a lado com os números publicados, no GGUF e no Splash.
- **Decisão:** esta campanha só recomenda. O driver diário e o launcher não mudam.
- **Parada:** disco < 150 GB, swap Δ > 2 GB ou kernel panic. Um braço que o Splash recusa sai da fila, com o erro no resultado.

## Tasks

A fila leva cerca de 32 h: 7 braços a cerca de 3.5 h cada, mais a segunda passada. A bateria do `k2a` levou 2.6 h na splash-longctx. O servidor do usuário fica parado até o fim desta campanha.

### Task W0: Preparação

- [ ] **Step 1:** Conferir o disco. Os cinco downloads somam 405.8 GB, ou menos se a Task 3 já tiver baixado o `Q2_0` da ISTA.
- [ ] **Step 2:** Baixar os packs com `hf download`, com `--revision` e `--include` de cada um. Conferir o tamanho.
- [ ] **Step 3:** Sincronizar `bench/flashnext-weights-2026-11/` e `run-candidate.sh` no rig. Rodar `tests/`.
- [ ] **Step 4:** Rodar `run-arm.sh <braço> 32768 --repeat 1 --tag smoke` nos braços da fila. Registrar boot, memória e erros em `results/etapaW0-preparacao.md`.
- [ ] **Step 5:** Tratar `k7` e `k8`. Uma nota do driver diz que o Splash só carrega GGUF dividido a partir de uma pasta `VARIANT/`. Essa regra vem da 1.4.0, e os dois repositórios têm os arquivos na raiz. Se o Splash recusar, montar um snapshot com uma pasta `VARIANT/` de symlinks no cache do Hugging Face e usar `--offline`, como no `k2m`, com teste antes. Se ele ainda recusar, o braço sai da fila.

### Task W1: Fila

- [ ] **Step 1:** Rodar `scripts/run-queue.sh <f|g>` numa chain no rig. Cada braço roda velocidade, bateria e tool calls, e imprime `CHECKPOINT-<braço>` antes do próximo. Com `g`, a referência `k2g` vem das Tasks 2 e 6 da splash16. Com `f`, a fila roda `k2f` primeiro.
- [ ] **Step 2:** Rodar `summarize_ab.py` de cada braço contra `k2R`, de `k6R` e `k5R` contra `k1R`, e de `k8R` contra `k4R`.
- [ ] **Step 3:** Escrever `results/etapaW1-fila.md`, com uma tabela por item da ordem de execução. Fazer o commit dos JSONL por questão.

### Task W2: Segunda passada

- [ ] **Step 1:** Repetir a bateria em ordem invertida, com `--label <braço>-r2`, no `k2R` e em cada braço que cumprir a regra de candidato. Se nenhum cumprir, repetir `k7R` e `k2R`, para medir o ruído.
- [ ] **Step 2:** Um resultado sem repetição não vira veredito.

### Task W3: Fechamento

- [ ] **Step 1:** Escrever `results/summary.md`: uma tabela por pergunta, o que não rodou, os desvios do plano e a seção "Próximos passos" abaixo, atualizada.
- [ ] **Step 2:** Atualizar o teste 7 da nota `research/rig-stack-updates-20261103.md` com o link do resultado.
- [ ] **Step 3:** Continuar nos passos finais da Task 8 da splash16: conferir o driver diário, reiniciar o servidor do usuário e abrir o PR.

## Próximos passos (fora da fila)

O usuário não pediu estes testes para esta execução. Eles ficam como sugestão, em ordem de prioridade.

| # | Teste | Por quê | Condição |
|---:|---|---|---|
| 7 | mlx-serve 26.11.2 contra 26.10.3: tool calls, `T_turno` e tokens em cache (testes 1 e 6 da nota) | É o servidor do uso diário | – |
| 8 | Thinking na 26.11.2 (teste 10 da nota) | A release remove os cortes de thinking, e o gasto de tokens pode subir | Junto com o 7 |
| 9 | Residência Metal na 26.11.2 (teste 8 da nota) | O teste é curto e usa a mesma instalação | Junto com o 7 |
| 10 | Terminal-Bench 2.1 do melhor peso, 12–24 h | Mede o candidato numa carga de agente | Só se um peso cumprir a regra de candidato |
| 11 | Swift GSQ-RCO `IQ3_XXS` ou ThinkingCap `RCO-3.8bpw` | Variantes menores dos fine-tunes | Só se o `k7` ou o `k8` mostrar ganho e o tamanho importar |
| 12 | Claude Code 2.1.317 contra 2.1.292 (teste 4 da nota) | Mede requests com tool search e retries | – |
| 13 | oMLX 0.7.3 e llama.cpp v0.8.0 (testes 2 e 3 da nota) | Não são os servidores do uso diário | – |
