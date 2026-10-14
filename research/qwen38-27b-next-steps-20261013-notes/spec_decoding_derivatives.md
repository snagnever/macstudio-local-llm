# Qwen3.8-27B (dense) on Apple Silicon: speculative decoding and derivatives (state as of 2026-10-13)

Scope: the dense `Qwen/Qwen3.8-27B` only. Sources were Hugging Face model cards and API (`/api/models`, read 2026-10-13), GitHub release notes (`gh api`), r/oMLX through the Reddit MCP, and web search. No weights were downloaded and nothing was measured on the rig in this pass. Unless a line cites a campaign in this repo, every number is **author-reported**. Items dated before 2026-08-01 are marked *(prior state)*. All Qwen3.8 artifacts date from 2026-08-05 or later, so very few are.

Local baseline for comparison: repo campaign `bench/engine-updates-2026-10/results/27b-summary.md` (2026-10-08). It ran on an M4 Max 128 GB with the mlx-community 8-bit target, `temperature=1.0, top_p=0.95, top_k=20`, reasoning xhigh and a 4096-token cap. Decode results:
- mlx-dspark 0.20.3 + DFlash2: 43.5 tok/s at 32K, 32.4 tok/s at 128K.
- oMLX 0.7.0 oQ8e-mtp (native MTP): 42.2 / 28.2 tok/s.
- MTPLX 2.12.2: 41.4 / 25.2 tok/s.
- mlx-serve 26.10.1 + DFlash2: 37.0 / 15.5 tok/s, with DFlash2 per-draft acceptance of about 47–49%.

The Etapa F follow-up made mlx-dspark with `--prefix-cache-rungs 1024` the leader on `T_turno`: 16.7 s at 32K and 25.7 s at 128K.

---

## 1. Speculative-decoding methods for Qwen3.8-27B on Apple Silicon: runtimes, acceptance, measured gain

### Takeaway
Four routes run on Metal today:
- **Native MTP head**, in MTPLX, oMLX Lightning MTP, mlx-serve, llama.cpp `draft-mtp` and mlx-vlm.
- **DFlash 2** (incoai/z-lab), in mlx-dspark, oMLX, mlx-serve, Splash and llama.cpp `draft-dflash`.
- **DSpark**: RadixArk v1/v2 and Red Hat's head, in mlx-dspark `--mode dspark`.
- **Prompt lookup / n-gram**: mlx-serve PLD and MTP-lookup.

On datacenter GPUs, DFlash 2 has the highest acceptance length (about 4.1–5.5 against about 3.7–5.0 for MTP at 7 drafts). On Macs the realized gain is about 1.8–2.7× at short context and roughly 1.8× at 32K with the newest kernels. No EAGLE-3, HASS or small same-family drafter runs on Metal for this model. All methods verify every drafted token against the target and claim lossless output.

### Cited Findings

**Native MTP head**
- The base model card lists "MTP (Multi-Token Prediction): trained with multiple steps", under Apache-2.0. — [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)
- On H200 with SGLang, at 7 draft tokens, xhigh, T=1.0 and top-p 0.95, the MTP acceptance length was:
  - GSM8K 5.02, MATH-500 4.72, HumanEval 3.91, MBPP 3.99, MT-Bench 3.74.
  - Concurrency-1 throughput was 2.59× on GSM8K and 1.96× on MT-Bench over autoregressive decoding (68.9 tok/s).
  - Source: the DFlash2 authors (incoai), so a competitor of MTP. — [incoai/Qwen3.8-27B-DFlash2](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2)
- **MTPLX** (Youssofal), pack `Qwen3.8-27B-MTPLX-Optimized-Speed`:
  - 4-bit dynamic, with the MTP head kept at 16-bit.
  - Depth 3. Per-depth draft acceptance on a coding task was 0.95 / 0.88 / 0.80, with a verify cost of 50–53 ms per round.
  - Measured on an M5 Max: 58.7 tok/s on a coding task at medium reasoning, and 35.1 / 37.3 tok/s on long xhigh answers of 28K / 20K tokens.
  - The card claims exactness: 1,000 four-token draws from the fast path match the plain path within noise at T=1.
  - The repo pinned revision `1d5087d` (last modified 2026-09-24).
  - Source: [Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed)
