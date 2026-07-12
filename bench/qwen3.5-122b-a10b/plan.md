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

## First-session results (2026-07-10, MTP OFF baseline)

Model already staged on disk (`qwen3.5-122b-a10b-mtp`, 75.23 GB, arch
`qwen35moe`) → Gate 0 done, Gate 1 confirmed on load.

**Gate 1–2 — load + memory + speed.** Loaded sole-model (evicted
`qwen3.6-27b-ud-mlx@6bit`) at ctx 65,536, parallel 4, `--no-speculative-draft-mtp`.
Cold load **20.9 s**, resident **75.23 GB**, IDLE. Estimate at load: 75.14 GiB
total (KV ~5 GiB over weights — the cheap hybrid-attention KV, as predicted).
Soak: **swap 0, no spill, GPU 97 %**, RAM ~107 GB total during gen.

Scenario throughput (`tools/local-llm-bench/bench.py`, no-think via
`BENCH_NOTHINK_PREFILL=1`, gen t/s / eff t/s) vs the `qwen3.6-27b` MLX-6bit
baseline:

| Scenario | 27B gen / eff | 122B gen / eff | speedup |
|---|---:|---:|---:|
| creative-writing | 20.7 / 19.9 | **37.8 / 36.1** | ~1.8× |
| doc-summary | 20.2 / 11.2 | **39.6 / 23.2** | ~2× |
| ops-agent | 20.0 / 16.2 | **35.6 / 20.1** | ~1.8× |
| prefill-test | 20.4 / 4.0 | **35.8 / 7.5** | ~1.8× |

**A 122B model serves ~2× faster than the 27B incumbent** — the 10B-active MoE
payoff. Prefill (eff on prefill-test) is also ~2× better; no prefill-collapse
tarpit. speed_probe sustained-gen (thinking ON) ≈ 36–37 t/s; no-think probe
answers are too short (2–67 tok) to measure sustained decode — the scenario
bench is the authoritative speed source.

**Gate 3 (partial) — fast signals: tool-calling (thinking ON, model default).**

| Suite | 122B | 27B incumbent |
|---|---|---|
| jdhodges (40) | **95 % (38/40)**, 9.6 min, 26.2 t/s | 95 % (38/40) |
| veerman (12) | **83 % (10/12)**, 3.1 min, 30.0 t/s | 83.3 % |

Tool-calling is a **dead tie** — saturated; scale adds nothing here (expected).

**Interim read:** challenger wins decisively on speed (~2× on both decode and
prefill) and matches on tool-calling. The slot decision now rests entirely on the
**knowledge + LCB ladder** (MMLU/MATH/DROP/HumanEval/LCB-50, thinking ON) — the
`+2 pp knowledge` or `LCB ≥ 68 %` bar in the decision rule. That leg is the
expensive one (thinking-on, multi-hour) → run via detached driver, not foreground.

### Harness fixes made this session (both env-gated, inert by default)

- `tools/local-llm-bench/bench.py`: added request-level `BENCH_NOTHINK_PREFILL=1`
  no-think prefill (pre-closed `<think>\n\n</think>` as a trailing assistant turn,
  injected only into the request, not persistent history). This checkout's bench.py
  only had the `--no-think` **template-patch** path, which silently no-ops on a GGUF
  (no external `chat_template.jinja`) → the qwen3.6-mtp study's documented
  `BENCH_NOTHINK_PREFILL` mechanism did not actually exist here.
- `tools/local-llm-bench-m4-32gb/scripts/speed_probe.py`: same env-gated prefill,
  mirroring bench.py, so the probe can run clean no-think.

## Second-session results (2026-07-11, quality ladder, THINKING ON)

Detached driver (`scripts/run-122b-full-ladder.sh`, `nohup` + Python `os.setsid()`
— macOS lacks `setsid`), sole-model, ctx 65k, `max-tokens 65536`,
`BENCH_TIMEOUT=3600`, thinking ON (no prefill). Decode held ~35–37 t/s, swap 0,
no spill throughout.

| Bench | 122B (Q4_K_S) | 27B (6-bit) | Δ |
|---|---|---|---|
| HumanEval (100) | **96 %** | 93 % | **+3** |
| MMLU (100) | 87 % | 88 % | −1 |
| DROP (100) | 89 % | 90 % | −1 |
| MATH | ~87 % (60/69, **skipped** at Q69) | 88 % | ~−1 |
| **LiveCodeBench-50** | **62 % (31/50)** | 62 % (31/50) | **0 — exact tie** |

**LCB is a statistical dead heat — identical per difficulty:** easy 10/15=10/15,
medium 14/23=14/23, hard 7/12=7/12. Same-question head-to-head traded **3 wins
each way**; net identical. Full 50-question table reproducible from the matched
`lcb_question_id` join of the two runs' jsonl logs.

**The 122B's one real weakness: truncation.** 4 of its LCB questions spiralled
past the 65k cap (Q8, Q23, Q44, +1) — 30–36 min / ~65k thinking tokens each,
graded fail. Its longer reasoning chains convert would-be passes into fails; at a
tighter output budget its LCB would drop below the 27B's. Same failure mode the
27B shows on GPQA, but here it bites coding. LCB leg wall-clock ~8 h; MATH was
the other slow leg (deep reasoning, some Qs 10 min) and was cut at Q69 by user
request to reach LCB sooner.

