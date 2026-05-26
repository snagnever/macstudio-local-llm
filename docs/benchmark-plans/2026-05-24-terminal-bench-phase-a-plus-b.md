# 2026-05-24 — Terminal-Bench 2.0 backfill (Phase A tie-breaker + Phase B expansion)

## Context

Terminal-Bench 2.0 (T-Bench) is the rig's missing column. The cross-frontier
chart in [`reports/quality-benchmarks-charts.html`](../../reports/quality-benchmarks-charts.html)
(`chartTBench`, lines 446-457) currently shows two **vendor-claimed** Qwen
numbers next to measured frontier values — every other quality chart on
the page has real local measurements.

T-Bench is the only published bench that scores **agentic shell behavior**
(multi-turn agent loop in a Linux container) rather than single-shot
generation or tool-schema correctness. It's the bench that breaks the
remaining open question from the post-Phase-2 analysis:

> `qwen/qwen3-coder-next` vs `gemma-4-26b-a4b@6bit` for the OpenCode
> agentic-default slot — both score ~92% on combined tool-calling, but
> LCB and static benches disagree about coding quality.

Phase A measures both contenders directly. Phase B expands to the rest of
the Phase 1 + Phase 2 candidates only if Phase A's smoke signal is real.

**Outcome:** populate the chartTBench data block with 7 measured local rows,
update the agentic-default recommendation in [`docs/local-llm-reference.md`](../local-llm-reference.md),
add the T-Bench column to [`docs/testing-plan.md`](../testing-plan.md), and
resolve the open "coding-best vs knowledge-best diverge" tension with a
workload-level signal.

## Models in scope (phased)

| Phase | # | Model ID (API) | Role on the bench |
|---|---|---|---|
| A | 1 | `qwen/qwen3-coder-next` | Default agentic coder — measure the vendor-claimed 36.2 |
| A | 2 | `gemma-4-26b-a4b-it-mlx@6bit` | LCB ceiling 80%; multi-turn behavior unknown |
| B | 3 | `gemma-4-e4b-it-mlx` | Fastest decode; also doubles as Phase 0 smoke target |
| B | 4 | `gemma-4-26b-a4b-it-mlx@4bit` | Quant A/B against #2 |
| B | 5 | `qwen3.6-35b-a3b@6bit` | MoE thinking; F1 thinking-format guard (see §Failure modes) |
| B | 6 | `gemma-4-31b-it-mlx` | Phase 2 demote candidate; abort early if rank holds |
| B | 7 | `qwen3.6-27b` | Knowledge king, dense thinking — longest leg, run last |

**Skipped:** `deepseek-v4-flash-dq` (96 GB, separate Phase 3 fit-test track).

## Step 0 — One-time setup (dependency-ordered, ~1-2 h)

Docker is not currently installed on this rig. Each step has a verification
gate. Do not proceed past a failing gate.

### 0.1 Install Docker Desktop for Apple Silicon

```bash
brew install --cask docker
open -a Docker
```

