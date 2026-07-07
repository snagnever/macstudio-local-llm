# 2026-07-03 — MiniMax-M2.5-3bit feasibility + cheap-signal benchmark

## Context

`mlx-community/MiniMax-M2.5-3bit` (93 GB on disk, downloaded 2026-07-03) is a
new large-MoE arrival on the Mac Studio M4 Max 128 GB rig: `minimax_m2` arch,
256 experts / 8 active, 62 layers, 196k context, thinking + tool-calling in the
chat template. It's the highest-ceiling new model but also the riskiest —
93 GB puts it in the **sole-model-loaded** class (like `deepseek-v4-flash-dq`,
the only prior model in that class), and it ships custom modeling code
(`modeling_minimax_m2.py` + `auto_map`).

**Load confirmed (2026-07-03):** `GET /v1/models` returns id **`minimax-m2.5`**;
`lms ps` shows it resident at **100.10 GB, context 65000, PARALLEL 4, IDLE**, and
it's the *only* model loaded. The arch-support risk is retired — the remaining
risk is purely **memory + 3-bit quality**: 100 GB resident on a 128 GB machine
leaves only ~28 GB for KV, and **PARALLEL 4 reserves ~4× the KV cache**, so the
feasibility soak must drop parallelism to 1 and watch wired RAM closely.

**Why this is *not* expected to be DeepSeek-V4-class blocked:** the config
confirms standard GQA (`num_kv_heads 8` vs 48 heads, `head_dim 128`), **no MLA**
(`kv_lora_rank`/`q_lora_rank` absent), and full attention every layer
(`attn_type_list` all `1`). The DeepSeek-V4 Metal `resource_limit: 499000` wall
was specifically its MLA compressor/indexer leaking a live buffer per layer per
decode step — MiniMax has no MLA, so that exact failure mode does not apply.

**Decisions (user-confirmed 2026-07-03):**
- **Runtime:** on-disk MLX 3-bit via LM Studio (confirmed loading). The
  standalone-`mlx_lm.server` and GGUF fallbacks are **not needed**.
- **Scope:** feasibility + cheap signals only. Gate hard. The expensive tail
  (MATH / DROP / GPQA / throughput / Terminal-Bench) runs **only if** the model
  clears a quality bar on the cheap signals — a follow-up plan, not committed up
  front.

**Outcome:** a defensible verdict on whether `minimax-m2.5` is worth a full
sweep — proven to load + sustain generation without OOM/degeneration, with
tool-calling + coding + MMLU numbers to rank it against the existing scoreboard.

Mirrors the format of
[`2026-05-29-deepseek-v4-flash-phase-3.md`](../deepseek-v4-flash/plan-phase-3.md)
(the closest precedent) but stops at the cheap-signal gate.

## Approach

Drive the **existing harnesses only** — no new scripts. Route every bench at
LM Studio's OpenAI endpoint (`http://127.0.0.1:1234/v1`) via the `LMSTUDIO_URL`
env var (or `--base-url`). Run **model-major** with MiniMax as the *only*
resident model. Benches run cheap-first so a disqualifying result saves the
expensive tail. Use the model ID **`minimax-m2.5`** verbatim (from
`GET /v1/models`) for every `--model`.

**Runtime:** LM Studio MLX engine, on-disk model — **confirmed working**.
Fallbacks (standalone `mlx_lm.server`; GGUF via llama.cpp) are documented in the
DeepSeek-V4 plan but not needed here. Only revisit if the memory soak (Phase 0)
proves the 3-bit MLX build can't fit + sustain on this rig.

## Phase 0 — Short feasibility test (the "short test first")

Goal: now that the arch loads, prove it **sustains a long generation** without
OOM or 3-bit degeneration, at a benching-safe memory config. This is the whole
gate — if it fails, nothing downstream matters.

