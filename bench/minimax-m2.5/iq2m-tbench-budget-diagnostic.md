# 2026-07-09 — IQ2_M Terminal-Bench: agent-timeout-budget diagnostic

**TL;DR.** MiniMax-M2.5 UD-IQ2_M scores **25.8% (23/89)** on Terminal-Bench 2.0 at our
standard `--agent-timeout-multiplier 0.5`. The vendor reports **51.7%** for MiniMax-M2.5
on Terminal-Bench 2 — and our run logged exactly **46 `AgentTimeoutError`** trials, so
`46/89 = 51.7%` is a tempting "it was just the clock" explanation. We tested that directly
by re-running timeout-failed tasks at full (`1.0×`) and generous (`1.5×`) agent budgets.

**Verdict: the tight budget cost a few real points, but it is NOT the main gap.** Only
**~25–33%** of curated timeout tasks recover even with 2–3× more time. The bulk of the gap
to vendor is **structural** — throughput (2-bit @ ~40 t/s over LAN), tool-call **format
instability**, and genuine capability limits — not a multiplier artifact. Vendor's number
is full-precision on datacenter GPUs, where the same wall-clock buys far more turns.

---

## Why this experiment

- Official IQ2_M: **23/89 = 25.8%** (`0.5×`). Exceptions: 46 `AgentTimeoutError`, 2 `RuntimeError`.
- Vendor MiniMax-M2.5 Terminal-Bench 2: **51.7%**. `46/89 = 51.7%` — suspiciously exact.
- Hypothesis: the `0.5×` cap (halved each task's declared agent budget) starved a slow-but-capable
  model. If timeouts were pure budget-starvation, full budget would recover most of them.

`--agent-timeout-multiplier` scales **each task's own declared budget** (T-Bench tasks declare
15–200 min; most are 15 min). So `0.5×` gave a 15-min task 8 min; `1.0×` gives 15; `1.5×` gives 22.5.

## Method

