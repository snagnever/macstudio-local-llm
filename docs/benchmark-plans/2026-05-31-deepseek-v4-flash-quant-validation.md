# DeepSeek-V4-Flash — validate "it's the quant": does higher precision reduce the loop?

**Date:** 2026-05-31 · **Branch:** `deepseek-v4-tool-dsml`
**Hypothesis:** the degeneration loop is caused by the **2-bit quantization of the MoE experts**
(`ffn.switch_mlp.*`). Higher-precision experts → lower loop rate. If true, "it's the quant" goes from
strong inference to direct evidence.

## Feasibility (why the obvious test is impossible, and what we do instead)

The 2-bit-DQ is a **mixed** quant: 4-bit base, **2-bit MoE experts** (the experts are ~70 GB of the
90 GB). To raise precision we'd need a higher-bit build that fits **128 GB unified memory**:

| build | size | fits 128 GB RAM? |
|---|---|---|
| `mlx-community/…-2bit-DQ` (have it) | 90 GB | ✅ (baseline) |
| `mlx-community/…-4bit` / `…-mxfp4` | **151 GB** | ❌ exceeds RAM |
| 3-bit **MLX** (would have to build) | ~113 GB | can't build: converting from bf16 (~320 GB) needs >128 GB RAM |
| GGUF `Q3_K_M` | 135 GB | ❌ exceeds RAM |
| GGUF `Q2_K` | 107 GB | fits, but ~same precision (no gain) |
| **GGUF `IQ3_XXS`** (ssweens) | **111.8 GB** | ✅ **~3-bit, fits with ~16 GB headroom — the test** |

→ The only feasible higher-precision DeepSeek-V4-Flash on this rig is **`IQ3_XXS` GGUF** (~3-bit,
importance-matrix), run via **llama.cpp / LM Studio**. 3 shards, already located:
`ssweens/DeepSeek-V4-Flash-GGUF-YMMV` → `…-IQ3_XXS-0000{1,2,3}-of-00003.gguf`.

**Confounds (stated honestly):** different runtime (llama.cpp vs mlx_lm) and quant scheme (IQ3 imatrix
vs MLX affine). So this is "**same model, higher precision**," not a bit-only delta. We bound the
runtime confound with the free Qwen control below, and note llama.cpp **honors per-request seeds**
correctly (unlike the mlx_lm bug we patched), so the rate measurement is valid.

## Experiment

**Primary — IQ3_XXS (~3-bit) vs 2-bit-DQ, same harness:** ⛔ **NOT PURSUED (cancelled 2026-05-31).**
The 111.8 GB download was stopped at 17 GB and deleted; we accept the local-model control below as the
answer rather than spend hours + ~112 GB to run a heavier model whose comparison is confounded anyway
(different runtime + quant scheme). Steps retained for the record only:
1. Download the 3 IQ3_XXS shards (111.8 GB) → `~/.lmstudio/models/ssweens/…`.
2. Load via LM Studio / `lms`, serve OpenAI API (small ctx ~4096; weights ~112 GB leave little
   headroom).
3. Run the **degeneration rate harness** (`degeneration_sweep.py`) — 8 seeds — on `exec_pt` (short
   trigger), `qa_fact` (control), `story_en` + `list_en` (long-form). Judge long-form coherence with
   the same Qwen judge.
4. Compare loop/collapse rates to the 2-bit-DQ numbers already on record
   (exec_pt ~50%, long-form ~94–100%).

**Free control (run now, during the download) — does a high-precision model loop at all on these
prompts?** Run the same harness on **Qwen3.6-35B-A3B 6-bit and 8-bit** (MLX, both local), thinking off,
8 seeds, on `exec_pt` + `story_en`. Expectation: ~0% loop → high precision ⇒ no degeneration in our own
pipeline, isolating the effect to low-bit weights (not the harness/prompts/runtime).

## Results — free control (done 2026-05-31)

High-precision models on the **same prompts + harness + (patched) runtime** as DeepSeek-2bit, thinking
off, 8 seeds:

| model | exec_pt | qa_fact | story_en |
|---|---|---|---|
| Qwen3.6-35B-A3B **6-bit** | **0/8** | 0/8 | **0/8** (coherent, clean stop ~1.1K tok) |
| Qwen3.6-35B-A3B **8-bit** | **0/8** | 0/8 | **0/8** |
| *DeepSeek-V4-Flash 2-bit (for reference)* | *~50%* | *0%* | *~94–100% collapse* |

**48/48 clean.** High-precision models do **not** loop on the trigger that breaks DeepSeek-2bit ~50% of
the time, and they write coherent, cleanly-terminating long-form where DeepSeek-2bit collapses
~94–100%. This rules out the harness, prompts, and runtime as the cause and localizes the degeneration
to the **low-bit weights** — consistent with "it's the quant." (The direct same-model IQ3_XXS test is
the clincher; download in progress.)

## Conclusion (final — direct test cancelled)

We did **not** run the higher-precision DeepSeek-V4-Flash, because (a) every build that would isolate
precision is infeasible on 128 GB (4-bit MLX = 151 GB > RAM; can't build a 3-bit MLX without loading
~320 GB bf16; the only fitting ~3-bit is a GGUF on a different runtime + quant scheme), and (b) the
heavier GGUF test was cancelled to avoid a multi-hour, ~112 GB download for a confounded comparison.

**Epistemic status: "it's the quant" is strongly supported, but the direct same-model precision bump
remains unproven on this rig.** The evidence we *do* have:
- **Local high-precision control:** Qwen3.6-35B-A3B at 6-bit and 8-bit loop **0/48** on the exact
  prompts/harness/runtime where DeepSeek-2bit fails (~50% short, ~94–100% long-form). → not the
  harness, prompts, or runtime.
- **Structure:** the 2-bit-DQ is 4-bit everywhere except the MoE experts, which are 2-bit (~70 GB of
  90 GB) — the lowest-precision, highest-mass part, the natural suspect.
- **Rate study + literature:** the loop is stochastic and only worsens under XTC; low-bit quant damage
  is the documented cause of this failure mode.

What would close it (not feasible here): a higher-precision DeepSeek-V4-Flash that fits 128 GB — i.e.,
a future ~3-bit MLX conversion, or running the IQ3_XXS GGUF on a machine with more memory headroom.

## Predictions → interpretation

| result | meaning |
|---|---|
| IQ3_XXS loops **much less** than 2-bit-DQ (and Qwen high-bit ~0%) | **confirms "it's the quant"** — precision is the lever |
| IQ3_XXS loops **about the same** as 2-bit-DQ | the loop is **not** purely 2-bit-expert precision (architecture / this checkpoint / something else) — important negative result |
| IQ3_XXS partially better | partial — quantify the precision→stability curve |

## Cost / risk

- Download: 111.8 GB (1.1 TB free disk; bandwidth = hours). Resumable.
- Memory: ~112 GB weights on 128 GB → tight; small context only; stop all other models first.
- Reversible: pure addition; delete the GGUF dir to undo.
