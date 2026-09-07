# opencode × qwen3.8-flash-next

## Config

| | |
|---|---|
| Harness | OpenCode `1.18.20` (provider `rigfn`, Tailscale) |
| Model | `rigfn--ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd` |
| Runtime | mlx-serve (arm FS, ddalcu mixed-4/8), `http://mac-studio:11234` |
| Effort | `xhigh` |
| Date | 2026-09-06 |

## Task — dolphin / hula hoop / fish

- **Prompt:** "Write `svg` code for an image of a dolphin jumping out of the water and
  through a hula hoop to bite a fish out of its trainers hand." (prefixed "do not look
  for local files" — no repo exploration requested by the prompt itself)
- **Outcome:** single-pass `dolphin.svg` (800×600, `<title>` included; rainbow-striped
  hoop drawn twice — whole ring behind the dolphin, bottom half clipped in front of the
  belly — for the through-the-hoop read; open jaws with dark mouth wedge, fish held in
  the trainer's extended hand, splash foam at the waterline). Well-formed XML
  (validated with `xml.dom.minidom`) and rasterized via Quick Look; the model could not
  view the raster (no image input) and said so. Opened in Chrome on follow-up.
  No edits or retries.
- **Wall:** 00:06–00:26 local (~20 min, incl. "open in chrome" + save follow-ups) ·
  **tokens:** n/a (not surfaced in-session)
- **Raw:** `../../logs/opencode/qwen3.8-flash-next/dolphin.svg`
- **SVGBench:** 5/7 (q7) · verdict: `../svgbench/verdicts/opencode/qwen3.8-flash-next/dolphin.json`

## Notes

- Single-shot scene with layered depth (hoop back/front, splash over tail, jaw strip
  over the fish) — comparable ambition to the `qwen3.8-27b-8bit` run of the same prompt,
  but this pass included accessibility markup (`<title>`) the 27B run omitted.
- Session in this working tree; token counts would need the rig's metrics endpoint.

## Task — cow plowing a field (4-take iteration)

- **Prompt:** "Write `svg` code to draw an image of a cow plowing a field."
- **Outcome:** four takes by fresh subagent-generators under an orchestrator that
  rendered each take with headless Chrome, viewed it, and wrote the critique fed to the
  next take (generators were not told further takes would follow).
  `cow-plowing.svg` (blind first pass; balloon-oval cow, incoherent harness, illegible
  plow) → `-v2` (added farmer, yoke+traces, perspective furrows, cast shadows) →
  `-v3` (team scaled to ~half the frame, bovine head, clod tilth, gentle convergence)
  → `-animated` (fixed drooping head / tangled harness, plus a seamless 2.4 s SMIL
  plod cycle: leg phases, body bob, head nod, tail flick, farmer steps, tumbling
  clods, drifting clouds/birds; motion verified via two headless-Chrome frames 1.2 s
  apart). All 800×600, self-contained.
- **Wall:** 13:46–15:08 local (~82 min: v1 7 min, v2 stalled 12 min + retry 14 min,
  v3 20 min, v4 22 min; generator sessions 76 min + orchestrator renders/critiques) ·
  **tokens:** ~509k input / ~196k output / ~1.38M cache-read (orchestrator's 16 steps +
  5 subagent sessions, incl. the stalled take; ~705k total). Figures reconstructed
  after the fact from `~/.local/share/opencode/opencode.db` (`session.tokens_*` and
  per-step `message.data.tokens`); cost n/a (self-hosted). The stalled v2 take burned
  ~32k output tokens without writing an artifact.
- **Raw:** `../../logs/opencode/qwen3.8-flash-next/cow-plowing.svg` ·
  `cow-plowing-v2.svg` · `cow-plowing-v3.svg` · `cow-plowing-animated.svg`
- **Renders:** `../../logs/renders/opencode/qwen3.8-flash-next/` (gitignored PNGs;
  `cow-plowing-animated.png` is the t=0 frame)
- **SVGBench:** 7/12 (q0) · verdict: `../svgbench/verdicts/opencode/qwen3.8-flash-next/cow-plowing.json`

## Task — dolphin / hula hoop / fish (fresh-agent 4-take)

- **Prompt:** "Write `svg` code for an image of a dolphin jumping out of the water and
  through a hula hoop to bite a fish out of its trainers hand."
- **Outcome:** four takes by fresh subagent-generators under an orchestrator that
  rendered each take with headless Chrome, viewed it, and wrote the critique fed to the
  next take (generators were not told further takes would follow).
  `dolphin-hula-hoop-fish-v1.svg` (blind 800×600 pass; rainbow hoop split back/front,
  open jaws at the fish, thin splash) → `-v2` (1600×1200; parametrically recomputed
  through-the-hoop arcs so the body verifiably crosses the ring plane, thicker body,
  fanged gape gripping the fish, crown splash, real gripping hand) →
  `-v3` (melon-and-rostrum head replacing the fanged maw, small conical teeth, leaf
  flukes, hoop recentered so the near rim overlaps the belly, fish clamped head-first
  in the pinch grip) → `-dolphin-hula-hoop-fish-animated.svg` (5 s seamless SMIL loop:
  dolphin bobs on its jump arc with pitch rock, fluke flutter, pectoral wave, fish wag
  in the grip, hoop rims wobble on-beat, waterline path-morph with expanding ripples,
  staggered falling droplets, drifting clouds; every animation starts and ends on the
  v3 pose). All self-contained; XML validated with `xmllint`.
  The v2 generator stalled once (session ended without writing its artifact; a resume
  prompt produced the file) — same failure mode as the cow-plowing v2 take.
- **Wall:** 16:42–17:38 local (~56 min incl. the stalled v2 take and its resume) ·
  **tokens:** n/a this session
- **Raw:** `../../logs/opencode/qwen3.8-flash-next/dolphin-hula-hoop-fish-v1.svg` ·
  `-v2.svg` · `-v3.svg` · `-animated.svg`
- **Renders:** `../../logs/renders/opencode/qwen3.8-flash-next/` (gitignored PNGs;
  `dolphin-hula-hoop-fish-animated.png` is the t=0 frame)
- **SVGBench:** 7/7 (q7) · verdict: `../svgbench/verdicts/opencode/qwen3.8-flash-next/dolphin-hula-hoop-fish-animated.json`
