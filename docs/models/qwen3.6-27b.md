# Qwen3.6-27B (dense)

> **Status: 🟢 DAILY DRIVER** — Planning role winner.
> Knowledge king: **85.8 % knowledge avg, top of rig**. Slow (~20 t/s gen, 67 s prefill @ 8.5k) — but you wait once for a plan.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [Qwen/Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) | HF card (fetched 2026-07-05) |
| Parameters | 27B dense, 64 layers | HF card |
| Architecture | Hybrid: `16 × (3 × (Gated DeltaNet → FFN) → 1 × (Gated Attention → FFN))`; attention 24 Q / 4 KV heads @ dim 256; DeltaNet 48 V / 16 QK linear heads @ dim 128. Local MLX arch id: `qwen3_5` | HF card + [testing-plan.md](../testing-plan.md) |
| Native context | 262,144 tokens (up to 1,010,000 with RoPE scaling / YaRN); run locally at 65,536 (agentic) | HF card / local |
| License | Apache 2.0 | HF card |
| Release | April 2026 (citation metadata) | HF card |
| Modalities | image + text + video input, text output (vision advertised; unbenchmarked locally — too slow to be the vision default) | HF card + [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md) |
| Reasoning | **Thinking mode by default** — emits `<think>\n...\n</think>` before the final response; disableable via config | HF card |
| Tool calling | ✓ (vLLM: `--enable-auto-tool-choice --tool-call-parser qwen3_coder`) | HF card |
| Vendor sampling | thinking: `temperature=1.0, top_p=0.95, top_k=20`; precise coding: `temperature=0.6, top_p=0.95, top_k=20`; non-thinking: `temperature=0.7, top_p=0.80, top_k=20` | HF card |
| Vendor claims | SWE-bench Verified 77.2, AIME 2026 94.1, GPQA Diamond 87.8 *(vendor — not reproduced locally)*; T-Bench 2.0 59.3 ("Opus 4.5 parity") *(vendor — local result 31.5 %, see Quality benchmarks)* | HF card + [local-llm-reference.md](../local-llm-reference.md) |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `qwen3.6-27b` | [mlx-community/Qwen3.6-27B-6bit](https://huggingface.co/mlx-community/Qwen3.6-27B-6bit) | MLX safetensors | 6-bit | 22.80 GB | LM Studio MLX | 🟢 **DAILY DRIVER** | Planning / hard-reasoning slot; sole benched variant |

**Pinned HF revisions** (verified 2026-07-06 via HF API: no upstream commits since download → local snapshot = current `main`): 6-bit: [`9bf9761`](https://huggingface.co/mlx-community/Qwen3.6-27B-6bit/tree/9bf976157e09080fbc11ccd971d4e9c57554889d) (downloaded 2026-05-16).

> Out-of-scope community re-quants on disk (alignment-stripped — not daily-driver candidates): `qwen3.6-27b-paro` (z-lab, 18.80 GB), `qwen3.6-27b-ud-mlx` (unsloth 4-bit, 26.21 GB), `qwen3.6-27b-jang_4m-crack` (dealignai 4-bit, 17.55 GB). See [local-llm-reference.md](../local-llm-reference.md).

## Architecture & spec notes
- **Dense — all 27B parameters active every token.** That's the whole trade: highest raw reasoning quality on the rig, paid for in ~20 t/s decode and a 67 s prefill at 8.5k context ("the dense tax"). KV is also expensive relative to the rig's hybrid/sliding-window MoEs (`coder-next`, `gemma-4-26b-a4b`) — see the [two-resident context math](../local-llm-reference.md#two-resident-pair-context-math).
- **Thinking model.** `<think>` reasoning by default; this drives both its quality lead *and* its two operational failure modes: thinking spirals at token caps (GPQA @ 32k) and multi-hour bench wall-clocks (~55 min per 65k spiral at ~20 t/s).
- MLX conversion by mlx-community via **mlx-vlm 0.4.4** (vision-capable conversion path), 6-bit from BF16.
- 6-bit preserves syntax precision — no quant-related code-format issues observed across HumanEval/LCB/T-Bench.

## Local performance (measured)

| Metric | MLX 6-bit |
|---|---|
| Sustained generation | **~20 t/s** (20.0–20.7 gen across scenarios) |
| Effective throughput (ops-agent) | **16.2 t/s** |
| Prefill at 8.5k ctx | **67 s** — effective collapses to **1.9 t/s**; prefill is the killer |
| Tool-call runs | 14.5 t/s (jdhodges) / 18.4 t/s (veerman) |
| Bench wall-clock cost | Full Phase 1 suite 37.6 h; LCB v6 alone 16.2 h (~20 min/question avg); T-Bench 18.9 h |
| Memory | 22.80 GB alone — tons of headroom on the 128 GB rig |

Context: 6× slower decode than `coder-next` (67 t/s effective) and 4× slower than `gemma-4-26b-a4b@6bit` (80.8 t/s). The prefill collapse is why it loses the agent slot despite near-parity T-Bench quality.
Source: [local-llm-reference.md throughput matrix](../local-llm-reference.md), [testing-plan.md](../testing-plan.md), [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).

## Quality benchmarks (measured)

Config: n=100 (LCB n=50), temp 0, seed 42, ctx 65,536; GPQA ran at the 32,768 cap.

| Bench | MLX 6-bit | Notes |
|---|---|---|
| Knowledge avg (5 benches) | **85.8 %** | **Top of rig** — best on 5 of 6 Phase 1 benches; Phase 2 confirmed no Gemma comes within 7.8 pp |
| HumanEval (100) | **93 %** | Best of Phase 1 trio (HE saturated — LCB is the canonical coding signal) |
| LiveCodeBench v6 (50) | **62 %** | Best Qwen on the rig; 1 truncation (Q3, spirals on every model). +6 pp over coder-next; rig ceiling is `gemma-4-26b-a4b@6bit` at 80 % |
| MMLU | **88 %** | +10 pp over best Gemma |
| MATH | **88 %** | ±1 pp of the rig best |
| DROP | **90 %** | Rig best |
| GPQA | **70 % raw** † | 15/100 truncated at the 32k cap (thinking spirals); corrected ceiling **~78–85 %** |
| jdhodges tool-calling (40) | **95 %** (38/40) | Ties 35b-a3b on combined tool-calling 92.3 % |
| Veerman tool-calling (12) | **83.3 %** | Ties coder-next |
| Terminal-Bench 2.0 (leg B5) | **31.5 %** ⌛0.5x cap | 28/61 PASS, 18.9 h. **#2 on rig**, 1.1 pp behind coder-next but 6× slower decode. Far below vendor 59.3 — frontier vendors run more elaborate agent harnesses than terminus-2 |

† GPQA raw score under-counts true ability — truncated questions grade FAIL. See the [truncation finding](../testing-plan.md#truncation-finding-gpqa--thinking-models).

Raw data: `tools/local-llm-bench-m4-32gb/benchmarks/runs/*_qwen3.6-27b_20260517_*` / `_20260518_*`, `livecodebench_qwen3.6-27b_MERGED_summary.json`; full tables in [M4_MAX_128GB_NOTES.md](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).

## Feasibility & verdict

- **Role: Planning** — design, hard reasoning, code review, careful single-file edits, knowledge-heavy Q&A. The rationale: slow, but *you wait once for a plan*, unlike an agent loop where the 67 s prefill compounds every turn.
- **Phase 1 (2026-05-17→19): quality king by a wide margin.** Best or tied on every accuracy bench; knowledge avg 85.8 %.
- **LCB backfill (2026-05-24):** only Phase 1 model to clear 60 % on LCB v6 — displaced the "coder-next is good enough" assumption when correctness > speed.
- **Phase 2 (Gemma family):** **retained the knowledge generalist slot** — no Gemma beats it on knowledge (best Gemma trails by MMLU −10, MATH −5, DROP −11, GPQA −17 pp raw). But the **LCB-specific recommendation diverged**: `gemma-4-26b-a4b@6bit` is the single-shot code ceiling at 80 % (+18 pp).
- **T-Bench backfill (2026-05-29):** lands #2 (31.5 %), gaining 2 rank spots vs its LCB rank — Qwen's agentic training transfers — but coder-next wins the agent slot speed-adjusted.

Plans: [2026-05-22-livecodebench-phase-1.md](../../bench/lcb-phase1/plan.md) · [2026-05-24-terminal-bench-phase-a-plus-b.md](../../bench/terminal-bench/plan.md) · [testing-plan.md](../testing-plan.md)

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| GPQA thinking spirals truncate at 32,768 cap (15/100 graded FAIL) | Single-letter answer format forces the full reasoning chain before the answer token | Run GPQA (and any thinking bench) with `--max-tokens 65536`; rerun of the 15 questions queued (~7–10 h). Raw 70 % is a floor; ceiling ~78–85 % |
| Bench requests wedge / cascade-timeout on spirals | `bench2.py` hardcoded 1800 s urlopen timeout too short — a 65k spiral takes ~55 min at ~20 t/s | Set `BENCH_TIMEOUT=3600` for any ≤ 25 t/s thinking model at the raised cap (fix landed in `bench2.py`) |
| Long `bench2.py` runs silently die at ~2–3 h under `Bash run_in_background` | Harness limitation, reproduced 3× | Detached driver pattern (`nohup` → PPID=1), e.g. `bench/lcb-phase1/scripts/run-27b-lcb-remaining.sh` |
| Agentic loops feel glacial despite decent T-Bench score | 67 s prefill @ 8.5k → 1.9 t/s effective, re-paid every turn | Not a bug — role mismatch. Use `coder-next` for loops; keep 27b for one-shot planning |

## Loading & memory
- 22.80 GB alone — tons of headroom; loads via LM Studio JIT in ~8–10 s.
- **Verified pairs** (under the ~80 GB weights+KV rule): `gemma-4-26b-a4b@4bit` + 27b = **38.4 GB** (comfortable); `gemma-4-31b` + 27b = **56.6 GB** (OK); **code-heavy resident pair** `gemma-4-26b-a4b@6bit` + 27b ≈ **44.6 GB** (two always-hot Phase-2 winners — pure code + planning day).
- Two-resident with the coder: `coder-next@4bit` (~44 GB) + 27b = ~67 GB OK; **`coder-next@6bit` + 27b = 87.6 GB ❌ — has caused queue stalls historically.**
- Dense KV is expensive — cap context at load; don't max out 262k.

## Client configuration
- Model id: `qwen3.6-27b` (verbatim from LM Studio `GET /v1/models`; the `mlx-community/...` path 404s). Port 1234, `/v1` OpenAI-compatible.
- Context at load: **65,536** for agentic use, **131,072** for long-doc Q&A, 32,768 for short chat (per [local-llm-reference.md](../local-llm-reference.md)).
- OpenCode: registered in `~/.config/opencode/opencode.json` as `lmstudio/qwen3.6-27b` ("Qwen 3.6 27B (dense, reasoning)", `tools: true`).
- Sampling: vendor recommends `temp=1.0/top_p=0.95/top_k=20` (thinking) or `temp=0.6` for precise coding; local benches ran temp 0 / seed 42 for reproducibility.
- Tool calling works natively through LM Studio's parser (jdhodges 95 %) — no template surgery needed.

## External links
- Vendor: https://huggingface.co/Qwen/Qwen3.6-27B (Apache 2.0; hybrid Gated DeltaNet + Gated Attention)
- MLX conversion: https://huggingface.co/mlx-community/Qwen3.6-27B-6bit (mlx-vlm 0.4.4, 6-bit, 22.8 GB)

## History
- **2026-05-17 → 05-19** — Phase 1 (Qwen daily-driver trio): quality king, knowledge avg 85.8 %; full suite 37.6 h ([M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)).
- **2026-05-22** — Phase 2 concludes: no Gemma displaces it on knowledge; retains the knowledge-generalist slot.
- **2026-05-24** — LCB v6 backfill: **62 %**, best Qwen, 16.2 h ([plan](../../bench/lcb-phase1/plan.md)); LCB-specific recommendation diverges to `gemma-4-26b-a4b@6bit` (80 %).
- **2026-05-29** — Terminal-Bench 2.0 leg B5: **31.5 %** ⌛0.5x cap, #2 on rig ([plan](../../bench/terminal-bench/plan.md)); agent slot stays with coder-next on speed.
- **2026-07-05** — Model card written; still the Planning daily driver post-Phase-5 arrivals (MiniMax-M2.5 GGUF is sole-model only and doesn't contest the slot).
