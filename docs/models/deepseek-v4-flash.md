# DeepSeek-V4-Flash

> **Status: 🟢 GO via GGUF** (llama.cpp, standalone `llama-server`) · **MLX: 🟡 CONSTRAINED** (Metal OOM fixed by local patch, but the 2-bit DQ quant loops on open-ended generation and every LM Studio-native path is blocked) · **⚫ 4-bit variant REMOVED 2026-05-18** (151 GB — never loaded; exceeded 128 GB unified memory).
> The long arc on this rig: three runtime bugs diagnosed and fixed/dodged (mlx-lm Metal residency leak, missing tool template, llama.cpp repack abort) before the model could show what it actually is — a capable non-thinking tool-caller/coder at 2-bit.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [deepseek-ai/DeepSeek-V4-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | HF card (fetched 2026-07-05) |
| Parameters | 284B total MoE / 13B active | HF card; matches local inventory ([testing-plan.md](../testing-plan.md) #10, [upstream writeup](../deepseek-v4-flash-metal-oom-upstream-writeup.md) — local config: `num_hidden_layers = 43`) |
| Architecture | MoE with hybrid attention — "Compressed Sparse Attention (CSA) + Heavily Compressed Attention (HCA)", Manifold-Constrained Hyper-Connections (mHC), Muon optimizer *(vendor labels)*. The mlx-lm port implements this as an MLA compressor + indexer (`deepseek_v4.py`) — the component behind the Metal leak. Arch ids: `deepseek_v4` (MLX) / `deepseek4` (GGUF) | HF card + local inspection |
| Native context | 1M tokens; run locally at 32,768 | HF card / local |
| License | MIT | HF card |
| Release | 2026-04-26 (arXiv 2606.19348) | HF card |
| Reasoning | Three vendor modes: Non-think / Think High / Think Max. Local runs use thinking OFF; GGUF emits **0 reasoning tokens** on every generation | HF card + local ([M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)) |
| Tool calling | Not explicit on the card; native **DSML** format landed via [HF discussion #16](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/discussions/16) chat template — measured excellent locally once wired (see Quality) | HF card + [pr16 comment](../deepseek-v4-flash-hf-pr16-comment.md) |
| Vendor sampling | temp 0.6 recommended default *(per DeepSeek, via [setup doc](../deepseek-v4-flash-setup.md))*; local benches ran temp 0 / thinking off | setup doc |
| Vendor claims | MMLU-Pro 86.4 (High) / 86.2 (Max), LiveCodeBench 91.6 (Flash Max), SimpleQA-Verified 34.1, MRCR-1M 78.7 *(vendor — not reproduced locally; local builds are 2-bit)* | HF card |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `deepseek-v4-flash-dq` | [mlx-community/DeepSeek-V4-Flash-2bit-DQ](https://huggingface.co/mlx-community/DeepSeek-V4-Flash-2bit-DQ) | MLX | 2-bit DQ (dynamic mixed-precision: routed experts 2-bit, sensitive layers 4/6/8-bit; converted by Lambda.ai, mlx-lm version not stated on card) | 96.53 GB (19 shards) | Standalone **patched** `mlx_lm.server` :8765 — LM Studio's MLX engine (mlx-llm 1.9.1) lacks the arch | 🟡 **CONSTRAINED** | OOM fixed by local patch; 2-bit degeneration loop remains; benchable but not daily-driver |
| `deepseek-v4-flash-iq2xs` | [teamblobfish/DeepSeek-V4-Flash-GGUF](https://huggingface.co/teamblobfish/DeepSeek-V4-Flash-GGUF) | GGUF | IQ2_XS-XL (2.45 BPW; non-expert tensors pinned Q8_0) | 81 GB (2 shards) | Standalone `llama-server` 2.24.0 (LM Studio beta-channel binary) with `--no-repack -np 1` — LM Studio-native load BLOCKED | 🟢 **GO 2026-07-05** | 16,384-tok soak dead-flat; jdhodges 87.5%, HumanEval 88% |
| ~~`deepseek-v4-flash`~~ | — | MLX | 4-bit | 151 GB | — | ⚫ **REMOVED 2026-05-18** | Never loaded — exceeded 128 GB unified memory ([local-llm-reference.md](../local-llm-reference.md) inventory note) |

## Architecture & spec notes
- 43 layers with an MLA-style compressor/indexer cache in the attention path — this is what made the model uniquely exposed to the mlx-lm lazy-graph cache leak (standard `KVCache` models write in place and don't leak). Contrast MiniMax-M2.5 (no MLA): its MLX failure was a different, driver-level mechanism.
- GGUF arch `deepseek4` is **not** recognized by stock llama.cpp 2.23.1; LM Studio's **2.24.0 beta** runtime binary is required. The [teamblobfish HF card](https://huggingface.co/teamblobfish/DeepSeek-V4-Flash-GGUF) (fetched 2026-07-05) says the quants need the `cchuter/llama.cpp` `feat/v4-port-cuda` fork — locally the LM Studio 2.24.0 `llama-server` loads IQ2_XS-XL fine (with `--no-repack`), so treat the fork note as stale/upstream-stock-specific.
- The MLX conversion ships a 24-line `chat_template.jinja` with **no tools branch** — tool calling appears "unsupported" out of the box. That was a conversion gap, not a model property (see Known issues).
- Non-thinking in practice: on the GGUF path output goes straight to the answer (0 reasoning tokens, verified in raw JSONL), so **effective throughput = raw throughput** — no reasoning tax; this is why ~10 t/s is usable.

## Local performance (measured)

| Metric | GGUF IQ2_XS-XL | MLX 2-bit DQ (patched server) |
|---|---|---|
| Sustained generation | **~10 t/s** (compute-bound, GPU ~100%) | **31.3 t/s** on the 20k forced-gen reproducer; ~36 t/s in the bench sweep; 26 t/s cold speed probe |
| Feasibility soak | ✅ 16,384-tok single generation, memory **dead-flat at 82.3 GB**, 0 leak/OOM/error — past MLX's ~11.3k death point | ✅ post-patch: 19,989-tok forced gen clean (baseline died at 11,314); **300-request knowledge soak, ~2h44m, 0 `metal::malloc`, 0 errors** |
| Leak slope (MLX) | n/a — different Metal path, no leak | 205 KB/step → **7.1 KB/step** after fix (97% reduction) |
| Memory | 82.3 GB resident, flat | 96.53 GB weights, sole-model, ctx ≤ 32,768; warm-load ~5 min |
| Reasoning tax | **0 reasoning tokens** (effective = raw) | thinking disabled via `--chat-template-args '{"enable_thinking":false}'` |

Sources: [M4_MAX_128GB_NOTES.md § DeepSeek-V4-Flash GGUF](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md) and § Phase 3 #10 addenda; [OOM investigation](../deepseek-v4-flash-metal-oom-investigation.md).

## Quality benchmarks (measured)

Config: ctx 32,768, greedy temp 0, thinking OFF, sole-model. MLX numbers 2026-05-30/31 on the patched standalone server (per-request `max_tokens` capped 2048–4096 to bound the degeneration runaway); GGUF numbers 2026-07-05 on standalone `llama-server`.

| Bench | GGUF IQ2_XS-XL (2026-07-05) | MLX 2-bit DQ (2026-05-30/31) |
|---|---|---|
| jdhodges tool-calling (40) | **87.5%** (35/40) — overturns the MLX 12.5% crash-floor; near coder-next's 90% | no template: 20% prose-only floor → Hermes workaround **82%** → **native DSML 98%** (39/40) — matches the best full-size local (`qwen3.6-35b-a3b`, 98%) |
| Veerman tool-calling (12) | **58.3%** (7/12) — strong mechanics, weak agentic proactivity (p6/p8/p12 mismatch, p7 spiral); same shape as MiniMax | no template: 17% → Hermes 50% → **native DSML 75%** (9/12); parallel multi-tool 3/8 → **8/8** under DSML |
| HumanEval (100) | **88%** — 0 trunc (~90% excl. 2 empty-response hiccups); ties coder-next 89% | 48% (15 TRUNC — degeneration, not runtime) |
| LiveCodeBench v6 (50) | **86% partial (6/7)** ⏸ — stopped at 7/50, finish armed overnight (some cases blow to 11k tok / ~19 min) | 6% floor (40/50 degenerated) |
| MMLU (100) | ⏸ not run (after LCB) | 44% |
| GPQA (100) | ⏸ not run | 24% (36 TRUNC) |
| DROP (100) | ⏸ not run | **71%** — best MLX knowledge result; extractive QA survives 2-bit |
| MATH (100) | ⏸ not run | 47% floor (41% degenerated at temp 0) |

Reading it: the MLX knowledge scores are the **2-bit DQ quality floor** (long-form output collapses), not a runtime signal; the GGUF IQ2_XS-XL — pinned Q8_0 non-expert tensors — scores dramatically higher on the same rig. Tool-calling is genuinely strong in the model's native DSML format even at 2-bit.
Raw data: `tools/local-llm-bench-m4-32gb/benchmarks/runs/{toolcall_*,humaneval_*,livecodebench_*}_deepseek-v4-flash-iq2xs_*`, `toolcall_jdhodges__Users_vitor_.lmstudio_models_mlx-community_DeepSeek-V4-Flash-2bit-DQ_*`, `results/speed_probe/deepseek-v4-flash-iq2xs_*`.

## Feasibility & verdict

- **2026-05-29 — MLX 2-bit DQ: blocked.** Full Phase 3 sweep aborted at tool-calling: `RuntimeError: [metal::malloc] Resource limit (499000) exceeded` — 49 OOMs in the server log, 161.5 min wall-clock for one 40-case suite, requests wedging the Metal queue.
- **2026-05-30 — root cause + fix (the repo's deepest debugging story).** Apple's Metal `resource_limit` (499,000) is a **count of live resident MTLResources, not bytes**. The DeepSeek-V4 attention caches (`PoolingCache`/`RotatingKVCache` + `Batch*` variants) update per-step with `concatenate`/sliced assignment and never detach the lazy graph → ~1 live Metal buffer **per layer per decode step** → 499,000 / 43 layers ≈ **OOM at ~11,300 generated tokens, decode-step driven, prompt-length independent**. Ablation: ~83% compressor/indexer, ~17% core attention; MoE/mHC clean. The original H1–H6 hypothesis ladder is dead (H1 per-layer eval tested and FAILED — can't reclaim live buffers; H2–H4 invalidated by the count mechanism; the earlier indexer-chunk patch reduced OOMs 49→3 but cost 3–4× throughput and never fixed it). **Verified fix:** one `mx.eval` per forward materializing all per-layer cache arrays — [`patches/mlx-lm-deepseek-v4-cache-materialize.patch`](../../patches/mlx-lm-deepseek-v4-cache-materialize.patch). 40/40 jdhodges 0 OOMs; 300-request soak 2h44m 0 errors; 31.3 t/s unchanged. Details: [investigation](../deepseek-v4-flash-metal-oom-investigation.md) §2, [fix plan](../deepseek-v4-flash-metal-oom-fix-plan.md) Phase 2-revised (R5), [upstream writeup](../deepseek-v4-flash-metal-oom-upstream-writeup.md), [issue/PR drafts](../deepseek-v4-flash-metal-oom-issue-and-pr-drafts.md).
- **2026-05-31 — orthogonal quality ceiling stands.** The 2-bit DQ quant **loops stochastically ~50% at temp 0.6** on open-ended generation; a rate-measured sweep (8 real seeds/cell, after porting the mlx-lm seed fix #1331) found **no sampling setting that fixes it — XTC roughly doubles the loop rate (~87%)**, and long-form collapses 94–100% under every config. It's the quant, not the setup; the remedy (4-bit) exceeds 128 GB. [Degeneration plan + results](../benchmark-plans/2026-05-31-deepseek-v4-flash-degeneration-sampling.md).
- **2026-07-05 — GGUF IQ2_XS-XL: ✅ GO.** Different runtime, different Metal path, **no leak** (16,384-tok soak flat at 82.3 GB). Three gates cleared: llama.cpp **2.24.0 beta** for the `deepseek4` arch; `--no-repack` to dodge a `ggml_abort` in the CPU repack path (Q8_0 MoE `mul_mat_id`, ref llama.cpp PR #17869); `-np 1` to avoid KV overcommit. Quality clears the gate (jdhodges 87.5%, HumanEval 88%). The only runnable model in the DeepSeek-V4 / large-MoE class on this rig.
- **Remaining work:** finish LCB v6 overnight (43 cases, `.bench-logs/run-ds4-lcb-overnight.sh` armed for 01:00) → MMLU → charts + potential [local-llm-reference.md](../local-llm-reference.md) slot.

Plans: [2026-05-29 Phase 3](../benchmark-plans/2026-05-29-deepseek-v4-flash-phase-3.md) · [2026-05-30 remaining benches](../benchmark-plans/2026-05-30-deepseek-v4-flash-remaining-benches.md) · [2026-05-30 tool template](../benchmark-plans/2026-05-30-deepseek-v4-flash-tool-template.md) · [2026-05-31 degeneration sampling](../benchmark-plans/2026-05-31-deepseek-v4-flash-degeneration-sampling.md) · [2026-07-05 Phase 5 (GGUF)](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md)

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| `[metal::malloc] Resource limit (499000) exceeded` at ~11,300 generated tokens (MLX) | Un-detached lazy cache graphs retain ~1 live Metal buffer/layer/step; 499,000 is a *count* cap | **FIXED** — [`patches/mlx-lm-deepseek-v4-cache-materialize.patch`](../../patches/mlx-lm-deepseek-v4-cache-materialize.patch). Filed upstream: [issue #1332](https://github.com/ml-explore/mlx-lm/issues/1332) (open), [Blaizzy/mlx-lm#25](https://github.com/Blaizzy/mlx-lm/pull/25). Deprecated en-route artifacts kept as record: [`mlx-lm-deepseek-v4-indexer-chunk.patch`](../../patches/mlx-lm-deepseek-v4-indexer-chunk.patch) (do NOT apply), [`mlx-lm-deepseek-v4-per-layer-eval.patch.candidate`](../../patches/mlx-lm-deepseek-v4-per-layer-eval.patch.candidate) (failed H1) |
| Repetition/loop on open-ended gens (MLX 2-bit DQ) | 2-bit quant floor — stochastic ~50% at temp 0.6, distinct from the OOM | **No fix.** XTC *worsens* it (~87%); additive penalties within noise. Needs ≥4-bit (doesn't fit) |
| "model does not support tool calling", tools array dropped (MLX) | Conversion ships a template with no tools branch | **FIXED** — native DSML template ([HF #16](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/discussions/16)) + `deepseek_dsml` parser; installer `assets/deepseek-v4-dsml/install.sh`. 0 → 98% jdhodges |
| Valid `<tool_call>` returned as content, `tool_calls: null` (mlx-lm generic) | Tokenizer merges the marker's trailing `>` with the next byte; exact token-id matching never fires | **FIXED locally** (prefix-marker matching) — [writeup](../mlx-lm-tool-call-marker-merge-writeup.md); upstream [issue #1335](https://github.com/ml-explore/mlx-lm/issues/1335) / [PR #1336](https://github.com/ml-explore/mlx-lm/pull/1336) (open, no maintainer response as of 2026-07-05); DSML parser PR [#1337](https://github.com/ml-explore/mlx-lm/pull/1337). 0→82% on the Hermes path |
| `unknown model architecture: 'deepseek4'` (GGUF) | Stock llama.cpp 2.23.1 lacks the arch | Upgrade LM Studio GGUF runtime to **2.24.0 beta** (`lms runtime get --channel beta`) |
| `ggml_abort` on first forward pass (GGUF, LM Studio-native) | CPU repack path (Q8_0 MoE `mul_mat_id`, ref llama.cpp PR #17869); `lms load` has no flag and `LLAMA_ARG_REPACK` is ignored by `LlamaV4::load` | Run standalone `llama-server` with `--no-repack`. **LM Studio-native remains BLOCKED** |
| Metal OOM at load (GGUF) | Default `n_slots=4` overcommits KV | `-np 1` |
| HTTP 404 `list index out of range` on short prompts (mlx-lm server) | Negative `start` in `TokenizerWrapper._find` ([mlx-lm #1326](https://github.com/ml-explore/mlx-lm/issues/1326)) | [`patches/mlx-lm-find-negative-start.patch`](../../patches/mlx-lm-find-negative-start.patch) — always apply |
| XTC requests 500 (mlx-lm server) | Ragged `xtc_special_tokens` ([#1257](https://github.com/ml-explore/mlx-lm/issues/1257)) | [`patches/mlx-lm-xtc-special-tokens-flatten.patch`](../../patches/mlx-lm-xtc-special-tokens-flatten.patch) |
| Per-request `seed` silently ignored (mlx-lm server) | Compiled sampler captures RNG state ([#1245](https://github.com/ml-explore/mlx-lm/issues/1245)) | [#1331](https://github.com/ml-explore/mlx-lm/pull/1331) ported locally for the rate runs — see [`patches/mlx-lm-server-seed-fix-NOTE.md`](../../patches/mlx-lm-server-seed-fix-NOTE.md) |
| `config.json` rejected (`rope_theta`/`compress_rope_theta` int vs float) | transformers PR #45643 strict dataclass validation | Coerce both to float in place (`.bak` kept) — [setup doc](../deepseek-v4-flash-setup.md) step 1 |
| Occasional empty response, ~2–3% (GGUF) | Unknown, non-systematic | Counted as FAIL in benches; watch it |

## Loading & memory

**GGUF (the GO path) — full working recipe** (sole-model; 82.3 GB resident):

```bash
BIN=~/.lmstudio/extensions/backends/llama.cpp-mac-arm64-apple-metal-advsimd-2.24.0
M=~/.lmstudio/models/teamblobfish/DeepSeek-V4-Flash-GGUF/DeepSeek-V4-Flash-IQ2_XS-XL-00001-of-00002.gguf
cd "$BIN" && ./llama-server -m "$M" -a deepseek-v4-flash-iq2xs \
  --no-repack -c 32768 -np 1 -ngl 999 --host 127.0.0.1 --port 1235
# harness: LMSTUDIO_URL=http://127.0.0.1:1235/v1
```

All three flags are load-bearing: 2.24.0 binary (arch), `--no-repack` (repack abort), `-np 1` (KV overcommit). Source: [M4 notes § DeepSeek-V4-Flash GGUF](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).

**MLX (patched standalone server)** — full procedure in [deepseek-v4-flash-setup.md](../deepseek-v4-flash-setup.md); summary:

```bash
# venv: /Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash (uv, Python 3.12)
# stack: transformers ≥ post-2026-05-02 + mlx-lm from PR #1192 head, then:
(cd "$VIRTUAL_ENV/lib/python3.12/site-packages" \
   && patch -p0 < patches/mlx-lm-find-negative-start.patch \
   && patch -p0 < patches/mlx-lm-deepseek-v4-cache-materialize.patch)   # both REQUIRED, this order
python -m mlx_lm.server \
  --model "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --chat-template-args '{"enable_thinking":false}' \
  --host 0.0.0.0 --port 8765 --max-tokens 4096 --temp 0.0
```

Prereq: `config.json` int→float patch (setup doc step 1). Do **not** apply the deprecated indexer-chunk patch.

- **Sole-model only, both paths:** 96.53 GB (MLX) / 82.3 GB (GGUF) — far over the ~80 GB pairing rule; evict everything else. Context ≤ 32,768.
- MLX warm-load: ~5 min cold to first inference. GGUF soak-verified flat at 82.3 GB — the 01:00 LCB overnight job runs against this footprint.

## Client configuration
- **GGUF:** model id `deepseek-v4-flash-iq2xs` at `http://127.0.0.1:1235/v1` (standalone llama-server — NOT LM Studio's :1234). Non-thinking; benches ran temp 0.
- **MLX:** OpenAI-compatible at `http://127.0.0.1:8765/v1`; drive via Open WebUI (Docker, `host.docker.internal:8765`) or `mlx_lm.chat`. Vendor-recommended temp 0.6; thinking off via `--chat-template-args`.
- **Tool calling (MLX):** install the native DSML template + parser (`bash assets/deepseek-v4-dsml/install.sh`) — use DSML, not the Hermes workaround (98% vs 82% jdhodges; parallel multi-tool 8/8 vs 3/8). GGUF path needed no template surgery for its 87.5%.
- Cap `max_tokens` (2048–4096) on the MLX DQ build to bound the degeneration runaway.

## External links
- Vendor: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash (fetched 2026-07-05)
- MLX conversion: https://huggingface.co/mlx-community/DeepSeek-V4-Flash-2bit-DQ (96.5 GB per card; converted by Lambda.ai; mlx-lm conversion version not stated)
- GGUF conversion: https://huggingface.co/teamblobfish/DeepSeek-V4-Flash-GGUF (IQ1_S-XL 57 GiB → Q8_0 282 GiB; IQ2_XS-XL 2.45 BPW ~81 GiB, 2 shards; `-XL` = non-expert tensors pinned Q8_0)
- Upstream: [mlx-lm PR #1192](https://github.com/ml-explore/mlx-lm/pull/1192) (arch port — **closed unmerged 2026-06-19** by author) · [issue #1332](https://github.com/ml-explore/mlx-lm/issues/1332) (leak — **open**) · [Blaizzy/mlx-lm#25](https://github.com/Blaizzy/mlx-lm/pull/25) (fix PR against the #1192 branch) · [issue #1335](https://github.com/ml-explore/mlx-lm/issues/1335) / [PR #1336](https://github.com/ml-explore/mlx-lm/pull/1336) (marker merge — **open**) · [PR #1337](https://github.com/ml-explore/mlx-lm/pull/1337) (DSML parser) · spicyneuron's `fix-ds4` fork + 4000-token reproducer gist (see [investigation](../deepseek-v4-flash-metal-oom-investigation.md) external signals)
- Community posts drafted here: [HF leak post](../deepseek-v4-flash-hf-leak-post.md) (mlx-community discussion #1), [HF #16 DSML comment](../deepseek-v4-flash-hf-pr16-comment.md)

## History
- **2026-05-17≈** — family arrives on disk: 4-bit (151 GB) + 2-bit DQ (96.53 GB).
- **2026-05-18** — ⚫ 4-bit **removed** — never loaded, exceeded 128 GB unified memory ([local-llm-reference.md](../local-llm-reference.md) inventory note).
- **2026-05-19** — [setup plan](../deepseek-v4-flash-setup.md): patched standalone mlx-lm venv (PR #1192 head + transformers float fix), since LM Studio's engines lack the arch.
- **2026-05-29** — Phase 3 #10 bench attempt **aborted**: Metal `resource_limit` OOM (49 errors, jdhodges 12.5% crash-floor). Indexer-chunk patch + restart-per-batch tried same day — neither sufficient.
- **2026-05-30** — root cause nailed (live-buffer *count*, ~1/layer/step, OOM @ ~11.3k tokens; H1–H6 ladder dead); **cache-materialize fix verified** (19,989 tok clean, 31.3 t/s, slope 205→7.1 KB/step). Knowledge sweep + 300-request soak (0 OOMs): MMLU 44 / GPQA 24 / HumanEval 48 / DROP 71 / MATH 47 / LCB 6. Filed upstream (#1332, Blaizzy#25, comment on #1192).
- **2026-05-31** — **tool calling recovered**: marker-merge fix (#1335/#1336, 0→82%) then native DSML template (HF #16) + parser → **jdhodges 98% / Veerman 75% / combined 92%**. Degeneration sampling sweep: no config fixes the ~50% loop; XTC doubles it — 2-bit quant floor confirmed.
- **2026-06-19** — upstream PR #1192 closed unmerged by its author; MLX-native path indefinitely stalled.
- **2026-07-05** — 🟢 **GGUF GO**: IQ2_XS-XL on standalone llama-server 2.24.0 (`--no-repack -np 1`) — 16,384-tok soak flat 82.3 GB, jdhodges 87.5%, HumanEval 88%, Veerman 58.3%, LCB partial 7/50 @ 86% (overnight finish armed). First clean runtime for the model on this rig.
