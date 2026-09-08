# Hyper Runner — Plan

## Stack (versions verified on npm 2026-09-06)
- Vite 8 + React 19 + TypeScript
- three 0.185 · @react-three/fiber 9.7 · @react-three/drei 10.7
- @react-three/rapier 2.2 (rapier3d-compat WASM) — physics + collision events
- @react-three/postprocessing 3.1 — Bloom + ChromaticAberration
- zustand 5 — game state (status, score, speed, lane, flags)
- @use-gesture/react — swipe gestures (keyboard handled by small custom hook)

Rationale: pmndrs ecosystem = declarative scene graph, WASM physics off-the-shelf,
zero hand-written engine code; procedural assets = zero downloads.

## Architecture
State (zustand)  →  R3F components read/mutate refs in useFrame (no re-render churn)
Events (input)   →  store intents → Player rigid-body API (impulses/kinematics)
Collisions       →  rapier events → store actions (crash, coin+, respawn)

Entities recycle: world scrolls toward player at store.speed; each pool slot,
once z < playerZ − 15, respawns ahead (z += poolLength) with randomized lane/type.

## Files
- src/store.ts            zustand: status|score|best|coins|speed|lane, actions,
                          localStorage best, reset()
- src/sfx.ts              WebAudio oscillator beeps (~40 lines), mute flag
- src/hooks/useControls.ts keyboard listeners → store intents (lane±, jump, slide)
- src/components/Player.tsx        RigidBody(dynamic, lockedRot, z fixed) +
                          CapsuleCollider ⇄ CuboidCollider swap for slide;
                          useFrame: x lerp to lane, jump impulse on ground
- src/components/World.tsx         fog, drei Grid, Stars, sun mesh, ground
                          fixed collider, lane guides
- src/components/Pools.tsx         ObstaclePool (20 kinematic bodies,
                          contact events) + CoinPool (30 sensors, intersection
                          events) with recycling logic
- src/components/Camera.tsx        chase lerp + speed FOV kick
- src/components/Effects.tsx       Bloom, ChromaticAberration, Vignette
- src/components/Hud.tsx           HTML overlay: score, screens, touch hint
- src/App.tsx              Canvas + Physics + Suspense + Hud + gesture wiring
- src/index.css            neon overlay styles

## Implementation steps
1. Scaffold Vite react-ts, install deps            [DONE pre-plan]
2. store.ts + sfx.ts + useControls.ts
3. Player.tsx (movement, jump, slide collider swap)
4. World.tsx (grid, sun, stars, ground collider)
5. Pools.tsx (spawn/recycle, collision→crash, intersection→coin)
6. Camera.tsx + Effects.tsx + Hud.tsx + App.tsx wiring
7. Verify: tsc -b && vite build clean; dev-server smoke test
8. Polish pass: tuning constants (jump force, ramp curve, colors)

## Risks / mitigations
- Rapier WASM async init → <Physics> + Suspense handles it.
- Slide collider swap mid-physics → conditional collider child (react-three-rapier
  lifecycle-safe); if flaky, fallback: single capsule + bar-height filtering.
- npm scripts blocked by security policy (only fsevents pending approval —
  optional macOS watcher, ignore) → verify esbuild/vite binary works at step 7.
