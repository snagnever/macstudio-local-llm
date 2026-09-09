# AGENTS.md

## What this repo is

Hyper Runner: a browser 3D endless-runner demo. Neon synthwave grid,
three-lane weaving, jump/slide, coins with combo multiplier, three
power-ups, ramps, difficulty ramp, persistent high score. All art and
audio are procedural — the repo ships zero binary assets.

- Read `SPEC.md` for required behavior and tuning values.
- Read `PLAN.md` for build milestones and what is verified versus
  browser-pending.
- Change a gameplay number in `src/config.ts` (`CFG`), not in call
  sites.

## Commands

```bash
npm install        # once
npm run dev        # Vite dev server, opens the game
npm run build      # tsc --noEmit && vite build
npm run preview    # serve the production build
```

There is no test runner. Verification today is the type-check inside
`npm run build` plus a manual browser session.

## Module map

Entry: `index.html` → `src/main.ts` → `src/game.ts`.

| File | Role |
| --- | --- |
| `src/config.ts` | `CFG`: every tunable number. Frozen contract. |
| `src/state.ts` | `GameStateName`, `PowerupKind` unions. |
| `src/events.ts` | Typed synchronous `EventBus`. |
| `src/main.ts` | Engine boot, DPR cap, resize, context-loss. |
| `src/game.ts` | State machine, frame order, hit resolution. |
| `src/player.ts` | Pure-TS player physics: lanes, jump, slide. |
| `src/input.ts` | Keyboard + touch swipes → named actions. |
| `src/cameraRig.ts` | Follow camera, shake, roll, FOV kick. |
| `src/world.ts` | Grid/sky/sun shaders, fog, glow layer. |
| `src/factory.ts` | Mesh pools, entity struct, pooled spawn/release. |
| `src/track.ts` | Procedural segment generator, passability rules. |
| `src/collision.ts` | AABB slab tests; emits game events. |
| `src/score.ts` | Distance + combo, localStorage best. |
| `src/powerups.ts` | Shield/magnet/boost timers. |
| `src/audio.ts` | WebAudio music scheduler + synthesized SFX. |
| `src/hud.ts` | DOM HUD poller (ids defined in `index.html`). |
| `hud.css` | All HUD styling. |

## Conventions and traps

- **Motion direction**: the player is fixed at z = 0; entities travel
  toward **-Z**. Do not flip this without rewriting track, factory, and
  camera code together.
- **Pools**: create no mesh after boot. Spawn with
  `factory.spawn(...)`, free with `release`/`releaseAt`.
- **Array iteration**: `factory.actives` is swap-removed. Never hold an
  index across a `releaseAt`. Hits are deferred one step in `game.ts`
  for exactly this reason.
- **ShaderMaterial**: GLSL is inline in `src/world.ts`. Scene fog does
  not apply to it; the fog mix is manual. `fwidth` is deliberately
  unused (extension risk); line width is analytic.
- **DOM contract**: `src/hud.ts` throws if an id from SPEC §9 is
  missing from `index.html`. Keep both files in sync.
- **Audio**: nothing may call `AudioContext` before `audio.unlock()`
  runs from a user gesture. All SFX are no-ops before that.
- `@babylonjs/core` deep imports are forbidden; import from the package
  root so tree-shaking stays predictable.
- Numbers that gameplay depends on belong in `CFG`; add them to
  `SPEC.md` § tuning surfaces at the same time.
