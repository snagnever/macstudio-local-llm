# MiniCPM5-2B

> **Status: 🔴 NO-GO como modelo de suporte (funcional, parked).** Medido em 2026-09-15/16.
> O 2B faz bem as tarefas curtas (formato e idioma em português 100%, 159,7 tok/s solo),
> mas sob carga contínua o driver perde **43–66% do decode** (`T_turno` +43% a +66%) a 32K.
> O s1 **cabe em toda a faixa testada (32K–512K)** — sem erro de contexto e sem swap — mas
> paga +31% a +50% de `T_turno` sob carga contínua; o bloqueio é **velocidade, não memória**.
> Viável só em contexto ≤32K com turnos ≥1 s de intervalo (+12%).
> Last updated: 2026-09-16

Campanha: [`bench/minicpm5-2b-support-2026-09/plan.md`](../../bench/minicpm5-2b-support-2026-09/plan.md)
— veredito em [`results/summary.md`](../../bench/minicpm5-2b-support-2026-09/results/summary.md).

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [openbmb/MiniCPM5-2B](https://huggingface.co/openbmb/MiniCPM5-2B) | HF card |
| Parameters | 2.52B total, 1.98B non-embedding | HF card |
| Architecture | Dense `LlamaForCausalLM`, 42 layers, GQA with 16 query heads and 2 KV heads, `hidden_size` 2048, `head_dim` 128 | HF card + `config.json` |
| Native context | 131,072 tokens | HF card |
| License | Apache 2.0 | HF card |
| Languages | English and Chinese | HF card |
| Reasoning | Hybrid — `enable_thinking` in the chat template toggles a `<think>` block | HF card |
| Tool calling | Own XML format, `<function name="..."><param name="...">`. SGLang has a `minicpm5` parser; `optiq serve` also parses it into OpenAI `tool_calls` | HF card + OptiQ card |
| Vendor sampling | `temperature=1.0, top_p=0.95, min_p=0.0`; add `repetition_penalty=1.05` on loops. llama.cpp defaults `min_p=0.05`, which can loop | HF card |
| Vendor claims | BFCL v4 66.6%, IFEval 86.7%, AIME 2025 86.5%, LiveCodeBench v6 69.1%, SWE-bench Verified 46.4%, LongBench v2 43.7%, average 53.9 *(vendor — not reproduced locally; the AIME and SWE-bench numbers almost certainly use thinking)* | HF card |
| Release | September 2026 *(blog, not confirmed on the HF card)* | [MindStudio](https://www.mindstudio.ai/blog/minicpm5-2b-on-device-model) |

Sibling checkpoints exist for speculative decoding (`MiniCPM5-2B-DSpark`), GGUF, GPTQ and LiteRT-LM.
This card covers the MLX line only.

## Variants on this rig

| API id (dir name) | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `mlx-community-MiniCPM5-2B-OptiQ-4bit-d139292…` | [mlx-community/MiniCPM5-2B-OptiQ-4bit](https://huggingface.co/mlx-community/MiniCPM5-2B-OptiQ-4bit) | MLX safetensors | mixed 4/8-bit, 5.34 bpw achieved (112 of 295 linear layers at 8-bit) | 1.8 GB | untested | ⚪ PLANNED | First choice. Ships `kv_config.json` (per-layer KV plan) and `optiq/metadata.json` |
| `mlx-community-MiniCPM5-2B-8bit-2d20e8e…` | [mlx-community/MiniCPM5-2B-8bit](https://huggingface.co/mlx-community/MiniCPM5-2B-8bit) | MLX safetensors | 8-bit, group size 64, mlx-lm 0.31.3 | 2.5 GB | untested | ⚪ PLANNED | Quality reference for the 4-bit A/B |

**Pinned HF revisions** (downloaded 2026-09-15 with `hf download --revision`, so the pin is exact):
OptiQ: [`d139292`](https://huggingface.co/mlx-community/MiniCPM5-2B-OptiQ-4bit/tree/d1392929adb5693640daeebe6b45e12a07a60b5a) ·
8-bit: [`2d20e8e`](https://huggingface.co/mlx-community/MiniCPM5-2B-8bit/tree/2d20e8e672ce892d50f7265bfd3fc9b59b718f2a).

Local path on the rig: `~/.cache/local-llms/minicpm5-2b-support/<dir name>`.

Repos **not** taken: `openbmb/MiniCPM5-2B-MLX` (4-bit uniform, 1.42 GB, no quant-level benchmark) and
`UraionLabs/MiniCPM5-2B-oQ4e` (oMLX format, 1.48 GB, 182 downloads). A 2B loses more to uniform
4-bit than a large model does, so the mixed quant costs +0.5 GB to protect the sensitive layers.

## Why this model for the support slot

- **Footprint.** 1.8 GB of weights against 8.97 GB for [gemma-4-e4b](gemma-4-e4b.md), the current
  tiny slot. Fewer bytes read per token means less memory-bandwidth taken from the driver.
- **Small KV.** 2 KV heads, `head_dim` 128, 42 layers — about 42 KB per token at fp16 (arithmetic,
  not measured), so a long support context still fits beside the driver's 97–108 GB of wired memory.
- **Tool calling.** Vendor BFCL v4 66.6%; BFCL v3 simple-AST 82.5% on the OptiQ quant without
  thinking. The E4B has tool calling but 14% on MATH and no thinking mode.
- **License.** Apache 2.0.

## Third-party measurements (not this rig)

| Source | Setup | Result |
|---|---|---|
| [mlx-community OptiQ card](https://huggingface.co/mlx-community/MiniCPM5-2B-OptiQ-4bit) | OptiQ 4-bit, non-thinking | MMLU 59.8%, GSM8K 82.1%, IFEval 86.7%, BFCL v3 82.5%, HumanEval 81.1%, HashHop 24.0%, capability score 69.36 — level with the 2.8 GB Qwen3.5-4B-OptiQ-4bit (68.76) |
| [HiQS-Labs/MiniCPM-fork#1](https://github.com/HiQS-Labs/MiniCPM-fork/issues/1) | M1 Max 64 GB, mlx-lm 0.31.3, MLX 4-bit vs Ollama Q4_K_M | MLX 141–143 gen tok/s and 1.558 GB peak memory, ~26% ahead of Ollama; **preliminary, author's own caveat**. Ollama hit a 256-token reasoning cap and returned no content |

The OptiQ card compares its quant against another family, never against bf16 or against uniform
4-bit, so the mixed-precision gain is plausible but undemonstrated. HashHop 24.0% says the model is
weak at long-context retrieval: keep its prompts short.

## Local measurements (2026-09-15/16, M4 Max 128 GB)

Runtime: `optiq serve` 0.5.8 (venv isolado em `~/.local/opt/minicpm5-support/venv`); importar
`optiq` registra o parser MiniCPM5 (`<function name=...>` → OpenAI `tool_calls`) e expõe
`<id>:no-think` / `:think`. `mlx_lm.server` 0.31.3 puro **não** tem esse parser. O `s3`
(gemma-4-e4b) precisa de `mlx_vlm` 0.7.1 — `mlx_lm` não carrega o checkpoint.

| medida | s1 OptiQ-4bit | s2 8-bit |
|---|---|---|
| decode solo @~0,4K | **159,7 tok/s** | 130,8 tok/s |
| decode solo @8K | 117,8 tok/s | 108,1 tok/s |
| TTFT solo @~0,4K / 8K | 0,240 / 3,866 s | 0,248 / 3,874 s |
| tool call → `tool_calls` | sim | sim |
| `:no-think` suprime o reasoning | sim (47 vs 105–112 tokens) | sim |

Concorrência (driver Flash-Next + suporte gerando em laço, `T_turno` do driver):

| arranjo | 32K | 128K | 256K | 512K |
|---|---:|---:|---:|---:|
| driver sozinho | 10,82 s | 12,58 s | 11,48 s | 16,24 s |
| +s1 contínuo | +42,8% | +31,1% | +49,7% | +34,6% |
| +s1 gap 1 s / 3 s | +12,4% / +0,6% | — | — | — |
| +s2 | +48,1% | falha (contexto ~87K, swap +1,0) | — | — |
| +s3 gemma-e4b | +65,5% | +48,7% | — | — |

O s1 **coube em todas as bandas** (256K/512K no perfil 512k, KV 8-bit; `T_turno` +31% a +50%
sob carga contínua). O `s2` é que falha a 128K. Detalhe: `etapa2-maior.md`.

Qualidade em português (s1, 20 tarefas + 10 tool calls): formato 30/30, idioma 30/30,
conteúdo ~28/30 (uma classificação trocada; um argumento traduzido; dois inteiros como string).

Config recomendada (`optiq serve`): `--ngram-draft 16` (+28% no uso típico, **+337%** quando a
saída copia o input; não piora o driver), KV **fp16**, `:no-think` temp 0.7 / top_p 0.95.
**Não** usar `guided_choice` na classificação (piorou, 4/5→3/5). Detalhe: `etapa-tuning.md`.
