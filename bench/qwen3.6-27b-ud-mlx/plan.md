# Qwen3.6-27B — UD-MLX-6bit vs the dense-27B daily driver (2026-07-10)

## Correction (2026-07-10)

Originally framed this as UD-6bit vs the **35B-A3B MoE `@6bit`** daily driver.
Wrong comparison — that's a different architecture (MoE, 3B active) and the
dense-27B family already has its own daily driver documented in
[docs/models/qwen3.6-27b.md](../../docs/models/qwen3.6-27b.md). This campaign is
**27B vs 27B, quant vs quant**. Phase 1 numbers below are corrected against the
right anchor; Phase 2 was stopped before completion under the wrong framing and
restarts clean against the corrected one.

## Hypothesis

`unsloth/Qwen3.6-27B-UD-MLX-6bit` just landed (**28 GB disk / 30.52 GB
resident**). The dense-27B daily driver is `qwen3.6-27b`
(`mlx-community/Qwen3.6-27B-6bit`, **22.80 GB**, ~20 t/s, knowledge avg 85.8%,
🟢 DAILY DRIVER). Same architecture, same nominal "6-bit" label — but Unsloth
Dynamic (UD) quantization assigns mixed precision per-layer (higher bits to
sensitive layers), so it isn't actually the same recipe at the same size.

> Does UD's **+34% memory** over the mlx-community 6-bit build buy enough
> quality to be worth it — or is it the same quant label doing more work for a
> worse size/speed trade?

A third data point is already on disk: `qwen3.6-27b-ud-mlx@4bit` (unsloth
UD-MLX-4bit, 24 GB) — flagged in the model card as an "out-of-scope community
re-quant, not a daily-driver candidate," **never formally benched**. Cheap
signals here can retire or promote that flag for free alongside the 6-bit
comparison.

## Config (locked to the 27b@6bit daily-driver anchor)

| Knob | Value |
|------|-------|
| Served id (subject) | `qwen3.6-27b-ud-mlx@6bit` |
| Served id (baseline) | `qwen3.6-27b` (mlx-community 6-bit) |
| Context | 65536 |
| Temperature / seed | 0 / 42 |
| Thinking | **ON** (reasoning_tokens>0 asserted before each phase) |
| Parallel | 4 (speed probe: 1 for clean single-stream) |

## Anchors — what to beat (dense 27B daily driver, `qwen3.6-27b` mlx-community 6-bit)

