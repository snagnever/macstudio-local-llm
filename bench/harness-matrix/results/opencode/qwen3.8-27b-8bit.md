# opencode × qwen3.8-27b-8bit

## Config

| | |
|---|---|
| Harness | OpenCode `1.18.20` (provider `rig`, Tailscale) |
| Model | `mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9` |
| Runtime | mlx-dspark arm S (MLX 8-bit + DFlash2 drafter), `http://mac-studio:8484` |
| Date | 2026-09-05 |

## Task A — cow plowing (smoke run)

- **Prompt:** "Write `svg` code to draw an image of a cow plowing a field."
- **Outcome:** single-pass `cow-plowing.svg` (800×500, `<title>`, sun with rays, cloud,
  field, cow + plow). Opened in Chrome on follow-up. No edits or retries.
- **Wall:** 13:18–13:26 local (~8 min, incl. follow-up) · **tokens:** in 26,099 / out 15,087
- **Raw:** `../../logs/opencode/qwen3.8-27b-8bit/cow-plowing.svg`

## Task B — dolphin / hula hoop / fish

- **Prompt:** "Write `svg` code for an image of a dolphin jumping out of the water and
  through a hula hoop to bite a fish out of its trainers hand."
- **Outcome:** single-pass `dolphin.svg`. Reads well as a scene (splash, striped hoop with
  back/front halves, trainer on a pier) but has **no `<title>`/`<desc>`/`role="img"`**
  accessibility markup — both Claude Code runs in this matrix added it unprompted.
- **Wall:** 13:46–14:11 local (~25 min, incl. "open on chrome" follow-up) ·
  **tokens:** in 42,107 / out 22,222
- **Raw:** `../../logs/opencode/qwen3.8-27b-8bit/dolphin.svg`

## Notes

- Both SVGs are well-formed and render cleanly in Chrome; no interventions.
- Sessions: `ses_f8da2ce7…` (smoke) and `ses_f8d89033…` (dolphin).
