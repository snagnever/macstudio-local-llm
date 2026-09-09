# SPEC — Hyper Runner

Hyper Runner is a browser 3D endless runner demo. The player controls a robot that runs down a
neon tunnel, dodges obstacles, and collects coins. The run ends on the first crash.

This document defines what the game is. `PLAN.md` defines how it gets built.

## 1. Goals

- Deliver a complete, visually impressive 3D demo that runs in any modern browser.
- Keep new code small by using existing libraries for rendering, animation, effects, and physics.
- Ship as a static build with no server and no backend.

## 2. Non-goals

- No multiplayer, no accounts, no network calls at runtime.
- No power-ups. No magnet, shield, or speed boost.
- No level editor and no procedural art pipeline.
- No WebGPU renderer. The demo targets WebGL 2.

## 3. Stack

| Package | Version | Role |
| --- | --- | --- |
| `three` | 0.185.1 | Renderer |
| `@react-three/fiber` | 9.7.0 | Declarative scene graph |
| `@react-three/drei` | 10.7.8 | `useGLTF`, `useAnimations`, instancing helpers |
| `@react-three/postprocessing` | 3.1.1 | Bloom, chromatic aberration, vignette, SMAA |
| `postprocessing` | 6.39.4 | Effect backend |
| `@react-three/rapier` | 2.2.0 | Crash debris only |
| `zustand` | 5.0.15 | Game phase and score store |
| `react` / `react-dom` | 19.2.8 | User interface overlay |
| `vite` | 8.2.2 | Development server and build |
| `@vitejs/plugin-react` | 6.1.1 | React transform |
| `typescript` | 7.0.2 | Types and `tsc --noEmit` |

All versions were read from npm on 2026-09-06. Their peer ranges are mutually compatible on
React 19.2.

## 4. Art direction

A neon cyber tunnel. The tunnel is dark. Light comes from emissive strips on the ribs, the floor
seams, the obstacles, and the coins. Exponential fog hides the spawn distance. Bloom, chromatic
aberration, and a vignette finish the image. Speed lines stream past the camera and grow denser
as the run gets faster.

## 5. Gameplay

### 5.1 Track

Three lanes at x = -2.4, 0, and 2.4. The player stays at z = 0. The track moves toward the player,
so distance is the integral of speed.

A run opens with 55 m of clear track. Beyond that the spawner keeps the corridor filled out to
190 m ahead. Chunk timings are converted to metres with the speed the run will have reached by
the time the player arrives, not the speed at the moment of spawning, so an authored 0.9 s gap
is still 0.9 s when it matters.

### 5.2 Speed

Speed starts at 14 m/s. It gains 0.35 m/s per second of run time. It caps at 42 m/s. Camera field
of view widens with speed to sell the acceleration.

### 5.3 Actions

| Action | Keys | Swipe | Timing |
| --- | --- | --- | --- |
| Change lane | Arrow Left / Right, A / D | Left / right | 0.12 s ease |
| Jump | Arrow Up, W, Space | Up | 0.62 s arc, 2.2 m apex |
| Slide | Arrow Down, S | Down | 0.55 s, collider height halved |

The input buffer is 0.15 s: a jump or slide pressed while the player is still airborne fires
the moment they land. There is no coyote time, because a flat track has no ledge to leave.

### 5.4 Obstacles

| Type | Required action |
| --- | --- |
| Ground barrier | Jump |
| Overhead beam | Slide |
| Full-lane wall | Change lane |
| Drifting drone | Change lane, timed against its motion |

Obstacles arrive as hand-authored chunks. Every chunk keeps at least one lane passable. The
spawner picks chunks from a weighted table whose weights shift with the difficulty curve.

### 5.5 Coins

Coins spawn in arcs of five. Some arcs sit on the jump path above a ground barrier, so a clean
jump is also the greedy line.

### 5.6 Scoring

Score is distance in metres plus 10 points per coin. The best score is stored in `localStorage`
under the key `hyper-runner.best` and survives a reload.

### 5.7 Collision

An axis-aligned bounding box test between the player box and each obstacle box. It lives in pure
code. The physics engine is never consulted during play.

The collision box is narrower than the mesh on purpose. An obstacle is drawn 2.0 m wide but
collides at 1.56 m, and the player is drawn at model size but collides at 0.6 m. Without that
margin a lane change still in flight clips the neighbouring lane and every run ends the same way.

### 5.8 Phases

`menu -> playing <-> paused -> dead -> menu | playing`

Space starts a run. Escape or P pauses. Space restarts from the game over screen.

## 6. Character

`public/models/robot.glb` is the `RobotExpressive` model from the three.js examples: CC0, by
Tomás Laulhé, modified by Don McCurdy. It is committed to the repository, so the demo makes no
network call at runtime.

The animation clips used are Running, Jump, and Death. Clip names are resolved through a lookup
table with a fallback to the first clip, so a renamed clip cannot crash the demo.

## 7. Physics

The Rapier provider mounts only in the `dead` phase. A crash spawns about 14 dynamic boxes at the
impact point. They simulate for 2.5 s during the death camera orbit, then unmount. This keeps a
solver out of the gameplay path.

## 8. Audio

Every sound is generated in Web Audio. There are no audio files. Jump, coin, crash, and a looping
music bed are built from oscillator and gain nodes. The context is created on the first user
gesture, as browsers require. A mute toggle sits in the heads-up display.

## 9. Performance

- Instanced meshes for tunnel ribs, floor tiles, coins, speed lines, and each obstacle type.
- Objects are pooled and recycled once they pass 8 m behind the player. Nothing is allocated per frame.
- Device pixel ratio is clamped to the range 1 to 2.
- If the frame rate stays under 45 for 2 s, quality drops: bloom off, pixel ratio 1.
- Target: 60 frames per second on a 2020 laptop integrated graphics processor.

## 10. Mobile

A full-screen touch layer reads swipes with a 30 px threshold. The heads-up display scales down
and the menus stay legible at a 390x844 viewport.

## 11. Acceptance criteria

1. `npx tsc --noEmit` reports no error.
2. `npm run build` succeeds and `npm run preview` serves the demo.
3. The browser console shows no error. Two deprecation warnings do appear, both from library
   internals rather than this code: `THREE.Clock` from React Three Fiber, and an initialisation
   notice from the Rapier WebAssembly module.
4. A run can be started, paused, resumed, crashed, and restarted.
5. Jumping clears a barrier, sliding clears a beam, and a lane change clears a wall.
6. A crash spawns debris and ends the run.
7. The best score survives a page reload.
8. Swipe controls work at a 390x844 viewport.

Two items are not verified by the checks above. Audible output cannot be confirmed from a
headless browser, so only the absence of audio errors was checked. The quality auto-degrade
never fired during testing, because the frame rate never dropped far enough to trigger it.
