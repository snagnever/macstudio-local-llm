# Qwen3.8-27B prefix-cache campaign — referências

> **Data da revisão:** 2026-08-23

Este documento separa fontes primárias, relatos comunitários e dados locais.
Relatos comunitários orientam hipóteses. Eles não substituem medições no rig.

## Fontes primárias

| ID | Fonte | Uso na campanha |
|---|---|---|
| P1 | [Qwen3.8 repository](https://github.com/QwenLM/Qwen3.8) | Arquitetura, thinking e compatibilidade |
| P2 | [Qwen3.8-27B model card](https://huggingface.co/Qwen/Qwen3.8-27B) | Contexto, sampling e recomendações oficiais |
| P3 | [Qwen3.8-27B FP8 model card](https://huggingface.co/Qwen/Qwen3.8-27B-FP8) | Arquitetura detalhada e `preserve_thinking` |
| P4 | [mlx-serve README](https://github.com/ddalcu/mlx-serve) | Recursos e setup do runtime |
| P5 | [mlx-serve CLI](https://github.com/ddalcu/mlx-serve/blob/main/docs/cli.md) | Opções de cache, MTP, prefill e métricas |
| P6 | [mlx-serve performance](https://github.com/ddalcu/mlx-serve/blob/main/docs/performance.md) | Defaults e efeitos de tuning |
| P7 | [mlx-serve engine notes](https://github.com/ddalcu/mlx-serve/blob/main/CLAUDE.md) | Limitações do cache híbrido e tool calls |
| P8 | [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) | Prompt cache, checkpoints e KV cache |
| P9 | [mlx-lm cache implementation](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/models/cache.py) | Estados de cache e persistência |
| P10 | [Unsloth Qwen3.8 GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) | Arquivos Q4, Q6, Q8 e tamanhos |
| P11 | [Unsloth Dynamic 3.0](https://unsloth.ai/docs/basics/dynamic-3.0-ggufs) | Método e métricas de quantização |
| P12 | [Unsloth Qwen3.8-27B guide](https://unsloth.ai/models/qwen3.8-27b) | Quant recomendado, memória e presets de thinking |
| P13 | [Unsloth Qwen3.8 MTP sidecar](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/tree/main/MTP) | Artefato MTP distribuído com os GGUFs |
| P14 | [llama.cpp speculative decoding](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md) | `draft-mtp`, sidecars e estatísticas de aceitação |
| P15 | [mlx-serve releases](https://github.com/ddalcu/mlx-serve/releases) | Revisão que corrige restore de prefix cache com MTP |
| P16 | [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases) | Revisão reproduzível do runtime GGUF |
| P17 | [oMLX repository](https://github.com/jundot/omlx) | Runtime, API compatível e configuração isolada |
| P18 | [oMLX v0.6.2](https://github.com/jundot/omlx/releases/tag/v0.6.2) | Última versão estável durante a revisão |
| P19 | [oMLX v0.6.3rc2](https://github.com/jundot/omlx/releases/tag/v0.6.3rc2) | Correção da estimativa KV híbrida e prefill ANE experimental |
| P20 | [oMLX per-model settings](https://github.com/jundot/omlx/blob/main/omlx/model_settings.py) | Campos de MTP, SpecPrefill e prefill ANE |
| P21 | [oMLX SpecPrefill implementation](https://github.com/jundot/omlx/blob/main/omlx/patches/specprefill.py) | Seleção de tokens e métricas do prefill sparse |
| P22 | [SpecPrefill paper](https://arxiv.org/abs/2502.02789) | Método de seleção por atenção do draft |
| P23 | [True2456 AWQ 5.0 bpw model card](https://huggingface.co/True2456/Qwen3.8-27B-AWQ-5.0bpw) | Quantização, loader exigido e drafts recomendados |
| P24 | [AWQ revision fixed by the campaign](https://huggingface.co/True2456/Qwen3.8-27B-AWQ-5.0bpw/commit/dc699a76ddcbef44c188a8aee2ccc79ccc339a04) | Revisão reproduzível do checkpoint |
| P25 | [AWQ MTP-head repair](https://huggingface.co/True2456/Qwen3.8-27B-AWQ-5.0bpw/commit/c5839cc642e479b7bbcd28311a4b8b9fb52fbd02) | Correção incluída na revisão fixada |
| P26 | [oMLX OpenAI request fields](https://github.com/jundot/omlx/blob/main/omlx/api/openai_models.py) | Overrides de SpecPrefill por request |
| P27 | [mlx-dspark repository](https://github.com/ARahim3/mlx-dspark) | Modos baseline, DSpark, DFlash 2, cache e telemetria |
| P28 | [mlx-dspark v0.14.0](https://github.com/ARahim3/mlx-dspark/releases/tag/v0.14.0) | Adaptação do draft cap em contexto longo |
| P29 | [mlx-dspark v0.15.0](https://github.com/ARahim3/mlx-dspark/releases/tag/v0.15.0) | Métricas por request, roofline e memory-pressure guard |
| P30 | [mlx-community Qwen3.8-27B-8bit](https://huggingface.co/mlx-community/Qwen3.8-27B-8bit) | Target 8-bit, group size 64 e sampling do model card |
| P31 | [RadixArk Qwen3.8-27B-DSpark](https://huggingface.co/RadixArk/Qwen3.8-27B-DSpark) | Drafter DSpark compatível com o target |
| P32 | [Inco AI Qwen3.8-27B-DFlash2](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2) | Drafter DFlash 2, parâmetros e garantia lossless |
| P33 | [Jundot Qwen3.8-27B-oQ8e-mtp](https://huggingface.co/Jundot/Qwen3.8-27B-oQ8e-mtp) | Checkpoint oQ8e BF16 principal e quantização declarada |
| P34 | [Revisão fixada do oQ8e BF16](https://huggingface.co/Jundot/Qwen3.8-27B-oQ8e-mtp/commit/c99e5aad8a478f71c10b9a3dde6709158b690da6) | Revisão reproduzível do candidato principal |
| P35 | [Revisão fixada do oQ8e fp16](https://huggingface.co/Jundot/Qwen3.8-27B-oQ8e-fp16-mtp/commit/4761782b9455f335292f4d6cb0c89570dff27a11) | Revisão reproduzível do controle fp16 |
| P36 | [oMLX performance: Qwen3.8-27B-oQ8e-fp16-mtp](https://omlx.ai/benchmarks/performance/2pko3m1k) | Configuração e números públicos em M3 Ultra; hipótese externa, não baseline local |
| P37 | [oQ8e fp16 model card detalhado](https://huggingface.co/evsinlb/Qwen3.8-27B-oQ8e-fp16-mtp) | Bpw efetivo, contexto, sampling e preferência BF16 em M3/M4 |

## Issues e discussões técnicas

| ID | Fonte | Risco coberto |
|---|---|---|
| I1 | [Qwen chat template breaks KV-cache reuse](https://github.com/QwenLM/Qwen3/issues/1826) | Mudança dos tokens históricos |
| I2 | [Qwen3.6 historical think-block drift](https://github.com/QwenLM/Qwen3.6/issues/131) | Normalização de reasoning e tool calls |
| I3 | [llama.cpp hybrid cache reuse issue](https://github.com/ggml-org/llama.cpp/issues/18497) | Reutilização em modelos recorrentes |
| I4 | [llama.cpp host-memory prompt caching](https://github.com/ggml-org/llama.cpp/discussions/20574) | Capacidade e operação do cache em RAM |
| I5 | [mlx-dspark prefix cache never hits](https://github.com/ARahim3/mlx-dspark/issues/7) | Regressão que o gate local deve impedir; upstream declara correção desde v0.10.1 |
| I6 | [Qwen3.8 preserve_thinking for llama.cpp](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/39) | Flags do template no GGUF |
| I7 | [SpecPrefill cache did not activate](https://github.com/jundot/omlx/issues/2443) | Risco de queda silenciosa do prefixo estático |
| I8 | [Persist static prefix for SpecPrefill](https://github.com/jundot/omlx/pull/2440) | Escopo da correção para system prompt e tools |
| I9 | [Qwen ANE prefill on M3 Max](https://github.com/jundot/omlx/issues/2781) | Protocolo, custo de memória e sinais de execução |
| I10 | [ANE prefill regression on M5](https://github.com/jundot/omlx/issues/2779) | Evidência de dependência do hardware |

## Relatos comunitários

| ID | Fonte | Sinal útil | Limite |
|---|---|---|---|
| C1 | [Introducing Qwen3.8 Dynamic v3 Unsloth GGUFs](https://www.reddit.com/r/LocalLLaMA/comments/1vsr67c/introducing_qwen3827b_dynamic_v3_unsloth_ggufs/) | Nova família Dynamic v3 | Post do fornecedor |
| C2 | [Qwen3.8 on 2x 3090 with vLLM and DFlash2](https://www.reddit.com/r/LocalLLaMA/comments/1vsccit/qwen3827b_on_2x_3090_vllm_dflash2_218_toks_single/) | Especulação depende do tipo de saída | CUDA, não Apple Silicon |
| C3 | [Dynamic 3.0 independent comparison](https://www.reddit.com/r/LocalLLM/comments/1vt9ucx/the_new_unsloth_dynamic_30_quants_are_real_good/) | Q6 perto de Q8 em métricas indiretas | Não mede agent loops |
| C4 | [Qwen3.8 not caching context on MLX](https://www.reddit.com/r/LocalLLM/comments/1vozpl6/qwen_38_27b_not_caching_context_on_mlx/) | Decode rápido pode perder no tempo total | Relato individual |
| C5 | [Qwen3.8 up to 3x faster with mlx-dspark](https://www.reddit.com/r/LocalLLaMA/comments/1vokrcy/qwen3827b_is_now_up_to_3_faster_on_apple_silicon/) | Motiva medir decode especulativo | Números não são do M4 Max desta campanha |
| C6 | [Qwen3.8 forks on M4 Max 128 GB](https://www.reddit.com/r/LocalLLaMA/comments/1vq50xf/having_all_those_qwen_38_27b_forks_which_one/) | MLX é o ponto inicial no Mac | Recomendações sem protocolo comum |
| C7 | [Q6_K_XL on M2 Ultra](https://www.reddit.com/r/LocalLLaMA/comments/1vr3s7j/qwen3827b_q6_k_xl_speeds_on_m2_ultra_192gb_what/) | Flags de cache e MTP no `llama.cpp` | Hardware diferente |
| C8 | [vLLM hybrid cache and MTP field notes](https://www.reddit.com/r/LocalLLaMA/comments/1vspexl/qwen38_27b_via_vllm_i_love_it_and_i_hate_it_here/) | Cache e especulação precisam de teste conjunto | CUDA e patches comunitários |
| C9 | [Qwen3.8 AWQ 5 bpw discussion](https://www.reddit.com/r/oMLX/comments/1vr3agq/if_you_were_initially_put_off_by_qwen3827b_pptg/) | Motiva o AWQ e o prefill especulativo | Relato do ecossistema oMLX |
| C10 | [Qwen3.8 oQ8e performance setup](https://www.reddit.com/r/LocalLLaMA/comments/1vty1g4/been_tweaking_my_qwen_38_setup_up_to_45_steady/) | Aponta para a combinação oQ8e, MTP, SpecPrefill e ANE | Não identifica de forma inequívoca o namespace do checkpoint |

## Evidência local reutilizável

| ID | Arquivo | Uso na campanha |
|---|---|---|
| L1 | [`docs/testing-plan.md`](../../docs/testing-plan.md) | Protocolo geral e benchmarks locais |
| L2 | [`docs/models/qwen3.6-27b.md`](../../docs/models/qwen3.6-27b.md) | Baseline local da arquitetura híbrida |
| L3 | [`docs/local-llm-reference.md`](../../docs/local-llm-reference.md) | Inventário e limites de memória |
| L4 | [`tools/local-llm-bench/scenarios/prefill-test.json`](../../tools/local-llm-bench/scenarios/prefill-test.json) | Prompts existentes de prefill |
| L5 | [`tools/local-llm-bench-m4-32gb/scripts/long_context_test.py`](../../tools/local-llm-bench-m4-32gb/scripts/long_context_test.py) | Fixture de contexto longo |
| L6 | [`tools/local-llm-bench-m4-32gb/scripts/speed_probe.py`](../../tools/local-llm-bench-m4-32gb/scripts/speed_probe.py) | Telemetria com `macmon` |
| L7 | [`bench/terminal-bench/plan.md`](../terminal-bench/plan.md) | Protocolo do Terminal-Bench |
| L8 | [`bench/terminal-bench/scripts/run-tbench-minimax-REMOTE.sh`](../terminal-bench/scripts/run-tbench-minimax-REMOTE.sh) | Driver remoto pelo MacBook Pro |
| L9 | [`tools/local-llm-bench/results/qwen3.6-27b-dense-mlx-6bit/prefill-test/m4-max-128gb-40gpu_lmstudio.md`](../../tools/local-llm-bench/results/qwen3.6-27b-dense-mlx-6bit/prefill-test/m4-max-128gb-40gpu_lmstudio.md) | Baseline de prefill no rig |

## Fatos que orientam a campanha

### Arquitetura híbrida

O Qwen3.8-27B usa 64 camadas. O layout repete três camadas Gated DeltaNet e uma camada de atenção.

O prefix cache precisa preservar o estado recorrente e o KV cache.
Uma implementação para Transformers puros não garante o mesmo comportamento.

Fontes: P1, P3, P9 e I3.

### `preserve_thinking`

O Qwen recomenda `preserve_thinking=true` para tarefas multi-turn.
Esse valor também mantém o histórico de tokens mais estável.

Uma mudança no rendering de `<think>` pode invalidar todo o prefixo.

Fontes: P2, P3, I1 e I2.

### Prefix cache no `mlx-serve`

O `mlx-serve` oferece cache em RAM, cache em SSD e cache de tokenização.
O limite padrão de RAM é 2 GB.

As notas do runtime registram invalidação após tool calls.
Elas também registram pequenas diferenças numéricas em hits de modelos híbridos.

Fontes: P4, P5, P6 e P7.

### Prefix cache no `llama.cpp`

O `llama-server` ativa prompt caching por padrão.
Ele oferece checkpoints por slot e cache em memória do host.

O `--cache-reuse` não garante reutilização após mudanças no meio de um modelo recorrente.

Fontes: P8, I3 e I4.

### Quantização

O Dynamic v3 `UD-Q4_K_XL` é o primeiro GGUF da campanha porque a Unsloth o recomenda como melhor equilíbrio local.
Q6 e Q8 funcionam como variantes de maior fidelidade e custo.

Os dados públicos disponíveis usam perplexidade, divergência e correspondência de tokens.
Eles não comprovam qualidade em Terminal-Bench.

Fontes: P10, P11, P12, C1 e C3.

### Speculative decoding

MTP, DFlash e DSpark podem acelerar código mais que prosa.
O ganho depende da taxa de aceitação e do custo de verificação.

Esta campanha testa MTP, DSpark e DFlash 2 como técnicas distintas.
O braço GGUF valida o sidecar publicado pela Unsloth e a aceitação reportada pelo
`llama.cpp`. Os braços `mlx-dspark` usam o mesmo target 8-bit para que baseline,
DSpark e DFlash 2 sejam comparações causais.

O `mlx-dspark` verifica cada token proposto no target e documenta saída lossless.
O modo `auto` escolhe DFlash 2 para Qwen3.8 na revisão atual, mas a campanha mede
modos explícitos para não tornar o resultado dependente do registry.

O issue I5 invalida versões antigas como evidência de cache. A documentação atual
declara correção por stable boundaries, rungs e anchors; o gate local continua
obrigatório porque o workload da campanha usa o mesmo padrão híbrido e tool turns.

Não copie caps publicados em M4 Pro. A partir de P28 o runtime adapta o cap à
profundidade do contexto; P29 expõe decode isolado, TTFT e roofline para validar o
ganho no M4 Max.

Fontes: P6, P13, P14, P27, P28, P29, P30, P31, P32, I5, C2, C5 e C8.

### oMLX e o AWQ misto

O `oMLX` expõe uma API compatível com OpenAI.
Ele oferece cache em camadas, MTP e ajustes por modelo.

O AWQ de 5,0 bpw usa quantização mista e group size 64 nas projeções principais.
A revisão fixada inclui a correção da cabeça MTP.

O model card exige `oMLX`.
O loader padrão do `mlx_vlm` pode deslocar norms ao interpretar o namespace `mtp.*`.

Os números publicados usam M5 e kernels NAX.
Eles não medem o Mac Studio M4 Max desta campanha.

Fontes: P17, P20, P23, P24, P25 e C9.

### oQ8e

O oQ8e usa quantização em 8 bits com group size 64 e preserva o MTP. O checkpoint
BF16 fixado é o candidato principal porque a documentação do formato recomenda BF16
em M3/M4; o fp16 permanece apenas como controle curto de desempenho.

O benchmark público de fp16 foi executado em M3 Ultra com oMLX 0.6.2 e combinou MTP,
SpecPrefill, draft Qwen3.5-0.8B e prefill ANE. Esta campanha usa M4 Max, oMLX
0.6.3rc2 e começa com essas acelerações desligadas, portanto os números não são
diretamente comparáveis. O namespace exato usado na página também não é publicado;
há uploads com o mesmo nome e conteúdo diferente.

Fontes: P33, P34, P35, P36, P37 e C10.

### SpecPrefill

SpecPrefill usa a atenção de um draft para escolher tokens importantes do prompt.
O target processa somente o subconjunto escolhido.

O método reduz trabalho de prefill.
Ele não equivale a MTP, PLD ou cache de prefixo.

O `oMLX` aceita um draft, keep rate e threshold por modelo.
Ele também aceita overrides por request.

A correção de I8 persiste somente o prefixo estático do system prompt e das tools.
Ela não transforma o histórico esparso em prefixo integral reutilizável.

Fontes: P20, P21, P22, P26, I7 e I8.

### Prefill pela ANE

O `oMLX` oferece prefill experimental pela Apple Neural Engine.
O recurso usa interfaces privadas e programas de forma fixa.

Resultados públicos mostram diferenças entre gerações de hardware.
O plano exige ajuste e medição locais no M4 Max.

Fontes: P19, P20, I9 e I10.

## Questões que somente o rig pode resolver

1. O `mlx-serve` atual mantém o prefixo após um tool call real?
2. O client reenfileira `reasoning_content` sem normalização?
3. O MTP mantém o estado correto depois de um cache restore?
4. Q4, Q6 ou Q8 reduz o tempo total no M4 Max sem perder qualidade?
5. Q6 ou Q8 recupera falhas funcionais do Q4 recomendado?
6. O cache em SSD reduz o tempo após restart?
7. O runtime mantém memória estável por 20 tool turns?
8. DSpark ou DFlash 2 vence no tempo total, não apenas em decode isolado?
9. O ganho especulativo permanece positivo em 32K e 65K no M4 Max?
10. O modo `auto` resolve o mesmo drafter registrado pelos braços explícitos?
8. Qual draft de SpecPrefill reduz TTFT sem perder as três chaves?
9. O cache estático permanece correto quando SpecPrefill está ativo?
10. O AWQ misto oferece ganho real no M4 Max sem NAX?
11. O prefill pela ANE executa operações e reduz TTFT neste rig?

## Política de uso das fontes

- Prefira fontes primárias para opções e comportamento declarado.
- Use issues abertas como riscos, não como fatos universais.
- Use Reddit para criar hipóteses e escolher braços baratos.
- Use resultados locais para decidir o setup do rig.
- Registre a revisão e a data de cada runtime no resultado final.
