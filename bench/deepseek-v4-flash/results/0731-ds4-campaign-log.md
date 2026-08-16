# DeepSeek-V4-Flash-0731 on ds4 — campaign log

Running record for the **0731** checkpoint on the **ds4 / DwarfStar** Metal
engine. Plan: [plan-0731-ds4.md](../plan-0731-ds4.md).

Baseline to beat (original checkpoint, Unsloth 2-bit on `llama-server` 2.24.0,
2026-07-12): **10.3 t/s**, 92.0 GB RSS, ctx 32,768, jdhodges 90.0% /
Veerman 75.0% / HumanEval 95.0% / LCB v6 56.0% raw.

---

## Task 1 — engine build + speed probe (2026-08-15)

**Build:** `vendor/ds4` at upstream `main`, `make` → clean in 17 s
(`ds4`, `ds4-server`, `ds4-bench`, `ds4-eval`, `ds4-agent`). No patches needed —
in contrast to the mlx-lm path, which required two.

**Weights:** `antirez/deepseek-v4-gguf` (the engine author's own repo, 1.27 M
downloads) rather than the `ox-ox` mirror (9 k). Same quant recipe, but the
author's file carries a `-fixed-` suffix the mirror lacks.
`...chat-v2-imatrix-fixed-0731.gguf`, 97,591,747,456 B — byte-exact against the
HF blob size.

**Load:** cold mmap + Metal residency in **31.6 s** (warm: 0.7 s). No
`--no-repack`, no `-np 1`, no runtime version pin. LM Studio's `qwen3.6-27b`
(22.8 GB, idle) had to be unloaded first.

### Methodology finding: ds4 defaults to thinking ON, and hides the split

`ds4-server` defaults DeepSeek chat requests to high-effort thinking.
`model=deepseek-chat` selects non-thinking. Critically, **ds4 counts reasoning
tokens inside `completion_tokens` but returns no `completion_tokens_details`**,
so the `reasoning_tokens` field every prior bench on this rig relied on reads 0
in *both* modes. It is a false negative, not a thinking-off confirmation.

Detect thinking by token count against identical output instead:

| Question | non-thinking | thinking high | identical final answer? |
|---|---|---|---|
| trivial (2+2) | 1 tok | 62 tok | yes (`4`) |
| mmlu_atmosphere | 1 tok | 41 tok | yes (`A`) |
| code_second_largest | 39 tok | 325 tok | yes (byte-identical) |

**8.3× the tokens for byte-identical output** on the coding question. Worse, at
`max_tokens=2048` the thinking mode burned the entire budget and returned
**0 characters of content** — it never reached the answer. Any bench run against
ds4 defaults would measure a model that never finishes.

### Throughput

The 3-question probe is **not** a valid A/B here: the 0731 model answers
`code_second_largest` in 39 tokens where the baseline took 224, so the run is
per-request-overhead dominated and reads an artificially low 21.9 t/s. Re-measured
with a 2,048-token generation (red-black tree implementation, temp 0):

| Config | tok | elapsed | **t/s** | vs baseline |
|---|---|---|---|---|
| llama.cpp 2.24.0 (baseline, 224 tok) | 224 | 21.7 s | 10.3 | 1.00× |
| **ds4, non-thinking** | 2048 | 61.0 s | **33.6** | **3.26×** |
| ds4, thinking high | 2048 | 60.3 s | 34.0 | (0 chars delivered) |

Decode speed is mode-independent, as expected — same decode loop. What differs
is *effective* throughput. Lands squarely in the 30–34 t/s predicted from memory
bandwidth (M3 Max 27 t/s → M4 Max 546 GB/s → M5 Max 39 t/s).

**Gate (≥ 20 t/s): PASS at 33.6 t/s.**

## Task 2 — memory, DSpark, and context (2026-08-15)

**Residency.** `phys_footprint` reads ~5 GB and is meaningless: ds4 mmaps the
weights as overlapping shared Metal buffers. The server log's planned figure is
the real one.

| Config | KV | buffers | model | **total planned** |
|---|---|---|---|---|
| ctx 65,536 | 0.86 GiB | 0.50 | 90.88 | **92.25 GiB** |
| ctx 262,144 | 2.36 GiB | 2.00 | 90.88 | **95.25 GiB** |
| ctx 65,536 + DSpark | 0.86 GiB | 0.50 | +5.58 | **~97.8 GiB** |

