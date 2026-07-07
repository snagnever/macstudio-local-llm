# Repo Reorganization Design

**Date:** 2026-07-06
**Status:** Approved design, pending implementation plan
**Goal:** Discoverability. Make the structure self-explanatory: visible directories,
clear taxonomy, updated documentation. Everything tracked is moved with `git mv`
(history preserved via `--follow`); nothing tracked is pruned.

## Problems being solved

1. `.bench-logs/` is a **hidden** directory holding ~75 tracked source files
   (run drivers, probe scripts, result JSONLs) mixed with ~98 GB of untracked
   logs and gputrace bundles. Tracked code in a dotdir is easy to lose and hard
   to discover.
2. `docs/` mixes three content types at one level: stable reference, one-off
   investigation writeups, and dated benchmark runbooks.
3. `assets/` is vaguely named — it holds model fixes (chat-template overrides +
   install scripts), conceptual siblings of `patches/` (mlx-lm patches).
4. `results/` overlaps in meaning with `reports/` and `research/`.
5. `README.md` describes a layout that no longer matches reality (no mention of
   `patches/`, `assets/`, `.bench-logs/`, `docs/models/`, `docs/benchmark-plans/`).
6. No written convention tells future work (human or agent) where new files go.

## Target structure

```
.
├── README.md          # rewritten to match reality + link to conventions
├── AGENTS.md          # org conventions: what goes where, how to add a campaign
├── CLAUDE.md          # one-line pointer/import of AGENTS.md
├── bench/             # ← replaces hidden .bench-logs/ (visible, per-campaign)
│   ├── <campaign>/
│   │   ├── plan.md            # runbook (from docs/benchmark-plans/)
│   │   ├── scripts/           # run-*.sh drivers, probe .py (tracked)
│   │   ├── results/           # .jsonl outputs (tracked)
│   │   └── logs/              # runtime logs, gputraces (gitignored)
│   └── coding-task/           # ← from results/ (qualitative apps, content unchanged)
├── docs/
│   ├── machine-configuration.md
│   ├── local-llm-reference.md
│   ├── testing-plan.md
│   ├── models/                # model-centric: card + its writeups together
│   │   ├── README.md
│   │   ├── deepseek-v4-flash/ # README.md (card) + setup, OOM writeups, HF/PR drafts
│   │   ├── <model-with-writeups>/
│   │   └── <model>.md         # models with only a card stay flat files
│   ├── mlx-lm/                # writeups not tied to one model
│   └── superpowers/           # skill-managed specs/plans, stays put
├── fixes/                     # ← merges patches/ + assets/
│   ├── mlx-lm/                # .patch files + seed-fix NOTE + tool-marker repro
│   └── deepseek-v4-flash/     # dsml + tool-template overrides (jinja, install.sh)
├── reports/                   # unchanged (GitHub Pages URLs stay valid)
├── research/                  # unchanged (deep-dive notes stay here)
├── tools/                     # unchanged: 2 submodules + scripts/
└── vendor/                    # unchanged
```

**Directories that disappear:** `.bench-logs/`, `assets/`, `patches/`,
`results/`, `docs/benchmark-plans/`.
**Directories explicitly kept:** `reports/` (published dashboard URLs),
`research/` (deep-dive notes), `tools/`, `vendor/`, `docs/superpowers/`.

## Design decisions

### bench/ — per-campaign, code split from artifacts

Initial campaign set (from the runbooks in `docs/benchmark-plans/` and filename
prefixes in `.bench-logs/`):

