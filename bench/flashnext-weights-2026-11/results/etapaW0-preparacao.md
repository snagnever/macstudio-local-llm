# Task W0: Preparação (2026-11-08)

**7 de 8 braços carregam no Splash 1.5.0, e o `k7` sai da fila.** O Splash 1.5.0 e o 1.6.0 recusam os tensores `hc_attn_inject` e `hc_ffn_inject` em `IQ4_XS` do ThinkingCap. O `k8` carrega depois de uma pasta `Q2_0/` de symlinks no cache do Hugging Face.

## Downloads

`hf download` (uvx `huggingface_hub` 2.4.0) com `--revision` e `--include`. Todos terminam com exit 0. Disco livre: 1301 GB antes e 862 GB depois.

| braço | repositório @ revisão | variante | esperado | baixado | tempo |
|---|---|---|---:|---:|---:|
| `k6` | `unsloth/Qwen3.8-Flash-Next-GGUF` @ `084c631` | `UD-IQ4_XS` | 93.7 GB | 93.7 GB | 17.7 min |
| `k1` | `unsloth/Qwen3.8-Flash-Next-GGUF` @ `766911a` | `UD-IQ4_XS` | 93.7 GB | 93.7 GB | 17.6 min |
| `k7` | `bottlecapai/ThinkingCap-Qwen3.8-Flash-Next-GGUF` @ `2a053f7` | `IQ4_XS` | 95.5 GB | 95.5 GB | 18.5 min |
| `k5` | `unsloth/Qwen3.8-Flash-Next-GGUF` @ `084c631` | `UD-IQ3_XXS` | 83.6 GB | 83.6 GB | 10.5 min |
| `k8` | `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF` @ `99bb8f7` | `Q2_0` | 66.6 GB | 66.5 GB | 12.7 min |
| `k4` | `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF` @ `ed59f92` | `Q2_0` | 66.4 GB | 66.4 GB | 12.7 min |

- O `k1` saiu do cache depois da campanha anterior, então a W0 baixou o pack de novo.
- Os scripts `hf` dos pacotes do Splash apontam para um interpretador que não existe (exit 126). A W0 usa o `hf` do uvx.

## Smoke

`run-arm.sh <braço> 32768 --repeat 1 --tag smoke`, Splash 1.5.0. Cada braço faz 5 requests. A RAM pico e o swap Δ vêm dos campos `ram_peak_gb` e `swap_delta_gb` do JSONL.

| braço | peso | carga dos pesos | acertos | decode p50 | RAM pico | swap Δ |
|---|---|---:|---:|---:|---:|---:|
| `k2f` | Swift 1.5 `IQ4_XS` | 20.7 s | 5/5 | 109.6 tok/s | 106.4 GB | 0 |
| `k6f` | unsloth `UD-IQ4_XS` V3.1 | 11.3 s | 5/5 | 105.7 tok/s | 102.9 GB | 0 |
| `k1f` | unsloth `UD-IQ4_XS` base | 8.6 s | 5/5 | 95.1 tok/s | 108.6 GB | 0 |
| `k7f` | ThinkingCap `IQ4_XS` | **recusado** | – | – | – | – |
| `k5f` | unsloth `UD-IQ3_XXS` V3.1 | 7.8 s | 5/5 | 106.3 tok/s | 92.6 GB | 0 |
| `k8f` | Swift 1.5 GSQ-RCO `Q2_0` | 4.7 s | 4/5 | 126.8 tok/s | 74.9 GB | 0 |
| `k4f` | ISTA GSQ-RCO `Q2_0` | 4.5 s | 5/5 | 118.4 tok/s | 74.7 GB | 0 |
| `k3f` | ISTA GSQ-RCO-Coder `IQ1_M` | 12.0 s | 5/5 | 110.2 tok/s | 67.5 GB | 0 |

- O erro do `k8f` é um request que chegou ao limite de 4096 tokens sem resposta (`finish_reason: length`). O smoke só confere a carga, então o braço fica na fila. A W1 mede a qualidade.
- A carga dos pesos é o tempo do log de boot. O primeiro boot de cada pack também inclui a instalação a partir do cache.
- O smoke usa 32768 tokens e 1 rep. O decode dele não é um resultado.

## `k7` e `k8`: GGUF dividido na raiz

Os dois repositórios têm os arquivos divididos na raiz, sem pasta `VARIANT/`.

1. No primeiro boot, o Splash 1.5.0 recusa os dois: `no single GGUF matches :IQ4_XS` e `:Q2_0`.
2. A W0 cria uma pasta `VARIANT/` no snapshot de cada um, com symlinks para os mesmos blobs: `IQ4_XS/` no `k7` e `Q2_0/` no `k8`. O boot usa `HF_HUB_OFFLINE`, como no `k2m`.
3. Com a pasta, o `k8f` carrega e passa no smoke.
4. O `k7f` passa pela escolha de arquivos, mas o Splash 1.5.0 recusa o conteúdo: `this GGUF stores tensors Splash cannot load: hc_attn_inject.weight IQ4_XS (48 tensors), hc_ffn_inject.weight IQ4_XS (48 tensors)`.
5. O Splash 1.6.0 dá o mesmo erro (`logs/k7g-loadcheck.log`, só a carga).

Pela Step 5, o `k7` sai da fila. `scripts/run-queue.sh` agora roda `k2 k6 k1 k5 k8 k4 k3`.

As pastas `VARIANT/` ficam no cache do rig, fora do repositório. Um `hf download` novo do `k8` não as cria de novo.

## Estado do rig

Swap: 1751 MB de 3072 MB, sem mudança durante a W0. Nenhuma condição de parada.
