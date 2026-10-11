# Qwen3.8-Flash-Next (125B-A6B MoE)

> **Status: 🟢 DAILY DRIVER — responsiveness default.** The most responsive daily setup on this rig:
> **Swift 1.5** (`Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw`, a reasoning-efficiency fine-tune of
> Flash-Next) on **mlx-serve 26.10.1**. Same quality as the previous iQ-MLX-4.7bpw pack and 2–3× less time to
> the final answer on reasoning tasks (GPQA median 22 s vs 64 s). T_turno (time for one tool turn with a
> 512-token reply) **7.9 s at 32K** and **8.6 s at 128K**. Agent quality (Terminal-Bench) is **not measured**
> for this model yet. License: Swift Open License v1.0 on top of the Qwen Community License.
> Last updated: 2026-10-11

Campaign that selected these weights: [`bench/swift15-flashnext-2026-10/results/summary.md`](../../bench/swift15-flashnext-2026-10/results/summary.md) (2026-10-11: iQ-MLX-4.7bpw → Swift 1.5 MLX-4.7bpw, same runtime and flags).
Campaign that selected the runtime: [`bench/qwen38-flashnext-updates-2026-10/results/summary.md`](../../bench/qwen38-flashnext-updates-2026-10/results/summary.md) (2026-10-07: runtime 26.9.2 → 26.10.1).
Campaign that selected the stack: [`bench/qwen38-flashnext-daily-driver-2026-09/results/summary.md`](../../bench/qwen38-flashnext-daily-driver-2026-09/results/summary.md).
Model research, builds and older measurements: [`bench/qwen38-flash-next/references.md`](../../bench/qwen38-flash-next/references.md).
Dashboard: [`reports/qwen38-flashnext-driver.html`](../../reports/qwen38-flashnext-driver.html).

## Daily driver configuration

