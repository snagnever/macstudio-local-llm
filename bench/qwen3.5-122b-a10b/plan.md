# 2026-07-10 — Qwen3.5-122B-A10B (MTP GGUF): planning-slot challenger

## Context

The Planning slot is held by [`qwen3.6-27b`](../../docs/models/qwen3.6-27b.md)
(MLX 6-bit dense, 22.80 GB): knowledge avg **85.8 %** (top of rig), LCB **62 %**,
but ~20 t/s decode and a 67 s prefill collapse at 8.5k. The slot's own rationale
("you wait once for a plan") is exactly where a bigger, sole-model contender is
tolerable — and there is visible quality headroom above the 27B (LCB ceiling on
the rig is 80 %; GPQA raw 70 %).

The two previous big-model attempts both lost to the same constraint — **quant
quality at the size that fits, not param count**:

- [`minimax-m2.5`](../../docs/models/minimax-m2.5.md) (229B MoE): had to run at
  IQ2/Q3, sole-model, T-Bench NO-GO on memory; never contested Planning.
- [`deepseek-v4-flash`](../../docs/models/deepseek-v4-flash/README.md): fit only
  at 2-bit DQ → degeneration loops.

**This candidate dodges that trap.** 122B total / **10B active** fits at an
honest 4-bit:

| Field | Value | Source |
|---|---|---|
| Model | [unsloth/Qwen3.5-122B-A10B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.5-122B-A10B-MTP-GGUF) | HF card (fetched 2026-07-10) |
| Quant (this campaign) | **UD-Q4_K_S, 73.4 GB** (optional quality bump: UD-Q4_K_XL, 78.6 GB) | HF card |
| Architecture | Hybrid `16 × (3 × (Gated DeltaNet → MoE) → 1 × (Gated Attention → MoE))`, 48 layers; MoE 256 experts, 8 routed + 1 shared; attention 32 Q / **2 KV** heads @ dim 256 | HF card |
| Native context | 262,144 (1M via YaRN); run locally at 65,536 | HF card / local convention |
| MTP | Draft head in the GGUF; card claims ~1.5–2× decode | HF card |
| Vendor sampling | thinking: `temp=0.6, top_p=0.95, top_k=20`; non-thinking: `temp=0.7, top_p=0.8, top_k=20` | unsloth docs |

Family notes that transfer: same hybrid DeltaNet layout as the benched
`qwen3.6-27b` / `qwen3.6-35b-a3b` → KV is cheap (2 KV heads, ~¼ of layers full
attention). The MTP GGUFs from the [Draft MTP study](../qwen3.6-mtp/plan.md)
loaded in LM Studio under arch tag `qwen35` with a working **Draft MTP** toggle
— this model should take the same path (gate 1 verifies).

### The question this campaign answers

**Does a one-generation-older model at 4.5× the total params displace
`qwen3.6-27b` from the Planning slot?** Scale vs. generation is a real matchup,
not a guaranteed win. And the challenger carries a workflow tax the incumbent
doesn't: at 73.4 GB it is **sole-model only** — every planning session evicts
`coder-next` and pays a multi-minute warm load each way (MiniMax at 98.7 GB took
~5 min). The quality delta has to pay for that.

### Expected speed (why this is cheap to bench)

10B active @ ~4.5 bpw ≈ 5–6 GB touched per token → **~35–45 t/s** expected
(MiniMax M2.5, similar active footprint, held 36.8 t/s). That is ~2× the
incumbent *before* MTP. The full gate ladder should run overnight, not the 27B's
37.6 h.

### Decisions (baked in)

- **Harnesses:** existing only — `bench2.py`, `tool_call_bench.py`,
  `speed_probe.py`, `tools/local-llm-bench/bench.py` (scenario throughput). No
  new scripts.
