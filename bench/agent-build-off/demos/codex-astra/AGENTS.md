# Repository Instructions

## Objective

Build Hyper Runner, a complete browser-based 3D endless runner.
Prioritize a functional demo, clear controls, coherent visuals, and short implementation time.
Reuse established libraries, engine modules, and licensed assets before creating new infrastructure.

## Required documents

Read [SPEC.md](SPEC.md) before changing product behavior.
Read [PLAN.md](PLAN.md) before implementation.
The specification defines scope, controls, architecture, quality targets, and acceptance tests.
The plan defines implementation order, files, interfaces, and verification steps.
Keep both documents consistent with accepted decisions.
Record material deviations and their reasons.

## Working rules

- Save the specification and plan before building the game.
- Follow the user's confirmed decisions and explicit instructions.
- Use Babylon.js, TypeScript, and Vite as specified in SPEC.md.
- Keep Babylon.js core and loaders on matching versions.
- Pin direct dependencies and preserve the lockfile.
- Keep simulation rules separate from scene presentation and interface code.
- Use seeded patterns and bounded object pools.
- Reuse engine features instead of creating a general game framework.
- Store required assets locally and retain their license records.
- Keep commands and test results in the implementation record.
- Do not claim performance or device support without corresponding evidence.
- Do not publish the demo or contact others without user authorization.

## Verification

Run type checking, unit tests, the production build, and browser checks before completion.
Test the start, play, pause, collision, restart, and persistence flows.
Test touch controls and responsive layout.
Inspect the actual rendered game and capture screenshots.
Record checks that could not run.

## Output style

Use Simplified Technical English for prose, comments, documentation, and interface messages.
Keep one idea per sentence.
Keep instructions within 20 words and descriptions within 25 words.
Use active voice and concrete terms.
Use one term consistently for each concept.
Write abbreviations in full at first use.
Avoid figurative language, filler, intensifiers, marketing adjectives, and unsolicited emoji.
Use short paragraphs and meaningful structure.
Write in the user's language during conversation.
Follow a supplied template when its format differs.
