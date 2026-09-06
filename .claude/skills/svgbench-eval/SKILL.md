---
name: svgbench-eval
description: Use when a model-generated SVG lands in bench/harness-matrix/logs, when SVGBench scores or verdicts must be refreshed or re-judged, when results/svgbench/scores.json is stale or fails the score step, or when someone asks how a harness×model pair scores on SVGBench.
---

# SVGBench evaluation of harness-matrix SVGs

Scores every `logs/<harness>/<model>/**/*.svg` in `bench/harness-matrix/` against the
matching [SVGBench](https://github.com/johnbean393/SVGBench) question. One artifact's
score is `requirements met / total`, judged on a headless-Chrome render. The display
JSON is `bench/harness-matrix/results/svgbench/scores.json`.

All paths below are relative to `bench/harness-matrix/`. Driver: `scripts/svgbench/svgbench_eval.py` (`--help` lists subcommands).

## Recipe

1. **Manifest.** `python3 scripts/svgbench/svgbench_eval.py manifest`
   Read the printed map. `qNone` = off-benchmark prompt (stays unscored). `STRAY` = SVG
   without a `logs/<harness>/<model>/` directory: do not move it, do not score it. It is
   already recorded under `skipped` in `scores.json`; mention it in the reply, nothing else.
   Wrong match? Add `"question_index_override": N` to that artifact in
   `results/svgbench/manifest.json` and rerun `manifest`.
2. **Render.** `python3 scripts/svgbench/svgbench_eval.py render --only <substring>`
   (omit `--only` for all). `--only` is a substring of the artifact path, so qualify it
   with the model when slugs repeat across models: `--only qwen3.8-flash-next/treasure-barrel`. PNGs land in `logs/renders/<harness>/<model>/<slug>.png` (gitignored).
3. **Judge** each artifact whose verdict file is missing or stale. Two ways:
   - Automated: set `SVGBENCH_JUDGE_URL`, `SVGBENCH_JUDGE_MODEL`, `SVGBENCH_JUDGE_KEY`
     (OpenAI-compatible vision endpoint) and run `... judge [--only X] [--force]`.
   - By hand (the current dataset): view the PNG, crop detail regions at 2x with
     `sips -c H W --cropOffset Y X in.png --out crop.png; sips -z 2H 2W crop.png`,
     then write the verdict file (contract below).
4. **Score.** `python3 scripts/svgbench/svgbench_eval.py score` rewrites `scores.json`.
   A `StaleVerdict` error names a verdict whose requirement texts no longer match the
   pinned `scripts/svgbench/questions.json`: re-judge that artifact.
5. **Tests.** `python3 tests/test_svgbench_eval.py` after any driver change.
6. **Cite.** If `results/<harness>/<model>.md` exists, add one line to the task's bullet
   list, in this form: `- **SVGBench:** 4/10 (q13) · verdict: `../svgbench/verdicts/<harness>/<model>/<slug>.json``.
   That file is the qualitative writeup; `scores.json` is the quantitative one.

## Verdict file contract

Path: `results/svgbench/verdicts/<harness>/<model>/<slug>.json`

```json
{
  "artifact": "logs/opencode/qwen3.8-flash-next/dolphin.svg",
  "question_index": 7,
  "render": "logs/renders/opencode/qwen3.8-flash-next/dolphin.png",
  "judge": {"kind": "claude-vision", "model": "<judge model id>", "date": "YYYY-MM-DD",
            "method": "viewed the Chrome render plus 2x crops of detail regions; strict per-requirement pass/fail"},
  "requirements": [{"text": "<exact text from questions.json>", "met": true, "note": "<one short reason>"}]
}
```

- `requirements` holds every requirement of the question, in order, text verbatim.
- One `met` per requirement, judged strictly and independently. A requirement with
  several conditions fails if any condition fails (e.g. "grey dolphin" fails for a blue
  one; "two small clouds" fails for four). Write the failing condition in `note`.
- `judge.kind` is `claude-vision` for a hand judgment, `llm` for the `judge` subcommand.
- Variants (`-animated`, `-v2`) are separate artifacts. If the render is visually
  identical to the base variant, copy its verdicts and add
  `"note": "render is visually identical to the base variant; same verdicts"` under `judge`.

## Common mistakes

| Mistake | Fix |
|---|---|
| Scoring from the SVG source instead of the render | Judge the PNG. Unrendered features do not count. |
| Passing a requirement that is half met | Strict: partial = `false`, say which part is missing. |
| Moving a stray SVG into a model directory to score it | Attribution is unknown. Leave it, list it as skipped. |
| Comparing `mean_score` with the upstream leaderboard | Different subset, harness path, and judge. Not comparable. |
| Editing `scores.json` by hand | It is generated. Edit verdicts, rerun `score`. |
| Refreshing `questions.json` without `questions.meta.json` | Record the upstream commit; existing verdicts may become stale. |
