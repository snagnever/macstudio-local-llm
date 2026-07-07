# Repository organization

This is the contract for where things live. Follow it so the layout stays
coherent as work accrues. When a new file doesn't obviously fit, match the
closest rule below rather than inventing a new top-level directory.

## Top-level map

| Directory | Holds | Not |
|-----------|-------|-----|
| `docs/` | Stable reference: hardware, model cards, the master plan, runtime writeups | Per-run scratch, benchmark output |
| `bench/` | Benchmark **campaigns**: runbook + driver scripts + distilled results + raw logs | The tools themselves (those are submodules) |
| `fixes/` | Patches, chat-template overrides, install scripts we apply to make a model/runtime work | General-purpose code |
| `tools/` | The benchmark runners (git submodules) + shared helper scripts | Rig-specific orchestration |
| `reports/` | Self-contained Chart.js dashboards (served via GitHub Pages) | Source data |
| `research/` | Cross-model deep-dive analysis notes | Single-campaign runbooks |
| `vendor/` | Unrelated third-party infra kept locally | Anything we author |

## Where does a new file go?

- **A new benchmark run / campaign** → `bench/<campaign>/`. Put the runbook at
  `plan.md` (or `plan-<topic>.md` if the campaign has several), driver `.sh` and
  probe `.py` under `scripts/`, distilled `.jsonl`/summaries under `results/`,
  and raw logs under `logs/`. A campaign is a coherent line of work (a model's
  phase, or a cross-model study like `terminal-bench/` or `degeneration/`), not
  one script.
- **A new model card** → `docs/models/<model>.md` (flat file). When that model
  accumulates investigation writeups, **promote it to a folder**:
  `docs/models/<model>/` where `README.md` is the card and each writeup sits
  beside it with the redundant model prefix stripped
  (`deepseek-v4-flash-metal-oom-investigation.md` → `metal-oom-investigation.md`).
- **An investigation / incident writeup** → next to its model
  (`docs/models/<model>/`), or `docs/mlx-lm/` if it's about the runtime rather
  than one model.
- **A fix** (patch, chat-template override, install script) → `fixes/mlx-lm/`
  for runtime patches, `fixes/<model>/` for model-specific overrides.
- **A dashboard** → `reports/` (keep it self-contained; it may be published).
- **A cross-model analysis note** → `research/`.

## The results boundary (important)

Benchmark results live in two places on purpose:

- **Canonical per-model scores → the submodule `results/` trees.**
  `tools/local-llm-bench/results/` (per-model score dirs, tracked on the
  `results/m4-max-128gb-40gpu` branch) and
  `tools/local-llm-bench-m4-32gb/results/` (aggregate reports like
  `M4_MAX_128GB_NOTES.md`) are the authoritative scoreboard, committed alongside
  the tool that produced them. A `bench/<campaign>/scripts/` driver typically
  *invokes* one of these runners.
- **This rig's orchestration + scratch → `bench/`.** Driver scripts, ad-hoc
  result JSONLs, and logs that were never promoted into a submodule.

## Benchmark outputs policy

Benchmark *results* are irreplaceable measurements, not regenerable artifacts —
runs take hours on the rig and quant/runtime versions drift, so a rerun won't
reproduce them. Therefore:

- **Track** distilled outputs — scores, verdict/telemetry JSONLs, small
  summaries; anything a doc cites (guideline **≤ ~1 MB per file**) — under
  `bench/<campaign>/results/`.
- **Ignore** raw outputs — transcripts, `*.log`, run dirs, `*.gputrace` — under
  `bench/<campaign>/logs/`. The `bench/**/logs/` gitignore rule covers this.
- **Promote** canonical per-model scores into the submodule `results/` trees.

The failure mode this guards against is committing the bulky raw layer: git
never forgets, and a few full-transcript JSONLs would permanently bloat every
clone.

## Conventions

- Reference other files by repo-relative path so links stay clickable on GitHub.
- Each `bench/<campaign>/plan.md` preserves the original dated title so the
  chronology isn't lost.
- Don't add a new top-level directory without a reason that none of the above
  cover.
