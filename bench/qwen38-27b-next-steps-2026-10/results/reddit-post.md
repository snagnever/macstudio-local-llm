# Dense Qwen3.8-27B on an M4 Max 128 GB: Splash 1.3.1 is the fastest of 3 servers, but Qwen3.8-Flash-Next is still ~2× faster for agent loops

**TL;DR**

- Fastest setup: **Splash 1.3.1 + DFlash2** (8-bit weights). Agent turn time at 128K: **17.7 s** at thinking effort xhigh, **15.9 s** at medium.
- **0.69×** the baseline (mlx-dspark 0.20.3 + DFlash2, same weights and draft, 25.7 s at xhigh).
- Still **~2×** Qwen3.8-Flash-Next, our daily model (8.6 s; 2.06× at xhigh, 1.85× at medium): for agent loops, Flash-Next is still faster.

Agent turn time = time to the first token of a turn that carries a tool result, plus 512 generated tokens. Median of the repetitions on one machine; shorter is better.

| Setup | Thinking effort | 32K | 128K |
|---|---|---:|---:|
| mlx-dspark 0.20.3 + DFlash2 (baseline) | xhigh | 17.0 s | 25.7 s |
| mlx-dspark 0.20.3 + DFlash2 (baseline) | medium | 13.5 s | not measured |
| Splash 1.3.1 + DFlash2 | xhigh | 13.3 s | 17.7 s |
| Splash 1.3.1 + DFlash2 | medium | 10.4 s | 15.9 s |
| mlx-serve 26.10.2 + DFlash2 | xhigh | 19.9 s | 44.7 s |
| mlx-serve 26.10.2 + DFlash2 | medium | 15.7 s | 34.8 s |
| Qwen3.8-Flash-Next · Swift 1.5 quant (our daily model), reference on mlx-serve 26.10.1 | xhigh | 7.9 s | 8.6 s |
| Qwen3.8-Flash-Next · ddalcu iQ quant, reference on mlx-serve 26.10.1 | xhigh | 8.1 s | 8.9 s |

Full page (selection funnel, every number, how to run it): https://snagnever.github.io/macstudio-local-llm/qwen38-27b-stacks.html

**If you run it on Splash 1.3.1:** do not resend `reasoning_content` in earlier assistant messages. At 128K every tool turn that did got HTTP 400 (6/6); without it 6/6 worked (TTFT 7.4 s).

**Limitations.** One M4 Max 128 GB; 3 repetitions per point (median); a synthetic agent-turn probe, not a real task. Quality and per-task time were not measured for the 27B. 8 of the 11 candidate setups never got the full test (5 never ran; 3 ran only an 8K smoke). The Splash prefill gain over the baseline is attributed to the Neural Engine by the vendor only.
