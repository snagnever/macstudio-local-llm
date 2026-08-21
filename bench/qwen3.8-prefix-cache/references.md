# Qwen3.8-27B prefix-cache campaign — referências

> **Data da revisão:** 2026-08-21

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
| P10 | [Unsloth Qwen3.8 GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) | Arquivos Q6, Q8 e tamanhos |
| P11 | [Unsloth Dynamic 3.0](https://unsloth.ai/docs/basics/dynamic-3.0-ggufs) | Método e métricas de quantização |

## Issues e discussões técnicas

| ID | Fonte | Risco coberto |
|---|---|---|
| I1 | [Qwen chat template breaks KV-cache reuse](https://github.com/QwenLM/Qwen3/issues/1826) | Mudança dos tokens históricos |
| I2 | [Qwen3.6 historical think-block drift](https://github.com/QwenLM/Qwen3.6/issues/131) | Normalização de reasoning e tool calls |
| I3 | [llama.cpp hybrid cache reuse issue](https://github.com/ggml-org/llama.cpp/issues/18497) | Reutilização em modelos recorrentes |
| I4 | [llama.cpp host-memory prompt caching](https://github.com/ggml-org/llama.cpp/discussions/20574) | Capacidade e operação do cache em RAM |
| I5 | [mlx-dspark prefix cache never hits](https://github.com/ARahim3/mlx-dspark/issues/7) | Motivo para adiar DSpark |
| I6 | [Qwen3.8 preserve_thinking for llama.cpp](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/39) | Flags do template no GGUF |

## Relatos comunitários

| ID | Fonte | Sinal útil | Limite |
|---|---|---|---|
| C1 | [Introducing Qwen3.8 Dynamic v3 Unsloth GGUFs](https://www.reddit.com/r/LocalLLaMA/comments/1vsr67c/introducing_qwen3827b_dynamic_v3_unsloth_ggufs/) | Nova família Dynamic v3 | Post do fornecedor |
| C2 | [Qwen3.8 on 2x 3090 with vLLM and DFlash2](https://www.reddit.com/r/LocalLLaMA/comments/1vsccit/qwen3827b_on_2x_3090_vllm_dflash2_218_toks_single/) | Especulação depende do tipo de saída | CUDA, não Apple Silicon |
| C3 | [Dynamic 3.0 independent comparison](https://www.reddit.com/r/LocalLLM/comments/1vt9ucx/the_new_unsloth_dynamic_30_quants_are_real_good/) | Q6 perto de Q8 em métricas indiretas | Não mede agent loops |
| C4 | [Qwen3.8 not caching context on MLX](https://www.reddit.com/r/LocalLLM/comments/1vozpl6/qwen_38_27b_not_caching_context_on_mlx/) | Decode rápido pode perder no tempo total | Relato individual |
| C5 | [Qwen3.8 up to 3x faster with mlx-dspark](https://www.reddit.com/r/LocalLLaMA/comments/1vokrcy/qwen3827b_is_now_up_to_3_faster_on_apple_silicon/) | DSpark merece fase posterior | Cache ainda tem issue aberto |
| C6 | [Qwen3.8 forks on M4 Max 128 GB](https://www.reddit.com/r/LocalLLaMA/comments/1vq50xf/having_all_those_qwen_38_27b_forks_which_one/) | MLX é o ponto inicial no Mac | Recomendações sem protocolo comum |
| C7 | [Q6_K_XL on M2 Ultra](https://www.reddit.com/r/LocalLLaMA/comments/1vr3s7j/qwen3827b_q6_k_xl_speeds_on_m2_ultra_192gb_what/) | Flags de cache e MTP no `llama.cpp` | Hardware diferente |
| C8 | [vLLM hybrid cache and MTP field notes](https://www.reddit.com/r/LocalLLaMA/comments/1vspexl/qwen38_27b_via_vllm_i_love_it_and_i_hate_it_here/) | Cache e especulação precisam de teste conjunto | CUDA e patches comunitários |

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

O Dynamic v3 Q6 é o primeiro GGUF da campanha.
O Q8 funciona como referência de qualidade.

Os dados públicos disponíveis usam perplexidade, divergência e correspondência de tokens.
Eles não comprovam qualidade em Terminal-Bench.

Fontes: P10, P11, C1 e C3.

### Speculative decoding

MTP, DFlash e DSpark podem acelerar código mais que prosa.
O ganho depende da taxa de aceitação e do custo de verificação.

Esta campanha testa MTP primeiro. Ela adia DFlash e DSpark.

Fontes: P6, C2, C5 e C8.

## Questões que somente o rig pode resolver

1. O `mlx-serve` atual mantém o prefixo após um tool call real?
2. O client reenfileira `reasoning_content` sem normalização?
3. O MTP mantém o estado correto depois de um cache restore?
4. Q6 reduz o tempo total no M4 Max?
5. Q8 recupera falhas funcionais do Q6?
6. O cache em SSD reduz o tempo após restart?
7. O runtime mantém memória estável por 20 tool turns?

## Política de uso das fontes

- Prefira fontes primárias para opções e comportamento declarado.
- Use issues abertas como riscos, não como fatos universais.
- Use Reddit para criar hipóteses e escolher braços baratos.
- Use resultados locais para decidir o setup do rig.
- Registre a revisão e a data de cada runtime no resultado final.
