# 2026-07-05 — Phase 5: new-arrivals benchmark plan (Jun–Jul wave)

## Context

Since [`docs/testing-plan.md`](../testing-plan.md)'s inventory snapshot
(2026-05-18, Phases 1–2 complete), a wave of large models landed on the
Mac Studio M4 Max 128 GB rig (downloaded Jun 2 → Jul 4). This plan covers the
five the user prioritized, plus `agents-a1-xl` (the zero-cost resident win):

| Model (LM Studio API id) | Publisher | Fmt / quant | Size | LM Studio arch tag |
|---|---|---|---|---|
| `agents-a1-xl-mlx` | leonsarmiento | MLX 6-bit | 29.9 GB | `qwen3_5_moe` |
| `google/gemma-4-31b-qat` | lmstudio-community | GGUF Q4_0 | 18.9 GB | `gemma4` |
| `kimi-dev-72b` | unsloth | GGUF UD-Q6_K_XL | 67.2 GB | `qwen2` |
| `unsloth/minimax-m2.5` | unsloth | GGUF Q3_K_S | 98.7 GB | `minimax-m2` |
| `mellum2-12b-a2.5b-thinking-mlx` | jedisct1 | MLX bf16 | 24.3 GB | `mellum` |
| `nousresearch/hermes-4-70b` | lmstudio-community | MLX 6-bit | 57.3 GB | `llama` |

The one non-obvious lever this plan pulls: **the LM Studio "My Models" arch
badges + each model card's runtime notes let us gate on loadability *before*
committing bench hours.** Three of these six do not run cleanly on the current
stack as-is (bundled llama.cpp 2.23.1 + mlx-llm 1.9.1) — knowing that up front
is worth more than any single benchmark number.

### The runtime-loadability gate (the backbone of this plan)

| Model | Arch | Runtime needed | Loads on current stack? | Basis |
|---|---|:---:|---|---|
| `agents-a1-xl-mlx` | `qwen3_5_moe` | mlx-llm 1.9.1 | 🟢 **Yes** | Same arch as the already-benched `qwen3.6-35b-a3b`; currently **resident + IDLE**. |
| `google/gemma-4-31b-qat` | `gemma4` | llama.cpp 2.23.1 | 🟢 **Yes** | It's an **official lmstudio.ai catalog model** → the bundled runtime supports it. |
| `kimi-dev-72b` | `qwen2` | llama.cpp 2.23.1 | 🟢 **Likely** | Qwen2.5-72B base; card says *"no special fork — standard llama.cpp."* Verify (red arch badge in LM Studio — check `Show warnings`). |
| `unsloth/minimax-m2.5` | `minimax-m2` | llama.cpp 2.23.1 | 🟡 **Loads, but gate hard** | Arch recognized (`256x4.9B` params shown); card says *stock upstream llama.cpp*. **Real question is the Metal path**, not arch — see below. |
| `mellum2-12b-a2.5b-thinking-mlx` | `mellum` | mlx-llm **fork** | 🔴 **Verify — probably not** | Card: *"the mellum architecture is not supported by the stock mlx-lm code yet"* → needs the maintainer's fork; bundled mlx-llm 1.9.1 likely can't load it. |
| `nousresearch/hermes-4-70b` | `llama` | mlx-llm 1.9.1 | 🔴 **Loads, template broken** | Arch fine, but the documented `bos_token` **minja chat-template render error** ([writeup](../hermes-4-bos-token-minja-writeup.md)) breaks `/v1/chat/completions`. Fix template first. |

**Why `minimax-m2.5` GGUF is the marquee experiment.** The MLX build
(`mlx-community/minimax-m2.5`, 3-bit) is a **NO-GO** — it reproducibly
kernel-panicked the host ×3 in Apple's GPU driver
([feasibility plan](2026-07-03-minimax-m2.5-feasibility.md)). That plan's own
verdict named the only re-test path: *"a different runtime (e.g. GGUF via
llama.cpp, which uses a different Metal path — untested here, a separate
investigation)."* **This is that investigation.** llama.cpp's Metal backend
allocates GPU buffers on a completely different code path than MLX, so there is
genuine reason the panic may not recur — but it is unproven, so MiniMax gets a
sole-model feasibility soak *before* any bench, exactly like the MLX attempt.

