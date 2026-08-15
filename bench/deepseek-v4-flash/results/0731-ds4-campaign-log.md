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

## Status

- [x] T1 — speed probe → **PASS, 3.26×**
- [x] T2 — memory / DSpark / context → no wired-limit tuning needed; skip DSpark; 256k default
- [ ] T3 — context-vs-speed sweep (overlay on the llama.cpp curve, extend past 32k)
- [x] T4 — cheap quality signals → **PASS** (jdhodges +7.5, Veerman 0, HumanEval −5, confounded)
- [ ] T4b — Veerman + HumanEval re-run at temp 1.0 (vendor-recommended) — decision pending
- [ ] T5 — LiveCodeBench v6 (does ds4's KV manager kill the 12 HTTP-500 artifact?)
- [ ] T6 — Terminal-Bench 2.0
