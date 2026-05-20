# Local LLM Quality Benchmarks vs Frontier Models

**Date:** 2026-05-17
**Rig:** Mac Studio M4 Max, 128 GB unified memory, LM Studio + MLX
**Frontier baselines used:** GPT-5 (Aug 2025 release), Claude Opus 4.5 (Nov 2025), Claude Sonnet 4.6 (Feb 2026), Gemini 3 Pro (Nov 2025), Kimi K2.6 (Apr 2026) and DeepSeek V4 Pro (Apr 2026) as top open-weight references.

## Conventions

- All "Local model score" numbers come from the upstream model card / blog of the **base un-quantized model** unless otherwise noted. The user's on-disk quant is identified explicitly; quant-vs-base deltas are flagged in the "quant caveat" line under each table.
- "n/a" = number not published by the upstream author for that benchmark, or not measured publicly on the exact quant.
- Where Anthropic has not published an exact number, the most-cited third-party transcription of the Anthropic chart is used and labelled as such.

---

## 1. `qwen/qwen3-coder-next` — 80B / 3B-active MoE, MLX 6-bit (also 4-bit on disk)

Role: agentic coder. Upstream: `Qwen/Qwen3-Coder-Next` (Qwen team, Mar 2026).

| Benchmark | Qwen3-Coder-Next | GPT-5 | Opus 4.5 | Sonnet 4.6 | Gemini 3 Pro | Top open-weights (Kimi K2.6) |
|---|---|---|---|---|---|---|
| SWE-bench Verified | 70.6–71.3% (scaffold-dependent) | 74.9% | 80.9% | 79.6% (80.2% w/ prompt) | 76.2% | 80.2% |
| SWE-bench Multilingual | 63.7% | n/a | leads "7/8 langs" | n/a | n/a | 76.7% |
| SWE-bench Pro | 44.3% | 58.6% (5.5) / n/a (5.0) | 45.9% | n/a | n/a | 58.6% |
| Terminal-Bench 2.0 | 36.2% | 82.7% (5.5) / n/a (5.0) | 59.3% | 59.1% | 54.2% | 66.7% |
| Aider Polyglot | 66.2% | 88.0% | 10.6pt over Sonnet 4.5 (≈81–83%) | n/a | n/a | n/a |
| LiveCodeBench v6 | not officially reported; community ~80% | n/a | n/a | ~80% | n/a | 89.6% |

