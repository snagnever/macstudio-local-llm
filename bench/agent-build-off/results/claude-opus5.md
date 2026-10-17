# STATS — Hyper Runner build session

One session, on 2026-09-07, from an empty folder to a working demo. Numbers come from the
session transcript and from the repository itself, not from estimates.

## Session

| Metric | Value |
| --- | --- |
| Wall time, first prompt to final report | 41.9 min (00:52:37Z to 01:34:31Z) |
| Model | claude-opus-5, every message |
| User prompts | 3 (the brief, one interruption, one correction) |
| Questions asked to the user | 8, across 3 rounds |
| Questions answered | 8 |
| Tool calls | 107 |
| Assistant turns with token usage | 187 |
| Compactions | 0 |

Every figure below is a snapshot of the build session, up to the final report at 01:34:31Z. The
turns that wrote this file are excluded, except where stated.

### The first prompt, verbatim

> You are going to create a complete and impressive 3D demo runner game, using modules and
> libraries to reduce the need of new code. You should search the web for most updated
> information, stack and best practices. Select the stack based on easiness to implement a
> functional demo on reduced time. Question me for decisions and ambiguities while creating the
> plan.
>
> - SAVE a detailed SPEC AND PLAN to SPEC.md and PLAN.md on the folder before building
> - Create an AGENTS.md explaining the repo objective, poiting to both PLAN and SPEC files

### The eight questions

Round 1, before planning: art direction, character representation, physics scope, feature scope.
Round 2, before planning: scoring and collectibles, audio source, delivery and verification.
Round 3, mid-build: which connected Chrome browser to drive.

The user interrupted once, to ask for a broadcast prompt in Chrome instead of a browser list.

## Compactions

**None. The session never compacted.**

The transcript holds no compaction record: no `summary` entry, no `isCompactSummary` flag, no
`compactMetadata`. Every turn saw the full conversation, so nothing in this file is reconstructed
from a summary.

| Metric | Value |
| --- | --- |
| Compactions | 0 |
| Context window | 1,000,000 tokens (`claude-opus-5[1m]`) |
| Peak context, build session | 233,894 tokens, 23.4 % of the window |
| Context at the first request | 45,921 tokens |
| Growth | roughly 1,000 tokens per request |

Context grew steadily and never came close to the limit:

```
req   0    45,921
req  40    84,499
req  80   137,682
req 120   172,569
req 160   213,892
req 186   233,894   <- end of the build session
```

Three habits kept it flat enough to avoid a compaction, and they are worth repeating on the next
build of this size:

1. **Batched tool calls.** Browser work went through `browser_batch`, so a click, a wait, and
   three screenshots cost one round trip instead of five.
2. **Patches over rewrites.** After the first draft, files changed through small `python3` and
   `sed` edits. Re-reading and re-emitting whole files is what usually fills a window.
3. **Verification through scripts, not transcripts.** The autopilot ran in the browser console and
   returned one JSON line. Printing per-frame state instead would have cost tens of thousands of
   tokens and found the same defect.

Screenshots were the largest single cost: 29 of them during the build. Their per-image token
cost was not measured, so no share of the growth above is claimed for them. They were the only
way to catch the floating robot and the camera leaving the tunnel, so the spend was worth it.

## Tokens

| Metric | Value |
| --- | --- |
| Output | 240,076 |
| Cache read (input) | 25,978,321 |
| Cache creation (input) | 559,100 |
| Uncached input | 374 |

Cache reads dominate because every request resends the conversation. Cost is left out here; it
needs a current price list rather than a guess.

## Code

| Metric | Value |
| --- | --- |
| Source lines (`src/`, TypeScript and CSS) | 2,111 |
| Source files | 26 |
| Documentation lines | 319 across SPEC, PLAN, AGENTS, README |
| Direct dependencies | 15 |
| Installed packages, including transitive | 74 |
| Committed asset | `robot.glb`, 463,988 bytes |

Largest files: `ui/styles.css` 254, `game/chunks.ts` 198, `game/world.ts` 167, `game/player.ts`
148, `game/spawner.ts` 141, `audio/synth.ts` 134, `App.tsx` 125.

The `src/game/` directory holds 782 lines of pure logic that import neither three.js nor React.

## Libraries

| Package | Version | Role |
| --- | --- | --- |
| `three` | 0.185.1 | Renderer |
| `@react-three/fiber` | 9.7.0 | Declarative scene graph |
| `@react-three/drei` | 10.7.8 | Model loading, animation, helpers |
| `@react-three/postprocessing` | 3.1.1 | Bloom, chromatic aberration, vignette |
| `postprocessing` | 6.39.4 | Effect backend |
| `@react-three/rapier` | 2.2.0 | Crash debris only |
| `zustand` | 5.0.15 | Phase and score store |
| `react` / `react-dom` | 19.2.8 | Interface overlay |
| `vite` | 8.2.2 | Development server and build |
| `@vitejs/plugin-react` | 6.1.1 | React transform |
| `typescript` | 7.0.2 | Types |
| `@types/three`, `@types/react`, `@types/react-dom` | — | Types |

Audio uses the browser Web Audio API directly. No audio library, no audio files.

## Build output

| Artefact | Raw | Gzip |
| --- | --- | --- |
| `index.js` | 1,257 kB | 347 kB |
| `Debris.js` (Rapier, lazy) | 2,258 kB | 850 kB |
| `index.css` | 3.2 kB | 1.3 kB |
| `rapier.js` | 2.7 kB | 1.2 kB |

Build time: 0.39 s to 0.49 s over three runs. Rapier is a separate chunk, fetched when a run
starts rather than at first paint.

## Process

| Metric | Value |
| --- | --- |
| Web searches for stack research | 5 |
| `npm view` version checks | 4 |
| Production builds run | 17 |
| Type checks run | 18 |
| Files written whole | 20 |
| Files patched in place | 20 |
| Browser automation calls | 37 |

## Defects found during verification, and fixed

1. The robot floated above the floor. The model was scaled to height but never offset by the
   distance from its origin to its feet.
2. The track stayed empty for the first 13 seconds. The spawner started at the far edge instead
   of filling the corridor.
3. The lean angle reached 62 degrees on a lane change. The robot read as falling over.
4. The replay camera orbited outside the tunnel shell after a crash.
5. The collision box was as wide as the mesh, so a lane change still in flight always clipped the
   neighbouring lane. Every autopilot run died the same way. A narrower hitbox took survival from
   33 seconds to 65 to 107 seconds.

Defect 5 was found by a scripted autopilot driving the pure logic through `window.hyper`, not by
playing. That is the check worth keeping.

## Not verified

Audible output, because the browser harness gives no sound; only the absence of audio errors was
checked. The quality auto-degrade, because the frame rate never dropped far enough to trigger it.

## Other metrics worth adding

These were not collected this time and would need instrumentation:

- **Frames per second under load**, sampled on a low-end machine rather than this one.
- **Time to first interactive frame**, from navigation to the menu being clickable.
- **Cost in currency**, once a current price list is at hand.
- **Rework ratio**: lines written and later replaced, against lines that survived to the end.
- **Time split by phase**: research, planning, writing code, verification. Verification took the
  larger share here, which the transcript timestamps could confirm exactly.
- **Autopilot survival distribution** over many seeds, as a difficulty regression check between
  changes.
