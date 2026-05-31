# Paste-ready comment — deepseek-ai/DeepSeek-V4-Flash PR/discussion #16 ("Add chat template")

URL: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/discussions/16
Post under your HF account (no HF token configured locally). A shorter variant for the
`mlx-community/DeepSeek-V4-Flash-2bit-DQ` repo's Community tab is at the bottom.

---

A downstream data point from the MLX side, in support of landing this.

The `mlx-community/DeepSeek-V4-Flash-2bit-DQ` conversion currently ships a minimal
`chat_template.jinja` with **no tools branch**, so `mlx_lm.server` logs *"model does not support
tool calling"* and silently drops the `tools` array — tool calling is broken out of the box on
MLX, consistent with the "load-bearing for the agent ecosystem" note here.

To check whether it's even worth wiring up on such a heavily quantized build, I added a tool-aware
template + parser and benchmarked the **2-bit** model: **33/40 (82%)** on a jdhodges-style tool
suite and **6/12 (50%)** on Veerman, up from 8/40 and 2/12 with tools dropped. So even the 2-bit
MLX build is genuinely tool-capable once a template is present — more motivation to land one here
and propagate it to the conversions.

Heads-up for whoever ports this template to MLX: **mlx-lm matches tool-call markers by exact
token-id sequence**. A marker whose closing bracket merges with the next emitted byte silently
never matches — I hit this with a Hermes-style `<tool_call>` template (`>` + `\n` tokenize to one
`>\n` token), and filed a fix for the generic `json_tools` parser: ml-explore/mlx-lm#1335 /
ml-explore/mlx-lm#1336. The DSML core `｜DSML｜` is a special token in this tokenizer, but the full
markers (`<｜DSML｜tool_calls>`, `<｜DSML｜invoke …>`) span several tokens, so it's worth confirming
mlx-lm's matcher catches them cleanly when this template reaches MLX consumers.

Full write-up + reproducer: https://github.com/snagnever/macstudio-local-llm/blob/deepseek-v4-tool-template/docs/benchmark-plans/2026-05-30-deepseek-v4-flash-tool-template.md

---

## Shorter variant — for `mlx-community/DeepSeek-V4-Flash-2bit-DQ` (Community → New discussion)

**Title:** Tool calling: conversion ships no tool template (+ an mlx-lm parser gotcha)

This conversion's `chat_template.jinja` has no tools branch, so `mlx_lm.server` drops the `tools`
array ("model does not support tool calling") and tool calling fails out of the box. With a
tool-aware template the 2-bit model reaches **82% jdhodges / 50% Veerman** tool-calling, so it's
worth adding once the official template (deepseek-ai/DeepSeek-V4-Flash#16) lands. Note also that
mlx-lm's `json_tools` parser misses calls when a marker's closing `>` merges with the next token
(fix: ml-explore/mlx-lm#1335 / #1336) — relevant when wiring up any `<tool_call>`-style template here.
