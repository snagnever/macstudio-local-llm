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
└── logs/                ← raw artifacts (GITIGNORED via bench/**/logs/)
    └── <harness>/<model>/          transcripts, traces, run dirs, outputs
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
  generated repos, anything bulky. Never commit (gitignored).
- **`results/<harness>/<model>.md`** — distilled: task brief, config
  (harness version, model quant, sampling), outcome, wall-clock, tokens,
  qualitative notes, link to the raw dir. This is what gets cited from
  `research/` or `reports/`.

## Comparison axes

- **Same model, different harness**: isolates harness quality (prompting,
  tool surface, LSP/MCP access).
- **Same harness, different model**: isolates model capability under one
  fixed tool surface — the axis that matters for picking a daily driver.

See `research/qwen3.8-harness-report.md` for the harness landscape this
matrix operates over.
