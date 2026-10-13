# llama.cpp / GGUF path for dense Qwen3.8-27B on Apple Silicon (as of 2026-10-13)

Repo baseline (prior state, July 2026, from `docs/models/qwen3.6-27b.md` "Draft MTP" section): on Qwen3.6-27B unsloth UD-Q6_K_XL GGUF in LM Studio (ctx 65k, parallel 4, thinking off), Draft MTP at draft=2 gave doc-summary +28 %, ops-agent +15 %, prefill-test +5 %, creative-writing −8 % gen t/s; draft depth 3/4/6/8 were monotonically worse; MTP did not fix prefill. MLX 6-bit stayed the daily driver (~20 t/s).

Architecture facts used throughout (from the model card mirrored in unsloth's README, [unsloth README](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/raw/main/README.md)): 27B dense, 64 layers = 16 × (3 × Gated DeltaNet + 1 × Gated Attention); Gated Attention 24 Q heads / 4 KV heads, head dim 256; Gated DeltaNet 48 V heads / 16 QK heads, head dim 128; vocab 248,320; MTP "trained with multiple steps"; 262,144 native context, extensible to 1M (YaRN). In llama.cpp it loads through the existing `qwen35` (Qwen3.5-hybrid) arch, not a new arch ([#27756](https://github.com/ggml-org/llama.cpp/issues/27756); [Ollama #18541](https://github.com/ollama/ollama/issues/18541) "Qwen3.5 architecture").

## 1. GGUF repos: quants, sizes, MTP sidecar, revisions

### Takeaway
Five mainstream GGUF repos exist (unsloth, ggml-org, bartowski, lmstudio-community, mradermacher static + i1). There is no official `Qwen/Qwen3.8-27B-GGUF` repo. Only unsloth (`MTP/mtp-Qwen3.8-27B-Q4_0.gguf`, 1.37 GB) and ggml-org (`mtp-*` in BF16/Q8_0/Q4_0 plus `dflash-*` drafters) ship separate MTP sidecar files. Community reports also say the main unsloth and upstream GGUFs keep the MTP `nextn` tensors inline.

### Cited Findings
- **unsloth/Qwen3.8-27B-GGUF**: sha `4ca720788d1e01f1bff70c033e0d0028fd02e502`, created 2026-08-13, last modified 2026-08-20 (commit "Upload imatrix"), about 6.65 M downloads. Files: UD-IQ1_S 6.19 GB, UD-IQ1_M 6.73, UD-IQ2_XXS 7.27, UD-IQ2_S 8.37, UD-Q2_K_XL 9.83, UD-IQ3_XXS 10.93, UD-IQ3_S 12.04, UD-Q3_K_XL 13.15, UD-IQ4_XS 14.25, UD-Q4_K_S 15.36, Q4_0 16.06, UD-Q4_K_M 16.46, Q4_1 17.54, UD-Q4_K_XL 17.56, UD-Q5_K_S 18.67, UD-Q5_K_M 19.77, UD-Q5_K_XL 20.88, UD-Q6_K 21.98, UD-Q6_K_M 23.09, UD-Q6_K_L 24.19, UD-Q6_K_XL 25.30, UD-Q8_K_L 28.05, Q8_0 29.05, UD-Q8_K_XL 31.46, BF16 (2 shards) 54.66; mmproj BF16/F16 0.93; **MTP/mtp-Qwen3.8-27B-Q4_0.gguf 1.37 GB**; imatrix_unsloth.gguf. — [HF API listing](https://huggingface.co/api/models/unsloth/Qwen3.8-27B-GGUF?blobs=true)
- unsloth repo history on 2026-08-19: the MTP file was renamed `mtp-Qwen3.8-27B-Q4_K.gguf` → `mtp-Qwen3.8-27B-Q4_0.gguf` and then moved into `MTP/` (commit `990216cf`). The same day unsloth deleted its non-UD Q4_K_S/Q5_K_M/Q5_K_S/Q6_K and UD-IQ2_M files and renamed UD-Q8_K_S → UD-Q8_K_L. Any local pin taken before 2026-08-19 has different filenames. — [unsloth commits](https://huggingface.co/api/models/unsloth/Qwen3.8-27B-GGUF/commits/main)
- **ggml-org/Qwen3.8-27B-GGUF**: sha `71bc7b627595dc8a91039addd9c791ae548d6747`, created 2026-08-14, re-uploaded 2026-09-19, 09-20 and 09-27 by the automatic converter. `.src_sha`: PRIMARY=`1d4bf0f2…`, DFLASH=`015e7956…`. Files: Q4_K_M 18.97 GB, Q8_0 28.60, BF16 53.81; **mtp-Qwen3.8-27B-Q4_0 1.68 GB / Q8_0 3.16 / BF16 5.95**; **dflash-Qwen3.8-27B-Q4_0 1.09 / Q8_0 2.06 / BF16 3.86** (drafter from `incoai/Qwen3.8-27B-DFlash2`); mmproj BF16 0.93 / Q8_0 0.63. README: `llama serve -hf ggml-org/Qwen3.8-27B-GGUF`. — [HF API listing](https://huggingface.co/api/models/ggml-org/Qwen3.8-27B-GGUF?blobs=true), [README](https://huggingface.co/ggml-org/Qwen3.8-27B-GGUF)
- An older ggml-org snapshot, `0669b98607d47046c7c2b3f801011d54a08cfccf` (2026-08-14), had Q4_K_M at 18,973,870,432 bytes and mtp Q4_0 at 1,680,271,648 bytes. `llama download -hf ggml-org/Qwen3.8-27B-GGUF:Q4_K_M --mtp` fetches the drafter; without `--mtp` no drafter is downloaded. — [scriptable.com macOS guide](https://scriptable.com/posts/llama-cpp/run-qwen3-8-27b-llama-cpp-macos/)
- **bartowski/Qwen3.8-27B-GGUF**: sha `0c92138c51f112d2f0dc84d5f6d1ebe4b9912b9a`, created 2026-08-14, last modified 2026-09-20. Quants: IQ2_XXS 8.88 GB, IQ2_XS 9.09, IQ2_S 9.68, IQ2_M 10.52, Q2_K 10.82, Q2_K_L 13.08, IQ3_XXS 12.32, IQ3_XS 12.80, Q3_K_S 12.74, Q3_K_M 13.40, Q3_K_L 14.12, IQ3_M 14.86, Q3_K_XL 16.39, IQ4_XS 15.48, Q4_0 16.35, Q4_K_S 16.36, Q4_K_M 17.44, IQ4_NL 17.44, Q4_1 17.83, Q4_K_L 18.82, Q5_K_S 19.57, Q5_K_M 20.92, Q5_K_L 21.54, Q6_K_S 22.86, Q6_K 23.86, Q6_K_L 24.96, Q8_0 29.12, bf16 54.66; imatrix; calibration-v6; per-quant `layouts/*.tensor-types.txt`; perplexity.md; mmproj. **No separate MTP file.** (Note: the repo is `bartowski/Qwen3.8-27B-GGUF`, not `bartowski/Qwen_Qwen3.8-27B-GGUF`.) — [HF API listing](https://huggingface.co/api/models/bartowski/Qwen3.8-27B-GGUF?blobs=true)
- **lmstudio-community/Qwen3.8-27B-GGUF**: sha `5a7da681f60570ab5b439a587e912d2e5eddb582`, 2026-08-14. Q4_K_M 16.81 GB, Q6_K 22.43, Q8_0 29.05, mmproj BF16. No MTP sidecar. — [HF API](https://huggingface.co/api/models/lmstudio-community/Qwen3.8-27B-GGUF?blobs=true)
- **mradermacher/Qwen3.8-27B-GGUF** (static): sha `860659a596e879987cee91b4c43ae605796f3ef8`, 2026-08-15. Q2_K 10.86, Q3_K_S 12.26, Q3_K_M 13.50, Q3_K_L 14.56, IQ4_XS 15.42, Q4_K_S 15.83, Q4_K_M 16.81, Q5_K_S 18.97, Q5_K_M 19.54, Q6_K 22.43, Q8_0 29.05 GB, plus mmproj. **mradermacher/Qwen3.8-27B-i1-GGUF** (imatrix): sha `9eb2d6dbd01fca8d0b97a37b02f4dd8b7b94f69d`, 2026-08-15, i1-Q2_K … i1-Q6_K (for example i1-Q4_K_M 16.81, i1-Q6_K 22.43). Neither has an MTP sidecar. — [static](https://huggingface.co/api/models/mradermacher/Qwen3.8-27B-GGUF?blobs=true), [i1](https://huggingface.co/api/models/mradermacher/Qwen3.8-27B-i1-GGUF?blobs=true)
- **Qwen official**: the Qwen org lists `Qwen3.8-27B` and `Qwen3.8-27B-FP8` but no GGUF. `Qwen/Qwen3.8-27B-GGUF` returns not-found. — [HF API Qwen author search](https://huggingface.co/api/models?author=Qwen&search=Qwen3.8)
- Other notable repos: byteshape/Qwen3.8-27B-GGUF (bpw-labelled IQ2_XXS 2.56bpw 8.84 GB … IQ4_XS 3.84bpw 13.08 GB, updated 2026-09-18, about 1.42 M downloads); ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF (2026-08-28); Jackrong/Qwen3.8-27B-MTP-GGUF; incoai/Qwen3.8-27B-DFlash2 (drafter). — [HF API search](https://huggingface.co/api/models?search=Qwen3.8-27B)
- **MTP inline vs sidecar.** sudoingX says "the MTP head already ships inside your GGUF": unsloth UD-Q4_K_M, UD-Q4_K_XL and UD-Q2_K_XL carry `blk.*.nextn.*` tensors, verified via `qwen35.nextn_predict_layers`, and upstream Q8_0 GGUFs from Qwen-sourced conversions and LM Studio also worked with the flag. — [sudoingX/qwen38-mtp](https://github.com/sudoingX/qwen38-mtp). An M4 Max reporter likewise says unsloth UD-Q4_K_XL has "MTP module inside the same GGUF, no separate draft file". — [#30174](https://github.com/ggml-org/llama.cpp/issues/30174). The ggml-org route in contrast uses `-md mtp-*.gguf --spec-type draft-mtp` and says "Both flags are required". — [scriptable.com](https://scriptable.com/posts/llama-cpp/run-qwen3-8-27b-llama-cpp-macos/)

### Inferences
- For a 128 GB M4 Max, the natural candidates are unsloth UD-Q6_K_XL (25.30 GB) or UD-Q8_K_XL (31.46 GB), or ggml-org Q8_0 (28.60 GB) with the ggml-org `mtp-…-Q8_0` sidecar (3.16 GB). These match the repo's MLX 6-bit/8-bit quality tier. The unsloth sidecar exists only as Q4_0.
- The two layouts (inline nextn tensors vs a separate `mtp-*.gguf` passed with `-md`) both appear to work on current builds. The bench should state which one it used, because memory and quantization of the MTP head differ (unsloth Q4_0 1.37 GB vs ggml-org Q8_0 3.16 GB).

### Gaps
- I did not inspect GGUF metadata to confirm which bartowski, mradermacher or lmstudio-community files carry inline `nextn` tensors. A search-engine summary claimed "bartowski's MTP-enabled quants were built with llama.cpp b10419 or newer", but I could not verify it on the model card.
- I found no published KLD/perplexity comparison of the unsloth UD quants against bartowski or ggml-org specific to Qwen3.8-27B, beyond unsloth's own ">10 %" marketing claim and bartowski's `perplexity.md`, which I did not read.

## 2. llama.cpp support status, Metal, flags, open issues/PRs

### Takeaway
Qwen3.8-27B runs on the existing `qwen35` hybrid code path: Gated DeltaNet plus Gated Attention, with recurrent-state rollback allow-listed for QWEN35. Day-one support therefore came from mid-August 2026 builds (about b10330–b10470 on Homebrew). The current tip is **b11582 (2026-10-13)**, and the repo's **b11569 was published 2026-10-12**; its headline fix is the Metal `mul_mat_id` duplicate-ids fix, which matters for MoE, not for the dense model. No Qwen3.8-27B-specific Metal kernel bug is open. Main known problems are (a) host-memory growth with draft-mtp on Metal (#30174), (b) silent instant-EOS beyond about 96–130k context (#27756, engine-side), (c) Flash-Next-only MTP + `--kv-unified` + `--parallel>1` failure (#30368).

### Cited Findings
- **Releases.** b11569 was published 2026-10-12T13:16Z with release note "metal : fix mul_mat_id with duplicate ids (#30373)", and ships `llama-b11569-bin-macos-arm64.tar.gz`. Latest pre-release is b11582 (2026-10-13T08:29Z). — [b11569 release](https://github.com/ggml-org/llama.cpp/releases/tag/b11569), [release list](https://github.com/ggml-org/llama.cpp/releases)
- Library version strings changed: "llama.cpp : bump version to 0.5.0" (#29333, merged 2026-09-23) and "bump version to 0.6.0" (#29997, 2026-10-05). Reports now show for example `version: 0.6.0-dev (build 780, commit fc9ce6b9d)`. — [#29997](https://github.com/ggml-org/llama.cpp/pull/29997), [#30174](https://github.com/ggml-org/llama.cpp/issues/30174)
- **Minimum build.** An M5 Max guide validated 2026-08-18 used Homebrew `b10330-687e77892`; Homebrew had moved to 10470, and either works. Older builds fail with `unknown model architecture: 'qwen35'` (from search summary). — [scriptable.com](https://scriptable.com/posts/llama-cpp/run-qwen3-8-27b-llama-cpp-macos/). sudoingX says draft-mtp was added in llama.cpp PR #22673 (July 2026). — [sudoingX](https://github.com/sudoingX/qwen38-mtp). Separately, an issue states b9180 was "the first release version supports MTP" (for Qwen3.6). — [#25489](https://github.com/ggml-org/llama.cpp/issues/25489)
- **Hybrid / recurrent support.** "qwen4exp: support recurrent state rollback" (#28123, merged 2026-09-01) put QWEN4EXP (Flash-Next) next to the already-supported `LLM_ARCH_QWEN35` in `llm_arch_supports_rs_rollback()`. The issue's diff shows `LLM_ARCH_QWEN35` was already allow-listed. — [#28019](https://github.com/ggml-org/llama.cpp/issues/28019)
- Other merged MTP/spec PRs since September: "convert : write explicit recurrent_layers for Qwen3-Next / Qwen3.5" (#28208, 2026-09-07); "Enable CUDA graph for MTP draft" (#28549, CUDA only, 2026-09-16); "metal : key the fa-vec tuned table by family instead of SKU" (#29075, 2026-09-23); "common : stop accepting draft tokens at EOG" (#29638, 2026-09-29); "Make the drafter probabilistic and the target verify by rejection sampling for simple draft and MTP" (#27694, 2026-10-02); "spec: properly handle mtmd input for mtp" (#30257, 2026-10-10). — [merged PR search](https://github.com/ggml-org/llama.cpp/pulls?q=mtp+is%3Amerged)
- **Current flags** (master `tools/server/README.md`):
  - `--spec-type none,draft-simple,draft-eagle3,draft-mtp,draft-dflash,draft-dspark,ngram-*`
  - `--spec-draft-n-max N` (default **3**). There is no `--spec-draft-n`; the old `--draft`, `--draft-n` and `--draft-max` are "removed. use --spec-draft-n-max"
  - `--spec-draft-n-min` (default 0), `--spec-draft-p-min` (default 0.00)
  - `--spec-draft-sampling {greedy,probabilistic}` (default greedy; probabilistic = rejection sampling)
  - `--spec-draft-model/-md`, `--spec-draft-type-k/-v` (draft KV type, default f16), `--spec-default`
  - `-kvu/--kv-unified` ("default: enabled if number of slots is auto"), `-np/--parallel` (default −1 = auto)
  - `-ctxcp/--ctx-checkpoints` (default 32), `-cms/--checkpoint-min-step` (default 8192)
  - `-cram/--cache-ram` (default 8192 MiB), `--cache-idle-slots`, `--cache-reuse N` (default 0), `--slot-save-path`
  - `--reasoning-preserve` (default enabled, for templates with `supports_preserve_reasoning`)

  — [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- **Default slot behaviour.** With no `-np`, the server auto-picks 4 slots with `kv_unified = 'true'` (logged `n_slots = 4`, `n_ctx_slot = 32768` at `-c 32768`, M5 Max). — [scriptable.com](https://scriptable.com/posts/llama-cpp/run-qwen3-8-27b-llama-cpp-macos/). So `--parallel 1` must be explicit.
- **#30368 (open, 2026-10-12).** Qwen3.8-**Flash-Next** with `--spec-type draft-mtp` + `--kv-unified` + `--parallel 4` fails every request with `decode: Compute error … ret = -3`. Each pair of the three settings passes. Reported on M5 Max 40-core GPU 128 GB, macOS 27.0.1, build `0.6.0-dev (build 35, commit 08ffba21e)`. The 27B dense is not tested there. — [#30368](https://github.com/ggml-org/llama.cpp/issues/30368)
- **#30174 (open, 2026-10-08), Metal + Qwen3.8-27B.** On an M4 Max 16-core GPU 64 GB, master `fc9ce6b9d`, UD-Q4_K_XL, `--ctx-size 262144 -ctk q8_0 -ctv q8_0 --flash-attn on -ngl 99`:
  - MTP adds +2.9 GiB fixed GPU shared memory (10.0 → 12.9 G) and +0.4 GiB mapped weights.
  - Host malloc grows 3.4 → **15.0 GB** during a 95.9k-token session, versus 4.7 → 5.4 GB for 59.6k tokens without spec. It is released only on slot release.
  - Peak RSS is 47.2 GB with MTP vs 39.5 GB without.
  - Run B used `--spec-draft-sampling probabilistic`.

  — [#30174](https://github.com/ggml-org/llama.cpp/issues/30174)
- **#27756 (open).** Qwen3.8-27B (qwen35-hybrid, 48 GDN + 16 attention layers) "silently emits EOS as the first generated token once the prompt exceeds ~130k positions" on CUDA and CPU (commit ee4c505, 2026-08-19; still present at 539f245 on 2026-08-26). Later probing found non-monotonic failing "holes" from about 96.5k tokens, and failures at every depth ≥ about 174k. The same prompt passes on vLLM, so the reporter concludes the cause is "engine-side, not model-side". Qwen3.5-35B-A3B (30 GDN layers) passes at 243k. — [#27756](https://github.com/ggml-org/llama.cpp/issues/27756)
- **#26425 (open), MTP inter-request state.** "MTP retains inter-request state causing non-deterministic output and model degradation" (Qwen3.6-35B-A3B). It is reduced but not eliminated with `--parallel 1`. A commenter traced one variant to `common_context_can_seq_rm()` being destructive if called after prefill. — [#26425](https://github.com/ggml-org/llama.cpp/issues/26425). Related: #23577 "MTP with Qwen3.6 27B outputs repeated //// after long session" (open). — [#23577](https://github.com/ggml-org/llama.cpp/issues/23577)
- **#27151 (closed stale), MTP acceptance collapse.** Draft acceptance fell to 1 of 633 on Qwen3.8-27B with `ggml-org/mtp-Qwen3.8-27B-Q4_0.gguf` on Vulkan; restarting the server fixed it. The trigger was `RADV_DEBUG=nocompute`; a second user saw acceptance decay over time on CUDA. — [#27151](https://github.com/ggml-org/llama.cpp/issues/27151)
- **#25489 (open).** MTP throughput dropped 15–20 % from b9235 (the MTP clean-up PR #23269). One user reports prefill "basically halved", and another saw heavy decode drops past 60k context. Not bisected. — [#25489](https://github.com/ggml-org/llama.cpp/issues/25489)
- **Other open MTP issues** (mostly multi-GPU, CUDA or Vulkan, not Metal): #28790 (draft-mtp about 57× prefill slowdown on a Windows MSVC build); #27428 (draft-mtp roughly halves prompt processing on multi-GPU layer split, single GPU fine); #29044; #28158 (out-of-bounds token id 248320 on Vulkan); #27122 / #29868 (lockups with `--split-mode tensor`); #30424 (`llama-fit-params` rejects `--spec-type`/`-md`). — [GitHub issue search](https://github.com/ggml-org/llama.cpp/issues?q=draft-mtp)
- **Chat template.** #29947 (open, 2026-10-04): Qwen3.8-27B + opencode + opencode-tool-search plugin raises a Jinja error "While executing CallExpression at line 106". — [#29947](https://github.com/ggml-org/llama.cpp/issues/29947). #27661 (closed): an inline `</think>` inside the thinking block was mis-parsed as end of reasoning. — [#27661](https://github.com/ggml-org/llama.cpp/issues/27661). #27802 (open): "Qwen3.8 conversation/quantization issue?". — [#27802](https://github.com/ggml-org/llama.cpp/issues/27802). #28848 (open): server queued a 783k-token prompt against a 262k ctx, "likely reasoning-content re-injection". — [#28848](https://github.com/ggml-org/llama.cpp/issues/28848)
- **Effort levels.** `reasoning_effort: "high"` raises a Jinja exception; valid values are `low`, `medium`, `xhigh`, and the top-level `reasoning_effort` field is silently ignored, so pass it via `chat_template_kwargs`. MTP cannot be toggled per request (server restart needed). — [scriptable.com](https://scriptable.com/posts/llama-cpp/run-qwen3-8-27b-llama-cpp-macos/). Unsloth says the default effort is `xhigh` and passes it with `--chat-template-kwargs '{"reasoning_effort":"medium"}'`. — [unsloth docs](https://unsloth.ai/docs/models/qwen3.8)
- **`preserve_thinking`.** The model card says "reasoning context from historical messages is retained via `preserve_thinking`". — [unsloth README](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/raw/main/README.md). The llama-server flag is `--reasoning-preserve` (default enabled). — [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md). Users also pass `--chat-template-kwargs '{"enable_thinking": false,"preserve_thinking": true}'`. — [#27151 comment](https://github.com/ggml-org/llama.cpp/issues/27151)
- **Metal kernels.** All GDN kernel work found is CUDA/HIP/SYCL/WebGPU: "CUDA: Fuse GDN alpha/beta projections" (#29187 open), "cuda, hip: GDN chunked kernel" (#29353 open), "ggml-webgpu: add fused gated_delta_net" (#28976 merged). SYCL GDN "token soup on long prompts" (#29183 and #29167 open) is SYCL-only. — [PR search](https://github.com/ggml-org/llama.cpp/pulls?q=qwen3.8)

### Inferences
- A sensible Apple Silicon launch for the dense 27B on b11569 is:

  ```
  llama-server -m <gguf> [-md mtp-*.gguf] --spec-type draft-mtp --spec-draft-n-max 2 -np 1 --no-kv-unified -fa on -ngl 99 -c <ctx> --jinja
  ```

  - `--spec-draft-n-max 2` because the repo's Qwen3.6 study and sudoingX both found 2 best on Apple.
  - `-np 1 --no-kv-unified` defensively: #30368 is Flash-Next-specific, but the default auto-slots turn kv-unified on.
  - Use `-ctk/-ctv q8_0` only if context exceeds about 128k.
- No source shows a Metal slow path specific to Qwen3.8-27B. The Metal risks are memory (#30174) and long-context correctness (#27756).
- Keep KV f16 for ≤128k, where it costs only about 8 GiB (see section 6).

### Gaps
- I could not run the local b11569 binary: `~/.local/opt/qwen38/llama-b11569` does not exist on this host, so the flags come from master's README, not b11569's `--help`.
- I found no maintainer response yet on #30174 or #30368.
- I could not confirm the exact build that first loaded Qwen3.8-27B. Day-one evidence is b10330 (2026-08-18) and b10444 (#27151, 2026-08-15).

## 3. Measured decode/prefill on Apple Silicon (with and without MTP)

### Takeaway
The best controlled Apple GGUF measurement is on **M5 Max 128 GB with ggml-org Q4_K_M** (llama.cpp b10330, Aug 2026):
- about **25.5–26 t/s decode without MTP**
- **44–48 t/s mean with the MTP sidecar** (1.74–1.84×, acceptance 61.5–65.1 %)
- prefill about 114–132 t/s, about 9 % slower with MTP

On M3 Ultra, sudoingX measured Q6_K at only 22.8 → 24.2 t/s with MTP (acceptance about 0.80), and a 24 GB base M4 saw no gain. I found **no published M4 Max GGUF+MTP number for the 27B**. The only M4 Max Qwen3.8-27B GGUF data is a host-memory bug report without throughput. MLX on M4 Max: about 20 t/s at 6-bit and 25–28.5 t/s at 8-bit with MTP (oMLX).

### Cited Findings
- **M5 Max 128 GB, macOS 26.5.2, llama.cpp b10330 (Homebrew), ggml-org Q4_K_M + mtp Q4_0, f16 KV, default 4 slots / kv_unified, validated 2026-08-18.**

  | Run | Prefill (t/s) | Decode (t/s) |
  |---|---:|---:|
  | CLI, no MTP | 131.9 | 26.1 |
  | Single sample, no MTP | 113.9 | 25.9 |
  | Single sample, MTP | 76.7 | 55.6 |
  | Server bench, 6 samples, no MTP | — | 25.92 (25.80–26.17) |
  | Server bench, 6 samples, MTP | — | 47.64 (31.58–56.89) |
  | Server bench, 15 samples, no MTP | — | 25.50 |
  | Server bench, 15 samples, MTP | — | 44.37 (27.41–55.73) |

  Acceptance was 342/525 = 65.1 % and 885/1,440 = 61.5 %. Prefill with MTP was about 9 % slower (about 109 vs about 100 t/s). — [scriptable.com](https://scriptable.com/posts/llama-cpp/run-qwen3-8-27b-llama-cpp-macos/)
- **Mac Studio M3 Ultra 96 GB, Q6_K, draft-mtp n-max 2:** 22.8 → 24.2 t/s, acceptance 0.53–0.95 (aggregate 0.798 = 1681/2106). **Apple M4 24 GB (Metal):** 5.8 → 5.8 t/s, "a wash within noise"; code +9–10 %, prose −22–24 %. `-b 512 -ub 512` was needed because the default `-b 2048` OOMs the spec arm. Caveats: use `--parallel 1` (the spec advantage is gone by 4 concurrent streams), and `-p-min` gating can hurt fast cards. — [sudoingX/qwen38-mtp](https://github.com/sudoingX/qwen38-mtp)
- **Mac Studio M3 Ultra 256 GB, Ollama ≥0.32.12, Q4_K_M (~17 GB), 27 Aug 2026:**

  | Model | Decode (t/s) | Prefill (t/s) |
  |---|---:|---:|
  | Qwen3.8 27B Q4_K_M | 14.0 avg (13.2–15.4) | 93.1 |
  | qwen3.6:27b | 28.6 | 95.0 |
  | UD-IQ1_M in llama-bench | 27.2 | 309 |

  Qwen3.8 used 890–1,090 tokens per answer vs 1,950–3,340 for Qwen3.6. — [terminalbytes.com](https://terminalbytes.com/run-qwen-3-8-27b-locally/). These Ollama numbers conflict with the about 23–26 t/s llama.cpp numbers on similar-bandwidth chips above; the article does not say whether MTP was active.
- **Community Mac rows (social posts compiled on one page):**
  - M4 Max 64 GB, 4-bit, unnamed runtime: "~15 tok/s", 32 s prefill for a 6,000-token prompt
  - M3 Ultra MLX, no MTP: 13 t/s
  - Mac mini M4 Pro 24 GB: 15.1 t/s (thinking)
  - M5 Max with MTPLX: 73 t/s peak (not sustained)
  - M4 Max, three unnamed engines with DFlash 2 drafting: 154 / 146 / 146 t/s vs 29–31 without

  — [vramcalculator.com](https://vramcalculator.com/qwen3-8-27b-speed/). These are secondary and unverified.
- **MLX on M4 Max (oMLX benchmark uploads):**
  - Qwen3.8-27B-oQ8e-mtp, 8-bit, MTP on, M4 Max 40-core GPU 64 GB, oMLX v0.6.3rc3, 2026-08-27: PP 191.8 / TG 28.5 t/s at 1k; PP 198.9 / TG 25.0 at 4k; TTFT 20.6 s at 4k; peak 38.26 GB; batch 4× = 62.5 TG t/s. — [oMLX b2swmyox](https://omlx.ai/benchmarks/performance/b2swmyox)
  - MLX-6bit on M4 Max 48 GB: about 20.2 TG / 243.0 PP t/s at 1k. — [oMLX p3kbtfg6](https://omlx.ai/benchmarks/performance/p3kbtfg6) (via search snippet)
  - 4-bit on M4 Max 64 GB: 65.1 TG / 216.9 PP at 4k, dropping to about 27 at 8k, per search snippet. — [oMLX u19dattd](https://omlx.ai/benchmarks/performance/u19dattd) (not fetched; the 65 t/s figure is suspicious)
- **CUDA reference points (not Apple):**
  - RTX 3090, UD-Q4_K_XL 32K: 43.9 → 79.6 t/s at n-max 2, acceptance 0.78
  - RTX 5090, Q6_K 128K: 61.9 → 130.0
  - Ollama 0.33.2–0.34.2 on NVIDIA with qwen3.8:27b: 107–115 t/s at acceptance 0.939 on a counting prompt

  — [sudoingX](https://github.com/sudoingX/qwen38-mtp), [Ollama #18541](https://github.com/ollama/ollama/issues/18541)

### Inferences
- M4 Max has 546 GB/s of memory bandwidth vs about 614 GB/s on the M5 Max (bandwidth from [zachrattner.com](https://zachrattner.com/projects/ai-mac-cluster/agentic-coding)). A Q4_K_M no-MTP decode of about 22–24 t/s on the M4 Max is a plausible extrapolation, not a measurement; Q8_0 would be about 13–15 t/s.
- MTP gains on Apple are inconsistent across sources: +80 % on M5 Max (Q4, 4 slots), +6 % on M3 Ultra (Q6_K), 0 % on a base M4. The repo's own Qwen3.6-27B result (+15–28 % structured, −8 % creative at n=2) sits in between. A local A/B is required; quote both the decode gain and the prefill penalty (about −9 % on M5 Max).
- Compared with the repo's MLX 6-bit Qwen3.6-27B (~20 t/s), GGUF Q4_K_M + MTP on the M4 Max may roughly double decode on structured output. Prefill (~100–130 t/s llama.cpp vs ~190–240 t/s MLX at short context) looks like the weaker side of GGUF on Apple, by these single-source numbers.

### Gaps
- No M4 Max llama-bench (`pp512` / `tg128`) for Qwen3.8-27B GGUF at Q4_K_M, Q5, Q6 or Q8 was found, with or without MTP.
- No M5 Max or M3 Ultra numbers at Q8_0 GGUF.
- I could not search Reddit directly (the MCP server has no search), so r/LocalLLaMA llama-bench threads were not covered.

## 4. Unsloth guide for Qwen3.8-27B

### Takeaway
Unsloth recommends 4-bit (UD-Q4_K_XL) for 16–19 GB devices, the Qwen sampling presets, and `reasoning_effort` via chat-template kwargs (default `xhigh`). It gives llama-cli and `unsloth run` commands but **no llama.cpp MTP flags** on the Qwen3.8 page; it only says to budget 1–2 GB extra for MTP.

### Cited Findings
- Memory table (RAM + VRAM or unified):

  | Precision | 1-bit | 2-bit | 3-bit | 4-bit | 6-bit | 8-bit | BF16 |
  |---|---|---|---|---|---|---|---|
  | Memory | 7–8 GB | 9–11 | 12–14 | 16–19 | 23–26 | 31 | 56 |

  Plus "1-2GB extra headroom" for MTP. Context is 262,144, extendable to 1M via YaRN. — [unsloth docs](https://unsloth.ai/docs/models/qwen3.8)
- Sampling presets:
  - Thinking: temp 1.0, top_p 0.95, top_k 20, min_p 0, presence 0, repetition 1.0
  - Instruct: temp 0.7, top_p 0.80, top_k 20, min_p 0, presence_penalty 1.5

  Effort levels are `xhigh` (default), `medium`, `low` and none, set via `--chat-template-kwargs '{"reasoning_effort":"medium"}'`. "Preserve Thinking" keeps the previous turn's trace. — [unsloth docs](https://unsloth.ai/docs/models/qwen3.8)
- Commands: download with `hf download unsloth/Qwen3.8-27B-GGUF --include "*UD-Q4_K_XL*"`, then run `./llama.cpp/llama-cli --model …UD-Q4_K_XL.gguf --temp 1.0 --top-p 0.95 --top-k 20 --min-p 0.0`. Build with `-DGGML_CUDA=OFF` on Mac ("Metal support is on by default"). IQ1_XXXS (Q1_0) needs the `unslothai/llama.cpp` `iq1-narrow` branch. — [unsloth docs](https://unsloth.ai/docs/models/qwen3.8)
- The model card recommends output budgets of up to 262,144 reasoning + 131,072 final tokens, and the `presence_penalty` 0–2 knob against repetition. — [unsloth README](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/raw/main/README.md)

### Inferences
- The unsloth page does not settle the MTP flags. Use the llama.cpp README defaults (`--spec-draft-n-max` default 3) and tune down to 2 per the repo's prior study.

### Gaps
- I did not fetch the separate unsloth MTP doc page linked from the guide, so any unsloth-recommended `--spec-draft-n-max` or p-min value is unknown.

## 5. LM Studio and Ollama

### Takeaway
**LM Studio 0.4.26 (2026-10-13)** ships llama.cpp runtime **2.50.0 = upstream b11337**, which is older than b11569. MTP drafters have been supported since 0.4.22 (engine ≥2.29.1). **Ollama v0.40.3 (2026-10-11)** runs `qwen3.8:27b` through a vendored llama-server with draft-mtp on by default (`--spec-draft-n-max 4`). I found no Qwen3.8-27B MTP speed figures on Mac from either.

### Cited Findings
- LM Studio release history:
  - 0.4.26 (Oct 13, 2026): "Updated the llama.cpp runtime to 2.50.0 (upstream b11337)"
  - 0.4.25 (Sep 19): Splash engine on Apple Silicon M3+ / macOS 26.4+
  - 0.4.23 (Aug 28): "Improve reliability of Qwen 3.8 Flash Next"
  - 0.4.22 (Aug 28): "Support for DFlash, DSpark, and MTP assistant drafters … Requires llama.cpp engine version 2.29.1 or newer"

  — [LM Studio changelog](https://lmstudio.ai/changelog/lmstudio)
- LM Studio bug tracker items touching Qwen3.8-27B:
  - #2284 "Reasoning setting 'high' is not supported by model 'unsloth/Qwen3.8-27B-GGUF/…UD-Q4_K_XL.gguf'" (open)
  - #2471 tool calls lose an optional nested field (engine 2.45.0)
  - #2298 `/v1/responses` multiple developer messages → Jinja 500
  - #2362 MLX Qwen3.8 27B 6-bit omitted from catalog
  - #2478 Splash 0.0.5 in LM Studio gives gibberish Qwen3.8 output

  — [lmstudio-bug-tracker](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues?q=qwen3.8)
- Ollama latest stable is v0.40.3 (2026-10-11); v0.40.4-rc1 came out 2026-10-12. — [Ollama releases](https://github.com/ollama/ollama/releases). An Ollama 0.40.0 log shows runner options `-np 1 --flash-attn on --spec-type draft-mtp --spec-draft-n-max 4 --context-shift --chat-template chatml --no-jinja` with renderer `qwen3.8` / parser `qwen3.5`. — [Ollama #18840](https://github.com/ollama/ollama/issues/18840)
- Ollama issues:
  - #18541 (closed same day, 2026-09-19): a reported MTP regression in 0.34.2 was not reproduced; a maintainer measured 106.9–115.2 t/s with acceptance 0.939 across 0.33.2–0.34.2 (NVIDIA, KV q8_0, FA). — [Ollama #18541](https://github.com/ollama/ollama/issues/18541)
  - #18632: `think: "high"`/`"max"` silently run `medium`; `xhigh` is reachable only by an undocumented string. — [Ollama #18632](https://github.com/ollama/ollama/issues/18632)
  - #18840: /api/chat 500 after a normal llama-server completion (open). — [Ollama #18840](https://github.com/ollama/ollama/issues/18840)
  - #18131: MLX prefix cache fixed 8 GiB budget. — [Ollama #18131](https://github.com/ollama/ollama/issues/18131)
- Ollama tags: `qwen3.8:latest` 4-bit 18 GB, `qwen3.8:27b-q8_0` 30 GB, `qwen3.8:27b-bf16` 56 GB. Default context is 256k when VRAM ≥48 GiB. — [zachrattner.com](https://zachrattner.com/projects/ai-mac-cluster/agentic-coding). Ollama M3 Ultra measurement: 14.0 t/s (section 3). — [terminalbytes](https://terminalbytes.com/run-qwen-3-8-27b-locally/)

### Inferences
- LM Studio's b11337 predates the October MTP fixes (#30257 on 10-10) and Metal fixes (#30373 in b11569). For a controlled test, the repo's isolated b11569 llama-server is the more current runtime. LM Studio is useful only to check whether its "Draft MTP" toggle still behaves as in the July Qwen3.6 study.
- Ollama on Mac uses `--context-shift` and `--no-jinja`/chatml. That differs from llama-server's `--jinja` path, so tool-call and thinking behaviour may not match.

### Gaps
- No Mac speed numbers for LM Studio or Ollama with MTP on Qwen3.8-27B.
- I could not confirm whether LM Studio auto-enables MTP for unsloth GGUFs with inline heads.

## 6. KV cache cost and maximum context on 128 GB; KV quantization

### Takeaway
Only the 16 full-attention layers grow KV, at **64 KiB/token at f16** (16 layers × 4 KV heads × 256 dim × K+V × 2 bytes). Measured: 512 MiB at 8k, 8 GiB at 131k, **16 GiB at 262,144**. The 48 Gated DeltaNet layers add a fixed recurrent state of about 150 MiB per slot (598.5 MiB for 4 slots). On 128 GB, full native 262k context fits easily even at Q8_0 weights with f16 KV (about 47 GB). The real ceiling on usable context is the engine-side silent-EOS bug past about 96–130k (#27756), not memory.

### Cited Findings
- M5 Max, Q4_K_M, f16 KV, 4 slots:

  | `-c` | KV cache |
  |---:|---:|
  | 8,192 | 512 MiB |
  | 32,768 | 2,048 MiB |
  | 131,072 | 8,192 MiB |
  | 262,144 | 16,384 MiB |

  Recurrent state is 598.50 MiB at every size. Weights are 18,084 MiB Metal + 682 MiB CPU, and the loaded server before cache is about 19.0 GiB. Totals are about 27.6 GiB at 131k and about 35.6 GiB at 262k. — [scriptable.com](https://scriptable.com/posts/llama-cpp/run-qwen3-8-27b-llama-cpp-macos/)
- At 262k with q8_0 K/V on Metal, the M4 Max showed GPU shared memory of 10.0 G without MTP and 12.9 G with MTP. — [#30174](https://github.com/ggml-org/llama.cpp/issues/30174)
- Each slot keeps its own copy of the 48 linear-attention layers' state; four slots cost 0.44 GiB more than one slot from 32K to 256K. — [vramcalculator.com](https://vramcalculator.com/qwen3-8-27b-speed/)
- KV quantization effects:
  - q4_0 cache cost about 20 % decode at 32k on a Tesla T4. On an L4, f16 slowed about 10 % from 29k to 59k, with larger drops at 118k/236k attributed to q8_0/q4_0 caches. — [vramcalculator.com](https://vramcalculator.com/qwen3-8-27b-speed/)
  - For Qwen 35B: "q8/q8 was just as good as f16, but going any lower degraded performance … q4_1 will definitely cause degraded long-horizon performance". — [#26425 comment](https://github.com/ggml-org/llama.cpp/issues/26425)
- sudoingX's 24 GB-card recipe uses `--cache-type-k q4_0 --cache-type-v q4_0` because context creation fails past about 90K next to 17 GB of weights. — [sudoingX](https://github.com/sudoingX/qwen38-mtp)
- Instant-EOS / degraded generation appears from about 96.5k tokens (non-monotonic) and is deterministic at ≥ about 174k. It reproduced on CUDA, on CPU with f16 KV, and on ik_llama.cpp, but not on vLLM. — [#27756](https://github.com/ggml-org/llama.cpp/issues/27756)

### Inferences
- KV at q8_0 is about 34 KiB/token (q8_0 = 34 bytes per 32 values) → about 8.5 GiB at 262k. q4_0 is about 18 KiB/token → about 4.5 GiB. These are computed from the measured f16 figure.
- On 128 GB there is no memory reason to quantize KV for ≤262k. Keep f16, or q8_0 at most, to avoid the decode and quality penalties.
- YaRN to 1M would need about 64 GiB f16 KV (about 34 GiB at q8_0). That is memory-feasible but untested and likely affected by #27756.
- MTP on Metal adds about 3 GiB fixed plus a host heap that can reach about 10+ GB over a 96k session (#30174). Budget for it in two-resident-model plans.

### Gaps
- No Apple-specific measurement of decode speed vs KV type (f16 / q8_0 / q4_0) for Qwen3.8-27B was found.

## 7. Prefix / prompt cache in llama-server for agent workloads

### Takeaway
On hybrid/recurrent models, llama-server cannot truncate KV arbitrarily. It relies on **context checkpoints** of the full recurrent state (default up to 32 per slot, min spacing 8192 tokens, roughly 150 MiB each for Qwen3.8-27B). Reuse works only when a new prompt diverges at or after a saved checkpoint. `--cache-reuse` (KV shifting) is off by default. Slot save/restore to disk exists (`--slot-save-path`); session-keyed automatic save/restore is still an open PR (#29738). This directly affects `cache_probe.py`'s "cache hit on tool turns".

### Cited Findings
- Flags (master README):
  - `-ctxcp/--ctx-checkpoints N` (default 32), `-cms/--checkpoint-min-step` (default 8192, 0 = no minimum)
  - `-cram/--cache-ram` (default 8192 MiB; −1 no limit; 0 disables)
  - `--cache-idle-slots` (default enabled, "save idle slots to the prompt cache on new task, and clear them when using unified KV")
  - `--cache-reuse N` ("min chunk size to attempt reusing from the cache via KV shifting", default 0)
  - `--slot-save-path` plus the `/slots` save/restore endpoints

  — [server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- Checkpoint placement: "For every new prompt the server creates context checkpoints (by default: start of the last user message, `4 + n_ubatch` tokens before the end, and 4 tokens before the end). For recurrent / hybrid models each checkpoint copies the full recurrent state". On Qwen3.8-27B with about 21 recurrent layers on an RPC worker, each checkpoint was about 66–69 MB. Open PR #29463 adds `LLAMA_CKPT_OFFSETS` / `LLAMA_CKPT_LAST_USER`, and also makes MTP draft state checkpoint/restore consistently with the target. — [PR #29463](https://github.com/ggml-org/llama.cpp/pull/29463)
- Open PR #29738 "session-keyed automatic slot save/restore" keys off client session-id headers (tested with the Pi agent), so that "switches between sessions … prefill phases are avoided by loading the relevant slots from disk". — [PR #29738](https://github.com/ggml-org/llama.cpp/pull/29738)
- Open PR #30201 "server: allow checkpoint after last media" (multimodal). — [PR #30201](https://github.com/ggml-org/llama.cpp/pull/30201)
- #30366 (open): "server: slot KV is reused after the global lora config changes". — [#30366](https://github.com/ggml-org/llama.cpp/issues/30366)
- Ollama's MLX runner leaked about 0.43 GiB (three recurrent snapshots) per tool-call request on qwen3.6:27b-mlx (#18620, closed). An earlier issue reported no prefix caching between requests (#17829, closed). This is evidence that the snapshot-per-turn pattern is the norm for this architecture family. — [Ollama #18620](https://github.com/ollama/ollama/issues/18620), [Ollama #17829](https://github.com/ollama/ollama/issues/17829)
- The #30174 host-heap growth under draft-mtp is "only released when the slot is released", which interacts with long agent sessions held in one slot. — [#30174](https://github.com/ggml-org/llama.cpp/issues/30174)

### Inferences
- Recurrent state per checkpoint for all 48 GDN layers is about 48 × 48 heads × 128 × 128 × 4 B ≈ 151 MB (computed). That matches 66–69 MB for 21 layers and 598.5 MiB for 4 slots. With 32 checkpoints per slot this is up to about 4.7 GB of checkpoint RAM, bounded by `--cache-ram` (8 GiB default).
- Agent-turn behaviour with default checkpoints:
  - A tool turn that appends tool output after the previous assistant message should hit the "4 tokens before the end" checkpoint of the previous request, so cache hit should be high.
  - If the client re-renders history, for example by stripping or re-injecting `<think>` content under `preserve_thinking=false` or `--reasoning-preserve` mismatches, the prefix diverges before the last checkpoint and forces a re-prefill from an earlier checkpoint or from zero.
  - `cache_probe.py` should therefore test `--reasoning-preserve` on vs off, and `--parallel 1` vs auto slots, where `--cache-idle-slots` clears unified KV.
- `--cache-reuse` (KV shifting) is unlikely to help, because recurrent state cannot be shifted. I did not find an explicit statement of this for the current master.

### Gaps
- I found no measured cache-hit rates or TTFT-per-tool-turn for Qwen3.8-27B in llama-server on Apple Silicon.
- I found no explicit documentation of `--cache-reuse` behaviour for hybrid models on current master.
- I did not investigate whether `--cache-ram` checkpoints and slot-save interact correctly with draft-mtp state on b11569 (PR #29463 suggests the draft state was not checkpointed consistently before that PR).