Swap stayed at **0.00 M** throughout. `iogpu.wired_limit_mb` untouched at the
system default (`0`) — no tuning was needed, contrary to the community advice to
raise it.

**Context is nearly free.** 4× the context costs **+3.0 GiB**, thanks to the
compressed-attention KV, and carries **no speed penalty** (33.9 t/s at 256k
allocation vs 33.6 at 64k). The widely repeated "start at 64K, treat 256K as an
experiment" guidance is wrong for this engine on this machine — 256k is the
sensible default. The remaining limit at 1M is prefill *time*, not memory.

**DSpark is not worth it.** Speculative decoding via `--mtp` + `--dspark`:

| Config | t/s | Δ vs no DSpark | memory cost |
|---|---|---|---|
| no DSpark | 33.6 | — | — |
| `--dspark` (default confidence 0.6) | 36.2 / 36.1 | **+7.5%** | +5.58 GiB |
| `--dspark-confidence 0.3` | 34.8 / 34.8 | +3.6% | +5.58 GiB |

+7.5% for 5.58 GiB, against a vendor claim of ~1.9× and third-party claims of
51–400%. Lowering the confidence threshold made it *worse*, so the default is
already the better setting. **Recommendation: run without DSpark** and spend the
headroom on context instead. Not investigated further: whether the gap is low
draft acceptance or a Metal-path limitation — `--glm-mtp-timing` has acceptance
counters but there is no DSpark equivalent exposed.

**Prefill.** A ~32k-token prompt returned in 103.4 s for 9 generated tokens, so
prefill is very roughly **~300 t/s** — above llama.cpp's 146 t/s at comparable
depth. Rough figure from one unmatched probe, not a measurement; the T3 sweep
should replace it. (That probe's *answer* was also wrong — it undercounted 4,000
repeated definitions as 50 — but counting thousands of identical items is a poor
quality signal and should not be read as one.)

### Recommended serve config

```
ds4-server -m <...imatrix-fixed-0731.gguf> --metal -c 262144 --host 127.0.0.1 --port 8000
```

Non-thinking via model id `deepseek-chat`; thinking via `deepseek-v4-flash`.

## Official card cross-check (2026-08-15)

Everything above about thinking modes came from ds4's own `MODEL_CARD.md` and
`--help thinking`, **not** the vendor card. Fetched
[deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731)
afterwards to reconcile. Three corrections:

1. **The `<think>`/`</think>` marker mechanism is ds4's rendering, not the wire
   format.** The vendor ships no Jinja template — control is a Python
   `encoding/` folder driven by two params:
   `encode_messages(messages, thinking_mode=..., reasoning_effort=...)`, where
   `reasoning_effort` ∈ **low / high / max** (not ds4's "Non-think / High /
   Max" labels). The disable levers this campaign uses (`model=deepseek-chat`,
   `think=false`, `thinking={type:disabled}`) are **ds4-server's HTTP mapping**,
   correct for driving ds4 but not the vendor field names — they will differ on
   vLLM/SGLang. The `--ctx >= 393216` Max gate matches the vendor's recommended
   384K (=384×1024) output length for high/max, so that part is consistent.

2. **Sampling: every score here was taken at temp 0; the vendor recommends
   temp 1.0** (`top_p=0.95` agentic, `1.0` otherwise). Temp 0 is defensible for
   a deterministic A/B against the temp-0 baseline, but it is off-spec. The
   original April checkpoint recommended temp 0.6 (per [setup
   doc](../../../docs/models/deepseek-v4-flash/setup.md)); 0731 raised it to
   1.0. **Open question:** Veerman stalled at 75.0% with `veerman_hard` 1/3 —
   the exact agentic-proactivity axis 0731 was supposed to improve — and that
   was measured at temp 0. Worth a temp-1.0 re-run before concluding 0731 did
   not move agentic behaviour. (In thinking mode client sampling is ignored
   anyway, per both cards, so this only bites the thinking-off benches — i.e.
   all of ours.)

3. **DSpark "not worth it" is scoped to ds4 on Metal.** The vendor documents
   DSpark for vLLM (`num_speculative_tokens=7`) and SGLang
   (`--speculative-algorithm DSPARK`), different engines with different
   acceptance behaviour. The +7.5% figure is ds4's `--dspark`, not a verdict on
   DSpark generally.

## Task 4 — cheap quality signals (2026-08-15)

Thinking OFF (`model=deepseek-chat`, verified 1-token `2+2` before the run),
temp 0, sole-model on :8000. All fresh (`carried_over=0`).

