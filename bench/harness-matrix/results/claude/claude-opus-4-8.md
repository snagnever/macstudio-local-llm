# claude × claude-opus-4-8

## Config

| | |
|---|---|
| Harness | Claude Code `2.1.228` (bare `claude`, **Anthropic-hosted model — control arm, not a local rig model**) |
| Model | `claude-opus-4-8` |
| Date | 2026-09-05 |

## Task — dolphin / hula hoop / fish

- **Prompt:** "Write `svg` code for an image of a dolphin jumping out of the water and
  through a hula hoop to bite a fish out of its trainers hand."
- **Outcome:** `dolphin-hoop.svg` — one `Write` + one `Edit` (refinement), then the file
  was sent to the user. Adds `role="img"` + `aria-label`, a radial-gradient sun, and a
  darker, more "designed" palette than the local-model runs.
- **Wall:** 13:50:17–13:51:06 local (~50 s) · **tokens:** out 8,850 (cache read 435,543)
- **Raw:** `../../logs/claude/claude-opus-4-8/dolphin-hoop.svg`
- **Session:** `476cb5e8-…` (`~/.claude/projects/-Users-vitor-LocalProjects-macstudio-local-llm/`)
