# MiniMax-M2.5

> **Status: 🟢 GO via GGUF** (MLX build: 🔴 NO-GO — kernel panic).
> The marquee runtime-comparison result on this rig: the model is good; MLX's Metal allocation pattern panics the host, llama.cpp's doesn't.
> Last updated: 2026-07-06

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [MiniMaxAI/MiniMax-M2.5](https://huggingface.co/MiniMaxAI/MiniMax-M2.5) | HF card |
| Parameters | 229B total MoE (LM Studio reports `256×4.9B`; local inspection: 256 experts / 8 active, 62 layers, no MLA) | HF card + [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md) |
| Architecture | `minimax_m2` / `minimax-m2` (MLX / GGUF arch ids) | local inspection |
| Native context | **196,608 (192k)** — from GGUF metadata `minimax-m2.context_length` (RoPE freq_base 5e6, no YaRN). **Usable on this rig: 64,000 max** (hard `Compute error` cliff at 64,512 — a Metal KV-buffer limit; loads but won't infer above it). **Recommended operating ctx 61,440 (60k)**; benches ran at 32,768. | GGUF metadata + local sweep 2026-07-06 |
| License | modified-MIT | HF card |
| Modalities | text only | HF card |
| Reasoning | RL-trained internal reasoning; card says "no explicit thinking tags" but it emits ~145–810 reasoning tokens/response (see Local performance) | HF card + local |
| Tool calling | ✓ (vendor Tool Calling Guide) | HF card |
| Vendor sampling | `temperature=1.0, top_p=0.95, top_k=40` | HF card |
| Vendor claims | SWE-bench Verified 80.2%, Multi-SWE-Bench 51.3%, BrowseComp 76.3% *(vendor — not reproduced locally)* | HF card |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `mlx-community/minimax-m2.5` | [mlx-community/MiniMax-M2.5-3bit](https://huggingface.co/mlx-community/MiniMax-M2.5-3bit) | MLX | 3-bit (mlx-lm 0.30.7 conversion) | 93 GiB | LM Studio MLX | 🔴 **NO-GO 2026-07-04** | Reproducible host kernel panic ×3 under sustained inference |
| `unsloth/minimax-m2.5` | [unsloth/MiniMax-M2.5-GGUF](https://huggingface.co/unsloth/MiniMax-M2.5-GGUF) | GGUF | Q3_K_S | 98.7 GB (98.69 GB resident) | LM Studio llama.cpp 2.23.1 (native — no fork/flags) | 🟢 **GO 2026-07-05** | Soak passed; cheap-signal gate cleared |

## Architecture & spec notes
- 256-expert MoE, 8 active per token, 62 layers, **no MLA** — so no exposure to the mlx-lm MLA cache-leak class of bugs that hit DeepSeek-V4-Flash; its MLX failure is a different (driver-level) mechanism.
- GGUF `minimax-m2` arch is recognized by stock llama.cpp ≥ 2.23.1 — unlike DeepSeek-V4-Flash (which needed 2.24.0 beta + `--no-repack` + standalone server), MiniMax loads LM Studio-native with zero special handling.
- Reasoning tokens are parsed as structured `reasoning_tokens` by LM Studio (they don't pollute `content` — contrast Kimi-Dev's unparsed `◁think▷` markers).

## Local performance (measured)

| Metric | GGUF Q3_K_S | MLX 3-bit |
|---|---|---|
| Sustained generation | **36.8 t/s** (held over 2.3-min 8k soak; 36.2 t/s medium probe) | crashed before any sustained measurement |
| Tool-call runs | 28–31 t/s | — |
| Memory | 98.69 GB resident; peak 121.9/128 GB during soak, swap flat 1.58 GB; clean unload → 12.5 GB baseline (no leak) | 93 GiB weights, ~ceiling at crash #1 |
| Reasoning tax | ~145–810 reasoning tok/response (heavier on code); content stays clean | — |

Context: 5× Kimi-Dev's 7 t/s, faster than `qwen3.6-27b` (20 t/s). Sole-model only — at ~99 GB it cannot co-exist with anything else under the ~80 GB pairing rule.
Source: [M4_MAX_128GB_NOTES.md § MiniMax-M2.5 GGUF](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md), telemetry `.bench-logs/minimax-gguf-feasibility-{macmon.jsonl,lmslog.txt}`.

## Quality benchmarks (measured)

Config: ctx 32,768, temp 0, seed 42, sole-model. MLX numbers are **partial — the sweep crashed out three times and never completed**; not fully comparable.

| Bench | GGUF Q3_K_S (2026-07-05) | MLX 3-bit, partial (2026-07-03→04) |
|---|---|---|
| jdhodges tool-calling (40) | **95%** (38/40) — clears ≥85% gate, 6.9 min @ 28.3 t/s | 97.5% (39/40) |
| Veerman tool-calling (12) | **75%** (9/12) — 3 tool_mismatch (p2/p6/p12); same band as base `qwen3.6-35b-a3b`; the agentic tune did **not** lift the holdout suite | 58.3% (7/12) |
| HumanEval (100) | **94%** — 1 trunc (Q17 spiraled to 32k cap; true ceiling ~94–95%). Beats DeepSeek-V4 GGUF 88%, matches MLX pre-crash 95.8% — GGUF loses nothing | 95.8% raw / 97.2% hang-adj (cut at 72/100) |
| LiveCodeBench v6 (50) | **72%** (36/50) at ctx 60k — 68% (34/50) raw at 32k. easy 15/15, medium 16/23, hard 3/12→5/12. The 5 truncations reran at 60k/57344: **2 recovered** (Q38, Q48), 3 real spirals/wrong (Q8/Q19/Q44). Above `qwen3.6-27b` (62%); below Gemma leaders (80%) | 68% raw / 74% hang-adj (26/38, crashed 3×) |
| Terminal-Bench 2.0 | ❌ **NO-GO (memory)** — 46/46 `EnvironmentStartTimeoutError`; 98.69 GB model starves Docker on 128 GB. Retry path: remote Docker host (see notes) | — |
| MMLU | ⏸ not run | abandoned (host crashes) |

Raw data: `tools/local-llm-bench-m4-32gb/benchmarks/runs/toolcall_{jdhodges,veerman}_unsloth_minimax-m2.5_*`, `results/speed_probe/unsloth_minimax-m2.5_*`.

## Feasibility & verdict

- **2026-07-03 → 07-04 — MLX 3-bit: ⛔ NO-GO.** Loads and generates coherently with strong quality, but under sustained inference it **reproducibly hard kernel-panics the Mac Studio** (×3) in Apple's GPU driver (`IOGPUFamily 129.3.2` / `IOGPUGroupMemory` / `AGXG16X 345.20.4`, macOS 25D125):
  | # | Config | Panic |
  |---|---|---|
  | 1 | ctx 65000 / parallel 4 / fp16 KV | `remove_memory_object() memory object not found` @ IOGPUGroupMemory.cpp:323 |
  | 2 | ctx 32768 / parallel 1 / fp16 KV | `pending memory object … non pending hash` @ :528 |
  | 3 | ctx 32768 / parallel 1 / KV-quant 8-bit | same @ :528 (KV-quant only *delayed* it ~21 long generations) |
  Independent of parallelism, context, memory pressure, and KV quantization — nothing application-side fixes it. Correlates with long-generation / large-KV load (short gens never crashed; LCB's 20k–32k reasoning spirals did). Soft precursor: intermittent `p=0 c=0` dead-request hangs.
- **2026-07-05 — GGUF Q3_K_S: ✅ GO, NO-GO overturned.** The MLX plan's own re-test hypothesis ("a different runtime — GGUF via llama.cpp, a different Metal path") was tested and confirmed: the panic **did not recur** across load, probes, and a full 8k sustained soak (5,038 tok, `finish=stop`, coherent ~4,100-word essay, 0 Metal errors). **The failure was MLX's allocation pattern, not the model.**
- **Re-test triggers (MLX):** Apple macOS/GPU-driver update, or an MLX/LM Studio release changing the Metal allocation pattern. Until then do not re-test MLX.
- **2026-07-06 — LCB v6 68%→72% (ctx-recovery); Terminal-Bench NO-GO (memory).** LCB done (34/50 raw at 32k; reran the 5 truncations at 60k → +2 → 36/50 = 72%). Terminal-Bench can't run locally (98.69 GB model + Docker > 128 GB); the fix is a **remote Docker host** hitting the rig's LM Studio over the LAN (setup validated — see [M4 notes § Terminal-Bench path forward](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)).
- **Remaining work:** MMLU knowledge tail (sole-model, `--max-tokens 32768`); Terminal-Bench via the remote Docker host; then charts + potential `local-llm-reference.md` lineup slot (top-tier local MoE candidate).

Plans: [2026-07-03-minimax-m2.5-feasibility.md](../benchmark-plans/2026-07-03-minimax-m2.5-feasibility.md) · [2026-07-05-phase-5-new-arrivals.md](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md)

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| Host kernel panic under sustained inference (MLX) | Apple GPU-driver bug in `IOGPUGroupMemory` object-tracking hash, triggered by MLX's Metal alloc/free pattern for this model | **No app-side fix.** Use the GGUF build. See Feasibility above. |
| Intermittent `p=0 c=0` dead-request hangs (MLX) | Soft precursor of the panic | Same — GGUF path |
| Reasoning-token overhead (both) | RL-trained internal reasoning despite "no thinking tags" on card | Cosmetic on GGUF: LM Studio parses to `reasoning_tokens`; budget for it in token caps |
| `{"error":"Compute error."}` on every inference at ctx ≥ 64,512 (GGUF) | Metal KV-buffer limit at the 2^16 boundary — model loads fine but can't compute | **Cap context at 64,000; use 61,440 (60k).** 32k–64,000 all verified OK |
| `HTTP 400 Bad Request` on `max_tokens=60000` (2026-07-06, **since resolved**) | Was an artifact of the broken **65536-ctx state**, not a real `max_tokens` limit | Reload at ctx **61440**; `max_tokens=57344` then runs clean. The LCB truncation-recovery DID run this way (+2 recovered → 72%) |

## Loading & memory
- **Sole-model only:** 98.69 GB resident (Q3_K_S) — cannot pair with anything under the ~80 GB weights+KV rule; evict all other models first.
- Load LM Studio-native (bundled llama.cpp ≥ 2.23.1 recognizes `minimax-m2`): `--gpu max --parallel 1`.
- **Context ceiling = 64,000** (hard `Compute error` cliff at 64,512 — Metal KV-buffer limit; the model *loads* at any ctx up to native 192k but every inference errors above 64,000). **Use `--context-length 61440` (60k)** for a safe margin — validated with a real 2,693-token generation. Benches ran at 32,768.
- Soak-verified headroom: peak 121.9/128 GB at 32k with swap flat (60k ≈ 124 GB) — tight but stable; keep other memory consumers closed. ≥96k would exceed 128 GB regardless of the compute cliff.
- Unloads clean (12.5 GB baseline, no leak).

## Client configuration
- Model id: `unsloth/minimax-m2.5` (LM Studio `/v1` endpoint, port 1234).
- Sampling: vendor recommends `temperature=1.0, top_p=0.95, top_k=40`; local benches ran temp 0 / seed 42 for reproducibility.
- Tool calling works natively through LM Studio's parser (jdhodges 95%) — no template surgery needed.
- Default system prompt per unsloth card: "You are a helpful assistant. Your name is MiniMax-M2.5 and is built by MiniMax."

## External links
- Vendor: https://huggingface.co/MiniMaxAI/MiniMax-M2.5 (+ vendor Tool Calling Guide linked from the card)
- MLX conversion: https://huggingface.co/mlx-community/MiniMax-M2.5-3bit (mlx-lm 0.30.7)
- GGUF conversion: https://huggingface.co/unsloth/MiniMax-M2.5-GGUF (Q3_K_S 98.7 GB; range UD-IQ1_S 63.2 GB → Q8_0 243 GB; BF16 457 GB)

## History
- **2026-07-03** — MLX 3-bit feasibility begins ([plan](../benchmark-plans/2026-07-03-minimax-m2.5-feasibility.md)); partial cheap-signal results collected between crashes.
- **2026-07-04** — ⛔ MLX NO-GO after third kernel panic; verdict recorded in [testing-plan.md](../testing-plan.md) (#11) and [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).
- **2026-07-05** — GGUF Q3_K_S feasibility soak PASS (36.8 t/s); jdhodges 95%, Veerman 75%, HumanEval 94%. ✅ **GO via GGUF**; LCB/MMLU tail deferred (rig freed for the 01:00 DeepSeek LCB job).
- **2026-07-06** — LCB v6 **68%** (34/50) raw; ctx-recovery rerun of the 5 truncations at 60k → **+2 (Q38, Q48) → 72%** (36/50). Confirms ~40% of truncations are cap-too-tight, the rest real spirals. Terminal-Bench ❌ **NO-GO** (98.69 GB model leaves ~3 GB for Docker → 46/46 `EnvironmentStartTimeoutError`; not a capability verdict — a 128 GB memory-coexistence limit). **Context ceiling mapped: usable 64,000, cliff at 64,512, native 196,608** (recommend 60k). Distributed path set up (rig serves the model on the LAN at `192.168.68.123:1234`; a second Mac runs Docker/tbench) — see [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md). MMLU still not run.
