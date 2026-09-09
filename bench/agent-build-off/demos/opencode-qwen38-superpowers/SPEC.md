# Hyper Runner — Specification

A complete, impressive 3D endless-runner demo that runs in the browser with
`npm install && npm run dev`. Synthwave neon aesthetic, fully procedural assets
(no external models/textures/audio files), built almost entirely from
battle-tested libraries so hand-written code stays small.

## 1. Player experience

One sentence: sprint an endless neon highway at night, weaving lanes, jumping
barriers, sliding under gates, grabbing coins — until one mistake ends the run.

### 1.1 Controls (keyboard + touch, identical semantics)

| Intent     | Keyboard              | Touch               |
|------------|-----------------------|---------------------|
| Move left  | ArrowLeft / A         | swipe left          |
| Move right | ArrowRight / D        | swipe right         |
| Jump       | ArrowUp / W / Space   | swipe up            |
| Slide      | ArrowDown / S         | swipe down          |
| Pause      | Escape / P            | —                   |
| Confirm    | Enter (title/over)    | tap                 |

- Swipes: directional if displacement ≥ 30 px; otherwise a tap = confirm.
- One input module feeds one intent queue consumed by the game loop; keyboard
  and touch are indistinguishable to the game.

### 1.2 Game rules

- 3 lanes, lane width 2.4 units, player auto-advances (world scrolls toward
  camera; player mesh stays near z = 0).
- **Lane change:** snapped to target lane, damped slide (~0.12 s settle);
  instant and committed on intent (no half-lane states).
- **Jump:** ballistic, gravity 55 u/s², jump velocity 15.1 u/s → ~0.55 s air
  time, ~2.1 u peak height. Not steerable mid-air; lane intent applies
  immediately (player drifts horizontally in air).
- **Slide:** lasts 0.6 s, player collider height drops 1.6 → 0.7, visual
   squash. Pressing jump during a slide ends the slide early (stand up).
- **Speed:** starts 18 u/s, ramps +0.25 u/s per second, caps at 40 u/s
  (~88 s to cap). All spawn/collision math uses current speed.
- **Crash:** hitting any obstacle ends the run (no lives). Landing on top of a
  low barrier is a crash (no parkour) — patterns always leave a dodge lane.
- **Score:** `score = floor(distance) + 10 × coins`. Distance in units.
- **High score:** best score persisted in `localStorage` (`hyper-runner.best`),
  wrapped in try/catch.

### 1.3 World generation (seeded, winnable)

- Rows spawn every 18 world-units at a spawn line z = −120 (fog-hides pop-in).
  Each run gets a fresh `mulberry32` seed, shown in small print on the game
  over screen, so a run can be reproduced by entering it in the console.
- Row = one weighted-random pattern from a curated table:

| Pattern          | Weight | Content                                              | Win condition                 |
|------------------|--------|------------------------------------------------------|-------------------------------|
| barrier-single   | 22     | low barrier (h 1.0) in 1 random lane                 | jump it or dodge              |
| barrier-double   | 16     | low barriers in 2 lanes                              | jump or use the free lane     |
| gate-single      | 18     | overhead gate (gap below h 0.7) in 1 lane            | slide or dodge                |
| gate-double      | 12     | overhead gates in 2 lanes                            | slide or use the free lane    |
| wall-single      | 14     | full-height wall in 1 lane                           | dodge                         |
| wall-double      | 8      | full-height walls in 2 lanes                         | dodge (1 free lane)           |
| coin-line        | 10     | 3–5 coins in one lane (ground arc)                   | collect                       |

- Guaranteed fairness: every row leaves ≥ 1 fully open lane; two consecutive
  rows never force conflicting actions on the same lane at the same arrival
  time (rows are 18 u apart ≥ ~0.45 s apart at max speed; slides last 0.6 s
  only when triggered, and patterns are validated by tests to always be
  winnable via a free lane).
