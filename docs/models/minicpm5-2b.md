# MiniCPM5-2B

> **Status: ⚪ PLANNED — support-model candidate.** Intended role: a small model that runs
> **in parallel** with the [qwen3.8-flash-next](qwen3.8-flash-next.md) driver and absorbs short,
> non-reasoning turns (session titles, commit messages, classification, short summaries, simple
> tool calls). The driver does not batch decode, so parallel requests queue on one slot; a second
> resident model is the only way to get real concurrency.
> Two MLX quants are on the rig. **Nothing is measured locally yet.**
> Last updated: 2026-09-15

Campaign that will test it: [`bench/minicpm5-2b-support-2026-09/plan.md`](../../bench/minicpm5-2b-support-2026-09/plan.md).

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

## What is not measured here yet

- Decode and prefill on the M4 Max, alone and while the driver generates.
- The driver's `T_turno` penalty under concurrency — the number that decides the whole idea.
- Whether any MLX server on the rig parses the XML tool-call format. `optiq serve` (the `mlx-optiq`
  package) does; `mlx_lm.server` has no such parser and `mlx-serve` is unchecked.
- Portuguese quality. The card lists English and Chinese only, and the support tasks (titles,
  commit messages, summaries) run in Portuguese here.
- OptiQ 4-bit against 8-bit on those same tasks.
