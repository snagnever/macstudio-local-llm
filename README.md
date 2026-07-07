# macstudio-local-llm

Benchmarking workspace for the local LLMs running on this Mac Studio M4 Max
(128 GB unified memory). It centralises the benchmarking **tools**, the
per-campaign **runs** they produce, the **dashboards** that visualise them, the
**model reference** that maps each model to its best use case, and the
**fixes** applied to make specific models work on this stack.

> **New here? Read [AGENTS.md](AGENTS.md).** It's the map: what each directory is
> for and where a new file belongs. Following it keeps the layout coherent.

## Layout

```
.
├── AGENTS.md                     Organization contract — where everything goes
├── CLAUDE.md                     Pointer to AGENTS.md for Claude Code sessions
│
├── docs/                         Reference & hardware docs (stable, not per-run)
│   ├── machine-configuration.md  Chip, RAM, OS
│   ├── local-llm-reference.md    Which model to reach for, per task
│   ├── testing-plan.md           Master plan: phases, status, per-model verdicts
│   ├── models/                   One card per model (flat file, or folder when
│   │                             it has writeups: README.md = card + writeups)
│   └── mlx-lm/                   Runtime writeups not tied to one model
│
├── bench/                        Benchmark campaigns (one dir per campaign)
│   └── <campaign>/
│       ├── plan.md               Runbook (plan-<topic>.md if several)
│       ├── scripts/              Driver .sh + probe .py            (tracked)
│       ├── results/              Distilled .jsonl / summaries      (tracked)
│       └── logs/                 Raw logs, run dirs, GPU traces     (gitignored)
│
├── fixes/                        Things we apply to make models work
│   ├── mlx-lm/                   Runtime patches + notes
│   └── <model>/                  Chat-template overrides, install scripts
│
├── tools/                        Benchmarking tools (git submodules)
│   ├── local-llm-bench-m4-32gb/  Knowledge + tool-calling (MMLU, HE, MATH, …)
│   ├── local-llm-bench/          Scenario / real-workflow (ops-agent, tok/s)
│   └── scripts/                  Shared helpers (toggle-thinking.py)
│
├── reports/                      Self-contained Chart.js dashboards (GitHub Pages)
├── research/                     Deep-dive notes (cross-model analysis)
└── vendor/                       Unrelated third-party infra kept locally
```

The **canonical per-model scoreboard lives inside the submodules'** own
`results/` trees (committed with the tool that produced them). `bench/` is this
rig's orchestration and scratch layer — see [AGENTS.md](AGENTS.md) for the
boundary and the tracked-vs-ignored split.

## First-time clone

```bash
git clone https://github.com/snagnever/macstudio-local-llm.git
cd macstudio-local-llm
git submodule update --init --recursive
```

## Running a benchmark

**Knowledge + tool-calling (the M4 Max fork):**

```bash
cd tools/local-llm-bench-m4-32gb
# read the README for full setup (uv venv, LM Studio URL)
LMSTUDIO_URL=http://<host>:1234/v1 python3 scripts/bench2.py mmlu --examples 100
```

**Scenario / throughput (upstream-style runner):**

```bash
cd tools/local-llm-bench
python3 bench.py   # see its README for scenario flags
```

A campaign's driver scripts wrap these runners — e.g.
`bench/deepseek-v4-flash/scripts/run-deepseek-v4-flash-math.sh`. Each campaign's
`plan.md` is its runbook. After a run, refresh the dashboards from `reports/`
(see `reports/README.md`).

## Picking a model

[`docs/local-llm-reference.md`](docs/local-llm-reference.md) is the quick lookup
— which model to use for coding, tool-calling, reasoning, vision, etc. Per-model
detail lives in [`docs/models/`](docs/models/); the headline scores are
summarised in
`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`.

## Master plan

[`docs/testing-plan.md`](docs/testing-plan.md) is the orchestration document:
model phases, current status across all benches, per-model run order, and what's
next. Update it as facts change.

## Updating submodules

```bash
# Pull the latest commits of both submodules' tracked branches:
git submodule update --remote
git add tools/local-llm-bench tools/local-llm-bench-m4-32gb
git commit -m "Bump benchmarking submodules"
```

The `tools/local-llm-bench` submodule tracks the
`results/m4-max-128gb-40gpu` branch (where this rig's results live), not
`main`. The `tools/local-llm-bench-m4-32gb` submodule tracks `main` on the
`snagnever/` fork.
