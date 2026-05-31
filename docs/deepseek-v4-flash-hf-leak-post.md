# Paste-ready post — mlx-community/DeepSeek-V4-Flash-2bit-DQ discussion #1 ("KeyError: 'deepseek_v4'")

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

This is **not** a runtime bug. It's stochastic degeneration into repeated tokens on long /
open-ended generations, inherent to the **2-bit DQ** checkpoint. I ran a full sampling sweep —
temperature, top_p, top_k, min_p, repetition_penalty, repetition_context_size — and **no setting
fixes it**; several make it worse. `temp=0.6` reduces it somewhat but doesn't eliminate it. The real
remedy is a higher-precision quant (4-bit), but 4-bit DeepSeek-V4-Flash exceeds 128 GB, so on this
2-bit build, expect looping on long-form output regardless of settings. It's the quant, not your setup.

**So:** the **crash** is a real, fixable runtime bug (patch above, now upstream); the **looping** is
the quantization. They're orthogonal — fixing one doesn't touch the other.

### Setup footguns (confirming what's in this thread)

The `rope_theta` / `compress_rope_theta` int→float coercion and the `KeyError: 'deepseek_v4'`
(transformers PR #45643) are exactly right. My full reproducible setup — including the
cache-materialize OOM patch as a drop-in `.patch` — is here:
https://github.com/snagnever/macstudio-local-llm/blob/deepseek-v4-tool-dsml/docs/deepseek-v4-flash-setup.md

Full OOM writeup + the complete diagnostic path:
https://github.com/snagnever/macstudio-local-llm/blob/deepseek-v4-tool-dsml/docs/deepseek-v4-flash-metal-oom-upstream-writeup.md

(Aside, since it comes up: **tool calling does work** on this 2-bit build once you give it the
native DSML template + a parser — I got **98%** on a jdhodges-style tool suite. See the
chat-template PR on the official repo, deepseek-ai/DeepSeek-V4-Flash#16, and mlx-lm#1337.)
