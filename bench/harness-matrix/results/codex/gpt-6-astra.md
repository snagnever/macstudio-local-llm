# Codex + gpt-6-astra

Date: 2026-09-12

## Configuration

- Harness: Codex. The version was not recorded.
- Model: `gpt-6-astra`.
- Reasoning effort: `medium`.
- Runtime: OpenAI-hosted.

## Procedure

Seven agents created the drawings. Each agent received one SVGBench prompt directly.

The first turn requested only `v1`. The agent did not know that later versions were planned.
After each turn, the coordinator rendered the new SVG with headless Chrome.
The same agent opened that PNG before creating `v2` and `v3`.
The final turn requested an animated version from the rendered `v3` composition.

The agents did not read existing drawings, SVG reports, renders, scores, or verdicts before `v1`.

## Artifacts

The run produced 28 SVG files under `bench/harness-matrix/logs/codex/gpt-6-astra/`.

The files contain 21 static takes and seven animated takes.
XML validation passed for all 28 files.
No file loads an external resource.
All seven animated takes contain SVG or CSS animation.

## Scoring status

No judge verdict exists for these drawings.
Reports mark them as unscored and exclude them from score means.