1. **Pre-flight — already satisfied.** `minimax-m2.5` is resident and the only
   loaded model. Confirm nothing else has been loaded since:
   ```bash
   lms ps            # expect only minimax-m2.5
   ```
2. **Re-tune the load for benching: PARALLEL 4 → 1.** The model came up with
   `PARALLEL 4`, reserving ~4× the KV cache — wasteful and a memory risk at
   100 GB resident. Benching is sequential (seed=42, temp=0), so reload single-
   stream. Keep context at 65000 (matches the raised-cap benches); it's a no-MLA
   arch so OOM risk is lower than DeepSeek-V4, but if the soak (step 4) pushes
   wired RAM past ~120 GB, reload at `--ctx 32768`:
   ```bash
   cd /Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
   # reload with parallel=1 (via LM Studio UI load config, or lms load flags)
   python3 scripts/lms.py check     # status + warmup (2+2) + params
   ```
3. **Export the confirmed model ID** for every downstream command:
   ```bash
   export LMSTUDIO_URL=http://127.0.0.1:1234/v1
   export MODEL=minimax-m2.5          # verbatim from GET /v1/models
   ```
4. **Speed probe (~10 min)** — 3 prompts, confirms coherent output + rough tok/s:
   ```bash
   python3 scripts/speed_probe.py "$MODEL" results/speed_probe
   ```