- Coins: coin-line rows + 30 % chance of 2 bonus coins above a barrier lane.

### 1.4 Scoring, HUD & screens

States: `menu → running ⇄ paused → over → menu/running(restart)`.

- **Title:** game logo (a DOM/CSS neon wordmark layered over the canvas —
  chosen over drei Text because troika fetches a font at runtime, violating
  the §1.6 no-network rule), "press Enter / tap to run", control
  list, best score.
- **HUD (during run):** top-left score (big, tabular numerals), top-right
  coins and speed (u/s), subtle "NEW BEST" flare when beaten.
- **Pause:** dim overlay + "paused" + resume/restart hints. `Escape` toggles.
- **Game over:** crash stats (score, coins, distance, best; NEW BEST badge),
  "Enter / tap to retry" → immediate restart with new seed.

### 1.5 Audio (100 % synthesized, zero files)

- Single `AudioContext`, created lazily and resumed on first user gesture.
- **Music:** minor-key arpeggio loop — sawtooth osc → lowpass → master gain,
  16-step sequencer with lookahead scheduling (25 ms interval, 0.1 s lookahead);
  tempo scales mildly with speed (120→150 BPM).
- **SFX:** jump (rising square blip), lane-shift (short filtered noise whoosh),
  coin (two-note triangle ping 880→1320 Hz), crash (noise burst + low sine
  thump), UI confirm (blip).
- Muted-safe: every call try/catch; game logic never depends on audio.

### 1.6 Visual direction

- Night sky: near-black indigo `#070311` background, drei `<Stars>`, magenta
  horizon fog (exponential fog, density ≈ 0.022).
- Ground: dark reflective plane + glowing cyan lane striping (emissive
  instanced bars scrolling with the world), magenta grid horizon lines.
- Player: emissive cyan capsule with white core glow and a small point light;
  squash on slide, stretch on jump apex.
- Obstacles: barriers = magenta emissive boxes with bright edge frame;
  gates = overhead neon frames with a hazard bar; walls = tall violet slabs.
- Coins: spinning emissive yellow octahedrons (drei Instances).
- Post-processing (the "impressive" multiplier): Bloom (luminance-threshold
  ~0.6), subtle ChromaticAberration (±0.0012), Vignette.
- Juice: camera lag + roll on lane change; FOV punch with speed (70°→78°);
  screen shake + brief red flash on crash; pooled particle burst on coin grab.

## 2. Architecture

### 2.1 Stack (versions verified current, Sep 2026)

| Concern        | Choice                            | Version |
|----------------|-----------------------------------|---------|
| Language       | TypeScript (strict)               | ^5.9    |
| UI framework   | React                             | 19.x    |
| 3D binding     | @react-three/fiber                | ^9.7    |
| 3D helpers     | three + @react-three/drei         | 0.185.1 / ^10.7 |
| Post-processing| @react-three/postprocessing       | ^3.1    |
| Game state     | zustand                           | ^5.0    |
| Build/dev      | Vite (react-ts template)          | ^8.2    |
| Tests          | Vitest                            | ^5 (v3 is peer-incompatible with vite 8; verified 5.0.0) |
| Node (dev)     | ≥ 22 (local v26.8.1)              |         |

Rationale: declarative JSX scenes + drei + postprocessing carry ~80 % of the
"wow" surface (rendering, stars, text, instances, bloom). Hand-written code is
limited to game logic (rules, spawning, collision, input, audio), which is
small, pure, and testable. No physics engine: runner needs only AABB checks.

### 2.2 Data flow

```
input.ts ──intent queue──▶ GameLoop (single useFrame)
                              │ mutates (60 fps, no React)
                              ▼
                    game/runtime.ts (mutable world)
                     player, entities, speed, seed, timers
                              │ syncs ~4 Hz + on events
                              ▼
                      zustand store (UI state only)
                       phase, score, coins, speed, best
                              ▼
                    ui/* (Title, HUD, Pause, GameOver)
three/* components read runtime.ts directly in useFrame
```

