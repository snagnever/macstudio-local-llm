# Hyper Runner — SPEC

Version 1.0. This file is the source of truth for what the game must do.
`PLAN.md` holds the build plan; `AGENTS.md` maps the repository.

## 1. Product

An endless 3D runner that boots in the browser with `npm run dev`. The
player drives a neon ship down a three-lane synthwave grid, dodges
obstacles, collects coins, and chases a high score. Everything renders
procedurally: no external models, textures, sounds, or fonts load at
runtime.

Targets: 60 fps on an Apple Silicon laptop, playable on a phone with
swipes, first run within five seconds of opening the page.

## 2. Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Engine | Babylon.js 9 (`@babylonjs/core` only) | All-in-one scene graph, instancing, glow; no other runtime dependency |
| Bundler | Vite 7 | Instant dev server, `base: "./"` build |
| Language | TypeScript 5.9, `strict` | Game logic is numeric; strict catches errors early |
| Audio | Raw WebAudio API | Precise scheduling; Babylon audio module not needed |
| HUD | Plain DOM + CSS over the canvas | Cheaper than a Babylon GUI layer |

No physics engine. Collision is hand-written AABB logic (section 5).

## 3. Game loop and states

Three states: `menu`, `playing`, `gameover`.

- **menu** — attract mode. The world scrolls at `menuSpeed` (8 u/s), the
  track keeps generating, no collisions. Title and start button show.
- **playing** — full simulation (section 4). Collisions live.
- **gameover** — world frozen (speed 0). Final score panel shows. A
  0.6 s gate ignores restart inputs so the crash button press cannot
  skip the panel.

Any key/button gesture in `menu` or `gameover` (Enter, Space, tap, the
button) starts a run. `M` toggles mute in every state.

## 4. Mechanics

### 4.1 Movement

- Three lanes, `laneWidth` 2.6. The lane x target is
  `(lane - 1) * 2.6`. The ship damps toward it with `laneSwitchK` 16
  (exponential smoothing, frame-rate independent).
- Jump: `vy = 13`, gravity `55` → apex ≈ 1.54 units, hang ≈ 0.47 s.
  Clears a low hurdle (top 0.9).
- Coyote time 0.1 s and jump buffering 0.12 s keep takeoff forgiving.
  A buffered jump fires on landing.
- Slide: lasts 0.5 s, box height drops 1.7 → 0.8. Passes under a high
  bar (bottom 1.52). Pressing slide in the air adds fast-fall
  (`vy` clamped to -20).
- Ramp: hitting a ramp from the ground launches at `vy = 16` → apex
  ≈ 2.32, clears a high bar (top 2.08).

### 4.2 World motion

The player stays at z = 0. Entities spawn at z = 250 and travel toward
the player on -Z at the run speed. They despawn at z < -14. Track
segments recycle behind the camera.

### 4.3 Speed and difficulty

Speed runs from 14 to 28 over a 90 s time constant
(`d = 1 - exp(-elapsed/90)`, capped at 0.95). Boost adds +8 while
active. Music BPM tracks difficulty from 96 to 144.

### 4.4 Entities

| Kind | Size / position | Pass with |
| --- | --- | --- |
| low hurdle | orange box, top y 0.9 | jump or ramp |
| high bar | pink bar, slab 1.52–2.08 | slide, or fly over on a ramp |
| coin | gold torus at y ≈ 1.05, bobs and spins | any path through it |
| ramp | teal wedge, toe at ground | drives the launch |
| shield / magnet / boost gem | 4-sided crystal at y ≈ 1.15 | touch it |

A power-up lasts 6 s. Shield absorbs one hit (the obstacle is destroyed;
the run continues). Magnet drags nearby coins (radius 6) into the
player column. Boost adds speed and doubles score gain; the camera FOV
widens.

### 4.5 Score

- Distance: `speed * dt * mult * (boost ? 2 : 1)`.
- Coin: +25 × mult, and combo mult `1 + min(combo, 20) * 0.25` (max 6×).
  The combo decays 4 s after the last coin.
