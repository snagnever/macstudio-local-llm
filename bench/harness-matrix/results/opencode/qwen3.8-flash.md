# opencode + qwen3.8-flash

Date: 2026-09-09

## Configuration

- Harness: opencode 1.18.20 (picnic session) and 1.18.25 (treasure session).
- Model: `qwen/qwen3.8-flash` on OpenRouter, reasoning effort `max` (opencode variant).
- The last turns switched to `qwen3.8-flash` on the `qwencloud` provider, reasoning effort `xhigh`. That model wrote `picnic-above-clouds-animated.svg` and the animation edits in `treasure-barrel-v3.svg`.
- Runtime: hosted. This is not the rig's `qwen3.8-flash-next`.

## Procedure

This pair is not a subagent run. The operator drove two interactive sessions, one per prompt. Each session opened with the SVGBench prompt and an instruction not to look at other files.

- **Picnic on clouds (q5).** Takes in order: `picnic-above-clouds.svg` (take 1), `-v2`, `-v3`, `-v4`, and `-animated`. Before each new take the operator asked the model to look at the result, criticize it, and improve it. The animated take builds on the previous take.
- **Treasure barrel (q13).** Takes in order: `treasure-barrel.svg` (take 1), `-v2`, `-v3`. The request to add animation edited `-v3` in place, so `-v3` is animated and no static take 3 remains.

The model had shell, read, and edit tools, and the operator asked it to open the results. The takes after take 1 can depend on what the model saw of its own render.

The file names do not follow the SVGBench slugs. `results/svgbench/manifest.json` maps the picnic files to q5 with `question_index_override`.

The facts above come from the local opencode database (`~/.local/share/opencode/opencode.db`), sessions `ses_f7c00254affeJPJxgHCUYYYVio` (picnic) and `ses_f7bf6e6e5ffe3QKNC3RnUAD10d` (treasure).

## Artifacts

Eight SVG files under `bench/harness-matrix/logs/opencode/qwen3.8-flash/`. The model first wrote them in the repository root. They were copied here on 2026-09-15.

## Scoring status

No judge verdict exists for these drawings. Reports mark them as unscored and exclude them from score means.