| Signal | 0731 + ds4 | baseline (UD-Q2_K_XL, orig ckpt) | Δ | wall clock |
|---|---|---|---|---|
| jdhodges (40) | **97.5%** (39/40) | 90.0% | **+7.5** | 9.6 min |
| Veerman (12) | 75.0% (9/12) | 75.0% | **0.0** | 2.9 min |
| HumanEval (100) | **90.0%** (90/100, 0 trunc) | 95.0% | **−5.0** | 21.4 min |

**Gate (≥2 of 3 at-or-above, none catastrophically down): PASS.** jdhodges up,
Veerman level, HumanEval down 5 — not catastrophic, but a genuine regression,
not noise (5 problems).

Reading the three:

- **jdhodges 97.5%** — best tool-calling result on the rig in this suite, tying
  `qwen3.6-35b-a3b` (98%) and the MLX/DSML peak (98%). The single miss is in
  `multi_tool`; `tool_selection`/`argument_accuracy`/`edge_cases`/`format_compliance`
  all 8/8. This is where 0731's post-training shows up.
- **Veerman flat at 75.0%** — `veerman_action` 6/7, `veerman_restraint` 2/2,
  `veerman_hard` **1/3**. The hard agentic-proactivity cases are untouched. See
  the temp-0 caveat in the cross-check above: 0731 was *advertised* as an
  agentic upgrade, so measuring its headline axis at off-spec temp 0 is the
  weakest part of this campaign. **Flagged for a temp-1.0 re-run.**
- **HumanEval 90.0% (−5.0)** — a real drop, but the comparison is **confounded**:
  the baseline was the Unsloth `UD-Q2_K_XL` recipe on llama.cpp, this is the
  antirez `fixed-0731` mixed 2+4-bit recipe on ds4. Checkpoint, quant recipe,
  and runtime all changed at once, so the −5 cannot be attributed to the
  checkpoint. 0 truncations means it is not degeneration — just 10 wrong
  solutions vs the baseline's 5. Wall clock 21.4 min vs the baseline's 1h43m
  (4.8×) — HumanEval's longer generations sit nearer the 3.26× decode ceiling
  than the short tool-calling suites did.

**Provisional verdict: UPGRADE on tooling, WASH on code.** The runtime win
(3.26×, no workarounds, 256k nearly free) is unambiguous and stands on its own.
The 0731 *checkpoint's* quality delta is muddier: a big tool-calling gain, a
flat agentic axis (measured off-spec), and a confounded code regression. A clean
checkpoint read needs 0731 vs original *on the same engine* — not attempted.

## Task 4b — Veerman at vendor sampling (2026-08-15)

The T4 Veerman ran at temp 0; the 0731 card recommends temp 1.0 / top_p 0.95
(agentic). Veerman is the agentic suite and 0731's headline claim, so re-ran it
on-spec. Temp 1.0 is stochastic on 12 cases → 3 seeds. Raw jsonl confirms
`temperature:1.0, top_p:0.95` were actually sent (the summary JSON drops top_p,
but the request rows carry it). Made `BENCH_TEMPERATURE/TOP_P/SEED`
env-overridable in `tool_call_bench.py`; unset → unchanged temp-0 defaults.

| Run | score | veerman_hard | action | restraint |
|---|---|---|---|---|
| temp 0 (T4) | 75.0% (9/12) | 1/3 | 6/7 | 2/2 |
| temp 1.0 seed 1 | 66.7% (8/12) | 1/3 | 6/7 | 1/2 |
| temp 1.0 seed 2 | 75.0% (9/12) | 2/3 | 6/7 | 1/2 |
| temp 1.0 seed 3 | 83.3% (10/12) | 2/3 | 6/7 | 2/2 |

**Mean at temp 1.0 = 75.0%, identical to temp 0**, with a ±8.3-point spread
(66.7–83.3) that swamps any signal. **Vendor sampling does not unstick Veerman.**
The temp-0 measurement was not the problem — the agentic ceiling is real, and
0731's advertised agentic gains do not show up on this suite at either sampling.

Firmest signal: `veerman_action` is **6/7 in all four runs** — the same single
case fails every time. That is a stable model limitation, not sampling noise.
`veerman_hard` only wobbles 1–2 of 3 (within the seed spread). Closes the T4
caveat: the flat Veerman is genuine, not a temp-0 artifact.

## Task 3 — context-vs-speed sweep (2026-08-15)

