# Hyper Runner — PLAN

Build order for `SPEC.md`. Tick a box only when its verification step
passed. Items marked **[browser]** need a human browser session; they
are not verified from CI.

## M0 — Research and decisions

- [x] Brave-search current Babylon.js/Vite best practices.
- [x] Fix stack: Babylon 9 + Vite 7 + TS strict, procedural assets,
  synthwave theme, full mechanics (user-approved).

## M1 — Scaffold

- [x] `package.json`, `tsconfig.json` (strict, ES2022, bundler
  resolution), `vite.config.ts` (`base: "./"`), `.gitignore`.
- [x] `src/config.ts`: frozen tuning contract (`CFG`).
- [x] `npm install` resolves with `@babylonjs/core ^9`, vite ^7,
  typescript ^5.9.

## M2 — Core types and input

- [x] `src/state.ts`: `GameStateName`, `PowerupKind`.
- [x] `src/events.ts`: typed synchronous `EventBus`.
- [x] `src/input.ts`: keyboard map, swipe detection, repeat guard.
- [x] `src/player.ts`: lanes, damped interp, jump/coyote/buffer,
  slide/fast-fall; pure TS, no Babylon imports (unit-testable).

## M3 — World rendering

- [x] `src/world.ts`: scrolling grid `ShaderMaterial` (inline GLSL,
  CPU phase), starfield sky, sun plane, rails, fog, `GlowLayer`,
  `degradeGlow()`.
- [x] No `fwidth` (analytic line width); manual fog mix in the shader.

## M4 — Entities

- [x] `src/factory.ts`: masters + pooled `InstancedMesh`, per-kind free
  lists, spawn metrics table, scroll/animate/despawn update, ship
  builder, shield bubble.
- [x] No mesh is created after boot.

## M5 — Track generation

- [x] `src/track.ts`: segment cursor, recycle at -20, slot generator,
  ramp/obstacle/power-up/coin-line rolls, difficulty scaling,
  one-lane-always-open rule, ramp clearance rule, gentle first two
  segments.
- [x] Geometric checks on paper: jump apex 1.54 > low top 0.9; slide
  height 0.8 < bar bottom 1.52; ramp apex 2.32 > bar top 2.08.

## M6 — Collision and scoring

- [x] `src/collision.ts`: AABB slab tests, pickups release, hits defer
  to the game.
- [x] `src/score.ts`: distance + combo multiplier, localStorage best.
- [x] `src/powerups.ts`: 6 s timers, shield consume.

## M7 — Audio

- [x] `src/audio.ts`: gesture-gated context, compressor master,
  16-step music scheduler with BPM ramp, all SFX synthesized, no
  asset files.

## M8 — HUD and screens

- [x] `index.html` + `hud.css`: menu / playing HUD / game over /
  context-lost overlays; all ids from the SPEC §9 DOM contract.
- [x] `src/hud.ts`: 125 ms poller, state switching, mute label, bars,
  button blur so Enter cannot double-fire.

## M9 — Integration

- [x] `src/game.ts`: state machine, frame order (world → player →
  collide → draw), deferred hit resolution, restart gate, auto glow
  degrade under 45 fps.
- [x] `src/main.ts`: engine boot, DPR cap, resize, context-loss
  overlay.
- [x] `tsc --noEmit && vite build` clean.

## Post-build verification

- [x] `npm install` completes (see M1; run at integration time).
- [ ] **[browser]** 60 fps on Apple Silicon laptop; glow degrades if
  not.
- [ ] **[browser]** Touch play: swipes map correctly, no double-fire.
- [ ] **[browser]** Audio unlocks on first gesture; mute persists.
- [ ] **[browser]** Long run (3 min+) reaches max speed without pool
  exhaustion.
- [ ] **[browser]** `npm run dev` first paint under 5 s.
