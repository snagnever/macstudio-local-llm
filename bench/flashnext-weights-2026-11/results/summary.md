# Pesos do Flash-Next — resumo da campanha (2026-11-08 a 10)

**O Swift 1.5 `IQ4_XS` (`k2f`) continua o peso do rig.** Nenhum outro peso cumpre a regra de candidato. Todos gastam mais tokens medianos que o `k2f` no gpqa e no livecodebench, de 1.09 a 7.75 vezes, com qualidade dentro do ruído entre passadas. As exceções são o `k8f` e o `k3f`, que falham no G1. O ThinkingCap não carrega no Splash 1.5.0 nem no 1.6.0.

Release: Splash 1.5.0 (sufixo `f`), porque a regra "Trocar o launcher" da [splash16](../../splash16-2026-11/results/summary.md) falha. Regra de candidato: [plan.md](../plan.md).

## Respostas

| # | pergunta | veredito | resultado | fonte |
|---|---|---|---|---|
| 2 | O V3.1 melhora o base e ganha do Swift? | **não** (duas passadas do `k6f`) | O V3.1 decodifica 11% mais rápido que o base. Ele gasta mais tokens que o base e de 1.3 a 2.2 vezes os do Swift. A qualidade empata: 598 contra 595 do `k2f` em duas passadas. | [W1](etapaW1-fila.md), [W2](etapaW2-segunda-passada.md) |
| 3 | O ThinkingCap gasta menos que o Swift? | **não rodou** | O Splash recusa os tensores `hc_*_inject` em `IQ4_XS`. | [W0](etapaW0-preparacao.md) |
| 4 | Quanto se perde com o `UD-IQ3_XXS`? | **sem perda observada, uma passada** | 300 em 336, com 10 GB a menos que o `k6f`. Gasta de 1.31 a 1.86 vezes os tokens do `k2f`. | [W1](etapaW1-fila.md) |
| 5 | O fine-tune Swift muda o GSQ-RCO `Q2_0`? | **gasta menos, qualidade irregular, uma passada** | O `k8f` gasta 38% menos tokens no livecodebench que o `k4f` e acerta mais tool calls. O G1 falha no gpqa e no livecodebench. | [W1](etapaW1-fila.md) |
| 6 | O `k4f` se repete, e o `IQ1_M` serve de controle? | **sim, uma passada** | O `k4f` fica a 1 questão do `k2f` com 29 GB a menos de RAM, mas gasta de 2 a 3 vezes os tokens. O `k3f` perde 17 questões no gpqa. | [W1](etapaW1-fila.md) |

## Regra de candidato

| braço | qualidade | tokens gpqa / lcb contra `k2f` | candidato |
|---|---|---|---|
| `k6f` | empata (duas passadas) | 1.37 / 2.15 (W1), 1.85 / 1.79 (W2) | **não** |
| `k1f` | empata | 1.09 / 1.83 | **não** |
| `k5f` | empata | 1.31 / 1.86 | **não** |
| `k8f` | G1 falha no gpqa e no livecodebench | 1.81 / 1.91 | **não** |
| `k4f` | empata | 1.96 / 3.05 | **não** |
| `k3f` | G1 falha no gpqa | 7.75 / 2.16 | **não** |

- Entre as duas passadas, o mesmo braço muda até 10 questões em 336. As diferenças de qualidade da W1 ficam dentro desse ruído, exceto o gpqa do `k3f`.
- A mediana de tokens do `k2f` muda de 0.62 a 1.13 vezes entre passadas. No livecodebench, todos os braços ficam acima de 1.83, fora desse ruído.

## Afirmações dos vendors

| vendor | afirmação | resultado |
|---|---|---|
| Unsloth, V3.1 | até 50% menos tokens | não se confirma: o `k6f` gasta mais que o `k1f` nas duas passadas |
| Unsloth, V3.1 | cerca de 15% mais acurácia | não se confirma: 294 e 304 contra 297 |
| Unsloth, V3.1 | até 7% mais velocidade | confirma: decode +11% |
| UkisAI, Swift | 63.4% menos thinking na mediana | parcial: −8% no gpqa e −45% no livecodebench contra o `k1f` |
| BottleCap, ThinkingCap | 38.5% menos thinking | não rodou |

## O que não rodou

- **`k7` (ThinkingCap):** recusado na carga pelas duas releases.
- **Segunda passada** dos braços `k1f`, `k5f`, `k8f`, `k4f` e `k3f`. Pela W2 Step 1, só os candidatos e o par de ruído repetem.
- **Tool calls e teste de velocidade da W2:** a W2 repete só a bateria.

## Desvios do plano

- **W0:** o `k7` sai da fila. O `k8` precisa de uma pasta `Q2_0/` de symlinks no cache do Hugging Face.
- **W1:** a nota de tool calls conta sessões com os 5 turnos certos, porque o JSONL não tem veredito por sessão. O `T_turno` é o `e2e_ms` p50 do teste de velocidade a 262144, com thinking.
- **W2:** o `k6f` substitui o `k7` no par de ruído.
- **Probe de tool calls:** sai com exit 2 no `k6f`, `k5f`, `k8f` e `k4f`, e com exit 0 em braços que também têm sessões com falha. Não investigado.

## Próximos passos (fora da fila)

O usuário não pediu estes testes para esta execução. Eles ficam como sugestão, em ordem de prioridade.

| # | Teste | Por quê | Condição |
|---:|---|---|---|
| 7 | mlx-serve 26.11.2 contra 26.10.3: tool calls, `T_turno` e tokens em cache (testes 1 e 6 da nota) | É o servidor do uso diário | – |
| 8 | Thinking na 26.11.2 (teste 10 da nota) | A release remove os cortes de thinking, e o gasto de tokens pode subir | Junto com o 7 |
| 9 | Residência Metal na 26.11.2 (teste 8 da nota) | O teste é curto e usa a mesma instalação | Junto com o 7 |
| 10 | Terminal-Bench 2.1 do melhor peso, 12–24 h | Mede o candidato numa carga de agente | **Condição não cumprida:** nenhum peso cumpre a regra |
| 11 | ThinkingCap com os tensores `hc_*_inject` em `Q8_0`, ou Swift GSQ-RCO `IQ3_XXS` | O Splash recusa só o tipo `IQ4_XS` nesses tensores, e um GGUF refeito pode carregar. O `k8f` gasta menos que o `k4f` | Só se um GGUF com tipo suportado sair, ou se o tamanho importar |
| 12 | Claude Code 2.1.317 contra 2.1.292 (teste 4 da nota) | Mede requests com tool search e retries | – |
| 13 | oMLX 0.7.3 e llama.cpp v0.8.0 (testes 2 e 3 da nota) | Não são os servidores do uso diário | – |
| 14 | Exit 2 do `toolcall-probe.sh` | O código de saída não segue as sessões com falha | Antes da próxima campanha que use o probe |
| 15 | Segunda passada do `k8f` contra o `k4f` | O G1 do `k8f` falha numa passada só. No livecodebench, a diferença de 5 questões contra o `k4f` fica acima do ruído de até 1 questão medido na W2, mas o gpqa (4 questões) fica perto do ruído | Só se o `Q2_0` voltar a interessar pelo tamanho |
