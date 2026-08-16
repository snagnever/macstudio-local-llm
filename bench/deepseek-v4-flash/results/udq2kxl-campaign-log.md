# UD-Q2_K_XL campaign log

Running record for the DeepSeek-V4-Flash **UD-Q2_K_XL** (Unsloth, 96.8 GB, 3 shards)
quant A/B vs the teamblobfish **IQ2_XS-XL** baseline. Plan:
[plan-udq2kxl.md](../plan-udq2kxl.md). Server recipe identical to baseline except
model file + alias `deepseek-v4-flash-udq2kxl` (llama-server 2.24.0, `--no-repack
-c 32768 -np 1 -ngl 999`, :1235, temp 0, thinking off).

Baseline to beat (IQ2_XS-XL, 2026-07-05): jdhodges 87.5%, Veerman 58.3%,
HumanEval 88.0%, LCB v6 86% partial (6/7, **never finished**), ~10 t/s, 82.3 GB.

---

## Task 1 — preflight + speed probe (2026-07-12)

**Preflight:** 323 GB disk free (≥150 gate ✅); sole-model (no mlx_lm.server, LM
Studio empty) ✅; server healthy on :1235 ✅.

**Thinking off — confirmed.** All three probe questions emitted **0 reasoning
tokens**; output goes straight to the answer (sky-blue check: direct one-sentence
answer, no `<think>` block). So effective throughput = raw throughput, same as the
IQ2_XS-XL GGUF path — no reasoning tax.

**Speed probe** (`speed_probe.py`, temp 0, warmup 4.2s):

| Question | tokens | elapsed | tok/s | answer |
|---|---|---|---|---|
| trivial (2+2) | 26 | 3.65s | 7.1 | `4` ✅ |
| mmlu_atmosphere | 49 | 5.65s | 8.7 | `A` ✅ |
| code_second_largest | 224 | 21.66s | **10.3** | valid Python ✅ |

The short gens are dominated by per-request overhead; the 224-token coding gen is
the clean read: **10.3 tok/s**, matching this session's 1,800-token smoke
(10.9–11.2 t/s) and the IQ2_XS-XL baseline (~10 t/s). **No speed regression from
the larger quant.**

**Memory:** 92.0 GB resident (llama-server RSS) during the probe; system RAM 122.9
GB, swap 0.2 GB, **no spill**, GPU 96%, 37 W. Sits +9.7 GB over the 82.3 GB
baseline — expected for the +16 GB-on-disk quant, still clear of the 128 GB
ceiling with no swap pressure.

**Verdict so far:** speed and memory are a wash-to-slightly-heavier vs baseline, as
predicted — the quant has to earn its +9.7 GB on *quality* (Tasks 3/5/6). Raw:
`tools/local-llm-bench-m4-32gb/results/speed_probe/deepseek-v4-flash-udq2kxl_20260712_193227_*`.

## Task 2 — context-vs-speed sweep (2026-07-12)

Standalone probe (`udq2kxl_ctx_probe.py`) against the running llama-server; per
depth a synthetic prompt + 256-token gen at temp 0. `context_speed_bench.py`
couldn't be used — it loads via the LM Studio API, blocked for `deepseek4` (no
`--no-repack` in `lms load`).

| prompt tokens | prefill t/s | decode t/s | RSS GB |
|---|---|---|---|
| 502 | 161.3 | 10.9 | 92.3 |
| 1,870 | 209.9 | 11.0 | 92.3 |
| 3,718 | 228.4 | 10.9 | 92.3 |
| 7,414 | 214.4 | 10.4 | 91.0 |
| 14,782 | 182.1 | 10.2 | 91.1 |
| 22,150 | 157.0 | 9.9 | 91.1 |
| 27,694 | 145.7 | 9.4 | 91.2 |

**Decode holds up under depth: 10.9 → 9.4 t/s, only a 13.8% drop across the full
0→27.7k context** — a gentle linear decline, no collapse. Prefill peaks ~228 t/s
mid-range and eases to ~146 t/s deep (still fast; a 28k prompt prefills in ~3 min).
RSS is flat at ~91–92 GB (KV for 32k is reserved at load, so depth doesn't grow
resident memory). Terminal-Bench viability (Task 6) is fine on the speed axis —
even at 84%-full context the model sustains >9 t/s.

**Probe gotcha (fixed):** the first run tripped "Context size has been exceeded" at
the two deep points because every prompt shares the same filler prefix and
llama-server's prompt-cache prefix reuse accumulated KV across requests. Fix:
`cache_prompt: false` per request (now baked into the committed script). Raw:
`bench/deepseek-v4-flash/results/udq2kxl-ctxspeed.json`.

## Task 3 — cheap quality signals (2026-07-12)

