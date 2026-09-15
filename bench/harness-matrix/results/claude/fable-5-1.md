# claude × fable-5-1

## Config

| | |
|---|---|
| Harness | Claude Code (bare `claude`, **Anthropic-hosted model — control arm, not a local rig model**); version not recorded |
| Model | `fable-5-1` |
| Date | 2026-09-06 (artifacts landed in the repo that day; the run itself was not logged) |

This pair was run without a verdict file at the time. The file exists now because
the SVGBench rejudge scored its four artifacts, and a scored pair on the board
should not be the only one without a writeup. The run narrative below is
reconstructed from the artifacts and the verdicts, not from a session transcript.

## Task — cow plowing a field (four takes)

- **Prompt:** "Write `svg` code to draw an image of a cow plowing a field."
- **Outcome:** four takes — `cow-plowing.svg` (165 lines) → `-v2` (177) → `-v3` (193)
  → `-animated` (231). All four are 960×600, self-contained, with no external
  references. The scene is the same across takes: sky with clouds, distant hills, a
  barn and a tree on the horizon, a cow facing left in harness, a plow behind it, a
  farmer walking behind the plow, and a field split between standing grass and
  turned soil. The revisions are localised. v2 moves the plowed soil so it starts at
  the blade instead of running under the cow, routes the traces low along the belly,
  and draws the share tip in the soil with earth curling off the moldboard. v3 adds
  a ragged edge to the fresh soil with clods along it, and replaces the single
  collar with a girth band plus a sagging trace rope. `-animated` adds SMIL: a
  2.4 s plod cycle (leg phases, head nod, tail swish, trace tug, farmer steps),
  a kicked-up clod at the share, and slower loops for drifting clouds, a swaying
  tree and circling birds — 16 `animateTransform` and 4 `animate` elements.
- **Wall / tokens:** not recorded.
- **Raw:** `../../logs/claude/fable-5-1/cow-plowing.svg` · `cow-plowing-v2.svg` ·
  `cow-plowing-v3.svg` · `cow-plowing-animated.svg`
- **Renders:** `../../logs/renders/claude/fable-5-1/` (gitignored PNGs;
  `cow-plowing-animated.png` is the t=0 frame)
- **SVGBench:** 9/12 (q0) · verdict: `../svgbench/verdicts/claude/fable-5-1/cow-plowing-animated.json`

## SVGBench

Four artifacts, all on question 0. Scores: `cow-plowing` 8/12, `-v2` 9/12,
`-v3` 9/12, `-animated` 9/12. Pair mean **0.729**. On q0 that is second of five
pairs, behind `claude/claude-opus-5` at 0.750 (four takes, all 9/12; self-judged — the
judge is `claude-opus-5`, this pair's own model) and ahead of
`opencode/qwen3.8-27b-8bit` 0.583, `opencode/qwen3.8-flash-next` 0.562 and
`opencode/gpt-5.6-terra` 0.458.

Eight requirements pass in all four takes: the bovine anatomy (body, head, four
legs, tail, udder), the face (ears, eyes, snout), the forward pulling stance, the
brown hooves, the wooden plow with a visible metal share, at least three dark
furrows trailing behind the plow, the plowed/unplowed split with the cow at the
boundary, and the background horizon with a blue sky and a yellow sun.

Three requirements fail in all four takes:

- **Black and white patches.** The cow is tan/caramel with off-white cream
  patches. There is no black anywhere on the body.
- **A wooden yoke connected to the plow by visible chains.** A dark brown collar
  or shoulder strap is drawn, but the line running back to the plow is a smooth
  strap or rope with no links.
- **Short green grass visibly being overturned by the plow.** Green grass is
  present in the unplowed section, but nothing is shown being overturned: only
  bare brown soil is turned at the share, with no green sod lifted or flipped.

One requirement splits the lineage, and it is what separates the first take from
the other three: *the plow's blade must be partially buried in the soil, actively
turning over a chunk of earth.* In `cow-plowing` the grey share is drawn fully
visible on top of the flat brown field on a small wheeled carriage — no part of it
is below the soil surface, and no earth is being lifted. From v2 onward a brown
mound covers the bottom of the share, which satisfies the buried clause by
occlusion, and earth curls off the moldboard.

## Notes

- This pair attempted **only question 0**. It has no cross-prompt mean, and its
  0.729 must not be placed in an overall ranking against pairs that ran four,
  five or seven questions. It is comparable to other pairs only on q0.
- The four takes are one lineage, but none is pixel-identical to another and each
  was judged on its own render.
- The judge for all four is `claude-opus-5`, the same single judge used across the
  whole board. See `../svgbench/judging-conventions.md` for the threshold rules,
  including the q0 rows on brown-vs-black hooves, what counts as a dark furrow,
  and what "partially buried" requires.
