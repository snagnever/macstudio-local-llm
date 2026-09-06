# Harness × model matrix — artifacts per (harness, model) combination

_Dated 2026-09-05._

Artifacts produced by running local models through coding-agent harnesses
(OpenCode, Cline, Aider, Pi, …). Each artifact belongs to one **(harness, model)**
pair; the directory layout mirrors that pair so comparisons along either axis
stay trivial.

## Layout

```
harness-matrix/
├── plan.md              ← this runbook
├── results/             ← distilled verdicts (TRACKED, keep ≤ ~1 MB/file)
│   └── <harness>/<model>.md        one verdict file per combination
└── logs/                ← raw artifacts (gitignored via bench/**/logs/**)
    └── <harness>/<model>/          transcripts, traces, run dirs, outputs
                                    (model-generated SVGs: tracked exception)
```

## Naming

- `<harness>`: lowercase harness name as invoked — `opencode`, `cline`, `aider`, `pi`
- `<model>`: the LM Studio model ID, with path separators replaced by `-`
  (e.g. `qwen3.8-flash-next`, `qwen3.6-27b-mlx-6bit`)

Example: a Qwen3.8 Flash-Next run under OpenCode lands in
`logs/opencode/qwen3.8-flash-next/` with its verdict distilled to
`results/opencode/qwen3.8-flash-next.md`.

## What goes where

- **`logs/<harness>/<model>/`** — raw: session transcripts, tool-call traces,
  generated repos, anything bulky. Never commit (gitignored). The one
  exception: model-generated **SVG artifacts are tracked** (small, verifiable,
  cited by the verdict via its `Raw:` link).
- **`results/<harness>/<model>.md`** — distilled: task brief, config
  (harness version, model quant, sampling, **reasoning effort**), outcome,
  wall-clock, tokens, qualitative notes, link to the raw dir. This is what gets
  cited from `research/` or `reports/`. Record the effort level per run: it is
  the strongest lever on token count, and each harness sends it through a
  different wire field (see `bench/qwen3.8-harness-eval/plan.md`, "Effort por
  harness").

## SVGBench scoring of the artifacts

Every SVG under `logs/<harness>/<model>/` whose filename slug matches an
[SVGBench](https://github.com/johnbean393/SVGBench) prompt gets scored against that
question's requirements. Score = requirements met / total, the SVGBench metric,
judged on a headless-Chrome render (SVGBench renders with Chrome too).

- Driver: `scripts/svgbench/svgbench_eval.py` (`manifest` → `render` → `judge` or
  hand-written verdicts → `score`). Run `--help` for the subcommands.
- Pinned questions: `scripts/svgbench/questions.json` (+ `questions.meta.json` with the
  upstream commit).
- Tracked outputs (`results/svgbench/`): `manifest.json` (artifact → question map),
  `verdicts/<harness>/<model>/<slug>.json` (per-requirement pass/fail + note),
  `scores.json` (the display JSON: per-artifact, per-pair, per-question).
- Renders go to `logs/renders/` (gitignored, PNG).
- Recipe for updating after a new artifact or re-judging: the project skill
  `.claude/skills/svgbench-eval/SKILL.md`.

Caveat: the subset is small, the artifacts came through coding harnesses (not the
SVGBench direct-API loop), and the judge differs from upstream's `gemini-2.5-flash`.
Do not compare `mean_score` with the upstream leaderboard.

## Comparison axes

- **Same model, different harness**: isolates harness quality (prompting,
  tool surface, LSP/MCP access).
- **Same harness, different model**: isolates model capability under one
  fixed tool surface — the axis that matters for picking a daily driver.

See `research/qwen3.8-harness-report.md` for the harness landscape this
matrix operates over.