- `gemma-4-phase2/` — `run-full-*`, `run-knowledge-4bit*`, gemma drivers
- `lcb-phase1/` — `run-27b-lcb-remaining`, LCB phase-1 files
- `terminal-bench/` — all `run-tbench-*` (cross-model campaign)
- `degeneration/` — cross-model campaign (started on DeepSeek, extended with
  Qwen quant controls in PR #17): `degeneration*`, `qwen-*-degeneration*`,
  `run-qwen-degeneration-control.sh`, sampling sweep, longform-coherence,
  XTC files; both related runbooks (degeneration-sampling, quant-validation)
- `deepseek-v4-flash/` — `run-deepseek-v4-flash-*`, `run-ds4-*`, `repro_oom_*`,
  tool-template tests, jdhodges runs
- `minimax-m2.5/` — `run-minimax-*`, minimax macmon JSONLs
- `agents-a1-xl/` — agents-a1-xl runs
- `phase-5-new-arrivals/` — phase-5 runbook (+ future files)
- `coding-task/` — the qualitative app-build benchmark from `results/`

Rules:

- Tracked scripts → `bench/<campaign>/scripts/`; tracked result JSONLs →
  `bench/<campaign>/results/`; untracked logs/gputraces → `bench/<campaign>/logs/`
  (gitignored). The 98 GB of untracked artifacts moves with a same-volume `mv`.
- File-by-file mapping is an implementation-plan artifact. Ambiguous stragglers
  are assigned to the campaign whose runbook mentions them; `bench/misc/` is the
  escape hatch only for true orphans.
- `.gitignore`: replace `.bench-logs/*` rules with `bench/**/logs/`; keep
  `*.gputrace/` and the model-weight patterns.

### docs/models — flat file until a model earns a folder

A model with only a card stays `docs/models/<model>.md`. When a model
accumulates writeups, it is promoted to `docs/models/<model>/` where
`README.md` is the card and writeups sit beside it with the redundant model
prefix stripped (e.g. `deepseek-v4-flash-metal-oom-investigation.md` →
`metal-oom-investigation.md`). Today this promotes: **deepseek-v4-flash**
(setup, OOM family, HF leak post, PR-16 comment), **gemma-4-26b-a4b**
(channel-token-leak writeup), and **hermes-4-70b** (minja render error). `mlx-lm-tool-call-marker-merge-writeup.md`
is not model-specific → `docs/mlx-lm/`.

### fixes/ — one home for things we apply to make models work

- `fixes/mlx-lm/` — the `.patch` files, `mlx-lm-server-seed-fix-NOTE.md`, and
  `assets/mlx-lm-tool-marker-fix/` repro.
- `fixes/deepseek-v4-flash/` — `assets/deepseek-v4-dsml/` and
  `assets/deepseek-v4-tool-template/` (jinja overrides, install/uninstall
  scripts, probes).

### Submodules and the results boundary

`tools/` holds two submodules — separate git repos whose internal layout is
**out of scope** (a superproject `git mv` cannot touch them, and one of them
deliberately commits results to a tracked branch). They are not restructured.

The design must, however, resolve where benchmark results live, because three
result homes otherwise coexist ambiguously. The rule (documented in AGENTS.md):

- **Submodule `results/` = canonical.** `tools/local-llm-bench/results/` (the
  ~20 per-model score dirs, tracked on the `results/m4-max-128gb-40gpu` branch)
  and `tools/local-llm-bench-m4-32gb/results/` (aggregate reports —
  `M4_MAX_128GB_NOTES.md`, `FINAL_100Q_RESULTS.md`, charts, runs/) remain the
  authoritative scoreboard, committed alongside the tool that produced them.
- **`bench/` = orchestration + scratch.** This rig's driver scripts, ad-hoc
  result JSONLs, and logs that were never promoted into a submodule. A
  `bench/<campaign>/scripts/` driver typically *invokes* a submodule runner
  (`tools/local-llm-bench-m4-32gb/scripts/bench2.py`, `tools/local-llm-bench/bench.py`);
  its JSONL/log output is scratch that lands under `bench/<campaign>/`.

AGENTS.md states this split so future work knows: canonical per-model scores →
submodule `results/`; a new rig run's drivers and scratch output → `bench/`.
`README.md` keeps its existing "picking a model" pointer at
`tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md`.

### Runbooks move into their campaign

`docs/benchmark-plans/<date>-<topic>.md` → `bench/<campaign>/plan.md`. The
dated original filename is preserved in the file's title line so chronology
isn't lost. Campaigns with multiple runbooks (deepseek-v4-flash has 4;
degeneration gets 2 — degeneration-sampling and quant-validation) keep
`plan-<topic>.md` files side by side.

### Documentation deliverables

- **README.md** — full rewrite: actual layout tree, per-directory purpose,
  first-time clone, running a benchmark, updating submodules, link to AGENTS.md.
- **AGENTS.md** (new) — the organization contract: what each top-level dir is
  for, the decision table for "where does a new file go" (new benchmark run →
  new `bench/<campaign>/`; new model card → `docs/models/`; investigation
  writeup → model folder or `docs/mlx-lm/`; fix/override → `fixes/<target>/`),
  the flat-file-vs-folder promotion rule for model docs, the tracked/ignored
  split inside `bench/`, the **submodule-results-vs-`bench/` boundary**
  (canonical per-model scores live in the submodule `results/`; a rig run's
  drivers and scratch output live in `bench/`), and the **benchmark outputs
  policy** below.

  **Outputs policy (goes verbatim into AGENTS.md):** benchmark *results* are
  irreplaceable measurements, not regenerable artifacts — runs take hours on
  the rig and quant/runtime versions drift, so a rerun won't reproduce them.
  Therefore: **track** distilled outputs (scores, verdict/telemetry JSONLs,
  small summaries — anything a doc cites; guideline ≤ ~1 MB per file) under
  `bench/<campaign>/results/`; **ignore** raw outputs (transcripts, `*.log`,
  run dirs, `*.gputrace`) under `bench/<campaign>/logs/`; **promote** canonical
  per-model scores into the submodule `results/` trees. The failure mode this
  guards against is committing the bulky raw layer — git never forgets, and a
  few full-transcript JSONLs would permanently bloat every clone.
- **CLAUDE.md** (new) — one-line import of AGENTS.md so Claude Code sessions
  load the same conventions.
- Path-reference rewrite in the same PR: `testing-plan.md`, `reports/README.md`,
  `docs/models/README.md`, and any `run-*.sh` referencing `.bench-logs/` paths.

## Out of scope (deliberate)

- No pruning of tracked content (`vendor/web-search-mcp/dist/`, committed
  `db.sqlite`, the Next.js apps under coding-task — they move, nothing more).
- No submodule changes — their internal layout and their `results/` trees are
  separate git repos, left entirely as-is; the reorg only *documents* the
  boundary between them and `bench/`.
- No history rewriting; all moves are `git mv`.

## Execution

One dedicated PR off `main`. Gate (updated 2026-07-07 — the original gate,
`docs/minimax-context-limit-and-eval`, landed as PR #14): start **after PR #16
and PR #17 land**, since both add files to trees this reorg moves (#16 → one
macmon JSONL in `.bench-logs/`; #17 → four `.bench-logs/` files + a runbook in
`docs/benchmark-plans/`). PR #18 (submodule pointer bump) is orthogonal and can
land any time. Open stale branches accept the rebase/conflict risk.

## Error handling / verification

- After the move: `git status` must show only renames (`R`) plus the new/edited
  docs; no deletions without a paired add.
- `rg -n '\.bench-logs|benchmark-plans|assets/|patches/|research/benchmarks'`
  across tracked files must return no stale references (excluding this spec and
  historical writeup prose that intentionally quotes old paths).
- Dashboards in `reports/` still open and render after the move.
- `du -sh bench/` ≈ old `.bench-logs/` size; no artifact left behind in a
  deleted dotdir.