**Verdict (quality, pre-Terminal-Bench): quality TIE, ~2× faster.** HumanEval a
hair up, knowledge a hair down (−1 pp across MMLU/DROP/MATH), hard-coding signal
(LCB) exactly even. Combined with the first-session ~2× speed win, the 122B is a
**faster sidegrade, not an upgrade** — not enough quality gain to justify evicting
`coder-next` for a sole-model 75 GB planner, but a legitimate **fast planning
alternate** when raw speed beats the 27B's 22.8 GB pairing flexibility. Leaning
🟡 **marginal — 27B keeps the Planning slot** pending the Terminal-Bench agentic leg.

### Terminal-Bench 2.0 — FINAL (2026-07-12, terminus-2, Docker, thinking ON)

**22 / 89 = 24.7%** (official harbor mean reward 0.247), 0.5× agent-timeout cap,
~18.5 h wall-clock. Rig standing:

| Model | T-Bench | note |
|---|---|---|
| `qwen3-coder-next` | **32.6 %** | agent-slot winner, ~68 t/s, non-thinking |
| `qwen3.6-27b` | 31.5 % | #2, 6× slower decode |
| `qwen3.6-35b-a3b@6bit` | 28.1 % | #3 |
| `minimax-m2.5` (both GGUF quants) | 25.8 % | #4 |
| **`qwen3.5-122b-a10b`** | **24.7 %** | **#5 — mid-pack; above Gemmas, below MiniMax + the Qwen thinkers** |
| `gemma-4-31b` | 22.5 % | best Gemma (LCB lead doesn't transfer) |
| `gemma-4-26b-a4b@6bit` | 21.3 % | LCB ceiling 80 %, but weak agent |

**Failure analysis** (why 67 fails): median episode count is **10 for both PASS
and FAIL** → failures are *wrong/incomplete solutions that fail the verifier*,
not timeouts or infra. Three modes: (1) dominant — agent terminates believing it
succeeded but output fails unit tests (`chess-best-move` wrong answer;
`db-wal-recovery` 0/7, never produced valid output); (2) partial completions
graded as full fails (`build-cython-ext` 7/11 tests pass → still FAIL; the 24.7 %
*understates* work done); (3) minority thrash-to-timeout on brutal tasks
(`build-pov-ray` 128 episodes). No `AgentTimeoutError`/context/connection errors;
the litellm "model isn't mapped" warning was cosmetic. Root cause: capable
**one-shot reasoner, weak agentic executor** — over-thinks, under-executes;
same trait as its LCB truncations.

## FINAL VERDICT — 🔴 NO-GO for the Planning slot; `qwen3.6-27b` keeps it

Complete campaign scorecard (thinking ON, temp 0, seed 42, ctx 65k):

| Bench | 122B Q4_K_S | 27B 6-bit | Δ |
|---|---|---|---|
| HumanEval | 96 % | 93 % | +3 |
| MMLU | 87 % | 88 % | −1 |
| DROP | 89 % | 90 % | −1 |
| MATH | ~87 % (60/69) | 88 % | ~−1 |
| LCB-50 | 62 % | 62 % | **0 (exact tie, identical per difficulty)** |
| Terminal-Bench | **24.7 %** | 31.5 % | **−6.8** |
| decode speed | ~36 t/s | ~20 t/s | **~2× faster** |

**The 122B is a faster sidegrade, not an upgrade.** One-shot quality is a wash
(±3 pp everywhere, LCB an exact tie), decode is ~2×, but it is a **distinctly
weaker agent** (−6.8 pp T-Bench) and its long-thinking-chain trait is an active
liability in loops (4 LCB truncations, 128-episode T-Bench thrash). It also forces
**sole-model residency (75 GB)** where the 27B swaps in at 22.8 GB and pairs with
the coder stack. Scale on a one-generation-older model (Qwen3.5) does **not** beat
the newer, smaller Qwen3.6 — the campaign's headline lesson: **test the newest
generation, not the biggest old model.** Only niche: a fast one-shot planner on a
dedicated box where 2× speed beats pairing flexibility — too narrow for a slot.

**SWE-with-agents stack unchanged:** `coder-next@4bit` (agent loop) +
`gemma-4-26b-a4b@6bit` (single-shot code ceiling) resident; `qwen3.6-27b`
swap-in planner. 122B stays on the bench.

## History

- **2026-07-12** — Campaign COMPLETE (~37.5 h total). Terminal-Bench **24.7 %**
  (22/89), #5 on rig. **Final verdict: 🔴 NO-GO** — faster sidegrade, weaker agent;
  `qwen3.6-27b` keeps the Planning slot. Unsloth-catalog cross-check: no new
  Qwen3.6 (only 27B/35B-A3B, both benched) or SWE-relevant Gemma (new 12B-Unified
  is audio/edge) warrants testing.
- **2026-07-10** — Plan written; candidate staged on disk. **First session:**
  Gate 0–2 + fast tool-calling done. Speed ~2× the 27B (gen + prefill),
  tool-calling ties (95 % / 83 %). Sole-model 75 GB, 0 swap. Fixed the no-think
  prefill mechanism in bench.py + speed_probe.py. Knowledge/LCB ladder (the
  decision gate) still pending — detached-driver leg.