ds4-server emits no llama.cpp-style `timings` field, so
[`ds4_0731_ctx_probe.py`](../scripts/ds4_0731_ctx_probe.py) times the client
side via SSE streaming: TTFT ≈ prefill, `(gen−1)/(total−TTFT)` = decode,
`prompt_tokens/TTFT` = prefill t/s (`stream_options.include_usage` recovers
`prompt_tokens`). Each depth uses a unique filler prefix so ds4's prompt cache
cannot inflate a deep read. Thinking OFF (`deepseek-chat`), 256 gen tokens/point.

| prompt tok | prefill t/s | **decode t/s** | TTFT |
|---|---|---|---|
| 510 | 191 | **33.1** | 2.7 s |
| 1,879 | 334 | 32.6 | 5.6 s |
| 3,727 | 336 | 31.9 | 11.1 s |
| 7,423 | 304 | 30.3 | 24.4 s |
| 14,791 | 308 | 29.9 | 48.0 s |
| 22,159 | 306 | 29.2 | 72.5 s |
| 27,703 | 298 | 28.7 | 92.9 s |
| — past what llama.cpp -c 32768 could reach — | | | |
| 44,287 | 284 | 27.2 | 156 s |
| 59,023 | 271 | 26.9 | 217 s |
| 118,015 | 234 | **24.4** | **505 s** |

**Overlay vs the llama.cpp baseline** (`udq2kxl-ctxspeed.json`, decode 10.9→9.4
over 0.5k→27.7k = −13.8%):

- **Decode slope is the same shape, at 3× the height.** ds4 falls 33.1→28.7 over
  the same 0.5k→27.7k span = **−13.3%**, essentially identical to llama.cpp's
  −13.8%. So the 3.26× runtime win is *preserved across depth*, not eroded by
  context — ds4 is 3.0–3.1× the baseline at every overlapping point.
- **It keeps going where llama.cpp stopped.** Still **26.9 t/s at 65k** (−19%)
  and **24.4 t/s at 128k** (−26%) — depths the `-c 32768` config could not reach
  at all.
- **Prefill is consistently higher and holds better:** peaks 336 t/s at 4k vs the
  baseline's 228 peak, and is still 271 t/s at 65k where the baseline had already
  sagged to 146 by 28k.

**The real long-context limiter is prefill *time*, not decode and not memory.**
A 118k-token prompt takes **8.4 min to first token** (TTFT 505 s). Memory at that
depth is a non-issue (T2: 256k KV = +3 GiB), and decode is still usable — but an
8-minute wait before the first token is the practical ceiling for interactive
use. This is why the 1M window is "operationally unwise" on any tier: it is a TTFT
wall, not a RAM wall. For agentic loops with a 20k-token system prompt, budget
~60–70 s of prefill per cold turn.

## Task 4-think — the with-thinking half of the A/B (2026-08-15)

Repeated the three cheap signals with thinking HIGH (`model=deepseek-v4-flash`,
`TOOLBENCH_MAX_TOKENS=16384` so a tool call isn't truncated behind the reasoning,
HumanEval `--max-tokens 32768`). This is the read that lines up with the vendor's
own thinking-mode headline numbers. Max mode is out of scope — it needs
`--ctx >= 393216`, above this 256k server.

| Suite | thinking OFF | thinking HIGH | Δ | wall clock |
|---|---|---|---|---|
| jdhodges (40) | 97.5% (39/40) | **95.0%** (38/40) | **−2.5** | 9.6 → 10.3 min |
| Veerman (12) | 75.0% (9/12) | 83.3% (10/12) | +8.3 | 2.9 → 3.1 min |
| HumanEval (100) | 90.0% (90/100, 0 trunc) | 91.0% (91/100, **3 trunc**) | +1.0 | 21.4 → **106.3 min** |

**Verdict: thinking does not earn its cost on these workloads. Thinking-off is
the right default.**

- **jdhodges −2.5** — reasoning *hurts* direct tool-calling. The extra loss is in
  `multi_tool` (6/8 vs 7/8): deliberation second-guesses a clean parallel call.
- **Veerman +8.3 is within noise, not a real gain.** T4b measured a ±8.3-point
  seed spread on this 12-case suite, and thinking's 10/12 sits at the top of that
  band (the temp-1.0 seeds ranged 8–10/12). `veerman_hard` 2/3 vs 1/3 is one
  case. n=1 in thinking mode (which ignores the seed) cannot distinguish this
  from luck. Not a demonstrated improvement.