- **Rule:** React re-renders only on state transitions and HUD updates
  (~4 Hz). All per-frame reads/writes bypass React entirely.

### 2.3 Modules (each one clear purpose, testable in isolation)

`src/game/` — pure logic, no React/three imports where possible:

| Module        | Responsibility |
|---------------|----------------|
| `constants.ts`| all tuning numbers (speeds, gravity, lane x positions, spawn distances, colors) |
| `rng.ts`      | mulberry32 + seed formatting |
| `patterns.ts` | weighted pattern table → row descriptors; exports `isWinnable(row)` |
| `collision.ts`| AABB helpers; `checkRun(world): CrashEvent | CoinEvents | null` |
| `runtime.ts`  | mutable world singleton: spawn rows, advance, jump/slide integration, reset |
| `store.ts`    | zustand: phase machine, score/coins/best, localStorage persistence |
| `input.ts`    | keydown + touch swipe → typed intent queue |
| `audio.ts`    | AudioContext lifecycle, music sequencer, SFX |

`src/three/` — rendering:

| Module        | Responsibility |
|---------------|----------------|
| `Scene.tsx`   | Canvas contents: lights, fog, stars, ground, `<Effects>` |
| `GameLoop.tsx`| the only `useFrame` game logic; calls runtime.step(dt), feeds collisions → store/audio |
| `Player.tsx`  | player mesh, reads runtime pose, squash/stretch |
| `Track.tsx`   | scrolling lane stripes (drei Instances) |
| `Obstacles.tsx` | pooled obstacle meshes bound to runtime entities |
| `Coins.tsx`   | spinning coin Instances bound to runtime entities |
| `Particles.tsx` | pooled coin-burst points |
| `CameraRig.tsx` | follow, roll, FOV punch, crash shake |
| `Effects.tsx` | EffectComposer: Bloom, ChromaticAberration, Vignette |

`src/ui/` — `TitleScreen.tsx`, `Hud.tsx`, `PauseOverlay.tsx`,
`GameOverScreen.tsx`, styled by `src/ui.css` (neon CSS: text-shadow glows,
backdrop blur panels; `font-variant-numeric: tabular-nums`).

### 2.4 Error handling

- No WebGL → `<Canvas>` error boundary shows a friendly fallback card.
- AudioContext creation/resume failure → silently continues silent.
- localStorage failures → high score session-only, no throw.
- Fixed-step loop with `dt` clamped to 50 ms → alt-tab doesn't teleport the
  player into a wall.

### 2.5 Testing (vitest, pure modules only)

- `rng` — deterministic sequence for fixed seed.
- `patterns` — every pattern winnable (≥ 1 open lane); generator never emits
  a sequence where all lanes are blocked within one row; distribution sanity.
- `collision` — matrix: barrier hit vs jump clearance vs slide; gate hit vs
  slide clear vs jump fail; lane overlap boundaries; coin radius pickup.
- Manual playtest checklist (in PLAN.md) for feel: responsiveness, readability
  at max speed, crash fairness.

### 2.6 Performance budget

Target 60 fps on Apple Silicon / integrated GPUs: < 150 draw calls (instanced
stripes/coins/obstacles), no per-frame allocations in loop (object pools),
shadow maps disabled (emissive look doesn't need them), bloom at
`resolutionScale 0.5`.

## 3. Definition of done (acceptance)

1. `npm install && npm run dev` → title screen in < 2 s, no console errors.
2. Keyboard **and** touch both fully playable end-to-end on desktop + phone.
3. Crashes end the run with shake/flash/SFX; instant restart works.
4. Score/coins/speed visible; high score survives reload.
5. Music + SFX audible; tabbing away and back doesn't break the run.
6. `npm run build` and `npm run preview` work; `npm test` green.
7. Looks screenshot-worthy: neon bloom, stars, fog horizon, particles.
