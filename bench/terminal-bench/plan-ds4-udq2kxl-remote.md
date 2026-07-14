# 2026-07-14 — DeepSeek-V4-Flash UD-Q2_K_XL on Terminal-Bench 2.0 (remote Docker host)

> **Runbook.** Two machines, two scripts. The model rig (macstudio) serves the model;
> a second Apple-Silicon Mac runs Docker + harbor/terminus-2. This is Task 6 of the
> [UD-Q2_K_XL campaign](../deepseek-v4-flash/plan-udq2kxl.md) — the tiebreaker the
> single-shot benches can't settle (see [campaign log](../deepseek-v4-flash/results/udq2kxl-campaign-log.md)).

**Goal:** Get the first Terminal-Bench 2.0 number for DeepSeek-V4-Flash (any quant) on
this rig, to decide whether a 284B MoE's multi-step planning justifies its 97 GB / 10 t/s
footprint against the small dense models that already beat it on speed and LCB.

**Why remote:** the model is ~95 GB resident and the Terminal-Bench task containers are
amd64 (Rosetta/qemu, RAM-hungry). On one machine they fight for memory — the exact NO-GO
that sank the local MiniMax run. Splitting model (rig) from Docker (second Mac) fixes it.
Same split the `run-tbench-minimax-REMOTE.sh` campaign used.

## The two machines

| Role | Machine | Runs | Script |
|---|---|---|---|
| **Model rig** | macstudio (128 GB) | standalone `llama-server` bound to `0.0.0.0:1235` | [`serve-udq2kxl-lan.sh`](../deepseek-v4-flash/scripts/serve-udq2kxl-lan.sh) |
| **Docker host** | second Apple-Silicon Mac | Docker Desktop + `harbor` + terminus-2 | [`run-tbench-ds4-udq2kxl-REMOTE.sh`](scripts/run-tbench-ds4-udq2kxl-REMOTE.sh) |

**Key gotcha — not on :1234.** Every other model on this rig is served by LM Studio on
`:1234`. UD-Q2_K_XL is **not**: the `deepseek4` arch aborts in LM Studio's CPU repack path,
so it only loads under `llama-server --no-repack` on `:1235`. The serve script and the
runner both target `:1235`, not `:1234`. Don't "fix" them to point at LM Studio.

## Step 1 — On the rig (macstudio): serve the model to the LAN

The campaign's local GO recipe binds `127.0.0.1` (localhost only). `serve-udq2kxl-lan.sh`
is the identical recipe with `--host 0.0.0.0` so the LAN can reach it.

```bash
# on macstudio, from the repo root:
bash bench/deepseek-v4-flash/scripts/serve-udq2kxl-lan.sh
```

- Leave it running in a terminal for the whole tbench run (it's `exec`, foreground).
- **Evict everything else first** — sole-model, 92–98 GB resident. No LM Studio model
  loaded, no `mlx_lm.server` (the script refuses to start if it sees one).
- **First run pops a macOS firewall prompt** ("allow incoming network connections") —
  click **Allow**, or the remote Mac can't reach `:1235`.
- Cold load is ~5 min (warm, seconds). Warm-up: `curl -s localhost:1235/v1/models`.

## Step 2 — On the Docker host: prerequisites (one-time)

1. **Docker Desktop** installed + running. Settings → Resources → give it as much RAM as
   you can spare (task images are emulated amd64). `docker info` must succeed.
2. **harbor**: `uv tool install harbor-cli` (rig used 0.8.0).
3. **This repo checked out** on this Mac. Edit `REPO=` at the top of the runner to this
   Mac's checkout path (default assumes `~/LocalProjects/macstudio-local-llm`).
4. **Same LAN** as the rig.

## Step 3 — On the Docker host: confirm reachability, then run

```bash
# MUST list the model id before you run — this is the #1 failure point:
curl -s http://macstudio.local:1235/v1/models | grep deepseek-v4-flash-udq2kxl

# then launch (the script re-checks reachability + Docker, cleans orphan containers, runs 89 tasks):
bash bench/terminal-bench/scripts/run-tbench-ds4-udq2kxl-REMOTE.sh
```

If reachability fails: the rig isn't bound to `0.0.0.0` (re-run Step 1), the firewall
prompt was dismissed (allow it), or `macstudio.local` doesn't resolve — fall back to the
rig's LAN IP (`ipconfig getifaddr en0` on the rig) and edit `RIG=` in the runner.

## Config (matches the campaign + the MiniMax remote precedent)

- `--agent terminus-2`, `--dataset terminal-bench/terminal-bench-2` (89 tasks).
- `--agent-timeout-multiplier 0.5` — local models are slow (~10 t/s); the 0.5 cap keeps
  wall-clock bounded, same as every prior local-model tbench on this rig.
- `--environment-build-timeout-multiplier 3.0` — amd64 image builds under emulation are slow.
- `-n 1` concurrent by default. Bump only if Docker has RAM to spare (~16–24 GB/trial):
  32 GB free → 1, 64 GB → 2, 96 GB+ → 3–4. The model rig serves `-np 1` (single slot), so
  **concurrent trials serialize at the model** — raising `-n` past 1 mostly helps hide
  container build/setup latency, not model latency.
- `--model "openai/deepseek-v4-flash-udq2kxl"` — LiteLLM's `openai/` provider sends the bare
  alias as the model name; `llama-server` validates it against its `-a` alias (unlike
  `mlx_lm.server`, which needed the full model path).

## Known risk to watch — the KV-cascade 500s

Task 5 (LCB) surfaced this: when a generation spirals and fills the `-np 1` slot's 32k KV
cache, that sequence isn't evicted before the next request, so the next prefill 500s with
"Context size has been exceeded" (`off=0`). In Terminal-Bench this could manifest as an
agent step suddenly erroring mid-task after a long/looping model turn. terminus-2 will
likely record it as a failed step. If you see a cluster of tasks failing right after a
long agent turn, that's this — not (only) the model reasoning poorly. It's a known runtime
issue, documented in the [campaign log](../deepseek-v4-flash/results/udq2kxl-campaign-log.md#task-5--livecodebench-v6-50-2026-07-13);
note it in the results rather than chasing it mid-run.

## When it finishes — bring results back to the campaign

1. Run log + per-task results land in `bench/terminal-bench/logs/tbench-runs/ds4-udq2kxl-remote/`
   on the **Docker host** (that path is gitignored — it's raw logs).
2. Harbor prints the resolved/unresolved count in the run-log tail. Compute % of 89.
3. Copy the aggregate + a short note back to the model rig and append to the
   [campaign log](../deepseek-v4-flash/results/udq2kxl-campaign-log.md) (Task 6 section),
   comparing against the cross-model tbench slots (MiniMax-M2.5 25.8%, Qwen3.5-122B 24.7%).
4. That closes the campaign's last open input → Task 8 synthesis / verdict.
