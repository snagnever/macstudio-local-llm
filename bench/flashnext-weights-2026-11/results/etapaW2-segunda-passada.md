# Task W2: Segunda passada (2026-11-10)

**A segunda passada confirma que o `k6f` não é candidato, e o `k2f` continua o peso do rig.** O `k6f` gasta de 1.79 a 1.85 vezes os tokens medianos do `k2f` no gpqa e no livecodebench, como na W1. A qualidade dos dois braços sobe cerca de 10 questões em 336 entre as passadas. Esse ruído é maior que a diferença entre os braços na W1.

Bateria: `run-battery.sh <braço> w2 --label <braço>-r2`, Splash 1.5.0, effort `xhigh`, 262144. Ordem invertida: braços `k6f` e depois `k2f`, suítes veerman, jdhodges, if, livecodebench, gpqa e humaneval. Das 11:48 às 19:29 (relógio do rig). As duas baterias terminam com exit 0. O swap fica em 1743 MB, e o disco livre fica acima de 840 GB.

Nenhum peso cumpre a regra de candidato na W1, e o `k7` sai da fila na W0. Então a W2 repete o `k6f` e o `k2f`, em vez do `k7` e do `k2f`. O `k6f` é o `IQ4_XS` no mesmo nível do `k7`.

Comparações: `summarize_ab.py`, em [`results/w2/ab/`](w2/ab/).

## Acertos por passada

| suíte | `k2f` W1 | `k2f` W2 | `k6f` W1 | `k6f` W2 |
|---|---:|---:|---:|---:|
| humaneval /164 | 144 | 144 | 143 | 149 |
| gpqa /50 | 42 | 44 | 40 | 43 |
| livecodebench /50 | 46 | 47 | 47 | 47 |
| if /20 | 19 | 19 | 20 | 19 |
| jdhodges /40 | 35 | 38 | 35 | 36 |
| veerman /12 | 7 | 10 | 9 | 10 |
| **total /336** | 293 | **302** | 294 | **304** |
| soma das duas passadas /672 | | **595** | | **598** |

- G1 passa em todas as suítes nas três comparações: `k2f` W1 contra W2, `k6f` W1 contra W2 e `k2f` W2 contra `k6f` W2.
- A maior mudança de um braço entre passadas é de 6 questões no humaneval do `k6f` e de 3 no veerman do `k2f`.
- Os dois braços sobem na W2, então parte da mudança pode vir do dia ou da ordem das suítes. A W2 não separa esses efeitos.

## Tokens medianos

| suíte | `k2f` W1 | `k2f` W2 | `k6f` W1 | `k6f` W2 | `k6f` / `k2f` W1 | `k6f` / `k2f` W2 |
|---|---:|---:|---:|---:|---:|---:|
| gpqa | 2298 | 1431 | 3147 | 2642 | 1.37 | 1.85 |
| livecodebench | 1376 | 1559 | 2961 | 2795 | 2.15 | 1.79 |
| humaneval | 361 | 381 | 499 | 489 | 1.38 | 1.28 |

- A mediana do `k2f` no gpqa cai 38% entre as passadas, e a do livecodebench sobe 13%. A mediana de um braço numa suíte de 50 questões varia muito entre passadas.
- Mesmo com esse ruído, o `k6f` gasta mais tokens que o `k2f` nas duas passadas e nas três suítes.
- No tempo total, o `k6f` W2 leva 1.81 vezes o `k2f` W2 no gpqa e 2.29 vezes no livecodebench.

## O que a W2 muda nos resultados da W1

- **`k6f`:** com duas passadas, o resultado vira veredito. O V3.1 `UD-IQ4_XS` **não é candidato**: a qualidade empata com o `k2f`, e o gasto de tokens fica de 1.3 a 2.2 vezes maior.
- **`k2f`:** continua o peso do rig.
- **Diferenças de qualidade entre braços na W1:** de 291 a 301 em 336. A W2 mostra até 10 questões de diferença no mesmo braço, então essas diferenças não separam os braços. A exceção é o gpqa do `k3f`, com 17 questões a menos.
- **Tokens no livecodebench na W1:** os outros braços gastam de 1.83 a 3.05 vezes o `k2f`. A razão do `k2f` entre as passadas fica entre 0.88 e 1.13, então a margem fica acima do ruído medido. Os outros braços rodaram uma passada só, então isso não é veredito para eles.
- **Afirmação da Unsloth de até 50% menos tokens no V3.1:** nas duas passadas, o `k6f` gasta mais tokens medianos que o `k1f` W1 no gpqa (3147 e 2642, contra 2503) e no livecodebench (2961 e 2795, contra 2512). O `k1f` rodou uma passada só, então isso não é veredito, mas a W2 não mostra a redução.

## Desvios

- **Braços:** o `k6f` substitui o `k7`. Motivo acima.
- **Tool calls e teste de velocidade:** a W2 repete só a bateria. O probe de tool calls e o `run-arm.sh` rodaram uma vez, na W1.

Fonte: `results/w2/t1/<braço>-r2/<suíte>.jsonl`, `results/w1/t1/<braço>/<suíte>.jsonl` e `results/w2/ab/*.md`. As razões e a soma das passadas foram calculadas ad hoc a partir desses arquivos.
