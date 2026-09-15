# opencode + deepseek-v4.1-flash

Date: 2026-09-10

## Configuration

- Harness: opencode 1.18.30.
- Model: `deepseek/deepseek-v4.1-flash`.
- Reasoning effort: `high` (opencode variant).
- Runtime: OpenRouter-hosted.

## Procedure

One opencode session asked the model to complete SVGBench with subagents of the same model, at effort `high`.

Seven `general` subagents created the drawings, one subagent per prompt. Each subagent received only the SVGBench prompt, the requested version, and the output path.

Each subagent created four takes in this order: `v1`, `v2`, `v3`, and `animated`.

The subagents could not read, list, or search files. They could not use the web, git, references, or other subagents.

The facts above come from the local opencode database (`~/.local/share/opencode/opencode.db`), parent session `ses_f71d07d5affeBa5XKaIraCy2mH`.

## Artifacts

The run produced 28 SVG files under `bench/harness-matrix/logs/opencode/deepseek-v4.1-flash-high/`: 21 static takes and seven animated takes.

The model also wrote `gallery.html` in the same directory. It is not an SVG, so it stays untracked.

## Scoring status

No judge verdict exists for these drawings. Reports mark them as unscored and exclude them from score means.