Fresh `harbor run`s into **separate job dirs** (canonical 25.8% result left untouched), remote
model on the rig (`macstudio.local`), MBP-side Docker, terminus-2, `-n 1`. Two knobs changed vs
canonical, both toward vendor conditions:
1. **agent-timeout-multiplier** `1.0` then `1.5`.
2. **temperature = 1.0** (MiniMax's recommended setting). NOTE: canonical sent *no* temperature
   (terminus-2 leaves it unset → LM Studio server default), so the probes move two variables at
   once; recoveries are a combined "match-vendor" effect, reported as such.

Scripts: [`run-tbench-minimax-iq2m-tmult1-probe.sh`](../terminal-bench/scripts/run-tbench-minimax-iq2m-tmult1-probe.sh),
[`run-tbench-minimax-iq2m-tmult1p5-probe.sh`](../terminal-bench/scripts/run-tbench-minimax-iq2m-tmult1p5-probe.sh),
[`run-tbench-minimax-iq2m-tmult1p5-backfill.sh`](../terminal-bench/scripts/run-tbench-minimax-iq2m-tmult1p5-backfill.sh).

## Results

### 1.0× probe — 12 curated "winnable" timeout tasks (monsters excluded)

| Recovered ✅ (3) | Still failed ❌ (9) |
|---|---|
| `fix-code-vulnerability` | 8 timed out again at full budget: `adaptive-rejection-sampler`, `gpt2-codegolf`, `polyglot-c-py`, `polyglot-rust-c`, `regex-log`, `rstan-to-pystan`, `schemelike-metacircular-eval`, `write-compressor` |
| `mcmc-sampling-stan` | 1 finished-but-wrong (no timeout): `count-dataset-tokens` |
| `multi-source-data-merger` | |

**Recovery: 3/12 = 25%.**

### 1.5× probe — 6 smallest-budget (15-min) tasks that timed out at 1.0×

| Task | 1.0× | 1.5× (22.5 min) |
|---|---|---|
| `adaptive-rejection-sampler` | ❌ timeout | ✅ **PASS** |
| `polyglot-rust-c` | ❌ timeout | ❌ wrong (finished, incorrect) |
| `regex-log` | ❌ timeout (looped) | ❌ wrong (finished, incorrect) |
| `write-compressor` | ❌ timeout | ❌ timeout again |
| `polyglot-c-py` | ❌ timeout | ❌ timeout (parser instability) |
| `gpt2-codegolf` | ❌ timeout | ❌ wrong (finished, incorrect) |

**Recovery: 1/6 = 17%.** (`polyglot-rust-c` + `regex-log` were re-run in the
[backfill](#docker-freeze-incident) after a mid-probe Docker freeze; both came back clean-wrong.)

### Aggregate

- **Escalated recovery** (12 unique curated timeout tasks, budget pushed to 1.5×): **4/12 ≈ 33%**.
- **Verified-recoverable score**: 23 original passes + **4 confirmed recoveries**
  (`fix-code-vulnerability`, `mcmc-sampling-stan`, `multi-source-data-merger` @1.0×;
  `adaptive-rejection-sampler` @1.5×) = **27/89 = 30.3%**. ⚠️ Budget-boosted — **not** comparable
  to the other local models, which are all at `0.5×`.
- **Projected full-run at generous budget**: 33% is an *optimistic ceiling* (the probe cherry-picked
  winnable tasks; the excluded ~34 include monster >60-min builds and 0–1/8-historical tasks). Realistic
  full-set landing ≈ **mid-to-high 30s**, still well short of vendor **51.7%**.

## Failure taxonomy (the real finding)

More budget mostly lets the model **finish and be wrong**, not get it right. Four distinct modes:

1. **Throughput wall** — too slow (2-bit, ~40 t/s, over LAN) to finish long tasks within budget;
   times out even at 1.0×/1.5×. E.g. `write-compressor` (timed out 3×), `rstan-to-pystan`,
   `schemelike-metacircular-eval`, `polyglot-c-py`.
2. **Behavioral looping** — fixates on one sub-problem and never steps back. `regex-log` @1.0×:
   **49 turns, 675k prompt tokens** re-tweaking the IPv4 octet regex while the *date* test (the one
   graded) stayed broken. Context bloat + ~40 t/s = each turn crawls. temp=1.0 likely worsens spirals.
3. **Tool-call / JSON format instability** — terminus-2 needs a clean JSON tool-call; the 2-bit model
   frequently emits malformed output. `polyglot-c-py` @1.5×: **~42 of ~48 turns** logged
   `Parser warnings: No valid JSON object found / Extra text after JSON object` — budget burned on
   *unparseable* actions, not progress.
4. **Capability misses** — finishes within budget, wrong answer. `count-dataset-tokens`, `gpt2-codegolf`,
   and (at 1.5×) `polyglot-rust-c` / `regex-log`. Not a time problem at all. `polyglot-rust-c`'s attempt
   used `exec(open(__file__).read())` — a self-referencing infinite loop that isn't a valid polyglot.

## Docker-freeze incident

Mid-1.5×-probe, Docker Desktop's LinuxKit VM froze and had to be force-killed (same failure family as
the canonical run's 16-trial wedge). It produced two **infra-noise** verdicts — `polyglot-rust-c`
(`RuntimeError` on container teardown) and `regex-log` (`EnvironmentStartTimeoutError`, env never started).
Neither is a model verdict. Both were **backfilled** on healthy Docker
([backfill script](../terminal-bench/scripts/run-tbench-minimax-iq2m-tmult1p5-backfill.sh)); the table
above reflects the clean re-runs. Carry-forward guardrail: the backfill script preflights `docker info`
and the drivers pre-prune; for long detached runs, watch for the 30-min-cadence timeout signature.

## What this means for the MiniMax-vs-Qwen decision

Unchanged from the [strategic read](plan.md): on this hardware MiniMax IQ2_M is **throughput-limited**
on the agentic loop and clusters *near*, not above, the top local agents.

- **Fair (apples-to-apples 0.5×): 25.8% — 4th/5th**, below all three Qwens (coder-next 32.6, 27b 31.5,
  a3b35 28.1). This stays the official number.
- **Budget-boosted 30.3% / projected mid-30s**: would only rank higher because MiniMax alone got extra
  budget; the Qwens have their own timeout-fails that would also recover at full budget.
- MiniMax still **wins decisively on raw code** (LCB 76 vs Qwens 54–62). It is a **code specialist**,
  not an agentic-loop leader.

### Recommended combination / use cases

- **Role: co-resident code oracle**, not the loop driver. Best local raw code (LCB 76, HumanEval 94),
  strong tool-calling (jd 92.5 / veer 83.3), but slow + no vision.
- **Pattern A (flagship):** `qwen3-coder-next` drives the agentic/terminal loop (fast, T-Bench 32.6,
  tiny) **+ MiniMax IQ2_M** called for hard code subtasks — **both co-resident**. IQ2_M's 78 GB (vs
  Q3_K_S 98.69 GB) leaves ~40–50 GB headroom on the 128 GB rig, so no swap latency. This is the concrete
  reason to prefer IQ2_M.
- **Pattern B:** a thin fast front-end (gemma-e4b / coder-next) with MiniMax as a call-when-needed
  backend for code/reasoning-heavy requests.
- **Do NOT** use MiniMax as the terminal-agent driver (coder-next wins on quality *and* speed), pair two
  heavyweights (MiniMax + 27b dense — memory/latency blowup), use it for latency-sensitive chat, or reach
  for it for vision (Gemma's lane).

## Reproduce

Rig must serve `minimax-m2.5@iq2_m` loaded (run **before** the q3_k_xl speed probe, which unloads it).
```
( nohup bash bench/terminal-bench/scripts/run-tbench-minimax-iq2m-tmult1-probe.sh    >/dev/null 2>&1 & disown )
( nohup bash bench/terminal-bench/scripts/run-tbench-minimax-iq2m-tmult1p5-probe.sh  >/dev/null 2>&1 & disown )
( nohup bash bench/terminal-bench/scripts/run-tbench-minimax-iq2m-tmult1p5-backfill.sh >/dev/null 2>&1 & disown )
```
Raw results: `bench/terminal-bench/logs/tbench-runs/minimax-m2.5-iq2m-tmult1{,p5{,-backfill}}-probe/result.json`
(git-ignored per the results boundary).
