# OpenCode x gpt-5.6-terra - eight-prompt four-take SVG series

_Run date: 2026-09-06._

- **Harness / model:** OpenCode x `openai/gpt-5.6-terra`.
- **Method:** eight independent temporary workspaces; a fresh agent made v1 without
  seeing files or future takes, then fresh agents separately made v2, v3, and an
  animated version from the immediately preceding artifact. Each agent opened its
  completed SVG. Headless Chrome rendered all 32 imported artifacts.
- **Raw:** [`../../logs/opencode/gpt-5.6-terra/`](../../logs/opencode/gpt-5.6-terra/)
- **Prompt set:** cow plowing; dolphin through a hula hoop for a trainer's fish;
  picnic on clouds after a hot-air-balloon landing; rubber ducky in a soapy bathtub;
  fruit stall; half-buried treasure barrel; stunt car through a circle of fire; and
  the recovered animated dawn-on-the-beach request with the `Qwen 3.8 can draw`
  plane banner.
- **SVGBench:** 28 artifacts map to q0, q4, q5, q6, q7, q12, and q13; mean
  **0.421**. Per-question means: q0 0.604, q4 0.361, q5 0.300, q6 0.469,
  q7 0.714, q12 0.273, q13 0.225. The four dawn artifacts are intentionally
  off-benchmark. Verdicts are strict Chrome-render self-judgments by
  `openai/gpt-5.6-terra`, so they are useful for this internal series but not
  independent evaluation. See
  [`../svgbench/verdicts/opencode/gpt-5.6-terra/`](../svgbench/verdicts/opencode/gpt-5.6-terra/).

The picnic filenames use `balloon` while the pinned question uses the source typo
`ballon`; `results/svgbench/manifest.json` therefore records `question_index_override: 5`
for the four picnic artifacts.
