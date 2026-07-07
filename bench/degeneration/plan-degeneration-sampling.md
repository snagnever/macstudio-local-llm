# DeepSeek-V4-Flash — can sampling mitigate the 2-bit degeneration loop?

**Date:** 2026-05-31 · **Branch:** `deepseek-v4-tool-dsml` · **Model:** `mlx-community/DeepSeek-V4-Flash-2bit-DQ`

## Why this exists

Our HF posts currently claim *"a full sampling sweep … and **no setting fixes it**."* That claim is
**overstated** — the earlier sweep (`bench/degeneration/scripts/sampling_sweep.py`) tested only
temperature / top_p / min_p / repetition_penalty / frequency_penalty. It **never tested the two
samplers most specifically designed to fight degeneration** that mlx-lm actually supports:

- **XTC** (`xtc_probability` / `xtc_threshold`) — removes the *most probable* tokens, which is exactly
  the class that drives repetition/cliché loops ([oobabooga XTC PR #6335](https://github.com/oobabooga/text-generation-webui/pull/6335)).
- **presence_penalty** — additive penalty on any already-seen token.

This experiment closes that gap with evidence, then we correct the public posts to match whatever we find.

## What the literature says (and the hard ceiling)

- XTC is the standard anti-repetition knob; recommended pairing is **min_p then XTC** (e.g. min_p 0.02,
  xtc_probability 0.5) — which is already mlx-lm's fixed order.
- **DRY** is the strongest anti-*verbatim*-loop tool but (a) **mlx-lm doesn't implement it** (no DRY, no
  `no_repeat_ngram`, no mirostat) and (b) it ["cannot break out of a loop already in progress"](https://github.com/ggml-org/llama.cpp/blob/master/tools/completion/README.md).
- Sampler **order** matters; naive repetition_penalty can *worsen* looping. mlx-lm's order is hard-coded
  (see below) so we can't vary it — but we can confirm whether rep_penalty hurts here.
- The ceiling: samplers only reshape the **output distribution** — [they have no access to the model's
  internal state](https://news.ycombinator.com/item?id=43888112). Low-bit damage is
  [early-emerging "method/execution" corruption](https://arxiv.org/pdf/2505.11574). So the honest split is:

| Goal | Expectation on 2-bit |
|---|---|
| **Break the repetition loop** (terminate, no repeat tail) | **Plausible** — that's what XTC/presence target |
| **Restore coherent, *good* output** | **Unlikely** — that's the quant floor (needs 4-bit) |

**This is the core of the experiment: a config that breaks the loop but emits different garbage is NOT a
win.** We measure both, separately.

## Mechanics verified in mlx-lm source on this rig (these shape the test)

1. **All knobs are per-REQUEST body params** (`server.py` reads `xtc_probability`, `xtc_threshold`,
   `presence_penalty`, `frequency_penalty`, `repetition_penalty`, `min_p`, `top_p`, `top_k`, `seed`, …).
   → **no server restarts between configs.** One server, many requests.
2. **`make_sampler` short-circuits to `argmax` when `temperature == 0`** → top_p/min_p/**XTC**/top_k are
   ALL bypassed at temp 0. **XTC only does anything at temp > 0.** (Penalties are *logits_processors*,
   applied before the sampler, so presence/frequency/repetition DO work at temp 0.)
3. **Sampler order is hard-coded**: penalties → top_p → min_p → XTC → top_k → categorical(temp). Can't
   reorder; the default min_p→XTC is already the recommended order.
4. **Server protects EOS + `"\n"`** via `xtc_special_tokens`, so XTC won't suppress termination.
   `xtc_threshold` must be in `[0, 0.5]`.

## Test matrix (`bench/degeneration/scripts/degeneration_sweep.py`)

Controls + the untested knobs + combos. Each config runs N seeds/prompt at temp>0 (temp 0 is
deterministic → 1 run). Full text of every generation is saved to JSONL for coherence review.

| Group | Configs |
|---|---|
| **Controls** | `ctrl_greedy_t0`, `ctrl_t0.6` (reproduce prior baseline) |
| **XTC** (untested) | `xtc_p0.5_th0.1`, `xtc_p0.5_th0.1_minp`, `xtc_p1.0_th0.1_minp`, `xtc_p0.5_th0.2_minp` |
| **presence_penalty** (untested) | `presence0.5`, `presence1.0`, `presence1.5`, `presence1.0_t0` |
| **frequency_penalty** (higher) | `frequency1.0`, `frequency1.5_t0` |
| **Negative control** | `rep1.3_ctx64` (does rep_penalty worsen it here?) |
| **Combos** | `combo_xtc_presence`, `combo_xtc_freq` |

**Prompts** (long-form, loop-prone): `exec_pt` ("você executa código" — the known reliable trigger),
`story_en` (800-word story), `list_en` (50-item list). Screen uses `exec_pt` only.

**Metrics per run:** `finish_reason`, `completion_tokens`, `tok/s`, `distinct_ratio`, and a
`degenerate` flag (finish=length, or tail-token repeat ≥15/60, or distinct≤25%, or a ≥5× consecutive
3-gram). **Aggregated per config:** `loop%` = fraction degenerate across seeds.

## Procedure

**Phase A — Screen** (≈30–45 min): all 15 configs, `exec_pt`, 3 seeds.
```bash
nohup bash bench/degeneration/scripts/run-degeneration-sweep.sh screen >/dev/null 2>&1 & disown
tail -f bench/degeneration/logs/degeneration-screen.log
```
The runner stops any server, **restores the pristine plain template** (reversible — backups in
`bench/deepseek-v4-flash/logs/_pre-sweep-*.bak`; live config is just the DSML template + a `tool_parser_type` line),
starts one server (cap 2048, temp 0 default), runs the sweep, leaves the server up.

→ Pick **survivors**: configs whose `loop%` is materially below the `ctrl_t0.6` baseline.

**Phase B — Confirm** (survivors only, ≈30–60 min): all 3 prompts × 5 seeds.
```bash
SURVIVORS="xtc_p0.5_th0.1_minp,presence1.0,combo_xtc_presence" \
  nohup bash bench/degeneration/scripts/run-degeneration-sweep.sh confirm >/dev/null 2>&1 & disown
```

**Phase C — Coherence gate** (the decisive read). Loop-broken ≠ good. For each survivor, read the full
generations and judge coherence:
```bash
jq -r 'select(.config=="xtc_p0.5_th0.1_minp" and .degenerate==false) | .content' \
  bench/degeneration/results/degeneration-confirm.jsonl | less
```
Optional automated proxy: spin up a *separate* judge (e.g. the local `qwen3.6-35b-a3b-6bit` on another
port) and have it rate each non-looping output 1–5 for coherence/answer-quality. A survivor only counts
if it's **loop-broken AND coherent**.

## Decision gates → action

| Outcome | Conclusion | Action on the HF posts |
|---|---|---|
| A config is **loop-broken AND coherent** at a real rate | Sampling *can* mitigate it | Replace "no setting fixes it" with the recommended config (params + measured loop% drop) |
| Configs **break the loop but output is incoherent** | Confirms symptom≠cause: stops the loop, can't restore quality | Rewrite the claim precisely: "XTC/presence can suppress the loop but not restore coherence — that's the 2-bit floor" |
| **Nothing** beats baseline (incl. XTC + presence) | Original claim stands — now properly tested | Keep the claim but cite that XTC + presence_penalty were tested too (stronger, honest) |

In every branch we also record: **0 `metal::malloc`** (the OOM fix stays in force) and the **tok/s
overhead** each knob adds.

---

# RESULTS (2026-05-31) — corrected: no setting fixes it, and XTC *backfires*

**Bottom line (rate-measured, real seeds):** the trigger loop is **stochastic (~40–50%)** — it
self-terminates coherently about half the time with plain `temp 0.6`. **No sampling config reliably
lowers that rate**, and the one knob with the biggest effect — **XTC — roughly *doubles* it** (≈87% vs
≈37–50%). This **confirms and strengthens the original "no setting fixes it."** 0 `metal::malloc`
throughout; ~36 tok/s (no throughput regression).

> ### ⚠️ RETRACTION of this section's first draft
> The first write-up of these results claimed an "impossibility finding" — that XTC + min_p + presence
> *fixes* the loop on short prompts but *breaks* factual prompts (a fragile sweet spot). **That was
> wrong**, an artifact of a server bug. The test server (mlx-lm pre-#1331) **ignored per-request
> `seed`** ([#1245](https://github.com/ml-explore/mlx-lm/issues/1245) / fix
> [#1331](https://github.com/ml-explore/mlx-lm/pull/1331)): the compiled sampler captures RNG state, so
> `mx.random.seed()` had no effect — **all 50 multi-seed groups were byte-identical.** Every cell of the
> original verdict matrix was therefore *one deterministic sample*, not a rate. I ported the #1331 fix
> locally (uncompiled sampling for seeded stochastic requests + prompt-cache bypass; verified seeds now
> vary), re-ran with **8 real seeds per cell**, and the picture inverted. The single-sample matrix is
> retracted; the rate table below supersedes it.

### Two upstream bugs surfaced (both already known — do **not** refile)

- **XTC ragged `xtc_special_tokens`** → every XTC request 500s with `ValueError: Initialization
  encountered extra dimension` (server builds `[eos_id, [newline_ids]]`). Already
  [#1257](https://github.com/ml-explore/mlx-lm/issues/1257) + open PRs
  [#1258](https://github.com/ml-explore/mlx-lm/pull/1258)/[#1301](https://github.com/ml-explore/mlx-lm/pull/1301)/[#1176](https://github.com/ml-explore/mlx-lm/pull/1176).
  Local one-char unblock: [`fixes/mlx-lm/mlx-lm-xtc-special-tokens-flatten.patch`](../../fixes/mlx-lm/mlx-lm-xtc-special-tokens-flatten.patch).
- **Compiled sampler ignores per-request seed** → stochastic completions don't vary by seed. Already
  [#1245](https://github.com/ml-explore/mlx-lm/issues/1245) / open PR
  [#1331](https://github.com/ml-explore/mlx-lm/pull/1331). Ported locally to enable the rate run.

### Rate table — 8 real seeds per cell, 95% Wilson CI

XTC = `xtc_probability 0.5, xtc_threshold 0.1`; min_p = 0.02. exec_pt = the loop trigger; qa_fact = a
confident factual prompt (control).

| config | exec_pt loop% [95% CI] | qa_fact loop% | mean tok (exec_pt) |
|---|---|---|---|
| `ctrl_t0.6` (temp 0.6, plain) | **50%** [22, 78] | 0% [0, 32] | 816 |
| `abl_noxtc` (temp 0.7, min_p, presence 1.0, **no XTC**) | **37%** [14, 69] | 0% | 681 |
| `combo_xtc_presence` (temp 0.7, **+XTC**, presence 1.0) | **87%** [53, 98] | 0% | 1341 |
| `abl_presence0.5` (temp 0.7, **+XTC**, presence 0.5) | **87%** [53, 98] | 0% | 1320 |

### What the rates actually show

1. **The loop is a coin-flip, not deterministic.** Plain `temp 0.6` self-terminates coherently ~50% of
   the time on the trigger (a CLEAN sample, distinct 0.70: *"I'm not able to run code… I can help you
   understand code, explain concepts…"*). The earlier "100% loop" was the seed bug handing back one
   unlucky trajectory.

2. **XTC makes it markedly worse, not better.** Both XTC configs loop ~87% vs ~37–50% without XTC —
   roughly **2×**. Removing the dominant token *derails* the model into incoherence/looping more often
   than it rescues it. (n=8 → wide CIs, but the effect is large and identical across both XTC configs,
   and the XTC lower bound (53%) sits above the non-XTC point estimates.)

3. **presence_penalty + min_p (no XTC) ≈ baseline.** 37% vs 50% is within noise — **no reliable
   improvement** from any additive-penalty config.

4. **qa_fact never loops — under *any* config (0/8 everywhere).** The earlier "XTC breaks the factual
   prompt / impossibility tradeoff" was pure seed-artifact: a confident factual answer is simply not
   degeneration-prone here.

5. **Long-form degenerates almost universally — and *no* config helps.** Seeded re-run (8 seeds × 2
   long-form prompts) scored for coherence by an independent judge (Qwen3.6-35B-A3B-6bit, 1–5; failure =
   score ≤ 2), so repetition loops *and* XTC word-salad land on one scale:

   | config | mean | fail (≤2) / 16 |
   |---|---|---|
   | `ctrl_t0.6` (baseline) | 1.3 | **16/16** |
   | `abl_noxtc` (temp 0.7, presence, no XTC) | 1.9 | **15/16** |
   | `combo_xtc_presence` (temp 0.7, +XTC) | 1.7 | **15/16** |

   At 2-bit, long-form output collapses **~94–100% of the time regardless of sampling** — even the plain
   baseline fails 16/16 (vs ~50% on the short trigger). The dominant failure is *structural* repetition
   (the model restarts the story/list from the top); XTC swaps some of that for word-salad. (Methodology
   note: a token-level loop detector **misses** the structural-restart mode — it keeps high word
   diversity, distinct ≈ 0.53 — which is why I used an LLM judge; it caught restarts the heuristic
   scored as "clean.")

### Conclusion → public claim (reverts to, and strengthens, the original)

> *"The looping is stochastic (~40–50% on a trigger prompt) and inherent to the 2-bit quant. A
> rate-measured sweep with real seeds — temperature, min_p, presence/frequency/repetition penalty, and
> XTC — finds **no setting that reliably reduces it**; additive penalties are within noise of baseline,
> and **XTC roughly doubles the loop rate** (it derails the model rather than rescuing it). It's the
> quant, not your setup; the real remedy is a higher-precision quant."*

**Lesson:** the intermediate "XTC fixes it" excursion was a phantom created by a silent seed bug —
caught only by measuring real rates. Single-sample qualitative verdicts on a *stochastic* failure mode
are untrustworthy; rates are mandatory.

## Deliverables

- `bench/degeneration/logs/degeneration-{screen,confirm}.jsonl` — every full generation + metrics.
- A results table appended to this doc (loop% per config + coherence verdict).
- Corrected text in `docs/deepseek-v4-flash-hf-leak-post.md` (§2) and
  `docs/deepseek-v4-flash-hf-pr16-comment.md` if relevant.

## Cleanup (restore tool calling)

```bash
pkill -f mlx_lm.server
bash fixes/deepseek-v4-flash/dsml/install.sh   # re-installs the DSML template + tool_parser_type
```
(Or restore the exact pre-sweep state from `bench/deepseek-v4-flash/logs/_pre-sweep-*.bak`.)

## Scope / honesty notes

- We can't test DRY or sampler-reordering (mlx-lm lacks both) — noted as a limitation, not a gap we can close.
- 2-bit is the floor regardless: the *fix* for quality remains 4-bit (which exceeds 128 GB here). This
  experiment is about **mitigating the loop**, not beating the quant.
