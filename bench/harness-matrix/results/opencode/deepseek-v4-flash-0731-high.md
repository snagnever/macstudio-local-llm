# opencode + deepseek-v4-flash-0731

Date: 2026-09-10

## Configuration

- Harness: opencode 1.18.30.
- Model: `deepseek-v4-flash-0731`.
- Reasoning effort: `high` (opencode variant).
- Runtime: hosted by the `qwencloud` provider.

## Procedure

One opencode session asked the model to complete SVGBench with subagents of the same model, at effort `high`. The brief was the same as for [deepseek-v4.1-flash-high.md](deepseek-v4.1-flash-high.md).

Seven `general` subagents created the drawings, one subagent per prompt. Each subagent received only the SVGBench prompt, the requested version, and the output path.

Each subagent created four takes in this order: `v1`, `v2`, `v3`, and `animated`.

The subagents could not read, list, or search files. They could not use the web, git, references, or other subagents.

The first dolphin subagent did not finish. A second subagent, titled "dolphin v1 SVG (retry)", created the four dolphin takes.

The facts above come from the local opencode database (`~/.local/share/opencode/opencode.db`), parent session `ses_f71d140f2fferttlTVtI6oKpnF`.

## Artifacts

The run produced 28 SVG files under `bench/harness-matrix/logs/opencode/deepseek-v4-flash-0731-high/`: 21 static takes and seven animated takes.

## Scoring status

No judge verdict exists for these drawings. Reports mark them as unscored and exclude them from score means.
