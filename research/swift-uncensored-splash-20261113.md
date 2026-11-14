# 2026-11-13 — Swift 1.5 uncensored no Splash 1.6.1: candidatos e compatibilidade

Pesquisa no Hugging Face em 13/11/2026. Fontes: API do Hugging Face (`/api/models`), cards dos repos e os
cabeçalhos GGUF lidos por HTTP range. Nenhum peso foi baixado e nada rodou no rig. O rig não respondeu por SSH
durante a pesquisa. Os números de qualidade e de velocidade abaixo são **declarados pelos autores**.

Pedido do usuário: achar os melhores modelos uncensored do Flash-Next ou do Swift para o rig, com preferência
para o Splash e para o Swift, e medir o desempenho geral.

Plano da campanha: [bench/swift-uncensored-2026-11/plan.md](../bench/swift-uncensored-2026-11/plan.md).
Nota anterior sobre derivados: [qwen38-flashnext-derivatives-20261009.md](qwen38-flashnext-derivatives-20261009.md), seção 6.

Legenda: **[vendor]** = autor do pack ou do modelo; **[header]** = lido do cabeçalho GGUF em 13/11;
**[rig]** = medido neste repo.

## Resumo

1. **Três GGUF de Swift 1.5 uncensored passam na regra de tensores do Splash.** São o `IQ4_XS-plus` do
   jackjusko, o `swift-IQ3_S` da huihui-ai e o `IQ3_S` do SC117 [header].
2. **Três GGUF não passam.** O `IQ3_S-85G` do jackjusko, o `iq4_xs` do fzcfweasdferttgg e o `Q4_K_M` do
   XopMC513 guardam os tensores `hc_*_inject` em tipos que o Splash recusa [header].
3. **O candidato principal é o `IQ4_XS-plus` do jackjusko.** Ele tem o mesmo nível de quantização do `k2`
   e a menor edição: 7 tensores [vendor].
4. **Os dois `IQ3_S` usam a quantização GSQ-RCO da UkisAI.** Eles diferem só na fonte da abliteração: a
   huihui-ai v2 edita 96 tensores, e o SC117 transplanta 144 tensores da orcarouter [vendor].
5. **Nenhum autor mediu estes packs num Mac nem no Splash.**
6. **Para o mlx-serve existe um pack de Swift uncensored**, o do skudzinau. O repo exige aceite de termos, e o
   card não foi lido.

## 1. A regra de tensores do Splash

O Splash só aceita `F32`, `BF16` ou `Q8_0` nos tensores `hc_attn_inject` e `hc_ffn_inject`. Duas fontes:

- O card do [tegsvenson Q5_K_S Splash-Repack](https://huggingface.co/tegsvenson/Qwen3.8-Flash-Next-Uncensored-GGUF-Q5_K_S-Splash-Repack)
  cita o erro da 1.4.0 e a constante `FLOAT_ROW_TYPES` de `install/gguf.py` [vendor].
- A campanha de pesos tirou o `k7` (ThinkingCap `IQ4_XS`) da fila porque o Splash 1.5.0 e o 1.6.0 recusam os
  `hc_*_inject` em `IQ4_XS` ([run-queue.sh](../bench/flashnext-weights-2026-11/scripts/run-queue.sh)) [rig].

A 1.6.1 não foi testada com um pack recusado. O plano assume a mesma regra.

## 2. Cabeçalhos GGUF

O script [gguf_header.py](../bench/swift-uncensored-2026-11/scripts/gguf_header.py) lê o cabeçalho de cada shard
por HTTP range. O resultado completo está em
[gguf-headers-20261113.json](../bench/swift-uncensored-2026-11/results/gguf-headers-20261113.json).
Todos os packs têm arquitetura `qwen4exp` e as mesmas 47 famílias de tensores do `k2`.

| Pack | Tensores | Shards | `hc_*_inject` | Tipos que o `k2` não tem | Regra do Splash |
|---|---:|---:|---|---|---|
| `k2` ukisai `IQ4_XS` (referência, carrega) | 1224 | 3 | `BF16` | – | passa [rig] |
| `k8` ukisai GSQ-RCO `Q2_0` (referência, carrega) | 1224 | 2 | `BF16` | `Q3_K`, `Q4_0`, `Q4_K`, `Q5_0`, tipo 42 | passa [rig] |
| jackjusko `IQ4_XS/` | 1224 | 6 | `F32` | `IQ3_S` | passa |
| huihui-ai `swift-IQ3_S/` | 1224 | 2 | `BF16` | `IQ2_S`, `IQ3_S`, `IQ3_XXS`, `Q4_K`, tipo 42 | passa |
| SC117 `IQ3_S` (raiz) | 1224 | 2 | `BF16` | `IQ2_S`, `IQ3_S`, `IQ3_XXS`, `Q4_K`, tipo 42 | passa |
| jackjusko `IQ3_S-85G/` | 1224 | 8 | `IQ3_S` | `IQ2_XXS`, `IQ3_S`, `IQ3_XXS`, `Q5_1`, tipo 42 | **falha** |
| fzcfweasdferttgg `iq4_xs/` | 1224 | 4 | `IQ4_XS` | `Q5_1` | **falha** |
| XopMC513 `Q4_K_M/` | 1558 | 1 | `Q4_K` | `Q4_K`, `Q5_0` | **falha** |

Riscos que o cabeçalho não resolve:

- **Tipos de expert novos.** O `IQ3_S` aparece nos três packs que passam. O rig carregou o Unsloth `UD-IQ4_XS`
  (`k1`, `k6`), que usa `IQ3_S` nos experts segundo o card do jackjusko, mas esse cabeçalho não foi lido aqui.
  `IQ2_S` e `IQ3_XXS` não têm carga confirmada no rig.
- **Resolução da variante.** O Splash recebe `HUB:VARIANT`. A pasta da huihui-ai chama `swift-IQ3_S`, e os
  arquivos do SC117 ficam na raiz, ao lado de outras pastas. O `k8` já carrega da raiz [rig].
- **XopMC513.** O arquivo único de 119.3 GB traz a torre de visão dentro do GGUF.

## 3. Candidatos para o Splash

| Braço | Pack | Revisão | GB | Edição | Evidência do autor |
|---|---|---|---:|---|---|
| `z1h` | [jackjusko/Swift-1.5-Flash-Next-Heretic-ReverseEngineer](https://huggingface.co/jackjusko/Swift-1.5-Flash-Next-Heretic-ReverseEngineer), `IQ4_XS/` | `bd3bca0` | 95.9 | Heretic v2 do jeffpeng3: updates de posto 1 em 7 tensores de saída de atenção, camadas 30–37 | Nenhuma métrica de recusa nem de velocidade. Receita Unsloth `UD-IQ4_XS` com 6 camadas reforçadas; imatrix própria com 8.8% de engenharia reversa. |
| `z2h` | [huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF), `swift-IQ3_S/` | `cbc7fba` | 83.7 | Abliteração v2: 96 tensores, nenhum expert roteado | Nenhuma métrica. O card diz que a série Swift vem do GGUF da UkisAI. |
| `z3h` | [SC117/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF](https://huggingface.co/SC117/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF), `IQ3_S` na raiz | `3db919a` | 83.5 | Transplante de 144 tensores da orcarouter, inclusive `ffn_down_exps` | No `IQ2_XS`, contra o Swift sem edição: decode −2.2%, aceitação MTP −4.3 pp, thinking tokens 552 contra 471 (sem diferença significativa). |

O que cada braço responde:

- **`z1h` contra `k2h`:** o custo da edição Heretic v2 com o mesmo nível de quantização. A receita e a imatrix
  também mudam.
- **`z2h` contra `z3h`:** a fonte da abliteração, com a mesma quantização GSQ-RCO.
- **`z2h` e `z3h` contra `k2h`:** a edição e a quantização juntas. O controle que separa as duas é o Swift
  GSQ-RCO `IQ3_S` sem edição (`z0h`), que o rig não tem.

O card do SC117 justifica o transplante: 98% da massa editada (`ffn_down_exps`) é idêntica byte a byte entre o
Swift 1.5 e o Flash-Next base em BF16 [vendor].

## 4. Candidatos fora da fila

| Pack | Motivo |
|---|---|
| [fzcfweasdferttgg/…-heretic-GGUF](https://huggingface.co/fzcfweasdferttgg/Swift-1.5-Qwen3.8-Flash-Next-heretic-GGUF) `5b7d453`, `iq4_xs/` (98.4 GB) | Falha na regra do Splash. Sem imatrix. O conserto é reescrever os 96 tensores `hc_*_inject` em `F32` com `llama-quantize --tensor-type`, como no repack do tegsvenson. |
| jackjusko `IQ3_S-85G/` (86.5 GB) | Falha na regra do Splash. Os nomes dos arquivos terminam em `.gguf-0000N-of-00008.gguf`. |
| [XopMC513/Swift-1.5-…-Heretic](https://huggingface.co/XopMC513/Swift-1.5-Qwen3.8-Flash-Next-Heretic) `Q4_K_M/` (119.3 GB) | Falha na regra do Splash. O card declara HumanEval 152/164. |
| [IndrasMirror/…-Swift-1.5-XQ-Uncensored](https://huggingface.co/IndrasMirror/Qwen3.8-Flash-Next-Swift-1.5-XQ-Uncensored) | 2.61 bpw nos experts; só o engine Xolotl foi testado. |
| [skudzinau/Swift-1.5-…-Heretic-V2-MLX-Serve-iQ-MLX-4.7bpw](https://huggingface.co/skudzinau/Swift-1.5-Flash-Next-Heretic-V2-MLX-Serve-iQ-MLX-4.7bpw) `51dc131` (107.3 GB) | Formato do mlx-serve; o Splash só carrega GGUF. Fica como braço opcional do mlx-serve. |
| [dotyerts/Swift1.5-…-abliterated-oQ4e-mtp](https://huggingface.co/dotyerts/Swift1.5-Qwen3.8-Flash-Next-abliterated-oQ4e-mtp) | Formato oMLX. O card não diz a fonte da abliteração. |

Packs do Flash-Next base (sem Swift), para referência:
[Veedy heretic-2 iQ-MLX-4.7bpw](https://huggingface.co/Veedy/Qwen3.8-Flash-Next-heretic-2-MLX-Serve-iQ-MLX-4.7bpw)
(mlx-serve; recusas 5/100 e 2/100, HumanEval 95.7 [vendor]),
[tegsvenson Q5_K_S Splash-Repack](https://huggingface.co/tegsvenson/Qwen3.8-Flash-Next-Uncensored-GGUF-Q5_K_S-Splash-Repack)
(128.6 GB; carga declarada no Splash 1.4.0 num M4 Max 128 GB) e a pasta `unsloth-UD-IQ4_XS/` da huihui-ai v2 (93.7 GB).

## 5. Métodos de edição

| Fonte | Método | Tensores | Recusas declaradas |
|---|---|---:|---|
| jeffpeng3 Heretic v2 (Swift) | Heretic, updates de posto 1 | 7 | não lido (repo com termos) |
| huihui-ai v2 | abliteração de uma direção, sem experts | 96 | não declara |
| orcarouter | abliteração (Arditi et al. 2024), direção da camada 24 | 149 | ~94–100% → ~0–2% em AdvBench, JailbreakBench e StrongREJECT |
| trohrbaugh heretic-2 (base) | Heretic 1.3.0 | 26 | 99/100 → 0/100; KL 0.0818 |

## 6. Licença

Os packs de Swift herdam a Swift Open License v1.0: uso livre até US$ 1 000 000 de receita bruta anual. O repo
do SC117 de Flash-Next base declara Apache-2.0, mas a base usa a Qwen Community License 1.0.

## 7. O que não foi verificado

- Carga de qualquer um dos três packs no Splash 1.6.1.
- Disco livre no rig. Os três downloads somam 263.1 GB; o controle `z0h` soma mais 83.7 GB.
- Taxa de recusa, qualidade e velocidade no rig.
- Os cards do jeffpeng3 e do skudzinau (HTTP 401 sem login).
- O Reddit não foi consultado.
