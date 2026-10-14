# Community experience: dense Qwen3.8-27B on Apple Silicon (Reddit, GitHub, blogs), as of 2026-10-13

Method: I read the Reddit MCP listings (r/LocalLLaMA top/month and new, r/LocalLLM top/month, r/MacStudio top/year) and filtered them for Qwen3.8 / 27B / Mac. I read the full comment threads of 10 relevant posts. I also ran WebSearch/WebFetch on GitHub (oMLX discussions, Splash issues, QwenLM issues, recipe repos) and blogs. Most Reddit 27B threads come from people on NVIDIA/AMD GPUs. Mac-specific numbers are concentrated in the Splash threads, oMLX GitHub discussions/recipes and the oMLX benchmark site. Every number below carries the hardware, runtime, quant and context it was reported with, where the source gave them.

## 1. Preferred quant and runtime on Macs, with tok/s and RAM

### Takeaway
On M3+ Macs, community attention in Sep–Oct 2026 moved to two stacks. The first is **Inco Splash**, a model-specific Metal engine with DFlash speculative decoding that uses its own 4-bit package. The second is **oMLX with the oQ4e-mtp checkpoint and native MTP k=3**, sometimes with ANE prefill. Plain MLX 4/8-bit without MTP is the slow baseline: roughly 25–40 tok/s on M4 Max and 65–75 tok/s on M3 Ultra with oQ4e+MTP. 4-bit (oQ4e / UD-Q4_K_XL) is the common default. Q8/oQ8e costs about 15 GB more and decodes noticeably slower, and quality evals barely separate the two.

