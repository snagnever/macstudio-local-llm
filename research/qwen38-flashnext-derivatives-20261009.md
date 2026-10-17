# 2026-10-09 — Qwen3.8-Flash-Next: pesos derivados, fine-tunes e runtimes desde o lançamento

Pesquisa web e Hugging Face em 09/10/2026. Somente metadados, cards, release notes e PRs; nenhum peso
baixado e nenhum número medido no rig. Todos os números de qualidade e velocidade abaixo são **declarados
pelos autores**, salvo quando a linha cita uma campanha deste repositório.

Nota anterior da mesma série: [qwen38-quant-refresh-20260904.md](qwen38-quant-refresh-20260904.md).
Driver diário atual e suas medições: [docs/models/qwen3.8-flash-next.md](../docs/models/qwen3.8-flash-next.md).
Referências e builds do lançamento: [bench/qwen38-flash-next/references.md](../bench/qwen38-flash-next/references.md).

**Método.** Busca web; API e páginas do Hugging Face (`/api/models`, histórico de commits, cards);
GitHub (`gh api`) para releases e PRs. O Reddit não foi consultado: o Claude in Chrome bloqueia
`reddit.com` por restrição de segurança, e a busca web não retornou threads do r/LocalLLaMA sobre os
derivados novos. As referências Reddit do lançamento ficam em
[references.md](../bench/qwen38-flash-next/references.md).