**Quant caveat:** The on-disk quants are MLX 6-bit (primary) and MLX 4-bit. The numbers above are for the unquantized base. Community Qwen3 quant studies (Awni Hannun perplexity sweep on Qwen3, plus Unsloth's Qwen3-Coder-Next Q4_K_M analysis) report ~99% retention of BF16 SWE-bench/HumanEval performance at Q4-class quant, and effectively lossless at 6-bit. Expect MLX-6bit to land within ≤1pt of base on SWE-bench. The 4-bit MLX version may lose 1–3pt; DWQ-style 4-bit is closer to lossless than plain RTN 4-bit.

Sources:
- [Qwen3-Coder-Next blog](https://qwen.ai/blog?id=qwen3-coder-next)
- [Qwen3-Coder-Next Technical Report (arXiv 2603.00729)](https://arxiv.org/pdf/2603.00729)
- [Unsloth: Qwen3-Coder-Next docs](https://unsloth.ai/docs/models/qwen3-coder-next)
- [Awni Hannun: Qwen3 MLX quant perplexity study](https://x.com/awnihannun/status/1925270481642598436)
- [GPT-5 announcement (74.9 SWE / 88 Aider / 94.6 AIME)](https://openai.com/index/introducing-gpt-5/)
- [Opus 4.5 announcement (80.9 SWE Verified)](https://www.anthropic.com/news/claude-opus-4-5)
- [Sonnet 4.6 announcement (79.6 SWE Verified, 80.2 w/ prompt mod)](https://www.anthropic.com/news/claude-sonnet-4-6)
- [Gemini 3 Pro announcement (76.2 SWE Verified, 54.2 Terminal-Bench)](https://blog.google/products-and-platforms/products/gemini/gemini-3/)
- [Kimi K2.6 model card (80.2 SWE Verified, 66.7 Terminal-Bench, 89.6 LiveCodeBench)](https://huggingface.co/moonshotai/Kimi-K2.6)

---

## 2. `qwen3.6-27b` — 27B dense, MLX 6-bit

Role: reasoning specialist. Upstream: `Qwen/Qwen3.6-27B` (Apr 2026, Apache-2.0). The on-disk weights are the multimodal/thinking model; numbers below are from the official Qwen3.6-27B model card.

| Benchmark | Qwen3.6-27B | GPT-5 | Opus 4.5 | Sonnet 4.6 | Gemini 3 Pro | Top open-weights (Kimi K2.6) |
|---|---|---|---|---|---|---|
| MMLU-Pro | 86.2 | ~85–87 (AA Intelligence Index input) | 89.5–90.0 | 79.2 | ~91.0 (per V4 card comparison) | n/a (vision-strong) |
| GPQA Diamond | 87.8 | 88.4 (Pro) / 89.4 (5) | 87.0 | 74.1 | 91.9 (93.8 Deep Think) | 90.5 |
| AIME 2026 | 94.1 | 100 (AIME 2025) | n/a | 98 (AIME 2025, per third-party) | n/a (Apex 23.4) | 96.4 |
| LiveCodeBench v6 | 83.9 | n/a | n/a | ~80 | n/a | 89.6 |
| SWE-bench Verified | 77.2 | 74.9 | 80.9 | 79.6 | 76.2 | 80.2 |
| MMMU | 82.9 | 84.2 | 80.7 | n/a | 81.0 (MMMU-Pro) | 79.4 (MMMU-Pro) |
| HLE (no tools) | 24.0 | 42 | n/a | n/a | 37.5 | 54.0 (w/ tools) |

**Quant caveat:** On-disk is MLX 6-bit. For 27B-class dense models, Awni Hannun's MLX quant sweep and the Qwen3.6 quant deep-dive both show 6-bit is essentially lossless vs BF16 (perplexity delta well under 1%). Mixed-precision oQ6 vs RTN-6bit shows ~13% lower mean KLD but both are excellent. Expect this on-disk quant to track the card numbers within ~0.5pt.

Sources:
- [Qwen3.6-27B model card on Hugging Face](https://huggingface.co/Qwen/Qwen3.6-27B)
- [Qwen3.6-27B blog](https://qwen.ai/blog?id=qwen3.6-27b)
- [GPT-5 announcement](https://openai.com/index/introducing-gpt-5/)
- [Vellum: Claude Opus 4.5 benchmarks](https://www.vellum.ai/blog/claude-opus-4-5-benchmarks)
- [Morph: Claude benchmark tracker (Opus 4.6 91.3 GPQA, Sonnet 4.6 74.1 GPQA)](https://www.morphllm.com/claude-benchmarks)
- [Gemini 3 Pro (Vellum transcription)](https://www.vellum.ai/blog/google-gemini-3-benchmarks)
- [Kimi K2.6 model card](https://huggingface.co/moonshotai/Kimi-K2.6)
- [Qwen3.6 quantization deep dive (BF16 vs Q4_K_M vs Q8)](https://dasroot.net/posts/2026/05/qwen-36-quantization-bf16-gguf-q4-k-m-q8-0/)
- [MLX quantization quality (KL divergence study)](https://smcleod.net/2026/04/measuring-model-quantisation-quality-with-kl-divergence/)

---

## 3. `qwen3.6-35b-a3b` — 35B / 3B-active MoE, MLX 6-bit

Role: fast generalist. Upstream: `Qwen/Qwen3.6-35B-A3B` (Apr 16, 2026, Apache-2.0).

| Benchmark | Qwen3.6-35B-A3B | GPT-5 | Opus 4.5 | Sonnet 4.6 | Gemini 3 Pro | Top open-weights (Kimi K2.6) |
|---|---|---|---|---|---|---|
| MMLU-Pro | 85.2 | ~85–87 | 89.5–90.0 | 79.2 | ~91.0 | n/a |
| GPQA Diamond | 86.0 | 88.4 (Pro) | 87.0 | 74.1 | 91.9 | 90.5 |
| AIME 2026 | 92.7 | 100 (AIME 2025) | n/a | 98 (AIME 2025) | n/a (Apex 23.4) | 96.4 |
| LiveCodeBench v6 | 80.4 | n/a | n/a | ~80 | n/a | 89.6 |
| SWE-bench Verified | 73.4 | 74.9 | 80.9 | 79.6 | 76.2 | 80.2 |
| Terminal-Bench 2.0 | 51.5 | 82.7 (5.5) | 59.3 | 59.1 | 54.2 | 66.7 |

**Quant caveat:** On-disk is MLX 6-bit. There is a documented MoE-specific 4-bit/8-bit MLX issue for Qwen3.x-A3B (multi-turn tool calling degrades on mlx-community 4-bit/8-bit checkpoints but NOT on GGUF Q4_K_XL or full-precision cloud). 6-bit MLX has not shown the same degradation in public reports; on the static benchmarks above, expect ≤1pt loss vs BF16 at 6-bit. Tool-call-heavy workloads may be more fragile than these static evals suggest.

Sources:
- [Qwen3.6-35B-A3B model card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)
- [Qwen3.6-35B-A3B blog](https://qwen.ai/blog?id=qwen3.6-35b-a3b)
- [MLX issue: Qwen3.5-35B-A3B multi-turn tool-calling degradation](https://github.com/ml-explore/mlx-lm/issues/1011)
- Frontier sources as in section 2.

---

## 4. `gemma-4-26b-a4b-it-mlx` — 26B / 4B-active MoE, MLX 4-bit

Role: knowledge generalist + vision. Upstream: `google/gemma-4-26B-A4B-it` (Apr 2, 2026).

| Benchmark | Gemma 4 26B-A4B | GPT-5 | Opus 4.5 | Sonnet 4.6 | Gemini 3 Pro | Top open-weights (Kimi K2.6) |
|---|---|---|---|---|---|---|
| MMLU-Pro | 82.6 | ~85–87 | 89.5–90.0 | 79.2 | ~91.0 | n/a |
| GPQA Diamond | 82.3 | 88.4 (Pro) | 87.0 | 74.1 | 91.9 | 90.5 |
| AIME 2026 (no tools) | 88.3 | 100 (AIME 2025) | n/a | 98 (AIME 2025) | n/a | 96.4 |
| LiveCodeBench v6 | 77.1 | n/a | n/a | ~80 | n/a | 89.6 |
| MMMU-Pro | 73.8 | 84.2 (MMMU) | 80.7 (MMMU) | n/a | 81.0 (MMMU-Pro) | 79.4 |
| BigBench Extra Hard | 64.8 | n/a | n/a | n/a | n/a | n/a |
| MRCR-v2 128k (8 needle) | 44.1 | n/a | n/a | n/a | n/a | n/a |

**Quant caveat:** On-disk is MLX 4-bit. This is the most quantization-sensitive model in the user's set. Community Gemma-4 GGUF analyses report Q4_K_M retains ~96–98% of BF16 on most benchmarks; **uniform MLX 4-bit is documented to be ~4.7× worse on perplexity than llama.cpp K-quants** for Gemma 4. Expect 1–3pt loss on MMLU-Pro/GPQA-class evals and possibly 3–5pt on hard math/code unless this is a DWQ or mixed-precision MLX build. If the on-disk file is plain RTN 4-bit MLX, consider switching to a GGUF Q4_K_M or MLX-DWQ-4bit build for quality.

Sources:
- [Gemma 4 26B-A4B-it model card](https://huggingface.co/google/gemma-4-26B-A4B-it)
- [Gemma 4 specs & benchmarks overview](https://aurigait.com/blog/gemma-4-features-benchmarks-guide/)
- [GGUF vs MLX 4-bit for Gemma 4 on Apple Silicon](https://theagenttimes.com/articles/gguf-outpaces-mlx-for-gemma-4-on-apple-silicon-developers-re-ca3911a0)
- [MLX quant KL-divergence study (RTN-4 vs DWQ-4 etc.)](https://smcleod.net/2026/04/measuring-model-quantisation-quality-with-kl-divergence/)
- Frontier sources as above.

---

## 5. `nvidia/nemotron-3-nano-omni` — 30B / 3B-active MoE, GGUF Q4_K_M

Role: experimental multimodal MoE (text + image + video + audio). Upstream: `nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16` (Apr 27, 2026).

| Benchmark | Nemotron 3 Nano Omni | GPT-5 | Opus 4.5 | Sonnet 4.6 | Gemini 3 Pro | Top open-weights (Kimi K2.6) |
|---|---|---|---|---|---|---|
| MMLU-Pro | 78.3 (Nemotron 3 Nano family) | ~85–87 | 89.5–90.0 | 79.2 | ~91.0 | n/a |
| GPQA Diamond | 73.0 (no tools) / 75.0 (w/ tools) | 88.4 (Pro) | 87.0 | 74.1 | 91.9 | 90.5 |
| AIME 2025 | 89.1 (no tools) / 99.2 (w/ tools) | 100 | n/a | 98 | n/a | 96.4 (AIME 2026) |
| OCRBench v2 (En) | 65.8 / 67.0 | n/a | n/a | n/a | n/a | n/a |
| MMlongBench-Doc | 57.5 | n/a | n/a | n/a | n/a | n/a |
| OSWorld | 47.4 | n/a | 72.7 (Opus 4.6) | 72.5 | n/a | 73.1 |
| Video-MME | 72.2 | n/a | n/a | n/a | 87.6 (Video-MMMU) | n/a |
| VoiceBench | 89.4 | n/a | n/a | n/a | n/a | n/a |
| AA Intelligence Index | 21 | 68 (High effort) | top tier | top tier | top tier | top tier |

**Quant caveat:** On-disk is GGUF Q4_K_M. NVIDIA's own model card publishes BF16 vs FP8 vs NVFP4 deltas for the multimodal evals (e.g. MathVista 71.90 BF16 vs 71.30 NVFP4 — within 1 point on average; mean of 9 non-ASR benches: BF16 65.80 → FP8 65.40 → NVFP4 65.43). No NVIDIA-published Q4_K_M number exists, but Q4_K_M typically lands between FP8 and FP4 in quality on K-quant benchmarks — expect ≤1pt loss on most non-ASR tasks. ASR (WER) is essentially unchanged. The text-reasoning numbers (MMLU-Pro 78.3, GPQA 73, AIME 89) come from the Nemotron 3 Nano (text) sibling — Omni's specific text-reasoning numbers are not all separately published; treat those rows as an upper bound for Omni text reasoning.

Sources:
- [Nemotron 3 Nano Omni model card (NVIDIA HF)](https://huggingface.co/nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16)
- [HF blog: Nemotron 3 Nano Omni multimodal intelligence](https://huggingface.co/blog/nvidia/nemotron-3-nano-omni-multimodal-intelligence)
- [Nemotron 3 Nano Omni report PDF](https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Omni-report.pdf)
- [Artificial Analysis: Nemotron 3 Nano Omni (AA Index 21)](https://artificialanalysis.ai/models/nemotron-3-nano-omni-30b-a3b)
- [NeMo Evaluator reproducibility recipe (MMLU-Pro 78.3, AIME 89.06, GPQA 73)](https://github.com/NVIDIA-NeMo/Evaluator/blob/main/packages/nemo-evaluator-launcher/examples/nemotron/nano-v3-reproducibility.md)

---

## 6. `google/gemma-4-e4b` — 7.5B / 4.5B-effective, GGUF Q4_K_M

Role: tiny / fast / vision. Upstream: `google/gemma-4-E4B-it`.

| Benchmark | Gemma 4 E4B | GPT-5 | Opus 4.5 | Sonnet 4.6 | Gemini 3 Pro | Top open-weights (Kimi K2.6) |
|---|---|---|---|---|---|---|
| MMLU-Pro | 69.4 | ~85–87 | 89.5–90.0 | 79.2 | ~91.0 | n/a |
| GPQA Diamond | 58.6 | 88.4 (Pro) | 87.0 | 74.1 | 91.9 | 90.5 |
| AIME 2026 (no tools) | 42.5 | 100 (AIME 2025) | n/a | 98 (AIME 2025) | n/a | 96.4 |
| LiveCodeBench v6 | 52.0 | n/a | n/a | ~80 | n/a | 89.6 |
| MMMU-Pro | 52.6 | 84.2 (MMMU) | 80.7 (MMMU) | n/a | 81.0 (MMMU-Pro) | 79.4 |
| MATH-Vision | 59.5 | n/a | n/a | n/a | n/a | 87.4 |
| Codeforces ELO | 940 | n/a | n/a | n/a | n/a | n/a |

**Quant caveat:** On-disk is GGUF Q4_K_M. For ~5B-class models, Q4_K_M quality drop is typically larger than for big models (small dense models are more quant-sensitive). Generic Q4_K_M vs BF16 perplexity delta is +0.1–0.3 (~1–3% PPL increase, 0–2% on MMLU/GSM8K). For Gemma 4 E4B specifically there is no published Q4_K_M benchmark number — expect ~2–4pt loss on hard reasoning and minimal loss on chat/RAG. Q8 GGUF would close most of the gap if you have headroom (you do, on 128 GB).

Sources:
- [Gemma 4 E4B model card](https://huggingface.co/google/gemma-4-e4b-it)
- [Gemma 4 GGUF quantization guide](https://gemma4-ai.com/blog/gemma4-gguf-guide)
- [Q4_K_M perplexity / quality references](https://willitrunai.com/blog/quantization-guide-gguf-explained)
- Frontier sources as above.

---

## 7. `deepseek-v4-flash-dq` — DeepSeek V4 Flash, MLX 2-bit DQ (dynamic mixed-precision)

Role: frontier reasoning at home. Upstream: `deepseek-ai/DeepSeek-V4-Flash`, 284B / 13B-active MoE, ships in mixed FP4+FP8 already. The user's on-disk file is `mlx-community/DeepSeek-V4-Flash-2bit-DQ` (or `2bit-M-DQ`), ~96.5 GB on disk.

| Benchmark | DeepSeek V4 Flash | GPT-5 | Opus 4.5 / 4.6 | Sonnet 4.6 | Gemini 3 Pro | Kimi K2.6 |
|---|---|---|---|---|---|---|
| MMLU-Pro | 86.4 | ~85–87 | 89.5–90.0 / 89.1 | 79.2 | 91.0 | n/a |
| GPQA Diamond | 88.1 | 88.4 (Pro) / 89.4 (5) | 87.0 / 91.3 | 74.1 | 91.9 (93.8 Deep Think) | 90.5 |
| AIME (latest year) | n/a (V4 family +17.5pt over V3 on AIME 2025 → ~87.5) | 100 (AIME 2025) | n/a | 98 (AIME 2025) | n/a | 96.4 (AIME 2026) |
| SWE-bench Verified | 79.0 (max thinking) | 74.9 | 80.9 / 80.8 | 79.6 | 76.2 | 80.2 |
| Terminal-Bench 2.0 | 56.9 | 82.7 (5.5) | 59.3 / 65.4 | 59.1 | 54.2 | 66.7 |
| LiveCodeBench | 91.6 (max thinking) | n/a | 88.8 (Opus 4.6 max) | ~80 | 91.7 | 89.6 |
| HLE (w/ tools) | 45.1 | 42 | 43.2 (4.5) | n/a | 37.5 (no tools) | 54.0 |
| MRCR 1M | 78.7 | n/a | n/a | n/a | n/a | n/a |

**Quant caveat:** On-disk is `2bit-DQ` MLX (dynamic mixed-precision: most routed MoE experts at 2-bit, sensitive layers at 4/6/8-bit). DeepSeek V4 Flash ships natively at FP4+FP8, so the headroom for further compression is genuinely small. The MLX-community 2-bit-DQ card explicitly warns: "Q4_K_M GGUF retains most of the source quality, dropping below that is fragile, as the QAT FP4 experts in V4 leave no room for aggressive compression." No public benchmark deltas for 2-bit-DQ exist yet; expect non-trivial degradation (likely 3–8pt on hard reasoning, more on long-context), though the model "fits and runs end-to-end with coherent output." Treat the table above as an **upper bound** — real-world quality on this rig will be meaningfully below the published Flash numbers. The 4-bit MLX build is the recommended quality target if you can fit it, but the user has flagged it as not-loadable on 128 GB.

Sources:
- [DeepSeek-V4-Flash model card (official benchmarks)](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash)
- [mlx-community DeepSeek-V4-Flash-2bit-DQ](https://huggingface.co/mlx-community/DeepSeek-V4-Flash-2bit-DQ)
- [antirez DeepSeek V4 Flash llama.cpp port (hybrid quant notes)](https://github.com/antirez/llama.cpp-deepseek-v4-flash)
- [DGX Spark thread on antirez's MLX hybrid quant recipe](https://forums.developer.nvidia.com/t/deepseekv4-flash-hybrid-quant-1x-dgx-spark-antirezs-optimized-128-gb-mlx-recipe-ported-to-vllm-for-gb10/369584)
- Frontier sources as above.

---

## 8. `deepseek-v4-flash` — MLX 4-bit (won't load on this rig)

Skipped per the user's note. If it did fit, the 4-bit MLX build would track the official Flash numbers (table in section 7) within ~1–2pt — DeepSeek V4 Flash is QAT-trained at FP4 for experts so 4-bit MLX is the lowest "lossless-ish" target.

---

# Summary: where each local model lands vs frontier

| Local model (on-disk quant) | One-line verdict |
|---|---|
| qwen3-coder-next 80B-A3B (MLX 6-bit) | **Sonnet-4.5-class coding** at 3B active — ~6–10pt behind Opus 4.5 / Sonnet 4.6 / GPT-5 on SWE-bench Verified, 20–30pt behind GPT-5.5 on Terminal-Bench; pound-for-active-parameter the best agentic coder you can run locally. |
| qwen3.6-27b (MLX 6-bit) | **Best all-rounder on disk.** Within 1–3pt of Opus 4.5 on GPQA, within ~4pt on SWE-bench Verified, beats Sonnet 4.6 on GPQA and AIME. Loses to Gemini 3 Pro on MMLU/GPQA by 4–6pt. |
| qwen3.6-35b-a3b (MLX 6-bit) | **Almost a tie with the 27B dense** on most evals but lighter to run. ~7pt behind frontier on SWE-bench Verified, ~5pt behind on GPQA. Watch the MoE-MLX tool-call regression. |
| gemma-4-26b-a4b (MLX 4-bit) | **Knowledge generalist mid-tier.** ~7pt below Opus 4.5 on MMLU-Pro, ~5pt below on GPQA, and uniquely strong on long-context vision. The MLX 4-bit penalty here is the largest of any quant on disk — switch to GGUF Q4_K_M if quality matters. |
| nemotron-3-nano-omni (GGUF Q4_K_M) | **Multimodal specialist, not a general reasoner.** Below frontier on every text benchmark (MMLU-Pro 78, GPQA 73), but state-of-the-art among small models on OCR / long-document / audio / video. AA Intelligence Index 21 vs frontier ~60+. |
| gemma-4-e4b (GGUF Q4_K_M) | **Edge-tier.** 20–30pt below frontier on every hard benchmark. Useful as a fast/cheap drafter and vision toy; not a quality reasoning option. |
| deepseek-v4-flash 2-bit-DQ (MLX) | **The only "frontier-class" model on disk, asterisked.** Base Flash matches GPT-5 / Opus 4.5 on most benchmarks (88.1 GPQA, 91.6 LiveCodeBench, 79.0 SWE-Verified), but the 2-bit-DQ quant has no published quality numbers and the model is already QAT-FP4 with little compression headroom — expect non-trivial degradation in practice. |
| deepseek-v4-flash 4-bit (skipped) | Would land within ~2pt of the Flash table above; doesn't fit on 128 GB per user note. |

## Three most important caveats

1. **MLX 4-bit for Gemma 4 is the weakest quant on disk by a wide margin.** Community measurements show MLX uniform 4-bit RTN runs ~4.7× worse perplexity than llama.cpp K-quants for Gemma 4. For this specific model, GGUF Q4_K_M or an MLX-DWQ-4bit build would close most of the gap.
2. **DeepSeek V4 Flash 2-bit-DQ is the asterisk-heaviest entry in the report.** No public benchmark deltas exist; the MoE experts ship at FP4 natively so dropping experts to 2-bit is closer to "destructive recompression of an already-quantized model" than a clean post-train quant. Treat the table-7 numbers as a ceiling, not an estimate.
3. **Frontier comparison numbers come from heterogeneous sources.** Anthropic's announcement pages don't publish exact AIME / MMLU-Pro numbers — those rows use the most-cited third-party transcriptions (Vellum, Morph, llm-stats). Opus 4.6 (newer than the user's "Opus 4.5" baseline) is included where Opus 4.5 numbers weren't published. GPT-5 numbers are the original Aug 2025 release; GPT-5.5 (Apr 2026) is meaningfully better on coding (Terminal-Bench 82.7, SWE 88.7).