### Cited Findings
**M4 Max 128 GB (Mac Studio)**
- oMLX 0.6.3rc2 + ANE prefill + native MTP k=3, model `Jundot/Qwen3.8-27B-oQ4e-mtp`: 53.3 tok/s prose, 72.1 tok/s code, 273.7 tok/s prefill at 4K. Same setup with ANE off: 47.9 / 47.9. Raw decode with MTP off: about 24.6 tok/s. Conditions: thinking off, temp 0, ~2.1–2.4K prompts, 320 output tokens, measured 2026-08-21. Resident memory ~17 GB. Context set to 262144. — [Weschera/Qwen3.8-27B-oMLX-MTP-Mac](https://github.com/Weschera/Qwen3.8-27B-oMLX-MTP-Mac)
- The same repo found vllm-metal 0.3.0 (8-bit, no MTP) gives only 13.2 tok/s on code, about 3.6x slower than oMLX. MTP k=4 helps code by +1.2 tok/s but hurts prose by −5.4, so k=3 is the author's pick. — [Weschera repo](https://github.com/Weschera/Qwen3.8-27B-oMLX-MTP-Mac)
- oMLX benchmark site, M4 Max (40c) entries:
  - 8-bit MLX on 128 GB: 34.0 tok/s at 1K, 28.3 tok/s at 4K.
  - mxfp4 on 128 GB: 39.3 tok/s at 4K (oMLX v0.6.0.dev1).
  - 4-bit on 64 GB: 65.1 tok/s gen and 216.9 tok/s PP at 4K, 18.7 GB peak, dropping to 27.3 tok/s at 8K (v0.6.3rc3, 2026-08-25).
  - oQ8e-mtp on 64 GB: 25.0 tok/s at 4K.
  - 6-bit on 48 GB: 20.2 tok/s at 1K.
  - These figures come from the search summary of the per-run pages. I did not re-open each page. — [4bit](https://omlx.ai/benchmarks/performance/u19dattd), [8bit](https://omlx.ai/benchmarks/performance/xdk5d3uj), [oQ8e-mtp](https://omlx.ai/benchmarks/performance/b2swmyox), [mxfp4](https://omlx.ai/benchmarks/performance/qxx9ctqo), [6bit](https://omlx.ai/benchmarks/performance/p3kbtfg6)

**M3 Ultra 512 GB (4-machine fleet, daily driver), oMLX 0.6.1/0.6.2, mlx 0.32.0, macOS 26.6.2 (GitHub discussion, 2026-08-18/20)**
- oQ4e + MTP3: 65–75 tok/s gen at 8K (1K 62–72; 4K 61–63; 8K 67–79) and 260–275 tok/s at batch 8.
- oQ8e: 43 tok/s, with about 15 GB more resident memory.
- Prefill: ~420–442 tok/s at 1K–8K. With ANE fraction 0.53 it reaches 494–501 tok/s at 8–16K.
- TTFT: ~2.5 s at 1K and ~19 s at 8K.
- Footprint ~20 GB at 8K.
- Source for all of the above: [jundot/omlx Discussion #2811](https://github.com/jundot/omlx/discussions/2811)
- In the same thread, quality was nearly identical across quants (greedy, thinking off): oQ4e averages 89.8 and oQ8e 89.9 on MMLU/GSM8K/ARC-C on the Ultra. The author calls n=128 differences across oQ4e–oQ8e "too small to rank" and recommends oQ4e. — [Discussion #2811](https://github.com/jundot/omlx/discussions/2811)

**M3 Max 128 GB (40c), Splash vs others (GitHub issue, 2026-09-20 to 10-12)**
- Splash 1.0.1: 30.0 tok/s short-prompt decode. On the same machine, Ollama's MLX engine (NVFP4) did 42.5 and Ollama llama.cpp Q4_K_M did 12.0.
- After Splash 1.0.2: 57.7 tok/s (+92%) and 4-stream 64 tok/s.
- Splash 1.3.0: 58.2 tok/s decode, 22K prefill 328→473 tok/s thanks to the GPU/ANE FFN split, warm TTFT ~330 ms.
- Source: [incoai/splash #37](https://github.com/incoai/splash/issues/37)

**M5 Max 128 GB, same thread**
- Splash 1.0.2: 83 tok/s at a 71-token prompt, 74 at 22.4K, 68 at 51.5K. Prefill at 22.4K is 806–823 tok/s.
- MLX server, 8-bit + native MTP: 41 / 38 / 30 tok/s.
- Splash cached-replay TTFT at 22.4K is 0.17 s versus 5.1 s for MLX.
- On battery or a weak charger, decode collapses (84→16 tok/s on a 15 W source).
- Source: [incoai/splash #37](https://github.com/incoai/splash/issues/37)

**Splash official/LM Studio**
- 74 tok/s short prompt and 54 tok/s at 32K on a 48 GB M5 Pro. 170 tok/s aggregate with 4 concurrent requests.
- Requires an M3 or newer, macOS 26.4+, at least 36 GB (48 GB+ recommended). Shipped as an "Experimental backend" in LM Studio Bionic 1.1.5+, and only for Qwen3.8-27B and Qwen3.6-35B-A3B (2026-09-18).
- Source: [LM Studio blog](https://lmstudio.ai/blog/splash-engine)

**M1/M2 (older but informative)**
- Splash-M1 port on an M1 Max 32c 64 GB: 39.1 tok/s average on npanj's 5-prompt benchmark, versus 18.9 with stock Splash kernels.
  - Prefill: 142 tok/s at 2K and 110 at 32K.
  - Real OpenCode session: 36.5 tok/s at 16–32K ctx, 19.5 at 32–64K, 23.4 at 64–96K.
  - Peak memory ~26–28 GB at ~135K ctx.
  - Posted 2026-09-24. — [r/LocalLLM 1woq7cd](https://www.reddit.com/r/LocalLLM/comments/1woq7cd/you_can_now_run_qwen3827b_on_a_2021_m1_max_at_39/)
- Comment on that thread from an M2 Max user: "From 10 t/s (qwen3.8 27b 8-bit in oMLX) to 30-45 t/s now." — [same thread](https://www.reddit.com/r/LocalLLM/comments/1woq7cd/you_can_now_run_qwen3827b_on_a_2021_m1_max_at_39/)
- Comment from an M1 Max 32 GB user (tragdor85): Splash is "faster than OMLX and MTPLX. And more consistent. MTPLX is fast but it is in bursts. OMLX is stable but slower." — [same thread](https://www.reddit.com/r/LocalLLM/comments/1woq7cd/you_can_now_run_qwen3827b_on_a_2021_m1_max_at_39/)
- Independent M1 Max 24c 64 GB test (2026-09-25), 4-bit MLX on oMLX 0.6.4 vs Splash-M1:
  - Average: 16.0 vs 32.8 tok/s.
  - Short code with reasoning off: 16.0 vs 61.3.
  - Prose: 16.1 vs 18.3.
  - 32K prompt: 13.0 vs 17.1.
  - 4 parallel requests: 15.9 vs 62.3.
  - Quality on 217-item suite + 50 GSM8K: same as the 4-bit quant.
  - Source: [r/LocalLLM 1wpza1i](https://www.reddit.com/r/LocalLLM/comments/1wpza1i/a_breakthrough_for_m1_and_m2_macs/)

**MTPLX (M5 Max 128 GB, project README)**
- "Bare Speed" flat 4-bit: 65.2 tok/s, 17.0 GB peak.
- "Optimized Speed" 4-bit dynamic: 87.6 tok/s on a rewrite task, 23.6 GB peak, top-1 agreement with bf16 96.0%.
- 8-bit "Optimized Quality": 32.7 GB peak, top-1 agreement 99.3%.
- Exposes an Anthropic-compatible `/v1/messages` endpoint for Claude Code/OpenCode.
- Source: [youssofal/MTPLX](https://github.com/youssofal/MTPLX)

**Blog-level memory guidance**
- Weights: 4-bit ~16–19 GB, 6-bit ~21–22 GB, 8-bit ~27–30 GB, BF16 55.6 GB.
- KV at ~64 KB/token: ~2 GB at 32K, ~8 GB at 128K, ~16.4 GB at 262K.
- Reported Mac mini M4 32 GB 4-bit speed: only ~5–6 tok/s.
- Source: [OrcaRouter blog, 2026-08-15](https://www.orcarouter.ai/blog/qwen-3-8-27b-mlx)

### Inferences
- On a 128 GB M4 Max, memory is not a constraint for the 27B (~17–33 GB plus at most ~16 GB KV at 262K). The choice comes down to decode speed. The best documented M4 Max number is ~48–53 tok/s prose / ~65–72 tok/s code on oMLX oQ4e-mtp with MTP k=3. Splash on an M4 Max has no public number yet. By bandwidth (546 GB/s, versus 400 GB/s on the M3 Max, which reaches ~58 tok/s on Splash 1.3) it would likely land in the 60–80 tok/s range, but that is unmeasured.
- Q8 is chosen mainly for long-agent stability, not for eval scores (see section 5). On Macs it costs roughly 35–40% of decode speed (M3 Ultra: 65–75 vs 43 tok/s).

### Gaps
- No Reddit thread with Splash or MTPLX numbers specifically on an M4 Max 128 GB or an M3 Ultra.
- No GGUF/llama.cpp Metal numbers on an M4 Max for UD-Q4/Q6/Q8 were found. The only llama.cpp Mac data point is Ollama Q4_K_M at 12 tok/s on an M3 Max ([splash #37](https://github.com/incoai/splash/issues/37)).
- A widely repeated claim (the search snippet attributed it to a stacker.news item): Qwen3.8 27B Q4_K_M runs at ~14 tok/s versus Qwen3.6-27B at ~28.6 tok/s on an M3 Ultra via Ollama. The page returned empty, so this is unverified.

## 2. Does MTP / speculative decoding help the dense 27B on Macs?

### Takeaway
Yes, and it is the largest single lever. Native MTP (k=3) roughly doubles decode on M4 Max and M3 Ultra for code and structured output. DFlash in Splash gives about 2–2.6x. Acceptance depends heavily on content: ~94–99.6% on code and much lower on free prose (19–80% depending on the engine and draft). Prose gains are therefore small.

### Cited Findings
- M4 Max 128 GB, oMLX native MTP k=3:
  - Code acceptance 99.6% (3.76 tokens/cycle). Prose 75–80% (2.5–2.8 tokens/cycle).
  - Raw decode is ~24.6 tok/s. With MTP it reaches 47.9–53.3 tok/s on prose and 65.5–72.1 on code.
  - Source: [Weschera repo](https://github.com/Weschera/Qwen3.8-27B-oMLX-MTP-Mac)
- M3 Ultra, oMLX MTP draft-token sweep: gen at 8K was 50.0 / 60.7 / 75.0 / 65.6 tok/s for k=1/2/3/4, with k=3 best. MTP acceptance on an M4 Pro mini with TurboQuant was 86–92%. — [omlx #2811](https://github.com/jundot/omlx/discussions/2811)
- M3 Max 128 GB, DFlash/MTP gain measured as predictable vs technical text: Splash 82.7 vs 32.1 tok/s (2.58x); Ollama MLX 55.0 vs 18.4 (2.99x, attributed to MTP heads). — [splash #37](https://github.com/incoai/splash/issues/37)
- M1 Max: Splash draft acceptance was "about 94% of the time on code but only about 19% on free prose," so prose runs near plain decode speed. — [r/LocalLLM 1wpza1i](https://www.reddit.com/r/LocalLLM/comments/1wpza1i/a_breakthrough_for_m1_and_m2_macs/)
- MTPLX claims ~2x over plain decode: 1.6x measured on a 16 GB M4 Mac mini and 2.24x on an M5 Max. — [MTPLX](https://github.com/youssofal/MTPLX) (via search summary)
- For comparison, a non-Mac case: 30-day daily use on a 5070 Ti + 4070 Super with llama.cpp and UD-Q4_K_XL showed MTP acceptance of only 0.48. DFlash2 + ngram was 20% faster than MTP + ngram there. — [r/LocalLLM 1whqwdq](https://www.reddit.com/r/LocalLLM/comments/1whqwdq/i_ran_qwen_38_27b_locally_for_30_days_here_are/)

### Inferences
- For agentic coding, where output is mostly code or tool JSON, MTP k=3 on oMLX or DFlash on Splash should give close to 2x. For chat or prose, expect +10–50%.
- Splash's advantage over oMLX+MTP on the M3 Max (58 vs 42.5 tok/s short prompt) and its very fast cached-replay TTFT matter for agent loops, which re-send long prefixes.

### Gaps
- No Mac report measured MTP acceptance with thinking on during long agent sessions. All the controlled Mac benchmarks above ran with thinking off or used short prompts.

## 3. Thinking mode: spirals, caps, effort levels

### Takeaway
Overthinking is the most common complaint ("but wait", "Hmm"). Practitioners mitigate it by running reasoning_effort=medium instead of the xhigh default, setting thinking budgets of 1K–5K tokens, or using the Swift reasoning-efficiency fine-tune. There is a documented bug at xhigh: empty answers, where reasoning never closes, at 19–38% in one reporter's runs. Turning thinking off fully hurts hard tasks. Several users report tasks that only succeeded with reasoning on.

### Cited Findings
- QwenLM issue #216 (opened 2026-08-19, closed as not planned 2026-10-12):
  - At xhigh, the default when effort is omitted, the API returns empty content with `finish_reason: stop`.
  - Failure rate: 18/93 (19.4%), later ~38% over ~1,000 calls. low/medium: 0/95, later ~8%.
  - Local llama.cpp at temp 0 failed 12/12.
  - Workarounds: repetition_penalty 1.05–1.10, frequency_penalty 0.3, thinking off, or a server-side thinking budget (4,096).
  - LM Studio silently dropped `reasoning_effort`.
  - Source: [QwenLM/Qwen3.8 #216](https://github.com/QwenLM/Qwen3.8/issues/216)
- 30-day user (2026-09-16), on 5070 Ti + 4070 Super (not Mac):
  - "Without it, the model is crippled. Multiple tasks could not be solved without reasoning."
  - Up to 50% of context goes to reasoning, with single bursts of 60K reasoning tokens.
  - Effort levels "are more of a suggestion."
  - Basic tasks run up to 50% slower than on 3.6.
  - Source: [r/LocalLLM 1whqwdq](https://www.reddit.com/r/LocalLLM/comments/1whqwdq/i_ran_qwen_38_27b_locally_for_30_days_here_are/)
- Reasoning caps in practice:
  - LM Studio "Reasoning Budget" 1024 + temp 0.1 with Cline "eliminated the annoying over thinking." Another user pushed back that this cripples the model. — [r/LocalLLaMA 1wp0z3i](https://www.reddit.com/r/LocalLLaMA/comments/1wp0z3i/qwen3827b_is_good_enough_that_i_stopped_using_api/)
  - "Use MEDIUM reasoning. Xhigh is only for really really hard tasks." — [same thread](https://www.reddit.com/r/LocalLLaMA/comments/1wp0z3i/qwen3827b_is_good_enough_that_i_stopped_using_api/)
  - One user said capping reasoning tokens removed the "but wait" loops and closed most of a 10 h vs 30 min gap with Claude. — [same thread](https://www.reddit.com/r/LocalLLaMA/comments/1wp0z3i/qwen3827b_is_good_enough_that_i_stopped_using_api/)
- M3 Ultra, oMLX: thinking/xhigh GSM8K (n=64) scored 62/64 in 521–556 s, versus instruct (thinking off) at 59/64 in 301 s. The M4 Pro mini uses thinking/medium as its agent default. — [omlx #2811](https://github.com/jundot/omlx/discussions/2811)
- oMLX trap: setting only `reasoning_effort` can leave thinking off, so set both `enable_thinking` and the effort. — [omlx #2811](https://github.com/jundot/omlx/discussions/2811)
- M1 Max, Splash: with xhigh and an 8K token cap, a few answers get cut off. The stock 4-bit quant shows the same behavior. — [r/LocalLLM 1wpza1i](https://www.reddit.com/r/LocalLLM/comments/1wpza1i/a_breakthrough_for_m1_and_m2_macs/)
- Codersera (updated 2026-10-05) reports:
  - Simon Willison's SVG test took 21 min and 22,276 reasoning tokens. An M4 Pro owl SVG took 17 min.
  - Recommendation: effort medium or low, ~5K reasoning cap, `preserve_thinking` on.
  - LM Studio's default 8,192 context gets consumed by thinking, so raise it to 262,144.
  - On the AA Index, Qwen3.8 used ~200M output tokens versus 160M for Qwen3.6.
  - Source: [Codersera](https://codersera.com/blog/qwen-3-8-27b-local-claude-code-replacement-2026/)
- The "Sharp" chat templates claim ~59% fewer tokens with stock Qwen. — [r/LocalLLM 1wgwgrf comment](https://www.reddit.com/r/LocalLLM/comments/1wgwgrf/what_do_you_guys_think_of_qwen_38_27b_so_far_can/) ([templates](https://huggingface.co/peculiar-ragdoll/Qwen-Sharp-Chat-Templates))

### Inferences
- For a Mac daily driver, the community-consensus default is thinking on with effort=medium plus a budget cap, never the template's implicit xhigh. Run thinking off for subagents and trivial tool steps.
- Combining slow Mac prefill with heavy reasoning tokens is what makes 27B agent turns feel slow. This is a stronger effect on Macs than on GPUs.

### Gaps
- No Mac-specific measurement of time-to-final-answer across low/medium/xhigh in agent sessions was found.

## 4. Long context on Macs

### Takeaway
The model supports 262K natively, and Macs fit the KV easily: ~16 GB at 262K on the Ultra, since only 16 full-attention layers hold KV. The practical collapse comes from prefill time and decode slowdown, not memory. Cold prefill at 128K takes minutes even on an M3 Ultra, and decode roughly halves between short context and 64–100K. Prefix caching is therefore essential for agents.

### Cited Findings
- M3 Ultra, oMLX oQ4e:
  - Prefill 397 tok/s at 32K (97 s), 345 at 64K (204 s), 274 at 128K (494 s), 193 at 262K (1,372 s).
  - KV ~16 GB at 262K.
  - The 123K-token needle test passed.
  - Source: [omlx #2811](https://github.com/jundot/omlx/discussions/2811)
- M4 Pro 64 GB mini: fp16 KV at 128K is ~32 GB and does not fit. TurboQuant 4-bit KV brings it to ~8 GB. Cold 115K prefill takes ~20 min, and a warm SSD prefix re-prefill ~43 s. — [omlx #2811](https://github.com/jundot/omlx/discussions/2811)
- M1 Ultra 64 GB, Splash-M1 in a DeepSeek harness with a 171K window:
  - Decode was 49 tok/s at 12.7K input, ~25 at 45K, ~21 at 63K, and ~17 at 105K.
  - Memory grew from 33 GB to 57–59 GB at 100K+.
  - The same user's earlier oMLX oQ4e-mtp run "starts with 26 t/s ... and keeps draining."
  - Source: [r/LocalLLM 1woq7cd comment](https://www.reddit.com/r/LocalLLM/comments/1woq7cd/you_can_now_run_qwen3827b_on_a_2021_m1_max_at_39/)
- M1 Max Splash-M1 in an OpenCode session: 95% of prompt tokens hit the prefix cache, yet "about half of the wall time was still spent waiting for the first token after each tool call ... long-context attention is now the bottleneck for agents." — [r/LocalLLM 1woq7cd](https://www.reddit.com/r/LocalLLM/comments/1woq7cd/you_can_now_run_qwen3827b_on_a_2021_m1_max_at_39/)
- M5 Max, Splash 1.0.2: decode stays at 68 tok/s at 51.5K, versus 83 at a short prompt. — [splash #37](https://github.com/incoai/splash/issues/37)
- On an M2 Ultra, Splash-M1 "keeps crashing at larger contexts (64K or 128K and up)." — [r/LocalLLM 1wpza1i comment](https://www.reddit.com/r/LocalLLM/comments/1wpza1i/a_breakthrough_for_m1_and_m2_macs/)
- Splash long-context quality is disputed. One commenter: "I heard splash has problems after a long context, forgetting things." Another: "Used splash on a 256k context ... It held fairly well." — [r/LocalLLM 1woq7cd](https://www.reddit.com/r/LocalLLM/comments/1woq7cd/you_can_now_run_qwen3827b_on_a_2021_m1_max_at_39/)
- On GPUs, quantized KV and low quants are blamed for indentation and edit errors ("might be the result of quantizing KV and/or a low q4 quant"). One user says the Q4 GGUFs "fuck with super long context tasks" and that keeping linear-attention layers unquantized fixed it (vLLM, not Mac). — [r/LocalLLaMA 1wp0z3i](https://www.reddit.com/r/LocalLLaMA/comments/1wp0z3i/qwen3827b_is_good_enough_that_i_stopped_using_api/)
- Cache invalidation: a harness that does not respect prefix caching triggers full re-prefill on a 3-word input. — [r/LocalLLM 1whqwdq](https://www.reddit.com/r/LocalLLM/comments/1whqwdq/i_ran_qwen_38_27b_locally_for_30_days_here_are/)

### Inferences
- On an M4 Max 128 GB, keep context ≤128K and rely on compaction plus subagents. Extrapolating from Ultra prefill, cold 128K prefill would take roughly 8–15 min. No fp16 KV quantization is needed for memory reasons.

### Gaps
- No direct M4 Max long-context prefill or decode curve for the 27B was found.

## 5. Agentic use: harnesses, tool-calling reliability, loops

### Takeaway
Practitioners use Pi, OpenCode, Cline, Hermes, Goose and Claude Code (via Ollama's `ollama launch claude` or an Anthropic-compatible endpoint). Tool-call JSON validity is good at Q4/Q8 in short tests. Failure modes in long sessions are:
- poisoned or looping tool calls at 100K+ context, worse at Q4;
- edit-tool indentation failures;
- repetitive rewrite loops;
- Claude Code's `effort: high` crashing the template (HTTP 500).

### Cited Findings
- M3 Ultra/M4 Pro oMLX: tool calls passed 4/4 (oQ4e and oQ8e) with 0 invalid JSON. An independent M4 Pro 64 GB tester had dense-instruct pass 5/5 tool calls and finish a multi-file fix that the MoE model broke. — [omlx #2811](https://github.com/jundot/omlx/discussions/2811)
- "Poisoned tool calls (may be related to Q4)": with 100K+ context, a bad tool call gets spammed in a loop even after the user warns the model. The author's fixes are enforced subagents, per-subagent reasoning levels, and loop detection that deletes bad tool calls. — [r/LocalLLM 1whqwdq](https://www.reddit.com/r/LocalLLM/comments/1whqwdq/i_ran_qwen_38_27b_locally_for_30_days_here_are/)
- Counterpoints in the same thread:
  - FP8 "several million tokens ... no issues with tool calls and it barely ever loops," running to ~262K with auto-compact. Looping "happens far sooner at Q4."
  - Another user on UD-Q4_K_XL with q8_0 KV saw zero issues after fixing cache evictions.
  - Source: [same thread](https://www.reddit.com/r/LocalLLM/comments/1whqwdq/i_ran_qwen_38_27b_locally_for_30_days_here_are/)
- Pi agent, Q4_K_S with Q8_0 KV: "The edit tool in Pi is the weakest link, the model often has to retry edits, because it messed up the indentation." Swift-Qwen was faster but got "trapped in loops." — [r/LocalLLaMA 1wp0z3i](https://www.reddit.com/r/LocalLLaMA/comments/1wp0z3i/qwen3827b_is_good_enough_that_i_stopped_using_api/)
- Agentic loop anecdote: the model wrote an email for 30 minutes, then deleted and rewrote it 10+ times. Another user replied "Something is not right on that setup." — [r/LocalLLM 1wgwgrf](https://www.reddit.com/r/LocalLLM/comments/1wgwgrf/what_do_you_guys_think_of_qwen_38_27b_so_far_can/)
- Harness comparison with the 27B UD-Q4_K_XL (GPU), 144 runs: solve rate was tied across mini-swe-agent, Codex CLI, OpenCode and Qwen Code (21–23/24). OpenCode was 2–4x faster and passed 9/9 safety probes. — [r/LocalLLaMA 1x357dq](https://www.reddit.com/r/LocalLLaMA/comments/1x357dq/standard_evals_cant_tell_my_local_quants_apart_my/)
- Claude Code: the Qwen3.8 template accepts only xhigh/medium/low. Claude Code's default `effort: "high"` causes HTTP 500 on vLLM's `/v1/messages`, and Claude Code retries, so sessions look hung. The workaround is `CLAUDE_CODE_EFFORT_LEVEL=medium` or `--effort`. The issue was closed as not planned (2026-10-03). — [QwenLM/Qwen3.8 #217](https://github.com/QwenLM/Qwen3.8/issues/217)
- `ollama launch claude --model qwen3.8` works for fully local Claude Code. Codersera's verdict is "viable execution layer for well-scoped work," not a Claude Code replacement. — [Codersera](https://codersera.com/blog/qwen-3-8-27b-local-claude-code-replacement-2026/)
- Ollama `qwen3.8:27b-mlx` rejects the "developer" role on `/v1/responses`, which breaks `ollama launch codex`. — [OrcaRouter](https://www.orcarouter.ai/blog/qwen-3-8-27b-mlx)
- One user reported "Jinja Exception: System message must be at the beginning" with GGUF + Ollama + Claude Code. — [Towards AI article, via search](https://pub.towardsai.net/how-to-use-unsloth-qwen3-8-27b-gguf-in-claude-code-via-ollama-without-dying-in-the-process-1-2-31acd5105227)
- Common workflow: a cloud model (ChatGPT/Claude/"Astra") plans and the local 27B implements. — [r/LocalLLM 1wgwgrf](https://www.reddit.com/r/LocalLLM/comments/1wgwgrf/what_do_you_guys_think_of_qwen_38_27b_so_far_can/)
- A 27B-only project took 10 h where Claude would have taken about 30 min. — [r/LocalLLaMA 1wp0z3i](https://www.reddit.com/r/LocalLLaMA/comments/1wp0z3i/qwen3827b_is_good_enough_that_i_stopped_using_api/)
- Splash/M1 tool-calling complaints: one M1 Ultra user said that once it "starts tool calling ... it threw some weird number in the middle of chat and do really weird stuff." That is ambiguous; it may have been about MTPLX. Another user said JSON-schema responses were cut off. — [r/LocalLLM 1woq7cd](https://www.reddit.com/r/LocalLLM/comments/1woq7cd/you_can_now_run_qwen3827b_on_a_2021_m1_max_at_39/)
- Vendor benchmarks: Terminal-Bench 2.1 73.0 for 3.8 vs 63.4 for 3.6; SWE-bench Pro 61.7 (re-run by Qwen, graded C). — [Codersera](https://codersera.com/blog/qwen-3-8-27b-local-claude-code-replacement-2026/)

### Inferences
- On Macs, Q8 or oQ8e is a reasonable trade for long unattended agent runs, given the Q4 looping reports. Q4 with MTP is better for interactive speed.
- Claude Code users must pin effort to medium regardless of runtime when the server applies the official template.

### Gaps
- No Mac-specific Terminal-Bench or SWE-bench runs by community members were found.
- No Claude Code Router–specific reports for the 27B on Mac were found.
- No Aider reports were found.

## 6. Head-to-head: 27B dense vs Flash-Next MoE, and vs Qwen3.6-27B

### Takeaway
On agentic coding, the most careful community bench favors Flash-Next (125B-A6B) clearly: 98% vs 77% on hidden-test tasks, and 82% vs 69% on SWE-rebench. Flash-Next also has broader world knowledge. On single-question evals and some personal domain tests, the 27B ties or wins, and Flash-Next truncates more from overthinking. On a 128 GB Mac, Flash-Next 4-bit nearly fills the GPU working set (~104 GB), while the 27B leaves huge headroom. Versus Qwen3.6-27B, the 3.8 model is the same architecture with large post-training gains, but it uses more tokens and is slower per task.

### Cited Findings
- 2× RTX 5070 Ti bench (2026-10-11), OpenCode, 112 runs each:
  - 27B NVFP4 solved 86/112 (77%); Flash-Next NVFP4 solved 110/112 (98%).
  - Hidden-tests-no-hints family: 1/12 vs 12/12.
  - Time per run 271 s vs 207 s; generated tokens 72K vs 46K.
  - SWE-rebench: 69% vs 82% (p≈0.007).
  - Vendor SWE-bench Pro is basically tied (61.7 vs 62.5).
  - Source: [r/LocalLLaMA 1x357dq](https://www.reddit.com/r/LocalLLaMA/comments/1x357dq/standard_evals_cant_tell_my_local_quants_apart_my/)
- Personal domain test (2026-10-12): Flash-Next (OpenRouter, undisclosed quant) scored below the 27B bf16 and was "the model that gets truncated the most" even at 32K max tokens. In the comments, one user says Flash-Next is "leagues above" in real projects. Another says "flash next is not a straight upgrade to 27b ... 6b active vs 27b active." — [r/LocalLLaMA 1x49pmn](https://www.reddit.com/r/LocalLLaMA/comments/1x49pmn/qwen3827b_vs_frontier_vs_others/)
- "The 27B can't [replace Claude], but the Qwen 3.8 Flash Next almost can." One user uses Flash-Next to plan and Swift-27B to implement. — [r/LocalLLM 1wgwgrf](https://www.reddit.com/r/LocalLLM/comments/1wgwgrf/what_do_you_guys_think_of_qwen_38_27b_so_far_can/)
- M4 Pro 64 GB (oMLX): MoE was stronger on long context and deep reasoning, and dense was better on a multi-file fix. That comment pairs the dense 27B with "MoE (~21 GB)", most likely a 35B-A3B, not Flash-Next. — [omlx #2811](https://github.com/jundot/omlx/discussions/2811)
- Flash-Next on an M4 Max 128 GB via oMLX 0.6.4 oQ4e MTP:
  - Footprint ~103.94 GB; Metal working-set cap ≈107.5 GB.
  - 69.14 tok/s on sequence prompts and 53.74 tok/s on code.
  - Do not run another GPU-heavy app alongside it.
  - Source: [Weschera/qwen38-flash-next-omlx-mac](https://github.com/Weschera/qwen38-flash-next-omlx-mac), [hudsonwa recipe](https://github.com/hudsonwa/Qwen3.8-Flash-Next-oMLX-Recipe) (via search summary)
- vs Qwen3.6-27B:
  - Same architecture and context; AA Index 21.43 vs 33.70; Terminal-Bench 63.4 vs 73.0.
  - 3.8 uses ~200M vs 160M output tokens on the Index, and cost per task is ~$1.01 vs $0.62.
  - Source: [Codersera](https://codersera.com/blog/qwen-3-8-27b-local-claude-code-replacement-2026/)
  - User report: basic tasks are "up to 50% slower than 3.6," but "the improvement jump from 3.6 to 3.8 is extremely large." — [r/LocalLLM 1whqwdq](https://www.reddit.com/r/LocalLLM/comments/1whqwdq/i_ran_qwen_38_27b_locally_for_30_days_here_are/)
- M1 Max Splash: 27B dense averaged 39.1 tok/s versus 94.7 tok/s for Qwen3.6-35B-A3B MoE. Prefill was 142 vs 448 tok/s. — [r/LocalLLM 1woq7cd](https://www.reddit.com/r/LocalLLM/comments/1woq7cd/you_can_now_run_qwen3827b_on_a_2021_m1_max_at_39/)

### Inferences
- On a 128 GB M4 Max, decode speeds of the 27B (oQ4e+MTP) and Flash-Next (oQ4e+MTP) are similar, in the ~50–70 tok/s range. Flash-Next is stronger on hard agentic tasks but leaves little memory headroom. The 27B fits better as a fast secondary or subagent model, or for co-residency with other models.

### Gaps
- No same-Mac, same-harness 27B vs Flash-Next agentic comparison was found. The careful bench above was run on NVIDIA.

## 7. Fine-tunes and derivatives

### Takeaway
**Swift-Qwen3.8-27B (UkisAI)** is the dominant derivative. It cuts thinking by ~58% and roughly doubles effective speed. It has 100K+ downloads and was the #1 fine-tune on HF trending in mid-September. Reports are mixed on accuracy: many users praise it, while some measure losses or loops. Uncensored/abliterated variants are widely used, including on Macs via oMLX. "Arex-2" and mradermacher fine-tunes come up in personal benches.

### Cited Findings
- Swift launch (2026-09-14): claims −58.3% thinking and 1.95x speed at xhigh accuracy.
  - "Unlike 3.8 Grug, this didn't make the model lazy."
  - One user found it 45% faster but missing details in a stock-analysis pipeline (Q8, f16 context).
  - The uncensored FP8 build under OpenCode/Cline with MTP was "about 10% slower than Unsloth's FP8 ... but doesn't appear to suffer from the crazy overthinking."
  - The team said they were working on a Flash-Next version (−38.1% median thinking).
  - Source: [r/LocalLLaMA 1wg7dd5](https://www.reddit.com/r/LocalLLaMA/comments/1wg7dd5/ukisai_swiftqwen3827b_583_thinking_x195_speed/)
- Swift hit 100K+ downloads, #1 fine-tune and #9 model on HF trending (2026-09-17). — [r/LocalLLaMA 1wj3s31](https://www.reddit.com/r/LocalLLaMA/comments/1wj3s31/) (title only; thread not read)
- Critique of Swift 1.5 accuracy: BF16 91.4%, Unsloth 4-bit 85.1%, Swift 82.9%. The commenter argues "the entire point of that 27b model ... is it's over-thinking." Swift also took much longer on an OpenRouter provider. — [r/LocalLLaMA 1x49pmn](https://www.reddit.com/r/LocalLLaMA/comments/1x49pmn/qwen3827b_vs_frontier_vs_others/)
- Swift users report loops ("trapped in loops, which is very rare in vanilla Qwen"). — [r/LocalLLaMA 1wp0z3i](https://www.reddit.com/r/LocalLLaMA/comments/1wp0z3i/qwen3827b_is_good_enough_that_i_stopped_using_api/)
- A senior dev on llama.cpp Vulkan Q6 + DFlash2 rates "Qwen 3.8 on xhigh as highly as Opus 4.6" and uses Swift for speed. — [r/LocalLLM 1wgwgrf](https://www.reddit.com/r/LocalLLM/comments/1wgwgrf/what_do_you_guys_think_of_qwen_38_27b_so_far_can/)
- A Swift Splash package exists for Macs (SiliconSpecies/Swift-Qwen3.8-27B-Splash). It claims 79–129 tok/s decode at 1K–8K and ~88 at 64K, with DFlash2 acceptance ~0.61, but the chip is not named. — [HF](https://huggingface.co/SiliconSpecies/Swift-Qwen3.8-27B-Splash)
- Uncensored on Mac: an M2 Max 96 GB user runs "oMLX deployment of 3.8 27b Abliterated." — [r/LocalLLM 1woq7cd](https://www.reddit.com/r/LocalLLM/comments/1woq7cd/you_can_now_run_qwen3827b_on_a_2021_m1_max_at_39/)
- Swift-Qwen3.8-27B-Uncensored autorounded with linear-attention layers left unquantized: ~110 tok/s, 27 GB, served on vLLM (non-Mac). — [r/LocalLLaMA 1wp0z3i](https://www.reddit.com/r/LocalLLaMA/comments/1wp0z3i/qwen3827b_is_good_enough_that_i_stopped_using_api/)
- Arex-2 Q4_K_M is reported to outperform the base model at full quality on one personal bench. "Iv been using arex for agentic coding ... much better than base qwen." — [r/LocalLLaMA 1x49pmn](https://www.reddit.com/r/LocalLLaMA/comments/1x49pmn/qwen3827b_vs_frontier_vs_others/)
- Qwen3.8-27B-Humanlike-Chat 2.0 (tool calls) and a creative-writing 27B fine-tune exist. — [r/LocalLLaMA listing](https://www.reddit.com/r/LocalLLaMA/comments/1wvxl4n/) (titles only)

### Inferences
- For Mac speed, Swift + Splash/MTP stacks multiplicatively: fewer reasoning tokens and faster tokens. For long autonomous agent runs, the community is split. Base Qwen at medium effort is seen as safer.

### Gaps
- **No community reports found for ukisai Qwen3.8-27B-multi-turn-agent-sft.**
- No Mac-measured Swift accuracy deltas were found.

## 8. Known bugs and workarounds

### Takeaway
Template issues dominate:
- xhigh empty answers;
- `effort: high` rejected;
- empty historical `<think>` blocks invalidating the cache;
- `preserve_thinking` needing to be on;
- `developer` role rejected.

Runtime issues include LM Studio dropping `reasoning_effort` and its small default context, oMLX settings quirks and ANE kernel packaging, and Splash crashes at long context on M2 Ultra.

### Cited Findings
- xhigh empty-answer bug and workarounds (repetition_penalty 1.05–1.10, effort medium, thinking budget). — [QwenLM/Qwen3.8 #216](https://github.com/QwenLM/Qwen3.8/issues/216)
- `reasoning_effort="high"` raises an exception and returns HTTP 500 for Claude Code. Pin `CLAUDE_CODE_EFFORT_LEVEL=medium`. — [QwenLM/Qwen3.8 #217](https://github.com/QwenLM/Qwen3.8/issues/217)
- The official template wraps every assistant turn in think blocks, including empty ones. In multi-turn agent loops they nest or truncate, so use a corrected template. — [OrcaRouter](https://www.orcarouter.ai/blog/qwen-3-8-27b-mlx)
- Fixed-template collections say the official Qwen 3.8 template "injects duplicate blank <think></think>" and support `preserve_reasoning`/`preserve_thinking`. A vLLM fork defaults preserve_thinking to true because "Qwen 3.8 was trained with retained reasoning context." — [froggeric/Qwen-Fixed-Chat-Templates](https://huggingface.co/froggeric/Qwen-Fixed-Chat-Templates), [nrrso/Qwen3-Chat-Template-vLLM-Fixes](https://huggingface.co/nrrso/Qwen3-Chat-Template-vLLM-Fixes) (via search summary). Codersera also recommends keeping `preserve_thinking` on. — [Codersera](https://codersera.com/blog/qwen-3-8-27b-local-claude-code-replacement-2026/)
- LM Studio silently drops `reasoning_effort` ([#216](https://github.com/QwenLM/Qwen3.8/issues/216)). Its 8,192 default context gets consumed by thinking ([Codersera](https://codersera.com/blog/qwen-3-8-27b-local-claude-code-replacement-2026/)).
- oMLX quirks ([omlx #2811](https://github.com/jundot/omlx/discussions/2811)):
  - `mtp_num_draft_tokens` cannot be set via PUT.
  - The context bench persists the cap.
  - Running two variants at once returns 409.
  - Setting only reasoning_effort can leave thinking off.
  - A TQ+MTP crash was fixed in 0.6.2.
  - On the 0.6.2 open-source build the ANE runtime was unavailable.
- Further oMLX quirks ([Weschera repo](https://github.com/Weschera/Qwen3.8-27B-oMLX-MTP-Mac)):
  - The brew bottle lacks the ANE prefill kernel ("qwen35_prefill: available: false").
  - Settings apply only after `omlx restart`.
  - The brew service holds ~17 GB at boot.
- Ollama: `qwen3.8:27b` and `qwen3.8:27b-mtp-q4_K_M` share a digest ([splash #37](https://github.com/incoai/splash/issues/37)). The `-mlx` tag rejects the developer role on `/v1/responses` ([OrcaRouter](https://www.orcarouter.ai/blog/qwen-3-8-27b-mlx)).
- Splash:
  - Loads only Splash packages, not MLX/GGUF weights.
  - Stop it with SIGINT, because pkill makes it respawn.
  - Requires macOS 26.4+.
  - Crashes at 64K–128K+ on an M2 Ultra (M1 port).
  - Source: [r/LocalLLM 1wpza1i](https://www.reddit.com/r/LocalLLM/comments/1wpza1i/a_breakthrough_for_m1_and_m2_macs/)
- Power state matters on MacBooks: decode fell from 84 to 16 tok/s on a 15 W USB-C source. — [splash #37](https://github.com/incoai/splash/issues/37)

### Inferences
- A robust Mac setup for agents is: a corrected template with preserve_thinking=true, effort pinned to medium (or low for subagents), repetition_penalty ~1.05 if xhigh is ever used, context raised explicitly, and a harness that preserves the prefix cache.

### Gaps
- I did not find LM Studio- or mlx-lm-specific GitHub issues for Qwen3.8-27B tool-call parsing on Mac.
- Reddit search via the MCP is listing-only, so older or low-score Mac threads (for example in r/macapps or r/ollama) may have been missed.
