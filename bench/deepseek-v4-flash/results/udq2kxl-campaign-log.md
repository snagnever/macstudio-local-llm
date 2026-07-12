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
