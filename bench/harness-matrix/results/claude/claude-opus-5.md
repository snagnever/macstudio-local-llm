# claude × claude-opus-5

## Config

| | |
|---|---|
| Harness | Claude Code `2.1.228` (bare `claude`, **Anthropic-hosted model — control arm, not a local rig model**) |
| Model | `claude-opus-5` |
| Date | 2026-09-05 |

## Task — dolphin / hula hoop / fish (two runs)

### Run 1 — no-op

- **Prompt:** dolphin prompt (no prefix).
- **Outcome:** no artifact. The model ran a single `ls -la dolphin-hoop.svg cow-plowing.svg`
  (seeing prior outputs) and stopped. 13:51:35–13:51:52 local (~17 s), out 882 tokens.
- **Session:** `8917d2a1-…`

### Run 2 — dolphin-hoop-jump.svg

- **Prompt:** "do not check for existing files." + dolphin prompt.
- **Outcome:** `dolphin-hoop-jump.svg` (134 lines). Most iterative run of the matrix:
  - wrote the SVG via bash heredoc,
  - removed an unused `skin` gradient,
  - re-authored the dolphin geometry (`translate/rotate/scale` group) after a zoom-crop
    inspection,
  - validated with `xml.dom.minidom`,
  - visually checked with the Claude Browser MCP (navigate + screenshot),
  - cleaned up its scratch crop (`_zoom_tmp.svg`, deleted in-session).
- **Wall:** 13:52:02–13:58:25 local (~6.4 min) · **tokens:** out 60,947 (cache read 2,254,316)
- **Raw:** `../../logs/claude/claude-opus-5/dolphin-hoop-jump.svg`
- **Session:** `f8454b8d-…`

## Notes

- Run 1 shows the pair can no-op when the repo already contains same-prompt outputs
  (the "do not check for existing files" prefix was the user's fix).
