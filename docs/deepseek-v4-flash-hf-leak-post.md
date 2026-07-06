# Paste-ready post — mlx-community/DeepSeek-V4-Flash-2bit-DQ discussion #1 ("KeyError: 'deepseek_v4'")

> Model card: [deepseek-v4-flash](models/deepseek-v4-flash.md)


**Post it here:** https://huggingface.co/mlx-community/DeepSeek-V4-Flash-2bit-DQ/discussions/1
(this is the thread with the open, unexplained "repeating output in long generations" — our post
answers it and links the fix). Needs your HF account.

---

Following up on the open item here — the **repeating output on longer generations**. I've been
running this exact 2-bit build heavily on an M4 Max 128 GB and chased it to the bottom. The
confusing part is that there are **two completely different failure modes** on long generations,
and they get conflated:

### 1. A hard crash: `[metal::malloc] Resource limit (499000) exceeded` after ~11,300 tokens

If you push generation long enough through `mlx_lm.server`, it aborts with this, **independent of
prompt length**, and afterward the Metal queue is wedged until you restart the process. (You may not
have hit it yet if your generations stayed short or you used `mlx_lm.generate`.)

- **Root cause** — it's a *count* of live resident Metal buffers, not bytes (only ~2–3 GB is
  actually leaked at the crash). The DeepSeek-V4 attention caches (the compressor/indexer
  `PoolingCache` and `RotatingKVCache`) build their per-decode-step update with `concatenate` /
  sliced assignment and **never detach the graph**, so MLX keeps every prior step's intermediate
  array — and its backing Metal buffer — resident. That's ~1 buffer per layer per step →
  `499000 / 43 layers ≈ 11.3K steps`, matching the crash point exactly.
- **How I diagnosed it** — Metal GPU capture + sub-module ablation (bypass attention / MoE /
  hyper-connections one at a time and measure the per-step buffer-count slope) localized it to the
  compressor/indexer cache path; force-evaluating the cache state each step collapsed the growth
  (~205 → ~7 KB/step), which proved it's un-evaluated cache-update graphs — **not** memory size,
  **not** `mx.compile`, **not** prompt-cache length.
- **The fix** — materialize (`mx.eval`) all per-layer cache state once per forward pass in
  `DeepseekV4Model.__call__`. One hunk; it detaches the chains so the live-buffer count stays
  bounded. After the patch: a forced 20K-token generation runs **clean to 19,989 tokens** (was OOM
  at 11,314), **31.3 tok/s** (no regression), and **0 OOMs across a 300-request benchmark soak**.
  Filed upstream: **issue [ml-explore/mlx-lm#1332](https://github.com/ml-explore/mlx-lm/issues/1332)**
  and **PR [Blaizzy/mlx-lm#25](https://github.com/Blaizzy/mlx-lm/pull/25)** (against the #1192 branch).

### 2. The repeating/looping text itself is a *different* thing — the 2-bit quant quality floor

This is **not** a runtime bug — it's stochastic degeneration into repeated tokens on open-ended
generations, inherent to the **2-bit DQ** checkpoint. I measured real loop *rates* (8 independent seeds
per config, after patching two server bugs noted below) on a reliable trigger prompt:

| sampling config | loop rate (8 seeds, 95% CI) |
|---|---|
| `temp 0.6`, nothing else | **50%** [22, 78] |
| `temp 0.7` + `min_p 0.02` + `presence_penalty 1.0` (no XTC) | **37%** [14, 69] |
| same **+ XTC** (`xtc_probability 0.5, xtc_threshold 0.1`) | **87%** [53, 98] |

Three takeaways:

- **The loop is a coin-flip, not deterministic** — even plain `temp 0.6` self-terminates with a clean,
  coherent answer about half the time. (So "it always loops" is itself a sampling illusion.)
- **No setting reliably reduces the rate.** Additive penalties (presence/frequency/repetition) land
  within noise of baseline.
- **XTC makes it *worse*, not better** — it roughly **doubles** the loop rate (≈87%). XTC removes the
  most-probable token, which derails the model into incoherence/looping more often than it rescues it.
  (A confident *factual* prompt like "capital of France" never loops at baseline — 0/8 — so there's
  nothing for XTC to "fix" there either.)

And it's **worse on genuinely long-form output**: across an 800-word story and a 50-item list (8 seeds
each, coherence scored by a separate model), **every config failed 15–16 of 16** — baseline, +presence,
and +XTC alike. At 2-bit, long generations collapse ~94–100% of the time *regardless of settings*
(usually the model restarts the story/list from the top; XTC swaps that for word-salad).

So: **there is no sampling setting that fixes the looping**; the most aggressive anti-repetition knob
the library has (XTC) actively backfires. The robust remedy is a higher-precision quant (4-bit), but
4-bit DeepSeek-V4-Flash exceeds 128 GB, so on this 2-bit build expect intermittent looping on
open-ended output regardless of settings. **It's the quant, not your setup.**

*(Methodology note, in case you try to reproduce: `mlx_lm.server` currently has two bugs I had to patch
first — XTC crashes on a ragged `xtc_special_tokens` list (`ValueError: Initialization encountered extra
dimension`; both already tracked upstream as #1257 + #1331/#1245), and the compiled sampler ignores the
per-request `seed`, so without that fix every "different seed" returns byte-identical text — which will
fool you into thinking the loop is deterministic. Measure rates with the seed fix applied.)*

**So:** the **crash** is a real, fixable runtime bug (patch above, now upstream); the **looping** is
the quantization. They're orthogonal — fixing one doesn't touch the other.

### Setup fixes (the two errors at the top of this thread are one chain)

Both startup errors come from the **same** transformers PR, in sequence:

- **`KeyError: 'deepseek_v4'`** (the thread title) → fixed by transformers
  **[PR #45643](https://github.com/huggingface/transformers/pull/45643)**, which adds `deepseek_v4`
  support and **merged into transformers `main` on 2026-05-02**. So today you no longer need to
  install the PR ref by hash — a recent `transformers` from PyPI (≥ the post-2026-05-02 release) or
  `git+https://github.com/huggingface/transformers.git@main` resolves it. (`--trust-remote-code` on
  `mlx_lm.server` / `mlx_lm.generate` is a fallback if your transformers is older.)
- **`StrictDataclassFieldValidationError` (`rope_theta` expected float, got int)** → this is the
  *same* PR #45643's stricter config validation kicking in *right after*, which is why it's the very
  next error once the KeyError clears. Coercing `rope_theta` / `compress_rope_theta` (and any other
  int field the error names) to float in `config.json`, exactly as done in this thread, clears it.

So the startup sequence is fully solved; the only remaining runtime issues are the two above (the OOM
crash, fixed + filed; and the quant looping). My full reproducible setup — pinning these + the
cache-materialize OOM patch as a drop-in `.patch` — is here:
https://github.com/snagnever/macstudio-local-llm/blob/deepseek-v4-tool-dsml/docs/deepseek-v4-flash-setup.md

Full OOM writeup + the complete diagnostic path:
https://github.com/snagnever/macstudio-local-llm/blob/deepseek-v4-tool-dsml/docs/deepseek-v4-flash-metal-oom-upstream-writeup.md

(Aside, since it comes up: **tool calling does work** on this 2-bit build once you give it the
native DSML template + a parser — I got **98%** on a jdhodges-style tool suite. See the
chat-template PR on the official repo, deepseek-ai/DeepSeek-V4-Flash#16, and mlx-lm#1337.)
