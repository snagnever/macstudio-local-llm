# Qwen3.8 Flash-Next — template overrides

## `swift15-effort-tail.jinja`

This file is the chat template of `Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw` at `13839b7` (MD5 `519239a4908bb1f805bbce5fa8c8a242`), with one change. The reasoning-effort instruction moves out of the first system block. It now goes into a separate system block right before the final `<|im_start|>assistant`.

Why: the official template writes the instruction at the start of the prompt, before the tools. A change of `reasoning_effort` in a session then changes the first tokens, and the prefix cache misses the whole conversation. In bench/flashnext-next-steps-2026-10 Task 3 (3e), a switch from `xhigh` to `medium` at 128K gave hit 0.00 and ~167 s TTFT. With this template, the prefix does not depend on the effort. Only the last block changes, and the next turn drops it.

`medium` renders the same as in the official template, because `medium` has no instruction.

How to use it: `bench/flashnext-next-steps-2026-10/scripts/make-overlay.sh <pack> <pack>-efftail swift15-effort-tail.jinja` builds a hardlink overlay of the pack with this template. The runtime has no flag for an external template. The arm `w1t` of `run-candidate.sh` serves that overlay.

Measured in: bench/flashnext-next-steps-2026-10/results/etapa11-effort-tail.md.
