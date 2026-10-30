# STATS — Hyper Runner build session (`hyper-runner-qwen-cc`)

Numbers come from the session transcript and the repository, not estimates.
The source is the Claude Code transcript under
`~/.claude/projects/-Users-vitor-LocalProjects-hyper-runner-qwen-cc/`
(session `1a5e9107-…`, plus plan-mode session `2f6b0ef7-…`, which is the same
conversation continued). OpenCode holds no data for this folder: its
identically-named runner session (`ses_f865c42e0ffe…`) built a different
project, `../hyper-runner-superpowers` (212 tool parts reference that path,
zero reference this one). Token sums are deduplicated by message id, keeping the
maximum usage seen for each id (streamed blocks repeat the usage object, and
a subagent stream contains partial stub lines). A naive per-line sum inflates
the totals about 3.4×. Counts include one spawned subagent.

## Session

| Field | Value |
| --- | --- |
| Date | 2026-09-07 |
| Wall time | 14:13:06 → 16:37 UTC ≈ 2 h 24 min (single flow, still open at extraction) |
| Model | `ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit` (local MLX proxy, provider `rigfn`, variant `xhigh`) |
| User prompts | 6 (brief, "use brave search", "/btw why did you forget to write spec, plan and agents?", "continue", "whats the status?", this STATS request) |
| Interruptions | 2 Esc interruptions (one rejected the first `npm install`; "continue" resumed it) |
| Compactions | 8 (all `auto`, session `1a5e9107`; plan session `2f6b0ef7`: 0) — see note below |
| Question rounds | 1 AskUserQuestion round, 4 questions, all answered "(Recommended)" |
| Tool calls | 127 unique (124 main session + 3 in the planning subagent), deduplicated by call id |
| Assistant API turns | 96 (94 main session + 2 subagent) |

One subagent ran during planning (`Plan` type, "Design runner game
architecture", 14:22:32 → 14:28:23 UTC): 3 tool calls (1 shell check, 2 Brave
searches), 14,302 output tokens, 14,347 input tokens, 6,125 cache-read tokens.

Compactions, from the `compact_boundary` markers in the transcript (count as
of this edit; each future context-window rollover adds one):

| # | Time (UTC) | Trigger | Pre → post tokens | Duration |
| --- | --- | --- | --- | --- |
| 1 | 14:49:43 | auto | 107,169 → 18,827 | 163 s |
| 2 | 15:00:51 | auto | 112,404 → 13,039 | 223 s |
| 3 | 15:12:12 | auto | 99,004 → 15,003 | 215 s |
| 4 | 15:21:50 | auto | 102,948 → 14,441 | 175 s |
| 5 | 15:31:00 | auto | 99,292 → 7,147 | 156 s |
| 6 | 16:33:28 | auto | 99,319 → 13,599 | 170 s |
| 7 | 16:46:12 | auto | 100,156 → 10,650 | 211 s |
| 8 | 17:08:04 | auto | 101,079 → 13,264 | 189 s |

Every compaction fired near the ~100k-token window limit. Cumulative dropped
tokens: 715,401. During the active build (compactions 1–5) the average gap
was 10.5 minutes.

First prompt, verbatim:

> You are going to create a complete and impressive 3D demo runner game, using
> modules and libraries to reduce the need of new code.
> You should search the web for most updated information, stack and best practices
> Select the stack based on easiness to implement a functional demo on reduced time.
> Question me for decisions and ambiguities while creating the plan.
>
> - SAVE a detailed SPEC AND PLAN to SPEC.md and PLAN.md on the folder before building
> - Create an AGENTS.md explaining the repo objective, poiting to both PLAN and SPEC files

The question round locked four decisions before any code: stack (Babylon.js 9 +
Vite + TypeScript), theme (neon synthwave grid), mechanics (full set), art and
audio (fully procedural, zero binary assets).

## Tokens

Session-wide (main session + planning subagent):

| Kind | Tokens |
| --- | --- |
| Output | 149,235 (134,933 main + 14,302 subagent) |
| Cache read | 3,194,985 (3,188,860 main + 6,125 subagent) |
| Cache creation | 0 (the local proxy never reports it) |
| Uncached input | 3,538,572 (3,524,225 main + 14,347 subagent) |

Cost is not computable: the `rigfn` local MLX proxy charges nothing in the
transcript (`cost` field absent), and no public price list exists for this
private model.

## Code

| Metric | Value |
| --- | --- |
| Source lines | 2,135 across 19 files (`src/*.ts` 1,824 / 17 files, `hud.css` 246, `index.html` 65) |
| Documentation lines | 343 (SPEC.md 181, PLAN.md 90, AGENTS.md 72) |
| Babylon-independent logic | 309 lines (collision 79, config 86, powerups 38, score 64, events 35, state 7) |
| Direct dependencies | 3 runtime + 2 dev |
| Installed packages | 20 (node_modules ≈ 183 MB) |
| Binary assets | 0 (all meshes, textures, audio procedural) |

