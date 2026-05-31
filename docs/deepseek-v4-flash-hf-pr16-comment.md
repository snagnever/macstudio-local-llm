# Paste-ready comment — deepseek-ai/DeepSeek-V4-Flash PR/discussion #16 ("Add chat template")

**Post it here:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/discussions/16
(open the discussion, scroll to the comment box at the bottom, paste, "Comment". Needs your HF account.)

---

**A data point from the MLX side, strongly in support of landing this.**

I tested how this template behaves on the heavily-quantized MLX build (`mlx-community/DeepSeek-V4-Flash-2bit-DQ`, ~96 GB, running under `mlx_lm` on a 128 GB Mac Studio).

**Without a tool template** — the current state of that conversion — `mlx_lm.server` logs `"model does not support tool calling"` and silently drops the `tools` array, so tool calling is fully broken out of the box. This matches the "load-bearing for the agent ecosystem" observation in this thread.

**With this DSML template** (ported into the conversion) **+ a DSML tool parser**, I benchmarked the 2-bit model on two tool-calling suites (greedy, thinking off):

| Suite | no template | Hermes `<tool_call>` workaround | **native DSML (this template)** |
|---|---|---|---|
| jdhodges (40) | 0 (tools dropped) | 33/40 (82 %) | **39/40 (98 %)** |
| Veerman (12) | 0 | 6/12 (50 %) | **9/12 (75 %)** |
| parallel multi-tool cases | — | 3/8 | **8/8** |

Two takeaways:

1. **Even the 2-bit build is an excellent tool-caller in its native format** — 98 % on jdhodges, matching the best full-size local model I have on this rig (a 35B-A3B at 98 %). For a 2-bit checkpoint that's a strong argument that the template is what's gating tool use, not the model.

2. **Native DSML materially beats a generic Hermes `<tool_call>` workaround** (82 % → 98 %), and the gap is almost entirely **parallel calls**. DSML's single `<｜DSML｜tool_calls>` block containing multiple `<｜DSML｜invoke>` is what lets the model emit parallel calls reliably; when I coaxed it into emitting *separate* Hermes `<tool_call>` blocks instead, it produced only the first of N every time (3/8 on the parallel cases). I initially mistook that for a quantization ceiling — it wasn't; it was a format mismatch. So this template doesn't just make tool calls "more correct," it unlocks parallel calling.

**For MLX specifically:** `mlx-lm` ships no parser for DSML, so the template alone isn't sufficient there — I wrote one and submitted it upstream: [ml-explore/mlx-lm#1337](https://github.com/ml-explore/mlx-lm/pull/1337). One gotcha for anyone wiring DSML into mlx-lm: it matches tool-call markers by exact **token-id sequence**, and the marker's trailing `>` merges with the next byte on this tokenizer (`...tool_calls>\n` tokenizes as one `>\n` token), so a full-`>` marker silently never matches. I anchor on the `<｜DSML｜tool_calls` prefix instead — the `｜DSML｜` core is a special token, so it's a stable anchor. (Related generic fix for the same issue in the `json_tools` parser: [#1335](https://github.com/ml-explore/mlx-lm/issues/1335) / [#1336](https://github.com/ml-explore/mlx-lm/pull/1336).)

Net: strong +1 to landing this template — it's the enabler, and it's worth propagating into the `mlx-community` conversions too.

Methodology + per-case data: https://github.com/snagnever/macstudio-local-llm/blob/deepseek-v4-tool-dsml/docs/benchmark-plans/2026-05-30-deepseek-v4-flash-tool-template.md