5. **Sustained-generation soak (the key gate).** The DeepSeek-V4 leak only
   surfaced past ~11,300 generated tokens — a 3-prompt probe would have missed
   it. Force one long generation and watch the server log + memory:
   ```bash
   curl -s http://127.0.0.1:1234/v1/chat/completions -H 'Content-Type: application/json' \
     -d '{"model":"'"$MODEL"'","messages":[{"role":"user","content":"Write a detailed 4000-word technical essay on distributed consensus algorithms."}],"max_tokens":8192,"temperature":0.0}' \
     | jq '.usage, .choices[0].finish_reason'
   ```
   In a **second pane** during steps 4–5: `sudo memory_pressure` (watch "Wired").

   **Decision gate — abort Phase 0 (and re-evaluate fit) if any of:**
   - Wired memory trends past **~120 GB** → reload at `--ctx 32768` / parallel 1,
     retry; if it still OOMs, the model doesn't fit — stop.
   - Any `metal::malloc` / `Resource limit` error in the server log during the
     soak (unexpected given no-MLA, but this is exactly what we're checking).
   - Output degenerates into repetition/gibberish (3-bit floor) at `temp=0.0` —
     note it; try `temp=0.6`; if still broken, the quant is not viable — stop.

   **Pass condition:** 3-prompt probe coherent, and the 8k-token soak completes
   with `finish_reason: length` (not an error), 0 Metal OOMs, coherent prose.
   Only then proceed to Phase 1.

## Phase 1 — Cheap quality signals (gated on Phase 0 pass)

Cheap-first order from `testing-plan.md`. All assume the Phase 0 env vars. Stop
early if the model floors on tool-calling or HumanEval.

- **1a. Tool-calling (~15–30 min)** — the fastest useful day-to-day signal.
  MiniMax declares `tool_call` in its template, so expect real structured calls:
  ```bash
  python3 scripts/tool_call_bench.py --model "$MODEL" --suite jdhodges --base-url "$LMSTUDIO_URL"
  python3 scripts/tool_call_bench.py --model "$MODEL" --suite veerman  --base-url "$LMSTUDIO_URL"
  ```
- **1b. HumanEval (~30–60 min)** — quick code-gen sanity, back-comparable:
  ```bash
  python3 scripts/bench2.py humaneval --examples 100 --model "$MODEL" --max-tokens 65536
  ```
- **1c. LiveCodeBench v6 (~30–90 min)** — the canonical coding signal:
  ```bash
  python3 scripts/bench2.py livecodebench --examples 50 --model "$MODEL" --lcb-version release_v6 --max-tokens 65536
  ```
- **1d. MMLU (~30–60 min)** — broad knowledge, fast single-letter scoring:
  ```bash
  python3 scripts/bench2.py mmlu --examples 100 --model "$MODEL" --max-tokens 65536
  ```

**Gate to the expensive tail:** MiniMax is a *thinking* model — MATH/GPQA will
spiral and cost hours (cf. Qwen 3.6 dense: 22 h GPQA). Only write the Phase 2
follow-up plan if the cheap signals justify it, e.g. **tool-calling ≥ ~85 %
AND (LCB v6 ≥ ~56 % OR MMLU ≥ ~76 %)** — i.e. it credibly beats the current
daily drivers on at least one axis. Otherwise record the verdict and stop.

## Phase 2 — Expensive tail (deferred; only if Phase 1 clears the bar)

Not committed by this plan. If the gate is met, spin off
`bench/minimax-m2.5/plan-full-sweep.md` mirroring the
DeepSeek-V4 full-sweep steps: MATH, DROP, GPQA (all `--max-tokens 65536`, use
the **detached driver** pattern `nohup bash bench/deepseek-v4-flash/logs/run-<name>.sh & disown`
— this rig lacks `setsid` and Bash-background silently kills long python runs
past ~2 h), then the 4 throughput scenarios (`bench.py --backend lmstudio`),
then Terminal-Bench 2.0 (`--agent-timeout-multiplier 0.5`). Budget ~3–5 days.

## Phase 3 — Record verdict + update docs

Regardless of pass/fail, after Phase 1:
1. **`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`** — append a
   "MiniMax-M2.5-3bit (feasibility, 2026-07-03)" section: runtime path, soak
   result, cheap-signal numbers, one-paragraph verdict.
2. **`docs/testing-plan.md`** — add MiniMax to the model inventory and record it
   on the Phase 4 (watchlist) → arrived path; note "no MLA so not
   DeepSeek-V4-class; gate on memory + 3-bit quality, not arch support."
3. **`docs/local-llm-reference.md`** — only if it earns a slot in the
   Planning/Code/Agent stack.
4. **This plan doc** — fill the Outcome section with the timeline table + verdict.
5. Charts/dashboards — only if it produced comparable (non-floor) numbers;
   otherwise skip to avoid conflating a 3-bit floor with working models
   (the DeepSeek-V4 precedent).

## Verification

In order; stop at first failure.
1. `curl -s $LMSTUDIO_URL/models | jq '.data[].id'` returns `minimax-m2.5`.
2. `lms.py check` warmup returns the right answer to 2+2.
3. Phase 0 soak completes with `finish_reason:"length"`, coherent prose,
   0 `metal::malloc` in the LM Studio server log.
4. Each Phase 1 bench writes both a `.jsonl` and a `_summary.json` under
   `tools/local-llm-bench-m4-32gb/benchmarks/runs/`; summary counts match
   request (40 / 12 / 100 / 50 / 100).
5. Verdict + numbers land in `M4_MAX_128GB_NOTES.md` and this doc.
6. LM Studio still loads other MLX models normally afterward.

## Known risks

- **~~Arch-load unknown~~ — RESOLVED 2026-07-03.** LM Studio's MLX engine loads
  `minimax_m2` (`lms ps` shows `minimax-m2.5` resident). No fallback needed.
- **🔴 GPU kernel panic — MATERIALIZED THREE TIMES, and it is NOT the memory risk
  (2026-07-04).** Under sustained inference the host hard-panicked three times in
  `IOGPUFamily` / `IOGPUGroupMemory` / `AGXG16X`, across every config: parallel 4
  and parallel 1, ctx 65000 and 32768, twice with memory **OK** (0% compressor),
  and once with **KV-cache quantization on** (crash #3, panicked task =
  `LM Studio Helper (GPU)`). A **reproducible Apple GPU-driver bug**, not the
  memory-ceiling risk we predicted. Nothing application-side fixes it — memory
  tuning, config tuning, and KV quantization were all tried and all crashed. See
  "Kernel panic — THREE TIMES" under Outcome. **Verdict: NO-GO; do not re-test on
  this stack.**
- **3-bit degeneration.** Aggressive quant on a large MoE may degrade long-form
  output (cf. DeepSeek-V4 2-bit). The Phase 0 soak catches this before bench hours.
- **Thinking-model spirals.** MATH/GPQA (Phase 2 only) will consume the 65 536
  cap on hard problems; that's why the tail is gated, not committed.
- **Model-ID mismatch → 404.** Always use `minimax-m2.5` verbatim.

## Critical files / paths

- Model: `/Users/vitor/.lmstudio/models/mlx-community/MiniMax-M2.5-3bit`
- Harnesses: `tools/local-llm-bench-m4-32gb/scripts/{speed_probe.py,tool_call_bench.py,bench2.py,lms.py}`,
  `tools/local-llm-bench/bench.py`
- Precedent plan: `bench/deepseek-v4-flash/plan-phase-3.md`
- Outputs: `tools/local-llm-bench-m4-32gb/benchmarks/runs/`, `.../results/speed_probe/`
- Scoreboards: `tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`,
  `docs/testing-plan.md`, `docs/local-llm-reference.md`

## Outcome (2026-07-03) — Phase 0 ✅ PASS (loads, sustains, at memory ceiling)

**Phase 0 verdict:** `minimax-m2.5` loads cleanly in LM Studio's MLX engine and
sustains coherent generation — **but sits right at this rig's memory ceiling.**
It is *not* DeepSeek-V4-class blocked (no MLA, no Metal `resource_limit`), the
sole real constraint is RAM. Proceeding to Phase 1 at **ctx 32768** (the 65536
raised cap does not fit — see below).

### Memory finding (the headline)
- `lms load --estimate-only` reports a **flat 130.52 GiB** at every context length
  (8k–64k) — the estimator doesn't model KV for this custom arch, so it's a
  conservative weights+overhead figure, uninformative for picking ctx.
- Empirically at **ctx 32768 / parallel 1** (parallel count does *not* change the
  estimate — it was a red herring; **context length is the only lever**):
  weights load = 93.23 GiB; during the speed probe **peak RAM 117.8 GB, wired
  106 GB, macmon `Spill=YES`**; during the 4095-token soak **wired plateaus
  ~107 GB and OS swap stays flat (~5.1 GB, all pre-existing)** — no runaway.
- **ctx 65536 is not viable** on 128 GB (estimate 130 GiB; weights 93 + KV would
  overcommit). Benches run at ctx 32768 = bench2.py's default cap, so the
  standard `--max-tokens 65536` raised cap is dropped for this model. Document
  any LCB/GPQA truncation as a memory-imposed floor, not a model limit.

### Timeline
| Time | Step | Result |
|---|---|---|
| 21:4x | Load @ ctx 32768, parallel 1 | ✅ 93.23 GiB, loaded in 21 s |
| 21:4x | `lms.py check` warmup (2+2) | ✅ "4" (37 think + 4 vis tok), PRE-FLIGHT PASS |
| 21:50 | Speed probe (3 prompts) | ✅ ~50 tok/s; trivial/mmlu correct, code coherent; **peak RAM 117.8 GB, Spill=YES** |
| 21:51 | Sustained soak (req 8k tok) | ✅ 4095 tok, `finish_reason: stop`, coherent essay, **0 repetition, 0 metal::malloc, wired ~107 GB, swap flat** |
| ~21:53 | Phase 1a tool-calling **jdhodges** | ✅ **97.5%** (39/40) — strong mechanics |
| ~22:01 | Phase 1a tool-calling **veerman** | ⚠️ **58.3%** (7/12) — weak agentic proactivity (see A/B) |
| 22:04 | Phase 1b HumanEval (contaminated) | ⏹ aborted 41/100 (ran under the A/B preset; discarded) |
| 07-04 ~09:5x | Phase 1b HumanEval (clean rerun) | ✅ **95.8% raw (69/72)** / **97.2% hang-adjusted (69/71)** — cut at 72/100; the last 28 were crawling behind `parallel-4` dead-request hangs (`p=0 c=0`, ~866 s each). Strong pass; HumanEval is a sanity signal, not a gate input. |
| 07-04 ~13:3x | Phase 1c LiveCodeBench v6 (run 1) | 🔴 **kernel panic at 16/50** (crash #1, ctx 65000/parallel 4). 10/16 raw. |
| 07-04 ~15:2x | Phase 1c LiveCodeBench v6 (resume Q17–50) | 🔴 **2nd kernel panic at combined 27/50** (crash #2, *safe* ctx 32768/parallel 1, memory OK). |
| 07-04 ~16:5x | KV-quant workaround attempt (8-bit) + soak + resume Q28–50 | 🔴 **3rd kernel panic at combined 38/50** (crash #3, ctx 32768/parallel 1 **+ KV quant 8-bit**, memory OK, panicked task = `LM Studio Helper (GPU)`). KV quant *delayed* (survived a 10-gen soak + 11 questions) but did **not** prevent it. Combined **26/38 raw (68%) / 26/35 hang-adj (74%)** — permanently incomplete. |
| — | Phase 1d MMLU | ❌ not run — abandoned (model reproducibly crashes the host) |

### 🔴 Kernel panic — THREE TIMES — the disqualifying finding (2026-07-04)

Under sustained inference load, the Mac Studio **hard kernel-panicked and rebooted
THREE times**, all in Apple's GPU driver (`IOGPUFamily` / `AGXG16X`), at the same
`IOGPUGroupMemory` object-tracking subsystem — across every config we tried:

```
Crash #1 (ctx 65000 / parallel 4, fp16 KV, ~memory ceiling):
  panic(cpu 12): "IOGPUGroupMemory::remove_memory_object() memory object not found"
    @IOGPUGroupMemory.cpp:323 · IOGPUFamily(129.3.2)

Crash #2 (ctx 32768 / parallel 1, fp16 KV — the SAFE config; memory OK):
  panic(cpu 5): "pending memory object unexpectedly found in non pending hash"
    @IOGPUGroupMemory.cpp:528 · IOGPUFamily(129.3.2) + AGXG16X(345.20.4)
  Compressor Info: 0% compressed (OK) ... OK swap  ← NOT OOM

Crash #3 (ctx 32768 / parallel 1, KV-CACHE QUANTIZATION 8-bit; memory OK):
  panic(cpu 8): "pending memory object unexpectedly found in non pending hash"
    @IOGPUGroupMemory.cpp:528 · IOGPUFamily(129.3.2) + AGXG16X(345.20.4)
  Compressor Info: 0% compressed (OK) ... OK swap  ← NOT OOM
  Panicked task: pid 685: LM Studio Helper (GPU)   ← LM Studio's GPU process itself

OS build 25D125 · Darwin 25.3.0 (xnu-12377.81.4~5) · Apple M4 Max T6041
```

**Root cause — a reproducible Apple GPU-driver bug, independent of everything we
can control.** It crashes regardless of parallelism (4 and 1), context (65000 and
32768), memory pressure (twice with memory explicitly OK), and KV-cache
quantization (crash #3, KV quant on). Crash #3's panicked task is literally
`LM Studio Helper (GPU)` — LM Studio's Metal process — confirming the trigger is
MLX's Metal allocation/free pattern for this model corrupting `IOGPUGroupMemory`'s
object-tracking hash.

**KV quantization was tested as a workaround and FAILED.** Rationale was sound (it
changes the decode-time Metal buffer path, and the crashes correlate with
long-generation / large-KV load). It *delayed* the crash — survived a deliberate
10-generation stress soak + 11 LCB questions, ~21 long generations, more than the
fp16 path managed — but crash #3 proves it does not prevent the bug. (Cost noted:
KV quant also slows long generations ~10%; a 26k-token spiral averaged 31 t/s vs
~34 fp16. No progressive/cumulative slowdown, though — short gens still hit ~48 t/s
deep into the run.)

**Precursors:** the intermittent `p=0 c=0` dead-request hangs (HumanEval Q67, LCB
Q11, resume Q19, KV-quant Q28) are the same GPU-memory subsystem failing *softly*;
the panic is the *hard* version. They recurred under every config including KV
quant — consistent with a driver bug, not memory.

**VERDICT — NO-GO on this rig/OS.** `mlx-community/MiniMax-M2.5-3bit` is **not
viable** on this Mac Studio (M4 Max, macOS 25D125, IOGPUFamily 129.3.2 / AGXG16X
345.20.4, LM Studio MLX engine). It reproducibly kernel-panics the host under
sustained inference — a machine-crashing, data-loss-risking failure that cannot be
tuned around from the application side. **Do not re-test this model on this stack.**
Only external changes could revisit it: a macOS/GPU-driver update from Apple, an
MLX/LM Studio release that changes the Metal allocation pattern, or a different
runtime (e.g. GGUF via llama.cpp, which uses a different Metal path — untested here,
a separate investigation). The cheap-signal *quality* numbers below are strong, but
they are moot for deployment while the host crashes.

### System-prompt A/B — proactivity nudge (2026-07-04)

**Diagnosis of the veerman gap:** failures were *not* broken tool-calling mechanics
(every call was schema-valid) but **under-agency** — the model asks a clarifying
question instead of acting on implicit / multi-step requests. Baseline fails
`p4`/`p6`/`p11`/`p12` were all "no tool called"; `p2` is a `**/*.py` vs `*.py`
grading artifact, not a real miss.

**Tested prompt:** *"You are a helpful AI Assistant. Prefer taking action with
available tools over asking clarifying questions."*

**Method notes (both non-obvious, both cost time):**
- **LM Studio's UI *System Prompt* field does NOT reach the `/v1/chat/completions`
  API.** The harness sends its own system message and the API uses only the
  request `messages`; the UI preset is ignored. A first attempt via the UI preset
  was a null result (numbers = baseline ± temp-0 jitter). The prompt only takes
  effect when injected into the request — added a `TOOLBENCH_SYSTEM_PROMPT` env
  override in `scripts/tool_call_bench.py`.
- **The proactive prompt sends this *thinking* model into unbounded generation
  spirals** on noisy prompts (`p7_noisy_params` ate the full 600 s call timeout).
  Added a `max_tokens` cap (`TOOLBENCH_MAX_TOKENS`, default 4096) to bound it —
  normal tool-call completions are <350 tok, so ~12× headroom.
- **temp-0 is non-deterministic on this MoE** — `p6` flipped failure modes between
  identical runs, so ±1 case is noise.

| Suite | Baseline | Proactive prompt\* (injected, cap 4096) | Δ |
|---|---|---|---|
| veerman (agentic) | 58.3% (7/12) | **66.7% (8/12)** | +8.3pp |
| jdhodges (mechanics) | 97.5% (39/40) | **90.0% (36/40)** | −7.5pp |

**Verdict:** the proactivity nudge is a **trade, not a free win.** It fixes the
clearest agentic misses (`p4` ambiguous, `p11` negation) and **holds restraint at
2/2** (no indiscriminate firing), but costs 3 jdhodges mechanics cases (multi-tool
8/8 → 5/8) and destabilizes the thinking model on noisy prompts. Net: better for
open-ended agent use, slightly worse for precise multi-tool orchestration. The
jdhodges −3 is consistent across both modded attempts and looks real; the veerman
+1 is within temp-0 jitter and should be re-confirmed before weighting it heavily.

\* = modified (proactive) system prompt injected into the request.