Largest files: `src/factory.ts` 302, `src/game.ts` 265, `hud.css` 246,
`src/audio.ts` 243, `src/world.ts` 212.

## Libraries

| Package | Version | Role |
| --- | --- | --- |
| @babylonjs/core | 9.25.0 | meshes, materials, GlowLayer, ShaderMaterial, InstancedMesh pooling |
| vite | 7.3.6 | dev server + production build |
| typescript | 5.9.3 | strict ES2022, `moduleResolution: "bundler"` |
| (none) | — | audio: raw WebAudio oscillators, no library |
| (none) | — | HUD: plain DOM + CSS, no Babylon GUI |

## Build output

| Artefact | Raw | Gzip |
| --- | --- | --- |
| dist/assets/index-*.js | 6,868.46 kB | 1,516.54 kB |
| dist/assets/index-*.css | 2.90 kB | 1.15 kB |
| dist/index.html | 2.28 kB | 0.89 kB |
| dist/assets/ total | 46 files (44 lazy Babylon chunks + entry js + css), dist ≈ 6.8 MB | — |

Build time: 35.5 s. The chunk-size warning is cosmetic: the demo imports all
of `@babylonjs/core` tree-shaken only by ES module boundaries.

## Process

| Activity | Count |
| --- | --- |
| Web searches | 7 (3 built-in WebSearch — all returned empty; 4 Brave searches via WebFetch, per user instruction: 2 in the main session, 2 in the planning subagent) |
| Production builds | 2 (first failed with 9 type errors, second clean) |
| Type checks | 2 (same runs as builds) |
| Files written whole (Write) | 28 |
| Files patched (Edit) | 11 edits across 6 files |
| Reads | 29 |
| Shell commands (Bash) | 41 (3 `npm install` attempts — one rejected, one interrupted, one done; 3 `npx tsc`/vite port re-checks; the rest for stats) |
| Browser automation | 0 |

## Defects found during verification, and fixed

1. **Documentation was nearly forgotten.** Planning ran 14:13 → 14:28 with
   research and architecture work, but SPEC.md, PLAN.md, and AGENTS.md were
   never written in plan mode. The user caught it at 15:15 UTC
   (`/btw why did you forget to write spec, plan and agents?`); the three
   files were written at 15:17–15:18 UTC, before any code file.
2. **Nine TypeScript errors after the first full write.** Root cause:
   `as const` on the config object made every field a literal type, so
   `speed`, `lane`, and `bpm` could not be reassigned. Fix: annotate the
   mutable fields `: number`.
3. **`GameEventMap` as an interface broke `EventBus<E extends
   Record<string, unknown>>`.** Interfaces have no implicit index signature.
   Fix: changed `interface` to `type`.
4. **ShaderMaterial GLSL passed with the wrong keys (latent runtime bug, type
   check passed).** Babylon 9 expects `vertexSource`/`fragmentSource` in the
   path object, and `attributes`/`uniforms` in the 4th constructor argument.
   The first code used `vertex`/`fragment` in the options object — the three
   grid materials would have rendered nothing. Found by reading the Babylon 9
   `IShaderPath` type in node_modules.
5. **GlowLayer option name.** `resolutionRatio` does not exist in Babylon 9;
   the option is `mainTextureRatio`.
6. **Phantom scaffold recovery.** An early `npm install` rejection plus an Esc
   interruption left the tooling files (package.json, tsconfig, vite.config)
   unwritten; the resume re-created them before continuing.
7. **Port 5199 false positive.** `curl` hit a stale server from another
   project. Re-verified the dev server with
   `npx vite --port 5317 --strictPort` and bound output.

## Not verified

Five PLAN items are marked `[browser]` and were never executed — no browser
automation ran in this session:

- 60 fps sustained on Apple Silicon
- touch swipe input on a real device
- audio unlock after first gesture, and the mute toggle
- a full 3-minute run without a stuck state
- first paint under 5 s

## Other metrics worth adding

- Cost, once a price list for the `rigfn` proxy exists.
- Sustained fps, via a stats panel in the running game.
- Time to first rendered frame, from the browser performance timeline.
- Autopilot survival time, from a headless test harness.
- Rework ratio: 11 edits / 28 writes ≈ 0.39 (low, because most defects were
  caught before the first successful build).
- Phase split (rough, from transcript timestamps): planning + research
  14:13–14:28 (15 min, subagent included), documentation 15:17–15:18 (1 min,
  late — see defect 1), code + builds + fixes 15:18–16:28 (≈ 70 min), stats
  investigation from 16:28 on.
