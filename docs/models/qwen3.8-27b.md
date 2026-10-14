# Qwen3.8-27B (dense)

> **Status: 🟡 ALTERNATIVE MODEL — not the agentic driver.** The fastest stack measured for the dense 27B on this
> rig is **Splash 1.3.1** with `mlx-community/Qwen3.8-27B-8bit` and the DFlash2 draft, at `reasoning_effort`
> **medium**: T_turno (time for one tool turn with a 512-token reply) **10.4 s at 32K** and **15.9 s at 128K**.
> That is 0.69× the previous best 27B stack at 128K (`xhigh`), and still **1.85×** the Flash-Next daily driver
> (8.6 s at 128K). The NO-GO as agentic driver stands (`P5_GO=0`). Use the 27B in place of Flash-Next when you need
> image input or ~60 GB of free RAM. Quality is **not measured** on this stack.
> Last updated: 2026-10-14

Campaign that selected this stack: [`bench/qwen38-27b-next-steps-2026-10/results/summary.md`](../../bench/qwen38-27b-next-steps-2026-10/results/summary.md) (2026-10-13/14, pt-BR).
Earlier 27B campaign (2026-10-08, oMLX / MTPLX / mlx-dspark / mlx-serve 26.10.1): [`bench/engine-updates-2026-10/results/27b-summary.md`](../../bench/engine-updates-2026-10/results/27b-summary.md), fixes in [`etapa-f-fixes.md`](../../bench/engine-updates-2026-10/results/etapa-f-fixes.md).
Research behind the campaign: [`research/qwen38-27b-next-steps-20261013.md`](../../research/qwen38-27b-next-steps-20261013.md), [`research/swift15-27b-mlx-serve-20261013.md`](../../research/swift15-27b-mlx-serve-20261013.md).
Dashboard: [`reports/qwen38-27b-stacks.html`](../../reports/qwen38-27b-stacks.html) (public: <https://snagnever.github.io/macstudio-local-llm/qwen38-27b-stacks.html>).
Agentic driver this model is compared against: [`qwen3.8-flash-next.md`](qwen3.8-flash-next.md).

## At a glance

| Field | Value |
|---|---|
| Vendor / base model | [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) |
| Parameters | 27B dense, 64 layers: 48 Gated DeltaNet + 16 attention (4 KV heads, dim 256), one MTP layer |
| Native context | 262,144 tokens (1M with YaRN factor 4); measured here at 32K and 128K |
| KV cost | 64 KiB/token in bf16: 8 GiB at 128K. Memory is never the limit on 128 GB; prefill is |
| Modalities | Image + text input (vision encoder). The measured runs use `--language-only` |
| Reasoning | Thinking on. Valid efforts: `xhigh` (default), `medium`, `low`. `high` raises a template error (HTTP 500, QwenLM #217) |
| Vendor sampling (thinking) | `temperature=1.0, top_p=0.95, top_k=20, min_p=0, presence_penalty=0` |

## Recommended local setup (Splash 1.3.1)

| Item | Value |
|---|---|
| Runtime | Splash 1.3.1 (Inco AI), standalone install in `~/.local/opt/qwen38/splash-v1.3.1/` (not the LM Studio copy) |
| Target weights | [`mlx-community/Qwen3.8-27B-8bit`](https://huggingface.co/mlx-community/Qwen3.8-27B-8bit) rev `815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9`, passed as a Hub ID. Splash refuses a local target directory: pre-fill the HF cache, then run with `--offline` |
| Draft | [`incoai/Qwen3.8-27B-DFlash2`](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2) rev `dedf8df68adfb1afeaf7b7480c0a0243108177b4`, local directory via `--draft-model` |
| KV cache | int8, the Splash 1.3.1 default (`--kv-format`) |
| Context | `--max-context 131072` |
| Endpoint | `http://<rig>:8585/v1` (OpenAI-compatible); model id `mlx-community/Qwen3.8-27B-8bit` |
| Effort | `medium`. Splash honours a top-level `reasoning_effort` |
| Launcher | [`bench/qwen3.8-prefix-cache/scripts/run-splash.sh`](../../bench/qwen3.8-prefix-cache/scripts/run-splash.sh) `K`, flags in [`config/splash-flags.env`](../../bench/qwen3.8-prefix-cache/config/splash-flags.env); the campaign arm is the `k27` block of [`run-candidate.sh`](../../bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh) |

```bash
# once: pre-fill the HF cache with the pinned target
~/.local/opt/qwen38/splash-v1.3.1/python/bin/hf download mlx-community/Qwen3.8-27B-8bit \
  --revision 815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9

~/.local/opt/qwen38/splash-v1.3.1/bin/splash serve \
  --model mlx-community/Qwen3.8-27B-8bit --host 0.0.0.0 --port 8585 \
  --max-context 131072 \
  --revision 815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9 \
  --draft-model ~/.cache/local-llms/qwen3.8-prefix-cache/incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4 \
  --idle-release off --language-only --no-webui --offline
```

| Flag | Reason |
|---|---|
| `--idle-release off` | The default releases the model after 10 idle minutes; the next request then reloads it |
| `--language-only` | Skips the vision tower. **Drop it when you want image input** (not measured without it) |
| `--offline` | Loads the pinned target from the HF cache; no Hub access at start |
| `--no-webui` | API only |

### Effort: use `medium`

Effort changes decode speed, not only the length of the reasoning. With `medium` the draft is accepted more often:
on Splash, decode rises from 54.7 to 79.3 tok/s at 32K and from 49.8 to 60.5 tok/s at 128K. Warm TTFT does not
change. The mlx-serve arm shows the mechanism, because it reports acceptance: 0.46 → 0.79 at 32K and 0.54 → 0.77
at 128K. `medium` also writes about half the tokens (median 637 vs 1542 at 32K), so the real gain per answer is
larger than the T_turno gain.

### Client cautions

- **Do not resend `reasoning_content`** in assistant messages. Splash 1.3.1 answers HTTP 400 to a tool turn that
  carries the previous reasoning (6 of 6 in the 128K think probe). Dropping it works (warm TTFT 7.4 s).
- Never send `reasoning_effort: "high"`.
- Splash reports `usage.prompt_tokens_details.cached_tokens` (hit 0.96 at 32K, 0.99 at 128K).

## Measured performance (2026-10-13/14, M4 Max 128 GB, temp 1.0)

`cache_probe.py`, fixture `audit_retrieval`, 3 repetitions, needles at 10/50/90%, `max_tokens` 4096.
T_turno = warm TTFT of `tool_turn` + 512 / median warm decode.

| Stack | Effort | T_turno 32K | T_turno 128K | Warm TTFT tool_turn 32K / 128K | Decode 32K / 128K | Cold prefill 32K / 128K | Wired peak 128K |
|---|---|---:|---:|---|---|---|---:|
| **Splash 1.3.1 + DFlash2, mlx-community 8bit (k27)** | **medium** | **10.4 s** | **15.9 s** | 3.9 / 7.4 s | 79.3 / 60.5 tok/s | 358 / 235 tok/s | 53.5 GB |
| Splash 1.3.1 + DFlash2, mlx-community 8bit (k27) | xhigh | 13.3 s | 17.7 s | 3.9 / 7.4 s | 54.7 / 49.8 tok/s | 358 / 235 tok/s | 53.8 GB |
| mlx-dspark 0.20.3 + DFlash2, `--prefix-cache-rungs 1024` (s27r, control) | medium | 13.5 s | — | 5.5 s / — | 63.8 tok/s / — | 249 tok/s / — | — |
| mlx-dspark 0.20.3 + DFlash2, `--prefix-cache-rungs 1024` (s27r, control) | xhigh | 17.0 s | 25.7 s | 5.4 / 9.8 s | 44.0 / 32.3 tok/s | 248 / 176 tok/s | 55.4 GB |
| mlx-serve 26.10.2, ddalcu 8bit, bundled DFlash2 drafter (r27d) | medium | 15.7 s | 34.8 s | 5.8 / 11 s | 51.9 / 21.3 tok/s | 252 / 175 tok/s | 69.5 GB |
| mlx-serve 26.10.2, ddalcu 8bit, bundled DFlash2 drafter (r27d) | xhigh | 19.9 s | 44.7 s | 5.8 / 11 s | 36.3 / 15.1 tok/s | 250 / 175 tok/s | 70.4 GB |
| Flash-Next driver w1 (Swift 1.5, mlx-serve 26.10.1) | xhigh | 7.9 s | 8.6 s | 1.8 / 1.9 s | 84.6 / 76.7 tok/s | 791 / 759 tok/s | 111.2 GB |
| Flash-Next secondary n2 (iQ-MLX-4.7bpw) | xhigh | 8.1 s | 8.9 s | 1.8 / 1.9 s | 82.3 / 73.2 tok/s | 791 / 760 tok/s | 110.6 GB |

All 27B arms pass every gate: zero HTTP errors, cache hit ≥ 0.94 (append) and ≥ 0.96 (tool_turn), swap Δ ≤ 0.04 GB,
needles 13/13 (12/13 in two 32K `xhigh` runs, one answer truncated at 4096 reasoning tokens). Empty answers
(QwenLM #216): 0 of 25 in the think probes. Splash cold TTFT at 128K is 535 s, against 713 s for the control.

Ratios at 128K: Splash `xhigh` / control = **0.689** (phase P1 passed, rule ≤ 0.75). mlx-serve `xhigh` / control =
1.739 (phase P3 failed, rule ≤ 1.00). Splash `medium` / Flash-Next w1 = **1.85**; the rule to reopen the driver
verdict is ≤ 1.25 on both bands.

8K smokes (`medium`, 1 rep; warm decode = median of identical, append and tool_turn, as on the public page): Splash
92.3, oMLX 0.7.1.dev1 oQ4e 81.4, mlx-serve drafter 80.6, mlx-serve MTP-only 51.5, llama.cpp b11569 Q8_0 + draft-mtp
35.3 tok/s. The last three were not measured at 32K/128K.

## Role on this rig

- **Not the agentic driver.** Flash-Next (Swift 1.5) stays the daily driver: 1.85× faster per tool turn at 128K
  and ahead on the one careful third-party agentic benchmark found (OpenCode, 98% vs 77%; see the research note). The bottleneck is the 27B warm TTFT on `tool_turn` (7.4 s at 128K
  on Splash). Reopening the verdict needs ≤ ~3 s warm TTFT and ≥ ~65 tok/s decode at 128K at the same time.
- **Alternative model, loaded instead of Flash-Next.** The rig serves one model at a time. The 27B on Splash peaks
  at 42–54 GB wired against ~111 GB for Flash-Next at 128K, so it frees ~60 GB for other work. Its vision
  encoder makes it the choice for image tasks (vision speed and quality are not measured here).
- **Quality on this stack is unmeasured.** Run the quality battery (~11 h) before using it for real work.

## Stacks compared (why this one)

| Stack | T_turno 32K / 128K (`xhigh`) | Verdict |
|---|---|---|
| **Splash 1.3.1 + DFlash2 (mlx-community 8bit)** | **13.3 / 17.7 s** (`medium` 10.4 / 15.9 s) | Fastest 27B stack (2026-10-13). Fastest prefill and lowest warm TTFT of the 27B |
| mlx-dspark 0.20.3 + DFlash2, `--prefix-cache-rungs 1024` | 17.0 / 25.7 s | Previous leader (2026-10-08: 16.7 / 25.7 s); reproduced within 2% |
| oMLX 0.7.0 + Jundot oQ8e-mtp (obsolete pin `c99e5aad`) | 18.0 / 29.8 s | 2026-10-08. Not re-measured with the refit pin `6c76ddfb82af` |
| MTPLX 2.12.2 (prime 64) | 17.8 / 30.2 s | 2026-10-08 |
| mlx-serve 26.10.2 + bundled DFlash2 (ddalcu 8bit) | 19.9 / 44.7 s | Decode collapses at 128K (15.1 tok/s). Same as 26.10.1 (15.5 tok/s) |
| mlx-serve 26.10.2, MTP head only | 8K smoke only | 51.5 tok/s at 8K, 38% below the drafter path; not run at 32K/128K |
| llama.cpp b11569 Q8_0 + draft-mtp | 8K smoke only | 35.3 tok/s at 8K; not competitive |

## Not measured / next tests

- Quality battery on Splash `medium` (HumanEval, GPQA, LiveCodeBench, tool-calling, IF, loops), ~11 h.
- oMLX 0.7.1.dev1 with the refit oQ8e pin `6c76ddfb82af` (fixes the o27 row of `27b-summary.md`) and oQ4e.
- Splash with the Swift 1.5 Splash pack [`SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash`](https://huggingface.co/SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash) @ `44c96f13` (4-bit + DFlash2).
- Swift 1.5 27B on mlx-serve with DFlash2 (w27d): only if a runtime fixes drafter decode at 128K.
- 256K, vision, and agentic quality (OpenCode / Terminal-Bench) are not measured.
