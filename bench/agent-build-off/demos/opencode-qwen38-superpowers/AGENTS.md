# Hyper Runner

A complete, impressive 3D endless-runner demo for the browser: synthwave neon
aesthetic, fully procedural assets, keyboard + touch.

## Start here

1. `SPEC.md` (repo root) — the approved specification. All game rules,
   numbers, and acceptance criteria live there. Do not change it without a
   note in the commit message.
2. `PLAN.md` (repo root) — the task-by-task implementation plan. Execute it
   in order; each task ends with a commit.

## Commands

- `npm install` — install deps
- `npm run dev` — dev server
- `npm test` — vitest unit tests (pure logic in `src/game/`)
- `npm run typecheck` — tsc strict
- `npm run build` / `npm run preview` — production build + serve

## Rules of the codebase

- Per-frame game state is a mutable singleton (`src/game/runtime.ts`);
  React/zustand holds only UI state (SPEC §2.2). Do not store per-frame
  values in zustand.
- `src/game/*` must not import React/three (audio/input may use Web
  APIs/DOM; runtime/patterns/collision/rng stay pure).
- Never let audio or localStorage failures throw (SPEC §2.4).