All three ran clean (rc=0), temp 0 / seed 42, sole-model on :1235. jdhodges 14.7
min, Veerman 6.8 min, HumanEval 1h43m (faster than the ~3h budget).

| Signal | UD-Q2_K_XL | IQ2_XS-XL baseline | Δ |
|---|---|---|---|
| jdhodges tool-calling (40) | **90.0%** (36/40) | 87.5% (35/40) | +2.5 |
| Veerman tool-calling (12) | **75.0%** (9/12) | 58.3% (7/12) | **+16.7** |
| HumanEval (100) | **95.0%** (95/100, 0 trunc) | 88.0% (88/100) | **+7.0** |

**UD-Q2_K_XL beats the baseline on all three signals — a clean sweep.** The two
big jumps (Veerman +16.7, HumanEval +7.0) are exactly where a dynamic quant should
help: Unsloth pins sensitive layers at higher precision, and Veerman's agentic
proactivity + HumanEval's longer-form code generation are the workloads most
sensitive to the 2-bit quality floor that hurt the flat IQ2_XS-XL quant. HumanEval
95% notably clears coder-next (89%) too — the best local coding result on this rig
in that suite. Raw:
`tools/local-llm-bench-m4-32gb/benchmarks/runs/{toolcall_jdhodges,toolcall_veerman,humaneval}_deepseek-v4-flash-udq2kxl_2026071220*`.

## Task 4 — decision gate (2026-07-12): **PROCEED** ✅

Gate rule: "UD ≥ baseline on ≥2 of 3 signals, none catastrophically down → proceed
to LCB + Terminal-Bench." Result: **3 of 3 up**, two by wide margins, none down.
The +9.7 GB memory cost is already justified on tool-calling + HumanEval alone. The
quant is a genuine quality upgrade, not a sidegrade. Proceed to **Task 5 (LCB v6)**
and **Task 6 (Terminal-Bench 2.0)** — and the strong HumanEval/Veerman lift makes
those two worth the overnight/multi-hour spend. Provisional trajectory: **UPGRADE**
(pending LCB/TBench not regressing).

## Task 5 — LiveCodeBench v6 (50) (2026-07-13)

Ran 629 min (~10.5h), temp 0, max_tokens 32768, sole-model on :1235.

- **RAW score: 56.0% (28/50)** — `livecodebench_deepseek-v4-flash-udq2kxl_20260713_084306_summary.json`.
- **Cache-adjusted: 73.7% (28/38)** — excluding the 12 HTTP-500 empties (see below).

**Failure breakdown (22 fails):** 12 HTTP-500 empties · ~5 degeneration spirals
(TRUNC at the 32,768-token cap) · ~5 genuine wrong-answers.

**The 12 empties are a runtime artifact, not the model returning blank text.** Each
is `finish_reason='error'`, `HTTP Error 500`. Server log:
`update_slots: decode() failed: Context size has been exceeded` + `failed to find
free space in the KV cache ... off = 0`. Mechanism: a hard case spirals and
generates ~32k tokens, filling the single `-np 1` slot's entire KV cache to the
`-c 32768` ceiling; that sequence's KV **isn't evicted before the next request**,
so the next case's fresh prefill (off=0) finds zero free cells and 500s. The
instant (~1s) empties sit directly after spirals (Q9→Q10, Q11→Q12, Q19→Q20); the
two slow empties (Q44 20min, Q46 50min) ground through the server's
`1024→…→1` batch-shrink retry loop before giving up. On a clean cache several of
those 12 would have been real attempts.

**Read:** the raw 56% is ~17 pts depressed by this KV-eviction bug. Even adjusted,
73.7% sits **below the rig LCB ceiling** (`gemma-4-26b-a4b@6bit` 80% — at 21.8 GB
and 80 t/s). The ~5 genuine spirals are real 2-bit degeneration on hard long-form
coding — the recurring DeepSeek-V4-Flash 2-bit story, surviving the dynamic quant.
So **LCB is this quant's weak spot**: mediocre even discounting the artifact, and
the artifact itself only appears because the model spirals. The baseline
IQ2_XS-XL never finished 50 (7/50), so no true A/B — but its reported ~2–3% empty
rate vs UD's 24% raw suggests UD may spiral more, or just drew a bad hard-case mix.

**Mitigation available (not yet run):** restart-server-per-case (repo has the OOM-era
pattern) or a per-request KV clear would remove the 12 artifact 500s and yield a
clean ~74% model-quality read — at ~4h server-warmload overhead. Decision deferred:
worth it only if the verdict hinges on LCB, which HumanEval 95% + tool-calling
already outweigh. Raw:
`tools/local-llm-bench-m4-32gb/benchmarks/runs/livecodebench_deepseek-v4-flash-udq2kxl_20260713_084306*`.
