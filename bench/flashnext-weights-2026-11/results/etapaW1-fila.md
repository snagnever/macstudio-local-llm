# Task W1: Fila (2026-11-08 a 10)

**Nenhum peso cumpre a regra de candidato a substituir o `k2f`.** Todos os braços gastam mais tokens que o Swift 1.5 `IQ4_XS` no gpqa e no livecodebench: de 1.09 a 7.75 vezes a mediana do `k2f`. A regra pede pelo menos 10% a menos. Na qualidade, os braços ficam a até 8 questões do `k2f` em 336, exceto o `k3f` no gpqa. Uma passada não separa essa diferença.

Fila: `scripts/run-queue.sh f` (Splash 1.5.0), de 08/11 18:35 a 10/11 11:36 (relógio do rig), 41 h. Ordem: `k2f k6f k1f k5f k8f k4f k3f`. Cada braço roda velocidade (`run-arm.sh 262144 --repeat 3`), bateria (`run-battery.sh`, effort `xhigh`, 262144) e o probe de tool calls (20 sessões por perfil). Todos os passos terminam. O probe sai com exit 2 no `k6f`, `k5f`, `k8f` e `k4f`. O swap fica em 1743 MB durante toda a fila, e o disco livre fica acima de 850 GB.

Comparações: `summarize_ab.py --ab-dir results/w1/t1`, em [`results/w1/ab/`](w1/ab/).

## Resumo por braço

| braço | peso | decode p50 | e2e p50 | RAM pico | bateria /336 | tempo da bateria | tool calls `fp0` / `fp1` |
|---|---|---:|---:|---:|---:|---:|---|
| `k2f` | Swift 1.5 `IQ4_XS` | 110.9 | 12.0 s | 116.6 GB | 293 | 2h53 | 20 / 11 |
| `k6f` | unsloth `UD-IQ4_XS` V3.1 | 105.8 | 19.4 s | 115.0 GB | 294 | 4h56 | 20 / 7 |
| `k1f` | unsloth `UD-IQ4_XS` base | 95.5 | 31.1 s | 116.6 GB | 297 | 5h22 | 20 / 13 |
| `k5f` | unsloth `UD-IQ3_XXS` V3.1 | 105.3 | 25.9 s | 105.4 GB | 300 | 4h52 | 20 / 8 |
| `k8f` | Swift 1.5 GSQ-RCO `Q2_0` | 123.2 | 19.9 s | 87.5 GB | 301 | 3h59 | 20 / 15 |
| `k4f` | ISTA GSQ-RCO `Q2_0` | 117.3 | 26.2 s | 87.3 GB | 294 | 4h41 | 18 / 10 |
| `k3f` | ISTA GSQ-RCO-Coder `IQ1_M` | 108.6 | 16.4 s | 79.7 GB | 291 | 6h33 | 20 / 9 |

- Decode em tok/s. O decode, o e2e e a RAM vêm do teste de velocidade a 262144: 13 requests, 3 reps. O swap Δ é 0 em todos os braços.
- O e2e inclui o thinking. Ele mede o tempo de turno de cada peso, não só a velocidade do engine.
- Tool calls: sessões em que os 5 turnos acertam, de 20. `fp0` usa `frequency_penalty` 0, e `fp1` usa 1, como o Crush.

## Bateria

| suíte | `k2f` | `k6f` | `k1f` | `k5f` | `k8f` | `k4f` | `k3f` |
|---|---:|---:|---:|---:|---:|---:|---:|
| humaneval /164 | 144 | 143 | 143 | 147 | **156** | 143 | 151 |
| gpqa /50 | 42 | 40 | 43 | **44** | 35 | 39 | 25 |
| livecodebench /50 | 46 | 47 | 47 | 45 | 42 | 47 | 47 |
| if /20 | 19 | 20 | 20 | 20 | 20 | 19 | 20 |
| jdhodges /40 | 35 | 35 | 35 | 36 | 38 | 37 | 38 |
| veerman /12 | 7 | 9 | 9 | 8 | 10 | 9 | 10 |
| **total /336** | 293 | 294 | 297 | 300 | **301** | 294 | 291 |

## Regra de candidato

| braço contra `k2f` | G1 | tool calls ≥ `k2f` − 1 | tokens gpqa / lcb | tempo gpqa / lcb | e2e ≤ 1.03× | candidato |
|---|---|---|---|---|---|---|
| `k6f` | passa | não (`fp1` 7) | 1.37 / 2.15 | 1.57 / 2.59 | não | **não** |
| `k1f` | passa | sim | 1.09 / 1.83 | 1.29 / 2.24 | não | **não** |
| `k5f` | passa | não (`fp1` 8) | 1.31 / 1.86 | 1.49 / 2.11 | não | **não** |
| `k8f` | falha: gpqa, livecodebench | sim | 1.81 / 1.91 | 1.87 / 1.85 | não | **não** |
| `k4f` | passa | não (`fp0` 18) | 1.96 / 3.05 | 1.86 / 3.07 | não | **não** |
| `k3f` | falha: gpqa | não (`fp1` 9) | 7.75 / 2.16 | 8.88 / 2.26 | não | **não** |