| Metric | **27b@6bit daily driver** (22.80 GB) |
|--------|---------------------------------------|
| Sustained gen | **~20 t/s** (20.0–20.7 across scenarios) |
| Effective (ops-agent) | 16.2 t/s |
| HumanEval (100) | **93%** |
| MMLU | **88%** |
| LiveCodeBench v6 (50) | 62% |
| MATH | 88% |
| DROP | 90% |
| GPQA (raw / ceiling) | 70% raw / ~78–85% ceiling |
| jdhodges tool-call (40) | **95%** (38/40) |
| veerman tool-call (12) | **83.3%** |
| Terminal-Bench 2.0 | **31.5%** (28/61 PASS, #2 on rig) |

Replacement bar for UD-6bit: **match-or-beat the daily driver** given it costs
+34% memory and (per Phase 1, corrected) is *slower*, not faster — so it has no
speed argument in its favor, only a possible quality one.

## Phases

- **Phase 1 — Speed probe**: single-stream decode t/s vs the 20 t/s anchor.
- **Phase 2 — Cheap signals**: jdhodges → veerman → HumanEval(100) → MMLU(100),
  thinking-on, run against `qwen3.6-27b-ud-mlx@6bit`. Same suite already used for
  the daily driver, so scores compare directly against the anchors table above.
- **Phase 3 — Terminal-Bench 2.0** (conditional on Phase 2 clearing the bar).

## Results

### Phase 1 — Speed probe (2026-07-10, corrected)

Single-stream (parallel 1, thinking-on, temp 0), ctx 65k, `qwen3.6-27b-ud-mlx@6bit`:

| Question | tokens | elapsed | t/s |
|----------|--------|---------|-----|
| trivial (2+2) | 120 | 7.8 s | 15.3 |
| mmlu_atmosphere | 315 | 20.3 s | 15.5 |
| code_second_largest | 1023 | 64.6 s | **15.8** |

System during code decode: RAM 60.8 GB, Swap 1.0 GB, GPU 99%, 43 W, no spill.
Held steady at 14–16 t/s across 28 live jdhodges calls in Phase 2 before the
run was stopped (see below) — not a probe artifact.

**Corrected comparison:** UD-6bit ~15.8 t/s vs the dense-27B daily driver's
**~20 t/s ⇒ ~21% slower**, same architecture. Resident memory: UD-6bit
**30.52 GB** vs daily-driver **22.80 GB ⇒ +34%**. So UD-6bit currently has
**no speed or memory argument** — it can only win this comparison on quality
headroom big enough to justify both costs.

**METHODOLOGY FLAG (2026-07-10, still open):** the numbers above were measured
**thinking-ON**. Checked the daily-driver anchor's raw JSON afterward — its
scenario speed numbers (gen_tps ~20, e.g. doc-summary 88 output tokens inside a
150-token cap) carry **no `reasoning_tokens` field and far too little budget for
a reasoning pass** — i.e. that anchor was produced **thinking-OFF**. (Its
accuracy anchors, HumanEval/MMLU, *are* thinking-on — `reasoning_tokens` present,
max_tokens=32768 — so Phase 2 stays correctly configured.) Thinking-on vs
thinking-off speed isn't comparable. Re-running Phase 1 + 1b thinking-off via
`scripts/run-27b-ud6-speed-nothink.sh` (chat-template patched the same way as
the 35B-A3B UD-4bit campaign) — queued to run right after Phase 2 finishes
(can't reload the model mid-Phase-2 without corrupting that run). The
thinking-on numbers above stay for the record but are **not the comparable
figure** — see the no-think results once they land.

### Phase 1b — Scenario throughput sweep (2026-07-10) — FAILED, load-bearing finding

Ran `tools/local-llm-bench/bench.py`, thinking-on, vs the daily driver's canonical
scenario anchors (`qwen3.6-27b-dense-mlx-6bit`: creative-writing gen_tps 20.6–20.7).
**All 4 scenarios failed** with the same error:

> Model produced reasoning tokens but no visible output. It spent its entire
> token budget on reasoning, leaving nothing for the actual response.

| Scenario | max_tokens | Result |
|----------|-----------:|--------|
| creative-writing | 2000 | Turn 1: 0 output tokens — all spent thinking |
| doc-summary | 150 | Turn 1: 0 output tokens |
| ops-agent | 500 | Turn 1: 0 output tokens |
| prefill-test | 150 | Turn 1: 0 output tokens |

For comparison, the daily driver answers creative-writing turn 1 in **520 output
tokens** inside the same 2000 cap — plenty of headroom. UD-6bit's thinking is
dramatically more verbose on the *same prompts*: it consumes the full budget on
`<think>` before ever reaching an answer, at every cap from 150 to 2000. This
matches Phase 1's `code_second_largest` result (1023/1024 tokens all thinking,
no answer emitted).

**This is a standalone disqualifier for realistic chat/agentic use**, independent
of whatever Phase 2 accuracy turns out to be: at the token budgets a real turn
uses (150–2000), UD-6bit doesn't produce output at all. Phase 2's tool-calling
calls succeed only because that harness allows much larger completions (seen:
c=65–1007 tokens per call) — there's no equivalent budget ceiling there.

No gen/effective t/s numbers were recoverable from this sweep (0 output tokens
→ undefined tok/s). Phase 1's raw ~15.8 t/s single-stream number stands as the
only throughput data point.

### Phase 2 — Cheap signals

First attempt was run against the wrong baseline framing and stopped by the
user mid-jdhodges (28/40, running ~93% cumulative, no FAIL pattern suggesting
a broken template — legitimate partial data, just not a clean summary). Restart
pending under the corrected framing; scores compare directly against the
27b@6bit anchors above (jdhodges 95%, veerman 83.3%, HumanEval 93%, MMLU 88%).

### Phase 3 — Terminal-Bench
_gated on Phase 2_

## Verdict
_pending_
