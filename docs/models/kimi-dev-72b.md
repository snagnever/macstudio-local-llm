# Kimi-Dev-72B

> **Status: 🔴 NO-GO on speed** (2026-07-05).
> ~7 t/s — the slowest model benched on this rig; disqualified at the speed gate of the cheap-signal ladder before any graded coding runs.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [moonshotai/Kimi-Dev-72B](https://huggingface.co/moonshotai/Kimi-Dev-72B), built on Qwen/Qwen2.5-72B | HF card |
| Parameters | 73B dense (GGUF arch `qwen2`) | HF card + local inspection |
| Architecture | Qwen2.5-72B fine-tune; large-scale RL for software-engineering / repo-patching | HF card |
| Native context | 32,768 (Qwen2.5-72B native; 128k only via YaRN) — run locally at 32,768 | base-model spec / local |
| License | MIT | HF card |
| Modalities | text only | HF card |
| Reasoning | mandatory `◁think▷` reasoning blocks — **non-standard markers** (not `<think>`); see Known issues | local |
| Tool calling | not mentioned on card; **no structured calls observed locally** | HF card + local |
| Release | June 2025 | HF card |
| Vendor claims | SWE-bench Verified 60.4% — SOTA among open-source models at release *(vendor — not reproduced locally)* | HF card |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `kimi-dev-72b` *(no publisher prefix in `/v1/models`)* | [unsloth/Kimi-Dev-72B-GGUF](https://huggingface.co/unsloth/Kimi-Dev-72B-GGUF) | GGUF | UD-Q6_K_XL | 62.55 GiB weights (67.16 GB resident @ ctx 32768 / parallel 1) | LM Studio llama.cpp 2.23.1 (stock — no fork/flags) | 🔴 **NO-GO 2026-07-05** | Loads clean in 36 s; aborted at the speed step (~7 t/s) |

## Architecture & spec notes
- GGUF arch is plain `qwen2` — stock llama.cpp 2.23.1 loads it with zero special handling (no fork, no flags). The **red arch badge LM Studio renders is benign** (a `Show warnings` flag, not a loadability problem).
- Dense 73B at Q6 is the speed story: decode is compute-bound on this rig (see Local performance) — the phenotype the phase-5 plan predicted (~10–14 t/s expected; reality was worse).
- RL fine-tune targets repo-patching (SWE-bench), **not** tool calling — it is not a tool-calling fine-tune, and it behaves like one (floor, like `deepseek-v4-flash-dq`).

## Local performance (measured)

| Metric | GGUF UD-Q6_K_XL |
|---|---|
| Sustained generation | **~7 t/s** — 3 probe runs: 7.0 / 7.0 / 7.1 t/s (trivial), 6.9 / 7.2 / 7.2 t/s (mmlu); code prompt timed out at the 120 s probe cap mid-`◁think▷` |
| Bottleneck | **Compute-bound**: GPU 100%, 54 W. Memory state did *not* move the number — identical t/s at 87 GB no-swap vs 135 GB / 19 GB swap (`Spill=YES`, coder-next co-resident) |
| Memory | 62.55 GiB weights, 67.16 GB resident @ ctx 32768 / parallel 1 |
| Load | clean, 36 s; pre-flight PASS (warmup answers "4") |
| Reasoning tax | mandatory `◁think▷` spiral on everything — even "2+2" spirals (180 tok, cut mid-think at the probe cap); markers unparsed by LM Studio, so raw reasoning lands in `content` |
| Tool calling | ✗ — given a tool + explicit instruction, emitted prose *about* calling it inside `◁think▷`; `tool_calls: []` |

Context: ~⅓ of `qwen3.6-27b`'s 20 t/s, ~½ of `gemma-4-31b` dense's 13.7 t/s — **the slowest model benched on this rig** — and the unparsed thinking spiral makes *effective* throughput worse still. (The M4-notes entry states this comparison with the fractions swapped; corrected here.)
Source: [M4_MAX_128GB_NOTES.md § kimi-dev-72b](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).

## Quality benchmarks (measured)

**None — deferred by design.** The cheap-signal ladder was aborted at the speed step; HumanEval / LiveCodeBench / MMLU were never run. Coding quality (LCB + HumanEval) is the model's only differentiating axis given the SWE-bench pedigree, but a full run would cost **~1–2 rig-days at 7 t/s for a model already ruled out** — not worth the compute. `qwen3.6-27b` (LCB 62%) remains the coding-quality reference and `gemma-4-26b-a4b@6bit` (LCB 80%) the coding leader.

## Feasibility & verdict

- **2026-07-05 — GGUF UD-Q6_K_XL: ⛔ NO-GO on speed.** Ran first in the phase-5 sequence (user's choice). Full ladder timeline:
  | Time | Step | Result |
  |---|---|---|
  | 10:40 | Speed probe #1 (87 GB, no swap) | ~7.0 t/s trivial, 6.9 t/s mmlu; code prompt hit the 120 s cap mid-`◁think▷` |
  | ~10:45 | Manual tool-call probe | `tool_calls: []` — prose about calling the tool inside `◁think▷`, no structured call |
  | 10:53 | Speed probe #2 | ~7.0 / 7.2 t/s despite coder-next JIT-reload → 135 GB / 19 GB swap |
  | ~10:58 | Unloaded coder-next | back to sole-model, 44 GB free |
  | 11:02 | Speed probe #3 (88.7 GB, no swap) | ~7.1 / 7.2 t/s — identical to #1; confirms compute-bound |
- Disqualified as a daily-driver / agentic model **regardless of coding quality**: too slow, no structured tool calling, and a mandatory unparsed thinking spiral on top.
- **Revisit only if a faster path appears:** a lighter quant that keeps the SWE quality, a speculative-decoding draft model (LM Studio supports `--speculative-draft-*`), or a smaller Kimi-Dev distillation.

Plans: [2026-07-05-phase-5-new-arrivals.md](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md) (§ seq 3) · verdict recorded in [testing-plan.md](../testing-plan.md) (#14).

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| ~7 t/s decode | 73B dense at Q6 is compute-bound on this GPU (100% util, 54 W); not memory/swap-related | **No fix at this quant.** Lighter quant, speculative decoding, or a distillation — see revisit triggers |
| Raw `◁think▷` reasoning pollutes `content` | Non-standard thinking markers (not `<think>`) → LM Studio doesn't parse them (`reasoning_tokens: 0`) | No app-side fix; contrast MiniMax-M2.5, whose reasoning parses cleanly |
| Spirals on trivial prompts | Mandatory reasoning fine-tune — even "2+2" emits a 180-token think block | Budget token caps accordingly; inflates effective latency well beyond raw t/s |
| No structured tool calls | Not a tool-calling fine-tune (SWE/repo-patching RL) | Floor, like `deepseek-v4-flash-dq` — do not use in agentic loops |
| Red arch badge in LM Studio | Cosmetic `Show warnings` flag on the `qwen2` GGUF | Benign — loads and serves fine on stock 2.23.1 |

## Loading & memory
- 67.16 GB resident @ ctx 32,768 / parallel 1 — under the ~80 GB pairing rule but was benched sole-model (evicted the two idle residents first).
- Loads LM Studio-native (stock llama.cpp 2.23.1), clean in 36 s.
- **Cap context/max-tokens at 32,768** — Qwen2.5-72B is 32k native (128k only via YaRN); overshooting could hurt or error.
- Beware LM Studio JIT-reloads of evicted models (6 h TTL) pushing the rig into swap mid-run — though here swap didn't change the t/s.

## Client configuration
- Model id: `kimi-dev-72b` (LM Studio `/v1` endpoint, port 1234) — **no publisher prefix**, unlike `unsloth/minimax-m2.5` etc.; verify with `GET /v1/models`.
- Local probes ran temp 0 / seed 42 house defaults; no vendor sampling recommendation found on the card (fetched 2026-07-05).
- Expect `◁think▷`-wrapped reasoning in `content` — strip it client-side if you must use this model.

## External links
- Vendor: https://huggingface.co/moonshotai/Kimi-Dev-72B (MIT, June 2025)
- GGUF conversion: https://huggingface.co/unsloth/Kimi-Dev-72B-GGUF (UD-Q6_K_XL 67.2 GB; range UD-IQ1_S 23 GB → Q8_0 77.3 GB / UD-Q8_K_XL 84 GB; BF16 145 GB)

## History
- **2026-07-05** — Phase-5 seq 3, ran first. Load clean 36 s, pre-flight PASS; 3× speed probes ≈ 7 t/s (compute-bound, memory-invariant); tool-call probe `tool_calls: []`. ⛔ **NO-GO on speed**; coding-quality tail deferred. Verdicts in [testing-plan.md](../testing-plan.md) (#14), [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md), and the [phase-5 plan](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md).
