# macstudio-local-llm

Benchmarking workspace for the local LLMs running on this Mac Studio M4 Max
(128 GB unified memory). Centralises the benchmarking **tools**, the **raw
results** they produce, the **dashboards** that visualise them, and the
**model reference** that maps each model to its best use case.

## Layout

```
.
├── docs/                          Reference & hardware docs
│   ├── machine-configuration.md   Chip, RAM, OS
│   └── local-llm-reference.md     Which model to reach for, per task
│
├── tools/                         Benchmarking tools (git submodules)
│   ├── local-llm-bench-m4-32gb/   Knowledge + tool-calling (MMLU, HE, MATH, DROP, GPQA, LCB)
│   ├── local-llm-bench/           Scenario / real-workflow (ops-agent, doc-summary, tok/s)
│   └── scripts/
│       └── toggle-thinking.py     Toggle Qwen `enable_thinking` for A/B benches
│
├── reports/                       Self-contained Chart.js dashboards
│   ├── benchmark-charts.html      Local-model scores across all benches
│   ├── quality-benchmarks-charts.html  Local vs frontier models
│   └── README.md                  How to refresh the dashboards
│
├── research/                      Deep-dive notes
│   └── quality-benchmarks-2026-05.md
│
├── results/                       Raw model outputs that aren't numeric
│   └── coding-task/               Qualitative app-build benchmark per model
│
└── vendor/                        Unrelated third-party infra kept locally
```

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

After a run, refresh the dashboards from `reports/` (see `reports/README.md`).

## Picking a model

`docs/local-llm-reference.md` is the quick lookup — which model to use for
coding, tool-calling, reasoning, vision, etc. — based on the Phase 1
results currently summarised in
`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`.

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
