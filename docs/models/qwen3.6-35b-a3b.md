# Qwen3.6-35B-A3B

> **Status: 🟢 DAILY DRIVER — fast generalist / MoE middle ground** (`@6bit` fully benched).
> `@8bit` variant: ⏸ quant A/B pending (Phase 2 #9).
> The rig's "goldilocks middle": thinking-mode reasoning at MoE speed — between `qwen/qwen3-coder-next` (agentic) and `qwen3.6-27b` (knowledge), dominating neither slot.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | HF card (fetched 2026-07-05) |
| Parameters | 35B total MoE / 3B active — 256 experts, 8 routed + 1 shared activated | HF card |
| Architecture | Hybrid `10 × (3 × (Gated DeltaNet → MoE) → 1 × (Gated Attention → MoE))`, 40 layers; MLX arch id `qwen3_5_moe` | HF card + [testing-plan.md](../testing-plan.md) |
| Native context | 262,144 tokens (up to 1,010,000 with YaRN) | HF card |
| License | Apache 2.0 | HF card |
| Release date | not stated on card (fetched 2026-07-05) | HF card |
| Modalities | text, image, and video understanding (multimodal) | HF card |
| Reasoning | Thinking mode **enabled by default** — reasoning traces before responses; "preserve thinking" supported for historical messages | HF card |
| Tool calling | ✓ (`tool-call-parser qwen3_coder`) | HF card |
| Vendor sampling | thinking: `temperature=1.0, top_p=0.95, top_k=20, presence_penalty=1.5`; precise coding: `temperature=0.6, top_p=0.95, top_k=20`; non-thinking: `temperature=0.7, top_p=0.80, top_k=20, presence_penalty=1.5` | HF card |
| Vendor claims | SWE-bench Verified 73.4, MMLU-Pro 85.2, HMMT Feb 2026 83.6 *(vendor — not reproduced locally)* | HF card |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `qwen3.6-35b-a3b@6bit` | [mlx-community/Qwen3.6-35B-A3B-6bit](https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-6bit) | MLX safetensors | 6-bit (mlx-vlm 0.4.4 conversion) | 29.09 GB | LM Studio MLX | 🟢 **DAILY DRIVER** | Full Phase 1 suite + LCB backfill + T-Bench 2.0 benched |
| `qwen3.6-35b-a3b@8bit` | [mlx-community/Qwen3.6-35B-A3B-8bit](https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-8bit) | MLX safetensors | 8-bit (mlx-vlm 0.4.4 conversion) | 37.75 GB | LM Studio MLX | ⏸ **Pending quant A/B (Phase 2 #9)** | Same weights, heavier quant — does it close the knowledge gap to `qwen3.6-27b`? All benches TBD |
| `qwen3.6-35b-a3b-mtp` | [unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF) | GGUF | UD-Q6_K_XL | 32.61 GB | LM Studio llama.cpp | ⚗️ **speed study only** | Not a quality candidate — benched only to isolate Draft MTP speculative decoding (see [Draft MTP tuning](#draft-mtp-speculative-decoding--speed-tuning-2026-07-10)). MLX `@6bit` stays the pick |

**Pinned HF revisions** (verified 2026-07-06 via HF API: no upstream commits since download → local snapshot = current `main`): @6bit: [`cb7e092`](https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-6bit/tree/cb7e092ef8efe540bc3672c8929c4adbe5f4f759) (downloaded 2026-05-17) · @8bit: [`e06a74e`](https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-8bit/tree/e06a74e6236a60c8367e1a3214e83d8b61b637b0) (downloaded 2026-05-17).

## Architecture & spec notes
- 256-expert MoE with only **3B active per token** → near-dense-7B decode cost at 35B-class quality; MLX optimises the A3B routing well (see the e4b finding: small-dense has no inference edge over this).
- **Thinking model** — emits `<think>...</think>` reasoning before answers. This is the source of both its MATH/GPQA strength and its truncation/spiral tax (see Known issues).
- Hybrid Gated DeltaNet / Gated Attention layout per vendor card — same `qwen3_5_moe` family as the Phase-5 arrival `agents-a1-xl` ([plan](../../bench/phase-5-new-arrivals/plan.md)).
- Vision + tools advertised in LM Studio metadata (`vision: true`, `trainedForToolUse: true`).
- The earlier MoE-MLX tool-call regression seen on `mlx-community` **4-bit** checkpoints of this model does **not** appear on the 6-bit variant (confirmed on T-Bench leg B3).

## Local performance (measured)

`@6bit` numbers; **`@8bit`: all throughput TBD — pending Phase 2 #9 quant A/B.**

| Metric | `@6bit` |
|---|---|
| Generation | **85–92 t/s** (~90 t/s sustained on the 3-q speed probe; 91.6 gen creative-writing, 85.5 gen ops-agent) |
| Effective (ops-agent) | **71.4 t/s** — what you actually wait for in agentic loops |
| Effective (creative-writing / doc-summary / prefill-test) | 86.9 / 55.9 / 22.9 t/s |
| Prefill @ 8.5k ctx | **10.8 s** (effective drops to 9.0 t/s) |
| Tool-call suite throughput | jdhodges 72.4 t/s, Veerman 85.8 t/s |
| Wall-clock, full Phase 1 suite | ~14.7 h (~6.5 h of it GPQA thinking spirals) — vs 37.6 h for 27b dense, 1.9 h for coder-next |

Context: ~4.5× faster than `qwen3.6-27b` dense (20 t/s), faster than `coder-next` (68–70 t/s), slower than `gemma-4-26b-a4b@4bit` (100–106 t/s).
Source: [local-llm-reference.md § Performance Expectations](../local-llm-reference.md), [testing-plan.md § Effective throughput](../testing-plan.md), [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).

### Draft MTP (speculative decoding) — speed tuning (2026-07-10)

The unsloth GGUF (`qwen3.6-35b-a3b-mtp`) carries an MTP draft head that LM Studio
exposes as the **Draft MTP** load toggle. A/B on the *same* GGUF (only the toggle
flipped; ctx 65k, parallel 4, thinking off) — gen t/s:

| Scenario | MTP off | MTP on (draft=2) | effect |
|---|---:|---:|---:|
| creative-writing | 74.7 | 68.1 | **−9 %** |
| doc-summary | 76.0 | 92.7 | **+22 %** |
| ops-agent | 72.7 | 82.2 | **+13 %** |
| prefill-test | 72.9 | 71.0 | −3 % |

**MTP is a per-workload toggle** (textbook speculative decoding): on for
structured/agentic/summarization, off for creative writing. **Draft depth 2 is
the optimum** — 3/4/6/8 are monotonically worse on every scenario (single draft
head → acceptance collapses past ~1 token; each reject still costs a forward
pass). The dense 27B reproduces the same profile, so this is a draft-head ×
workload property, not a MoE effect. This GGUF is also ~25 % slower than the MLX
`@6bit` on creative-writing (format/quant gap, independent of MTP) — **the MLX
build stays the daily driver; the value here is the tuning rule.** Full data +
depth curve: [bench/qwen3.6-mtp/plan.md](../../bench/qwen3.6-mtp/plan.md).

## Quality benchmarks (measured)

Config: n=100 per knowledge bench (LCB n=50, jdhodges 40, Veerman 12), `temp=0, seed=42`, LM Studio MLX. Phase 1 run 2026-05-17→19; LCB backfill 2026-05-24 at `--max-tokens 65536`; T-Bench 2.0 2026-05-26→29. **`@8bit`: all benches TBD (Phase 2 #9).**

| Bench | `@6bit` | Notes |
|---|---|---|
| HumanEval | **87 %** | Worst of the Phase 1 trio (27b 93, coder-next 89) — but HE is saturated; LCB is the canonical coding signal |
| LiveCodeBench v6 | **54 %** (27/50) | 6 truncations *at 65k* (Q3, Q4, Q23, Q33, Q39, Q44 — real spirals, not cap artifacts; Q4 rerun on clean state confirmed). Most spiral-prone of the trio; ceiling ~66 % with cap ≥ 96k |
| MMLU | **83 %** | 2 truncations. −5 pp vs 27b's 88 |
| MATH | **89 %** | **Best in the Phase 1 set** — within ±1 pp of 27b at 3× the speed. 2 truncations |
| DROP | **89 %** | −1 pp vs 27b |
| GPQA | **65 % raw** (23/100 truncated; corrected ceiling ~**75–83 %**) | Thinking spirals past the 32,768 cap — see [truncation finding](../testing-plan.md#truncation-finding-gpqa--thinking-models) |
| Knowledge avg (5 benches) | **82.6 %** | Between coder-next (73.8) and 27b (85.8) |
| jdhodges tool-calling (40) | **97.5 %** | Best of the Phase 1 trio (M4 notes round it to 98 %) |
| Veerman tool-calling (12) | **75.0 %** | Worst of the trio — multi-turn / ambiguous-intent cases trip it. **This is the rig's baseline band:** MiniMax-M2.5 GGUF landed at the same 75 % — the agentic tune didn't lift the holdout suite |
| Terminal-Bench 2.0 | **28.1 %** (25/64 PASS, 47 errored, 15.6 h, ⌛0.5x agent-timeout cap) | **#3 on rig** — +3 rank spots vs its LCB rank (6th). F1 thinking-format guard PASSED: thinking works fine with terminus-2 on the LM Studio → LiteLLM chain |

Raw data: `tools/local-llm-bench-m4-32gb/benchmarks/runs/*_qwen3.6-35b-a3b@6bit_20260519_*`, `livecodebench_qwen3.6-35b-a3b@6bit_MERGED_summary.json`, `tbench_*` per [M4 notes § Phase B](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).

## Positioning & verdict

- **The MoE-thinking middle.** Knowledge avg 82.6 % sits between coder-next (73.8) and 27b dense (85.8) at ~4.5× the dense model's speed. Best MATH (89 %) and best jdhodges (97.5 %) on the Phase 1 trio; worst HumanEval and Veerman.
- **Knowledge ceiling is below `qwen3.6-27b`** (−5 MMLU, −5 GPQA raw, −8 LCB) — when you need accuracy on one hard question, wait for the dense model.
- **T-Bench inverts LCB in its favor:** 6th on LCB (54 %) → **3rd on T-Bench (28.1 %)**, behind only coder-next (32.6 %) and 27b (31.5 %). The Qwen agentic-loop training transfers; Gemma's LCB lead does not.
- **Right choice when:** you want thinking-mode reasoning at MoE speed — fast general chat, math-flavored reasoning, single-call tool work. Drop-in replacement for coder-next when you specifically need a thinking model.
- **Post-Phase-2 caveat:** `gemma-4-26b-a4b@6bit` is now a viable peer for the fast-generalist slot (+3 pp HumanEval, +26 pp LCB, ties tool-calling) but trails it on knowledge (78.0 vs 82.6 avg) and loses badly on agentic shell (21.3 vs 28.1 T-Bench). Pick by workload.
- **Serves as the rig's Veerman baseline** (75 % band) for judging new arrivals — MiniMax-M2.5 was scored against it.
- **Remaining work:** `@8bit` quant A/B (Phase 2 #9); optional GPQA truncation rerun at 65k (`--only 2,4,12,...` — ~3–5 h); optional LCB spiral recovery at cap ≥ 96k.

Plans: [2026-05-22-livecodebench-phase-1.md](../../bench/lcb-phase1/plan.md) · [2026-05-24-terminal-bench-phase-a-plus-b.md](../../bench/terminal-bench/plan.md) · [testing-plan.md](../testing-plan.md)

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| GPQA records `FAIL` on hard questions (23/100 truncated) | Thinking spirals past `max_tokens=32768` before the required final answer letter lands | Run GPQA (and any thinking bench) with `--max-tokens 65536`. Raw 65 % under-counts; corrected ceiling ~75–83 % |
| LCB spirals even at 65k (6 questions) | Genuine deep-thinking limits on hard coding problems, not cap artifacts (Q4 rerun confirmed) | Accept 54 % as the defensible floor; a 96k rerun of the remaining spirals is estimated at +4–10 pp upside (untested; [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)) |
| Malformed tool calls on `mlx-community` 4-bit checkpoints (historical concern) | MoE-MLX 4-bit conversion regression | Does **not** reproduce on `@6bit` (T-Bench leg B3 clean). Stay on 6-/8-bit conversions |
| Low-rate MATH/MMLU truncations (2 each) | Same thinking-budget mechanism, lower severity | Format only matters meaningfully for GPQA; ignore elsewhere |

## Loading & memory
- `@6bit` alone: 29.09 GB — tons of headroom. `@8bit` alone: 37.75 GB — tons of headroom.
- **Pairing:** `@6bit` + `gemma-4-26b-a4b@4bit` = 44.7 GB, comfortable. **Do not** pair with `coder-next@6bit` (93.8 GB — over the ~80 GB weights+KV rule); all-three-Qwens is 124.6 GB — never.
- **`@8bit` is not advised for pairing** — at 37.75 GB it eats the pair budget for no measured quality return yet; keep it sole-model for the A/B.
- Context on load: 65,536 for agentic loops (this is also what LCB ran at), 32,768 for short chat. Always set explicitly — unbounded KV growth caused historical stalls.

## Client configuration
- Model ids: `qwen3.6-35b-a3b@6bit` / `qwen3.6-35b-a3b@8bit` (LM Studio `/v1` endpoint, port 1234 — use the strings `GET /v1/models` returns verbatim).
- OpenCode: registered as `qwen3.6-35b-a3b` with `"tools": true` ([reference config](../local-llm-reference.md#client-configurations)).
- Sampling: vendor recommends `temperature=1.0, top_p=0.95, top_k=20, presence_penalty=1.5` for thinking tasks; local benches ran `temp=0, seed=42` for reproducibility.
- Tool calling works natively through LM Studio's parser (jdhodges 97.5 %) and through the Harbor/terminus-2 chain (T-Bench thinking-format guard passed) — no template surgery needed.

## External links
- Vendor: https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- MLX 6-bit conversion: https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-6bit (mlx-vlm 0.4.4)
- MLX 8-bit conversion: https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-8bit (mlx-vlm 0.4.4)

## History
- **2026-05-17 → 05-19** — Phase 1 full suite (`@6bit`): knowledge avg 82.6 %, jdhodges 97.5 %, MATH 89 % best-in-trio; GPQA truncation finding documented ([M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)).
- **2026-05-24** — LCB v6 backfill at 65k cap: **54 %**, 6 real spirals ([plan](../../bench/lcb-phase1/plan.md)).
- **2026-05-26 → 05-29** — Terminal-Bench 2.0 Phase B leg B3: **28.1 %**, #3 on rig; thinking-format guard passed ([plan](../../bench/terminal-bench/plan.md)).
- **2026-07-05** — Confirmed as the Veerman 75 %-band baseline in the MiniMax-M2.5 GGUF evaluation ([minimax-m2.5.md](minimax-m2.5.md)). `@8bit` quant A/B still pending (Phase 2 #9).
- **2026-07-10** — Draft MTP speculative-decoding study on the unsloth GGUF variant: MTP is a per-workload toggle (structured +13–22 %, creative −9 %), draft depth 2 optimal ([bench/qwen3.6-mtp/plan.md](../../bench/qwen3.6-mtp/plan.md)). MLX `@6bit` remains the daily driver.