In Docker Desktop Settings → Resources:
- **CPUs:** 12 of 16 (leave 4 for LM Studio worker)
- **Memory:** 24 GB (T-Bench tasks aren't individually heavy; containers stack)
- **Disk image:** 100 GB (mitigates F2 — Docker disk exhaustion at task N+)
- **Virtualization framework:** Apple Virtualization + **Rosetta enabled**
  (T-Bench tasks run linux/amd64; without Rosetta the QEMU path is ~5× slower)

**Gate 0.1:**
```bash
docker version  # client + server both present
docker run --rm --platform linux/amd64 alpine:3.20 uname -a
```

### 0.2 Install `uv` and Harbor

```bash
brew install uv                     # if not present
uv tool install harbor              # the T-Bench 2.0 runner
which harbor && harbor --version
```

If `harbor` not on PATH after install: `uv tool update-shell && exec $SHELL -l`.

**Gate 0.2:** `harbor --help` returns; the bench list (subcommand TBD in
§0.3) shows `terminal-bench-2`.

### 0.3 Discover Harbor's CLI shape (10-min exploration, MUST DO before §1)

Several flags aren't confirmed in public docs. Run `harbor --help` and
`harbor run --help` and document the **actual** answers for these. Replace
the placeholders in §1 / §2 commands with the verified flags:

| Question | Why it matters | Likely flag candidates |
|---|---|---|
| Subset / N-task selector | §1 smoke test must run only 5 tasks, not 89 | `--subset`, `--tasks`, `--limit`, `--include` |
| Output dir flag | Pin Harbor's run artifacts to `.bench-logs/tbench-runs/<model>/` | `--output`, `-o`, `--results-dir` |
| Concurrency flag | **Set to 1** — non-negotiable per single-resident-model rule | `--concurrency`, `-p`, `--parallel` |
| Resume / retry flag | Recovery after mid-run failure | `--resume`, `--retry-failed`, `--continue` |
| Output schema (file + JSON shape) | Drives §3 adapter | Read `<output>/results.json` (or equivalent) after a 1-task run |

**Gate 0.3:** Document the discovered flags in a `HARBOR_CLI.md` cheatsheet
under `tools/local-llm-bench-m4-32gb/scripts/`, or as a comment block at
the top of the driver scripts, before any phase begins.

### 0.4 Wire LM Studio endpoint into Harbor (via LiteLLM)

Harbor uses LiteLLM for provider abstraction. Address LM Studio as an
OpenAI-compat backend with the `openai/` model prefix:

```bash
export OPENAI_API_BASE="http://127.0.0.1:1234/v1"
export OPENAI_API_KEY="lm-studio"       # dummy; LM Studio doesn't validate
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```

**Gate 0.4:** Direct probe succeeds:
```bash
curl -s http://127.0.0.1:1234/v1/models | python3 -c "import sys,json;print([m['id'] for m in json.load(sys.stdin)['data']])"
```

## Step 1 — Smoke test (Phase 0, ~30-45 min)

Goal: prove the full chain (LM Studio ↔ LiteLLM ↔ Harbor ↔ Docker ↔ task
container) end-to-end before sinking ~21 h on Phase A.

Load `gemma-4-e4b-it-mlx` in LM Studio (fastest model). Run 5 tasks:

```bash
cd $REPO
mkdir -p .bench-logs/tbench-runs/smoke

# Substitute verified flags from §0.3
harbor run terminal-bench-2 \
  --model "openai/gemma-4-e4b-it-mlx" \
  --tasks 5 \
  --concurrency 1 \
  --output .bench-logs/tbench-runs/smoke \
  2>&1 | tee .bench-logs/tbench-smoke-e4b.log
```

**Success criteria (all four must hold to advance):**

1. Run completes without exception (exit 0).
2. **≥ 1 of 5 tasks passes.** Proves the agent loop executes commands.
   0/5 = chain is broken (likely tool-format incompatibility).
3. Per-task wall-clock < 8 min on e4b. > 15 min = Docker emulation or
   model context fight; budget reset required.
4. `docker system df` shows measurable disk growth (cleanup works).
5. Output JSON/log file is parseable. **During this step, document the
   exact output schema** for §3 adapter.

## Step 2 — Phase A run plan (~21 h total)

**Gate: §1 passes.** Otherwise stop and diagnose.

Run order: `qwen/qwen3-coder-next` first (faster, earlier signal), then
`gemma-4-26b-a4b-it-mlx@6bit` (overnight). Single resident model — JIT swap
in LM Studio between models, never co-load.

**Pre-flight each model:**
```bash
cd $REPO/tools/local-llm-bench-m4-32gb
python3 scripts/lms.py check        # context 65536, no other large MLX resident
docker system df                    # > 20 GB free in Docker disk
docker system prune -f              # cleanup between models (NOT -a)
```

**Driver script per model** (mandatory — the 2h silent-kill bug
demonstrated in Phase 1 LCB affects any `Bash run_in_background` long run).
Template: copy [`.bench-logs/run-27b-lcb-remaining.sh`](../../.bench-logs/run-27b-lcb-remaining.sh)
verbatim, swap model ID + log paths. Skeleton:

```bash
#!/usr/bin/env bash
set -u
cd $REPO
mkdir -p .bench-logs/tbench-runs/coder-next

export OPENAI_API_BASE="http://127.0.0.1:1234/v1"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64

LOGDIR=$REPO/.bench-logs
DRIVER_LOG="$LOGDIR/tbench-coder-next-driver.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

harbor run terminal-bench-2 \
  --model "openai/qwen/qwen3-coder-next" \
  --concurrency 1 \
  --output .bench-logs/tbench-runs/coder-next \
  > "$LOGDIR/tbench-coder-next.log" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
```

Launch (detached, PPID=launchd):
```bash
nohup setsid bash $REPO/.bench-logs/run-tbench-coder-next.sh > /dev/null 2>&1 &
```

**Wall-clock estimates (high-uncertainty — Docker emulation tax is unknown):**

| # | Model | Decode t/s | Est. mean wall-clock/task | 89-task total |
|---|---|---|---|---|
| A1 | `qwen/qwen3-coder-next` | ~67 | ~6 min | **~9 h** |
| A2 | `gemma-4-26b-a4b@6bit` | ~58 | ~8 min | **~12 h** |

Phase A total: **~21 h** (1 overnight + 1 daytime block).

## Step 3 — Adapter: Harbor output → m4max chart pipeline

`m4max_charts.py` auto-discovers via `RUNS.glob("*_summary.json")` and reads
`{model, benchmark, score, elapsed_s}` (lines 60-70). Harbor's native output
will not match this shape — small adapter required.

### 3.1 Create `scripts/harbor_to_summary.py` (~30-line adapter)

Job: post-process a Harbor run directory into one canonical summary file +
per-task JSONL, dropped into `benchmarks/runs/`.

Inputs (from §0.3 discovery): Harbor's `--output` directory containing per-
task results.

Outputs:
- `tools/local-llm-bench-m4-32gb/benchmarks/runs/tbench_<model-slug>_<timestamp>_summary.json`
  with schema:
  ```json
  {
    "run_name": "tbench_<slug>_<ts>",
    "benchmark": "tbench",
    "model": "<lm-studio model id>",
    "score": 0.NN,
    "score_pct": "NN.N%",
    "correct": NN,
    "total": 89,
    "elapsed_s": NNNN,
    "elapsed_min": NN.N,
    "harbor_output_dir": ".bench-logs/tbench-runs/<short>",
    "timestamp_start": "<iso>",
    "timestamp_end": "<iso>"
  }
  ```
- `tools/local-llm-bench-m4-32gb/benchmarks/runs/tbench_<slug>_<ts>.jsonl`
  with one line per task (task_id, status, elapsed_s, log_excerpt).

### 3.2 Wire `m4max_charts.py` to recognize `tbench` AND `livecodebench`

The chart script's `BENCH_ORDER` (line 48) currently lists 6 benches —
`humaneval, mmlu, math, drop, gpqa, tool_combined`. **Neither `livecodebench`
nor `tbench` is plotted** even though LCB summaries already exist. Two-line
patch lands both:

```python
# Line 48
BENCH_ORDER = ["humaneval", "mmlu", "math", "drop", "gpqa",
               "livecodebench", "tool_combined", "tbench"]

# Lines 49-52 (BENCH_LABEL dict) — add:
"livecodebench": "LCB v6\n(n=50)",
"tbench": "Terminal-\nBench 2.0",
```

Also update the hardcoded `benches = [...]` lists at lines 173 and 207 to
match. **No other code changes needed** — the loader at line 60-70 already
handles any `*_summary.json` with the right keys, and the MERGED summaries
for LCB are already canonical.

Regenerate:
```bash
cd $REPO/tools/local-llm-bench-m4-32gb
source ../../.venv/bin/activate
python3 scripts/m4max_charts.py
```

## Step 4 — Phase B run plan (conditional on Phase A signal)

**Gate: Phase A complete; both summary JSONs land; chartTBench shows two
real measured numbers replacing the seeds.**

### Decision point before Phase B

Inspect both Phase A summaries:
- **Both < 10%**: T-Bench is too hard for local 6-bit MLX on this rig.
  **Abort Phase B**, document the finding, drop T-Bench from rotation.
- **Both > 25%** (vendor parity range): proceed full Phase B.
- **Split** (one < 10%, one > 25%): run only the 3 closest siblings of
  the winner; skip the rest.

### Run order (cheap-fail-first)

1. `gemma-4-e4b-it-mlx` — full 89-task run (§1 was just 5 tasks). ~3 h.
2. `gemma-4-26b-a4b@4bit` — quant A/B vs Phase A #2. ~10 h.
3. `qwen3.6-35b-a3b@6bit` — **F1 thinking-format guard**: if 35b-a3b's
   score is comparable to A's non-thinking models → thinking formatting
   works on T-Bench. If 35b-a3b ≤ 5% → thinking is the problem; **abort
   the 27b run** since it'll waste 30 h on the same failure. ~14 h.
4. `gemma-4-31b-it-mlx` — abort early if Phase 2 demotion holds. ~24 h.
5. `qwen3.6-27b` — only if 35b-a3b's thinking-format passed (#3). ~30+ h.

Driver pattern identical to Phase A. One driver per model.

### Wall-clock totals

- All 5: **~80 h** (~4 days with overnights)
- Reduced (skip 31b + 27b on F1 abort): **~27 h**

## Step 5 — Deliverables (after each phase lands)

### After Phase A (2 measured)

| File | Change |
|---|---|
| `tools/local-llm-bench-m4-32gb/scripts/harbor_to_summary.py` | New — adapter from §3.1 |
| `tools/local-llm-bench-m4-32gb/scripts/m4max_charts.py` | 2-line patch from §3.2 (adds `livecodebench` + `tbench` to plotted benches) |
| `.bench-logs/run-tbench-coder-next.sh` + `.bench-logs/run-tbench-gemma-26b-a4b-6bit.sh` | New driver scripts (template: `.bench-logs/run-27b-lcb-remaining.sh`) |
| `tools/local-llm-bench-m4-32gb/benchmarks/runs/tbench_*_summary.json` (×2) | New — adapter output, auto-discovered by chart script |
| `tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md` | Append `## Terminal-Bench 2.0 — Phase A (tie-breaker)` section with 2-row table (score, tasks passed, wall-clock, failure modes) |
| `reports/quality-benchmarks-charts.html` lines 446-457 (chartTBench) | Replace 2 vendor-claimed Qwen rows with measured values |
| `reports/quality-benchmarks-charts.html` line 228 (chartTBench subhead) | Add: "Local rows are measured on-rig via Harbor + LiteLLM → LM Studio (Docker linux/amd64); concurrency=1, vanilla T-Bench 2.0 task set." |
| `docs/testing-plan.md` "What we measure" table (~line 25) | New row: `**Terminal-Bench 2.0** (agentic shell) \| Multi-turn agent loop in Docker; only end-to-end shell-agent signal on this rig \| Harbor Framework → LiteLLM → LM Studio` |
| `docs/testing-plan.md` "Accuracy + coding + tool-calling" table (~line 113) | New T-Bench column right of `veerman`; Phase A fills 2 rows, rest `—` |
| `docs/testing-plan.md` "Next steps" section (~line 302) | New `### Step G — Terminal-Bench backfill` with link to this plan file |

### After Phase B (5 more measured)

| File | Change |
|---|---|
| `tools/local-llm-bench-m4-32gb/benchmarks/runs/tbench_*_summary.json` (×5) | New |
| `tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md` | Append `## Terminal-Bench 2.0 — Phase B (full backfill)` with full 7-row table + 1-paragraph takeaway on "what the agentic loop reveals that static benches miss" |
| `reports/quality-benchmarks-charts.html` chartTBench data block | Fill remaining 5 rows; all 7 local candidates present |
| `docs/local-llm-reference.md` slot recommendations (~lines 18-24) | **If** T-Bench reranks the agentic-default by > 10 pp → rewrite "Default for OpenCode" recommendation. **Otherwise** footnote existing recommendation with measured T-Bench number as defense. |
| `docs/local-llm-reference.md` per-model `qwen3.6-27b` row (~line 68) | Clarify the existing "T-Bench 59.3 (Opus 4.5 parity)" claim is a *frontier reference*, then add the **measured local** number from B's 27b leg |
| `docs/testing-plan.md` Next steps | Strike Step G when all 7 rows populated |
| Regenerate charts: `python3 tools/local-llm-bench-m4-32gb/scripts/m4max_charts.py` | Produces 8-bench-wide scores chart |

`reports/benchmark-charts.html` does NOT need a new bar group — it's the
throughput/local-only view; agentic-loop scoring belongs on the cross-
frontier chart. Skip unless explicitly requested.

## Step 6 — Failure modes + mitigations

| # | Failure | Symptom | Mitigation |
|---|---|---|---|
| F1 | T-Bench rejects thinking-model output | Qwen 27b / 35b-a3b emit `<think>...</think>` pre-amble before JSON tool calls; Harbor's parser rejects, all tasks fail | Run 35b-a3b BEFORE 27b in Phase B (cheap detection, ~14h vs 30h). If 35b-a3b ≤ 5% — try LM Studio "Auto"→"OpenAI" tool-format coercion, OR `--no-think` if Harbor exposes system-prompt override, OR document as "thinking models incompatible with T-Bench on this rig" |
| F2 | Docker disk exhaustion at task ~30+ | "no space left on device"; `docker system df` ballooning | Pre-flight raised disk to 100 GB in §0.1. Driver inserts `docker container prune -f && docker volume prune -f` between batches if Harbor exposes a batch flag (decided in §0.3) |
| F3 | 2-h `Bash run_in_background` silent kill | Confirmed in Phase 1 LCB | `nohup setsid bash …sh > /dev/null 2>&1 &` — confirmed working through 16h 27b LCB leg. Use existing pattern verbatim |
| F4 | LM Studio context exhaustion mid-task | Conversation > 65 536 tokens; truncation; task fails for harness reasons not model quality | Confirm 65 536 context on load (`lms.py check`). For the 27b thinking leg, consider 131 072 — verify `weights + KV < 80 GB` first |
| F5 | Harbor parallelism > 1 | Multiple containers hammer one LM Studio instance simultaneously; cascading timeouts | `--concurrency 1` on every Harbor command. Non-negotiable. If Harbor doesn't expose it, override via env var/config in §0.3 |
| F6 | Apple Silicon image-pull failure | "no matching manifest for linux/amd64" on first task | `export DOCKER_DEFAULT_PLATFORM=linux/amd64` (in driver template). Rosetta enabled in Docker Desktop settings |

## Step 7 — Verification (end-to-end before long runs)

The §1 smoke test on `gemma-4-e4b` is the verification gate. Chain is
healthy when all hold:

1. 5 tasks complete, ≥ 1 pass.
2. < 8 min/task wall-clock.
3. Adapter (§3.1) produces a valid `tbench_*_summary.json`.
4. Regenerating charts (`python3 scripts/m4max_charts.py`) shows a new
   "Terminal-Bench 2.0" column with the smoke result populated and the
   other rows blank (no false positives).

All four pass → Phase A is safe to launch.

Any failure → diagnose using §6 table before committing the ~21h Phase A
budget.

## Critical files (existing — to be referenced/modified)

- [`tools/local-llm-bench-m4-32gb/scripts/m4max_charts.py`](../../tools/local-llm-bench-m4-32gb/scripts/m4max_charts.py) — 2-line patch
  to `BENCH_ORDER` + `BENCH_LABEL` at lines 48-52; also lines 173 + 207
  hardcoded `benches = [...]` lists. Loader (lines 60-70) needs no change.
- [`reports/quality-benchmarks-charts.html`](../../reports/quality-benchmarks-charts.html) — chartTBench data block
  (lines 446-457); subhead (line 228); `LOCAL_COLOR` mapping (lines 294-301)
  already has all 7 model colorKeys wired.
- [`.bench-logs/run-27b-lcb-remaining.sh`](../../.bench-logs/run-27b-lcb-remaining.sh) — driver template; copy verbatim,
  swap model ID + log paths. Do not invent a new pattern.
- [`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md) — append
  Phase A + Phase B sections following the existing Phase 1+2 LCB-backfill
  style (~lines 200-260).
- [`docs/testing-plan.md`](../testing-plan.md) — Step G in Next-steps (~line 302); new T-Bench
  column in master table (~line 113); new row in "What we measure" (~line 25).

## New files (to create)

- `tools/local-llm-bench-m4-32gb/scripts/harbor_to_summary.py` — ~30-line
  adapter (§3.1).
- `.bench-logs/run-tbench-<model-short>.sh` — one driver per model
  (template: `.bench-logs/run-27b-lcb-remaining.sh`).
- (Optional) `tools/local-llm-bench-m4-32gb/scripts/HARBOR_CLI.md` —
  cheatsheet documenting verified Harbor flags from §0.3.

## Wall-clock summary + gates

| Phase | What | Wall-clock | Gate to next |
|---|---|---|---|
| 0 | Setup (Docker, Harbor, LM Studio chain) | 1-2 h | All 4 §0.* gates pass |
| 1 | Smoke (gemma-4-e4b, 5 tasks) | 30-45 min | ≥ 1/5 pass; chain validated |
| A | coder-next + gemma-26b-a4b@6bit (89 tasks each) | **~21 h** | At least 1 model scores > 10% |
| B (full) | 5 more models | **~80 h** | — |
| B (reduced, F1 abort) | 3 models (skip 31b + 27b) | **~27 h** | — |

**Total commitment if Phase A succeeds + B-reduced runs: ~50 h** (~6 days
realistic with overnight blocks). **B-full: ~100 h** (~10 days).

Decision points are at every gate — abort or descope cheaply at any of them.
