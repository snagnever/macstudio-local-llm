# STATS — Hyper Runner build session (opencode)

One session, on 2026-09-07, from an empty folder to a working demo, then a bug
report and a fix. Numbers come from the opencode session database and from the
repository itself, not from estimates. The sibling `hyper-runner-claude` repo
was driven by a hosted model; this one ran on a **local** MLX-served model.

## Session

| Metric | Value |
| --- | --- |
| First prompt to final report (raw clock) | 11 h 22 m 20 s (02:12:49Z → 13:35:09Z) |
| minus laptop asleep mid-task (03:54:03Z → 13:07:11Z, no input involved) | −9 h 13 m 08 s |
| minus time waiting for user input (8 prompts, sum of gaps) | −19 m 54 s |
| **Active time, input-wait corrected** | **1 h 49 m 18 s** |
| Model | Qwen3.8-Flash-Next, MLX mixed 4-bit, served locally, every message |
| User prompts typed | 10 (the brief, 4 planning answers, 2 interruptions, "como rodar?", a bug report, this stats request) |
| Questions asked to the user | 8, across 2 rounds |
| Questions answered | 8 |
| Tool calls (to the final report) | 230 valid + 1 malformed |
| Messages in session | 254 (236 assistant, 10 prompts, 4 auto-compactions, 4 auto-continuations) |

The raw clock number is not the build time. The machine slept for 9 h 13 m in
the middle of task 8, between two assistant messages — that is downtime, not
waiting for input, and it is deducted on its own line. Input wait is the sum of
the gaps between each agent answer and the next typed prompt: 45 s, 58 s, 33 s,
603 s (reading the spec), 14 s, 27 s, 100 s, 314 s. The slow local model is
included in active time on purpose: a 12-minute single-call plan write that
looked hung, and ~3.5-minute first-token delays after each compaction, are a
cost of this setup, not idle time.

### The first prompt, verbatim

> You are going to create a complete and impressive 3D demo runner game, using modules and
> libraries to reduce the need of new code. You should search the web for most updated
> information, stack and best practices. Select the stack based on easiness to implement a
> functional demo on reduced time. Question me for decisions and ambiguities while creating the
> plan.
>
> - SAVE a detailed SPEC AND PLAN to SPEC.md and PLAN.md on the folder before building
> - Create an AGENTS.md explaining the repo objective, poiting to both PLAN and SPEC files

The same brief that drove the claude session.

### The eight questions

Round 1, before planning: game concept, controls, assets, audio, gameplay
scope, stack. Round 2, after the plan: execute as planned, and whether to
isolate the work in a git worktree (consent was given to work on `main`).

