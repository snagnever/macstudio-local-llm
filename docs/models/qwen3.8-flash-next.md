# Qwen3.8-Flash-Next (125B-A6B MoE)

> **Status: 🟢 DAILY DRIVER — responsiveness default.** The most responsive daily setup on this rig:
> `ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit` on **mlx-serve 26.9.2**.
> T_turno (time for one tool turn with a 512-token reply) **11.03 s at 32K** and **12.35 s at 128K**, 18% ahead of
> the next stack. Agent quality (Terminal-Bench) is **not measured** for this model yet.
> Last updated: 2026-09-13

Campaign that selected this config: [`bench/qwen38-flashnext-daily-driver-2026-09/results/summary.md`](../../bench/qwen38-flashnext-daily-driver-2026-09/results/summary.md).
Model research, builds and older measurements: [`bench/qwen38-flash-next/references.md`](../../bench/qwen38-flash-next/references.md).
Dashboard: [`reports/qwen38-flashnext-driver.html`](../../reports/qwen38-flashnext-driver.html).

## Daily driver configuration

| Item | Value |
|---|---|
| Runtime | mlx-serve **26.9.2** (MLX 0.32.2) — `~/.local/opt/qwen38/mlx-serve-v26.9.2/mlx-serve` (also `~/.local/bin/mlx-serve`) |
| Weights | [`ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit`](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit) rev [`ef5b919`](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit/tree/ef5b919d31534faa1997666f1a22d362cd6383cd) |
| Local path | `~/.cache/local-llms/qwen3.8-prefix-cache/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd` |
| Quant | mixed 4/8-bit: experts 4-bit, non-expert weights 8-bit; n-gram table 4-bit, memory-mapped from SSD |
| Endpoint | `http://<rig>:11234/v1` (OpenAI-compatible); `/metrics` (Prometheus) |
| API model id | the weights directory name above (read it from `/v1/models`) |
| Launcher | [`tools/scripts/serve-flashnext-daily-driver.sh`](../../tools/scripts/serve-flashnext-daily-driver.sh) |

### Launch command (daily profile, 131K context)

```bash
~/.local/opt/qwen38/mlx-serve-v26.9.2/mlx-serve \
  --model ~/.cache/local-llms/qwen3.8-prefix-cache/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd \
  --serve --host 0.0.0.0 --port 11234 \
  --ctx-size 131072 \
  --mtp \
  --ssm-checkpoint-max 16 \
  --prefix-cache-mem 16GB --prefix-cache-disk 100GB --prefix-cache-entries 64 \
  --metrics
```

This is byte-for-byte the command the campaign measured (candidate c1).

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
- One model at a time. The MoE does not batch decode: parallel requests queue on one slot.
- Keep ≥ 100 GB free on the boot volume for the prefix-cache disk tier.

## Measured performance (2026-09-13, M4 Max 128 GB, temp 1.0)

T_turno = TTFT of the `tool_turn` scenario + 512 / median warm decode (identical, append, tool_turn). Median of 3 repetitions at 32K and 128K; 1 repetition at 256K.

| Context | T_turno | Cold TTFT (first turn) | Warm TTFT identical / append / tool_turn | Cache hit append / tool_turn | Warm decode | Wired peak | Swap |
|---|---:|---:|---|---|---:|---:|---:|
| 32K | **11.03 s** | 37.0 s | 0.1 / 1.9 / 1.9 s | 0.96 / 0.96 | 55.9 tok/s | 97.3 GB | 0 |
| 128K | **12.35 s** | 178.1 s | 0.2 / 2.0 / 2.1 s | 0.99 / 0.99 | 49.7 tok/s | 108.1 GB | 0 |
| 256K | 14.2 s | 378.6 s | 0.6 / — / 2.6 s | — / 1.00 | 44.2 tok/s | 108.5 GB | 0 |

Prefill is ~700–735 tok/s from 32K to 256K. Needles at 10/50/90% were correct in every served request (a few truncated at 4096 tokens of reasoning).

### Extended profile: 512K

Serves 524288 tokens with a follow-up, without `sudo`: cold TTFT 844.6 s, decode 42.6 tok/s, follow-up 0.6 s with full cache hit, wired 104.3 GB. **Memory is at the edge** (minimum free 0.01 GB): close heavy apps first. Capacity, not daily use.

```bash
tools/scripts/serve-flashnext-daily-driver.sh 512k
```

It adds `--ctx-size 524288 --kv-quant 8 --kv-attn-mode fused` and a YaRN override
(`rope_type yarn`, `factor 2.0`, `original_max_position_embeddings 262144`). 1M is out of scope: cold-only one-shot with 8-bit KV, or ~5 tok/s multi-turn with `turbo4`.

## Stacks compared (why this one)

| Stack | T_turno 32K / 128K | Verdict |
|---|---|---|
| **ddalcu mixed-4/8 @ mlx-serve 26.9.2** | **11.03 / 12.35 s** | Default. Fastest first turn and warm turn at every context. |
| Jundot oQ4e-mtp @ oMLX 0.7.0.dev2 | 13.48 / 15.03 s | 2nd. Same decode (~50 tok/s at 128K), slower TTFT (warm 4.8 s, cold 259 s). No YaRN: ceiling 262K. Needs `qwen4_ple_ssd_offload: true`. |
| Jundot oQ4e-mtp @ oMLX 0.6.4 | 17.1 / 22.7 s | Dominated by 0.7.0.dev2 on the same weights. |
| Youssofal MTPLX Optimized-Speed @ MTPLX 2.11.2 | 10.6 s (1 rep) / refused | Highest decode at 32K (~70 tok/s), but refuses 128K and 256K with HTTP 507 (memory-plan fit 114,688 tokens). With `MTPLX_MEMORY_LIMIT_BYTES=102G` it admits 128K but fails 2 of 5 scenarios. |

## Known issues and cautions

- **Agent quality is unmeasured.** The older conditional promotion stands on quality: run Terminal-Bench before replacing `qwen3-coder-next` in the agent role.
- The campaign harness (`bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh`) **wipes `~/.mlx-serve/kv-cache` and kills whatever listens on port 11234**. Stop the daily driver on purpose before running it.
- Reasoning at `xhigh` can exceed 4096 tokens on long mutated prompts; raise `max_tokens` in clients.
- Older numbers in `bench/qwen38-flash-next/references.md` and `bench/qwen38-updates-2026-09/` were measured at `temperature=0`; they read faster than daily use.
