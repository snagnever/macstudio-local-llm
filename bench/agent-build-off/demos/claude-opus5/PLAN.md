# PLAN — Hyper Runner

How the game in `SPEC.md` gets built. Each step ends with a check you can run.

## Layout

Game rules live in pure TypeScript that imports neither `three` nor React. Rendering reads that
state each frame. This keeps the rules readable and lets you change tuning without touching the
scene.

```
src/
  game/         pure logic, no three, no react
    config.ts       lanes, speeds, timings, spawn weights - every tunable in one file
    rng.ts          seeded mulberry32, so a seed replays the same track
    chunks.ts       hand-authored obstacle patterns, each with a guaranteed passable lane
    spawner.ts      streams chunks ahead of the player, recycles behind
    player.ts       lane lerp, jump arc, slide, input buffer
    collision.ts    axis-aligned bounding box overlap
    scoring.ts      distance, coins, difficulty curve, localStorage best
  state/store.ts    zustand: phase, score, coins, best, settings, quality
  input/            keyboard map and swipe layer -> one Intent type
  audio/synth.ts    Web Audio nodes for jump, coin, crash, and the music bed
  scene/            Tunnel, Player, Obstacles, Coins, Debris, Effects, CameraRig
  ui/               Menu, Hud, PauseOverlay, GameOver
  App.tsx, main.tsx
public/models/robot.glb
```

## Step 1 — Docs and scaffold

Write `SPEC.md`, `PLAN.md`, and `AGENTS.md`. Run `git init` and add `.gitignore`. Create the Vite,
React, and TypeScript project by hand, then install the packages listed in `SPEC.md` at their
pinned versions. Download `public/models/robot.glb`.

Check: `npm run dev` serves a page with no console error.

## Step 2 — Scene shell

Canvas, camera rig, neon tunnel from instanced ribs and floor tiles, exponential fog, and the
effect chain.

Check: the tunnel scrolls at a fixed speed and holds 60 frames per second.

## Step 3 — Player

Load the model, map the Running, Jump, and Death clips, add keyboard input, lane change, jump,
and slide.

Check: all three moves read correctly on screen.

## Step 4 — Track generation

`config.ts`, `rng.ts`, `chunks.ts`, and `spawner.ts`, plus instanced obstacles and coins with
pooling.

Check: a two-minute run never spawns a chunk without a passable lane.

## Step 5 — Rules and interface

Collision, scoring, the difficulty curve, the phase machine, and the overlay for menu, heads-up
display, pause, and game over.

Check: a crash ends the run and the best score survives a page reload.

## Step 6 — Juice

Rapier debris on crash, synthesized audio, screen shake, speed lines, field of view kick, and the
swipe layer.

Check: the demo plays at a 390x844 viewport.

## Step 7 — Ship

Quality auto-degrade, then the build.

Check: `npx tsc --noEmit`, `npm run build`, and `npm run preview` all succeed.

## Development hook

In a development build only, `window.hyper` exposes `{ world, startRun, stepWorld }`. It lets you
drive the simulation from the browser console with no renderer involved, which is how the
collision rules and the difficulty curve were checked:

```js
const { world, startRun, stepWorld } = window.hyper
startRun(12345)
for (let i = 0; i < 3600 && world.phase === 'playing'; i++) stepWorld(1 / 60)
world.phase // 'dead'
```

The production build does not define it.

## Verification

Run every acceptance criterion in `SPEC.md` section 11. Load the preview build in a browser,
screenshot the menu and a live run, and read the console to confirm it is clean.
