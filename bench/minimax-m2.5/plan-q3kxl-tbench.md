# 2026-07-08 — MiniMax-M2.5 UD-Q3_K_XL — speed probe + remote Terminal-Bench

## Context

Next candidate from the [quant roadmap](../../docs/models/minimax-m2.5.md#quant-roadmap-ranked-2026-07-06),
rank #1: **UD-Q3_K_XL** (101.3 GB), served on the rig as `minimax-m2.5@q3_k_xl`.
The question it answers: **how much quality is the static `Q3_K_S` (T-Bench 25.8%)
costing us?** Unsloth claims their dynamic UD quants "perform much better than their
non-Unsloth counterparts" (~10 pts per third-party data). This run gets the
apples-to-apples Terminal-Bench delta on the same rig, same harness, same protocol.

Runs right after the in-flight **UD-IQ2_M** remote T-Bench completes, on the same
two-machine setup:
- **Rig** (`macstudio.local`, M4 Max 128 GB) — serves the quant via LM Studio; runs the speed probe.
- **MBP** (`VitorMBPro2026.local`, M5 Pro 24 GB, this checkout) — Docker host; runs terminus-2 + Harbor over LAN.

## The hard constraint: ctx 32k, not 60k

UD-Q3_K_XL is **101.3 GB** — with ~23 GB inference overhead it peaks ~124 GB at
ctx 32k, and **does NOT fit at 60k** on 128 GB. So both the speed probe and
T-Bench run at **`--context-length 32768`**, unlike IQ2_M's 60k. This is a real
asymmetry in the comparison: q3_k_xl's agent trajectories are capped at half the
context IQ2_M had. Long-trajectory tasks that need >32k may truncate — record any
such fail as a memory-imposed floor, not a model limit (same note the IQ2_M @32k
LCB run carried).

## Two-machine split (and what can/can't be automated)

There is **no SSH from the MBP to the rig** (publickey/password denied). Therefore:

- **Speed probe → rig-side, manual.** It does `lms unload/load` + `speed_probe.py`
  locally on the rig; it cannot be driven from the MBP. Run
  [`scripts/run-minimax-q3kxl-speedprobe.sh`](scripts/run-minimax-q3kxl-speedprobe.sh)
  **on the rig** once the IQ2_M run has freed it. It loads q3_k_xl at ctx 32768,
  parallel 1, and **leaves the model resident** for T-Bench to reuse.
- **T-Bench → MBP-side, automated.** The arming trigger
  ([`scripts/arm-q3kxl-tbench-handoff.sh`](scripts/arm-q3kxl-tbench-handoff.sh),
  launched detached on the MBP) waits for **both** signals, then fires the remote
  driver — so it self-synchronises with whenever the rig speed probe runs:
  1. the current IQ2_M job is complete (all 89 trials resolved), and
  2. the rig's `/api/v0/models` shows `minimax-m2.5@q3_k_xl` **loaded**.

## Steps

1. **[rig, manual]** After IQ2_M T-Bench finishes, on the rig run
   `bash bench/minimax-m2.5/scripts/run-minimax-q3kxl-speedprobe.sh`. Expect
   weights ~101 GB, peak ~124 GB at 32k, `Spill=YES`; note tok/s (Q3_K_S decoded
   ~28 t/s — q3_k_xl should be similar). Leaves the model resident at 32k.
2. **[MBP, automated]** The arming trigger detects both conditions and launches
   `run-tbench-minimax-q3kxl-REMOTE.sh` under `caffeinate`, detached (PID 1 so the
   harness can't reap it — the failure mode that killed the IQ2_M run twice). Full
   89, terminus-2, `--agent-timeout-multiplier 0.5`, `-n 1` — identical protocol to
   the Q3_K_S (25.8%) and IQ2_M runs so the delta is clean.
3. **[MBP]** Results land in `bench/terminal-bench/logs/tbench-runs/minimax-m2.5-q3kxl-remote/`.
   On a silent kill, `harbor job resume -p <that dir> -y` continues (lost nothing on
   the IQ2_M run — 63/89 survived two kills). Score = `stats.evals[*].reward_stats`.

## Verification

1. `curl -s http://macstudio.local:1234/api/v0/models | grep q3_k_xl` → `state: loaded`, ctx ~32768.
2. Speed probe prints coherent output for all 3 prompts + a tok/s figure; no metal::malloc.
3. First T-Bench trial reaches container-up + a trajectory dump (agent↔rig loop live).
4. Final `stats.n_completed + n_errored == 89`; score recorded.

## Expected outcome & how to read it

A defensible T-Bench number for UD-Q3_K_XL to slot into the rig table beside
Q3_K_S (25.8%) and IQ2_M (~28% in progress). The roadmap's thesis: UD-Q3_K_XL
should **beat static Q3_K_S** and possibly IQ2_M. Caveats that push the number
around vs IQ2_M: q3_k_xl runs at **32k not 60k** (↓, truncation risk) but is a
**higher-bit quant** (↑, quality). If it lands at/above the Qwen leaders (~32%),
that closes the "quant discount" question the Q3_K_S caveat raised.

## Critical files / paths

- Rig speed probe: [`scripts/run-minimax-q3kxl-speedprobe.sh`](scripts/run-minimax-q3kxl-speedprobe.sh)
- MBP remote driver: [`../terminal-bench/scripts/run-tbench-minimax-q3kxl-REMOTE.sh`](../terminal-bench/scripts/run-tbench-minimax-q3kxl-REMOTE.sh)
- MBP arming trigger: [`scripts/arm-q3kxl-tbench-handoff.sh`](scripts/arm-q3kxl-tbench-handoff.sh)
- Precedent: [`plan.md`](plan.md) (IQ2_M + Q3_K_S), the IQ2_M REMOTE + speed-probe scripts.
- Scoreboard to update: `../../docs/models/minimax-m2.5.md`, `tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`.
