# Qwen3.8-Flash-Next (125B-A6B MoE)

> **Status: 🟢 DAILY DRIVER — responsiveness default.** The most responsive daily setup on this rig:
> **Swift 1.5** (`Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw`, a reasoning-efficiency fine-tune of
> Flash-Next) on **mlx-serve 26.10.1**. Same quality as the previous iQ-MLX-4.7bpw pack and 2–3× less time to
> the final answer on reasoning tasks (GPQA median 22 s vs 64 s). T_turno (time for one tool turn with a
> 512-token reply) **7.9 s at 32K** and **8.6 s at 128K**. Agent quality (Terminal-Bench) is **not measured**
> for this model yet. License: Swift Open License v1.0 on top of the Qwen Community License.
> **Secondary driver** (2026-10-12): ddalcu iQ-MLX-4.7bpw `dafff5c` on the same runtime and flags. It is the
> rollback and the reference arm for runtime tests, because it has the longest measurement series on this rig
> (26.9.2, 26.10.1, 256K, 512K, HumanEval, tool-calling). Start it with `FLASHNEXT_MODEL=<its cache path>`.
> The 2026-10 next-steps campaign kept both drivers and the runtime: mlx-serve 26.10.2 was not adopted, and no
> other pack or runtime beat Swift 1.5. Summary: [`bench/flashnext-next-steps-2026-10/results/summary.md`](../../bench/flashnext-next-steps-2026-10/results/summary.md).
> Dense 27B next steps: [`bench/qwen38-27b-next-steps-2026-10/results/summary.md`](../../bench/qwen38-27b-next-steps-2026-10/results/summary.md) (Splash 1.3.1 is the fastest 27B stack, still about 2x this driver).
> Last updated: 2026-10-18 (daily profile context raised to 262144)

Campaign that kept the drivers and tested 26.10.2, 512K, the agent battery, oMLX packs, GGUF and `--ple-gpu`: [`bench/flashnext-next-steps-2026-10/results/summary.md`](../../bench/flashnext-next-steps-2026-10/results/summary.md) (2026-10-16).
Campaign that selected these weights: [`bench/swift15-flashnext-2026-10/results/summary.md`](../../bench/swift15-flashnext-2026-10/results/summary.md) (2026-10-11: iQ-MLX-4.7bpw → Swift 1.5 MLX-4.7bpw, same runtime and flags).
Campaign that selected the runtime: [`bench/qwen38-flashnext-updates-2026-10/results/summary.md`](../../bench/qwen38-flashnext-updates-2026-10/results/summary.md) (2026-10-07: runtime 26.9.2 → 26.10.1).
Campaign that selected the stack: [`bench/qwen38-flashnext-daily-driver-2026-09/results/summary.md`](../../bench/qwen38-flashnext-daily-driver-2026-09/results/summary.md).
Model research, builds and older measurements: [`bench/qwen38-flash-next/references.md`](../../bench/qwen38-flash-next/references.md).
Dashboard: [`reports/qwen38-flashnext-driver.html`](../../reports/qwen38-flashnext-driver.html).

## Daily driver configuration