- **HumanEval +1.0 at 5× the wall clock**, plus 3 truncations (reasoning spirals
  that never reached code) where thinking-off had 0. Completions ballooned
  (~780–1260 tok vs ~150 thinking-off) — reasoning *is* engaging hard on code, it
  just doesn't convert to correctness on HumanEval's difficulty.

Why the vendor's thinking-mode gains (MMLU-Pro 86, LCB 91.6) don't show here:
those are reasoning-heavy benchmarks (hard math, contest code). Tool-calling and
standard HumanEval don't reward deliberation, so on this rig's cheap-signal suite
thinking is pure tax. **Where thinking might still pay is T5 (LiveCodeBench v6)** —
the one hard-code suite — so run T5 in *both* modes rather than assuming off.

## Task 5 — LiveCodeBench v6 (50), thinking HIGH (2026-08-16)

Ran 234 min (3.9h), thinking HIGH (`deepseek-v4-flash`), max_tokens 32768.

- **RAW score: 78.0% (39/50) — and it is a CLEAN 50: 0 HTTP-500, 0 runtime
  artifacts.** The 11 misses are 6 truncations (reasoning spiralled past the 32k
  cap before finishing code, scored FAIL) + 5 genuine wrong answers.

**The KV-eviction bug is gone.** The runner's post-hoc check found **0 error/500
of 50**, against the baseline's **12/50**. The llama.cpp failure mode — a
spiralled case fills the single `-np 1` slot's KV to the `-c` ceiling and the
next case's prefill finds no free cells → HTTP-500 — simply does not occur: ds4
manages its own KV and evicts between requests. **This is the first trustworthy
LCB read for this model on this rig** — no cache-adjustment asterisk needed.

Against the baseline (UD-Q2_K_XL, thinking-off, llama.cpp):

| | baseline raw | baseline cache-adj | **0731+ds4 think** |
|---|---|---|---|
| score | 56.0% (28/50) | 73.7% (28/38) | **78.0% (39/50)** |
| HTTP-500 empties | 12 | (excluded) | **0** |
| clean 50? | no | no | **yes** |

+22 pts over the baseline's raw 56%, +4.3 over its cache-adjusted 73.7% — and
unlike both, this is a full clean 50. The comparison still changes four things at
once (checkpoint + quant + runtime + thinking), so it is not a controlled
checkpoint read, but the **runtime half is now proven**: the artifact that
depressed every prior LCB number is eliminated.

**Thinking's cost on LCB: 6 truncations.** Token spread across the 50 cases:
median 3,016, mean 8,416, max 32,768 (the cap). Thinking-off never truncated on
HumanEval; here 6 hard cases reasoned past 32k before emitting complete code.
That is the real price of thinking on hard code — a raised cap or a reasoning
budget would recover some of those 6.

**Whether thinking *helped* LCB is still open** — this run has no thinking-off
0731+ds4 counterpart, only the confounded llama.cpp baseline. T4-think showed
thinking loses on tool-calling and is flat on HumanEval; LCB is the one suite
where it plausibly pays, so **T5b (LCB thinking-off, same engine) is the clean
isolation** and the natural next run.

## Status

- [x] T1 — speed probe → **PASS, 3.26×**
- [x] T2 — memory / DSpark / context → no wired-limit tuning needed; skip DSpark; 256k default
- [x] T3 — context-vs-speed sweep → decode slope matches llama.cpp at 3× height; usable to 128k; prefill *time* is the long-context limiter (8.4 min TTFT @118k)
- [x] T4-think — with/without thinking A/B → thinking-off is the right default (jdhodges −2.5, Veerman +8.3 within noise, HumanEval +1.0 at 5× cost)
- [x] T5 — LCB v6 thinking HIGH → **78.0% clean 50, 0 HTTP-500** (baseline had 12); ds4 KV manager kills the eviction bug. 6 truncations = thinking's cost on hard code.
- [ ] T5b — LCB v6 thinking-OFF, same engine → isolate whether thinking helps on the one hard-code suite
- [ ] T6 — Terminal-Bench 2.0
- [x] T4 — cheap quality signals → **PASS** (jdhodges +7.5, Veerman 0, HumanEval −5, confounded)
- [x] T4b — Veerman at temp 1.0 → flat (mean 75.0%, ±8.3); agentic ceiling confirmed, not a sampling artifact
- [ ] T5 — LiveCodeBench v6 (does ds4's KV manager kill the 12 HTTP-500 artifact?)
- [ ] T6 — Terminal-Bench 2.0