- **MTPLX 2.11.1 long-context changes**: 27B decode went from 38.6 to 41.4 tok/s at 16K (+7%) and from 20.5 to 30.9 tok/s at 88K (+51%). In 2.11.2, a flash-decoding verify route that needs M5 tensor units had shipped without a hardware gate. On M1–M4, including the M4 Max, it produced wrong attention past 8,192 KV tokens; 2.11.2 fixed that. The latest release is 2.12.2 (2026-10-03), a memory-guard fix. — [MTPLX releases](https://github.com/youssofal/MTPLX/releases)
- **mlx-serve with native MTP** on Qwen3.8-27B 4-bit, M4 Max:
  - 26.9.5: four MTP streams share one verify, 72 → 119 tok/s aggregate. With a DFlash drafter loaded, concurrent requests switch to the MTP head so they batch (64 → 122 tok/s).
  - 26.9.5: the MTP auto-depth planner gave code +2%, prose +2%, short echo +3%.
  - 26.10.1 (2026-10-01): "Qwen3.8 27B 4-bit + drafter" decode +28% on the M4 Max, +66% on the M5 Ultra. DFlash on dense Qwen3.5/3.8 now matches normal decoding exactly, sampled requests included. Qwen3.8-27B + DFlash2 now "tries a tree of drafts each round".
  - Source: [mlx-serve releases](https://github.com/ddalcu/mlx-serve/releases)
- **mlx-serve 26.10.2** (2026-10-12) adds "MTP depth bounds and greedy tail" and "DSpark that honors every opt-out". It names no 27B-specific speedup. — [mlx-serve releases](https://github.com/ddalcu/mlx-serve/releases)
- **ddalcu MLX-Serve packs**, decode with MTP on, on an M4 Max (llmprobe `--bench-only --quick`; differences under 5% are noise):
  - 8-bit: 46.4 tok/s
  - 6-bit: 57.0 tok/s
  - 4-bit: 69.6 tok/s
  - iQ-MLX-3.8bpw: 59.0 tok/s
  - In the iQ 3.8 bpw pack the MTP head is 4-bit/gs-64, ×7 depth.
  - Source: [ddalcu/Qwen3.8-27B-MLX-Serve-iQ-MLX-3.8bpw](https://huggingface.co/ddalcu/Qwen3.8-27B-MLX-Serve-iQ-MLX-3.8bpw)
- **oMLX Lightning MTP**:
  - 0.7.0rc1: 4-request batch decode on Qwen3.8-27B oQ4e went 88.9 → 136.9 tok/s (+54%); DFlash2 went 56.9 → 131.5 tok/s (+131%).
  - 0.7.0: less work per verify cycle for DFlash2 and Lightning MTP on Qwen3.8-27B, largest at long context.
  - 0.7.0.dev4: Qwen3.8-27B-oQ4e-mtp at 2 requests went 53.86 → 84.08 tok/s (+56%).
  - Source: [oMLX releases](https://github.com/jundot/omlx/releases)
- **llama.cpp `--spec-type draft-mtp`** reads the MTP head bundled in GGUFs, for example byteshape, ISTA GSQ-RCO `-mtp` builds, ThinkingCap and Unsloth.
  - byteshape advises `--spec-draft-n-max 3`, because "The head predicts one token ahead, so pushing … past 3 mostly adds rejected drafts".
  - ThinkingCap measured on H200 llama.cpp, 4 slots, MMLU-Pro, 24 questions: MTP speedup 1.07× (Q8_0), 1.30× (Q4_K_M), 1.34× (Q6_K), 1.76× (f16), with acceptance length 2.33–2.52 out of a maximum of 4.
  - Sources: [byteshape/Qwen3.8-27B-GGUF](https://huggingface.co/byteshape/Qwen3.8-27B-GGUF); [bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF](https://huggingface.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF)
- **llama.cpp MTP on Mac**: on a base M4 24 GB, a community nine-run median went from 5.3 tok/s baseline to 10.8 tok/s with `draft-mtp`. On NVIDIA the same repo reports +33–39% (title) and up to about +125% on code. I saw only the search summary, not the repo. — [sudoingX/qwen38-mtp](https://github.com/sudoingX/qwen38-mtp)
- **mlx-vlm MTP**: ThinkingCap's MLX DWQ pack runs MTP through `mlx_vlm generate --draft-kind mtp --draft-block-size 3`. Acceptance is 2.41 tokens per round for the 4-bit DWQ against 2.43 for bf16. The card notes "mlx-lm drops the MTP head and the vision tower". — [bottlecapai/ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ](https://huggingface.co/bottlecapai/ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ)

**DFlash 2 (block-diffusion drafter)**
- **Checkpoint**: [incoai/Qwen3.8-27B-DFlash2](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2), mirrored at [z-lab/Qwen3.8-27B-DFlash2](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2). Created 2026-08-18; last modified 2026-09-17; Apache-2.0. The Splash package pins draft revision `dedf8df6`.
  - Design: five layers reading target hidden states at five layers, proposing 7 tokens per step, about 1.2 GiB.
  - The card states: "greedy output matches the target model exactly, and sampling preserves its distribution."
  - Acceptance length on H200 SGLang: GSM8K 5.46, MATH-500 5.28, HumanEval 4.39, MBPP 4.79, MT-Bench 4.10.
  - Concurrency-1 speedup: 3.43× (GSM8K), 3.11× (HumanEval), 2.67× (MT-Bench).
  - Sources: [incoai/Qwen3.8-27B-DFlash2](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2); [incoai/Qwen3.8-27B-Splash](https://huggingface.co/incoai/Qwen3.8-27B-Splash)
- **GGUF drafter**: [z-lab/Qwen3.8-27B-DFlash2-GGUF](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2-GGUF) and [incoai/Qwen3.8-27B-DFlash2-GGUF](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2-GGUF). llama.cpp `--spec-type draft-dflash` requires build b10658 (2026-08-27) or newer.
  - DFlash 2 is text-only in llama.cpp: image requests fail with HTTP 500 while it is active.
  - Draft quantization "barely affects acceptance (Q4_K_M is on par with Q8_0 and BF16)".
  - Source: [byteshape/Qwen3.8-27B-GGUF](https://huggingface.co/byteshape/Qwen3.8-27B-GGUF)
- **mlx-dspark** (ARahim3):
  - 0.20.0 (2026-09-27): a new small-M verify kernel took Qwen3.8-27B-4bit + DFlash 2 from 2.30× to **2.71× (39.9 tok/s) on short prompts**. A new multi-token verify attention kernel took 32K from 1.23× (0.19.0) to **1.85×**.
  - The release's table lists 4-bit + DFlash 2 at 1.79× / 1.85× and 4-bit + Red Hat DSpark at 1.89× / 1.83×. The second column is 32K; the first column's label was not captured in my extract.
  - Latest release: 0.20.3 (2026-10-05).
  - Source: [mlx-dspark releases](https://github.com/ARahim3/mlx-dspark/releases)
- **mlx-dspark project log** (dated 2026-08-19, *prior to the v0.20 kernels*): 8-bit target with DFlash 2 reached 3.74× mean speedup with acceptance 5.42. — [mlx-dspark README (fork mirror)](https://github.com/sunkai174634/mlx-dspark)
- **24 GB Mac mini**: about 1.8× measured; an 8-bit draft was 3% slower than 4-bit. — [cooconsbit](https://tools.cooconsbit.com/en/articles/qwen38-dflash2-mac-mini-24gb-en)
- **48–64 GB Mac agent lane**: 15–19 tok/s end-to-end at 24–27K context with mlx-dspark + DFlash 2. — [felix-ab/qwen38-27b-mlx-agent-lane](https://github.com/felix-ab/qwen38-27b-mlx-agent-lane)
- **Splash (Inco AI)** is a new Apple-silicon engine built around DFlash 2.
  - Release history: 1.0 on 2026-09-18; 1.3.1 on 2026-10-09.
  - Author-measured on an M5 Pro 48 GB (SPEED-Bench coding prompts, 1,024-token outputs, medium reasoning):
    - Decode 74 tok/s (2.0× the next-fastest engine).
    - Prefill at 32K: 363 tok/s.
    - Cached TTFT on a 32K replay: 282 ms.
    - 4-request aggregate decode: 170 tok/s.
  - The card says the target verifies every draft, so "speculation changes speed and not the output distribution."
  - Source: [incoai/Qwen3.8-27B-Splash](https://huggingface.co/incoai/Qwen3.8-27B-Splash)
- **Splash release notes**:
  - 1.1.0: measured "4.5–5.3× llama.cpp's decode throughput on 27B" and 2.7–4.6× against llama.cpp with MTP (M5 Pro, M3 Max, Unsloth UD-Q4_K_M), with 99.30–99.45% top-1 agreement with llama.cpp.
  - 1.3.0: GPU + Neural Engine FFN split for 27B prefill. In a 19K shared-prefix case, TTFT fell from 39.6 s to 6.3 s.
  - 1.3.1: loads MLX affine 2–8-bit checkpoints at group sizes 32/64/128, including mlx-community 8-bit and "compatible fine-tunes". The pre-packed `*-Splash` packages no longer load.
  - Requirements: M3 or newer, macOS 26.4+.
  - Source: [incoai/splash releases](https://github.com/incoai/splash/releases)
- **Splash in other runtimes**: LM Studio exposes a Splash runtime (Bionic 1.1.5+). [SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash](https://huggingface.co/SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash). An oMLX PR wraps the installed Splash engine ([jundot/omlx#4447](https://github.com/jundot/omlx/pull/4447)). A post benchmarks that PR on an **M4 Max 128 Studio** and an M3 Ultra 512, but its gallery images were not readable through the MCP. — [r/oMLX 1x3l2wx](https://www.reddit.com/r/oMLX/comments/1x3l2wx/omlx_v07_splash_pr_benchmark_on_m3u_512_studio/)
- **Community vs vendor numbers**: a community post claims Splash is "significantly faster on decoding" than LM Studio's default on the 27B, "with no quality degradation" (anecdote). Separately, MrGermanIOTA measured Splash at about 2× oMLX 0.7.0 on JSON extraction, but with Qwen3.6, not 3.8. — [r/oMLX 1x3l2wx comments](https://www.reddit.com/r/oMLX/comments/1x3l2wx/omlx_v07_splash_pr_benchmark_on_m3u_512_studio/); [r/oMLX 1wusa85](https://www.reddit.com/r/oMLX/comments/1wusa85/omlx_070_vs_070rc1_benchmark_what_changed_7/)

**DSpark**
- **RadixArk/Qwen3.8-27B-DSpark** (created 2026-08-14, modified 2026-08-29; license "other"):
  - 1.86B parameters, 5 layers, aux layers 5/19/33/47/61, Markov head rank 256, serving gamma 7.
  - Trained against the NVFP4/FP8 targets with SpecForge.
  - DSpark v2 acceptance on GB300 SGLang over 17 workloads: macro 3.92 (v1 3.10). Examples: HumanEval 3.85, GSM8K 4.52, LongBench-v2 3.93, RULER-8K 6.30.
  - Concurrency-1 speedups were 2.25–3.16×, against EAGLE at 1.64–1.91×. The card does not identify which EAGLE checkpoint.
  - Source: [RadixArk/Qwen3.8-27B-DSpark](https://huggingface.co/RadixArk/Qwen3.8-27B-DSpark)
- **RedHatAI/Qwen3.8-27B-speculator.dspark** (release date 2026-09-21; Apache-2.0):
  - 5 layers, aux layers 4/12/20/28/36/44/52/60, up to 8 draft tokens, with a confidence head.
  - Trained on a Qwen3.8-27B-regenerated Open PerfectBlend (1.74M × 8,192-token examples), with Speculators 0.8.0.dev.
  - The checkpoint is at step 107,520, about 75% of one epoch.
  - In mlx-dspark 0.20.0 it replaced the earlier DSpark heads: **8-bit target 3.79×** (ties DFlash 2's 3.74×) and 4-bit target 2.63×. `--mode auto` still picks DFlash 2.
  - Sources: [RedHatAI/Qwen3.8-27B-speculator.dspark](https://huggingface.co/RedHatAI/Qwen3.8-27B-speculator.dspark); [mlx-dspark v0.20.0](https://github.com/ARahim3/mlx-dspark/releases/tag/v0.20.0)
- **Other DSpark checkpoints** exist on HF but have no Metal evidence: GGUF ports (Anbeeld, magnitudedev, erlidev), `tiyuvta/Qwen3.8-27B-DSpark-Agentic`, `DimInfer/Qwen3.8-27B-Dspark-v1`, and `LithosAI/…-DSpark-NVFP4` (2026-10-04). — [HF search "Qwen3.8-27B-DSpark"](https://huggingface.co/models?search=Qwen3.8-27B-DSpark)

**Prompt lookup / n-gram (PLD)**
- mlx-serve has PLD/lookup drafting (`--no-pld` flag). 26.9.6 added MTP drafting "from the conversation itself when the reply copies it", which makes file rewrites and edits decode 1.3–1.5× faster; it is on by default and `MLX_SERVE_MTP_LOOKUP=0` disables it. 26.10.1 fixed "lookup drafting could get stuck repeating itself" (#614), described as a cause of agent loops. — [mlx-serve releases](https://github.com/ddalcu/mlx-serve/releases); [ddalcu iQ-MLX-3.8bpw card](https://huggingface.co/ddalcu/Qwen3.8-27B-MLX-Serve-iQ-MLX-3.8bpw)

**EAGLE-3 / HASS / small-model drafts**
- No EAGLE-3 or HASS checkpoint for Qwen3.8-27B was found on HF (search "Qwen3.8-27B-EAGLE" returned nothing), and no Metal runtime is documented for one. RadixArk's table has an unnamed "EAGLE" column on GB300 only. — [HF search](https://huggingface.co/models?search=Qwen3.8-27B-EAGLE); [RadixArk card](https://huggingface.co/RadixArk/Qwen3.8-27B-DSpark)
- The Qwen org publishes only Qwen3.8-27B, Qwen3.8-Flash-Next and Qwen3.8-2.4T-A95B, plus FP8 versions. There is no small Qwen3.8 (0.x/1.x B) model to use as a same-family draft. — [HF API author=Qwen](https://huggingface.co/Qwen)
- A dataset `DaoCloud/Qwen3.8-27B-Drafter-SFT` (2026-08-27) exists. I did not read it. — [HF datasets search](https://huggingface.co/datasets?search=Qwen3.8-27B)

**Mac numbers I could not verify**
- A runbook reports about 53 tok/s on prose and 72 on code with oMLX MTP on an M4 Max, against about 25 tok/s raw. I saw only the search summary; it is a vendor blog. — [orcarouter blog](https://www.orcarouter.ai/blog/qwen-3-8-27b-uncensored-mlx)
- An aggregator claims 146–154 tok/s on an M4 Max for three engines sharing DFlash 2. That conflicts with this repo's measured 43.5 tok/s at 32K, so treat it as unreliable. — [vramcalculator](https://vramcalculator.com/qwen3-8-27b-speed/)

### Inferences
- **Context length matters more than method on the M4 Max.** The repo's 128K numbers range from 15.5 tok/s (mlx-serve DFlash2) to 32.4 tok/s (mlx-dspark DFlash2). The verify-attention kernel (mlx-dspark 0.20, oMLX 0.7.0, MTPLX 2.11) explains more of the spread than the choice of drafter does.
- **A rig re-measurement is due.** mlx-serve 26.10.2 (MTP depth bounds and greedy tail), Splash 1.3.1 and the oMLX Splash PR (#4447) all postdate the repo's 2026-10-08 27B ranking, and none of them is measured on the rig. Splash is the new candidate with the largest claimed gain: 2× decode against the next engine on an M5 Pro, plus ANE-assisted prefill.
- **Acceptance lengths are not comparable across sources.** Datacenter numbers (H200/GB300, FP8/NVFP4 targets, block of 7–8) overstate Mac gains. On Macs, verify cost per round at 27B dense (about 50 ms on an M5 Max) caps realized speedup near 2–2.7× short and about 1.8× at 32K.
- **Losslessness.** All runtimes claim it (target verification). mlx-serve 26.10.1 explicitly fixed a case where DFlash on dense Qwen was not exact. Seeded outputs therefore differ from pre-26.10.1 versions.

### Gaps
- I found no published Mac acceptance-rate breakdown for DSpark v2 (RadixArk) on MLX. mlx-dspark replaced it with the Red Hat head.
- I found no measurements of llama.cpp `draft-mtp` or `draft-dflash` on an M4 Max for the 27B.
- I found no EAGLE-3 or HASS drafter for Qwen3.8-27B and no Metal support.
- I could not read the M4 Max numbers in the oMLX Splash-PR Reddit gallery (images only).
- LM Studio's native (non-Splash) MTP support for the 27B is unknown.

---

## 2. New drafters, MTP retrains and runtime speculative features in Sep–Oct 2026

### Takeaway
September brought the Red Hat DSpark head, the Splash engine with DFlash 2 and the mlx-dspark long-context verify kernel. October brought mlx-serve 26.10.1 (tree drafts, +28% on the M4 Max) and 26.10.2 (MTP depth bounds), Splash 1.2–1.3.1, oMLX 0.7.1.dev1 (27B oQ4e TTFT −11–17%) and Jundot's oQ re-uploads with the refit quantizer. No one published a retrained MTP head or a new DFlash checkpoint for the base 27B after 2026-09-17.

### Cited Findings
- **RedHatAI DSpark speculator**: released 2026-09-21, adopted by mlx-dspark 0.20.0 on 2026-09-27. — [RedHatAI card](https://huggingface.co/RedHatAI/Qwen3.8-27B-speculator.dspark); [mlx-dspark v0.20.0](https://github.com/ARahim3/mlx-dspark/releases/tag/v0.20.0)
- **incoai DFlash2**: last modified 2026-09-17. No newer DFlash 2/3 checkpoint for the 27B was found. — [incoai/Qwen3.8-27B-DFlash2](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2)
- **Splash releases**: 1.0 (09-18), 1.1.0 (09-26, upstream GGUF/MLX loading), 1.2.0 (10-04, persistent conversation cache, exact top-k/top-p under DFlash), 1.3.0 (10-06, GPU+ANE prefill), 1.3.1 (10-09, all MLX affine bit-widths). — [incoai/splash releases](https://github.com/incoai/splash/releases)
- **mlx-serve**:
  - 26.10.1 (10-01): 27B 4-bit + drafter on an M4 Max +28% decode; DFlash2 tree drafts; drafters for 27B 6-bit and 8-bit; GGUF on the MLX engine (`--mlx-gguf`).
  - 26.10.2 (10-12): MTP depth bounds and greedy tail; llama.cpp v0.6.0.
  - Source: [mlx-serve releases](https://github.com/ddalcu/mlx-serve/releases)
- **oMLX**:
  - 0.7.0 (09-30): faster DFlash2 and Lightning MTP verify for Qwen3.8-27B.
  - 0.7.1.dev1 (10-09), Qwen3.8-27B oQ4e on an M3 Ultra: three timing columns improved 8.77 → 7.80 s, 36.66 → 32.52 s and 6.11 → 5.10 s (−11 to −17%). The columns are TTFT-type measurements; their exact labels were not captured. oQ8e with INT8-activation prefill gains +25% at 4K and +38% at 16K on an M5 Max.
  - Source: [oMLX releases](https://github.com/jundot/omlx/releases)
- **Jundot re-uploads**: `Jundot/Qwen3.8-27B-oQ8e-mtp` got a new commit `6c76ddfb` on 2026-10-11. The repo's pinned revision is `c99e5aad` (2026-08-18). `Jundot/Qwen3.8-27B-oQ4e-mtp` is now at `49c1d603` (modified 2026-10-12). A Reddit post says Jundot is re-uploading quants with the improved oQe method from 0.7.1.dev1 (PR #4385). — [HF API commits](https://huggingface.co/Jundot/Qwen3.8-27B-oQ8e-mtp/commits/main); [r/oMLX 1x3d7f8](https://www.reddit.com/r/oMLX/comments/1x3d7f8/jundot_has_been_reuploading_quants_using_improved/)
- **scottlowry oQ packs**: a full oQ4e–oQ8e set (bf16 and fp16 variants) of base Qwen3.8-27B was re-pushed on 2026-10-12, and the author said they would redo all uploads with the refit method. — [HF search](https://huggingface.co/models?search=scottlowry%2FQwen3.8-27B); [r/oMLX 1x3d7f8](https://www.reddit.com/r/oMLX/comments/1x3d7f8/jundot_has_been_reuploading_quants_using_improved/)
- **MTPLX**: no release after 2.12.2 (10-03). The 27B pack HEAD is `1d5087d` (09-24). — [MTPLX releases](https://github.com/youssofal/MTPLX/releases); [HF API](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed)
- **nerkyor DFlash2 draft re-encode**: nerkyor re-encoded its companion DFlash2 draft (FP8 block scales) on 2026-10-08. The earlier per-tensor-scale draft "accepted almost no draft tokens" in some engines. This is CUDA/NInfer-oriented. — [nerkyor Coder390 card](https://huggingface.co/nerkyor/Qwen3.8-27B-Coder390-EfficientThink-Opus5.5-GPT6Astra-Grok4.7-DSV4Pro-K3-SFT-RLOO-MTP-DFlash2)

### Inferences
- The repo's 27B arms predate Splash 1.3.x, mlx-serve 26.10.2 and the refit oQ packs. The oMLX arm (o27) used `c99e5aad`, which has now been superseded by `6c76ddfb`.
- Repeating the Flash-Next lesson ("re-check pinned revisions"), any new 27B campaign should pin the new revisions.

### Gaps
- I found no new MTP-head retrain for the base 27B. Whether the Jundot refit re-quantized the MTP head differently is undocumented.
- The oMLX Splash PR (#4447) is not merged as of the data I saw.

---

## 3. Derivatives of Qwen3.8-27B: reasoning-efficiency, agent/coder SFTs, distills, abliterated, merges

### Takeaway
Two reasoning-efficiency fine-tunes matter for an agent:
- **Swift 1.5 (ukisai)**: −41.9% mean / −58.5% median thinking tokens on GPQA-D at equal accuracy, LiveCodeBench +5, Terminal-Bench 2.1 +2.9. Swift Open License, with a US$1M revenue cap.
- **ThinkingCap (BottleCap AI)**: −37% reasoning tokens, 85.8% vs 86.6% average accuracy. PolyForm Small Business license, with an MLX 4-bit DWQ port that keeps MTP.

Both ship the base model's MTP head unchanged; neither retrains it. No public acceptance-rate data exists for a stale MTP head or stock DFlash2 on these derivatives. Agent SFTs (nerkyor Coder390), abliterated builds (OBLITERATUS, Heretic, huihui) and DavidAU merges exist, but none has independent agentic evidence or a well-validated MLX port.

### Cited Findings

**Swift 1.0 → 1.5 (ukisai)**
- **Swift 1.0** ([ukisai/Swift-Qwen3.8-27b](https://huggingface.co/ukisai/Swift-Qwen3.8-27b)): created 2026-09-08; tagged `lora`, delivered as adapter merged on the base.
  - Method: penalizes "reasoning-marker tokens" linked to overthinking.
  - BF16 vLLM, 5 seeds, xhigh, base → Swift: GPQA-D 88.38 → 88.28 (median tokens −58.3%); IFBench 73.53 → 71.80; AIME 2026 98.67 → 94.00; LiveCodeBench v6 76.76 → 81.55; Terminal-Bench 2.1 66.74 → 65.84 (tokens −26.5% mean).
  - Source: [Swift 1.0 card](https://huggingface.co/ukisai/Swift-Qwen3.8-27b)
- **Swift 1.5** ([ukisai/Swift-1.5-Qwen3.8-27b](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b)): created 2026-09-16, HEAD `b4c84d42` (modified 2026-10-03), gated.
  - Built from Swift 1.0 with scaled RL + OPD focused on long-horizon, agentic and coding tasks. Training data derives from [ukisai/Qwen3.8-27B-multi-turn-agent-sft](https://huggingface.co/datasets/ukisai/Qwen3.8-27B-multi-turn-agent-sft), "re-sampled, turned into proper RL environments".
  - BF16, 5 seeds, xhigh, base → Swift 1.5:

    | Benchmark | Base | Swift 1.5 | Token reduction |
    |---|---:|---:|---|
    | GPQA-D | 88.28 | 88.59 | mean −41.9%, median −58.5% |
    | C-Eval | 90.00 | 90.92 | |
    | IFBench | 73.53 | 72.07 | |
    | ERQA | 67.45 | 65.40 | |
    | AIME 2026 | 98.67 | 96.00 | |
    | HMMT Nov 2025 | 99.33 | 97.33 | |
    | LiveCodeBench v6 | 76.76 | 81.71 | −24.5% mean |
    | Terminal-Bench 2.1 | 69.21 | 72.13 | mean −16.3%, median −0.1% |

  - The authors say Terminal-Bench savings are about −38.7% on tasks both models solve.
  - Across reasoning efforts, GPQA-D: medium 84.14 → 82.22 (−24.8% tokens); low 84.04 → 84.85 (−28.7%).
  - Demo claim: a game built in 11.39 min against 104.6 min for the base.
  - Source: [Swift 1.5 card](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b)
- **MTP on Swift**: the Swift cards state "The published weights include the base model's MTP head", meaning the MTP head was carried over, not retrained, for both 1.0 and 1.5. — [Swift 1.5 card](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b)
- **License**: Swift Open License v1.0. Free, including commercial use, up to US$1,000,000 gross annual revenue including affiliates; above that, a Swift Enterprise License is required. The base remains Apache-2.0. — [Swift 1.5 card](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b)
- **Quantized Swift 1.5**, single seed, vLLM, against saved Qwen W4A16 references:
  - GPQA-D AWQ 88.38 vs 86.36 base (tokens −51.5% mean).
  - AIME 2026 AWQ 86.67 vs 70.00.
  - Swift 1.5 BF16 single-seed: GPQA 91.41, IFBench 72.00, AIME 86.67.
  - The authors themselves say these "do not establish quality parity".
  - Source: [Swift 1.5 card](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b)
- **Swift 1.5 ports**:
  - **Official MLX** ([ukisai/Swift-1.5-4bit-MLX](https://huggingface.co/ukisai/Swift-1.5-4bit-MLX), `82276731`, 09-25; [5bit](https://huggingface.co/ukisai/Swift-1.5-5bit-MLX); a 3-bit text-only build): plain mlx-lm affine 4-bit/gs64. They need ukisai's MLX-LM patch, because stock mlx-lm 0.32.0 rejects 501 vision entries. The MTP tensors (15) are preserved, but "speculative MTP generation are **not implemented** by the patch".
  - **oQ**: scottlowry oQ4e/5e/6e/8e (bf16 and fp16), re-pushed 10-12.
  - **AutomatosX MLX**: AXQ-MXFP4/MXFP8-MTP, 10-13.
  - **Splash**: [SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash](https://huggingface.co/SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash). Repacks ukisai 4-bit MLX with a byte-identical copy of the *base* DFlash 2 drafter; the drafter is not retrained.
  - **GGUF**: ukisai GGUF and GSQ-RCO GGUF (815K downloads, 8–12 GB), bartowski.
  - **Dankpaws**: only an abliterated Swift 1.5 EXL3 4.25bpw. No Dankpaws MLX port of the 27B.
  - Sources: HF cards above; [HF API author=Dankpaws](https://huggingface.co/Dankpaws)
- **Independent testing of Swift 1.0** (MindStudio, multi-step HTML task): Swift produced about 60,572 output tokens against 11,744 for base, with more tool calls, yet finished faster overall. The article concludes the original model "remains the safer default for demanding reasoning work". I saw only the search summary. — [MindStudio](https://www.mindstudio.ai/blog/qwen3-8-27b-swift-vs-original-thinking)

**ThinkingCap (BottleCap AI)**
- Fine-tune of Qwen3.8-27B. Cards created 2026-09-23. The card claims a cut in reasoning tokens "by 37% on average while holding 85.8% average accuracy against the base model's 86.6%".
- License: PolyForm Small Business 1.0.0 plus a personal-use grant, gated; commercial use by contact.
- The GGUFs carry the MTP head (`--spec-type draft-mtp`).
- Source: [bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF](https://huggingface.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF)
- **MLX port**: [bottlecapai/ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ](https://huggingface.co/bottlecapai/ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ), 22.5 GB.
  - Layout: mixed 4/8-bit gs64 with DWQ distillation. MTP `fc`, GDN gates and norms are bf16.
  - MTP acceptance 2.41 per round against 2.43 for bf16.
  - Results against bf16 (author): GPQA-D 0.862 vs 0.880; MMLU-Pro 0.849 vs 0.841; IFBench 0.785 vs 0.797; AA-LCR 0.830 vs 0.810.
  - Serve with mlx-vlm or oMLX, not mlx-lm.
- **Other ports**: scottlowry oQ4e–oQ6e (10-12), RCO 4.2bpw GGUF, FP8, AutoRound W4A16.

**Agent / coder SFTs and distills**
- **ukisai/Qwen3.8-27B-multi-turn-agent-sft** (dataset, Apache-2.0, 08-28): about 15,200 Terminus-2 agent traces generated by Qwen3.8-27B FP16 on OpenThoughts-Agent-v1-SFT tasks (nl2bash, InferredBugs). It is a dataset, not a model. — [dataset card](https://huggingface.co/datasets/ukisai/Qwen3.8-27B-multi-turn-agent-sft)
- **nerkyor Coder390** ([nerkyor/Qwen3.8-27B-Coder390-…-SFT-RLOO-MTP-DFlash2](https://huggingface.co/nerkyor/Qwen3.8-27B-Coder390-EfficientThink-Opus5.5-GPT6Astra-Grok4.7-DSV4Pro-K3-SFT-RLOO-MTP-DFlash2)): created 2026-10-04, Apache-2.0, HEAD `bae2cbd7`.
  - Lineage: SFT + SimPO "EfficientThink" base (itself "Uncensored"), then K3 SFT, then alternating SFT/RLOO rounds using teacher trajectories from frontier models.
  - Author results (SGLang, RTX PRO 6000; GPQA 198 / MMLU 500 / LCB 100): original FP8 177 / 444 / 83 against Coder390 BF16 178 / 446 / 90, with large cuts in reasoning length and 94K truncations.
  - It bundles a BF16 MTP head and a companion DFlash2 draft. Accept length: MTP about 2.6–2.97; DFlash2 about 3.35–4.36 (NVFP4 tiers, CUDA).
  - Formats: GGUF (Q2–Q6, "LynnStyle"), NVFP4/NInfer, INT8. No MLX port.
- **Other distills/SFTs** (no cards read): Altworld/Hemmingway-1, BAAI/AREX-2, `nerkyor/…-EfficientThink-Uncensored-…-SimPO-DFlash2` (09-03), `IsValorum/Qwen3.8-27B-EfficientThink-VAL-APEX` GGUFs (10-12), `mradermacher/Qwen3.8-27b-Terse-Coder-i1-GGUF`, `JRamirez-UAB/Qwen3.8-27B-pi-*` ("Qwen pi" variant used with the Pi harness). HF lists 461 fine-tunes of the base. — [HF fine-tunes of Qwen3.8-27B](https://huggingface.co/models?other=base_model%3Afinetune%3AQwen%2FQwen3.8-27B)

**Abliterated / uncensored**
- **OBLITERATUS/Qwen3.8-27B-OBLITERATED** (08-19 → 08-24, Apache-2.0, 596K downloads): V3 MMLU 82.3% against 84.5% stock (−2.1 pp). It recommends T=0 with rep-penalty 1.15 and thinking off, and warns of loops in agent harnesses without the rep-penalty. — [OBLITERATUS card](https://huggingface.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED)
- **Others**:
  - huihui-ai Huihui-…-abliterated GGUF (2.26M downloads, updated 10-10).
  - HauhauCS Uncensored-Aggressive-MTP-GGUF (2.33M).
  - JonathanColetti Uncensored GGUF (2.44M).
  - orcarouter Uncensored (FP8 / NVFP4 / GGUF / MLX, updated 10-12).
  - 0bserverx Heretic-Abliterated (1.13M).
  - llmfan46 "Heretic-Native-MTP-Preserved".
  - sci4ai Max/Optimal-Ablit-Heretic (10-12).
  - preemware RANA-abliterated-MLX.
  - Source: [HF API sorted by downloads](https://huggingface.co/models?search=Qwen3.8-27B&sort=downloads)
- **Merges**: the DavidAU "TURBO-Fable-Cold-Fusion-735-882-Heretic-Uncensored-NEO-CODER-MAX-MTP-GGUF" line (1.94M downloads, 09-01) and "TWIN-TURBO" merges; ManniX-ITA Omnimerge-v6 (10-12); Qwen3.8 + 3.6 "blend" GGUFs. DavidAU's performance claims are unverified. — [DavidAU post](https://huggingface.co/posts/DavidAU/258606293594674); [HF API](https://huggingface.co/models?search=Qwen3.8-27B-Coder&sort=downloads)
- **Ternary Bonsai 2 27B** (Prism ML): a Hadamard-rotated 2-bit Qwen3.8-27B. It runs in mlx-serve (73.5 tok/s on an M4 Max with MTP, per 26.9.5), MTPLX 2.12 and Splash. — [mlx-serve releases](https://github.com/ddalcu/mlx-serve/releases)

### Inferences
- **Stale MTP head risk.** Swift 1.x and ThinkingCap keep the base MTP head. The SiliconSpecies Splash pack keeps the base DFlash 2 drafter. A shift in the token distribution, for example fewer "Wait/Actually" tokens, plausibly lowers draft acceptance. This is the same risk flagged in the assignment.
  - ThinkingCap's 2.41-vs-2.43 MLX acceptance compares a quant against its own bf16, not against base Qwen. It does not measure the staleness.
  - I found only one piece of contrary evidence: a snippet quoting acceptance of about 0.61 per token on Swift Splash against 0.501 for base. It was not visible in the card text I fetched, so it stays unverified.
- **Transfer from Flash-Next.** Swift 1.5 on Flash-Next (the repo's daily driver) is the same recipe and the same license. On the 27B, ukisai claims a Terminal-Bench 2.1 gain (+2.9) and equal-or-better GPQA. Wall-clock benefit for agent turns depends on token reduction (about −16% mean on Terminal-Bench), which is smaller than on single-shot reasoning (−42% mean).
- **MLX path for Swift 1.5 27B.** The official ukisai MLX build cannot do MTP speculation. Practical routes are:
  - scottlowry oQ packs in oMLX (MTP kept);
  - Splash with ukisai 4-bit MLX plus the base DFlash 2;
  - mlx-serve, if it loads the oQ or plain MLX checkpoint with the 27B drafter.
- **Abliterated builds** belong to the uncensored backlog, not to the agent driver. OBLITERATUS documents degraded sampling behavior (greedy plus rep-penalty) that conflicts with agent sampling defaults.

### Gaps
- There are no independent agentic benchmarks (Terminal-Bench, SWE-bench) for Swift 1.5 27B, ThinkingCap or Coder390. All numbers are the authors'.
- I found no MTP or DFlash2 acceptance measurement on Swift 1.5 27B against base on Mac.
- ThinkingCap's training recipe and main card were not read; only the GGUF/MLX cards were.
- I found no Dankpaws MLX port of the 27B (only EXL3) and no ddalcu MLX-Serve pack of Swift 27B.

---

## 4. Quantization quality for Qwen3.8-27B (4-bit, ~4.7–5 bpw calibrated, 6-bit, 8-bit)

### Takeaway
Plain MLX 4-bit gs64 is noticeably lossy on the 27B dense:
- ddalcu: top-1 83.6%, KL 0.32 (M4 Max pack set).
- preemware: KLD 0.047, top-1 90%.

6-bit closes most of the gap (KL 0.004–0.056, top-1 95.5–96.9%) and 8-bit is near-lossless (KL 0.0005–0.014). Calibrated mixed 4-bit layouts (MTPLX dynamic, ThinkingCap DWQ, ISTA GSQ-RCO) recover most of the 4-bit loss at 4–5 bpw. For coding and agent use on 128 GB, the evidence favors 6-bit or 8-bit, or a calibrated ≥4.5 bpw pack; the rig has the memory for it.

### Cited Findings
- **ddalcu MLX-Serve packs**, top-1 and mean KL against bf16 (32 held-out windows × 16 positions; ±2–3 pt error):

  | Pack | Size | Top-1 | Mean KL | Decode, M4 Max, MTP on |
  |---|---:|---:|---:|---:|
  | 8-bit | 30.7 GB | 95.5% | 0.014 | 46.4 tok/s |
  | 6-bit | 22.7 GB | 95.5% | 0.056 | 57.0 tok/s |
  | 4-bit | 17.7 GB | 83.6% | 0.322 | 69.6 tok/s |
  | iQ-MLX 3.8 bpw | 13.4 GB | 81.6% | 0.466 | 59.0 tok/s |

  The card's advice: "If you have the RAM, download the 6-bit." — [ddalcu/Qwen3.8-27B-MLX-Serve-iQ-MLX-3.8bpw](https://huggingface.co/ddalcu/Qwen3.8-27B-MLX-Serve-iQ-MLX-3.8bpw)
- **preemware RANA-abliterated MLX** (abliterated weights, wiki.test.raw, 100 × 512): 4-bit (4.695 bpw) KLD 0.0468 / top-1 90.0%; 6-bit (6.661 bpw) 0.0042 / 96.9%; 8-bit (8.627 bpw) 0.0013 / 98.3%. — [preemware/Qwen3.8-27B-RANA-abliterated-MLX](https://huggingface.co/preemware/Qwen3.8-27B-RANA-abliterated-MLX)
- **MTPLX packs** (teacher-forced, 2,389 positions, against bf16):
  - Optimized Speed (4-bit dynamic: gs32, 8-bit embeddings/head/GDN out-proj/last 8 MLPs, 16-bit MTP): top-1 96.0%, KL 0.012 (0.022 on the coding battery).
  - Optimized Quality (8-bit dynamic): 99.3%, KL 0.0005.
  - Source: [Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed)
- **ThinkingCap MLX 4-bit DWQ** (mixed 4/8, 22.5 GB): every benchmark within about 2 pts of bf16, with completion length unchanged. — [ThinkingCap MLX DWQ](https://huggingface.co/bottlecapai/ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ)
- **ThinkingCap GGUF against bf16** (llama.cpp vs vLLM, multi-seed, McNemar):
  - IQ4_XS and Q6_K: −2.8 pp on GPQA-D (p ≈ 0.02).
  - Q6_K: −7.0 pp on AA-LCR (p 0.065).
  - Q4_K_M and Q8_0: no detected difference, but intervals allow up to 9.5 / 7.5 pp loss on AA-LCR.
  - The authors note the estimates "are not ordered by bit width".
  - Source: [ThinkingCap GGUF](https://huggingface.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF)
- **ISTA GSQ-RCO GGUF** (non-uniform):

  | Quant | Size | Wiki PPL | AIME25 | GPQA-D | LCB v6 |
  |---|---:|---:|---:|---:|---:|
  | BF16 | — | 7.05 | 100 | 89.90 | 85.71 |
  | IQ3_S (3.50 bpw) | 11.8 GB | 7.07 | 100 | 89.39 | 85.71 |
  | IQ3_XXS (3.0 bpw) | — | — | — | 88.89 | 84.57 |
  | Unsloth UD-IQ3_S (3.52 bpw) | — | 7.16 | 96.67 | 89.90 | 84.00 |

  `-mtp` builds add about 0.35 GB. Apache-2.0. — [ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF)
- **byteshape ShapeLearn GGUF**: 2.56–3.84 bpw, evaluated on a multi-benchmark suite (incl. ACEBench, BFCL V4) against BF16, with plots on RTX GPUs only. Speculative decoding "adds another 1.4–1.8x". — [byteshape/Qwen3.8-27B-GGUF](https://huggingface.co/byteshape/Qwen3.8-27B-GGUF)
- **mlx-community OptiQ-4bit**: per-layer bit allocation from a KL sensitivity pass. No final KLD published. — [mlx-community/Qwen3.8-27B-OptiQ-4bit](https://huggingface.co/mlx-community/Qwen3.8-27B-OptiQ-4bit)
- **PocketAiHub MLX at 4K context**: 4-bit 36.6 tok/s at 21.80 GB peak; 8-bit 20.1 tok/s at 37.27 GB peak. The hardware is not stated in the summary. — [PocketAiHub/Qwen3.8-27B-MLX](https://huggingface.co/PocketAiHub/Qwen3.8-27B-MLX)
- **oQe refit** (oMLX PR #4385, in 0.7.1.dev1) lowers KL at the same layout. Validation was on Qwen3.5-9B and Qwen3.6-35B, not on the 27B; this is from the repo's earlier Flash-Next note. Jundot's 27B oQ4e/oQ8e were re-uploaded 10-11/10-12. — [repo note research/qwen38-flashnext-derivatives-20261009.md §11](../../research/qwen38-flashnext-derivatives-20261009.md); [r/oMLX 1x3d7f8](https://www.reddit.com/r/oMLX/comments/1x3d7f8/jundot_has_been_reuploading_quants_using_improved/)
- **Swift 1.5 INT4 exports** (AWQ, AutoRound, AWQ+GPTQ) score within about 3 pts of Swift BF16 on GPQA/IFBench/AIME, single seed. — [Swift 1.5 card](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b)

### Inferences
- **The 4-bit gap depends on method.** The ddalcu 4-bit KL (0.32) is about 25× the MTPLX 4-bit dynamic KL (0.012). Plain affine 4-bit/gs64 differs from calibrated or mixed 4-bit, and the measurement methods differ (sampled positions vs teacher-forced), so absolute values are not comparable across cards. Within each card, the ordering is consistent: 8-bit ≥ 6-bit ≫ plain 4-bit.
- **Recommendation for the M4 Max 128 GB** (inference, not measured on the rig):
  - Coding and agent use: 6-bit or 8-bit (oQ6e/oQ8e or MLX-Serve 6/8-bit), or a calibrated ~4.5–5 bpw mixed pack (MTPLX Optimized Speed, ThinkingCap-style DWQ, GSQ-RCO IQ3_S+), when decode speed matters more.
  - Plain 4-bit gs64 is the riskiest choice for long agent sessions.
- **Speed trade-off.** Decode cost scales with bpw: on the M4 Max with MTP, 4-bit gives 69.6 tok/s against 46.4 tok/s for 8-bit. The repo's 8-bit choice for the 27B campaigns therefore trades about 30% decode for quality.

### Gaps
- No single study compares 4 / ~4.7 (calibrated) / 6 / 8 bpw for base Qwen3.8-27B on agentic tasks.
- No KLD exists for the Jundot refit oQ packs of the 27B.
- orcarouter's MLX KL table was truncated in search results.
- AWQ True2456 5.0 bpw quality was not re-checked (it is a repo reference from a prior campaign).

---

## 5. 27B dense vs Qwen3.8-Flash-Next on agentic benchmarks run locally

### Takeaway
No source compares the two head-to-head on Terminal-Bench 2.x, SWE-bench Verified or Aider polyglot at local 4–8-bit quantization. On official BF16 numbers, both are close on SWE-bench Pro (27B 61.7 vs Flash-Next about 62.5), Flash-Next leads on DeepSWE (58.7 vs 42.2), and only the 27B publishes Terminal-Bench 2.1 (73.0). Flash-Next decodes 2–3× faster on the rig, so the 27B's case rests on memory headroom and quality per bit, not speed.

### Cited Findings
- **Qwen3.8-27B official**: Terminal-Bench 2.1 (Terminus) 73.0; SWE-bench Pro 61.7 (refined task set, Claude Code harness, 256K); DeepSWE 1.1 42.2; QwenSWEBench (in-house) 79.0. — [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)
- **Flash-Next** is listed at SWE-bench Pro 62.5 and DeepSWE 58.7, per the aggregator citing the model card. The architecture paper says Flash-Next-Base outperforms 27B-Base on all 14 base benchmarks. — [BenchLM](https://benchlm.ai/models/qwen3-8-flash-next); [Qwen3.8-Next architecture paper](https://arxiv.org/pdf/2608.30320)
- **Swift 1.5 27B** (ukisai, BF16, 5 trials/task, context 131K): Terminal-Bench 2.1 69.21 base → 72.13 Swift 1.5. The base number differs from Qwen's 73.0, a different harness/setting. — [Swift 1.5 card](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b)
- **Local speed** (this repo, M4 Max 128 GB): 27B 8-bit decode 43.5 / 32.4 tok/s at 32K / 128K (best arm). The Flash-Next driver runs at about 113 tok/s, per the Dankpaws Swift pack on an M5 Ultra 96 GB after 4K. That Flash-Next figure is author-reported on different hardware; the repo's own Flash-Next numbers are in `docs/models/qwen3.8-flash-next.md`. — repo `bench/engine-updates-2026-10/results/27b-summary.md`; [Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw](https://huggingface.co/Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw)
- **Community sentiment**: several r/oMLX posts (10-05 to 10-11) complain the 27B is slow on Macs, at 10–20 tok/s on an M5 Pro 48 GB and "sloooow" on an M5 128 GB with the Qwen-pi variant. Anecdotal, configuration unknown. — [r/oMLX 1x2zelw](https://www.reddit.com/r/oMLX/comments/1x2zelw/qwen_38_27b_4_and_8bit_runs_like_a_pig_is_it_me/); [r/oMLX 1wybhas](https://www.reddit.com/r/oMLX/comments/1wybhas/qwen_pi_27b/)

### Inferences
- **The comparison remains open.** The repo's own harness-matrix (`bench/harness-matrix/results/opencode/qwen3.8-27b-8bit.md` and `…/qwen3.8-flash-next.md`) is the only local same-harness comparison available. Any claim that the 27B is "better as an agent" needs a local Terminal-Bench subset run at the chosen quant.
- **Expected gain from Swift-style tuning on the 27B.** Lower thinking tokens (−16% mean on Terminal-Bench) cut wall time per turn modestly. That gain is smaller than the 2–3× time-to-final-answer cut seen on Flash-Next single-shot reasoning, because agent turns are dominated by tool loops, not long thinking.

### Gaps
- I found no published local (4–8-bit, Mac) Terminal-Bench, SWE-bench Verified or Aider polyglot numbers for either model.
- Qwen publishes no Terminal-Bench 2.1 score for Flash-Next.
- SWE-bench Verified and Aider polyglot are not reported for either model in the sources found. Qwen switched to SWE-bench Pro and DeepSWE.
