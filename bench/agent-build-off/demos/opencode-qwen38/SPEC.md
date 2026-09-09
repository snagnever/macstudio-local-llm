# Hyper Runner — Spec

3D endless-runner demo running in the browser. Neon synthwave/outrun aesthetic,
built almost entirely from procedural primitives + battle-tested libraries.

## Core loop
1. Player auto-runs forward (world scrolls toward a fixed player).
2. Player switches between 3 lanes, jumps over low obstacles, slides under
   overhead bars, collects coins.
3. Speed ramps up with distance. Collision with an obstacle = game over.
4. Game-over screen shows score + best score (localStorage), restart resets.

## Mechanics
- Lanes: x ∈ {−2, 0, 2}; lane change = smooth damped lateral movement.
- Jump: upward impulse (physics gravity brings player down); ~1.1 s airtime.
- Slide: player collider shrinks for 0.6 s (duck under bars, ~0.9 s cooldown).
- Coins: +10 each, sensor collisions, respawn via recycling pool.
- Obstacles: 2 types — LOW block (jump or dodge) and HIGH bar (slide under).
- Difficulty: speed 12 → 30 units/s over ~90 s; spawn gap tightens with speed.
- Score: distance (1/unit) + coins ×10. Best score persisted.

## Controls
- Keyboard: ← → / A D (lane), ↑ / W / Space (jump), ↓ / S (slide),
  R (restart), Enter (start/restart), M (mute).
- Touch: swipe left/right/up/down anywhere on screen (@use-gesture/react).

## Visual direction (no downloaded assets)
- Dark fog (#05010f), drei infinite neon Grid floor, drei Stars sky.
- Outrun sun: large emissive semicircle on the horizon.
- Neon emissive primitives: player (capsule), obstacles (boxes), coins (torus).
- Bloom postprocessing (@react-three/postprocessing); light chromatic aberration.
- Chase camera: lerps to player x, subtle speed FOV kick.
- HUD: neon CSS overlay — score/coins/speed, start/game-over screens.
- Minimal WebAudio SFX (oscillator beeps): coin, jump, slide, crash. M to mute.

## Performance / correctness requirements
- Obstacles + coins use fixed recycling pools (kinematic bodies, setNextKinematic
  Translation) — no runtime mounts after start, stable 60 fps.
- Rapier collision events drive game logic (contacts = crash, sensors = coins).
- Desktop + mobile responsive; page never scrolls; works on iOS Safari.

## Out of scope
Power-ups, sound assets files, downloaded GLTF models, multiplayer, level editor.
