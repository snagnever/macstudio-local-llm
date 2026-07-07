# Gemma-4-E4B

> **Status: 🟡 NICHE** — tiny / FIM / quick tool-calls only.
> **⚠️ MATH 14 %** — never use for math or reasoning. Value on this rig is coexistence, not capability: 8.97 GB, loads in seconds, pairs with anything.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it) | HF card |
| Parameters | 4.5B effective (8B total with embeddings) — "E4B" = **effective-4B**; Per-Layer Embeddings (PLE) shrink the effective count for on-device deployment | HF card |
| Architecture | Dense, 42 layers; hybrid attention — local sliding-window (512 tokens) + full global attention; unified K/V in global layers with Proportional RoPE | HF card |
| Native context | 128K tokens | HF card |
| License | Apache 2.0 | HF card |
| Modalities | Text, image, and audio (native on E2B/E4B); video via frame sequences; variable image aspect ratios/resolutions | HF card |
| Reasoning | None — no thinking tokens (`think=0` in every local response) | HF card + local |
| Tool calling | ✓ "Native support for structured tool use, enabling agentic workflows" | HF card |
| Vendor sampling | `temperature=1.0, top_p=0.95, top_k=64` | HF card |
| Vendor claims | MMLU Pro 69.4 %, GPQA Diamond 58.6 %, LiveCodeBench v6 52.0 %, MRCR v2 25.4 % avg *(vendor — not reproduced locally; local GPQA/LCB use different configs, see below)* | HF card |
| Release / cutoff | Release date not clearly stated on card (fetched 2026-07-05); card cites a January 2025 training-data cutoff | HF card |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `gemma-4-e4b-it-mlx` | [lmstudio-community/gemma-4-E4B-it-MLX-8bit](https://huggingface.co/lmstudio-community/gemma-4-E4B-it-MLX-8bit) | MLX safetensors | 8-bit (LM Studio team, `mlx_vlm` conversion) | 8.97 GB (HF card lists 8.94 GB) | LM Studio MLX | 🟡 **NICHE 2026-05-22** | Vision + tools flags set; fills the FIM / quick-call slot |

**Pinned HF revisions** (verified 2026-07-06 via HF API: no upstream commits since download → local snapshot = current `main`): 8-bit: [`c63b2f9`](https://huggingface.co/lmstudio-community/gemma-4-E4B-it-MLX-8bit/tree/c63b2f9519d800e591cb331e5c19c021f66bf79a) (downloaded 2026-05-17).

## Architecture & spec notes
- Dense 4B-class — the smallest model in the lineup by far. No MoE routing; its throughput story is therefore *worse* relative to the MoE siblings than the size suggests (see Local performance).
- 512-token sliding-window on most layers keeps KV growth cheap; combined with the 8.97 GB footprint it coexists with any resident model under the ~80 GB weights+KV rule.
- Like all Gemma 4: **no thinking tokens** — single-pass answers only. What you see is the model's ceiling; there is no "raise the cap" recovery path for hard problems (and indeed E4B had 0 truncations across the entire Phase 2 suite — it never spirals, it just answers, sometimes wrongly).

## Local performance (measured)

| Metric | MLX 8-bit |
|---|---|
| Sustained generation | **70–75 gen t/s** (ops-agent 70.9; creative 73.7; doc-summary 75.4) |
| Effective throughput (ops-agent) | **62.9 t/s** (prefill-test drops to 29.1 eff) |
| Tool-call runs | jdhodges @ 42.5 t/s; Veerman @ 60.3 t/s |
| Memory | 8.97 GB weights — tiny; loads in seconds, no pairing constraints |
| Full Phase 2 suite wall-clock | ~2.5 h (fastest of the four Gemmas) |

**Key surprising finding:** E4B is **not** dramatically faster than the 26B MoE at 4-bit — 70.9 vs 100.3 ops-agent gen t/s. MLX optimises MoE A3B/A4B expert routing well, so the small-dense model has **no inference edge** on this rig. Its value is coexistence (footprint), not speed.

Source: [M4_MAX_128GB_NOTES.md § Phase 2 results](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md), throughput table in [local-llm-reference.md](../local-llm-reference.md).

## Quality benchmarks (measured)

Config: `temp=0, seed=42`, n=100 per knowledge bench (LCB n=50), run 2026-05-20 → 2026-05-22 as Phase 2 model #7 ([testing-plan](../testing-plan.md)). **Zero truncations** on any bench (contrast 26B-A4B's LCB truncation profile).

| Bench | `gemma-4-e4b-it-mlx` (8-bit) | Best Gemma sibling (`26b-a4b@6bit`) | Δ |
|---|---|---|---|
| HumanEval (100) | **91 %** | 97 % | −6 |
| LiveCodeBench v6 (50) | **68 %** | 80 % | −12 |
| MMLU | **65 %** | 78 % | −13 |
| MATH | **14 % ⚠️** | 83 % | **−69** |
| DROP | **65 %** | 79 % | −14 |
| GPQA (raw) | **34 %** | 53 % | −19 |
| jdhodges tool-calling (40) | **87.5 %** | 97.5 % | −10 |
| Veerman tool-calling (12) | **66.7 %** | 83.3 % | −16.6 |
| Knowledge avg (HE+MMLU+MATH+DROP+GPQA) | **53.8 %** | 78.0 % | −24.2 |
| Terminal-Bench 2.0 (Phase B, 2026-05-29) | **4.5 %** (4/85 PASS, 10 errored, 6.4 h) | 21.3 % | −16.8 |

- **MATH collapses to 14 %** — the 4B size simply can't handle hard symbolic math. This is the disqualifying number: never route math or multi-step reasoning here.
- **T-Bench 4.5 % confirms the 4B agentic floor** — the agent runs *cleanly* (only 10 errored tasks vs 40+ on bigger models; it isn't timing out), the verifier just scores 0 on 85/89 tasks. It doesn't solve; it politely fails fast (4.3 min/task mean).
- HumanEval 91 % and jdhodges 87.5 % are the usable numbers — single-shot autocomplete and call-and-format work.

Raw data: `tools/local-llm-bench-m4-32gb/benchmarks/runs/` (label `gemma-4-e4b-mlx-8bit`); full matrix in [testing-plan.md](../testing-plan.md) (Phase 2 #7).

## Feasibility & verdict

- **2026-05-20 → 05-22 — Phase 2 full suite: 🟡 NICHE.** The plan's question ("Is `gemma-4-e4b` viable for the FIM / quick-call slot?") answers **yes — and only that**. It fills the previously open FIM / quick-call slot in [local-llm-reference.md](../local-llm-reference.md); it is explicitly **not a daily-driver fallback**.
- **What it's for:** inline autocomplete (interim FIM until Qwen 2.5 Coder 7B is added), one-shot tool calls, call-and-format work, and being the only fast Gemma that fits beside `coder-next@6bit` (64.76 GB + 8.97 GB = 73.7 GB, under the 80 GB rule).
- **What it's not for:** math (14 %), reasoning, knowledge lookups (MMLU 65 %, GPQA 34 %), multi-step agentic loops (T-Bench 4.5 %), or anything where Veerman-style holdout tool robustness matters (66.7 %).
- **Speed caveat:** don't pick it "because small = fast" — `gemma-4-26b-a4b@4bit` decodes ~40 % faster (100 vs 70 gen t/s) with vastly better quality. Pick E4B only when the 8.97 GB footprint is the point.

Plans: [2026-05-20-gemma-4-phase-2.md](../benchmark-plans/2026-05-20-gemma-4-phase-2.md) · [testing-plan.md](../testing-plan.md)

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| Wrong answers on math / symbolic problems | 4B capability floor — MATH 14 % | **No fix.** Route math to `gemma-4-26b-a4b@6bit` (83 %) or `qwen3.6-27b` (88 %) |
| Near-zero agentic-loop success | 4B size floor on T-Bench (4.5 %) | Use `qwen/qwen3-coder-next` for agent loops |
| `<|channel|>` marker leak in Hermes-style clients (seen on sibling `26b-a4b@6bit`) | Client wraps a no-reasoning Gemma 4 in a harmony/channel reasoning template | Family-level caution: use a plain chat template; see [gemma-4-channel-token-leak-writeup.md](../gemma-4-channel-token-leak-writeup.md) |

## Loading & memory
- 8.97 GB weights — **coexists with anything**: loads in seconds, no eviction needed, no pairing math required.
- Reference pairing: `coder-next@6bit` (64.76 GB) + E4B = 73.7 GB — the only fast Gemma that fits beside the 6-bit coder under the ~80 GB rule.
- Sliding-window attention (512) keeps KV growth minimal; context can sit at 32–64k without meaningful pressure.

## Client configuration
- Model id: `gemma-4-e4b-it-mlx` (LM Studio `/v1` endpoint, port 1234).
- Sampling: vendor recommends `temperature=1.0, top_p=0.95, top_k=64`; local benches ran temp 0 / seed 42 for reproducibility.
- Tool calling works through LM Studio's parser (jdhodges 87.5 %) — fine for one-shot calls; expect misses on holdout-style suites (Veerman 66.7 %).
- Vision + audio advertised on the card and vision flag set in LM Studio; vision quality not yet benchmarked locally.
- Bench note: Gemma 4 family rule is `--max-tokens 65536` on LCB, though E4B itself never truncated.

## External links
- Vendor: https://huggingface.co/google/gemma-4-e4b-it
- MLX conversion: https://huggingface.co/lmstudio-community/gemma-4-E4B-it-MLX-8bit (LM Studio team, `mlx_vlm`, 8-bit)

## History
- **2026-05-20 → 05-22** — Phase 2 full suite as model #7 ([plan](../benchmark-plans/2026-05-20-gemma-4-phase-2.md)); ~2.5 h wall-clock, 0 truncations. Verdict: fills the FIM / quick-call slot, MATH 14 % disqualifies everything else.
- **2026-05-24** — Step B Gemma truncation reruns: E4B unaffected (0 truncations); scores final.
- **2026-05-29** — Terminal-Bench 2.0 Phase B leg B1: **4.5 %** — confirmed 4B agentic floor; FIM / quick-call verdict unchanged.
