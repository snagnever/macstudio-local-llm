# Mellum2-12B-A2.5B-Thinking

> **Status: ⚪ PLANNED** — Phase 5 seq 5; load-probe first (the `mellum` arch is likely NOT supported by LM Studio's bundled mlx-llm 1.9.1 and may need the maintainer's mlx-lm fork).
> Small thinking coder targeting the FIM / quick-call slot currently held by `gemma-4-e4b`.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | JetBrains/Mellum2-12B-A2.5B-Thinking (via the MLX conversion card) | [HF card](https://huggingface.co/jedisct1/Mellum2-12B-A2.5B-Thinking-mlx) |
| Parameters | 12B total / ~2.5B active MoE — 64 experts, 8 active per token | HF card |
| Architecture | `mellum`; sliding-window + full-attention layer mix; targets code + FIM | HF card + [phase-5 plan](../../bench/phase-5-new-arrivals/plan.md) |
| Native context | 131,072 | HF card |
| Precision | native bf16 ("weights are kept in their native `bfloat16` precision") | HF card |
| License | Apache 2.0 | HF card |
| Reasoning | thinking model — emits `<think>…</think>` blocks before answers | HF card |
| Vendor sampling | `temperature=0.6, top_p=0.95, top_k=20` | HF card |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `mellum2-12b-a2.5b-thinking-mlx` | [jedisct1/Mellum2-12B-A2.5B-Thinking-mlx](https://huggingface.co/jedisct1/Mellum2-12B-A2.5B-Thinking-mlx) | MLX | bf16 | 24.3 GB | LM Studio MLX (🔴 verify) / mlx-lm fork | ⚪ PLANNED | Card: "the mellum architecture is not supported by the stock mlx-lm code yet" |

**Pinned HF revisions** (verified 2026-07-06 via HF API: no upstream commits since download → local snapshot = current `main`): bf16: [`463ddb6`](https://huggingface.co/jedisct1/Mellum2-12B-A2.5B-Thinking-mlx/tree/463ddb634c4d805c87ff71f7ded88ef3e4d55d21) (downloaded 2026-06-02).

## Architecture & spec notes
- MoE with only 2.5B active — cheap and fast to bench if it loads.
- Downloaded conversion is un-quantized bf16 (24.3 GB) — unusual for this rig's lineup (everything else is 3–8-bit).

## Local performance (measured)
Not measured — load-probe not yet run.

## Quality benchmarks (measured)
Not measured. Planned ladder if it loads: speed probe → tool-calling → HumanEval → LCB ([phase-5 plan §5](../../bench/phase-5-new-arrivals/plan.md)).

## Feasibility & verdict
- **Gate (planned):** load-probe first —
  ```bash
  lms load mellum2-12b-a2.5b-thinking-mlx --context-length 32768 2>&1 | tee /tmp/mellum-load.log
  ```
  - **If it loads:** run the small-model ladder — it's cheap (24 GB) and fast (2.5B active).
  - **If it errors on arch:** park it. Re-test path = standalone `mlx_lm.server` built from the maintainer's fork pointed at `~/.lmstudio/models/jedisct1/Mellum2-12B-A2.5B-Thinking-mlx`; track as a separate build task, do **not** block the rest of Phase 5 on it.
- **Hypothesis:** a 2.5B-active thinking coder is a **FIM / quick-call** candidate, not a daily driver. Bench against `gemma-4-e4b` (current small-slot holder: HumanEval 91%, jdhodges 87.5%). Watch for two risks: the `<think>` reasoning tax, and the small-model MATH collapse that sank E4B (14%).

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| Probable arch-load failure on bundled mlx-llm 1.9.1 | `mellum` arch not in stock mlx-lm (per conversion card) | Standalone server from the maintainer's mlx-lm fork (untested) |

## Loading & memory
24.3 GB bf16 — comfortable-fit class; would pair with anything under the ~80 GB rule. Context 131,072 native; plan probes at 32,768.

## Client configuration
Not yet configured — pending the load-probe. Vendor sampling `temp 0.6 / top_p 0.95 / top_k 20`; reasoning arrives in `<think>` blocks (verify LM Studio parses them as `reasoning_tokens`).

## External links
- MLX conversion: https://huggingface.co/jedisct1/Mellum2-12B-A2.5B-Thinking-mlx
- Vendor base: https://huggingface.co/JetBrains/Mellum2-12B-A2.5B-Thinking

## History
- **2026-06-02 → 07-04** — downloaded in the Phase 5 new-arrivals wave (24.3 GB bf16).
- **2026-07-05** — queued as Phase 5 seq 5 with a load-probe gate ([plan](../../bench/phase-5-new-arrivals/plan.md), [testing-plan #16](../testing-plan.md)).
