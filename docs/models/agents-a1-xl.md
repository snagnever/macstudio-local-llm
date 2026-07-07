# Agents-A1-XL

> **Status: 🟡 GO (marginal)** — well-rounded mid-tier all-rounder (top-tier tool-calling + HumanEval), but the thinking tax makes it slower than `coder-next` for real agentic loops; expensive tail **DEFERRED**.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [InternScience/Agents-A1](https://huggingface.co/InternScience/Agents-A1) — agentic fine-tune of a Qwen3.5-family MoE (card doesn't name the exact Qwen variant; local arch is `qwen3_5_moe` and it self-IDs as "Qwen3.5 / Alibaba Tongyi") | HF card (fetched 2026-07-05) + local |
| Parameters | 35B total MoE, ~3B active per token (256 experts, 8 active + 1 shared) | HF card |
| Architecture | `qwen3_5_moe` (reported by `bench2.py` at load); hybrid full + linear (Gated DeltaNet) attention per card | local inspection + HF card |
| Native context | 262K per card; run locally at 131,712 | HF card / local |
| License | Apache 2.0 | HF card |
| Modalities | card mentions a vision encoder; benched text-only locally | HF card / local |
| Reasoning | **heavy thinker** — emits reasoning tokens on everything (see thinking tax below); "Agentic Reasoning", Qwen3-variant reasoning parser | HF card + local |
| Tool calling | ✓ native function calling (`qwen3_coder` parser on the MLX conversion) | HF card |
| Vendor sampling | `temperature=0.85, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=1.1` | HF card |
| Vendor claims | Three-stage training (full-domain SFT → domain teachers → multi-teacher on-policy distillation); SOTA claims incl. Seal-0 56.4, HiPhO 46.4, FrontierScience-Olympiad 79.0 *(vendor — not reproduced locally)* | HF card |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `agents-a1-xl-mlx` | [leonsarmiento/Agents-A1-6bit-XL-mlx](https://huggingface.co/leonsarmiento/Agents-A1-6bit-XL-mlx) | MLX | 6-bit ("BaseQuant_XL" 6/8-bit mixed, 6.808 bpw avg; routing-critical layers kept bf16) | 27.8 GB (29.90 GB resident) | LM Studio MLX (mlx-llm 1.9.1) | 🟡 **GO (marginal) 2026-07-05** | Cheap tail complete, zero crashes; expensive tail + T-Bench deferred |

**Pinned HF revisions** (verified 2026-07-06 via HF API: no upstream commits since download → local snapshot = current `main`): 6-bit XL: [`f0decd3`](https://huggingface.co/leonsarmiento/Agents-A1-6bit-XL-mlx/tree/f0decd3fa41a35f532f2628bc6af661f04e218a6) (downloaded 2026-07-03).

## Architecture & spec notes
- Qwen3.5 MoE family (`qwen3_5_moe`) — same arch as the already-benched `qwen3.6-35b-a3b`; loaded on stock LM Studio MLX with no special handling.
- 256 experts / 8 active + 1 shared expert; hybrid full + linear (Gated DeltaNet) attention per the HF card.
- Self-IDs as "Qwen3.5, developed by Alibaba Cloud's Tongyi Lab" — the agentic fine-tune keeps the base identity.
- **Comfortable-fit class** (~48 GB resident with KV at ctx 131712) — *not* the sole-model / memory-ceiling class that blocked DeepSeek-V4 and crash-looped MiniMax-M2.5. No memory or GPU-panic risk expected, and none observed.

## Local performance (measured)

| Metric | agents-a1-xl-mlx (MLX 6-bit) |
|---|---|
| Decode, thinking outputs | **~40 t/s** (mmlu 390 tok / 9.7 s; code 1023 tok / 24.9 s) |
| Decode, short completions | ~65–80 t/s (tool-call runs 67–75 t/s weighted) |
| Raw gen (ops-agent scenario) | 82.1 t/s — between gemma@6bit 80.8 and 35b-a3b 85.5 |
| **Effective throughput** | **35.9 t/s** — ~half the non-thinking peers (coder-next 55.8 / 35b-a3b 71.4 / gemma@4bit 80.7) |
| Memory | 48 GB resident with KV, swap 0.2 GB `Spill=no`, GPU 100% @ 76 W; zero crashes across the entire tail |

**Thinking tax (the headline caveat):** emits reasoning tokens on *everything* — 109 on "2+2", 18k on a "leetcode/easy", 2× 65k-cap spirals on *both* MMLU and LCB. MMLU 100q took 104 min, LCB 50q took 4 h. This is the Qwen 3.6-dense phenotype; a full MATH/DROP/GPQA sweep would be 20–40 h.
Source: [M4_MAX_128GB_NOTES.md § agents-a1-xl-mlx](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md), drivers `.bench-logs/run-agents-a1-xl-{cheaptail,throughput}.sh`.

## Quality benchmarks (measured)

Config: ctx 131712, temp 0, seed 42, `--max-tokens 65536`, single-model residency.

| Bench | Score (2026-07-04 → 07-05) | Notes |
|---|---|---|
| jdhodges tool-calling (40) | **92.5%** (37/40) | sel 7/8 · args 8/8 · multi 6/8 · edge 8/8 · format 8/8; 7.4 min. Mid-top: > coder-next 90, < the 97.5 cluster / 27b 95 |
| Veerman tool-calling (12) | **83.3%** (10/12) | action 6/7 · **restraint 2/2** · hard 2/3 — **ties the leaders** (coder-next / 27b / gemma). Calibrated, not trigger-happy; all misses `no_tool_called`/`tool_mismatch` on genuinely ambiguous prompts |
| HumanEval (100) | **97%** | 1 trunc (Q85 spiraled to 10.6k think tok → wrong); 75 min. Top band — ties gemma@6bit 97, > 27b 93 / coder-next 89 |
| MMLU (100) | **82%** | 3 trunc, 2× 65k-cap spirals (~17 min each); 104.6 min. 2nd tier: < 27b 88, ≈ 35b-a3b 83, > gemma ~78 / coder-next 76 |
| LiveCodeBench v6 (50) | **64%** (32/50) | 2 trunc, 2× 65k-cap spirals (~29 min each); **240.6 min (4 h)**. Mid-pack: > 27b 62 / coder-next 56 / 35b-a3b 54, < gemma@6bit 80 / gemma-31b 76. Solved `abc365_c` (27b's lone unsolved); failed the universal-hard `abc354_d` |
| Terminal-Bench 2.0 | ⏹ **ABORTED** (2/89) | User-stopped 2026-07-05; task 2 errored on `EnvironmentStartTimeoutError` (Docker env, not the model). No usable score; driver + job dir retained for a clean resume |

### Effective-throughput scenarios — thinking tax breaks 3 of 4

| Scenario | Budget | Result |
|---|---|---|
| ops-agent | 500 tok | ✅ gen 82.1 t/s / **effective 35.9 t/s** (8 turns, coherent) |
| doc-summary | 150 tok | ❌ reasoning alone > 150 → zero visible output |
| prefill-test | 150 tok | ❌ same — no visible output in budget |
| creative-writing | 2000 tok | ❌ spiraled past 2000 in pure reasoning on a turn |

On short-output workloads (150-tok budgets) it produces **no usable output at all** — a genuine unsuitability for latency-sensitive short responses, not just slowness.

Raw data: `tools/local-llm-bench-m4-32gb/benchmarks/runs/`, `results/speed_probe/`; full write-up in the [plan doc](../benchmark-plans/2026-07-04-agents-a1-xl.md).

## Feasibility & verdict

- **2026-07-04 → 07-05 — cheap tail ✅ COMPLETE, 🟡 GO (marginal).** Strong, well-rounded Qwen3.5 MoE — top-tier tool-calling + HumanEval, near-top MMLU, solid mid-pack LCB — with zero crashes. But a heavy thinker that pays a real wall-clock tax.
- **Gate decision:** pre-registered gate was **LCB ≥ ~62% (beat 27b) OR MMLU ≥ ~85% (near 27b)**. It marginally clears on coding only (LCB 64% vs 27b 62%, +2 pp; MMLU 82% misses 85%). A thin pass — the coding edge is 2 pp while 27b leads knowledge by 6 pp — so the **expensive MATH/DROP/GPQA tail is DEFERRED** (20–40 h of thinking spirals for an already-well-characterized marginal model).
- **Slot:** does **not** displace `coder-next` (agentic speed — effective 35.9 vs 55.8 t/s), `27b` (knowledge), or `gemma@6bit` (coding). Best fit: **tool-calling generalist** when calibrated restraint matters more than latency.
- **Remaining work (optional, ranked):** (1) Terminal-Bench 2.0 resume — the on-brand end-to-end agentic-shell signal, ~18–30 h, re-launch `.bench-logs/run-tbench-agents-a1-xl.sh` when the rig has a free day; (2) no-think throughput A/B (invasive template surgery, low value); (3) proactivity-nudge tool-calling A/B (curiosity).

Plans: [2026-07-04-agents-a1-xl.md](../benchmark-plans/2026-07-04-agents-a1-xl.md) · [2026-07-05-phase-5-new-arrivals.md](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md)

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| Short-budget workloads produce zero output; wall-clock 2–13× a non-thinking peer | Mandatory heavy reasoning (109 tok on "2+2" → 65k-cap spirals) | No off switch found: inline `/no_think` is **ignored**; bench.py's template-patch `--no-think` can't resolve it (on-disk dir ≠ API id). Manual `chat_template.jinja` surgery would be needed — deferred. Budget ≥500 output tok per turn |
| `bench.py check_context_size` false-failed the model | `max_tokens=5` pre-flight probe fully consumed by reasoning → `output_tokens==0` → bogus "context too small" exit | **Fixed** in harness (bench.py:408): probe returning only reasoning without a context-length error = pass |
| Reasoning silently undetected in throughput runs | `bench.py` needs `--base-url http://host:1234` (no `/v1`); a trailing `/v1` doubles to an endpoint that drops `reasoning_content` | **Fixed** in driver — bare host in `run-agents-a1-xl-throughput.sh` |
| T-Bench task errored at start | `EnvironmentStartTimeoutError` — Docker env issue, not the model | Resume from retained job dir `.bench-logs/tbench-runs/agents-a1-xl/` |

## Loading & memory
- Comfortable-fit: 29.90 GB resident weights, ~48 GB with KV at ctx 131712 / parallel 4 — pairs fine under the ~80 GB rule, but bench single-model for clean numbers.
- **Operational note:** it arrived co-resident with `hermes-4-70b` + `qwen3.6-27b` (~110 GB weights, swap maxed 19.9/20.5 GB, `Spill=YES`); unloading the other two dropped swap to 166 MB. All recorded numbers are single-model / clean-state.
- Cold start after a residency change: ~120 s warmup + ~11 t/s (weights reload + Metal graph recompile for the 131712-ctx graph) — discard first probe, warm numbers are steady-state.
- Zero crashes across the full cheap tail, throughput scenarios, and 65k-token reasoning spirals.

## Client configuration
- Model id: `agents-a1-xl-mlx` (LM Studio `/v1` endpoint, port 1234); on-disk dir `~/.lmstudio/models/leonsarmiento/Agents-A1-6bit-XL-mlx`.
- Sampling: vendor recommends `temperature=0.85, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=1.1` (MLX card adds `repeat_penalty=1.05, min_p=0.01`); local benches ran temp 0 / seed 42 for reproducibility.
- Tool calling works natively through LM Studio's parser (jdhodges 92.5%) — no template surgery needed. `qwen3_coder` tool-call parser per the MLX card.
- Reasoning tokens are parsed as structured `reasoning_tokens` (content stays clean) — but budget for them: ≥500 output tokens per turn or you may get no visible output.

## External links
- Vendor: https://huggingface.co/InternScience/Agents-A1 (Apache 2.0; SGLang/vLLM deployment configs, 262K context)
- MLX conversion: https://huggingface.co/leonsarmiento/Agents-A1-6bit-XL-mlx (BaseQuant_XL 6/8-bit mixed, 6.808 bpw, ~28 GB / 6 shards)

## History
- **2026-07-04** — New arrival; residency correction (unloaded hermes-4-70b + 27b, swap 19.9 GB → 166 MB); speed probe + tool-calling (jdhodges 92.5%, Veerman 83.3%); cheap tail launched ([plan](../benchmark-plans/2026-07-04-agents-a1-xl.md)).
- **2026-07-05** — Cheap tail complete: HumanEval 97%, MMLU 82%, LCB v6 64%. Throughput scenarios: 3 of 4 fail on thinking tax (effective 35.9 t/s); 2 harness bugs found + fixed. T-Bench attempt aborted at 2/89 (Docker env error). Gate = marginal coding-only pass → 🟡 **GO (marginal)**, expensive tail deferred. Recorded in [testing-plan.md](../testing-plan.md) and [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).
