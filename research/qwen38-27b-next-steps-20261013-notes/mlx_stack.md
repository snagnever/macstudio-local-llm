# MLX stack for dense Qwen3.8-27B on Mac Studio M4 Max 128 GB (state as of 2026-10-13)

Scope: runtimes, quant packs and measured Apple Silicon speeds for the **dense** Qwen3.8-27B on MLX. Baseline from the local repo (`bench/qwen3.8-prefix-cache`, overview generated 2026-08-28) is **prior state**: oMLX 0.6.3rc2 / MTPLX 2.9–2.11 / mlx-dspark ~0.14–0.15. In that baseline, decode was about 32–42 tok/s at 32K and about 25 tok/s at 128K. MTPLX MTP collapsed to 6–9 tok/s at 262K, while oMLX and DFlash2 held 14–15 tok/s.

Collection method: GitHub release bodies via `gh release view`, the HF Hub API (`/api/models`, `/commits/main`, `/tree/main`), the raw omlx.ai leaderboard HTML, and vendor blogs. Revision hashes are HF `sha` values or git tag SHAs as of 2026-10-13.

---

## 1. mlx-serve: dense qwen3.8 support, MTP, prefix cache, flags, 26.10.x notes

### Takeaway
mlx-serve fully supports the dense 27B, which loads as the `qwen3_5` architecture. Since 26.10.1 the native MTP head is on by default for both dense and MoE. ddalcu's own 27B packs bundle a DFlash2 drafter (`drafter/`, added 2026-09-29) that loads automatically. 26.10.1 claims +28% decode on M4 Max for "27B 4-bit + drafter" versus 26.9.6. 26.10.2 (2026-10-12) has no 27B-specific perf item. Its relevant changes are the reasoning-replay behaviour, an SSD-only prompt cache, and MTP depth bounds / greedy tail. PLE (`--ple-gpu`) is a Flash-Next-only knob and does not apply to the dense model.