### Decisions (baked into this plan)

- **Harnesses:** existing only — `bench2.py`, `tool_call_bench.py`,
  `speed_probe.py`, `local-llm-bench/bench.py`. No new scripts.
- **Endpoint:** LM Studio OpenAI-compatible `http://127.0.0.1:1234/v1` for every
  model that loads in LM Studio. Only Mellum (if the fork is needed) would route
  to a standalone `mlx_lm.server`.
- **Order:** by `(value × confidence) / cost` — cheapest & highest-confidence
  first, so a green-light model produces numbers while the risky ones wait for a
  gate. **Model-major** (finish a model's ladder before the next).
- **Scope discipline:** the expensive knowledge tail (MATH / DROP / GPQA /
  throughput / Terminal-Bench) is **not committed up front** for any model — it
  runs only if the cheap signals earn it, per the same gate the MiniMax-MLX plan
  used.

## Run order & rationale

| Seq | Model | Load cost | Why here | Gate before it |
|---|---|---|---|---|
| **1** | `agents-a1-xl-mlx` | **0 GB** (resident) | Free win — already loaded + IDLE, agentic-tuned → tool-calling is its signal. Runs *alongside* the active `qwen/qwen3-coder-next` (4 parallel slots). | none |
| **2** | `google/gemma-4-31b-qat` | 18.9 GB | Smallest, highest-confidence. Settles the deferred **Engine A/B** (Step F): GGUF-QAT vs the already-benched MLX-8-bit `gemma-4-31b-it`. | evict coder-next |
| **3** | `kimi-dev-72b` | 67.2 GB | New 72B **SWE/coding** contender vs the reigning coding king `qwen3.6-27b` (LCB 62 %). High-confidence load. | sole large model |
| **4** | `unsloth/minimax-m2.5` | 98.7 GB | **The NO-GO retry.** Highest ceiling, highest risk. Feasibility soak gates everything. | sole large model + soak |
| **5** | `mellum2-12b-a2.5b-thinking-mlx` | 24.3 GB | Small thinking coder (FIM slot). **Load-probe first** — may need the mlx-lm fork. | verify arch loads |
| **6** | `nousresearch/hermes-4-70b` | 57.3 GB | Reasoning/agentic 70B. **Blocked on chat template** — parked until the minja `bos_token` error is fixed. | fix template |

`deepseek-v4-flash@iq2_xs` / `@q2_k` (GGUF, arch `deepseek4`) are **out of scope
here** — they need the `cchuter/llama.cpp` `feat/v4-port-cuda` fork (stock
llama.cpp lacks V4); that's a from-source build tracked separately.

## Per-model spec + ladder

Every session assumes the standard pre-flight and env:

```bash
export LMSTUDIO_URL=http://127.0.0.1:1234/v1
cd /Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
python3 scripts/lms.py check            # loaded? ctx set? warmup 2+2? one large model?
```

Use the **exact** `GET /v1/models` id for `--model` (mismatched id → 404).

---

### 1 — `agents-a1-xl-mlx` — agentic Qwen3.5-MoE (RUN FIRST, no eviction)

- **Arch / card:** `qwen3_5_moe` (same family as the benched `qwen3.6-35b-a3b`),
  6-bit MLX, 29.9 GB. LM Studio flags **vision + tools** (eye + hammer icons).
  An agentic fine-tune → tool-calling is the headline signal.
- **Loadability:** 🟢 resident + IDLE right now. Zero load cost; benches run on
  the spare parallel slots without evicting the active `coder-next`.
- **Ladder (cheap-only first pass):**
  ```bash
  python3 scripts/speed_probe.py agents-a1-xl-mlx results/speed_probe
  python3 scripts/tool_call_bench.py --model agents-a1-xl-mlx --suite both --base-url "$LMSTUDIO_URL"
  python3 scripts/bench2.py humaneval     --examples 100 --model agents-a1-xl-mlx --max-tokens 65536
  python3 scripts/bench2.py livecodebench --examples  50 --model agents-a1-xl-mlx --lcb-version release_v6 --max-tokens 65536
  ```
- **Hypothesis:** as a 35B-A3B-class MoE it should land near `qwen3.6-35b-a3b`
  (jdhodges 97.5 %) but the *agentic tune* may lift Veerman (the agentic suite)
  above the base model's 75 %. If tool-calling ≥ ~90 % on both suites, promote to
  the knowledge tail; else record and move on.

---

### 2 — `google/gemma-4-31b-qat` — the Engine A/B

- **Arch / card:** `gemma4`, **QAT** (quantization-aware trained) Q4_0, 18.9 GB;
  vision + tools + thinking (`<|channel>thought` markers, `enable_thinking`).
  Near-bf16 quality at 4-bit is the QAT claim.
- **Loadability:** 🟢 official LM Studio catalog model → bundled llama.cpp runs it.
- **The comparison:** this is the same base as the **already-benched
  `gemma-4-31b-it-mlx` (MLX 8-bit)** — so it's a true **cross-engine + cross-quant
  A/B**, the [testing-plan Step F](../testing-plan.md) engine comparison that was
  deferred for lack of a GGUF on disk. Record under
  `results/engine_comparison.md`.
- **Ladder:**
  ```bash
  # throughput sweep doubles as speed probe (llama.cpp Metal path)
  cd ../local-llm-bench
  python3 bench.py --backend lmstudio --base-url "$LMSTUDIO_URL" \
    --model google/gemma-4-31b-qat --model-label gemma-4-31b-qat-gguf-q4_0
  cd ../local-llm-bench-m4-32gb
  python3 scripts/tool_call_bench.py --model google/gemma-4-31b-qat --suite both --base-url "$LMSTUDIO_URL"
  python3 scripts/bench2.py humaneval     --examples 100 --model google/gemma-4-31b-qat --max-tokens 65536
  python3 scripts/bench2.py livecodebench --examples  50 --model google/gemma-4-31b-qat --lcb-version release_v6 --max-tokens 65536
  python3 scripts/bench2.py mmlu          --examples 100 --model google/gemma-4-31b-qat --max-tokens 65536
  ```
- **Hypotheses to settle:** (a) does QAT-Q4_0 match MLX-8-bit `gemma-4-31b` on
  quality (near-bf16 claim), at a fraction of the size (18.9 vs 33.8 GB)? (b) does
  the *"llama.cpp short, MLX long"* rule of thumb hold — GGUF faster on short
  tool-call outputs, MLX faster on long MATH generations? Watch the
  thinking-channel parser: verify the harness scores the final answer, not the
  `<|channel>thought` block.

---

### 3 — `kimi-dev-72b` — new SWE/coding contender

- **Arch / card:** `qwen2` (Qwen2.5-72B base), 73B dense, UD-Q6_K_XL 67.2 GB.
  RL-tuned for repo-patching; **SWE-bench Verified 60.4 %** (SOTA among open
  models at release). Card: standard llama.cpp, no fork.
- **Loadability:** 🟢 likely — but the LM Studio arch badge renders **red**;
  before a long run, verify it loads and serves chat (the red badge may be a
  `Show warnings` flag). **Context caveat:** Qwen2.5-72B is **32 768 native**
  (128k only via YaRN) — confirm the loaded context and whether `--max-tokens
  65536` overshoots native; if so, cap at 32 768 and note LCB truncations as a
  context floor, not a model limit.
- **Ladder (coding-weighted — it's a coding model):**
  ```bash
  python3 scripts/speed_probe.py kimi-dev-72b results/speed_probe
  python3 scripts/tool_call_bench.py --model kimi-dev-72b --suite both --base-url "$LMSTUDIO_URL"
  python3 scripts/bench2.py humaneval     --examples 100 --model kimi-dev-72b --max-tokens 32768
  python3 scripts/bench2.py livecodebench --examples  50 --model kimi-dev-72b --lcb-version release_v6 --max-tokens 32768
  python3 scripts/bench2.py mmlu          --examples 100 --model kimi-dev-72b --max-tokens 32768
  ```
- **Hypothesis:** the SWE-bench pedigree should make **LCB the headline** — target
  is to beat `qwen3.6-27b`'s 62 % (current rig leader). Dense 72B at Q6 → expect
  slow decode (~10–14 t/s, cf. `gemma-4-31b` dense 13.7); tolerable for a coding
  specialist but disqualifying for an agentic-loop daily driver. If LCB ≥ 62 %,
  it earns the full knowledge tail; if it just ties HumanEval-saturation and
  trails on LCB, park it.

---

### 4 — `unsloth/minimax-m2.5` (GGUF) — the NO-GO retry (feasibility-gated)

- **Arch / card:** `minimax-m2`, 229B MoE (`256×4.9B` per LM Studio), Q3_K_S
  98.7 GB. Card: **stock upstream llama.cpp**, tool-calling supported, sampling
  `temp 1.0 / top_p 0.95 / top_k 40`, no explicit thinking tags.
- **Loadability:** 🟡 arch loads — but at **98.7 GB it's sole-model class** (like
  the MLX build that sat at the 128 GB ceiling), and **the open question is
  whether llama.cpp's Metal path avoids the kernel panic** that NO-GO'd MLX.

**Phase 0 — feasibility soak (HARD GATE; nothing runs until this passes).**
Mirror the MLX feasibility plan's Phase 0, on the GGUF runtime:

1. Evict all other models; load `unsloth/minimax-m2.5` **parallel 1**, context
   **32 768** (65 536 will not fit at ~99 GB weights — same finding as the MLX
   build). Confirm sole residency: `lms ps`.
2. Speed probe (3 prompts) — coherent output + rough t/s.
3. **Sustained soak** — force a long generation and watch the host:
   ```bash
   curl -s $LMSTUDIO_URL/chat/completions -H 'Content-Type: application/json' \
     -d '{"model":"unsloth/minimax-m2.5","messages":[{"role":"user","content":"Write a detailed 4000-word technical essay on distributed consensus algorithms."}],"max_tokens":8192,"temperature":1.0,"top_p":0.95,"top_k":40}' \
     | jq '.usage, .choices[0].finish_reason'
   ```
   In a second pane: `sudo memory_pressure` (watch Wired) **and** tail the LM
   Studio server log for `metal::malloc` / resource errors.

   **Abort the whole model if any of:** host kernel-panics/reboots (the MLX
   failure mode — this is the entire point of the gate); wired RAM trends past
   ~120 GB and OOMs even at ctx 32 768; output degenerates at the card's sampling
   (3-bit-class floor). **Pass only if** the 8k soak completes with
   `finish_reason:"length"`, coherent prose, 0 Metal errors, no panic.

**Phase 1 — cheap signals (only on Phase 0 pass):** tool-calling (both suites) →
HumanEval → LCB v6 → MMLU, all at `--max-tokens 32768`, using the card's sampling
where the harness allows. Gate to the expensive tail:
**tool-calling ≥ ~85 % AND (LCB ≥ ~56 % OR MMLU ≥ ~76 %)**.

- **Hypothesis:** if the GGUF Metal path is stable, MiniMax's numbers were already
  strong on MLX before the crashes (jdhodges 97.5 %, HumanEval 95.8 %, partial LCB
  ~68–74 %) — so this becomes a genuine top-tier local model. If it *also* panics,
  that's a decisive result: the failure is the model's Metal allocation pattern on
  this GPU **regardless of runtime**, and MiniMax-M2.5 is closed on this rig until
  Apple ships a driver fix.

---

### 5 — `mellum2-12b-a2.5b-thinking-mlx` — small thinking coder (load-probe first)

- **Arch / card:** `mellum` (JetBrains Mellum2, MoE **12B total / 2.5B active**,
  64 experts / 8 per token, sliding-window + full-attention), **bf16** 24.3 GB,
  **131 072** context, reasoning in `<think>…</think>`. Targets code + FIM.
- **Loadability:** 🔴 **verify first.** Card: *"the mellum architecture is not
  supported by the stock mlx-lm code yet"* → needs the maintainer's mlx-lm fork.
  Bundled mlx-llm 1.9.1 likely errors on load despite LM Studio showing the badge.
  ```bash
  # LOAD PROBE — does the bundled MLX runtime accept the arch at all?
  lms load mellum2-12b-a2.5b-thinking-mlx --context-length 32768 2>&1 | tee /tmp/mellum-load.log
  python3 scripts/lms.py check
  ```
  - **If it loads:** run the small-model ladder (speed probe → tool-calling →
    HumanEval → LCB), it's cheap (24 GB) and fast (2.5B active).
  - **If it errors on arch:** park it. Re-test path is a standalone
    `mlx_lm.server` built from the maintainer's fork, pointed at
    `~/.lmstudio/models/jedisct1/Mellum2-12B-A2.5B-Thinking-mlx`, then route the
    harness `--base-url` at that server. Track as a separate build task; do **not**
    block the rest of Phase 5 on it.
- **Hypothesis:** a 2.5B-active thinking coder is a **FIM / quick-call** candidate,
  not a daily driver — bench it against `gemma-4-e4b` (the current small-slot
  holder: HumanEval 91 %, jdhodges 88 %). The `<think>` blocks mean it will spend
  tokens reasoning; watch for the small-model MATH collapse that sank E4B (14 %).

---

### 6 — `nousresearch/hermes-4-70b` — parked on chat template

- **Arch / card:** `llama` (Llama-3.1-70B base), 6-bit MLX 57.3 GB; reasoning +
  tool-use + agentic, hybrid thinking mode. Loads as an arch, but…
- **Loadability:** 🔴 **blocked** — the documented `bos_token` **minja
  chat-template render error** on LM Studio
  ([writeup](../hermes-4-bos-token-minja-writeup.md)) breaks
  `/v1/chat/completions`. A Claude-Agent-SDK provider for it is in flight
  (git history), which may carry the template fix.
- **Plan:** **do not bench until the template renders.** Prerequisite task: apply
  the template fix (patch the minja `bos_token` handling in the model's
  `chat_template`, or serve via the SDK provider path), verify with a single
  `lms.py check` warmup, *then* run the standard 70B ladder (speed probe →
  tool-calling → HumanEval → LCB → MMLU). Until then it stays out of the run queue.
- **Hypothesis:** a Hermes/Llama-70B is a **reasoning + tool-use** play, not a
  coder — compare tool-calling against `qwen3.6-27b` (95 %) and knowledge against
  the same. Dense 70B MLX → expect slow decode; likely a "quality reference," not
  a throughput pick.

## Memory & operational rules (recap for this wave)

- **`weights + KV < 80 GB`** where possible. Seq 1–2 co-exist with headroom; seq
  3–4 are **sole large model** (evict `coder-next`, which is currently PROCESSING
  with a 6 h TTL — coordinate before evicting). MiniMax (98.7 GB) and Kimi
  (67.2 GB) must be the only large model resident.
- **Context on load:** 32 768 for the ≥67 GB models (65 536 doesn't fit at those
  weights — confirmed for MiniMax-class on the MLX build). 65 536 for the small
  ones (Gemma-QAT, agents-a1, Mellum) to match the raised-cap benches. Document
  any truncation at 32 768 as a **memory/context floor**, not a model limit.
- **Parallel 1** for benching (sequential, temp-0/seed-42); parallel 4 wastes ~4×
  KV and adds memory risk on the big models.
- **Detached driver** (`nohup bash .bench-logs/run-<name>.sh & disown`) for any
  leg > ~2 h — Bash-background silently kills long python runs past ~2 h on this
  rig (no `setsid`). Set `BENCH_TIMEOUT=3600` for ≤ 20 t/s thinking-model runs.
- **Thermal:** watch 85 °C, abort 95 °C. Tool-call harness cools to 60 °C between
  cases.
- **Kernel-panic watch (MiniMax only):** a host panic is a *data-loss* event —
  run the Phase 0 soak with no unsaved work open, and stop the model at the first
  `IOGPUGroupMemory` panic rather than retrying configs (the MLX build proved
  config-tuning doesn't help).

## Deliverables (per [testing-plan §Deliverables](../testing-plan.md))

After each model completes (or is decisively gated out):

1. `tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md` — append a
   Phase 5 section per model: runtime path, loadability verdict, cheap-signal
   numbers, one-paragraph take.
2. `tools/local-llm-bench-m4-32gb/results/engine_comparison.md` — the
   Gemma-4-31B GGUF-QAT vs MLX-8-bit A/B (seq 2).
3. `tools/local-llm-bench-m4-32gb/benchmarks/runs/` — per-question JSONL +
   `_summary.json` (auto-written).
4. `tools/local-llm-bench/results/<label>/` — throughput scenario JSONs.
5. `reports/benchmark-charts.html` + `reports/quality-benchmarks-charts.html` —
   refresh per `reports/README.md` (only for models that produced non-floor
   numbers — don't conflate a crash/floor with a working model, per the
   DeepSeek-V4 / MiniMax-MLX precedent).
6. `docs/local-llm-reference.md` — slot/role updates if a new model displaces an
   incumbent (esp. Kimi vs 27b for coding, agents-a1 vs 35b-a3b for agentic).
7. `docs/testing-plan.md` — fold these six into the inventory as **Phase 5**;
   update the loadability-gate table and Current-status rows.
8. This plan — fill an **Outcome** section per model with a timeline table +
   verdict, as the MiniMax-MLX plan does.

## Verification (per model, stop at first failure)

1. `curl -s $LMSTUDIO_URL/models | jq '.data[].id'` returns the exact id.
2. `scripts/lms.py check` warmup returns the right answer to 2+2 (catches the
   Hermes template break and any Mellum arch-load failure immediately).
3. For MiniMax: Phase 0 soak completes `finish_reason:"length"`, 0 `metal::malloc`,
   **no kernel panic**, before any bench runs.
4. Each bench writes both `.jsonl` and `_summary.json`; counts match the request
   (40 / 12 / 100 / 50 / 100).
5. Numbers + verdict land in `M4_MAX_128GB_NOTES.md` and this doc.
6. LM Studio still loads other models normally afterward (esp. after MiniMax).

## Known risks

- **MiniMax GGUF may panic like the MLX build.** Different Metal path = reason for
  hope, not a guarantee. The Phase 0 gate exists precisely to find out cheaply and
  safely. A panic here is a *publishable* negative result.
- **Mellum needs a fork** (probable). Don't let its build block the green-light
  models — it's parked behind a load probe by design.
- **Hermes template** must be fixed before it can be benched at all; it's
  sequenced last for that reason.
- **Kimi native context 32 768** — overshooting with `--max-tokens 65536` could
  hurt or error; the ladder caps it at 32 768 deliberately. Verify on load.
- **Model-ID mismatch → 404.** Use the verbatim `GET /v1/models` ids
  (`google/gemma-4-31b-qat`, `unsloth/minimax-m2.5`, `nousresearch/hermes-4-70b`
  carry their publisher prefix; `kimi-dev-72b`, `agents-a1-xl-mlx`,
  `mellum2-12b-a2.5b-thinking-mlx` do not).
- **Evicting `coder-next`** interrupts whatever's using it (6 h TTL, currently
  PROCESSING) — coordinate before seq 3+.

## Critical files / paths

- Models: `~/.lmstudio/models/{leonsarmiento/Agents-A1-6bit-XL-mlx,
  lmstudio-community/gemma-4-31B-it-QAT-GGUF, unsloth/Kimi-Dev-72B-GGUF,
  unsloth/MiniMax-M2.5-GGUF, jedisct1/Mellum2-12B-A2.5B-Thinking-mlx,
  lmstudio-community/Hermes-4-70B-MLX-6bit}`
- Harnesses: `tools/local-llm-bench-m4-32gb/scripts/{speed_probe.py,
  tool_call_bench.py,bench2.py,lms.py}`, `tools/local-llm-bench/bench.py`
- Precedent plans: [`2026-07-03-minimax-m2.5-feasibility.md`](2026-07-03-minimax-m2.5-feasibility.md)
  (feasibility-gate format), [`2026-05-20-gemma-4-phase-2.md`](2026-05-20-gemma-4-phase-2.md)
  (full-suite format)
- Scoreboards: `tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`,
  `docs/testing-plan.md`, `docs/local-llm-reference.md`

## Outcome

### seq 3 — `kimi-dev-72b` — ⛔ ABORTED at the speed step (2026-07-05)

Ran first (user chose to start with Kimi). Loaded clean (evicted the two idle
residents; 62.55 GiB weights, 67.16 GB resident, ctx 32768, parallel 1; the red
LM Studio arch badge was benign — stock llama.cpp 2.23.1). Pre-flight PASS.
**Aborted at the speed step of the cheap-signal ladder** — never reached graded runs.

| Time | Step | Result |
|---|---|---|
| 10:40 | Speed probe #1 (87 GB, no swap) | ~7.0 t/s trivial, 6.9 t/s mmlu; code prompt timed out at the 120 s probe cap (mid-`◁think▷`) |
| ~10:45 | Manual tool-call probe | `tool_calls: []` — emitted prose *about* calling the tool inside `◁think▷`; **no structured call** |
| 10:53 | Speed probe #2 | ~7.0 / 7.2 t/s — but `qwen/qwen3-coder-next` had JIT-reloaded (6 h TTL) → 112 GB weights co-resident, **135 GB / 19 GB swap, Spill=YES** |
| ~10:58 | Unloaded coder-next (user-confirmed) | back to sole-model, 44 GB free |
| 11:02 | Speed probe #3 (88.7 GB, no swap) | ~7.1 / 7.2 t/s — **identical to #1**; confirms speed is compute-bound (GPU 100 %, 54 W), not memory-limited |

**Verdict — NO-GO on speed.** ~7 t/s is the slowest model benched on this rig
(½ of `qwen3.6-27b`, ⅓ of `gemma-4-31b` dense), and the mandatory `◁think▷` spiral
(non-standard markers, unparsed by LM Studio → land in `content`) makes effective
throughput worse still. Disqualified as a daily-driver / agentic model regardless of
coding quality; its one differentiating axis (SWE/coding, LCB+HumanEval) was **not
measured** — ~1–2 rig-days at 7 t/s is not worth spending on an already-ruled-out model.
Full write-up in `M4_MAX_128GB_NOTES.md` (§ kimi-dev-72b). Revisit only with a faster
path (lighter quant holding SWE quality, speculative-decoding draft model, or a smaller
Kimi-Dev distillation).

**Harness note:** the machine's Python env had lost the harness deps; stood up a fresh
`tools/local-llm-bench-m4-32gb/.venv` (uv, py3.11) with `openai`+`datasets`+`pyyaml`+
`huggingface_hub`. Invoke benches as `.venv/bin/python scripts/…`.
