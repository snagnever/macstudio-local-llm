# Gemma-4-31B (dense)

> **Status: 🟡 DEMOTED — MLX 8-bit** (dense tax: 6× slower than `gemma-4-26b-a4b@6bit` for no quality return; kept on disk as a reproducibility reference) / **⚪ QAT GGUF PLANNED** (engine A/B head-to-head, [Phase 5 seq 2](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md)).
> The family's MoE sibling `gemma-4-26b-a4b@6bit` matches or beats it on every bench except DROP — see the dense-tax verdict below.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [google/gemma-4-31b-it](https://huggingface.co/google/gemma-4-31b-it) (finetune of `google/gemma-4-31B`) | HF card |
| Parameters | 30.7B **dense** (+ ~550M vision encoder) | HF card |
| Architecture | `gemma4`; 60 layers; interleaved local sliding-window (1024) + full global attention | HF card |
| Native context | 256K (run locally at 65,536) | HF card / local |
| License | Apache 2.0 | HF card |
| Modalities | Text + image + video understanding; text out; tool/function calling; 140+ languages | HF card |
| Reasoning | Configurable thinking mode on the vendor card; **the MLX 8-bit build emitted `think=0` in every Phase 2 response** | HF card + [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md) |
| Vendor sampling | `temperature=1.0, top_p=0.95, top_k=64` | HF card |
| Training data cutoff | January 2025 | HF card |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `gemma-4-31b-it-mlx` | [lmstudio-community/gemma-4-31B-it-MLX-8bit](https://huggingface.co/lmstudio-community/gemma-4-31B-it-MLX-8bit) | MLX safetensors | 8-bit (mlx_vlm conversion) | 33.80 GB | LM Studio MLX | 🟡 **DEMOTED 2026-05-22** | Fully benched Phase 2; dense tax, no quality return vs `@6bit` MoE |
| `google/gemma-4-31b-qat` | [lmstudio-community/gemma-4-31B-it-QAT-GGUF](https://huggingface.co/lmstudio-community/gemma-4-31B-it-QAT-GGUF) | GGUF | **QAT** Q4_0 (quantization-aware trained) | 18.9 GB (LM Studio; HF lists 17.7 GB) | LM Studio llama.cpp 2.23.1 (official catalog model) | ⚪ **PLANNED** | Engine A/B vs the MLX 8-bit numbers ([Phase 5 seq 2](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md)) |

**Pinned HF revisions** (verified 2026-07-06 via HF API: no upstream commits since download → local snapshot = current `main`): MLX 8-bit: [`244e29d`](https://huggingface.co/lmstudio-community/gemma-4-31B-it-MLX-8bit/tree/244e29d3b19e7b50e3ddddc33fcc882f24a19399) (downloaded 2026-05-17) · QAT GGUF: [`5f1655e`](https://huggingface.co/lmstudio-community/gemma-4-31B-it-QAT-GGUF/tree/5f1655eb80159b7db3f6feb9ce1a9440ab076261) (downloaded 2026-07-01).

> Out-of-scope sibling on disk: `gemma-4-31b-jang_4m-crack` (dealignai 8-bit, 22.69 GB) — alignment-stripped community re-quant, not a daily-driver candidate ([reference](../local-llm-reference.md)).

## Architecture & spec notes
- **Dense, not MoE** — every one of the 30.7B parameters is active per token. That is the whole story of this model on this rig: the MoE sibling `gemma-4-26b-a4b` (26B total / 4B active) decodes 6× faster at equal-or-better quality.
- Interleaved sliding-window (1024) + full-attention layers — same KV-cheap pattern as the 26B-A4B, but the dense FFN dominates decode cost anyway.
- Gemma 4 does **not** emit thinking tokens on the MLX build (`think=0` in every Phase 2 response). The QAT GGUF card, by contrast, advertises thinking (`<|channel>thought` markers, `enable_thinking`) — a watch item for the planned A/B (verify the harness scores the final answer, not the thought block).
- **0 truncations across the entire Phase 2 suite** — unlike the 26B-A4B quants (18%/8% LCB truncation), the 31B writes long exhaustive code but always finishes.

## Local performance (measured)

Phase 2 sweep, `--model-label gemma-4-31b-dense-mlx-8bit`, 2026-05-20 → 05-22.

| Scenario | Effective t/s | Gen t/s |
|---|---|---|
| ops-agent | **10.3** | **13.7** |
| creative-writing | 13.6 | 13.9 |
| doc-summary | 8.0 | 14.3 |
| prefill-test | 3.3 | 13.6 |

Context: `gemma-4-26b-a4b@6bit` does 66.6 / 80.8 on ops-agent and `@4bit` does 80.7 / 100.3 — the dense 31B is **6× slower** than the family flagship. Full quality suite took ~5.0 h wall-clock vs ~3.0 h for either 26B quant. Tool-call benches ran at 11.4–12.3 t/s.
Source: [M4_MAX_128GB_NOTES.md § Phase 2](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).

## Quality benchmarks (measured)

Config: ctx 65,536, temp 0, seed 42, sole Gemma resident, n=100 (LCB n=50). Δ column is vs `gemma-4-26b-a4b@6bit`, the family flagship.

| Bench | MLX 8-bit (2026-05-20→22) | Δ vs `@6bit` MoE |
|---|---|---|
| Tool calls jdhodges (40) | **97.5%** @ 11.4 t/s | tie |
| Tool calls Veerman (12) | **83.3%** @ 12.3 t/s | tie |
| HumanEval (100) | 95% | **−2** |
| LiveCodeBench v6 (50) | 76% (0 trunc) | **−2** (vs 80% — the rig LCB ceiling) |
| MMLU | 77% | **−1** |
| MATH | 79% | **−4** |
| DROP | **85%** — its only standout | **+6** (but still trails `qwen3.6-27b`'s 90) |
| GPQA (raw, `--max-tokens 65536`) | 48% | **−5** |
| Knowledge avg (HE+MMLU+MATH+DROP+GPQA) | 76.8% | −1.2 |
| Terminal-Bench 2.0 (2026-05-26→29, ⌛0.5× cap) | **22.5%** (20/69, 49 errored, 17.4 h, 11.7 min/task) | +1.2 (22.5 vs 21.3) — but ~10 pp behind `coder-next`'s 32.6% |

Raw data: `tools/local-llm-bench-m4-32gb/benchmarks/runs/` (Phase 2 + `tbench_*`), `tools/local-llm-bench/results/gemma-4-31b-dense-mlx-8bit/`.

## Verdict — the dense tax (🟡 DEMOTED)

- **2026-05-22 — Phase 2 verdict: demote / skip in normal rotation.** Decode is **6× slower than `@6bit`** (13.7 vs 80.8 gen t/s) and quality is indistinguishable or worse on every bench except DROP (+6 pp): HumanEval −2, LCB −2, MMLU −1, MATH −4, GPQA −5. 33.80 GB on disk vs the flagship's 21.81 GB. It pays the dense tax for no return; DROP 85% is its only headline, and even that trails `qwen3.6-27b` (90%).
- **2026-05-29 — the verdict generalizes to agentic shell.** Terminal-Bench 2.0: 22.5% — ties-or-loses to `26B-A4B@6bit` (21.3%) there too, and sits ~10 pp behind the agentic leader `qwen/qwen3-coder-next` (32.6%). Its LCB #2 rank (76%) drops to T-Bench #4 (−2 spots) — the Gemma one-shot-training pattern.
- **Why it stays on disk:** reproducibility reference only — it is the MLX-8-bit baseline for the planned QAT GGUF engine A/B (below). Not for daily rotation.

Plans: [2026-05-20-gemma-4-phase-2.md](../benchmark-plans/2026-05-20-gemma-4-phase-2.md) · [2026-07-05-phase-5-new-arrivals.md](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md)

## Planned — QAT GGUF engine A/B (⚪ Phase 5 seq 2)

The demoted MLX build gets a second life as a **baseline**: `google/gemma-4-31b-qat` (GGUF QAT Q4_0, 18.9 GB) is the same base model, so benching it is a true **cross-engine + cross-quant A/B** — the [testing-plan Step F](../testing-plan.md) engine comparison (LM Studio MLX vs llama.cpp GGUF) that was deferred for lack of a GGUF on disk.

- **Why seq 2 in the Phase 5 run order:** smallest and highest-confidence of the new arrivals (`(value × confidence) / cost` ordering). Official lmstudio.ai catalog model → bundled llama.cpp 2.23.1 loads it, no fork or flags. Gate before it: evict `coder-next`.
- **Hypotheses to settle:**
  1. Does QAT-Q4_0 match MLX-8-bit quality (the near-bf16-at-4-bit QAT claim) at ~56% of the size (18.9 vs 33.8 GB)?
  2. Does the *"llama.cpp short, MLX long"* rule of thumb hold — GGUF faster on short tool-call outputs, MLX faster on long generations?
- **Ladder** (ctx 65,536, `--max-tokens 65536`): throughput sweep (`local-llm-bench/bench.py`, label `gemma-4-31b-qat-gguf-q4_0`) → tool-calling both suites → HumanEval 100 → LCB v6 50 → MMLU 100.
- **Watch item:** the QAT card advertises a thinking channel (`<|channel>thought`, `enable_thinking`) that the MLX build never used — verify the harness scores the final answer, not the thought block.
- **Deliverable:** record under `tools/local-llm-bench-m4-32gb/results/engine_comparison.md`.

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| 6× decode slowdown vs 26B-A4B (13.7 vs 80.8 gen t/s) | Dense 31B — all parameters active per token | **No fix** — architectural. Use `gemma-4-26b-a4b@6bit` instead; that is the demotion. |
| Prefill-heavy effective throughput collapses to 3.3 t/s | Slow decode dominates once prefill is amortized | Same — demoted |
| Long exhaustive code answers (re-derives full helpers) | Gemma 4 family generation style | Cosmetic here: unlike the 26B quants it hit **0 truncations**; keep LCB `--max-tokens 65536` per the Gemma family rule |
| Possible thought-channel leakage on the QAT GGUF | QAT card enables `<|channel>thought` thinking markers | Untested — pre-flagged for the Phase 5 A/B; verify parser before grading |

## Loading & memory
- 33.80 GB alone (MLX 8-bit) — tons of headroom on the 128 GB rig; well under the `weights + KV < 80 GB` rule.
- Two-model pairing verified in the memory table: `gemma-4-31b` + `qwen3.6-27b` = 56.6 GB — comfortable dense+dense pair ([reference](../local-llm-reference.md)).
- Phase 2 operational rule: single Gemma resident at a time, context 65,536 on load.
- The QAT GGUF (18.9 GB) will be the cheapest 31B-class load on the rig when benched.

## Client configuration
- Model id: `gemma-4-31b-it-mlx` (MLX) / `google/gemma-4-31b-qat` (GGUF, publisher prefix required — mismatched id → 404). LM Studio `/v1`, port 1234.
- Sampling: vendor recommends `temperature=1.0, top_p=0.95, top_k=64`; local benches ran temp 0 / seed 42 for reproducibility.
- No `--no-think` flag needed (Gemma 4 family — verified in [testing-plan](../testing-plan.md)).
- Tool calling works natively (jdhodges 97.5%); vision + tools flagged in LM Studio metadata (vision quality not benchmarked).

## External links
- Vendor: https://huggingface.co/google/gemma-4-31b-it (Apache 2.0, 30.7B dense, 256K ctx)
- MLX conversion: https://huggingface.co/lmstudio-community/gemma-4-31B-it-MLX-8bit (mlx_vlm, 33.8 GB)
- QAT GGUF: https://huggingface.co/lmstudio-community/gemma-4-31B-it-QAT-GGUF (Q4_0, 17.7 GB per HF / 18.9 GB per LM Studio; lineage `gemma-4-31B-it` → `gemma-4-31B-it-qat-q4_0-unquantized` → this)

## History
- **2026-05-20 → 05-22** — Phase 2 full suite on MLX 8-bit ([plan](../benchmark-plans/2026-05-20-gemma-4-phase-2.md)): HE 95, LCB 76, MMLU 77, MATH 79, DROP 85, GPQA 48; 13.7 gen t/s. 🟡 **Demoted** — dense tax, no quality return vs `@6bit`.
- **2026-05-26 → 05-29** — Terminal-Bench 2.0 Phase B: 22.5% (#4 of 7) — the demotion verdict generalizes to agentic shell.
- **2026-07-05** — QAT GGUF (`google/gemma-4-31b-qat`, 18.9 GB) queued as seq 2 in the [Phase 5 plan](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md): the deferred Step F engine A/B, with the demoted MLX build as baseline. Not yet run.
