# STATS — Hyper Runner build session

One session, on 2026-09-07 (UTC), from an empty folder to a working demo. Numbers come from the
opencode session database (`~/.local/share/opencode/opencode.db`, session `ses_f86cb0de8ffe…`,
per-message token records and tool-call parts) and from the repository itself — file timestamps,
package manifests, build output — not from estimates. Where a number was not collected, the row
says so rather than guessing. Figures exclude the two later prompts that wrote this file.

## Session

| Metric | Value |
| --- | --- |
| Wall time, first files written to final source edit | 90 min (00:15:44Z to 01:46:00Z) |
| SPEC/PLAN/AGENTS written before any game code | 7 min in (00:22:27Z) |
| Model | ddalcu Qwen3.8 Flash Next (MLX, mixed 4/8-bit), all 120 assistant turns |
| User prompts | 10 (the brief, two follow-ups, two "yes", four continues/defect reports, one URL question) |
| Questions asked to the user | 3 (visual theme, project folder, folder name) |
| Questions answered | 3 |
| Tool calls | 142 |
| Assistant turns with token usage | 120 |

Timestamps are file metadata (birth/modification times, machine at UTC-3). The brief followed
the same template as the sibling project in `../hyper-runner-claude`: research the current
stack first, save SPEC.md and PLAN.md before building, add an AGENTS.md pointing at both. That
session ran 37 minutes earlier, in parallel, for a like-for-like comparison.

The three questions all came before scaffolding: theme, project folder, and — after "yes" to
the first option twice — the folder name. Every decision after that was autonomous.

## Tokens

| Metric | Value |
| --- | --- |
| Output | 112,802 |
| Cache read (input) | 4,790,430 |
| Cache creation (input) | 0 |
| Uncached input | 1,268,186 |
| Reasoning | 0 |

Cache reads dominate because every request resends the conversation; they are 3.5× the uncached
input by the end. Cost is left out here; it needs a current price list rather than a guess.

## Compactions

| # | Time | Trigger | Context |
| --- | --- | --- | --- |
| 1 | 01:18:10Z | automatic, threshold (no overflow) | 63 min in, after the implementation and the first defect rounds |
| 2 | 01:41:36Z | automatic, threshold (no overflow) | mid-defect-7, 42 tool calls after the first compaction |

Both compactions are recorded in the session DB as `auto: true, overflow: false` — opencode
compressed the conversation proactively at the context threshold, never because a request
failed on size. Each keeps a `tail_start_id`, so the summary plus the recent tail of messages
carry on unbroken; nothing from the game code itself was lost across either boundary.

Compaction 2 is the interesting one: the first threshold took ~62 minutes of normal build work
to fill, the second refilled in 23 minutes — and the message right before it wrote a
196,860-byte tool-output file: a single `grep` over Rapier's WASM bundle that dumped base64
into the transcript, on top of the per-frame traces of the same minutes. The lesson: route
giant or binary command output to a file and grep the file, not the transcript.

## Code

| Metric | Value |
| --- | --- |
| Source lines (`src/`, TypeScript and CSS) | 1,170 |
| Source files | 13 |
| Documentation lines | 159 across SPEC, PLAN, AGENTS, README |
| Direct dependencies | 17 (10 runtime + 7 dev) |
| Installed packages, including transitive | 136 |
| Committed assets | none — every mesh is a procedural primitive, every sound is synthesised |

Largest files: `components/Pools.tsx` 289, `index.css` 212, `components/Player.tsx` 120,
`components/World.tsx` 101, `components/Hud.tsx` 92, `hooks/useControls.ts` 91, `store.ts` 88,
`App.tsx` 58, `sfx.ts` 43.

Unlike the sibling project, there is no pure-logic core: gameplay rules live in `useFrame`
loops mutating refs plus Rapier collision events, per the repo convention in `AGENTS.md`.
Verification therefore drove the real renderer and the real physics world through
Chrome DevTools Protocol, not an injected headless simulation.

## Libraries

| Package | Version | Role |
| --- | --- | --- |
| `three` | 0.185.1 | Renderer |
| `@react-three/fiber` | 9.7.0 | Declarative scene graph |
| `@react-three/drei` | 10.7.8 | Stars, helpers |
| `@react-three/postprocessing` | 3.1.1 | Bloom, chromatic aberration, vignette |
| `postprocessing` | 6.39.4 | Effect backend |
| `@react-three/rapier` | 2.2.0 | All gameplay physics and collision |
| `@dimforge/rapier3d-compat` | 0.19.2 | WASM physics engine (transitive) |
| `zustand` | 5.0.15 | Status and score store |
| `@use-gesture/react` | 10.3.1 | Touch swipe controls |
| `react` / `react-dom` | 19.2.8 | Interface overlay |
| `vite` | 8.2.2 | Development server and build |
| `@vitejs/plugin-react` | 6.1.1 | React transform |
| `typescript` | 6.0.3 | Types |
| `oxlint` | 1.81.0 | Linter (from the template) |
| `@types/three`, `@types/react`, `@types/react-dom`, `@types/node` | — | Types |