| Item | Value |
|---|---|
| Runtime | mlx-serve **26.10.1** (MLX 0.32.3) — `~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve` (also `~/.local/bin/mlx-serve`). Rollback: 26.9.2 in `~/.local/opt/qwen38/mlx-serve-v26.9.2/`. 26.10.2 (stable) was tested on 2026-10-14 and not adopted: T_turno 1.038× at 32K and 1.000× at 128K, and it refused a 256K tool turn ([`etapa1-runtime.md`](../../bench/flashnext-next-steps-2026-10/results/etapa1-runtime.md)) |
| Weights | [`Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw`](https://huggingface.co/Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw) rev `13839b7` — port of [ukisai/Swift1.5-Qwen3.8-Flash-Next](https://huggingface.co/ukisai/Swift1.5-Qwen3.8-Flash-Next) |
| Local path | `~/.cache/local-llms/qwen3.8-prefix-cache/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0` |
| Secondary driver (rollback) | [`ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw`](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw) rev `dafff5c` (HEAD on HF as of 2026-10-12), in the same cache directory; start the launcher with `FLASHNEXT_MODEL=<that path>`. Reference arm for runtime A/B tests |
| License | Swift Open License v1.0 (free up to US$ 1M annual revenue; above that, a Swift Enterprise License) on top of the Qwen Community License 1.0 |
| Quant | Swift 1.5: calibrated 4-bit experts + 8-bit spine, same layout as the iQ pack; its n-gram table differs from the iQ pack (different LFS hash), so it is a separate 107 GB download. iQ pack (rollback): same layout as mixed-4/8 (experts 4-bit, non-expert weights 8-bit), experts calibrated with an importance matrix (`imatrix-weighted affine`); n-gram table identical to mixed-4/8, memory-mapped from SSD. The mixed-4-8bit pack is deprecated upstream since 2026-10-06 |
| Endpoint | `http://<rig>:11234/v1` (OpenAI-compatible); `/metrics` (Prometheus) |
| API model id | the weights directory name above (read it from `/v1/models`) |
| Launcher | [`tools/scripts/serve-flashnext-daily-driver.sh`](../../tools/scripts/serve-flashnext-daily-driver.sh) |

### Launch command (daily profile, 256K context)

```bash
~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve \
  --model ~/.cache/local-llms/qwen3.8-prefix-cache/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0 \
  --serve --host 0.0.0.0 --port 11234 \
  --ctx-size 262144 \
  --mtp \
  --ssm-checkpoint-max 16 \
  --prefix-cache-mem 16GB --prefix-cache-disk 100GB --prefix-cache-entries 64 \
  --metrics
```

These are the flags the 2026-10-11 campaign measured (arm w1): the flags of arm n2 (2026-10-07) and of the 2026-09 candidate c1, with the Swift 1.5 weights. The campaign served 131072 tokens. The daily profile serves 262144 tokens since 2026-10-18. The w1 arm at 256K was measured in Task 2 and Task 13 of the 2026-10 next-steps campaign (see the 256K/512K table and the open risks).

### Why each parameter

| Parameter | Value | Reason |
|---|---|---|
| `--ctx-size` | 262144 | The native maximum. Chosen on 2026-10-18 so that long sessions do not hit the context limit. T_turno grows only 12% from 32K to 128K and is 11.1 s at 256K. At 256K with unquantized KV, free memory reaches 0.01 GB; close heavy apps before long sessions. |
| `--mtp` | on | MTP is forced on for MoE targets; the runtime picks depth 6 and keeps PLD on (`draft_len=5`). MTP stays active at long context (`--max-mtp-ctx` default 0 = no ceiling). Measured acceptance 0.50–0.67. |
| `--prefix-cache-mem` | 16GB | The binary default (2 GB) cannot hold a 128K prefix (~3.7 GB) and re-prefills every turn (~184 s). 16 GB keeps identical/append/tool_turn at ~2 s. Decode cost: none. |
| `--prefix-cache-disk` | 100GB | Spill tier in `~/.mlx-serve/kv-cache`. Long KV goes to SSD by design, so RAM stays bounded and 256K/512K fit without swap. |
| `--prefix-cache-entries` | 64 | ~4 hot 128K sessions in RAM; dozens at typical 20–40K agent contexts. |
| `--ssm-checkpoint-max` | 16 | Gated DeltaNet state checkpoints for prefix reuse; the value the campaign measured. |
| KV quantization | off | `--kv-quant 8` costs ~38% decode at 256K and `turbo4` ~66%. The 512K profile uses 4-bit KV. |
| `--metrics` | on | Prometheus counters (prefill, cache, TTFT). MTP acceptance is **not** in `/metrics`; it is in the server log line `[spec-stats]`. |

### Client sampling (vendor thinking profile — what the campaign measured)

`temperature=1.0`, `top_p=0.95`, `top_k=20`, `min_p=0`, reasoning effort `xhigh`, thinking preserved.
The chat template default for `reasoning_effort` is `xhigh` in the three packs checked (Swift `13839b7`, iQ `dafff5c`, Jundot oQ4e `2615fc0`); accepted values are `xhigh`, `medium` and `low` ([`etapa0-preflight.md`](../../bench/flashnext-next-steps-2026-10/results/etapa0-preflight.md)).
Keep `xhigh` as the harness default. In the 2026-10 agent battery, `medium` and `low` scored 40–42 of 50 on the regraded LiveCodeBench against 47 for `xhigh`. That is outside the G1 margin of 3. `medium` stayed within margin on GPQA; `low` did not in one of two rounds. `medium` takes ~27% of the `xhigh` time and `low` ~16% ([`etapa3-agent.md`](../../bench/flashnext-next-steps-2026-10/results/etapa3-agent.md)).
Pin the effort per session. Switching effort mid-session gives cache hit 0.00 and ~167 s TTFT at 128K, because the official template writes the effort instruction at the start of the system prompt.
`medium` is fine outside code: on short chat and tool-calling it stayed within the G1 margin of `xhigh` on jdhodges, Veerman, IF and GPQA (2 rounds) and took 23–28% less time. In long agent sessions it had 2 empty tool-call turns against 0 for `xhigh`. Use `medium` for short chat and tool-calling, and `xhigh` for code and long sessions ([`etapa12-medium.md`](../../bench/flashnext-next-steps-2026-10/results/etapa12-medium.md)).
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
- One model at a time. Parallel requests to the driver batch their decode (see "Concurrent sessions" below).
- Keep ≥ 100 GB free on the boot volume for the prefix-cache disk tier.

### Concurrent sessions (measured 2026-10-17/18)

mlx-serve 26.10.1 batches decode for this model at its default `--max-concurrent 1`: the boot log shows `batched decode on` and `gdn batched decode engaged (slots=2)`. A second session does not queue behind the first. It shares decode: each overlapped stream runs at ~38–42 tok/s against 77–84 tok/s alone, so total decode does not grow. `--max-concurrent 2` measured the same as the default.

| Case | Worst stream ÷ solo T_turno | Notes |
|---|---:|---|
| 2 streams, 32K | 1.76× | no errors, swap 0 |
| 2 streams, 128K | 1.94× | wired peak 113.5 GB, swap 0 |
| 2 streams, 256K, `256k` profile (4 GB prefix cache) | 1.68× (1.81× against the campaign's 3-rep 256K control) | with the daily 16 GB cache, a 256K session beside a 32K one got `PrefillDoesNotFit` and missed a needle; 8-bit KV was refused with the 16 GB cache and missed a needle with the 4 GB cache |
| 3 streams with aux load, 32K / 128K | 2.37× / 2.36× | fails; fits in memory (wired peak 114.7 GB at 128K), no refusal |
| 4 streams, 32K / 128K | 2.84× / 3.85× | fails; 128K also refused 3 prefills |
| 2 Claude Code sessions (`claude -p`), 128K | 1.84–2.36× per session | every task done, no errors; the pair ends ~7% later than the two tasks run one after the other |

A short request from one session (permission check, title) waits behind another session's long prefill: p95 TTFT 170–356 s at 128K and 256K, during cold or mutated-prompt prefills. The same wait shows with `--max-concurrent 1`, and `--prefill-decode-share` 0.3 or 0.5 does not remove it (it doubles cold TTFT). Two sessions work on one driver, but they gain no time over running the tasks one after the other. Source: [`bench/flashnext-concurrency-2026-10/results/summary.md`](../../bench/flashnext-concurrency-2026-10/results/summary.md).

Splash 1.5.0 (measured 2026-10-29, `tools/scripts/serve-flashnext-splash.sh`) batches decode too, but reads one prompt at a time. The result depends on how much new prompt each turn brings:

| Test | mlx-serve | Splash 1.5.0 |
|---|---:|---:|
| One session, T_turno at 32K / 128K | 7.9 / 9.0 s (26.10.3) | 5.8 / 6.1 s |
| Two sessions, worst turn at 32K / 128K | 13.8 / 15.6 s (1.75× / 1.73×) | 14.1 / 15.4 s (2.43× / 2.52×) |
| Two 256K sessions, worst turn | 18.6 s, only with a 4 GB prompt cache (26.10.1) | 12.1 s, no memory setting |
| Short side request p95 at 128K | 183 s | 5 s |
| Claude Code pair ÷ the two tasks in sequence | 1.07 (26.10.1) | 0.76 |

With Claude Code (prompts almost all cached), two Splash sessions finish 24% sooner than the same tasks in sequence, and each task alone takes ~41 s against 62–75 s on mlx-serve. The daily driver stays on mlx-serve: Splash runs the GGUF pack, and agent quality on it is not measured. Source: [`bench/splash-concurrency-2026-10/results/summary.md`](../../bench/splash-concurrency-2026-10/results/summary.md).

```bash
tools/scripts/serve-flashnext-daily-driver.sh 256k   # two long sessions: 262144 tokens, 4 GB RAM prefix cache
```

## Measured performance (2026-10-07, M4 Max 128 GB, temp 1.0)

iQ-MLX-4.7bpw @ mlx-serve 26.10.1 (the daily pair until 2026-10-11, now the secondary driver). Swift 1.5 matches or beats these numbers (T_turno 7.9 / 8.6 s at 32K / 128K, same prefill and TTFT); see [`bench/swift15-flashnext-2026-10/results/summary.md`](../../bench/swift15-flashnext-2026-10/results/summary.md). Median of 3 repetitions. Source: [`bench/qwen38-flashnext-updates-2026-10/results/summary.md`](../../bench/qwen38-flashnext-updates-2026-10/results/summary.md).

| Context | T_turno | Cold TTFT (first turn) | Warm TTFT identical / append / tool_turn | Cache hit append / tool_turn | Warm decode | MTP acceptance | Wired peak | Swap |
|---|---:|---:|---|---|---:|---:|---:|---:|
| 32K | **8.3 s** | 34.8 s | 0.2 / 1.8 / 1.9 s | 0.96 / 0.96 | 79.4 tok/s | 0.81 | 97.7 GB | 0 |
| 128K | **8.9 s** | 165.1 s | 0.2 / 1.9 / 1.9 s | 0.99 / 0.99 | 73.9 tok/s | 0.70 | 111.6 GB | 0 |

The gain over 26.9.2 comes from decode: MTP acceptance rises from 0.50 to 0.81 at 32K. The same weights on 26.10.1 give the same T_turno as iQ (±1%). HumanEval 154/164 (iQ) against 151/164 (mixed-4/8); tool-calling 47/52 for both. 256K (T_turno 9.8 s, 1 rep) and 512K (13.0 s, 3 reps, `--kv-quant 4` + YaRN 2.0) were measured with iQ on 26.10.1 on 2026-10-11 ([`bench/engine-updates-2026-10/results/flashnext-summary.md`](../../bench/engine-updates-2026-10/results/flashnext-summary.md)); see the 512K section below.

### Measured 2026-10-14 (next-steps campaign, 3 reps)

| Arm | Runtime | Context | T_turno | Cold TTFT | Warm decode | MTP acceptance | Wired peak | Swap | Needles |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| iQ (n2) | 26.10.1 | 32K | 7.9 s | 34.5 s | 84.3 tok/s | 0.651 | 96.7 GB | 0 | 12/13 (1 truncated) |
| iQ (n2x) | 26.10.2 | 32K | 8.2 s | 34.6 s | 80.0 tok/s | 0.645 | 99.7 GB | 0 | 13/13 |
| iQ (n2) | 26.10.1 | 128K | 8.9 s | 165.4 s | 74.1 tok/s | 0.642 | 110.6 GB | 0 | 13/13 |
| iQ (n2x) | 26.10.2 | 128K | 8.9 s | 165.7 s | 74.0 tok/s | 0.775 | 106.4 GB | 0 | 13/13 |
| Swift 1.5 (w1) | 26.10.1 | 256K | 11.1 s | 350.8 s | 61.7 tok/s | 0.686 | 114.9 GB | 0 | 11/13 |
| Swift 1.5 (w1q4) | 26.10.1 | 512K | 13.3 s | 783.9 s | 53.8 tok/s | 0.698 | 113.5 GB | 0 | 13/13 |

26.10.2 against 26.10.1 on the same iQ weights: ratio 1.038 at 32K and 1.000 at 128K, above the adoption rule of ≤ 0.97. At 256K (1 rep) 26.10.2 refused the tool turn with `PrefillDoesNotFit` (~11.1 GB asked, ~10.0 GB free); 26.10.1 served 256K before. Source: [`etapa1-runtime.md`](../../bench/flashnext-next-steps-2026-10/results/etapa1-runtime.md).
Swift 1.5 at 256K uses unquantized KV and missed needles in 2 of 13 records, all with `finish_reason=stop`. A rerun in Task 13 of the same campaign (3 reps) found 15/15 for Swift and 14/15 for iQ (one truncated turn), so the 2 misses were variance: Swift totals 26/28 at 256K. Both arms reach 0.01 GB free memory ([`etapa13-needles256k.md`](../../bench/flashnext-next-steps-2026-10/results/etapa13-needles256k.md)). The 512K row is the `512k` profile (YaRN 2.0 + 4-bit KV); it passed every gate. Source: [`etapa2-swift-long.md`](../../bench/flashnext-next-steps-2026-10/results/etapa2-swift-long.md).

## Previous pair: mixed-4/8 @ mlx-serve 26.9.2 (2026-09-13)

T_turno = TTFT of the `tool_turn` scenario + 512 / median warm decode (identical, append, tool_turn). Median of 3 repetitions at 32K and 128K; 1 repetition at 256K.

| Context | T_turno | Cold TTFT (first turn) | Warm TTFT identical / append / tool_turn | Cache hit append / tool_turn | Warm decode | Wired peak | Swap |
|---|---:|---:|---|---|---:|---:|---:|
| 32K | **11.03 s** | 37.0 s | 0.1 / 1.9 / 1.9 s | 0.96 / 0.96 | 55.9 tok/s | 97.3 GB | 0 |
| 128K | **12.35 s** | 178.1 s | 0.2 / 2.0 / 2.1 s | 0.99 / 0.99 | 49.7 tok/s | 108.1 GB | 0 |
| 256K | 14.2 s | 378.6 s | 0.6 / — / 2.6 s | — / 1.00 | 44.2 tok/s | 108.5 GB | 0 |

Prefill is ~700–735 tok/s from 32K to 256K. Needles at 10/50/90% were correct in every served request (a few truncated at 4096 tokens of reasoning).

### Extended profile: 512K

The profile uses **Swift 1.5** since 2026-10-14. Swift was measured on mlx-serve 26.10.1, 3 reps (arm w1q4): T_turno 13.3 s, cold TTFT 784 s, decode 53.8 tok/s, wired 113.5 GB, minimum free 0.01 GB, swap 0, needles 13/13, no refusal and no OOM ([`etapa2-swift-long.md`](../../bench/flashnext-next-steps-2026-10/results/etapa2-swift-long.md)). The iQ pack gives 13.0 s and 0.05 GB minimum free on the same profile. Swift sits at the same memory edge. The plan asked for clean needles at 256K as well; that band missed 2 of 13 needles, but it measures the daily profile beyond its configured context, so the campaign ruled that the 512K band decides the profile. `FLASHNEXT_MODEL=<iQ path>` restores the iQ pack.

iQ-MLX-4.7bpw @ mlx-serve 26.10.1 on 2026-10-11, 3 reps (`bench/engine-updates-2026-10`, arm n2q4):

Serves 524288 tokens with follow-ups, without `sudo`: cold TTFT 784 s, prefill 662 tok/s, tool turn 3.9 s with 0.998 cache hit, decode 56 tok/s, T_turno 13.0 s, wired 113.9 GB, swap 0. **Memory is at the edge** (minimum free 0.05 GB): close heavy apps first. Capacity, not daily use.

The profile uses 4-bit KV. With 8-bit KV, 512K sometimes refused a prefill (`PrefillDoesNotFit`, short by 0.6–3.2 GB): mlx-serve 26.10.1 bills a hot-cache entry shared with a live request in full. A lower `--os-reserve-gib` does not fix it: with 2 GB, a turn failed with a Metal out-of-memory error. Needles were the only quality check of 4-bit KV.

```bash
tools/scripts/serve-flashnext-daily-driver.sh 512k
```

It adds `--ctx-size 524288 --kv-quant 4` and a YaRN override
(`rope_type yarn`, `factor 2.0`, `original_max_position_embeddings 262144`). 1M is out of scope: cold-only one-shot with 8-bit KV, or ~5 tok/s multi-turn with `turbo4` on 26.9.2 (`turbo2/turbo4` were removed in mlx-serve 26.9.3).

## Stacks compared (why this one)

| Stack | T_turno 32K / 128K | Verdict |
|---|---|---|
| **Swift 1.5 MLX-4.7bpw @ mlx-serve 26.10.1** | **7.9 / 8.6 s** | Default since 2026-10-11. Same quality as iQ in an A/B with `reasoning_effort xhigh` (HumanEval 158 vs 158, GPQA 43 vs 45, LCB 47 vs 45 of 50 after the [2026-10-14 regrade](../../bench/lcb-regrade-2026-10/results/regrade-summary.md) (was 42 vs 41; every published number: [`lcb-regrade-published.md`](../../bench/flashnext-next-steps-2026-10/results/lcb-regrade-published.md)), vendor sampling); median time per GPQA question 0.35× and per LCB question 0.49×. |
| ddalcu iQ-MLX-4.7bpw @ mlx-serve 26.10.1 | 8.1 / 8.9 s (re-measured 2026-10-11) | Default 2026-10-07 → 2026-10-11; now the rollback. Same speed as mixed-4/8 on 26.10.1. |
| ddalcu iQ-MLX-4.7bpw @ mlx-serve 26.10.2 (stable) | 8.2 / 8.9 s (2026-10-14) | Not adopted: 1.038× / 1.000× of 26.10.1 on the same weights, rule ≤ 0.97×. Refused a 256K tool turn (`PrefillDoesNotFit`). [`etapa1-runtime.md`](../../bench/flashnext-next-steps-2026-10/results/etapa1-runtime.md) |
| Jundot oQ4e refit `c4ddfb5` @ mlx-serve 26.10.2 (o1rm) | 8.6 / 9.1 s (2026-10-15) | Not a driver: 1.075× / 1.046× of Swift 1.5 (w1 8.0 / 8.7 s in the same run), needles 12/13 at 128K. Lower decode (74.9 vs 82.8 tok/s at 32K). [`etapa5-refit.md`](../../bench/flashnext-next-steps-2026-10/results/etapa5-refit.md) |
| Jundot oQ4e `2615fc0` @ oMLX 0.7.1.dev2 (o1x) | 10.3 / 11.9 s; 14.7 s at 256K (1 rep) | Reference arm for the oMLX packs. Needles 10/13 at 128K (2 truncated, 1 wrong). [`etapa5-refit.md`](../../bench/flashnext-next-steps-2026-10/results/etapa5-refit.md) |
| Jundot oQ4e refit `c4ddfb5` @ oMLX 0.7.1.dev2 (o1r) | 10.3 / 12.3 s; 15.0 s at 256K (1 rep) | The oMLX pack: Veerman 7/12 vs 10/12 for `2615fc0` in round 1 and 9/12 vs 8/12 in round 2 (16/24 vs 18/24, noise); the other five suites within margin. `2615fc0` was deleted from the rig on 2026-10-16. Same speed (the 1.034 ratio at 128K is decode noise). [`etapa5-refit.md`](../../bench/flashnext-next-steps-2026-10/results/etapa5-refit.md) |
| umixer oQ4e-mix6-mtp `73d2cd0` (= v2) @ oMLX 0.7.1.dev2 (x1) | 14.6 s at 256K (1 rep) | Does not replace the refit: G1 passes in every suite, but no suite beats it beyond the margin. Wired 107.2 GB at 256K, +7.6 GB over the refit, swap 0. [`etapa7-mix6.md`](../../bench/flashnext-next-steps-2026-10/results/etapa7-mix6.md) |
| ggml-org GGUF IQ4_NL + MTP Q8_0 @ llama.cpp b11609 (g1) | 12.2 s at 32K (1 rep) | Stopped at the smoke gate: decode 52.1 tok/s < 70 (36.0 without MTP). 0.07 GB minimum free already at 32K. [`etapa8-gguf.md`](../../bench/flashnext-next-steps-2026-10/results/etapa8-gguf.md) |
| ddalcu mixed-4/8 @ mlx-serve 26.10.1 | 8.3 / 8.8 s | Same speed as iQ. The pack is deprecated upstream. |
| ddalcu mixed-4/8 @ mlx-serve 26.9.2 | 11.03 / 12.35 s | Default until 2026-10-07. Fastest stack of the 2026-09 campaign. |
| Jundot oQ4e-mtp @ oMLX 0.7.0.dev2 | 13.48 / 15.03 s | 2nd. Same decode (~50 tok/s at 128K), slower TTFT (warm 4.8 s, cold 259 s). No YaRN: ceiling 262K. Needs `qwen4_ple_ssd_offload: true`. |
| Jundot oQ4e-mtp @ oMLX 0.6.4 | 17.1 / 22.7 s | Dominated by 0.7.0.dev2 on the same weights. |
| Youssofal MTPLX Optimized-Speed @ MTPLX 2.11.2 | 10.6 s (1 rep) / refused | Highest decode at 32K (~70 tok/s), but refuses 128K and 256K with HTTP 507 (memory-plan fit 114,688 tokens). With `MTPLX_MEMORY_LIMIT_BYTES=102G` it admits 128K but fails 2 of 5 scenarios. |

## Known issues and cautions

- **Agent quality is unmeasured.** The older conditional promotion stands on quality: run Terminal-Bench before replacing `qwen3-coder-next` in the agent role. The driver for it is ready (`bench/terminal-bench/scripts/run-tbench-flashnext.sh`); the run is on hold because it needs a second machine for the Docker containers.
- **Instruction following (Swift 1.5).** Its card declares −3 on IFBench. The A/B's 20-case IFEval-style probe found one consistent miss (two paragraphs separated by `***`) in both sampling profiles.
- **Swift 1.5 at 256K with unquantized KV: needles 26 of 28 records over two campaigns.** The 2 misses of Task 2 (11/13, all `finish_reason=stop`) did not repeat in Task 13 (15/15). Both arms reach 0.01 GB free memory at 256K. The daily profile serves 262144 since 2026-10-18 with this risk accepted. Sources: [`etapa2-swift-long.md`](../../bench/flashnext-next-steps-2026-10/results/etapa2-swift-long.md), [`etapa13-needles256k.md`](../../bench/flashnext-next-steps-2026-10/results/etapa13-needles256k.md).
- **Long sessions:** no `char_run` degeneration up to ~203K prompt tokens on Swift 1.5 or iQ (3c). iQ had 4 turns that called a tool instead of answering (`finish_reason=tool_calls`, empty content); Swift had none. Source: [`etapa3-agent.md`](../../bench/flashnext-next-steps-2026-10/results/etapa3-agent.md).
- **Switching `reasoning_effort` mid-session drops the prefix cache** (3e): hit 0.00 and TTFT ~167 s at 128K, against 1.3 s with the same effort. The official template writes the effort instruction at the start of the system prompt. Pin the effort per session. Source: [`etapa3-agent.md`](../../bench/flashnext-next-steps-2026-10/results/etapa3-agent.md). A template with the effort instruction at the end of the prompt (`w1t`, [`swift15-effort-tail.jinja`](../../fixes/qwen3.8-flash-next/swift15-effort-tail.jinja)) makes the switch cost 0.8–5.7 s, but it is not the default. On this hybrid model, mlx-serve restores a prefix only at a GDN state checkpoint. The logs suggest that it writes one at the start of the last message, which with `w1t` is the effort block after the user question. Short prompts then lose system-prompt reuse (0/55 against 53/55, +0.9 to +1.4 s on turn 1). The iQ pack with the same template (`n2t`) behaves the same: switch hit 0.97–1.00, reasoning within ×0.95–1.16 of the official template at each effort, accuracy within margin ([`etapa15-iq-effort-tail.md`](../../bench/flashnext-next-steps-2026-10/results/etapa15-iq-effort-tail.md)). Lesson: before you change where a variable text sits in a template, measure prefix reuse on short and long prompts. Diagrams, and five untested ways to keep both the cheap switch and the short-prompt cache (effort block before the last user message, smaller `--ssm-checkpoint-stride`, a template that moves the block by conversation length, a checkpoint at every message boundary, effort outside the prompt): [`etapa11-effort-tail.md`](../../bench/flashnext-next-steps-2026-10/results/etapa11-effort-tail.md). Public page: [`qwen38-flashnext-effort-tail.html`](../../reports/qwen38-flashnext-effort-tail.html).
- **`--ple-gpu` stays off.** With an 8 GB prefix cache, mlx-serve 26.10.1 still keeps the PLE gather on the CPU: weights 68.2 GB + table 29.8 GB + a fixed 16 GB headroom = 114 GB, above the 107.5 GB Metal working set. The headroom does not depend on the prefix cache. Source: [`etapa9-plegpu.md`](../../bench/flashnext-next-steps-2026-10/results/etapa9-plegpu.md).
- **Published LiveCodeBench numbers from earlier campaigns read low.** The submodule grader (`bench2.py` at `a4a95bb`) runs answers without the official LiveCodeBench import prelude and through `python -c`, which fails on large inputs (`E2BIG`). The fix is in the submodule at `2403125`, and the pointer now points there. `scripts/lcb_regrade.py` in the 2026-10 campaign regrades the stored answers: at `xhigh`, the Swift campaign's iQ goes from 41 to 45 and Swift 1.5 from 42 to 47 of 50. No passing answer flipped to failing. Source: [`etapa3-agent.md`](../../bench/flashnext-next-steps-2026-10/results/etapa3-agent.md); every published number, raw and regraded: [`lcb-regrade-published.md`](../../bench/flashnext-next-steps-2026-10/results/lcb-regrade-published.md).
- **The speed probe caps each request at 4096 tokens.** At `xhigh`, some answers of the non-Swift arms hit the cap before answering; they count as "truncated", not as needle failures. The probe now takes an opt-in `--max-tokens` (default 4096 kept for comparability).
- The campaign harness (`bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh`) **wipes `~/.mlx-serve/kv-cache` and kills whatever listens on port 11234**. Stop the daily driver on purpose before running it.
- Reasoning at `xhigh` can exceed 4096 tokens on long mutated prompts; raise `max_tokens` in clients.
- Older numbers in `bench/qwen38-flash-next/references.md` and `bench/qwen38-updates-2026-09/` were measured at `temperature=0`; they read faster than daily use.