### Cited Findings
- **Versions:** v26.10.2 is "Latest", published 2026-10-12T23:53Z, tag SHA `ccedc6a4820f48e576633062232ed0cba1139616`. v26.10.2-pre-release.1 was published 2026-10-11. v26.10.1 was published 2026-10-01, tag SHA `02bee553f48cd3bc7d82aba0f8073820bd924738`. v26.9.6 was published 2026-09-26. Main HEAD is `3877b792` (2026-10-13). — [mlx-serve releases](https://github.com/ddalcu/mlx-serve/releases)
- **26.10.1 measured gains** (vs shipped 26.9.6, same session, llmprobe; the release reports deltas only, no absolute tok/s):

  | Model | Mac | Decode | Prefill |
  |---|---|---|---|
  | 27B 4-bit + drafter | M5 Ultra | +66% | +14% |
  | 27B 4-bit + drafter | M4 Max | +28% | 0% |
  | 27B 4-bit + drafter | M1 Pro 32 GB | +37% | n/a |

  Output is "exactly the same as in 26.9.6" on 18 models. — [v26.10.1](https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.1)
- **26.10.1, M5 Ultra:** 27B decodes at 245 tok/s at 4-bit (was 197), 190 at 6-bit (was 134) and 168 at 8-bit (was 127). The notes do not state the workload, but these are speculative peak figures. — [v26.10.1](https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.1)
- **26.10.1 speculation changes:**
  - "Every model gets a drafter slot... a model's bundled drafter loads automatically; 27B 6-bit and 8-bit get the full-speed drafter too."
  - "Speculative drafting is now on by default for every model that supports it."
  - "Qwen3.8-27B with DFlash2 tries a tree of drafts each round instead of one path."
  - "DFlash on Nemotron-H and dense Qwen3.5/3.8 matches normal decoding exactly, sampled requests included (4, 6 and 8-bit)."
  - New `--mtp-greedy-tail` flag.

  — [v26.10.1](https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.1)
- **26.10.1 long-context and memory changes:**
  - "After long prompts: past 32k tokens it is about 12% faster, long agent sessions stay cached instead of re-reading the whole conversation every turn." This appears under the Flash Next bullet.
  - On a 32 GB Mac, the 27B with drafter at 16K context refused every request in 26.9.6 once its cache filled. 26.10.1 serves it.

  — [v26.10.1](https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.1)
- **`--ple-gpu`** is described under "Qwen3.8 Flash Next is faster everywhere": "prefill 2-4% faster and decode +15% at 128k. Off by default because it needs the whole table in memory." — [v26.10.1](https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.1)
- **GGUF on the MLX engine (26.10.1):** "Qwen 3.5, 3.6 and 3.8 (dense and MoE)... GGUFs now load straight onto the MLX path... same prefix cache, batching, speculative decoding" (`--mlx-gguf`). — [v26.10.1](https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.1)
- **26.9.6 changes:**
  - GDN layers run as one GPU dispatch ("a few percent on every Mac, 27B included").
  - MTP drafts from the conversation itself (on by default; `MLX_SERVE_MTP_LOOKUP=0` disables it).
  - Earlier turns' thinking is no longer replayed by default. `chat_template_kwargs: {"preserve_thinking": true}` restores it.

  — [v26.9.6](https://github.com/ddalcu/mlx-serve/releases/tag/v26.9.6)
- **26.10.2 items relevant to the dense model:**
  - "Qwen3.8 keeps its earlier reasoning, so follow-ups answer better and up to 8 seconds sooner in long sessions." This appears to reverse or adjust the 26.9.6 default.
  - A model caught repeating itself while thinking now finishes.
  - "An SSD-only prompt cache that holds no idle RAM".
  - "MTP depth bounds and greedy tail".
  - Crash-hardening under load.
  - The Flash-Next linear-attention state is now kept in f32 (`MLX_SERVE_GDN_STATE_F32=0` restores bf16). The notes mention this for Flash Next only.

  The release has no 27B dense speed line. — [v26.10.2](https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.2)
- **Current CLI flags that matter for the dense model:**
  - `--no-mtp`/`--mtp`: the head is on when loaded, and "dense and MoE both default on". `--mtp` is a no-op.
  - `--mtp-min-depth` / `--mtp-max-depth` (1..8).
  - `--mtp-greedy-tail`.
  - `--mtp-history-window N`: past 16K, the head history is limited to the last N tokens ("windowing costs acceptance on stock Qwen heads").
  - `--drafter DIR`, `--draft-block-size`.
  - `--pld` (prompt-lookup decoding, on by default) and `--pld-key-len`.
  - `--kv-quant {off,4,8}` with `--kv-attn-mode {auto,dense,fused}`; fused engages from 8K at 4/8-bit.
  - `--prefill-chunk` (default 8192).
  - `--prefix-cache-mem`: default 2 GB, "or one session at the working context on hybrid (Qwen3.5+...)".
  - `--prefix-cache-disk`: SSD tier; an 11K-token restart TTFT drops from 5.9 s to 0.7 s.
  - `--ctx-size` (auto).
  - `--dspark` is for DeepSeek V4 only.

  — [mlx-serve docs/cli.md](https://github.com/ddalcu/mlx-serve/blob/main/docs/cli.md)
- **Closed issues relevant to agentic use:**
  - #492: a multi-turn tool loop hallucinated on a partial prefix-cache hit with multiple entries (closed 2026-09-21).
  - #696: Claude Code sessions repeatedly prefilled most of the context (closed 2026-10-02).

  — [mlx-serve #492](https://github.com/ddalcu/mlx-serve/issues/492), [mlx-serve #696](https://github.com/ddalcu/mlx-serve/issues/696)

### Inferences
- Flags for the dense 27B on mlx-serve 26.10.2:
  - Use the ddalcu pack. Both MTP and the bundled DFlash2 drafter are loaded automatically.
  - Set `--prefix-cache-mem` explicitly. The hybrid default is "one session at working context". The 27B KV is about 64 KiB/token (see §7), so a 16 GB budget holds roughly 250K tokens of one session.
  - Set `--prefix-cache-disk`.
  - Optionally use `--kv-quant 8` for very long contexts.
  - `--ple-gpu` is irrelevant for the dense model.
- The +28% M4 Max gain in 26.10.1 applies only to the "4-bit + drafter" configuration. Run an A/B of MTP versus DFlash2 drafter on the rig, because the release notes do not say which one wins on M4 Max.

### Gaps
- No absolute M4 Max tok/s for the 27B appears in the 26.10.x notes, only relative deltas.
- When both the native MTP head and the bundled `drafter/` exist, the docs do not say which speculative path mlx-serve uses (or whether it combines them).
- I found no 27B-specific bug fixes listed in 26.10.2-pre-release.1 beyond the general items.

---

## 2. oMLX: version, oQ packs, benchmark pages, spec decoding for dense targets

### Takeaway
The latest is oMLX **0.7.1.dev1** (2026-10-09); the latest stable is **0.7.0** (2026-09-30). 0.7.0 made Lightning MTP and DFlash2 cheaper per verify cycle on Qwen3.8-27B, "with the largest gains at long contexts". Community leaderboard results on **M4 Max 128 GB, oMLX 0.7.0, oQ4e-mtp + Lightning MTP** show 69.0 tok/s TG at 32K and **40.0 tok/s at 128K**. In the repo's August baseline, the 128K figure was about 25. These runs use oMLX's "Code (Python)" benchmark context, which favours speculative acceptance. Jundot re-quantized all 27B oQe packs on 2026-10-11 with the new oQe refit (KL −14 to −18%).

### Cited Findings
- **Versions:** 0.7.1.dev1 was published 2026-10-09, tag SHA `c0b1056b41ebde9422af316cf5038a423eb8f24c`. 0.7.0 was published 2026-09-30, tag SHA `4d4f5a280bc1739ba2cf39c1cee44fd5cc89cb40`. 0.7.0rc1 was published 2026-09-24. 0.7.0 pins mlx-lm `94cdcae` (main after 0.32.0) and dflash-mlx `0.1.10+omlx.9`. — [oMLX releases](https://github.com/jundot/omlx/releases), [v0.7.0](https://github.com/jundot/omlx/releases/tag/v0.7.0)
- **0.7.0 speculative changes:**
  - "DFlash2 and Lightning MTP now do less work per verify cycle on Qwen3.8-27B and Qwen3.8-Flash-Next, with the largest gains at long contexts" (#3958).
  - Exact Lightning MTP: verify rows are bit-identical to serial decode for a single request (#4023).
  - Exact prefix reuse for split-GDN SpecPrefill (#3908).
  - The ANE prefill TypeError from rc1 is fixed (#3957).
  - "oQ A8 prefill on M5: Dense Qwen 4-bit projections silently fell back to W4A16 in rc1" is fixed (#3952).

  — [v0.7.0](https://github.com/jundot/omlx/releases/tag/v0.7.0)
- **0.7.1.dev1 changes:**
  - Concurrent prefills are batched into one forward. For **Qwen3.8-27B oQ4e on M3 Ultra**, mean TTFT dropped from 8.77 to 7.80 s with 8 simultaneous prompts (−11%), from 36.66 to 32.52 s with 8 prompts 0.4 s apart, and from 6.11 to 5.10 s with 4 prompts joining 4 decoding streams.
  - "Qwen3.8-27B oQ8e with INT8 activation prefill: Prefill +25% at 4K, +38% at 16K (M5 Max)". This is an M5-only path that uses the INT8 matrix units.
  - Lightning MTP on Qwen makes file edits 1.5–2× faster at temperature 1.0 (M3 Ultra).
  - **oQe refit** (#4385) "cuts KL to the original model by 11-15%. Only new conversions change."
  - Hybrid-model SSD cache tail cleanup.
  - "34 GiB less transient memory on a 1M-token restore".
  - About 150 `OMLX_*` debug env vars are removed, including `OMLX_QWEN35_ANE_PREFILL`. Use per-model settings instead.

  — [v0.7.1.dev1](https://github.com/jundot/omlx/releases/tag/v0.7.1.dev1)
- **Spec-decoding support for dense targets:**
  - Lightning MTP and DFlash2 both work on the dense 27B.
  - Per-model settings include `mtp_enabled`, `mtp_adaptive_max_depth` (3), `dflash_enabled`, DFlash in-memory/SSD cache, `specprefill_enabled`, `turboquant_kv_enabled`/`turboquant_kv_bits`, `qwen35_oq_a8_enabled`, and the `qwen35_ane_prefill_*` family.

  These come from settings dumps on the benchmark pages below. In 0.7.0, DSpark appears only for DeepSeek V4.1 ("DSpark rewrites"). I found no EAGLE support. — [omlx.ai benchmark grr8n1fk](https://omlx.ai/benchmarks/performance/grr8n1fk), [v0.7.1.dev1](https://github.com/jundot/omlx/releases/tag/v0.7.1.dev1)
- **Leaderboard: M4 Max (40c) 128 GB, oMLX v0.7.0, macOS 26.7.1, `Qwen3.8-27B-oQ4e-mtp`, Lightning MTP depth ≤3, no DFlash, no ANE, no TurboQuant, "Code (Python)" context, 2026-10-05:**

  | Context | PP (tok/s) | TG (tok/s) | Peak memory |
  |---|---|---|---|
  | 1K | 254.5 | 64.5 | 18.5 GB |
  | 4K | 269.6 | 57.4 | 22.0 GB |
  | 8K | 264.8 | 58.4 | 22.5 GB |
  | 16K | 254.7 | 63.9 | 23.4 GB |
  | 32K | 235.9 | 69.0 | 25.2 GB |
  | 64K | 205.5 | 46.4 | 27.8 GB |
  | 128K | 164.0 | 40.0 | 32.3 GB |

  TTFT at 128K was 799 s. — [omlx.ai fxmby881](https://omlx.ai/benchmarks/performance/fxmby881), [omlx.ai 7vyp8wo6](https://omlx.ai/benchmarks/performance/7vyp8wo6)
- **Leaderboard: M4 Max 128 GB, oMLX v0.7.0, `Qwen3.8-27B-oQ8e-mtp`, Lightning MTP, 2026-10-01:**

  | Context | PP (tok/s) | TG (tok/s) | Peak memory |
  |---|---|---|---|
  | 1K | 250.7 | 33.4 | 33.9 GB |
  | 8K | 253.3 | 40.7 | 37.8 GB |
  | 16K | 244.1 | 47.4 | 38.7 GB |
  | 32K | 225.9 | 46.3 | 40.4 GB |
  | 64K | 198.4 | 36.4 | 43.2 GB |
  | 128K | 159.7 | 34.1 | 47.7 GB |

  TTFT at 128K was 821 s. — [omlx.ai 2w1u2zl7](https://omlx.ai/benchmarks/performance/2w1u2zl7)
- **Leaderboard: M4 Max 128 GB, oMLX **v0.7.1.dev1**, macOS 27.0, `Swift-1.5-Qwen3.8-27b-oQ4e-mtp`, Lightning MTP + ANE prefill (fraction 0.45, GDN 0.375), 2026-10-12:**

  | Context | PP (tok/s) | TG (tok/s) | Peak memory |
  |---|---|---|---|
  | 1K | 255.3 | 53.6 | 21.8 GB |
  | 4K | 340.2 | 57.2 | not recorded |
  | 8K | 342.5 | 60.9 | not recorded |
  | 16K | 325.7 | 55.2 | not recorded |
  | 32K | 295.6 | **117.2** | 28.4 GB |
  | 64K | 249.5 | 47.4 | 31.1 GB |

  Batch TG was 53.6 (1×), 69.1 (2×) and 132.5 (4×). — [omlx.ai grr8n1fk](https://omlx.ai/benchmarks/performance/grr8n1fk)
- **Other M4 Max rows:**
  - Top TG rows at 32K (no SpecPrefill) also include `Qwen3.8-27B-oQ4e-mtp` at 105.8 / 100.6 tok/s on **48 GB** with v0.7.1.dev1 (2026-10-11; TG at 16K was 82.1 and at 1K was 55.6).
  - Several 64 GB / 128 GB rows sit at 68.5–69.6 tok/s at 32K (2026-10-01..05).
  - Top rows at 128K: oQ4e-mtp 40.0 (128 GB), ThinkingCap oQ4e-mtp 39.3 / 38.3 (64 GB), Swift-1.5 oQ4e-mtp 38.9 (64 GB, 2026-10-10/11), oQ8e-mtp 34.1, Swift-1.5 oQ8e-mtp 32.7 (128 GB), qwen3.8-27b-oq6-mtp 32.5 (64 GB).

  — [omlx.ai leaderboard, M4 Max filter](https://omlx.ai/benchmarks/performance?model=Qwen3.8-27B&chip=M4&device=%5B%22M4%22%2C%22Max%22%5D&context=131072&sort=tg_tps&order=desc&hide_specprefill=1), [omlx.ai pjd08tia](https://omlx.ai/benchmarks/performance/pjd08tia)
- **Other hardware rows on the leaderboard (2026-10-13 page):**
  - M3 Ultra 60c / 256 GB, `Qwen3.8-27B-4bit` (no speculation flag): TG 37.2 at 4K, 34.6 at 16K, 27.4 at 64K; PP 345.5 / 325.3 / 264.5.
  - M4 Pro 20c / 48 GB, MTPLX Optimized-Speed run through oMLX: TG 12.7 at 1K.

  — [omlx.ai leaderboard](https://omlx.ai/benchmarks/performance?model=Qwen3.8-27B)
- **Open oMLX issues on the 27B:**
  - #4214: greedy MTP output on Qwen3.8-27B varies between runs since #3958 (M4 Max 64 GB, MLX 0.32.2).
  - #4249: the Lightning MTP toggle on oQ8e-fp16-mtp is rejected until TurboQuant KV is enabled (0.7.0).
  - #3767: multi-request Lightning MTP with TurboQuant KV crashes (0.7.0.dev4).
  - #3737: VLM MTP verify is 25–70% slower on the 27B in 0.7.0.dev4.
  - #3952: prefill speed dropped after 0.7.0rc1.
  - #4244: context-bench capping.

  — [omlx #4214](https://github.com/jundot/omlx/issues/4214), [#4249](https://github.com/jundot/omlx/issues/4249), [#3767](https://github.com/jundot/omlx/issues/3767), [#3737](https://github.com/jundot/omlx/issues/3737)

### Inferences
- **The TG jumps at 32K are artifacts.** Examples are 117.2 versus 55.2 at 16K on the Swift pack, and 105.8 versus 82.1 on the 48 GB rows. They are almost certainly the "Code (Python)" fill text letting Lightning MTP / context lookup copy long runs. They are not real 32K agentic decode. The 64K and 128K rows (46–47 and about 40) are more trustworthy for planning.
- **oMLX 0.7.0+ with oQ4e-mtp is now the strongest documented M4 Max 128 GB path for the dense model at 64–128K.** It reaches about 40 tok/s at 128K, versus about 25 in the repo's August measurement. This makes a re-test worthwhile.
- **Prefill on M4 Max stays slow:** about 250 tok/s at ≤16K and 164 tok/s at 128K, roughly 13 minutes to cold-prefill 128K. Prefix-cache hits are therefore mandatory for agent use.
- **The repo's existing Jundot oQ8e pin is now outdated.** The repo pinned oQ8e at `c99e5aad` (August upload). The current revision is `6c76ddfb82af` (2026-10-11 re-quant).

### Gaps
- I could not retrieve M3 Ultra and M5 Max filtered leaderboards (HTTP 429 rate-limit), so M5 Max / M3 Ultra numbers for oQ4e+MTP/DFlash at 32K/128K are missing here. Earlier references (repo C13/C14) cover the M5 Pro.
- I found no M4 Max leaderboard row for oQ4e + DFlash2 on 0.7.x.
- The leaderboard does not publish the HF namespace of the pack (for example Jundot vs gcoli vs re-quant date).

---

## 3. MTPLX (Youssofal): version, 27B pack revisions, long-context/session-cache status

### Takeaway
The latest is **MTPLX 2.12.2** (2026-10-03). The 2.11.3 → 2.12.2 releases mainly fix memory accounting, session-cache retention and 8/4-bit KV NaNs on the 27B. They also fix an OOM at 261K on the first verify step. The structural long-context weakness the repo saw (MTP depth-3 verify re-reading the KV) is still reported as an **open** issue (#506). The 27B packs have had no weight changes since August/September; only metadata and sampler stamps changed. All published 27B speed numbers are on an **M5 Max**.

### Cited Findings
- **Versions:** 2.12.2 was published 2026-10-03, tag SHA `56ba82c095a262fbe36ddebf37bf334918073877`. 2.12.1 was published 2026-10-02, 2.12.0 on 2026-09-24, 2.11.3 on 2026-09-17, and 2.11.2 on 2026-09-06. — [MTPLX releases](https://github.com/youssofal/MTPLX/releases)
- **2.12.2:** fixes the 2.12.1 memory guard that refused ordinary prompts. On a **32 GB Mac**, 27B Optimized Speed now serves 6,800 and 7,800-token prompts and 4 agent turns. A 99,355-token 27B turn on a 48 GB Mac now runs in 1,024-token chunks. "A 1,024-token chunk uses about 1 GiB less than a 2,048-token one on the 27B models." — [v2.12.2](https://github.com/youssofal/MTPLX/releases/tag/v2.12.2)
- **2.12.1:**
  - "Use 8-bit or 4-bit KV cache on the 27B with a long answer (#526): every logit came back as NaN" is now fixed. An 18,893-token answer completed.
  - "a 250K-token 27B snapshot is 15.3 GiB, not the 4.9 GiB of its 4-bit pages"; the draft-head history costs 4,096 bytes/token on the 27B.
  - "Qwen 3.8 27B Optimized Quality's session cache under a full 262,144-token window is 42.5 GiB instead of 48 GiB."
  - Pressure trims now reach the session cache (#525).
  - SSD session-cache save fixes (#536).

  — [v2.12.1](https://github.com/youssofal/MTPLX/releases/tag/v2.12.1)
- **2.12.0:**
  - Adds Ternary Bonsai 2 27B, Prism ML's ternary rebuild of Qwen3.8-27B: 8.85 GB, `Youssofal/Ternary-Bonsai-2-27B-MTPLX-Optimized-Speed`.
  - On an **M5 Max**, Bonsai reaches 64.4 tok/s after a 4,061-token prompt versus **52.6 tok/s for Qwen3.8-27B Optimized Speed**, and 57.1 versus **51.0** after 16,350 tokens. Peak memory is 11.4/14.6 GB for Bonsai versus **23.9/27.0 GB for the 27B**. Settings: temperature 1.0, top-p 0.95, top-k 20, thinking off, 512-token answers.
  - Bonsai's draft depth defaults to 1 because depth 3 was 14% slower.
  - Session-cache fixes: #499 (a 149,649-token session over its allowance was re-prefilled every turn, 570 s TTFT) and #456 (3.7 GiB/turn growth).

  — [v2.12.0](https://github.com/youssofal/MTPLX/releases/tag/v2.12.0)
- **2.11.3:**
  - Correctness audit after reports that "the 8-bit Quality pack loops".
  - The Qwen3 pre-tokenizer regex was restored, and the loader fixes it for the 27B packs on the Hub.
  - A context-copy proposer can propose up to 24 tokens.
  - "At the pack's 261,120-token context the first speculative verify step ran out of GPU memory... about 6.4 GB across the twelve full-attention layers"; the verify KV update was rewritten.

  The note's "twelve" conflicts with the 16 full-attention layers in the 27B config (§7). The passage may describe Flash-Next. — [v2.11.3](https://github.com/youssofal/MTPLX/releases/tag/v2.11.3)
- **Open issue #506 (2026-09-18, OPEN):** "KV traffic per context token rises from 1.17× ... at depth 1 to 3.53× at depth 3". The packed-GQA verify kernel "declines every call", with an estimated "+30% decode at 64K context, +39% at 88K" if fixed. This matches the repo's 262K MTP collapse. — [MTPLX #506](https://github.com/youssofal/MTPLX/issues/506)
- **Pack revisions:**

  | Pack | HF sha | Created | Last modified | Safetensors | Changes since August |
  |---|---|---|---|---|---|
  | Optimized-Speed | `1d5087d2062c` | 2026-08-14 | 2026-09-24 | 20.68 GB | Card and metadata only; sampler stamped 2026-09-22 (`dea0534a`), 2.11.3 card numbers 2026-09-17 |
  | Optimized-Quality | `300a4ac6c605` | 2026-08-14 | 2026-09-22 | 29.95 GB | Quantized INT8 MTP draft head 2026-08-20 (`09f71b39`) |
  | Optimized-Speed-FP16 (M1/M2) | `d4ac53cd0346` | not recorded | not recorded | not recorded | not recorded |
  | Bare-Speed | `b59d70023685` | not recorded | not recorded | not recorded | not recorded |

  The repo pinned Optimized-Speed at `123db8bc`. — [HF Optimized-Speed commits](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed/commits/main), [HF Optimized-Quality commits](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality/commits/main)
- **Pack quality and speed (M5 Max, MTPLX 2.11.3, 2026-09-16):**
  - Optimized Speed: 96.0% top-1 agreement, KL 0.012 vs bf16; download 20.4 GB; peak 23.6 GB; MTP depth 3; acceptance 0.95/0.88/0.80; coding 58.7 tok/s; xhigh long reasoning 35.1 and 37.3.
  - Optimized Quality: 99.3% top-1 agreement, KL 0.0005; download 29.4 GB; peak 32.7 GB; coding 48.3 tok/s; xhigh 33.2 and 33.1.

  — [Optimized-Speed card](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed), [Optimized-Quality card](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality)

### Inferences
- The session-cache under-provisioning the repo hit (tool_turn miss at 128K with a 48G cap) is partly addressed by 2.12.x memory pricing and trims. The rule "size the per-session cap for KV + tool footprint" still applies.
- MTPLX's long-context decode disadvantage (depth-3 verify sweeping the KV) is not fixed as of 2.12.2. Expect MTPLX to stay best at ≤8–32K and lose to oMLX/DFlash2 beyond about 64K on M4 Max. The 64K estimate comes from #506 numbers plus the repo baseline.

### Gaps
- I found no M4 Max numbers from the MTPLX vendor for the 27B on 2.12.x.

---

## 4. mlx-lm upstream and the MLX framework

### Takeaway
**mlx-lm 0.32.0** (tag 2026-09-30, PyPI 2026-10-01) supports the dense model via `qwen3_5.py`. The upstream server still has **no native MTP**: PR #990 "Native MTP speculative decoding (Qwen3.5/3.6 reference implementation)" is still open. It now has **KV-cache quantization in the server** (#1832, 2026-09-09) and a packed gated-delta kernel (#1559, 2026-08-27). **MLX 0.32.3** (2026-09-29) adds GQA decode kernel tweaks, including `sdpa_vector_2pass_1_gqa` for GQA size 12/16. Qwen3.8-27B has 24 Q heads / 4 KV heads, a GQA ratio of 6, so it is not clearly covered.

### Cited Findings
- **mlx-lm releases:** GitHub "Releases" stop at v0.31.3 (2026-04-22). Tag v0.32.0 is `a9bd8af5c021`, with commit date 2026-09-30. PyPI mlx-lm latest is 0.32.0, uploaded 2026-10-01. — [mlx-lm tags](https://github.com/ml-explore/mlx-lm/tags), [PyPI mlx-lm](https://pypi.org/project/mlx-lm/)
- **Relevant mlx-lm commits since 2026-08:**
  - `e9308d7b08` (2026-08-27): "Add packed gated delta kernel, bitwise-pinned by an explicit-tree comparator (#1559)".
  - `a1ae4f405b` (2026-09-09): "Adding kv cache quantization to server (#1832)".
  - `f2b0c475b9` (2026-09-11): fixes a server model-swap leak (#1837).
  - `d081513cd0`: the server uses one stream for generation (#1840).
  - `05b7aed425` (2026-10-08): adds `prism_hadamard_qwen35`, a Hadamard-rotated 2-bit Qwen3.5 (#1941).

  — [mlx-lm commits](https://github.com/ml-explore/mlx-lm/commits/main)
- **Open MTP and model PRs:**
  - #990 "Native MTP speculative decoding (Qwen3.5/3.6 reference implementation)" has been OPEN since 2026-03-13.
  - #1543 `--preserve-mtp` was CLOSED.
  - #1468 "Attach Qwen3.6 MTP head ... fix cache-rewind for hybrid recurrent models" was CLOSED.
  - #1788 "Add Qwen3.8-Flash-Next (qwen4_exp)" is OPEN.

  — [mlx-lm PRs](https://github.com/ml-explore/mlx-lm/pulls?q=mtp)
- **mlx-lm drops MTP and vision:** "mlx-lm drops the MTP head and the vision tower when it loads a [checkpoint]"; the ThinkingCap card recommends mlx-vlm or oMLX instead. — [bottlecapai ThinkingCap card](https://huggingface.co/bottlecapai/ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ)
- **mlx-vlm 0.7.6** (2026-10-05) supports MTP drafting (`--draft-model <dir> --draft-kind mtp --draft-block-size 3`), per pack cards. 0.7.4 fixed Qwen3.5-arch left padding for batches. — [mlx-vlm releases](https://github.com/Blaizzy/mlx-vlm/releases), [ThinkingCap card](https://huggingface.co/bottlecapai/ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ)
- **MLX 0.32.3** (2026-09-29) changes:
  - "Use sdpa_vector_2pass_1_gqa for GQA size 12 and 16" (#4380).
  - Kernel batch offset fix for gqa decode (#4431).
  - "Make head-dim-256 prefill with array mask run fused NAX kernel" (#4416). NAX is M5-only.
  - Fixed sorted gather_qmm NAX row overflow above 32K.
  - Adaptive load I/O concurrency (#4408).

  0.32.2 was released 2026-08-25. — [MLX v0.32.3](https://github.com/ml-explore/mlx/releases/tag/v0.32.3)
- **mlx-dspark** (MLX DSpark/DFlash2 server):
  - v0.20.3 was released 2026-10-05.
  - v0.20.0 (2026-09-27) added a verify attention kernel that "reads the KV cache once for all the tokens being verified". With it, Qwen3.8-27B-4bit + DFlash 2 at 32K went from 1.23× (0.19.0) to **1.85×** speedup on an **M4 Pro**; 16K was 1.79×. Red Hat's DSpark head (`--mode dspark`) reached 1.89× at 16K and 1.83× at 32K.
  - A new small-M verify kernel raises 27B-4bit + DFlash 2 from 2.30× to **2.71× (39.9 tok/s)** on short prompts (M4 Pro).

  — [mlx-dspark v0.20.0](https://github.com/ARahim3/mlx-dspark/releases/tag/v0.20.0), [v0.20.3](https://github.com/ARahim3/mlx-dspark/releases/tag/v0.20.3)

### Inferences
- Plain `mlx_lm.server` is still a non-speculative floor for the dense 27B. Its new server KV quant helps memory, not speed.
- The fused DeltaNet/GDN gains live in the runtimes (mlx-serve's one-dispatch GDN, oMLX's fused verify kernels, mlx-lm's packed gated delta kernel), not in a new MLX quant format.
- mlx-dspark 0.20's long-context verify kernel addresses exactly the weakness that made the repo's DFlash2 arm lose to MTPLX at 32K. Re-test it on the M4 Max.

### Gaps
- I found no mlx-lm release notes for 0.32.0 (the tag has no GitHub release). I could not confirm whether `sdpa_vector_2pass_1_gqa` covers GQA 6.

---

## 5. LM Studio

### Takeaway
LM Studio (app 0.4.26, 2026-10-13) can run Qwen3.8-27B MLX. Its main route to fast 27B decode on Mac is now the **Splash engine by Inco AI**, added as a runtime in **0.4.25 (2026-09-19)**. Splash is a model-specific Metal engine with a DFlash 2 drafter, requires M3 or newer and macOS 26.4+, and uses its own `incoai/Qwen3.8-27B-Splash` checkpoint. The LM Studio MLX engine itself has no clear native MTP for Qwen3.8. 0.4.22 added "DFlash, DSpark, and MTP assistant drafters" but tied the note to the llama.cpp engine ≥2.29.1. Community cards describe MLX MTP via a separate drafter model.

### Cited Findings
- **LM Studio changelog entries:**

  | Version | Date | Entry |
  |---|---|---|
  | 0.4.26 | 2026-10-13 | Bionic coexistence |
  | 0.4.25 | 2026-09-19 | "[Mac] Added support for the Splash engine on Apple Silicon M3 or newer running macOS 26.4 or newer." |
  | 0.4.24 | not recorded | "Improve DSpark and DFlash assistant drafters compatibility heuristics" |
  | 0.4.23 | 2026-09-09 | "Improve reliability of Qwen 3.8 Flash Next" |
  | 0.4.22 | 2026-08-28 | "Support for DFlash, DSpark, and MTP assistant drafters — Requires llama.cpp engine version 2.29.1 or newer" |

  Bionic 1.1.5 (2026-09-19): "[Mac only] Ultra fast Qwen3.8 inference using a new engine: Splash (by Inco AI)". — [LM Studio changelog](https://lmstudio.ai/changelog/lmstudio), [Bionic changelog](https://lmstudio.ai/changelog)
- **lmstudio-ai/mlx-engine:** the last commit is `ab52366347` (2026-10-05), "Update MLX dependencies and upstream vision compatibility". It removes "unsupported VLM gdn_sink and target_verify arguments" from the Qwen3.5 patches. There is a `mlx_engine/utils/speculative_decoding.py` module (draft-model speculation). Code search found no MTP head path. — [mlx-engine commits](https://github.com/lmstudio-ai/mlx-engine/commits/main)
- **Splash benchmark (Inco blog, 2026-09-17), all on one 48 GB M5 Pro, Qwen3.8-27B, single-request decode:**

  | Engine | Short | 8K | 16K | 32K |
  |---|---|---|---|---|
  | Splash | 74 | 55 | 55 | 54 |
  | oMLX | 38 | 33 | 29 | 28 |
  | Ollama | 24 | 21 | 21 | 19 |
  | uzu | 19 | 18 | 17 | 15 |

  | Engine | Prefill 8K | Prefill 16K | Prefill 32K |
  |---|---|---|---|
  | Splash | 398 | 395 | 363 |
  | oMLX | 122 | 119 | 110 |

  - Cached 32K TTFT: Splash 282 ms versus oMLX 2,049 ms.
  - 4 parallel short requests: Splash 170 versus oMLX 43 tok/s combined.
  - Weights are 15 GiB 4-bit with an 8-bit KV cache and a 1.2 GiB DFlash 2 draft.
  - Paged prefix KV plus GDN snapshots.
  - Engine versions are not given, and mlx-serve and MTPLX were not compared.

  — [Inco blog: Splash](https://inco.ai/blog/splash), [LM Studio blog: Splash Engine](https://lmstudio.ai/blog/splash-engine)
- An aggregator cites 144 tok/s on an M5 Max from Inco's launch post. This is unverified. — [aiwiki Splash](https://aiwiki.ai/wiki/splash_inference_engine/raw)
- **Community MLX MTP in LM Studio:** leonsarmiento's 3-bit card instructs pairing the base model with a separate MTP drafter (`leonsarmiento/Qwen3.8-27B-MTP-4bit-mlx`, about 258 MB) as the Draft model and disabling the TurboQuant KV cache. — [leonsarmiento 3-bit card](https://huggingface.co/leonsarmiento/Qwen3.8-27B-3bit-mlx)

### Inferences
- Splash is not MLX, but it is the most aggressive Apple Silicon 27B dense engine published (2× oMLX on M5 Pro).
- The M4 Max qualifies (M3 or newer). Splash's oMLX comparison numbers (28 tok/s at 32K on M5 Pro) are far below the M4 Max oMLX leaderboard rows. This suggests Splash ran oMLX without MTP, or on a different workload. Treat the 2× claim as unverified until measured on the rig.

### Gaps
- I found no M4 Max Splash numbers, max context, or Splash version/commit.
- I found no LM Studio MLX-engine tok/s for Qwen3.8-27B.

---

## 6. Hugging Face MLX quant packs for Qwen3.8-27B

### Takeaway
The notable packs fall into five families:
- **Plain affine:** mlx-community and lmstudio-community 4/5/6/8-bit, plus ddalcu MLX-Serve 4/6/8-bit with the MTP head and a bundled DFlash2 drafter.
- **oQe imatrix mixed:** Jundot oQ4e/oQ6e/oQ8e-mtp, **re-quantized 2026-10-11**.
- **MTPLX dynamic:** Youssofal.
- **Calibrated:** AWQ (True2456), OptiQ (mlx-community), DWQ (bottlecapai ThinkingCap, WaveCut, AtomicChat).
- **Swift 1.5 fine-tune** (ukisai, a reasoning-efficient Qwen3.8-27B derivative) in many MLX quants.

Published quality metrics exist only for a few packs:
- Jundot oQ4e: KL 0.0117 code / 0.0600 prose after the refit.
- MTPLX: KL 0.012 / 0.0005.
- ddalcu: weight-noise 9.25% (4-bit) / 0.71% (8-bit).
- OptiQ: Capability Score 87.98.
- ThinkingCap DWQ: benchmark accuracies.

Sizes below are current safetensors bytes from the HF tree API. "sha" is the current HF revision.

### Cited Findings
- **Pack table (sizes and revisions from HF tree/commit API, 2026-10-13):**

| Pack | Format / bpw | MTP head | Safetensors size | sha (current) | Created / last change | Quality metric |
|---|---|---|---|---|---|---|
| [mlx-community/Qwen3.8-27B-4bit](https://huggingface.co/mlx-community/Qwen3.8-27B-4bit) | affine 4-bit | no (separate `-MTP-4bit` repo, 0.3 GB) | 16.05 GB | `10c35caafbb8` | 2026-08-14 / 2026-09-14 (image processor fix) | — |
| [mlx-community/Qwen3.8-27B-8bit](https://huggingface.co/mlx-community/Qwen3.8-27B-8bit) | affine 8-bit g64 | no (separate `-MTP-8bit`, 0.5 GB) | 29.5 GB | `815b83c0df8f` | 2026-08-14 | — |
| [mlx-community/Qwen3.8-27B-bf16](https://huggingface.co/mlx-community/Qwen3.8-27B-bf16) | bf16 | no | ~53 GB (usedStorage 106 GB incl. history) | `6f265714824f` | 2026-08-14 | — |
| lmstudio-community/Qwen3.8-27B-MLX-4/5/6/8bit | affine | not stated | 16.1 / — / 22.8 / 29.5 GB | 4bit `6067b15cf581`, 6bit `05f38c1f39e2`, 8bit `241ebb5f1d60` | 2026-08-14 | — |
| [ddalcu/Qwen3.8-27B-MLX-Serve-4bit](https://huggingface.co/ddalcu/Qwen3.8-27B-MLX-Serve-4bit) | affine 4-bit g64; embed, vision, `mtp.fc`, norms bf16 | **yes**, plus bundled DFlash2 `drafter/` | 22.05 GB (incl. drafter) | `901aa73a1ff5` | 2026-08-14 / 2026-09-29 (drafter added) | weight noise 9.25% |
| ddalcu/…-MLX-Serve-6bit | affine 6-bit | yes, plus drafter | 27.03 GB | `0aa59466e2de` | 2026-08-15 / 2026-09-29 | — |
| [ddalcu/…-MLX-Serve-8bit](https://huggingface.co/ddalcu/Qwen3.8-27B-MLX-Serve-8bit) | affine 8-bit | yes, plus drafter | 35.04 GB | `7775059e955f` | 2026-08-14 / 2026-09-29 | weight noise 0.71% |
| [Jundot/Qwen3.8-27B-oQ4e-mtp](https://huggingface.co/Jundot/Qwen3.8-27B-oQ4e-mtp) | oQ4e: 80.8% 4-bit g64, 17.4% 5-bit, 1.9% bf16 = **4.887 bpw** | yes (0.314 GB) | 16.97 GB | `49c1d60367d9` | 2026-08-17 / **2026-10-11 re-quant** (`d4566751`), KL added 2026-10-12 | KL code 0.0143→**0.0117**, prose 0.0696→**0.0600** |
| [Jundot/Qwen3.8-27B-oQ6e-mtp](https://huggingface.co/Jundot/Qwen3.8-27B-oQ6e-mtp) | 90.5% 6-bit, 7.6% 8-bit = **6.829 bpw** | yes (0.407 GB) | 23.72 GB | `dc2eaae3f1ed` | 2026-08-18 / 2026-10-11 re-quant | — |
| [Jundot/Qwen3.8-27B-oQ8e-mtp](https://huggingface.co/Jundot/Qwen3.8-27B-oQ8e-mtp) | 98.1% 8-bit g64 = **8.639 bpw** | yes (0.5 GB) | 30.0 GB | `6c76ddfb82af` | 2026-08-18 / 2026-10-11 re-quant (repo had `c99e5aad`) | — |
| Jundot/Qwen3.8-27B-oQ8e-fp16-mtp, oQ4e-fp16-mtp | fp16 variants (for GPUs without bf16) | yes | not recorded | `426fa703132b`, `9f7607169d66` | re-quant 2026-10-12 | — |
| [gcoli/Qwen3.8-27B-oQ4e-mtp](https://huggingface.co/gcoli/Qwen3.8-27B-oQ4e-mtp) | oQ4e (old recipe) | yes | about 17 GB | `c41ed507f1b1` (unchanged) | 2026-08-14 | — |
| [evsinlb/Qwen3.8-27B-oQ8e-fp16-mtp](https://huggingface.co/evsinlb/Qwen3.8-27B-oQ8e-fp16-mtp) | oQ8e fp16 | yes | not recorded | `48fb30d3c21c` | 2026-08-14 / 2026-08-30 | — |
| [Youssofal/…-MTPLX-Optimized-Speed](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed) | 4-bit g32 dynamic; 8-bit embed/head/GDN out/last 8 MLP; 16-bit GDN conv/state, norms, MTP | yes | 20.68 GB | `1d5087d2062c` | 2026-08-14 / 2026-09-24 | KL 0.012, top-1 96.0% |
| [Youssofal/…-MTPLX-Optimized-Quality](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality) | 8-bit g64; INT8 MTP head | yes | 29.95 GB | `300a4ac6c605` | 2026-08-14 / 2026-09-22 | KL 0.0005, top-1 99.3% |
| [True2456/Qwen3.8-27B-AWQ-5.0bpw](https://huggingface.co/True2456/Qwen3.8-27B-AWQ-5.0bpw) | AWQ mixed 5.0 bpw | yes (repaired) | 17.6 GB usedStorage | `dc699a76ddcb` (unchanged) | 2026-08-16 / 08-17 | — |
| True2456/Qwen3.8-27B-AWQ-4.85bpw | AWQ 4.85 bpw | not recorded | 17.1 GB | `9daec1e8dddc` | 2026-08-15 | — |
| [mlx-community/Qwen3.8-27B-OptiQ-4bit](https://huggingface.co/mlx-community/Qwen3.8-27B-OptiQ-4bit) | KL-sensitivity mixed 4/8 (261 8-bit, 237 4-bit layers), g64, target ~5.0 bpw; per-layer `kv_config.json` | MTP sidecar | 20.66 GB | `a97e1450285c` | 2026-08-15 / 2026-09-16 | Capability 87.98 (MMLU 84.1, GSM8K 96.1, IFEval 77.1, BFCL 93.5, HumanEval 92.1, HashHop 85.0) |
| [bottlecapai/ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ](https://huggingface.co/bottlecapai/ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ) | DWQ mixed 4/8-bit g64 (ThinkingCap fine-tune) | yes (`mtp-drafter/` + embedded) | 22.78 GB | `93944fefc63a` | 2026-09-24 / 09-25 | per-benchmark accuracy vs bf16, e.g. 0.862 vs 0.880; AA-LCR 0.830 vs 0.810 |
| WaveCut/Qwen3.8-27B-MLX-4bit-DWQ | DWQ 4-bit | not recorded | 16.1 GB | `f74a43512e93` | 2026-08-15 | — |
| AtomicChat/Qwen3.8-27B-MLX-AD-3.70bpw-DWQ-13.4GB | DWQ 3.70 bpw | not recorded | 13.4 GB | `16aea93cf9a1` | 2026-08-25 | — |
| [ukisai/Swift-1.5-4bit-MLX](https://huggingface.co/ukisai/Swift-1.5-4bit-MLX) | Swift 1.5 fine-tune, affine 4-bit g64 (mlx-lm converter) | source has 15 MTP tensors; needs supplied mlx-lm patch | 15.83 GB | `82276731e47e` | 2026-09-21 / 09-25 | vendor: "58.5% fewer thinking tokens... 0.35% higher" |
| ukisai/Swift-1.5-5bit-MLX | Swift 1.5, 5-bit | not recorded | 19.28 GB | `79bf5dd3f3fd` | 2026-09-22 / 09-25 | — |
| [scottlowry/Swift-1.5-Qwen3.8-27b-oQ4e-mtp](https://huggingface.co/scottlowry/Swift-1.5-Qwen3.8-27b-oQ4e-mtp) | Swift 1.5, oQ4e (oMLX 0.7.1.dev1, re-uploaded 2026-10-12) | yes | 16.97 GB | `881dc1914f65` | 2026-10-07 / 10-12 | — |
| dicksondickson/Swift-1.5-Qwen3.8-27b-oQ5e/oQ6e/oQ8e-{bf16,fp16}-mtp(-MLX) | Swift 1.5, oQe | yes | oQ6e-bf16 23.7 GB; oQ8e-bf16 30.0 GB | oQ6e `a71e37ae4818`, oQ8e `d8a5b0199a59` | 2026-09-28/29 | — |
| GazTrab/Swift-1.5-Qwen3.8-27b-RCO-DWQ-MLX | Swift 1.5, RCO-DWQ | not recorded | 13.5 GB | `a01865942890` | 2026-10-02 | — |
| leonsarmiento/Qwen3.8-27B-pi-4bit-mtp-mlx | 4-bit with MTP | yes | 15.9 GB | `411886b8319e` | 2026-10-01 | — |
| uqer1244/Qwen3.8-27B-GSQ-RCO-MLX | GSQ-RCO low-bit | not recorded | 10.4 GB | `6c6cd8a70588` | 2026-09-21 / 09-28 | — |

- **Drafters:**
  - [RadixArk/Qwen3.8-27B-DSpark](https://huggingface.co/RadixArk/Qwen3.8-27B-DSpark): `b9a5dbdf03bc`, last change 2026-08-29.
  - [incoai/Qwen3.8-27B-DFlash2](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2): `015e795645c7`, last change 2026-09-17.
  - ddalcu mirrors DFlash2 (credited "z-lab Qwen3.8-27B-DFlash2", "mirror of incoai/Qwen3.8-27B-DFlash2") inside its packs.
  - Vendor H200 acceptance lengths at concurrency 1: DFlash 2 4.10–5.46 versus native MTP 3.74–5.02 versus DSpark 3.01–4.36 (7 drafts/step). These are CUDA numbers.

  — [ddalcu drafter README](https://huggingface.co/ddalcu/Qwen3.8-27B-MLX-Serve-4bit/blob/main/drafter/README.md)
- **ddalcu 4-bit card speed, M4 Max 128 GB, macOS 26.5, temperature 0, median of 3:**

  | Workload | MTP on | MTP off | Speedup |
  |---|---|---|---|
  | Write a class from scratch | 75.3 tok/s | 26.3 tok/s | 2.86× |
  | Explanatory prose | 39.7 tok/s | 26.7 tok/s | 1.49× |

  The 8-bit pack reaches 53.6 tok/s with MTP on. The README dates from 2026-08-14 (`b543ed7c`), so these are **prior-state (pre-26.10) mlx-serve numbers**. — [ddalcu 4-bit card](https://huggingface.co/ddalcu/Qwen3.8-27B-MLX-Serve-4bit)
- **Conversion gotchas for raw-checkpoint MLX conversion** (ddalcu card): delta-encoded norms (+1), a depthwise conv1d transpose, and a Conv3d patch embed that must be channels-last. — [ddalcu 4-bit card](https://huggingface.co/ddalcu/Qwen3.8-27B-MLX-Serve-4bit)
- **Swift 1.5 MLX** requires the "supplied architecture patch" for mlx-lm. "A bare `mlx_lm.server` command may select a separate Homebrew installation that lacks the Swift architecture and cache patches." It was validated on a 48 GiB M4 Pro with an 86K-token conversation. — [ukisai Swift-1.5-4bit-MLX](https://huggingface.co/ukisai/Swift-1.5-4bit-MLX)

### Inferences
- **Jundot's 2026-10-11 re-quant is the main pack-level change since September.** Any oQe arm should repin to `49c1d603` (oQ4e) / `dc2eaae3` (oQ6e) / `6c76ddfb` (oQ8e).
- **I did not find a Swift 1.5 MLX pack of the dense 27B at a calibrated ~4.7 bpw comparable to Dankpaws' Flash-Next pack.** The closest are the oQ4e/oQ5e/oQ6e Swift-1.5 conversions (scottlowry, dicksondickson), which oMLX can serve with MTP. Dankpaws' pack (`Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw`, `13839b7191e0`, 2026-10-06) is Flash-Next only.

### Gaps
- No KL or perplexity is published for mlx-community / lmstudio-community plain packs, oQ6e/oQ8e after the refit, AWQ, or the Swift MLX quants.
- `usedStorage` from the HF API includes history, so the current size is taken from tree sums.

---

## 7. Long context on the dense 27B (KV size, max practical context on 128 GB, KV quant/SSD offload)

### Takeaway
KV grows only for the full-attention layers: about **64 KiB/token in bf16, or about 16 GiB at the native 262,144 tokens**. On top of that is a fixed GDN recurrent state. A 128 GB M4 Max can therefore hold the full 262K context even with an 8-bit pack. The practical limit is prefill time (about 13 min cold at 128K on M4 Max per oMLX rows) and long-context decode, not memory. KV quantization is available in mlx-serve (`--kv-quant 4/8`), mlx-lm server (#1832), oMLX (TurboQuant KV) and MTPLX (8/4-bit KV, NaN fixed in 2.12.1). SSD prefix tiers exist in mlx-serve (`--prefix-cache-disk`, plus an SSD-only mode in 26.10.2), oMLX (SSD cache) and MTPLX (SSD session cache).

### Cited Findings
- **Qwen/Qwen3.8-27B config:** `model_type` qwen3_5, 64 layers, `full_attention_interval` 4, 24 attention heads, **4 KV heads**, head_dim 256, linear (GDN) 16 key heads / 48 value heads with 128-dim keys and values, conv kernel 4, `max_position_embeddings` 262144, 1 MTP layer, hidden 5120. — [Qwen3.8-27B config.json](https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/config.json)
- **MTPLX memory measurements:** "a 250K-token 27B snapshot is 15.3 GiB"; the draft-head history is 4,096 bytes/token on the 27B; the Optimized Quality session cache at the full 262,144 window is 42.5 GiB. — [MTPLX v2.12.1](https://github.com/youssofal/MTPLX/releases/tag/v2.12.1)
- **Peak memory on M4 Max 128 GB (oMLX 0.7.0, MTP on):** oQ4e-mtp 32.3 GB at 128K; oQ8e-mtp 47.7 GB at 128K. — [omlx.ai fxmby881](https://omlx.ai/benchmarks/performance/fxmby881), [omlx.ai 2w1u2zl7](https://omlx.ai/benchmarks/performance/2w1u2zl7)
- **KV quant options:**

  | Runtime | Option |
  |---|---|
  | mlx-serve | `--kv-quant {off,4,8}`, fused read path from 8K |
  | mlx-lm server | KV quantization (2026-09-09) |
  | oMLX | `turboquant_kv_enabled`, bits 4 (issues #3767 and #4249 interact with Lightning MTP) |
  | MTPLX | 8/4-bit KV (NaN fix #526 in 2.12.1) |
  | Splash | 8-bit KV |
  | OptiQ | per-layer `kv_config.json` |

  — [mlx-serve cli.md](https://github.com/ddalcu/mlx-serve/blob/main/docs/cli.md), [mlx-lm #1832](https://github.com/ml-explore/mlx-lm/pull/1832), [omlx #3767](https://github.com/jundot/omlx/issues/3767), [MTPLX v2.12.1](https://github.com/youssofal/MTPLX/releases/tag/v2.12.1), [Inco Splash](https://inco.ai/blog/splash), [OptiQ card](https://huggingface.co/mlx-community/Qwen3.8-27B-OptiQ-4bit)

### Inferences
- **Computed KV size:** 16 attention layers × 2 (K, V) × 4 heads × 256 dim × 2 bytes = 65,536 B/token. 262,144 tokens therefore need 16 GiB, consistent with MTPLX's 15.3 GiB at 250K.
- **Computed GDN state:** 48 layers × 48 heads × 128 × 128 is about 75 MB in bf16 (about 150 MB in f32), a constant cost.
- **Max context on 128 GB:** the native 262K fits easily with any pack up to 8-bit. With prefix caches the budget is weights + about 16 GiB of live KV + the cache budget (16 GiB holds about one full 262K session).
- **The bottleneck is speed:**
  - Cold prefill: about 160–250 tok/s on M4 Max.
  - Decode at 128K: about 34–40 tok/s with MTP on oMLX 0.7.0.
  - KV quant would mainly help bandwidth-bound long-context decode. No M4 Max measurement of that effect was found.

### Gaps
- I found no published M4 Max numbers for decode with KV quant on versus off for the 27B on any runtime.
- I found no M4 Max 262K figures for the October versions of oMLX, mlx-serve or MTPLX. The repo's 262K numbers are on August builds.
