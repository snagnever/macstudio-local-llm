# 2026-07-09 — IQ2_M Terminal-Bench: retry the 16 Docker env-start failures

## ✅ OUTCOME (2026-07-09) — retry complete, score corrected 21.3% → 25.8%

Clean-Docker resume (`harbor job resume -f EnvironmentStartTimeoutError`) recovered
all 16 wedged trials with **zero** `EnvironmentStartTimeoutError` on the re-run —
the force-quit-Docker + prune fix held. Final IQ2_M standing:

- **Official: 23/89 = 25.8%** (was 19/89 = 21.3% before the retry — the +4 came from
  recovered passes `code-from-image`, `large-scale-text-editing`,
  `modernize-scientific-stack`, `portfolio-optimization`).
- Graded (excl. 3 infra errors): 23/86 = 26.7%. Remaining losses: AgentTimeoutError=46,
  RuntimeError=2 — genuine model timeouts, **not** infrastructure.
- The two slow deciders `qemu-startup` and `configure-git-webserver` both came back
  not-passed (agent timeout), so the number held at 23 rather than climbing to 24.
- **Result: IQ2_M (78 GB) ties Q3_K_S (98.69 GB) at 25.8% exactly** → the 2-bit quant
  costs nothing measurable on T-Bench. Reports updated (`reports/benchmark-charts.html`,
  `reports/quality-benchmarks-charts.html`, `reports/README.md`).

## What happened (root-caused, not sleep)

The IQ2_M remote run finished 89/89 but **16 trials failed with
`EnvironmentStartTimeoutError`** — the Docker environment never started, so the
model never attempted them. They count as fails in the official score, dragging
it to **19/89 = 21.3%** vs a "model actually ran" view of ~27%. At least three
are near-certain passes the model was denied (`modernize-scientific-stack` 7/8
historical, `portfolio-optimization` 6/8, `configure-git-webserver` 5/8 — all
Q3_K_S passes), so the raw number is unfairly low.

**Ruled out: MacBook sleep.** `pmset -g log` shows the `caffeinate` assertion
held `PreventSystemSleep` + `PreventUserIdleSystemSleep` continuously on AC
through the whole failure window (00:18–07:48); the first `Sleep` transition is
07:48:54, *after* the run ended. Zero sleep/darkwake events in between.

**Actual cause: Docker's LinuxKit VM wedged at ~00:18.** The 16 failures are
exactly 30 min apart (= the 1800 s env-start timeout) and unbroken from 00:18 to
the end — i.e. once wedged, *every* subsequent container-start timed out. Likely
trigger: VM state/resource exhaustion after ~64 heavy amd64 image build/teardown
cycles (Docker had accumulated **75 images / 96 GB, 93 GB reclaimable**).

## The 16 to retry

`adaptive-rejection-sampler, code-from-image, configure-git-webserver,
financial-document-processor, fix-code-vulnerability, gpt2-codegolf,
large-scale-text-editing, llm-inference-batching-scheduler, make-doom-for-mips,
mcmc-sampling-stan, modernize-scientific-stack, mteb-retrieve, path-tracing-reverse,
portfolio-optimization, qemu-startup, sqlite-db-truncate`

Likely passes (worth the retry): `modernize-scientific-stack`,
`portfolio-optimization`, `configure-git-webserver`, `fix-code-vulnerability`,
`mcmc-sampling-stan`, `code-from-image`. The rest are 0–1/8 historical — retried
for completeness, but expected to fail on the model even if the env starts.

## Preconditions

- Rig still serving `minimax-m2.5@iq2_m` (loaded) — **run this retry BEFORE the
  q3_k_xl speed probe**, since it reuses the same loaded model. The armed
  q3_k_xl trigger is unaffected (it waits for q3_k_xl to load, which won't happen
  until the rig speed probe).
- Docker Desktop healthy (verified: starts amd64 containers, 19.5 GB).

## Plan — [`scripts/retry-tbench-minimax-iq2m-envfail.sh`](../terminal-bench/scripts/retry-tbench-minimax-iq2m-envfail.sh)

Attack the root cause (VM wedge) first, then resume only the failed trials, with
auto-recovery if it re-wedges:

1. **Clean the slate** — `docker system prune -af` to reclaim the 93 GB of stale
   images/build cache that pressures the VM. (Task images re-pull on demand.)
2. **Restart Docker Desktop** — `osascript quit` → `open -a Docker` → wait for
   `docker info` healthy. Clears any lingering VM state.
3. **Resume, filtered** — `harbor job resume -p <job_dir> -f
   EnvironmentStartTimeoutError -y`. The `-f` drops the 16 env-timeout results so
   they re-run as fresh trials; the 19 passes + 51 real fails are untouched.
4. **Watchdog / auto-recover** — wrap steps 2–3 in a loop: after each resume,
   re-read `stats.exception_stats`; if `EnvironmentStartTimeoutError` trials
   remain, the VM re-wedged → prune + restart Docker + resume again. Cap at
   **3 rounds**, then stop and report whatever's left.
5. **Detached + caffeinate** — launch `( nohup caffeinate -i -s bash … & )`
   (PID 1), same pattern that survived the reaper for the main run.

## Verification

1. First retried trial reaches container-up + trajectory dump (env starts).
2. On completion, `stats.exception_stats.EnvironmentStartTimeoutError` is empty
   (or only genuinely-heavy images remain, logged).
3. Recompute score: `n1 = len(reward_stats.reward["1.0"])`; new official = `n1/89`.
   Expect ~22–26% depending on how many of the 6 likely-passes land.

## Guard rails for future runs (carry into q3_k_xl)

- **Pre-prune** Docker before a run; don't let images pile to 90+ GB.
- **Between-trial cleanup** is already in the drivers (`docker rm -f` orphans);
  consider a periodic `docker image prune` mid-run for 89-trial runs.
- **Watch for the 30-min-cadence signature** — ≥2 consecutive env-start timeouts
  = VM wedge; the watchdog restarts Docker rather than letting the run bleed out.
