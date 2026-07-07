# Gemma-4-26B-A4B (it)

> **Status: 🟢 DAILY DRIVER — Code role winner.**
> `@6bit` is the rig's LiveCodeBench ceiling (**80 %**, +18 pp over the best Qwen); `@4bit` is the fastest model on the rig (**100+ gen t/s**). Both quants resident-friendly; `@6bit` is the ⭐ recommended pairing partner for `coder-next@4bit`.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [google/gemma-4-26b-a4b-it](https://huggingface.co/google/gemma-4-26b-a4b-it) | HF card (fetched 2026-07-05) |
| Parameters | 25.2B total MoE / 3.8B active (marketed as 26B-A4B; local lineup uses 26B/4B) | HF card + [reference lineup](../../local-llm-reference.md#the-model-lineup) |
| Architecture | 30 layers; 128 experts, 8 active + 1 shared; hybrid attention — 1024-token sliding window + global-attention layers; unified K/V + Proportional RoPE | HF card |
| Native context | 256K tokens | HF card |
| License | Apache 2.0 (per HF card fetch 2026-07-05) | HF card |
| Modalities | Text + image (vision encoder ~550M params, variable aspect/resolution) | HF card |
| Reasoning | **None** — no thinking channel; `think=0` in every local response. Compensates by writing long, exhaustive code | HF card + [M4 notes §11](../../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md) |
| Release | Training cutoff January 2025; release date not stated on card (fetched 2026-07-05) | HF card |
| Vendor sampling | `temperature=1.0, top_p=0.95, top_k=64` | HF card |
| Vendor claims | MMLU Pro 82.6 %, AIME 2026 (no tools) 88.3 %, LiveCodeBench v6 77.1 %, Codeforces ELO 1718, GPQA Diamond 82.3 %, MMMU Pro 73.8 % *(vendor — not reproduced locally; local LCB v6 n=50 subset scored 80 % @6bit, not directly comparable)* | HF card |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `gemma-4-26b-a4b-it-mlx@4bit` | [lmstudio-community/gemma-4-26B-A4B-it-MLX-4bit](https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-MLX-4bit) | MLX | 4-bit (LM Studio team, `mlx_vlm` conversion) | 15.64 GB | LM Studio MLX | 🟢 **DAILY DRIVER** | Fastest model on rig (100–106 gen t/s); coding/tool-calling ties @6bit, hard-bench tax (LCB −14 pp) |
| `gemma-4-26b-a4b-it-mlx@6bit` | [lmstudio-community/gemma-4-26B-A4B-it-MLX-6bit](https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-MLX-6bit) | MLX | 6-bit (LM Studio team, `mlx_vlm` conversion) | 21.81 GB | LM Studio MLX | 🟢 **DAILY DRIVER** | Family flagship; rig LCB ceiling 80 %; Code-role winner in the [recommended stack](../../local-llm-reference.md#recommended-stack--planning--code--agent) |

**Pinned HF revisions** (verified 2026-07-06 via HF API: no upstream commits since download → local snapshot = current `main`): @4bit: [`3af5252`](https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-MLX-4bit/tree/3af5252ed1e675e6bba9be8cc3087bc00920799c) (downloaded 2026-05-17) · @6bit: [`fd6c729`](https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-MLX-6bit/tree/fd6c729deddbd6211b37be13f2a42ef2603b3b56) (downloaded 2026-05-17).

Both quants advertise `vision: true` and `trainedForToolUse: true` in LM Studio model metadata ([reference lineup](../../local-llm-reference.md#the-model-lineup)). Model ids above are exactly what `GET /v1/models` returns — use verbatim; `lmstudio-community/...` paths will 404.

## Architecture & spec notes

- **MoE 26B total / 4B active** — near-dense-27B quality at MoE decode cost; 100+ t/s at 4-bit is why it beats every dense model on throughput.
- **Sliding-window attention (window 1024) on 25 of 30 layers** — those layers' KV is capped regardless of context. Only **5 `full_attention` layers** grow, at 8 KV heads × head_dim 256. KV grows unusually slowly → this is the rig's best *pairing* model (see [Loading & memory](#loading--memory) and the [two-resident pair context math](../../local-llm-reference.md#two-resident-pair-context-math)).
- **No-reasoning model.** It never emits thinking tokens; instead it writes long, exhaustive code (often re-deriving full helpers), which is what drives its LCB truncations — a different failure profile from Qwen thinking-spirals ([M4 notes §11](../../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)). Never wrap it in a reasoning/harmony template — see [Known issues](#known-issues--fixes).
- MLX conversions by the LM Studio team via `mlx_vlm` (community model program; vision-capable conversion path), per both HF conversion cards (fetched 2026-07-05).

## Local performance (measured)

Phase 2 throughput sweep, ops-agent scenario headline ([M4 notes Phase 2 table](../../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)):

| Metric | `@4bit` | `@6bit` |
|---|---|---|
| Gen t/s (ops-agent) | **100.3** (creative-writing 106.0, doc-summary 107.6) | 80.8 (creative-writing 85.3) |
| Effective t/s (ops-agent, incl. prefill) | **80.7** | 66.6 |
| Effective t/s under heavy prefill (prefill-test) | 17.9 | 20.5 |
| T-Bench per-task mean | 10.8 min | 9.7 min |

Context: `@4bit` is the **fastest model benched on this rig** — beats every Phase 1 model and even the 4B-dense `gemma-4-e4b` (70.9 gen t/s), because MLX optimises MoE A4B routing well. `@6bit` is ~4× faster than `qwen3.6-27b` dense (20 t/s).
Source: [M4_MAX_128GB_NOTES.md § Phase 2 results](../../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md), [reference performance table](../../local-llm-reference.md#performance-expectations-verified-on-this-rig).

## Quality benchmarks (measured)

Config: n=100 per bench (LCB n=50), `temp=0, seed=42`, ctx 32,768; LCB/GPQA reruns at `--max-tokens 65536`. Phase 2 (2026-05-20 → 05-22) + Step B reruns (2026-05-24) + T-Bench Phase A/B (2026-05-24 → 05-29). Plans: [phase-2](../../../bench/gemma-4-phase2/plan.md) · [LCB phase-1](../../../bench/lcb-phase1/plan.md) · [terminal-bench A+B](../../../bench/terminal-bench/plan.md).

| Bench | `@4bit` | `@6bit` | Notes |
|---|---|---|---|
| HumanEval (100) | **98 %** | 97 % | Quant-insensitive; both at rig top |
| LiveCodeBench v6 (n=50) | 66 % (8 trunc post-Step-B) | **80 %** (1 trunc) | **Rig ceiling** — +18 pp over best Qwen (`27b` 62 %) |
| MMLU | 78 % | 78 % | −10 pp vs `qwen3.6-27b` (88) |
| MATH | 80 % (1 trunc) | 83 % | |
| DROP | 79 % | 79 % | |
| GPQA (raw, 65k cap) | 47 % (1 trunc) | 53 % (2 trunc) | |
| Knowledge avg (HE+MMLU+MATH+DROP+GPQA) | 76.4 % | **78.0 %** | Best in Gemma family; −7.8 pp vs `27b` (85.8 %) |
| jdhodges tool-calling (40) | 97.5 % | 97.5 % | |
| Veerman tool-calling (12) | 83.3 % | 83.3 % | |
| Terminal-Bench 2.0 (89 tasks, ⌛0.5x cap) | 20.2 % (18 PASS) | 21.3 % (19 PASS) | vs `coder-next` **32.6 %** — see below |

**Quant A/B verdict:** the 4→6-bit cost is **material on hard benches** (LCB −14 pp, GPQA −6 pp) but invisible on HumanEval, jdhodges, Veerman — and only 1.1 pp on T-Bench. Pick `@6bit` for single-shot code correctness, `@4bit` when throughput matters more than the last 14 pp of LCB.

**Truncation profile (Step B, 2026-05-24):** LCB truncations at 32k are mostly *real model limits*, not cap-too-tight. Rerun at 65k: `@6bit` 4 → 1 truncation (Q28 recovered, 78 → 80 %); `@4bit` recovered only Q2 (64 → 66 %) — **8 of 9 remaining truncations are genuine model limits at the 65k cap**. Operational rule: run LCB on Gemma 4 with `--max-tokens 65536`, but expect ~+2 pp, not +10–15. Explicit truncated-question list in [M4 notes § Phase 2 truncations](../../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).

**The LCB lead does NOT transfer to agentic shell.** T-Bench inverts the LCB ranking: `@6bit` drops from 1st (80 %) to 5th (21.3 %); best Gemma on the rig is 22.5 % (`31b` dense) vs `coder-next` 32.6 %. Gemma is trained general-purpose/one-shot, not for agent loops — keep `coder-next` as the agentic default ([M4 notes § T-Bench Phase B](../../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)).

Vision quality: ⏸ not benchmarked (advertised on both quants; `@6bit` is the default vision pick, workload-specific).
GGUF-engine A/B vs MLX: ⏸ not run (deferred since Phase 1).

Raw data: `tools/local-llm-bench-m4-32gb/benchmarks/runs/` incl. canonical `livecodebench_gemma-4-26b-a4b-it-mlx@{4bit,6bit}_MERGED_summary.json` and `tbench_gemma-4-26b-a4b-it-mlx-*_summary.json`. Status rows: [testing-plan.md](../../testing-plan.md) (2 #4, 2 #5).

## Role & verdict

- **Code role winner** in the [recommended stack](../../local-llm-reference.md#recommended-stack--planning--code--agent): `@6bit` for single-shot algorithm problems, isolated edits, code-generation peak — quality *and* speed (80 %, 80.8 t/s).
- **Fast-coder slot:** `@4bit` when raw decode + tool-calling matter and the last 14 pp of LCB doesn't.
- **Fast generalist peer** to `qwen3.6-35b-a3b@6bit` for non-vision work; strict winner if vision is needed.
- **Not** the agentic default (T-Bench ~11 pp behind `coder-next`) and **not** the knowledge generalist (no Gemma comes within 7 pp of `qwen3.6-27b`'s knowledge avg).
- Displaces `gemma-4-31b` dense entirely (6× slower for indistinguishable quality) and is not substituted by `gemma-4-e4b` (MATH collapses to 14 % at 4B).

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| Emits raw `<|channel>thought <channel|>` markers in an empty loop, never answers (seen on `@6bit` in Hermes) | Client wraps this **no-reasoning** model in a harmony/channel reasoning template it was never trained for → empty `thought` loop; markers leak because the tokenizer splits `<|channel|>` into plain text. **Not the quant.** | Disable the reasoning format for this model (plain/none) — fixes most cases. Verify the build: `tok.encode("<|channel|>")` must be **one** id, not 4–5 (else the conversion lacks the special tokens — re-pull or patch tokenizer config); update `mlx-lm` as third tier. Localize: clean via `mlx_lm.generate` CLI but broken in client → client wrapper. Full writeup: [gemma-4-channel-token-leak-writeup.md](channel-token-leak-writeup.md); summary in [reference troubleshooting](../../local-llm-reference.md#troubleshooting) |
| LCB/hard-problem truncation at 32k cap | Writes long, exhaustive code (no thinking channel to spiral, but re-derives full helpers) | Raise `--max-tokens` to 65,536 for LCB-class tasks; expect modest recovery (~+2 pp) — most 32k truncations are real model limits (Step B) |

## Loading & memory

- Alone: `@4bit` 15.64 GB / `@6bit` 21.81 GB — tons of headroom either way ([memory math](../../local-llm-reference.md#loading-strategy)).
- **KV-cheap by design:** only 5 of 30 layers grow KV (sliding window caps the other 25) → ~2.9 GB at 65k fp16, ~5.6 GB at 131k.
- **⭐ Recommended two-resident config: `coder-next@4bit` (~44 GB) + `gemma-4-26b-a4b@6bit` (21.8 GB) ≈ 66 GB weights.** Both at 65,536 ctx → ~70.5 GB total, ~10 GB slack under the 80 GB rule. Push the coder to 131k if needed (~74 GB); don't set 262k on both (~83 GB, over the line). Full table: [two-resident pair context math](../../local-llm-reference.md#two-resident-pair-context-math).
- Avoid `coder-next@6bit` (64.76 GB) + `@4bit` = 80.4 GB — at the rule *before* KV; the historical queue-stall combo.
- Also viable: `@6bit` + `qwen3.6-27b` ≈ 44.6 GB (code + planning day, no agent loops).

## Client configuration

- Model ids: `gemma-4-26b-a4b-it-mlx@4bit` / `gemma-4-26b-a4b-it-mlx@6bit` (LM Studio `/v1` endpoint, port 1234) — verbatim from `GET /v1/models`.
- Sampling: vendor recommends `temperature=1.0, top_p=0.95, top_k=64` (HF card); local benches ran `temp 0 / seed 42` for reproducibility.
- Tool calling works natively (jdhodges 97.5 %, Veerman 83.3 % on both quants) — no template surgery.
- **Never enable a reasoning/harmony format for this model** in Hermes or similar clients (see Known issues).
- OpenCode entry included in the [reference client configs](../../local-llm-reference.md#client-configurations).

## External links

- Vendor: https://huggingface.co/google/gemma-4-26b-a4b-it
- MLX 4-bit conversion: https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-MLX-4bit (LM Studio team via `mlx_vlm`)
- MLX 6-bit conversion: https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-MLX-6bit (LM Studio team via `mlx_vlm`)

## History

- **2026-05-18** — both quants inventoried on rig; queued as Phase 2 #4/#5 in [testing-plan.md](../../testing-plan.md).
- **2026-05-20 → 05-22** — Phase 2 full sweep ([plan](../../../bench/gemma-4-phase2/plan.md)): `@6bit` named Gemma flagship, `@4bit` named rig speed king; results in [M4 notes](../../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).
- **2026-05-24** — Step B LCB truncation reruns at 65k: `@4bit` 64 → 66 %, `@6bit` 78 → **80 %** (rig ceiling); most 32k truncations confirmed as real model limits.
- **2026-05-24 → 05-29** — Terminal-Bench 2.0 Phase A+B ([plan](../../../bench/terminal-bench/plan.md)): `@6bit` 21.3 %, `@4bit` 20.2 % — LCB lead does not transfer to agentic shell; `coder-next` keeps the Agent slot.
- **2026-05-29** — Code-role winner in the post-T-Bench [recommended stack](../../local-llm-reference.md#recommended-stack--planning--code--agent); `coder-next@4bit` + `@6bit` named ⭐ two-resident pair.
- *(undated)* — channel-token-leak incident on `@6bit` in Hermes diagnosed as client template mismatch, not quant ([writeup](channel-token-leak-writeup.md)).