| Item | Value |
|---|---|
| Runtime | mlx-serve **26.10.1** (MLX 0.32.3) — `~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve` (also `~/.local/bin/mlx-serve`). Rollback: 26.9.2 in `~/.local/opt/qwen38/mlx-serve-v26.9.2/` |
| Weights | [`Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw`](https://huggingface.co/Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw) rev `13839b7` — port of [ukisai/Swift1.5-Qwen3.8-Flash-Next](https://huggingface.co/ukisai/Swift1.5-Qwen3.8-Flash-Next) |
| Local path | `~/.cache/local-llms/qwen3.8-prefix-cache/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0` |
| Rollback weights | `ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw` rev `dafff5c`, in the same cache directory; start the launcher with `FLASHNEXT_MODEL=<that path>` |
| License | Swift Open License v1.0 (free up to US$ 1M annual revenue; above that, a Swift Enterprise License) on top of the Qwen Community License 1.0 |
| Quant | Swift 1.5: calibrated 4-bit experts + 8-bit spine, same layout as the iQ pack; its n-gram table differs from the iQ pack (different LFS hash), so it is a separate 107 GB download. iQ pack (rollback): same layout as mixed-4/8 (experts 4-bit, non-expert weights 8-bit), experts calibrated with an importance matrix (`imatrix-weighted affine`); n-gram table identical to mixed-4/8, memory-mapped from SSD. The mixed-4-8bit pack is deprecated upstream since 2026-10-06 |
| Endpoint | `http://<rig>:11234/v1` (OpenAI-compatible); `/metrics` (Prometheus) |
| API model id | the weights directory name above (read it from `/v1/models`) |
| Launcher | [`tools/scripts/serve-flashnext-daily-driver.sh`](../../tools/scripts/serve-flashnext-daily-driver.sh) |

### Launch command (daily profile, 131K context)

```bash
~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve \
  --model ~/.cache/local-llms/qwen3.8-prefix-cache/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0 \
  --serve --host 0.0.0.0 --port 11234 \
  --ctx-size 131072 \
  --mtp \
  --ssm-checkpoint-max 16 \
  --prefix-cache-mem 16GB --prefix-cache-disk 100GB --prefix-cache-entries 64 \
  --metrics
```

This is the config the 2026-10-11 campaign measured (arm w1): the flags of arm n2 (2026-10-07) and of the 2026-09 candidate c1, with the Swift 1.5 weights.

### Why each parameter

| Parameter | Value | Reason |
|---|---|---|
| `--ctx-size` | 131072 | Daily band. T_turno grows only 12% from 32K to 128K on this stack. The native maximum is 262144. |
| `--mtp` | on | MTP is forced on for MoE targets; the runtime picks depth 6 and keeps PLD on (`draft_len=5`). MTP stays active at long context (`--max-mtp-ctx` default 0 = no ceiling). Measured acceptance 0.50–0.67. |
| `--prefix-cache-mem` | 16GB | The binary default (2 GB) cannot hold a 128K prefix (~3.7 GB) and re-prefills every turn (~184 s). 16 GB keeps identical/append/tool_turn at ~2 s. Decode cost: none. |
| `--prefix-cache-disk` | 100GB | Spill tier in `~/.mlx-serve/kv-cache`. Long KV goes to SSD by design, so RAM stays bounded and 256K/512K fit without swap. |
| `--prefix-cache-entries` | 64 | ~4 hot 128K sessions in RAM; dozens at typical 20–40K agent contexts. |
| `--ssm-checkpoint-max` | 16 | Gated DeltaNet state checkpoints for prefix reuse; the value the campaign measured. |
| KV quantization | off | `--kv-quant 8` costs ~38% decode at 256K and `turbo4` ~66%. Use 8-bit only for the 512K profile. |
| `--metrics` | on | Prometheus counters (prefill, cache, TTFT). MTP acceptance is **not** in `/metrics`; it is in the server log line `[spec-stats]`. |

### Client sampling (vendor thinking profile — what the campaign measured)

`temperature=1.0`, `top_p=0.95`, `top_k=20`, `min_p=0`, reasoning effort `xhigh`, thinking preserved.
At `temperature=0` the MTP accepts more drafts, so decode reads optimistic; do not tune against temp-0 numbers.
Cap `max_tokens` above 4096 for hard prompts: with `xhigh` the reasoning can pass 4096 tokens and truncate.

### Machine settings

- **No `sudo` needed** for the daily profile, 256K multi-turn, or 512K: `iogpu.wired_limit_mb` stayed at the default (0).
- Wired memory of **97–108 GB is normal** for this stack (KV and the 16 GB prefix cache are pinned). Watch swap, not wired: swap stayed flat in every run.
- **Memory decomposition (measured 2026-09-16):** weights **75,3 GB**; attention KV (only the 12
  full-attention layers carry a context-growing cache; the 36 Gated-DeltaNet layers hold a fixed
  state) is **0,8 / 3,2 / 6,4 / 12,9 GB** at 32K/128K/256K/512K fp16 (halve for KV 8-bit); the
  remaining **~21–36 GB** of wired is fixed overhead (16 GB prefix cache, DeltaNet state, MLX
  pools). The context KV is the *smallest* term — a second small model (~2 GB) fits beside the
  driver at every context up to 512K. Source: [bench/minicpm5-2b-support-2026-09](../../bench/minicpm5-2b-support-2026-09/results/etapa2-maior.md).
- One model at a time. The MoE does not batch decode: parallel requests queue on one slot.
- Keep ≥ 100 GB free on the boot volume for the prefix-cache disk tier.

## Measured performance (2026-10-07, M4 Max 128 GB, temp 1.0)

iQ-MLX-4.7bpw @ mlx-serve 26.10.1 (the daily pair until 2026-10-11, now the rollback). Swift 1.5 matches or beats these numbers (T_turno 7.9 / 8.6 s at 32K / 128K, same prefill and TTFT); see [`bench/swift15-flashnext-2026-10/results/summary.md`](../../bench/swift15-flashnext-2026-10/results/summary.md). Median of 3 repetitions. Source: [`bench/qwen38-flashnext-updates-2026-10/results/summary.md`](../../bench/qwen38-flashnext-updates-2026-10/results/summary.md).

| Context | T_turno | Cold TTFT (first turn) | Warm TTFT identical / append / tool_turn | Cache hit append / tool_turn | Warm decode | MTP acceptance | Wired peak | Swap |
|---|---:|---:|---|---|---:|---:|---:|---:|
| 32K | **8.3 s** | 34.8 s | 0.2 / 1.8 / 1.9 s | 0.96 / 0.96 | 79.4 tok/s | 0.81 | 97.7 GB | 0 |
| 128K | **8.9 s** | 165.1 s | 0.2 / 1.9 / 1.9 s | 0.99 / 0.99 | 73.9 tok/s | 0.70 | 111.6 GB | 0 |

The gain over 26.9.2 comes from decode: MTP acceptance rises from 0.50 to 0.81 at 32K. The same weights on 26.10.1 give the same T_turno as iQ (±1%). HumanEval 154/164 (iQ) against 151/164 (mixed-4/8); tool-calling 47/52 for both. 256K and 512K were not re-measured on 26.10.1.

## Previous pair: mixed-4/8 @ mlx-serve 26.9.2 (2026-09-13)

T_turno = TTFT of the `tool_turn` scenario + 512 / median warm decode (identical, append, tool_turn). Median of 3 repetitions at 32K and 128K; 1 repetition at 256K.

| Context | T_turno | Cold TTFT (first turn) | Warm TTFT identical / append / tool_turn | Cache hit append / tool_turn | Warm decode | Wired peak | Swap |
|---|---:|---:|---|---|---:|---:|---:|
| 32K | **11.03 s** | 37.0 s | 0.1 / 1.9 / 1.9 s | 0.96 / 0.96 | 55.9 tok/s | 97.3 GB | 0 |
| 128K | **12.35 s** | 178.1 s | 0.2 / 2.0 / 2.1 s | 0.99 / 0.99 | 49.7 tok/s | 108.1 GB | 0 |
| 256K | 14.2 s | 378.6 s | 0.6 / — / 2.6 s | — / 1.00 | 44.2 tok/s | 108.5 GB | 0 |

Prefill is ~700–735 tok/s from 32K to 256K. Needles at 10/50/90% were correct in every served request (a few truncated at 4096 tokens of reasoning).

### Extended profile: 512K

Measured on mlx-serve 26.9.2 with mixed-4/8. The launcher now starts this profile with the current pair (iQ @ 26.10.1), which was not re-measured at 512K.

Serves 524288 tokens with a follow-up, without `sudo`: cold TTFT 844.6 s, decode 42.6 tok/s, follow-up 0.6 s with full cache hit, wired 104.3 GB. **Memory is at the edge** (minimum free 0.01 GB): close heavy apps first. Capacity, not daily use.

```bash
tools/scripts/serve-flashnext-daily-driver.sh 512k
```

It adds `--ctx-size 524288 --kv-quant 8 --kv-attn-mode fused` and a YaRN override
(`rope_type yarn`, `factor 2.0`, `original_max_position_embeddings 262144`). 1M is out of scope: cold-only one-shot with 8-bit KV, or ~5 tok/s multi-turn with `turbo4` on 26.9.2 (`turbo2/turbo4` were removed in mlx-serve 26.9.3).

## Stacks compared (why this one)

| Stack | T_turno 32K / 128K | Verdict |
|---|---|---|
| **Swift 1.5 MLX-4.7bpw @ mlx-serve 26.10.1** | **7.9 / 8.6 s** | Default since 2026-10-11. Same quality as iQ in an A/B with `reasoning_effort xhigh` (HumanEval 158 vs 158, GPQA 43 vs 45, LCB 42 vs 41 of 50, vendor sampling); median time per GPQA question 0.35× and per LCB question 0.49×. |
| ddalcu iQ-MLX-4.7bpw @ mlx-serve 26.10.1 | 8.1 / 8.9 s (re-measured 2026-10-11) | Default 2026-10-07 → 2026-10-11; now the rollback. Same speed as mixed-4/8 on 26.10.1. |
| ddalcu mixed-4/8 @ mlx-serve 26.10.1 | 8.3 / 8.8 s | Same speed as iQ. The pack is deprecated upstream. |
| ddalcu mixed-4/8 @ mlx-serve 26.9.2 | 11.03 / 12.35 s | Default until 2026-10-07. Fastest stack of the 2026-09 campaign. |
| Jundot oQ4e-mtp @ oMLX 0.7.0.dev2 | 13.48 / 15.03 s | 2nd. Same decode (~50 tok/s at 128K), slower TTFT (warm 4.8 s, cold 259 s). No YaRN: ceiling 262K. Needs `qwen4_ple_ssd_offload: true`. |
| Jundot oQ4e-mtp @ oMLX 0.6.4 | 17.1 / 22.7 s | Dominated by 0.7.0.dev2 on the same weights. |
| Youssofal MTPLX Optimized-Speed @ MTPLX 2.11.2 | 10.6 s (1 rep) / refused | Highest decode at 32K (~70 tok/s), but refuses 128K and 256K with HTTP 507 (memory-plan fit 114,688 tokens). With `MTPLX_MEMORY_LIMIT_BYTES=102G` it admits 128K but fails 2 of 5 scenarios. |

## Known issues and cautions

- **Agent quality is unmeasured.** The older conditional promotion stands on quality: run Terminal-Bench before replacing `qwen3-coder-next` in the agent role. The driver for it is ready (`bench/terminal-bench/scripts/run-tbench-flashnext.sh`); the run is on hold because it needs a second machine for the Docker containers.
- **Instruction following (Swift 1.5).** Its card declares −3 on IFBench. The A/B's 20-case IFEval-style probe found one consistent miss (two paragraphs separated by `***`) in both sampling profiles.
- **512K with Swift 1.5 is not measured.** The `512k` launcher profile was measured on 26.9.2 with the mixed-4-8bit weights.
- The campaign harness (`bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh`) **wipes `~/.mlx-serve/kv-cache` and kills whatever listens on port 11234**. Stop the daily driver on purpose before running it.
- Reasoning at `xhigh` can exceed 4096 tokens on long mutated prompts; raise `max_tokens` in clients.
- Older numbers in `bench/qwen38-flash-next/references.md` and `bench/qwen38-updates-2026-09/` were measured at `temperature=0`; they read faster than daily use.
