# DeepSeek-V4-Flash-**0731** on **ds4 / DwarfStar** — campaign plan

Started 2026-08-15. Two variables change at once versus every prior
DeepSeek-V4-Flash run on this rig, so the plan sequences them deliberately:

1. **Checkpoint** — `0731` (2026-07-31) replaces the original 2026-04-26 build.
   Same arch (`deepseek4`, 43 layers, 284B/13B active, 1M ctx); the delta is a
   new post-training pipeline aimed at coding, agents, reasoning and tool use.
2. **Runtime** — [`antirez/ds4`](https://github.com/antirez/ds4) (DwarfStar), a
   dedicated C+Metal engine for this model family, replaces `llama-server`.

## Why bother

The llama.cpp path is measured at **10.3 t/s** on this rig
([campaign log](results/udq2kxl-campaign-log.md) Task 1). Published ds4 numbers
on the same memory tier are **27.0 t/s** (M3 Max 128 GB) and **39.4 t/s**
(M5 Max 128 GB @2k ctx). Interpolating by memory bandwidth, the M4 Max
(546 GB/s) should land ~**30–34 t/s** — call it 3× — which is the difference
between "benchable" and "usable as an agent".

Secondary wins ds4 claims that map onto known pain here:

| Known pain (llama.cpp path) | What ds4 offers |
|---|---|
| 12 HTTP-500s in LCB v6 from KV not being evicted between requests | Its own KV manager + disk KV checkpoints |
| `--no-repack` / `-np 1` / 2.24.0 pin, LM Studio-native blocked | Purpose-built loader, no workarounds |
| Tool calling needed a template + parser transplant | Native DSML with OpenAI/Anthropic mapping |
| No speculative decoding | DSpark draft (`--mtp` + `--dspark`) |

## Artifacts

| Item | Path / id |
|---|---|
| Engine | `vendor/ds4` (built 2026-08-15, Metal, clean) |
| Weights | `antirez/deepseek-v4-gguf` → `...Layers37-42Q4KExperts-OtherExpertLayersIQ2XXSGateUp-Q2KDown-AProjQ8-SExpQ8-OutQ8-chat-v2-imatrix-fixed-0731.gguf` (97.59 GB) |
| DSpark draft | `DeepSeek-V4-Flash-DSpark-support-0731.gguf` (5.99 GB) |
| Serve | `scripts/serve-0731-ds4.sh` |
| Speed probe | `scripts/ds4_0731_speed_probe.py` |

Quant choice: the `-fixed-` mixed 2+4-bit build is the quality-first option that
still fits 128 GB — experts in layers 37–42 at Q4_K, other expert layers
IQ2_XXS gate/up + Q2_K down, attention projections / shared experts / output
pinned Q8. Sourced from the engine author's own repo (1.27M downloads) rather
than the `ox-ox` mirror (9k), which ships the same recipe **without** the
`-fixed-` correction. The 86.72 GB `ds4f-q2` is the fallback if residency is
tight; Q4 (164 GB) and MXFP4 (156 GB) do not fit.

## Methodology trap: ds4 defaults to thinking ON

`ds4-server` defaults DeepSeek chat requests to **high-effort thinking**. Every
prior number on this rig was taken with thinking OFF, where the GGUF path emits
**0 reasoning tokens** and effective throughput therefore equals raw
throughput. Comparing ds4-default against those would confound the runtime
change with a reasoning tax.

Levers: `model=deepseek-chat`, `think=false`, or `thinking={type:disabled}`
select non-thinking. The probe measures **both** modes so the comparison is
honest and the reasoning tax is quantified rather than hidden.

## Tasks

- [ ] **T1 — speed probe, both thinking modes.** Same 3 questions as
      `speed_probe.py`; `code_second_largest` (224 tok) is the clean read that
      produced the 10.3 t/s baseline. Record RSS. Gate: non-thinking ≥ 20 t/s,
      i.e. ≥ 2× baseline. Below that, ds4's advantage doesn't survive on M4 Max
      and the campaign stops here.
- [ ] **T2 — residency + DSpark headroom.** `iogpu.wired_limit_mb` is at the
      system default (`0`) and the prior run peaked at 92.0 GB RSS with zero
      swap. Weights are +6.7 GB over that; DSpark adds ~6 GB more. Measure RSS
      and swap with and without `--dspark`. Do **not** raise the wired limit as
      a first move — fall back to `ds4f-q2` (86.72 GB) if pressure goes amber.
- [ ] **T3 — context-vs-speed sweep.** Reuse the `udq2kxl_ctx_probe.py` depths
      (0.5k → 27.7k) for a direct overlay on the llama.cpp curve
      (10.9 → 9.4 t/s, −13.8%). Then extend past 32k, which the llama.cpp
      config could not reach. Watch prefill especially: sources disagree wildly
      (45 t/s vs 790 t/s), and prefill is what decides agentic usability.
- [ ] **T4 — cheap quality signals.** jdhodges (40), Veerman (12), HumanEval
      (100), thinking OFF, temp 0, against the original-checkpoint bar:
      **90.0% / 75.0% / 95.0%**. This is where the 0731 post-training should
      show up. Gate: ≥ 2 of 3 at or above, none catastrophically down.
- [ ] **T5 — LiveCodeBench v6 (50).** The known weak spot: 56.0% raw / 73.7%
      cache-adjusted, where 12 of 22 failures were the KV-eviction artifact.
      Two independent things could move it — the 0731 post-training and ds4's
      KV management. If the empties vanish, the raw score becomes trustworthy
      for the first time.
- [ ] **T6 — Terminal-Bench 2.0.** Only if T4/T5 hold. Reuse
      [`bench/terminal-bench/plan-ds4-udq2kxl-remote.md`](../terminal-bench/plan-ds4-udq2kxl-remote.md),
      repointing the LAN serve step at `ds4-server` (note: that plan's
      `ds4-udq2kxl` naming refers to *DeepSeek 4* the model, not this engine —
      an unfortunate collision now that `ds4` is also a runtime).

## Reproducibility note (found 2026-08-15)

`scripts/run-udq2kxl-speed-probe.sh` loads
`DeepSeek-V4-Flash-UD-Q2_K_XL-00001-of-00003.gguf`, but that file is **no longer
on disk**; what remains under `unsloth/DeepSeek-V4-Flash-GGUF/` is
`UD-IQ2_XXS` (~90.86 GB), with shards 1 and 3 dated 2026-07-12 — i.e. still
downloading while the campaign ran — and shard 2 re-fetched 2026-08-09. No
server log preserved the loaded path, so this is inference, not proof. The most
likely reading is that the campaign results are correctly labelled UD-Q2_K_XL
and the weights were deleted afterwards, leaving the campaign **not
reproducible without re-downloading**. Worth resolving before those numbers are
used as a long-lived baseline; a one-line `model_path` echo in future serve
scripts would have settled it.