- **Bench config:** temp 0, seed 42, ctx **65,536**, `--max-tokens 65536`
  (thinking model — the 27B's GPQA truncation lesson applies from day one),
  `BENCH_TIMEOUT=3600` unnecessary at ~40 t/s but set anyway for spiral safety.
- **Thinking stays ON.** This is a Planning-slot audition; thinking is the
  product. No `--no-think` surgery needed.
- **MTP OFF for all quality benches.** Quality ladder runs one variable
  (model+quant); the MTP speed study is a separate leg with only the toggle
  flipped — same isolation discipline as the [qwen3.6 MTP study](../qwen3.6-mtp/plan.md).
- **Scope discipline:** the expensive tail (GPQA, Terminal-Bench, MTP speed leg)
  is **not committed up front** — it runs only if the cheap gate earns it.

## Gate ladder

### Gate 0 — download (~73.4 GB)

```bash
lms get unsloth/Qwen3.5-122B-A10B-MTP-GGUF@UD-Q4_K_S   # or hf download
```

Record the pinned HF revision at download time (model-doc convention).

### Gate 1 — loadability + Draft MTP toggle

Load in LM Studio, ctx 65,536, sole-model (evict everything first).

- ✅ pass: arch tag recognized (expect `qwen35`), model answers 2+2 warmup,
  **Draft MTP toggle present** in load options.
- Record: exact `GET /v1/models` API id (needed verbatim for `--model`), load
  time cold + warm, resident GB at idle.
- 🔴 fail (arch unsupported): park campaign, file under runtime-blocked like
  Mellum; check for LM Studio runtime update before building llama.cpp MTP
  branch from source.

### Gate 2 — sole-model memory soak (MiniMax pattern)

```bash
export LMSTUDIO_URL=http://127.0.0.1:1234/v1
cd tools/local-llm-bench-m4-32gb
python3 scripts/lms.py check
python3 scripts/speed_probe.py <api-id> results/speed_probe   # sustained-gen soak
```

- Watch resident + peak + swap (macmon telemetry per the MiniMax runs). Expect
  ~74–78 GB resident at 65k ctx given the cheap hybrid KV.
- ✅ pass: no swap growth, no queue stall, sustained gen ≥ ~30 t/s.
- Record the speed number — it's also the "is planning wall-clock acceptable"
  input.

### Gate 3 — cheap quality ladder (the decision gate)

```bash
python3 scripts/bench2.py mmlu          --examples 100 --model <api-id> --max-tokens 65536
python3 scripts/bench2.py math          --examples 100 --model <api-id> --max-tokens 65536
python3 scripts/bench2.py drop          --examples 100 --model <api-id> --max-tokens 65536
python3 scripts/bench2.py humaneval     --examples 100 --model <api-id> --max-tokens 65536
python3 scripts/bench2.py livecodebench --examples  50 --model <api-id> --lcb-version release_v6 --max-tokens 65536
python3 scripts/tool_call_bench.py --model <api-id> --suite both --base-url "$LMSTUDIO_URL"
```

Incumbent's numbers to beat (`qwen3.6-27b`, same config): MMLU 88, MATH 88,
DROP 90, HumanEval 93, **LCB 62**, jdhodges 95 / Veerman 83.3.

**Decision rule:**

- 🟢 **GO (contests the slot):** knowledge subset avg (MMLU/MATH/DROP) **≥ +2 pp**
  over the 27B's same-three avg (88.7), **or** LCB **≥ 68 %** (+6 pp — the same
  margin that made the 27B displace coder-next on correctness). Sole-model tax
  demands a clear win, not a tie.
- 🟡 **MARGINAL:** within ±2 pp — record, keep the 27B, note the challenger as
  a "big-context planning alternate" only if Gate 2 speed was strong.
- 🔴 **NO-GO:** below the 27B on both axes → the generation gap beat scale;
  document and stop. No tail.

### Gate 4 — earned tail (only on 🟢)

1. **GPQA** `--examples 100 --max-tokens 65536` (the 27B's raw 70 % had 15
   truncations at 32k; run at 65k from the start).
2. **MTP speed leg:** scenario A/B via `tools/local-llm-bench/bench.py`, same
   protocol as [qwen3.6-mtp](../qwen3.6-mtp/plan.md) — toggle only, draft
   depth 2 first (prior verdict: depth 2 optimal, structured workloads +15–28 %,
   creative −8 %; confirm the profile holds at 122B).
3. **Planning-shaped smoke test:** one real design-doc prompt at 65k ctx,
   wall-clock vs the 27B end-to-end (load + prefill + think + answer) — the
   number that actually decides daily-driver ergonomics.
4. Model doc: `docs/models/qwen3.5-122b-a10b.md` per template; update
   `docs/local-llm-reference.md` Planning row if the slot flips.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| LM Studio runtime lacks the 122B MTP arch variant | Gate 1 is first and costs only the download; llama.cpp MTP branch from source is the documented fallback |
| Thinking spirals at 65k even at ~40 t/s (~27 min/spiral) | `BENCH_TIMEOUT=3600`; detached driver (`nohup`, PPID=1) for any leg > 2 h — harness kills backgrounded `bench2.py` at ~2–3 h |
| Q4_K_S quality vs the incumbent's 6-bit (two knobs: scale *and* quant) | Acknowledged in the verdict write-up; if MARGINAL and curious, UD-Q4_K_XL (78.6 GB) is the one-step quant probe |
| 73.4 GB + KV creeps past ~80 GB under parallel-slot prefill spikes | Soak at ctx 65k in Gate 2 before any bench; fall back to ctx 32,768 for the knowledge subset (they don't need 65k prompt room, only output cap) |
| Sole-model residency blocks the rig for the whole ladder | Run model-major and overnight; nothing else scheduled on the rig during the campaign |

## History

- **2026-07-10** — Plan written. Candidate identified (unsloth
  Qwen3.5-122B-A10B-MTP-GGUF UD-Q4_K_S, 73.4 GB); gates defined; awaiting
  Gate 0 download.
