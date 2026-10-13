# Qwen3.8-27B: vendor and partner documentation for local inference

Tags: [V]=vendor (Qwen/Alibaba), [P]=partner/engine docs (vLLM, Unsloth), [T]=third-party, [C]=community. All fetched 2026-10-13. Page text was summarized by a fetch tool, so exact wording of long passages is not verbatim. Model is Qwen3.8-27B (released 2026-08-14), not Qwen3 (2025) or Qwen3.6 (2026-04-22).

## Architecture, context length, KV cache vs Qwen3.6-27B

### Takeaway
Qwen3.8-27B is a dense 27B hybrid (48 Gated DeltaNet layers + 16 gated full-attention layers, 3:1) with a vision encoder and one MTP layer. Its config is identical to Qwen3.6-27B for the attention geometry, so KV cache per token is the same (about 64 KiB/token in bf16). Native context is 262,144, extensible to 1M via YaRN factor 4.

### Cited Findings
- [V] Release dates: Qwen3.8-27B 2026-08-14; Qwen3.8-2.4T-A95B 2026-08-12; Qwen3.6-27B 2026-04-22; Qwen3.5-27B 2026-02-24 — [QwenLM/Qwen3.8 README](https://github.com/QwenLM/Qwen3.8)
- [V] Card: causal LM with vision encoder, 27B params (safetensors metadata shows 28B), BF16, hidden 5120, 64 layers laid out as 16 x (3 x Gated DeltaNet->FFN, 1 x Gated Attention->FFN). Gated DeltaNet: 48 V heads, 16 QK heads, head dim 128. Gated Attention: 24 Q heads, 4 KV heads, head dim 256, RoPE dim 64. FFN intermediate 17,408. Vocab 248,320 (padded). MTP "trained with multiple steps". License Apache-2.0. — [HF card](https://huggingface.co/Qwen/Qwen3.8-27B)
- [V] config.json: architecture Qwen3_5ForConditionalGeneration (model_type qwen3_5); 64 layers; full attention every 4th layer; 24 heads / 4 KV heads / head_dim 256; max_position_embeddings 262,144; rope_theta 10,000,000; partial_rotary_factor 0.25; one MTP layer; vision tower 27 layers, hidden 1152, patch 16. — [config.json](https://huggingface.co/Qwen/Qwen3.8-27B/raw/main/config.json)
- [V] Qwen3.6-27B config.json: 64 layers, 3 linear : 1 full pattern (48 linear + 16 full), 24 heads / 4 KV heads / head_dim 256, linear_num_key_heads 16, linear_num_value_heads 48, key/value head dim 128, conv kernel 4, max_position 262,144, mtp_num_hidden_layers 1. Same as 3.8-27B on every field fetched. — [Qwen3.6-27B config](https://huggingface.co/Qwen/Qwen3.6-27B/raw/main/config.json)
- [V] Context: 262,144 native, extensible to 1,000,000. YaRN settings in text_config.rope_parameters: rope_type yarn, factor 4.0, original_max_position_embeddings 262144, rope_theta 10000000, partial_rotary_factor 0.25, mrope_interleaved true, mrope_section [11,11,10]. Card warns static YaRN can hurt short-text performance; use factor 2.0 for ~524K. vLLM needs VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 and --max-model-len 1000000; SGLang needs SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1 and --context-length 1000000. — [HF card](https://huggingface.co/Qwen/Qwen3.8-27B)
- [P] vLLM recipe: 1M context via --hf-overrides nested under text_config; halve YaRN factor to 2.0 for ~524K. Requires transformers >= 5.8.0. — [vLLM recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B)
- [C] Community KV estimate: ~0.5 GB at 8K, 2.0 GB at 32K, 16.4 GB at 262K — [aicybr guide via search](https://aicybr.com/blog/qwen38-27b-local-deployment-guide) (secondary).
- [C] MRCR v2 long-context test on vLLM (15 samples/run, noisy): in-range ~212-227k tokens, BF16 KV 0.833 at 256k, 0.741 at 512k (YaRN f=2), 0.742 at 1M (f=4); FP8 KV 0.717 / 0.737 / 0.742. At ~547k prompt: BF16 KV 0.789, FP8 KV 0.696. BF16 vs FP8 weights: no clear difference. YaRN extension drops BF16 to roughly FP8 level. — [HF discussion 182](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/182)

### Inferences
- KV bytes/token (my arithmetic from config, not a published number): 16 full-attn layers x 2 (K,V) x 4 KV heads x 256 dim x 2 bytes = 65,536 B = 64 KiB. At 262,144 tokens = 16 GiB bf16, matching the 16.4 GB community estimate. Identical to Qwen3.6-27B (same layers/heads/dims). The 48 DeltaNet layers add a fixed-size recurrent state per sequence, not per token.
- fp8 KV would halve this to ~32 KiB/token (arithmetic).

### Gaps
- No vendor-published KV-per-token figure; derived above. Qwen3.8-27B vs 3.6-27B difference is in post-training, not architecture (per config comparison).

## MTP head and speculative decoding depth

### Takeaway
The official checkpoint ships one MTP layer (mtp_num_hidden_layers=1, trained multi-step). The vLLM recipe uses num_speculative_tokens=3 for built-in MTP. The official Qwen cards give no spec-decode flags.

### Cited Findings
- [V] One MTP layer in config; cards say MTP "trained with multiple steps" — [config.json](https://huggingface.co/Qwen/Qwen3.8-27B/raw/main/config.json), [card](https://huggingface.co/Qwen/Qwen3.8-27B)
- [V] FP8 card gives only plain `vllm serve` and `sglang.launch_server` commands, no MTP flags, no parser flags. — [FP8 card](https://huggingface.co/Qwen/Qwen3.8-27B-FP8)
- [P] vLLM recipe: built-in MTP `{"method":"mtp","num_speculative_tokens":3}`; Ascend variant `qwen3_5_mtp` with 3 tokens and enforce_eager. External drafters: DFlash2 `incoai/Qwen3.8-27B-DFlash2` with 7 tokens (vLLM >= 0.28.0); DSpark `RedHatAI/Qwen3.8-27B-speculator.dspark` with 8 tokens. Recipe says to check acceptance via `vllm:spec_decode_num_{accepted,draft}_tokens_total`, not throughput alone. — [vLLM recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B)
- [P] Measured MTP acceptance on 2x RTX 5090: FP8 0.771, NVFP4 (Inferact) 0.897, NVFP4 (unsloth) 0.788. Ascend 950PR W8A8 single-stream ~64 tok/s with MTP. — same recipe
- [P] Unsloth: MTP needs 1-2 GB extra headroom; MTP commands given for vLLM/SGLang (NVFP4) only, not llama.cpp. — [Unsloth Qwen3.8 docs](https://unsloth.ai/docs/models/qwen3.8.md)
- [C] Prefix-cache block size varies with MTP setting; DFlash2 drafter made cache reuse coarser. — [HF discussion 169](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/169)
- [C] Discussion 181 title: "llama.cpp supports DFLash2 now" (content not fetched). — [discussions list](https://huggingface.co/Qwen/Qwen3.8-27B/discussions)
- [T] Community MLX conversion (OrcaRouter) ships a separate mtp/ drafter folder; malekoo bf16 MLX drops MTP and vision. — [orcarouter MLX](https://huggingface.co/orcarouter/Qwen3.8-27B-MLX), [malekoo](https://huggingface.co/malekoo/Qwen3.8-27B-MLX-bf16)

### Inferences
- Depth 3 is the only vendor-ecosystem number for the built-in head; no recipe for depth > 3 with the built-in head.

### Gaps
- No SGLang or TensorRT-LLM MTP depth found (NVIDIA NGC listing seen in search but not fetched). No MLX/llama.cpp MTP guidance from vendor.

## Thinking mode, sampling, output length

### Takeaway
Thinking is on by default; preserve_thinking is on by default; reasoning_effort is xhigh (default) / medium / low; disable with enable_thinking=false. Sampling: thinking T=1.0/top_p 0.95/top_k 20/presence 0; non-thinking T=0.7/top_p 0.8/top_k 20/presence 1.5.

### Cited Findings
- [V] Thinking on by default; disable per request with `enable_thinking: False` via chat_template_kwargs (self-hosted). reasoning_effort: xhigh (default), medium, low; card warns lower effort can raise total latency in multi-turn agent tasks. preserve_thinking on by default (keeps reasoning of all historical messages); set False to keep only latest turn's thinking. — [HF card](https://huggingface.co/Qwen/Qwen3.8-27B)
- [V] Sampling, thinking: temp 1.0, top_p 0.95, top_k 20, min_p 0.0, presence_penalty 0.0, repetition_penalty 1.0. Instruct (non-thinking): temp 0.7, top_p 0.80, top_k 20, min_p 0.0, presence_penalty 1.5, rep penalty 1.0. Presence penalty can go 0-2 against endless repetition but may cause language mixing. No separate "coding" profile found on the card; the thinking profile applies. — same card
- [V] Max output: reasoning up to 262,144 tokens; final response up to 131,072. — same card
- [P] Recipe: `--reasoning-parser qwen3` needed because template opens assistant turn with `<think>`; `--default-chat-template-kwargs` sets server-wide thinking mode. — [vLLM recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B)
- [P] Unsloth: llama.cpp `--chat-template-kwargs '{"reasoning_effort":"medium"}'`; Preserve Thinking uses more tokens but may help continued conversations. — [Unsloth](https://unsloth.ai/docs/models/qwen3.8.md)
- [C] Template: only xhigh and low inject instructions; medium injects nothing (reply says expected). — [discussion 173](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/173)
- [C] Thinking loops (20k-55k tokens) reported on SGLang BF16 + FP8 KV, Q4 GGUF, and 4-bit MLX (LM Studio, MTPLX, oMLX). Diagnoses: SGLang default top_k=-1 (card requires 20), presence_penalty 0 in thinking, reasoning_effort low. Working fix: explicit thinking_budget (2048/6144/16384); repetition penalties/DRY did not help. Unconfirmed whether thinking_budget works on MLX runtimes. — [discussion 178](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/178)
- [C] Reasoning field name: `reasoning` (non-streaming) vs `reasoning_content` (streaming). — [discussion 169](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/169)
- [T] MLX conversion cards say preserve_thinking: runtimes that don't retain reasoning should pass false; parser must handle pre-opened `<think>`. — [leok7v Core ML card](https://huggingface.co/leok7v/Qwen3.8-27B-coreml-q6)

### Inferences
- A client (e.g. oMLX/LM Studio) that strips reasoning from history while the template has preserve_thinking=true is a mismatch to test; vendor says pass false in that case (via T source).

### Gaps
- No vendor "coding mode" sampling profile. No vendor guidance on thinking_budget.

## Official quantized releases, benchmarks, comparison with Flash-Next

### Takeaway
Official FP8 (block 128) exists; vendor says metrics "nearly identical" to BF16 with no numbers. No official 4-bit/8-bit MLX or GGUF guidance. Flash-Next is slightly ahead on most listed benchmarks.

### Cited Findings
- [V] Qwen3.8-27B-FP8: fine-grained FP8, block size 128; tensor types BF16 + F8_E4M3; "nearly identical" performance to original; file size not stated. — [FP8 card](https://huggingface.co/Qwen/Qwen3.8-27B-FP8)
- [V] 27B card benchmarks (27B vs Qwen3.6-27B): Terminal Bench 2.1 (Terminus) 73.0 vs 63.4; SWE-bench Pro 61.7 vs 53.5; QwenSWEBench 79.0 vs 49.3; GPQA Diamond 89.2 vs 87.8; HLE 30.8 vs 24.0; LiveCodeBench v6 90.3 vs 83.9; OSWorld-Verified 84.3 vs 63.9; AndroidWorld 81.9 vs 70.3. Claude Opus 4.6 Max scores higher on Terminal Bench, GPQA, HLE. AIME not seen in fetched summary. — [HF card](https://huggingface.co/Qwen/Qwen3.8-27B)
- [V] FLASH-NEXT ONLY: Qwen3.8-Flash-Next = "125B with 6B activated, plus 51B n-gram embedding and 4B MTP" (safetensors shows 180B), 48 layers, 262,144 ctx (to 1M), one MTP layer. Benchmarks Flash-Next vs 27B: SWE-bench Pro 62.5 vs 61.7; GPQA 91.7 vs 89.2; LiveCodeBench v6 91.9 vs 90.3; HLE 35.9 vs 30.8. Terminal Bench not shown. Same sampling. — [Flash-Next card](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)
- [P] Unsloth memory (RAM+VRAM / unified): 1-bit 7-8 GB, 2-bit 9-11, 3-bit 12-14, 4-bit 16-19, 6-bit 23-26, 8-bit 31, BF16 56 GB. Aug 19 update: 27B GGUFs use Dynamic V3.0 ("10% more accuracy at same size"). UD-Q4_K_XL ~17.9 GB (T). — [Unsloth](https://unsloth.ai/docs/models/qwen3.8.md), [search summary](https://www.unsloth.ai/models/qwen3.8-27b)
- [P] vLLM 2x RTX 5090 weights/GPU: FP8 14.28 GiB, NVFP4 (Inferact) 12.02 GiB. — [vLLM recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B)
- [T] Ollama MLX build qwen3.8:27b-mlx ~18 GB at 4-bit, recommends 24 GB+ (unverified vendor blog). — [search result via orcarouter](https://www.orcarouter.ai/blog/qwen-3-8-27b-mlx)
- [C] Quant comparison threads: NVFP4 shootout (#192), quality-first quants (#157), BabyVision reproduction gap 46% vs 65.7% (#184). Not read in detail. — [discussions](https://huggingface.co/Qwen/Qwen3.8-27B/discussions)

### Inferences
- 4-bit MLX weights ~16-18 GB plus up to 16 GiB bf16 KV at full 262K context.

### Gaps
- No official 4/8-bit loss numbers. AIME and exact Terminal-Bench harness details for 27B not captured. Fetch tool returned a Terminal Bench 2.1 number for Flash-Next as "not listed".

## Engines, parsers, Apple Silicon / MLX, template issues

### Takeaway
Official engines: SGLang, vLLM, TokenSpeed, Transformers; parsers qwen3_coder (tools) and qwen3 (reasoning). Vendor README says mlx-lm/mlx-vlm and llama.cpp support the Qwen3.5 series but does not name Qwen3.8. No vendor MLX flags.

### Cited Findings
- [V] README: tool-call parser `qwen3_coder` on all three engines; reasoning parser `qwen3`; vLLM/TokenSpeed need `--enable-auto-tool-choice`. Transformers: `transformers serve Qwen/Qwen3.8-27B --port 8000 --continuous-batching`. Qwen-Agent not mentioned. — [README](https://github.com/QwenLM/Qwen3.8)
- [V] README: "llama.cpp supports Qwen3.5 series"; "mlx-lm text only, mlx-vlm vision+text, both support Qwen3.5 series"; Qwen3.8 not stated specifically. Card lists 1,442 quantized models for llama.cpp/Ollama/LM Studio/Jan. KTransformers recommended for Flash-Next production (Flash-Next only). — [README](https://github.com/QwenLM/Qwen3.8), [card](https://huggingface.co/Qwen/Qwen3.8-27B)
- [P] vLLM recipe uses `--kv-cache-dtype fp8`, `--reasoning-parser qwen3`, `--tool-call-parser qwen3_coder`; MXFP4 unsupported on NVIDIA. — [vLLM recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B)
- [P] Unsloth llama.cpp: standard build works (Metal default on); run with `--temp 1.0 --top-p 0.95 --top-k 20 --min-p 0.0`; mmproj needed for vision. — [Unsloth](https://unsloth.ai/docs/models/qwen3.8.md)
- [T] Third-party (via search summary, weak): GGUF uses `qwen35` arch, needs current llama.cpp; "official chat template has a known bug breaking multi-turn history, use --jinja / corrected template". Unsloth's own page (fetched) did NOT mention this bug, so treat as unverified. — [search summary](https://unsloth.ai/docs/models/qwen3.8.md)
- [T] mlx-lm: `pip install -U mlx-lm`; `mlx_lm.server`; model field must match /v1/models id. — [orcarouter MLX card](https://huggingface.co/orcarouter/Qwen3.8-27B-MLX)
- [C] Template PR #203 (one-line change to chat_template.jinja, a reviewer asked why a `content is tiger`-style condition; unmerged/unanswered at fetch). Discussion 173 on reasoning_effort. Tool-call issues: #212 (OpenRouter Persian), #193 (AMD tool agent with 4 quants). Prefix cache on hybrid (#169): 1,584-token blocks, lazy (cache created on 2nd request, read on 3rd), 7.5x TTFT on 48K prompt; needs --enable-prompt-tokens-details for cached_tokens. — [discussion 203](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/203), [169](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/169)
- No discussion mentioned MLX or preserve_thinking in titles (14 closed discussions hidden, not checked). — [discussions list](https://huggingface.co/Qwen/Qwen3.8-27B/discussions)

### Inferences
- On Apple Silicon the vendor-supported path is effectively "community MLX/GGUF + vendor sampling/template kwargs"; test parser handling of pre-opened `<think>` and preserve_thinking.

### Gaps
- Discussion 39 (cited in the brief) not located; the list showed only open discussions numbered 157+. The date shown on #203 ("March 2026") conflicts with release date 2026-08-14 and is likely a fetch artifact. recipes TRT-LLM/NVIDIA NIM guides and Qwen blog not fetched. HF commit hashes not retrieved.