Tokens e tempo são a mediana do braço dividida pela do `k2f`. A regra pede ≤ 0.90.

## Por item da ordem de execução

### Item 2: `UD-IQ4_XS` V3.1 contra base e Swift

| métrica | `k1f` base | `k6f` V3.1 | `k2f` Swift |
|---|---:|---:|---:|
| bateria /336 | 297 | 294 | 293 |
| decode p50 | 95.5 | 105.8 | 110.9 |
| tokens gpqa / lcb contra `k1f` | 1.00 / 1.00 | 1.26 / 1.18 | 0.92 / 0.55 |
| tool calls `fp1` | 13 | 7 | 11 |

O V3.1 decodifica 11% mais rápido que o base, com a mesma qualidade. Ele gasta mais tokens que o base, não menos. Ele não ganha do Swift: a qualidade empata, e o Swift gasta menos tokens e decodifica mais rápido.

### Item 3: ThinkingCap contra Swift

Não rodou. O Splash 1.5.0 e o 1.6.0 recusam os tensores `hc_*_inject` em `IQ4_XS` ([etapaW0](etapaW0-preparacao.md)).

### Item 4: `UD-IQ3_XXS` V3.1 contra `k2f` e `k6f`

O `k5f` tem 10 GB a menos de pesos que o `k6f` e não perde qualidade: 300 contra 294. Ele gasta 5% menos tokens no gpqa e 14% menos no livecodebench que o `k6f`, com o mesmo decode. Contra o `k2f`, ele gasta de 31% a 86% mais tokens. O ponto fraco dele é o perfil `fp1`, com 8 sessões certas de 20.

### Item 5: Swift GSQ-RCO contra GSQ-RCO

| métrica | `k4f` ISTA | `k8f` Swift |
|---|---:|---:|
| bateria /336 | 294 | 301 |
| tokens gpqa / lcb contra `k4f` | 1.00 / 1.00 | 0.92 / 0.62 |
| tempo lcb contra `k4f` | 1.00 | 0.60 |
| decode p50 | 117.3 | 123.2 |
| tool calls `fp0` / `fp1` | 18 / 10 | 20 / 15 |
| acertos no teste de velocidade | 12/13 | 10/13 |

Com quase a mesma quantização, o fine-tune Swift gasta 38% menos tokens no livecodebench e acerta mais tool calls. O G1 do `k8f` falha contra o `k4f` no gpqa (35 contra 39) e no livecodebench (42 contra 47). O humaneval sobe 13 questões. O perfil de qualidade do `k8f` fica irregular, e ele erra 3 de 13 requests no teste de velocidade.

### Item 6: `k4f` e o controle `k3f`

- O `k4f` (`Q2_0`, 66 GB) fica a 1 questão do `k2f` e usa 29 GB a menos de RAM. Ele gasta de 2 a 3 vezes os tokens do `k2f`.
- O `k3f` (`IQ1_M`) perde 17 questões no gpqa e leva 4 h nessa suíte, com 7 respostas truncadas. A bateria detecta a perda, então o `k3f` serve como controle.
- O `IQ1_M` não perde nas suítes de código e de tool calls: humaneval 151, livecodebench 47, jdhodges 38.

## Afirmações dos vendors

| vendor | afirmação | medido no Splash 1.5.0 | resultado |
|---|---|---|---|
| Unsloth, V3.1 contra base | até 50% menos tokens | +26% no gpqa, +18% no livecodebench (`k6f` contra `k1f`) | não se confirma |
| Unsloth, V3.1 contra base | cerca de 15% mais acurácia | 294 contra 297 | não se confirma |
| Unsloth, V3.1 contra base | até 7% mais velocidade | decode +11% | confirma |
| UkisAI, Swift contra base | 63.4% menos thinking na mediana | −8% de tokens no gpqa, −45% no livecodebench (`k2f` contra `k1f`) | parcial |
| BottleCap, ThinkingCap | 38.5% menos thinking | – | não rodou |

## Desvios e observações

- **Sem segunda passada ainda.** Pela W2 Step 2, nenhum resultado desta tabela vira veredito.
- **`k8f` no teste de velocidade:** 3 erros em 13 requests. O smoke da W0 também teve um request que chegou ao limite de tokens sem resposta.
- **Exit 2 do probe:** o exit 2 vem de sessões com falha. O `k2f`, o `k1f` e o `k3f` também têm sessões com falha no `fp1`, mas saem com exit 0. Não investigado.
- **`results/<braço>-65536-t1.0-toolcall-w1.jsonl` fica vazio.** O probe grava os dados em `results/toolcall/<braço>-fp*-w1.jsonl`.
- **Tool calls do `k4f` no `fp0`:** só 97 de 100 turnos rodaram. É o único braço com sessões incompletas nesse perfil.

Fonte: `results/<braço>-262144-t1.0-w1.jsonl`, `results/w1/t1/<braço>/<suíte>.jsonl`, `results/toolcall/<braço>-fp*-w1.jsonl` e `results/w1/ab/*.md`. A tabela de candidato foi calculada ad hoc a partir desses arquivos.