Audio uses the browser Web Audio API directly. No audio library, no audio files.

## Build output

| Artefact | Raw | Gzip |
| --- | --- | --- |
| `index.js` | 3,460 kB | 1,181 kB |
| `index.css` | 2.6 kB | 1.0 kB |
| `index.html` | 0.6 kB | 0.4 kB |

Build time: 0.33 s. One chunk, no code-splitting: the Rapier WASM ships inline in the main
bundle and is fetched at first paint. The sibling project lazy-loads physics as a separate
chunk; this one does not — the main trade-off behind the larger initial payload.

## Process

| Metric | Value |
| --- | --- |
| Tool calls by type | bash 54, edit 53, write 19, webfetch 4, todowrite 4, read 4, question 3, grep 1 |
| Web lookups for stack research | 4 |
| CDP test scripts written | 8 (smoke, regression, jump, four traces, one collider probe) |
| Headless Chrome automation sessions | 7 (debug ports 9333–9339) |
| Final automated assertions | 9 — 6 regression + 3 deterministic-jump, all green |
| Production builds | final run 0.33 s, green; exact count not recorded |
| Type checks (`tsc -b`) | exact count not recorded; final run green |
| Dev server | one long-lived Vite instance on :5199 with HMR driving the tests |

The deterministic-jump test forces the first three obstacles to be blocks at fixed positions
(z = 45/58/71, speed 12 u/s), then presses jump at three timings — mid, early, and an
edge-graze 1.42 units out. It is the check worth keeping; defect 7 below only reproduced under
it.

## Defects found during verification, and fixed

1. Entering play crashed the app. The ground collider was mounted outside the `Physics` provider.
2. React 19 rejects ref callbacks whose body implicitly returns the assignment. Three colliders
   hit this; every ref callback now uses a block body.
3. The death screen showed score 0. `crash()` never read the live score at the moment of death.
4. The sun vanished seconds into a run. It scrolled with the world; pinned at z = 168 so the
   player can never outrun it.
5. Lane controls were mirrored. The camera looks down +z, so world +x appears on the left;
   `moveLane` negates screen direction. Verified: ArrowRight → lane −1.
6. Inputs were silently dropped. A jump pressed while rising, or a slide pressed one frame
   before landing, vanished. Fixed with timestamped input buffering (0.18 s) plus coyote time
   (0.12 s). Verified: a slide pressed at y = 2.61 still executes.
7. Deaths happened on clean jumps, intermittently. The hard one. Rapier 0.19.2 kept generating
   contacts for colliders that reported `setEnabled(false)`: the capsule's bottom was 1.25
   above a 0.6-tall block, yet collision events fired with normals `{0,1,0}` and `{0,0,-1}` —
   geometrically possible only against the *disabled* wall and bar colliders. Enabled flags
   read false at apply time and 1.5 s later, so the flag and the narrow phase disagreed.
   Fixed by translating inactive colliders to y = −999 instead of disabling them, plus a z/x
   proximity guard in the crash handler. Found by per-frame CDP tracing with a seeded obstacle
   layout, not by playing.
8. A debug call to a nonexistent `collider.enabled()` method threw inside a zustand subscriber,
   which killed every later notification and made a passing test report a false failure — and
   at one point a dead dev server produced three false negatives on the jump test. Both were
   fixed before the defect-7 root cause was reachable.

## Not verified

Audible output, because the browser harness gives no sound; only the absence of audio errors
was checked. Touch/swipe controls were implemented via `@use-gesture/react` but the automation
drove the keyboard only. Frame rate on low-end hardware.

## Other metrics worth adding

These were not collected this time and would need instrumentation:

- **Frames per second under load**, sampled on a low-end machine rather than this one.
- **Time to first interactive frame**, from navigation to the menu being clickable — the
  inline 3.5 MB bundle makes this the first thing to measure if the payload is optimised.
- **Rework ratio**: lines written and later replaced, against lines that survived to the end.
- **Time split by phase**: writing, debugging, verification. The timestamps split roughly
  26 min code-first (00:15Z–00:41Z) against 65 min of automated verification (00:41Z–01:46Z),
  most of the latter on defect 7.
- **Autopilot survival distribution** over many seeds, as a difficulty regression check — this
  project has no autopilot; the deterministic-jump test covers fairness but not difficulty.