**Adendo de 10/10.** A [seção 11](#11-adendo-1010-alternativas-ao-jundot-oq4e-mtp-no-omlx) responde à
pergunta "existe pack mais novo que o Jundot oQ4e-mtp para o oMLX?". O adendo usa trechos do Reddit que
a busca Google exibe (`site:reddit.com`). As threads não foram abertas: o Claude in Chrome e o WebFetch
bloqueiam `reddit.com`.

## Resumo

1. **Os pesos oficiais não mudaram.** `Qwen/Qwen3.8-Flash-Next` está na revisão `de4b8e4` (27/08). A
   Qwen não publicou checkpoint novo, changelog ou variante oficial nova do Flash-Next.
2. **A troca de pesos mais relevante para o rig já foi feita.** O ddalcu descontinuou o `mixed-4-8bit` em
   06/10 e aponta para o `iQ-MLX-4.7bpw` (01/10). A campanha
   [qwen38-flashnext-updates-2026-10](../bench/qwen38-flashnext-updates-2026-10/results/summary.md)
   adotou esse pack em 07/10 com mlx-serve 26.10.1. Nada a fazer aqui.
3. **O derivado novo com mais potencial para o driver diário é o Swift 1.5 (ukisai, 24/09).** É um
   fine-tune de RL que declara 63% menos thinking tokens com menos de 1% de perda no GPQA-Diamond. Já
   existe um port para mlx-serve 26.10.1 com o mesmo layout do pack iQ. A licença tem um limite de
   receita que precisa de revisão antes de qualquer uso na empresa.
4. **O llama.cpp ganhou MTP para Flash-Next no upstream em 01/10** (PR #29761). Essa informação
   substitui a regra "GGUF fica fora (sem MTP)" de [references.md](../bench/qwen38-flash-next/references.md).
5. **O GGUF mais baixado é o GSQ-RCO do ISTA-DASLab** (quantização não uniforme, 66–84 GB). O
   mlx-serve 26.10.1 o carrega pelo engine llama.cpp. O card declara paridade com BF16 a 3.5 bpw.
   Esse valor fica abaixo do piso de ~4 bpw que [references.md](../bench/qwen38-flash-next/references.md) recomenda.
6. **Há uma onda de packs podados, de quants baixos e de builds abliterated.** Esses packs servem
   Macs de 48–96 GB ou o backlog de modelos sem censura. Nenhum deles é candidato direto a driver no
   M4 Max 128 GB.

## 1. Base oficial

| Repo | Revisão | Data | Nota |
|---|---|---|---|
| [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | `de4b8e4` | 26–27/08 | BF16. Único commit de pesos: "Upload folder using huggingface_hub" (26/08). ~1.75M downloads, ~6 000 likes. |
| [Qwen/Qwen3.8-Flash-Next-FP8](https://huggingface.co/Qwen/Qwen3.8-Flash-Next-FP8) | — | 24/08 | FP8 oficial, ~173 GiB. |
| [QwenLM/Qwen3.8-Flash-Next (GitHub)](https://github.com/QwenLM/Qwen3.8-Flash-Next/) | — | — | Relatório técnico; recomenda Unsloth, Swift (ms-swift) e Llama-Factory para SFT/DPO/GRPO. |

Arquitetura, para contexto: MoE `qwen4_exp`, 125B no modelo principal com ~6B ativos por token, uma tabela
n-gram (PLE) de ~51B e uma cabeça MTP de ~4B. O contexto nativo é 262 144 tokens, extensível a 1M
por YaRN. A licença é a Qwen Community License 1.0. O produto hospedado `Qwen3.8-Flash` (QwenCloud) é
um build de produção separado. Ele não equivale aos pesos abertos
([blog Qwen](https://qwen.ai/blog?id=qwen3.8-flash-next),
[llm-stats](https://llm-stats.com/blog/research/qwen3.8-flash-next-launch)).

O ranking do Hugging Face em 09/10 mostra para onde a comunidade foi:

| Repo (busca `Qwen3.8-Flash-Next`) | Downloads | Likes | Última modificação |
|---|---:|---:|---|
| ISTA-DASLab/…-GSQ-RCO-GGUF | 3 559 321 | 739 | 29/09 |
| Qwen/Qwen3.8-Flash-Next | 1 751 752 | 6 055 | 27/08 |
| unsloth/…-GGUF | 1 304 726 | 1 157 | 26/08 |
| AtomicChat/…-GGUF | 745 089 | 176 | 26/08 |
| SC117/…-GSQ-RCO-abliterated-GGUF | 684 487 | 165 | 02/10 |
| ISTA-DASLab/…-GSQ-RCO-Coder-GGUF | 622 990 | 363 | 26/09 |
| orcarouter/…-Uncensored-GGUF | 499 273 | 696 | 26/08 |
| nvidia/…-NVFP4 | 339 865 | 360 | 02/09 |
| ukisai/Swift-1.5-…-GSQ-RCO-GGUF | 292 602 | 154 | 24/09 |
| huihui-ai/Huihui-…-abliterated-GGUF | 281 367 | 160 | 09/10 |

## 2. Packs MLX usados no rig

| Pack | Estado em 09/10 | Ação |
|---|---|---|
| [ddalcu iQ-MLX-4.7bpw](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw) `dafff5c` | Driver diário desde 07/10. HEAD igual ao local em 07/10 ([engine-updates-2026-10](../bench/engine-updates-2026-10/plan.md)). | nenhuma |
| [ddalcu mixed-4-8bit](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit) | Descontinuado em 06/10 (commit `3191916`, só README). Fica como rollback. | nenhuma |
| [ddalcu iQ-MLX-3.3bpw](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-3.3bpw) | Publicado em 16/09, ~4 600 downloads. Pack menor para Macs de 96 GB. | não priorizar no 128 GB |
| [Youssofal MTPLX Optimized-Speed](https://huggingface.co/Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed) | Commits de 17 a 27/09, só no card: velocidades do MTPLX 2.11.3/2.12.0, recomendação de 128 GB ou mais (pico de 87 GiB) e tag image-text-to-text. Pesos iguais. | nenhuma |
| [Jundot oQ4e-mtp](https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ4e-mtp) `2615fc0` | Sem mudança desde 27/08 (HEAD conferido de novo em 10/10). | ver [seção 11](#11-adendo-1010-alternativas-ao-jundot-oq4e-mtp-no-omlx) |

O card do iQ-MLX-4.7bpw declara, contra os logits do bf16, KLD mediana 0.0052 contra 0.0066 e top-1
88.6% contra 87.9%. A campanha de 07/10 mediu paridade de velocidade (±1%) e HumanEval 154 contra 151.

## 3. Swift 1.5 (ukisai): fine-tune de eficiência de raciocínio

[ukisai/Swift1.5-Qwen3.8-Flash-Next](https://huggingface.co/ukisai/Swift1.5-Qwen3.8-Flash-Next),
revisão `0bd4fe2`, 22–24/09.

**Método declarado.** A ukisai identificou tokens associados a overthinking e os penalizou, sem um teto
direto de comprimento. Depois recuperou a acurácia com RL e OPD. O pós-treino também foi adaptado para
código e tarefas de agente de horizonte longo. Os dados derivam de
`ukisai/Qwen3.8-27B-multi-turn-agent-sft`, re-amostrados e convertidos em ambientes de RL.

**Resultados declarados** (BF16, reasoning xhigh, contra o Flash-Next base):

| Benchmark | Base | Swift 1.5 |
|---|---:|---:|
| GPQA-Diamond | 89.80 | 89.60 |
| Thinking tokens no GPQA-D (média) | 17 683 | 7 823 (−63.4%, 1.8× mais rápido) |
| AIME 2026 | 98.67 | 96.67 |
| LiveCodeBench v6 | 88.40 | 90.39 |
| IFBench | 73.20 | 70.13 |
| MMLU-Pro | 87.75 | 87.20 |

O ganho fica nos tokens de raciocínio e não na qualidade. As regressões em IFBench (−3.1) e AIME (−2.0)
são maiores que a perda no GPQA-D que o card usa como manchete.

**Licença.** A contribuição da ukisai usa a Swift Open License v1.0. O uso é livre (inclusive comercial)
para organizações com receita bruta anual até US$ 1 000 000. Acima disso, o uso exige uma Swift
Enterprise License. A base continua sob a Qwen Community License 1.0. **Confirme o enquadramento da
empresa antes de usar este modelo em trabalho.**

**Ports disponíveis:**

| Repo | Data | Formato | Nota |
|---|---|---|---|
| [Dankpaws/Swift1.5-…-MLX-4.7bpw](https://huggingface.co/Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw) | 06/10 | MLX para **mlx-serve 26.10.1** | Experts de 4 bits calibrados + spine de 8 bits. Shards de 74.7 GB + `ngram_table.bin` de 32.0 GB (mmap). MTP incluída; só texto. Medido pelo autor num M5 Ultra 96 GB: decode 113.7 tok/s após 4K e 81.1 após 95K; top-1 contra o Swift BF16 91.0%. |
| [scottlowry/Swift1.5-…-oQ4e-fp16-mtp](https://huggingface.co/scottlowry/Swift1.5-Qwen3.8-Flash-Next-oQ4e-fp16-mtp) (e oQ5e, oQ6e, oQ8e) | 06–07/10 | MLX oQ (oMLX 0.7.0) | Card mínimo, sem avaliação. |
| [ukisai/Swift-1.5-…-GSQ-RCO-GGUF](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF) | 24/09 | GGUF GSQ-RCO | ~293K downloads. |
| [ukisai/Swift-1.5-…-GGUF](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF) | 24/09 | GGUF | ~142K downloads. |

O pack Dankpaws tem o mesmo layout e o mesmo runtime do driver atual, mas a tabela n-gram **não é
idêntica** à do pack iQ (API de árvore do HF, 09/10). Os dois arquivos têm o mesmo tamanho e hashes LFS
diferentes:

| Pack | `ngram_table.bin` (bytes) | LFS SHA256 |
|---|---:|---|
| Dankpaws Swift1.5 MLX-4.7bpw | 32 000 153 976 | `20406b4b115fe5a1ceb4847fd40e00fe85ecc33fa55c48328652f93586e669c9` |
| ddalcu iQ-MLX-4.7bpw | 32 000 153 976 | `c8ab74bc343408cf3923d7d64b3698fbeb3e78c07ce7f85a650a8278731251d2` |

Consequência: a tabela do driver não pode ser reaproveitada nem ligada por hardlink. O teste exige
o download completo do repositório, 106.8 GB em 115 arquivos.

## 4. GSQ-RCO (ISTA-DASLab): GGUF não uniforme

[ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF),
revisão `ed59f92`, 07/09 (última modificação em 29/09).

GSQ é um método de quantização escalar pós-treino. RCO escolhe o tipo de quantização de cada tensor
sob um orçamento total de tamanho. Os arquivos são GGUF padrão em dois shards: o shard 1 contém o
transformer e precisa ficar residente; o shard 2 contém a tabela n-gram (28.8 GB) e pode ficar em
disco (`-lm mmap --lazy-mode on`).

| Variante | bpw médio | Total | Shard 1 | Média de tarefas (BF16 = 93.12) |
|---|---:|---:|---:|---:|
| Q2_0 | 2.40 | 66.4 GB | ~37.6 GB | 89.07 |
| IQ2_XS | 2.50 | 68.0 GB | — | 89.16 |
| IQ3_XXS | 3.00 | 75.8 GB | — | 92.57 |
| IQ3_S (recomendada) | 3.50 | 83.6 GB | ~54.8 GB | 93.26 |

**Variante Coder** ([GSQ-RCO-Coder-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF),
26/09). É uma compressão, não um fine-tune: o RCO remove metade dos experts roteados, escolhidos por KL
em dados de código, uso de ferramentas, visão e raciocínio espacial. O resto vai a 3.5 bpw. O total é
58.4 GB (transformer de 29.6 GB). Resultados declarados: SWE-bench Verified 75.60 contra 82.80
(91.3% retido) e LiveCodeBench v6 86.28 contra 87.43 (98.7%).

**Como rodar no Mac:**

- O mlx-serve 26.10.1 encaminha GGUF `qwen4exp` com tipos que o ds4 não aceita para o engine llama.cpp
  ([ddalcu/mlx-serve#546](https://github.com/ddalcu/mlx-serve/issues/546)). O PR cita o GSQ-RCO IQ3_XXS
  como o caso que falhava no 26.9.5.
- O llama.cpp upstream suporta `qwen4exp` desde a PR #27742 (28/08) e MTP desde a #29761 (01/10). Ver a seção 7.

**Leitura para o rig.** [references.md](../bench/qwen38-flash-next/references.md) pede "não descer
abaixo de ~4 bpw para caber", com base na compilação de PPL/KLD de 11/09. O GSQ-RCO declara que a IQ3_S
bate o BF16. Essa avaliação é do próprio autor, numa bateria de tarefas, e não em KLD contra os logits
do BF16. Os dois critérios não são comparáveis. O GSQ-RCO só seria útil no rig para liberar memória
(KV de 512K, ou um segundo modelo ao lado), e não por qualidade.

## 5. Packs podados e quants baixos (MLX)

| Repo | Data | O que é | Nota |
|---|---|---|---|
| [Litwein/…-REAP320-oQ3e-DWQ-MTP-Vision-MLX](https://huggingface.co/Litwein/Qwen3.8-Flash-Next-REAP320-oQ3e-DWQ-MTP-Vision-MLX) | 15/09, atualizado em 07/10 | REAP 512 → 320 experts por camada, experts de 3 bits, três rodadas de KL-DWQ contra os logits do bf16, MTP podada para os mesmos experts, visão em bf16. | Alvo: Mac de 48 GB no oMLX. Declara que o DWQ recupera 33.6% do gap da poda. Existe também uma variante MTPLX. |
| [sh0wie/…-REAP-288-MLX-4bit](https://huggingface.co/sh0wie/Qwen3.8-Flash-Next-REAP-288-MLX-4bit) | 27/08 | REAP 512 → 288 experts, 4 bits. | Fonte dos manifests REAP usados pelo Litwein. |
| [d9beuD/…-oQ2-mtp até oQ3.5e-mtp](https://huggingface.co/d9beuD/Qwen3.8-Flash-Next-oQ3.5e-mtp) | 05/10 | Varredura oQ/oQe (imatrix) do oMLX 0.7.0, níveis 2 a 3.5. | O oQ3.5e tem ~3.99 bpw efetivo e 90 GB. A calibração cobre 99.97% dos experts. Sem avaliação de qualidade. |
| [AutomatosX/AX-…-MLX-AXQ-MXFP4-MTP](https://huggingface.co/AutomatosX/AX-Qwen3.8-Flash-Next-MLX-AXQ-MXFP4-MTP) | 29/08, atualizado em 06/10 | AXQuant mixed, 5.88 bpw medido, 132 GB, MTP e visão em BF16. | O card diz que o pack "não é release certificado" e não publica qualidade nem velocidade. Grande demais para o rig. |
| [sanasol2008/…-Abliterated-Sushi-2bpw](https://huggingface.co/sanasol2008/Qwen3.8-Flash-Next-Abliterated-Sushi-2bpw) | 08/10 | Formato Sushi (experts EXL3). | O mlx-serve 26.10.1 carrega packs Sushi sem conversão (release notes). |

Pela regra de [references.md](../bench/qwen38-flash-next/references.md), um pack podado ou de 3 bits
só se justifica no rig se a meta for memória livre. Nenhum destes publica KLD contra o bf16 na mesma
metodologia do pack iQ.

## 6. Builds abliterated e uncensored

Relevante para o backlog de modelos sem censura. Estes builds removem o comportamento de recusa
(abliteration). Eles não adicionam treino de capacidade, e os autores marcam todos como uso experimental.

| Repo | Data | Formatos |
|---|---|---|
| [huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated) | 29/09–01/10 | BF16; [GGUF](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF) atualizado em 09/10; mradermacher GGUF e i1 (02–03/10) |
| [orcarouter/Qwen3.8-Flash-Next-Uncensored](https://huggingface.co/orcarouter/Qwen3.8-Flash-Next-Uncensored) | 26–27/08 | BF16, FP8, NVFP4, [MLX 4/6/8 bits](https://huggingface.co/orcarouter/Qwen3.8-Flash-Next-Uncensored-MLX), GGUF IQ2_XXS–Q5_K_M. O GGUF não traz a cabeça MTP; o MLX traz. Acesso com termos no HF. Runbook do autor: [orcarouter.ai](https://www.orcarouter.ai/blog/qwen3-8-flash-next-uncensored). Também há uma tag no [Ollama](https://ollama.com/orcarouter/Qwen3.8-Flash-Next-Uncensored) (só engine MLX). |
| SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF | 02/10 | GGUF GSQ-RCO, ~684K downloads; também existe a variante sobre o Swift 1.5 |
| alesha-pro/Qwen3.8-Flash-Next-abliterated-GSQ-RCO-Strata-GGUF | 04/10 | GGUF |
| GCSA-AiLab/Qwen3.8-Flash-Next-FP8-Abliterated-MLX | 09/10 | MLX (novo, sem downloads) |
| LOKSUN-158/SamQuant-Qwen3.8-Flash-Next-Uncensored-MLX-Serve-Mix-C58 | 09/10 | MLX para mlx-serve (novo) |
| ghost-actual/Qwen3.8-Flash-Next-Abliterated-EXL3-2.50bpw | ~18/09 | EXL3 |

## 7. Runtimes: o que mudou para o Flash-Next

| Runtime | Versão (data) | Mudança relevante | Estado no repo |
|---|---|---|---|
| mlx-serve | 26.10.1 (01/10) | MTP +5–8% no M4 Max, +12% acima de 32K; `--ple-gpu` opcional; carrega GGUF `qwen4exp` pelo engine llama.cpp (#546); carrega packs Sushi. | Driver atual ([summary](../bench/qwen38-flashnext-updates-2026-10/results/summary.md)). O `--ple-gpu` é recusado no 128 GB ([etapa-p](../bench/qwen38-flashnext-updates-2026-10/results/etapa-p.md)). |
| llama.cpp | PR [#29761](https://github.com/ggml-org/llama.cpp/pull/29761) "Qwen4Exp: add MTP", merge em 01/10 | MTP para Flash-Next no upstream. Substitui a [#28243](https://github.com/ggml-org/llama.cpp/pull/28243), fechada sem merge ("Superseded by #29761"). A [#27836](https://github.com/ggml-org/llama.cpp/pull/27836) segue aberta. | Ainda não medido. [references.md](../bench/qwen38-flash-next/references.md) diz "GGUF fica fora (sem MTP)", e essa premissa caiu. Forks com correções extras: [1bit-MONSTER #88](https://github.com/1bit-MONSTER/llama.cpp/pull/88) (draft logits NaN, 05/10), [unslothai #144](https://github.com/unslothai/llama.cpp/pull/144). Medição comunitária: [Strix Halo 17 → 47 tok/s com MTP](https://github.com/ggml-org/llama.cpp/discussions/27950). |
| oMLX | 0.7.1.dev1 (09/10) | Prefill em lote para requisições concorrentes (TTFT −13 a −22% no Flash-Next oQ4e). Checkpoints com group size 32: decode no M3 Ultra de 39 → 91 tok/s sem MTP e de 98 → 134 tok/s com MTP. Prefill de 32K com expert offload +61%. | O 0.7.0 foi medido em [engine-updates-2026-10](../bench/engine-updates-2026-10/results/flashnext-summary.md) e não bateu o driver. O 0.7.1 é dev release. |
| MTPLX | 2.12.2 (03/10) | Medido em engine-updates-2026-10 (Etapa F: 8.8 s a 32K com prime de 64 tokens). | Sem release nova depois de 03/10. |
| ds4 (antirez) | upstream | Suporta Flash-Next com `--mtp` e GGUF próprio `qwen38-q4k` ([antirez/qwen3.8-flash-next-gguf](https://huggingface.co/antirez/qwen3.8-flash-next-gguf), ~190K downloads). | Coberto em engine-updates-2026-10. |

Speedups do MLX declarados por terceiros, sem medição no M4 Max:
[Rapid-MLX 4bit](https://huggingface.co/rapid-mlx/Qwen3.8-Flash-Next-4bit) (M3 Ultra: MTP leva o decode de 25.2 a 34.9 tok/s),
[Vontra 8bit-MTP](https://huggingface.co/Vontra/Qwen3.8-Flash-Next-MLX-8bit-MTP),
[Vontra oQ3-MTP](https://huggingface.co/Vontra/Qwen3.8-Flash-Next-MLX-oQ3-MTP),
[MTPLX](https://github.com/youssofal/MTPLX) e [LLMCheck](https://llmcheck.net/blog/qwen3-8-flash-next-on-mac/).

## 8. Fora do Mac (para referência)

- **NVIDIA:** [nvidia/Qwen3.8-Flash-Next-NVFP4](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4)
  (02/09; experts W4A4 NVFP4; o SGLang precisa de um loader de branch de desenvolvimento) e
  RadixArk NVFP4. Há receitas para um único DGX Spark:
  [MiaAI-Lab TensorFold](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark-TensorFold),
  [blazux](https://github.com/blazux/qwen3.8-Flash-DGX) e o
  [thread do fórum NVIDIA](https://forums.developer.nvidia.com/t/qwen3-8-flash-next/381228/269).
- **SGLang:** [cookbook](https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-Flash-Next).
- **NeMo AutoModel:** [SFT do caminho só texto](https://github.com/NVIDIA-NeMo/Automodel/blob/main/docs/model-coverage/llm/qwen/qwen3-8-flash-next.mdx).
- **EXL3:** [turboderp/Qwen3.8-Flash-Next-exl3](https://huggingface.co/turboderp/Qwen3.8-Flash-Next-exl3) (31/08).
- **AMD:** agentionai ROCmFP4 imatrix GGUF (28/08); EliovpAI W3A8 RDNA4 (09/10).

## 9. Destilações que usam o Flash-Next como professor

- [empero-ai/Qwen3.8-35B-A3B-Distill](https://huggingface.co/empero-ai/Qwen3.8-35B-A3B-Distill): base
  Qwen3.6-35B-A3B, SFT sobre traces de Qwen3.8 (2.4T-A95B) e do Flash-Next. O Flash-Next é o professor,
  não a base. Não li o card completo; a informação vem do snippet de busca.

## 10. Recomendações para o rig (M4 Max 128 GB)

1. **Manter o driver** (mlx-serve 26.10.1 + iQ-MLX-4.7bpw). Nenhum peso usado no rig mudou depois das
   campanhas de 07/10 e 08/10.
2. **Candidato a A/B: Swift 1.5 em mlx-serve (pack Dankpaws 4.7bpw) contra o n2.** Antes de medir,
   resolver a licença. O download é de 106.8 GB, porque a tabela n-gram difere da do pack iQ. A métrica `T_turno` (512 tokens fixos) não captura o ganho que o Swift
   declara, porque esse ganho está no número de tokens de raciocínio. O A/B precisa de tempo até a
   resposta final com thinking livre, mais HumanEval e tool-calling com reasoning ativo, e de uma
   bateria de instruction-following, porque o card declara −3 no IFBench.
3. **Reabrir a premissa "GGUF sem MTP"** em [references.md](../bench/qwen38-flash-next/references.md).
   Isso só vale a pena se a meta for memória: GSQ-RCO IQ3_S (83.6 GB) no mlx-serve pelo engine llama.cpp,
   ou no llama.cpp com a #29761.
4. **Esperar o oMLX 0.7.1 estável** antes de medir de novo. O ganho de group size 32 foi declarado num
   M3 Ultra e exige um pack g32 (por exemplo
   [mlx-community/Qwen3.8-Flash-Next-4bit](https://huggingface.co/mlx-community/Qwen3.8-Flash-Next-4bit)).
   O 0.7.1 também traz o oQe refit, que muda a qualidade de conversões novas. O plano de teste do oMLX
   está na [seção 11](#11-adendo-1010-alternativas-ao-jundot-oq4e-mtp-no-omlx).
5. **Não usar como driver:** os packs podados (REAP, Coder), os quants abaixo de ~4 bpw e os builds
   abliterated. Os abliterated pertencem ao backlog de modelos sem censura, não ao driver diário.

## 11. Adendo 10/10: alternativas ao Jundot oQ4e-mtp no oMLX

Pergunta: existe pack mais novo que o `Jundot/Qwen3.8-Flash-Next-oQ4e-mtp` para o oMLX?

**Resposta: não existe sucessor do Jundot.** O pack segue em `2615fc0` (27/08). Há três caminhos com o
mesmo modelo base: um oQ5e da comunidade, uma reconversão local com o oQe refit do oMLX 0.7.1, e o
fine-tune Swift 1.5 em oQ. Nenhum deles deve vencer o driver (n2) em velocidade. O ganho possível é de
qualidade dentro do oMLX.

### 11.1 O que mudou desde o pack do Jundot

- **Uploads novos do Jundot não substituem o Flash-Next.** Depois de 27/08 o Jundot publicou
  `DeepSeek-V4.1-Flash-oQ4e-mtp` e `-oQ3e-mtp` (10–11/09; o oQ4e tem 432 GB e não cabe no rig) e
  `clef-oQ4e` / `clef-flash-oQ4e` (06/10). O clef é um modelo de decisão: o oMLX o serve em
  `POST /v1/systemone` e o modelo devolve uma probabilidade por opção, sem gerar texto. Não é chat.
- **oQe refit no oMLX 0.7.1.dev1** ([jundot/omlx#4385](https://github.com/jundot/omlx/pull/4385),
  merge em 09/10). Depois do arredondamento, o oQe refaz a escala e o bias de cada grupo por mínimos
  quadrados ponderados pelo imatrix. Um grupo só aceita o refit se o erro ponderado cai. O layout, o
  dtype e a alocação de bits não mudam, então a velocidade dos kernels é a mesma. **Só conversões novas
  mudam.** Validação do PR (Qwen3.5-9B e Qwen3.6-35B-A3B, não o Flash-Next):

  | Modelo | KL de texto oQ4e → oQ4e + refit | Acerto agregado oQ4e → + refit (original) |
  |---|---|---|
  | Qwen3.5-9B | 0.0326 → 0.0276 | 75.44 → 77.47 (77.08) |
  | Qwen3.6-35B-A3B (MoE) | 0.0723 → 0.0628 | 83.72 → 84.01 (83.62) |

  O acerto agregado soma MMLU 1000, Winogrande 300, HumanEval 164, MBPP 300 e GSM8K 300 (greedy, thinking
  desligado).
- **Variantes `-fp16`.** As notas do oMLX 0.7.0 dizem que os checkpoints fp16 servem GPUs sem bf16 nativo.
  O M4 Max tem bf16: use a variante sem `-fp16`.
- **Calibração layer-streaming** (oMLX 0.7.0rc1, [#2161](https://github.com/jundot/omlx/pull/2161))
  calibra o Flash-Next uma camada por vez. Ela torna possível converter no rig um modelo maior que a RAM.

### 11.2 Packs oQ do Flash-Next no Hugging Face (10/10)

Tamanho total pela API do HF (`?blobs=true`). Números de qualidade e memória são dos autores.

| Repo | HEAD | Data | Total | Quantizador | Nota |
|---|---|---|---:|---|---|
| [Jundot/…-oQ4e-mtp](https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ4e-mtp) | `2615fc0` | 27/08 | 106.3 GB | oMLX 0.6.3rc3 | Braço o1 de [engine-updates-2026-10](../bench/engine-updates-2026-10/results/flashnext-summary.md). |
| [GBP-DE/…-oQ5e-mtp](https://huggingface.co/GBP-DE/Qwen3.8-Flash-Next-oQ5e-mtp) | `75abb40` | 08/09 | 128.6 GB | oMLX 0.6.4 | Quantizado do BF16. Usa o pack do Jundot só como modelo de sensibilidade. O autor mede ~9 GB a mais de memória do sistema que o oQ4e (M5 Max 128 GB, SSD N-gram Offload e Lightning MTP ligados). O card relata um loop de autocorreção no oQ4e que o oQ5e não repetiu. |
| [txgsync/…-Dynamic-oQ5e-BF16-PLE-mtp](https://huggingface.co/txgsync/Qwen3.8-Flash-Next-Dynamic-oQ5e-BF16-PLE-mtp) | `b62713a` | 14/09 | 187.4 GB | conversão própria (imatrix da Unsloth) | Feito para M4 Max 128 GB com PLE SSD offload. Experts gate/up em Q4 e down em Q5 (algumas camadas em Q8). Atenção, GDN e mixer em Q8. Tabela n-gram (PLE), as 32 tensores MTP e a visão em BF16. ~5.0 bpw nos tensores quantizados. Sem números de qualidade. |
| [mlx-community/…-oQ6e-mtp](https://huggingface.co/mlx-community/Qwen3.8-Flash-Next-oQ6e-mtp) | `e171af8` | 31/08 | 150.5 GB | oMLX | Grande demais para uso diário no 128 GB. |
| [scottlowry/Swift1.5-…-oQ4e-mtp](https://huggingface.co/scottlowry/Swift1.5-Qwen3.8-Flash-Next-oQ4e-mtp) | `e8ed008` | 03/10 | 106.3 GB | oMLX | Fine-tune Swift 1.5 (seção 3). Também há oQ5e (`c3524ba`, 128.6 GB), oQ6e e oQ8e, e variantes `-fp16` de 07/10 (oMLX 0.7.0). Outros ports oQ: thosewhowrite, mrmurphydotdev, arkham00, b2z. Licença: ver seção 3. |
| ben0112/…-oQ4e-mtp | — | 07/10 | — | oMLX 0.6.3rc3 | Mesma versão de quantizador do Jundot. Sem ganho. |

Nenhum pack Flash-Next público usa o oQe refit em 10/10.

### 11.3 Reddit (somente trechos da busca Google)

As threads não foram abertas. Cada linha resume o trecho que o Google mostra.

- **r/oMLX, "Made an oQ5e" (~1 mês).** O autor do oQ5e relata raciocínio e geração mais estáveis que o oQ4e
  em prompts difíceis.
- **r/oMLX, thread do 0.7.0.dev2 (~3 semanas).** Um usuário relata oQ5e a ~500/60 tok/s (prefill/decode) num
  M4 Max 128 GB, +10% sobre a versão anterior.
- **r/oMLX, "Qwen3.8 Flash Next with oMLX + Pi for long-running agentic work" (~1 semana).** Um usuário usa
  oQ5e com os ajustes que o oMLX 0.7.0 aplica sozinho.
- **r/oMLX, "What's your current favorite engine for large MoEs" (~1 semana).** Um usuário roda o GBP-DE
  oQ5e num M2 Ultra 192 GB.
- **r/LocalLLM, "Qwen 3.8 Flash Next for MLX-Serve".** O trecho diz que o quant do ddalcu para o mlx-serve
  é rápido mas "somewhat weaker in reasoning", e cita o quant do Jundot para o oMLX como alternativa de
  qualidade. O trecho não diz qual pack do ddalcu. O card do iQ-MLX-4.7bpw declara KLD menor que o do
  mixed-4-8bit (seção 2). A queixa pode ser do pack antigo.
- **r/oMLX, "oq4e Quantization of Qwen Flash Next, Swift Edition" e "Swift/ThinkingCap fp16
  quantizations".** Anúncios dos ports oQ do Swift 1.5, sem medições no trecho.

### 11.4 Leitura para o rig

- **Velocidade.** O o1 (oMLX 0.7.0 + Jundot oQ4e) já fica em 1.23× (32K) e 1.38× (128K) o `T_turno` do n2.
  Um oQ5e lê mais bytes por token, então o decode deve cair mais. Nenhum pack oQ substitui o n2 pelo
  critério `T_turno ≤ 0.97 × n2`.
- **Memória.** O o1 mediu wired de 91.2 / 98.0 / 100.5 GB a 32K / 128K / 256K. Com os +9 GB que o
  GBP-DE declara, a estimativa do oQ5e é ~100 / ~107 / ~110 GB. Esses valores ficam perto do n2
  (96.8 / 110.6 / 111.7 GB). A estimativa não foi medida, e o 256K pode ficar apertado.
- **Reconversão com refit.** Exige baixar o BF16 oficial (~354 GB para ~177B parâmetros) e espaço em
  disco para a saída. O tempo de calibração layer-streaming no M4 Max é desconhecido.
- **Uso do oMLX no rig.** O oMLX faz sentido como segundo runtime (wired menor, reuso de `append`) ou
  como base de qualidade. Ele não é candidato a driver.

### 11.5 Plano de teste proposto (não executado; revisado em 12/10)

**Revisão de 2026-10-12.** O plano vigente está em
[qwen38-flashnext-next-steps-20261012.md](qwen38-flashnext-next-steps-20261012.md). Mudanças: o braço `s1` no
mlx-serve já rodou em 11/10 e virou o driver principal; `o3` passa a ser o Jundot oQ4e `c4ddfb5`, já re-quantizado
com o refit (sem reconversão local); `o2` e `o4` cedem lugar ao umixer oQ4e-mix6 v2. A tabela abaixo é a de 10/10.

Campanha sugerida: `bench/qwen38-flashnext-omlx-quants-2026-10/`. Siga o padrão de instalação isolada
de [engine-updates-2026-10](../bench/engine-updates-2026-10/plan.md) (`~/.local/opt/qwen38/`).

**Pré-condição.** oMLX 0.7.1 estável, ou o 0.7.1.dev1 isolado. Antes, procure a versão em
`bench/*/results/` e `docs/models/`.

**Disco.** Em 10/10 o rig tem 37 GiB livres (98% usado). Libere espaço antes de baixar qualquer braço. A lista
priorizada de pesos, com os packs que podem sair do cache, fica em
[references.md, Próximos passos, item 4](../bench/qwen38-flash-next/references.md#próximos-passos).

| Braço | Pesos | Runtime | Condição |
|---|---|---|---|
| o1 | Jundot oQ4e-mtp | mesma versão do oMLX dos outros braços | referência; repetir para isolar o efeito do runtime |
| o2 | GBP-DE oQ5e-mtp | idem | download de 128.6 GB |
| o3 | Jundot oQ4e-mtp `c4ddfb5` (refit publicado em 11/10) | oMLX 0.7.1.dev1 ou mlx-serve 26.10.2-pre | 106.3 GB; substitui a reconversão local de ~354 GB |
| o4 | txgsync Dynamic-oQ5e | idem | opcional; 187.4 GB em disco |
| s1 | Swift1.5 oQ4e (sem `-fp16`) | idem | licença aprovada em 10/10; a variante mlx-serve já é o driver principal desde 11/10; esta só roda se o3 ficar a ≤ 1.03× do Swift no mlx-serve |

Medições:

1. **Probe de cache e velocidade** de [engine-updates-2026-10](../bench/engine-updates-2026-10/results/flashnext-summary.md):
   `T_turno`, TTFT, hit, decode e wired a 32K, 128K e 256K, com a mesma amostragem
   (`temperature=1.0`, `top_p=0.95`, `top_k=20`). Gate de memória: swap delta 0 a 256K.
2. **Estabilidade de geração.** O GBP-DE declara menos loops. Reaproveite a taxa de loop de
   [bench/degeneration/](../bench/degeneration/plan-quant-validation.md) com a mesma bateria nos braços o1–o4.
3. **Qualidade.** HumanEval e tool-calling com reasoning ativo, como na seção 10, item 2. O rig não comporta
   o BF16, então não há KLD contra os logits de referência. Registre isso como limite.
4. **Swift (s1).** Tempo até a resposta final com thinking livre, mais uma bateria de instruction-following
   (o card declara −3 no IFBench).

Regra de decisão: um braço vira o pack padrão do oMLX se a qualidade empata ou supera o o1 e o 256K roda
sem swap. O driver só muda pelo critério já em uso (`T_turno ≤ 0.97 × n2`).

## O que não foi verificado

- Nenhum número deste documento foi medido no rig, salvo os que citam campanhas do repositório.
- O Reddit não foi lido (bloqueio do Claude in Chrome). Opiniões da comunidade sobre Swift 1.5 e GSQ-RCO
  ficaram de fora. O adendo de 10/10 (seção 11.3) usa só os trechos da busca Google; o WebFetch também
  bloqueia `reddit.com`.
- O efeito do oQe refit no Flash-Next. O PR valida só Qwen3.5-9B e Qwen3.6-35B-A3B.
- A memória do oQ5e no rig. Os valores da seção 11.4 são estimativas a partir do o1 e do card do GBP-DE.
- O primeiro build numerado do llama.cpp que contém a #29761.
- As avaliações do Swift 1.5, do GSQ-RCO e do REAP320 são dos autores.

## Fontes

Oficiais e agregadores:
[blog Qwen](https://qwen.ai/blog?id=qwen3.8-flash-next) ·
[QwenLM GitHub](https://github.com/QwenLM/Qwen3.8-Flash-Next/) ·
[Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) ·
[Qwen FP8](https://huggingface.co/Qwen/Qwen3.8-Flash-Next-FP8) ·
[fine-tunes no HF](https://huggingface.co/models?other=base_model%3Afinetune%3AQwen%2FQwen3.8-Flash-Next) ·
[Artificial Analysis](https://artificialanalysis.ai/models/qwen3-8-flash-next) ·
[BenchLM](https://benchlm.ai/models/qwen3-8-flash-next) ·
[llm-stats](https://llm-stats.com/blog/research/qwen3.8-flash-next-launch) ·
[DataCamp](https://www.datacamp.com/blog/qwen3-8-flash-next) ·
[cellcog](https://cellcog.ai/blog/qwen3-8-flash-next/) ·
[codersera lineup](https://codersera.com/blog/qwen-3-8-model-lineup-2026/) ·
[Akash: requisitos de GPU](https://akash.network/the-bid/qwen3-8-flash-next-architecture-gpu-requirements/) ·
[IntuitionLabs: memória](https://intuitionlabs.ai/articles/qwen3-8-flash-next-architecture-memory)

Pesos MLX:
[ddalcu iQ-MLX-4.7bpw](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw) ·
[ddalcu mixed-4-8bit](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit) ·
[ddalcu iQ-MLX-3.3bpw](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-3.3bpw) ·
[Youssofal MTPLX](https://huggingface.co/Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed) ·
[Jundot oQ4e](https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ4e-mtp) ·
[Litwein REAP320](https://huggingface.co/Litwein/Qwen3.8-Flash-Next-REAP320-oQ3e-DWQ-MTP-Vision-MLX) ·
[d9beuD oQ3.5e](https://huggingface.co/d9beuD/Qwen3.8-Flash-Next-oQ3.5e-mtp) ·
[AutomatosX MXFP4](https://huggingface.co/AutomatosX/AX-Qwen3.8-Flash-Next-MLX-AXQ-MXFP4-MTP) ·
[Rapid-MLX](https://huggingface.co/rapid-mlx/Qwen3.8-Flash-Next-4bit) ·
[Vontra 8bit-MTP](https://huggingface.co/Vontra/Qwen3.8-Flash-Next-MLX-8bit-MTP)

Swift 1.5:
[ukisai/Swift1.5-Qwen3.8-Flash-Next](https://huggingface.co/ukisai/Swift1.5-Qwen3.8-Flash-Next) ·
[Dankpaws MLX 4.7bpw](https://huggingface.co/Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw) ·
[scottlowry oQ4e](https://huggingface.co/scottlowry/Swift1.5-Qwen3.8-Flash-Next-oQ4e-fp16-mtp)

GGUF:
[ISTA-DASLab GSQ-RCO](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) ·
[ISTA-DASLab Coder](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF) ·
[unsloth GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF) ·
[dzannotti MTP GGUF](https://huggingface.co/dzannotti/Qwen3.8-Flash-Next-MTP-GGUF) ·
[antirez ds4 GGUF](https://huggingface.co/antirez/qwen3.8-flash-next-gguf) ·
[guia AtomicChat](https://atomic.chat/blog/guides/how-to-run-qwen-3-8-flash-next-locally) ·
[gist llama.cpp RTX 4090](https://gist.github.com/ryan4yin/48617bbddacc7067f10799770b7cc33f)

Abliterated:
[huihui-ai BF16](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated) ·
[huihui-ai GGUF](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF) ·
[orcarouter BF16](https://huggingface.co/orcarouter/Qwen3.8-Flash-Next-Uncensored) ·
[orcarouter MLX](https://huggingface.co/orcarouter/Qwen3.8-Flash-Next-Uncensored-MLX) ·
[orcarouter runbook](https://www.orcarouter.ai/blog/qwen3-8-flash-next-uncensored) ·
[Ollama orcarouter](https://ollama.com/orcarouter/Qwen3.8-Flash-Next-Uncensored)

Runtimes:
[mlx-serve releases](https://github.com/ddalcu/mlx-serve/releases) ·
[mlx-serve #546](https://github.com/ddalcu/mlx-serve/issues/546) ·
[oMLX releases](https://github.com/jundot/omlx/releases) ·
[MTPLX](https://github.com/youssofal/MTPLX) ·
[llama.cpp #29761](https://github.com/ggml-org/llama.cpp/pull/29761) ·
[llama.cpp #28243](https://github.com/ggml-org/llama.cpp/pull/28243) ·
[llama.cpp #27836](https://github.com/ggml-org/llama.cpp/pull/27836) ·
[llama.cpp discussão #27950](https://github.com/ggml-org/llama.cpp/discussions/27950) ·
[1bit-MONSTER #88](https://github.com/1bit-MONSTER/llama.cpp/pull/88) ·
[unslothai #144](https://github.com/unslothai/llama.cpp/pull/144) ·
[SGLang cookbook](https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-Flash-Next) ·
[NeMo AutoModel](https://github.com/NVIDIA-NeMo/Automodel/blob/main/docs/model-coverage/llm/qwen/qwen3-8-flash-next.mdx) ·
[nvidia NVFP4](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4) ·
[fórum NVIDIA](https://forums.developer.nvidia.com/t/qwen3-8-flash-next/381228/269) ·
[DGX TensorFold](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark-TensorFold) ·
[DGX blazux](https://github.com/blazux/qwen3.8-Flash-DGX) ·
[LLMCheck Mac](https://llmcheck.net/blog/qwen3-8-flash-next-on-mac/)

Destilação:
[empero-ai Qwen3.8-35B-A3B-Distill](https://huggingface.co/empero-ai/Qwen3.8-35B-A3B-Distill)

Adendo de 10/10 (oMLX):
[oMLX releases](https://github.com/jundot/omlx/releases) ·
[jundot/omlx#4385 (oQe refit)](https://github.com/jundot/omlx/pull/4385) ·
[Jundot no HF](https://huggingface.co/Jundot) ·
[GBP-DE oQ5e](https://huggingface.co/GBP-DE/Qwen3.8-Flash-Next-oQ5e-mtp) ·
[txgsync Dynamic-oQ5e](https://huggingface.co/txgsync/Qwen3.8-Flash-Next-Dynamic-oQ5e-BF16-PLE-mtp) ·
[mlx-community oQ6e](https://huggingface.co/mlx-community/Qwen3.8-Flash-Next-oQ6e-mtp) ·
[scottlowry Swift1.5 oQ4e](https://huggingface.co/scottlowry/Swift1.5-Qwen3.8-Flash-Next-oQ4e-mtp) ·
[r/oMLX: oq4e Swift Edition](https://www.reddit.com/r/oMLX/comments/1ws1zlm/oq4e_quantization_of_qwen_flash_next_swift_edition/) ·
[r/LocalLLM: Qwen 3.8 Flash Next for MLX-Serve](https://www.reddit.com/r/LocalLLM/comments/1wudu2v/qwen_38_flash_next_for_mlxserve/) ·
[r/oMLX: I do not get the love for Qwen3.8-Flash-Next](https://www.reddit.com/r/oMLX/comments/1wp8mvi/i_do_not_get_the_love_for_qwen38flashnext/) ·
[r/oMLX: Flash Next with oMLX + Pi](https://www.reddit.com/r/oMLX/comments/1wqkqeu/qwen38_flash_next_with_omlx_pi_for_longrunning/)