- The best score persists in `localStorage` under `hyperRunner.best`.
  Mute state persists under `hyperRunner.muted`.

### 4.6 Track generation guarantees

Segments are 20 long, three 6-long slots, 12 segments alive.
- An obstacle never blocks all three lanes. Doubles use lane
  `(first + 1 + rand(2)) % 3`, which always differs from `first`.
- At most one obstacle event per slot; ramps reserve two clear slots
  behind them.
- The first two segments of a run are gentle (coins only).
- At `d > 0.55` a 35% double-obstacle roll activates.

## 5. Collision rules

Player box: half-width 0.4, half-depth 0.8, height 1.7 standing / 0.8
sliding. Overlap is AABB against each entity slab, with a 0.8× width
credit on obstacles and a +0.4 depth credit on pickups. Pickups compare
the entity y against the player center (tolerance `pickupDy` 1.15).
Hits defer one step: the collision walker records the entity and the
game resolves shield-or-crash after the walk, because the walker is
iterating the same array.

## 6. Controls

| Action | Keyboard | Touch |
| --- | --- | --- |
| move left | ← / A | swipe left (≥30 px) |
| move right | → / D | swipe right |
| jump | ↑ / W / Space | swipe up |
| slide | ↓ / S | swipe down |
| start / restart | Enter (also Space/tap) | tap |
| mute | M | AUDIO button |

Key repeats are ignored. A swipe shorter than 30 px is a tap.

## 7. Look

Synthwave night. Clear color (0.02, 0, 0.05). One unlit emissive
material per mesh kind; all lighting is emissive plus one `GlowLayer`
(0.6 intensity, half resolution). Linear fog (color 0.12/0.01/0.16,
80→240) hides the spawn line.

- Ground: custom `ShaderMaterial` (inline GLSL) draws scrolling cyan
  grid lines; line width grows with distance to kill shimmer; the fog
  color is mixed in by hand because shader materials ignore scene fog.
- Sky: dark sphere with a shader starfield plus a horizon gradient;
  a billboard "sun" plane with horizontal slit bands.
- Player: cyan/magenta box ship with underglow; a transparent sphere
  shows the shield.
- Camera: fixed-height follow camera at (0, 4.2, -8), damped x follow,
  roll from lane speed, shake impulses on crash/shield break, FOV kick
  on boost.

Perf policy: hardware scaling caps DPR at 1.5; all entity meshes are
`InstancedMesh` from pools created at boot; the frame loop allocates
nothing; the glow layer auto-drops to 0.2 intensity after 2 s below
45 fps.

## 8. Audio

Fully synthesized WebAudio, unlocked on the first user gesture.
Music: 16-step lookahead scheduler (25 ms tick, 0.12 s horizon) — kick,
snare, hats, saw bass, triangle arp over an Am–F–C–G loop, tempo tied to
difficulty. SFX: coin (rising square, pitch climbs with combo), jump,
land, slide noise, pickup, shield break, crash, game over, UI blip.
A compressor sits on the master bus.

## 9. HUD (DOM contract)

`index.html` must expose exactly these hooks or `hud.ts` throws at boot:
`#ui[data-state]`, `#score`, `#combo`, `#best`, `.coin-count`,
`#bar-shield`, `#bar-magnet`, `#bar-boost`, `#final-score`,
`#final-best`, `#new-record`, `#btn-mute`, `#btn-start`,
`#btn-restart`. `#lost` shows on WebGL context loss. The HUD polls at
125 ms; nothing per-frame touches the DOM.

## 10. Acceptance criteria

1. `npm run dev` serves the game; `npm run build` type-checks and
   bundles with zero errors.
2. Menu → run → crash → game over → restart works by keyboard and by
   touch.
3. Every obstacle is passable; no spawn pattern can force a death.
4. Coins count with combo multiplier; best score survives a reload.
5. All three power-ups visibly and audibly work; shield consumes on one
   hit.
6. No external asset requests beyond engine/bundle files.
7. Runtime feel items (60 fps, visual quality) require a real browser
   session and are not claimable from CI.