The user interrupted twice: once to flag a stuck plan write ("it seems
something is wrong"), once to change how the plan file gets written ("escreva o
PLAN.md em partes, uma tarefa por chamada de write").

### Compaction

The session compacted itself 4 times — all automatic, none by overflow: the
transcript hit ~100k tokens and opencode summarized before the window filled.

| # | Time | Context at trigger | Auto-continuation arrived |
| --- | --- | --- | --- |
| 1 | 02:43:36Z | 108,114 tokens | 153 s later |
| 2 | 03:17:13Z | 100,893 tokens | 208 s later |
| 3 | 03:48:40Z | 99,396 tokens | 222 s later |
| 4 | 13:28:43Z | 101,801 tokens | 212 s later |

Peak context before any compaction was 108,114 tokens. The gap after each
trigger is the summary itself being generated on the slow local model; the
continuation prompt then re-injected a structured "## Objective / Work State /
Next Move" digest. The first compaction was a direct consequence of the
plan-write incident: the single 2,000-line `write` of PLAN.md blew the context
in one call, which is also what prompted the user's "em partes" interruption.
Compaction overhead totals ≈13 minutes — about 12 % of active time — and this
stats file is itself a consumer of digest #3's successor.

## Tokens


| Metric | Value |
| --- | --- |
| Output | 285,431 |
| Uncached input | 875,625 |
| Cache read (input) | 13,581,216 |
| Cache creation (input) | 0 |

Totals were read while this stats request was running, so they include it.
Cost in currency is effectively zero — the model runs on this machine — which
is the honest trade that bought the slower wall clock.

## Code

| Metric | Value |
| --- | --- |
| Source lines (`src/`, TypeScript + CSS) | 2,136 (1,978 TS/TSX, 158 CSS) |
| Source files | 34 |
| Documentation lines | 3,201 across SPEC (219), PLAN (2,953), AGENTS (29) |
| Direct dependencies | 16 (7 runtime, 9 dev) |
| Installed packages, including transitive | 156 |
| Committed assets | none — grid shader, WebAudio synth and CSS wordmark are all procedural |
| Tests passing | 65 |

Largest files: `game/runtime.test.ts` 289, `game/runtime.ts` 243, `ui.css` 158,
`game/audio.ts` 124, `game/store.ts` 114.

The `src/game/` directory holds 765 lines of pure logic (tests excluded) that
import neither three.js nor React.

## Libraries

| Package | Version | Role |
| --- | --- | --- |
| `three` | 0.185.1 | Renderer |
| `@react-three/fiber` | 9.7.0 | Declarative scene graph |
| `@react-three/drei` | 10.7.8 | Grid, camera helpers |
| `@react-three/postprocessing` | 3.1.1 | Bloom, vignette |
| `postprocessing` | 6.39.4 | Effect backend |
| `zustand` | 5.0.15 | Phase and score store |
| `react` / `react-dom` | 19.2.8 | Interface overlay |
| `vite` | 8.2.2 | Development server and build |
| `@vitejs/plugin-react` | 6.1.1 | React transform |
| `typescript` | 5.9.3 | Types (strict, noUnusedLocals) |
| `vitest` / `jsdom` | 5.0.0 / 30.0.1 | Tests (v3 was peer-incompatible with vite 8) |

No physics engine (hand-rolled kinematics), no audio library, no audio files,
no fonts fetched, no runtime network at all.

## Build output

| Artefact | Raw | Gzip |
| --- | --- | --- |
| `index.js` | 1,175 kB | 319 kB |
| `index.css` | 2,335 B | 958 B |

Single chunk, no lazy split. Build time: 0.147 s to 0.162 s over three runs.
The sibling project shipped 3.5 MB of JS plus a 464 kB `robot.glb` across two
chunks; this one ships 1.18 MB and nothing else.

## Process

| Metric | Value |
| --- | --- |
| Registry lookups (webfetch + `npm view`) | 7 + 9 |
| Production builds run | 7 |
| Type checks run | 13 |
| Full test suites run | 14 |
| Targeted `vitest run` invocations | 27 |
| Files written whole | 45 |
| Files patched in place | 49 |
| Skills invoked | 7 (brainstorming, writing-plans, executing-plans, worktrees, TDD, systematic-debugging, finishing) |
| Commits in repo | 18 (13 feat, 1 chore scaffold, 2 docs, 2 fixes), tag `v0.1.0-demo` |

## Defects found during verification, and fixed

1. The spawner used per-row timers instead of a distance accumulator, so rows
   spaced unevenly. Two red tests caught it; `spawnAccum` fixed it.
2. Coin-chain expansion placed the rear coins in front, making the train
   visually teleport. Fixed by expanding rear-first.
3. The plan's coin-grab tolerance formula let a standing player collect a coin
   floating at jump height. Replaced with a point-in-player-box test.
4. The localStorage key literal contained a `…` (U+2026) — a typographic
   ellipsis, not three dots. The garbage-value test caught the corrupted key.
5. `;`-chained `git commit` after a failing typecheck committed a Scene missing
   `<Player />` (TS6133). Fixed with a follow-up commit; commits now chain with
   `&&` so a red gate stops them.
6. The track blinked black and grid lines vanished (user-reported after
   delivery, 15 h into the raw clock). Root cause: `multisampling={0}` on the
   EffectComposer; drei's Grid draws lines with an alpha-blended `fwidth`
   shader that discards zero-alpha fragments, and the offscreen target had no
   MSAA at all — canvas `antialias` does not apply. Fix: `multisampling={4}`.

The flicker fix is the one worth keeping: found by reading the installed
shader source in `node_modules` after the first hypothesis (z-fighting) was
ruled out, not by guessing parameters.

## Not verified

Audible output — the headless gates can only prove the audio code never throws.
Visual confirmation of the flicker fix, since there is no browser harness in
this session; it is awaiting a human look. Touch swipes on a real device, and
frame rate on hardware slower than this machine.

## Other metrics worth adding

These were not collected this time and would need instrumentation:

- **Frames per second under load**, sampled on a low-end machine.
- **Time to first interactive frame**, from navigation to the menu being clickable.
- **Energy per build**, the only real currency cost of a local model.
- **Rework ratio**: lines written and later replaced, against lines that survived.
- **Time split by phase**: research, planning, writing, verification — the
  session timestamps could split this exactly; planning alone (brief to plan
  commit) took 65 minutes of active time here, dominated by the plan-write
  incident.
- **Autopilot survival distribution** over seeds — the sibling project drove
  the game with a scripted bot; this one only asserts same-seed replay
  determinism.
