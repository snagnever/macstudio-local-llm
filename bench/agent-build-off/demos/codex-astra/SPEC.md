# Hyper Runner Specification

Status: Implemented after user approval. See docs/VERIFICATION.md for verification results.

Research date: 2026-09-06, America/Sao_Paulo.

## 1. Objective

Build a complete, playable 3D endless runner for browsers.
Use existing engine modules and licensed assets to reduce implementation time.
Deliver a polished local demo with a reproducible production build.

The player controls a robot on an elevated track through a futuristic city.
The player changes lanes, jumps, slides, and collects energy cells.
Speed increases until a collision ends the run.
The player can immediately restart and improve a locally stored best score.

## 2. Decisions and assumptions

| Decision | Selection | Basis |
| --- | --- | --- |
| Platform | Browser; desktop first; mobile controls | User confirmed |
| Structure | Endless runner; increasing difficulty; local best score | User confirmed |
| Theme | Futuristic city with an animated robot | Recommended default after the user requested continuation |
| Camera | Third-person chase camera | Implementation choice for obstacle visibility |
| Movement | Three lanes, jump, slide | Approved design |
| Assets | Free assets with redistribution rights | Implementation choice for a self-contained demo |
| Delivery | Local development server and static build | Approved design; public deployment is not required |
| Interface language | English | User's language |

The user approves this design and its defaults with the instruction “implement”.

## 3. Definition of complete

The demo includes the complete start, play, pause, game-over, and restart flow.
It includes visible character animation, a coherent environment, responsive controls, sound, and score persistence.
It runs from a documented command without external service credentials.
All required assets ship locally with their license records.

The first release excludes multiplayer, accounts, online leaderboards, purchases, level editors, and native application packaging.
It excludes combat, branching tracks, full rigid-body physics, and character customization.
One environment receives visual variation through scenery and lighting changes.

## 4. Stack selection

| Approach | Reuse | Additional work | Decision |
| --- | --- | --- | --- |
| Babylon.js with TypeScript and Vite | Renderer, animation, asset loading, particles, audio, bounds, instances | Runner rules and HTML interface | Selected |
| React Three Fiber with Drei | Declarative scene components and visual helpers | Additional game systems and React lifecycle integration | Viable alternative |
| Plain Three.js with TypeScript | Rendering and loaders | More manual integration of game systems | Not selected |

Babylon.js provides the required game features in one ecosystem.
This reduces integration work for a small demo.
HTML and CSS provide accessible menus without another interface framework.
The game uses WebGL 2 for the first release.
WebGPU is outside this demo's scope.

### Dependency baseline

These versions come from npm metadata checked during planning.

| Dependency | Version | Responsibility |
| --- | --- | --- |
| `@babylonjs/core` | `9.25.0` | Rendering, scene objects, animation, particles, audio, math |
| `@babylonjs/loaders` | `9.25.0` | Load glTF assets |
| `vite` | `8.2.2` | Development server and production bundle |
| `typescript` | `7.0.2` | Static type checks |
| `vitest` | `5.0.0` | Simulation and persistence tests |
| `@playwright/test` | `1.63.0` | Browser tests and screenshots |

Use Node.js 22.12 or later within a supported major: 22, 24, or 26.
The current workspace provides Node.js 26.8.1 and npm 11.19.0.
Pin direct dependency versions and retain `package-lock.json`.
Keep Babylon.js core and loaders on the same version.
Verify package compatibility during installation before accepting the baseline.
Use the pinned Playwright version for browser tests.

Import the required Babylon.js modules explicitly.
Register the glTF loader once.
Do not introduce an entity-component framework, physics engine, or state library for this scope.
Use Babylon.js APIs for rendering, animation, particles, audio, and bounding-box overlap.

## 5. Player flow

| State | Visible content | Allowed transitions |
| --- | --- | --- |
| Loading | Progress and loading status | Ready or load error |
| Load error | Failure message and retry button | Loading |
| Ready | Animated scene, title, controls, best score, Start button | Running |
| Running | Score, distance, speed, shield status, pause and sound buttons | Paused or game over |
| Paused | Resume, restart, sound, and quality controls | Running or ready |
| Game over | Final score, distance, cells, best score, Restart button | Running or ready |

Start and restart reset all gameplay state before the next simulation step.
Restart retains preferences and the best score.
Restart reuses loaded assets and does not reload the page.
The page pauses a run when it loses focus or becomes hidden.
Resume requires an explicit player action.
The simulation does not advance while paused.

## 6. Controls

| Action | Keyboard | Touch |
| --- | --- | --- |
| Move left | Left arrow or A | Swipe left or left button |
| Move right | Right arrow or D | Swipe right or right button |
| Jump | Up arrow, W, or Space | Swipe up or jump button |
| Slide | Down arrow or S | Swipe down or slide button |
| Pause or resume | Escape or P | Pause or Resume button |
| Start or restart | Focused button with Enter or Space | Start or Restart button |

One key press produces one lane change.
Ignore keyboard repeat for movement actions.
Ignore gameplay commands while the player interacts with menus.
Prevent page scrolling only for active gameplay controls.
Use pointer events for touch gestures.
Recognize a swipe after 32 CSS pixels and within 500 milliseconds.
Choose the dominant swipe axis and emit one action per gesture.
Clear pending input after blur, pause, restart, and pointer cancellation.

## 7. Gameplay rules

### Movement

The simulation uses meters and seconds.
The player's forward coordinate remains near zero.
Track objects move toward and past the player.
The three lane centers use x coordinates of -2.6, 0, and 2.6 meters.
Horizontal movement approaches the selected lane at 18 meters per second.
Collision checks use actual horizontal position, not the selected lane.

A grounded jump starts with an upward velocity of 9.5 meters per second.
Gravity is 26 meters per second squared.
A jump reaches approximately 1.74 meters and lasts approximately 0.73 seconds.
The player cannot double-jump.
A slide lasts 0.7 seconds and reduces collision height from 1.6 to 0.65 meters.
Jump and slide cannot overlap.
Landing restores the grounded animation and collision bounds.

### Obstacles and collectibles

| Object | Shape and placement | Player response |
| --- | --- | --- |
| Barrier | Low obstacle, 0.75 meters tall | Jump or change lanes |
| Overhead gate | Crossbar with a lower edge at 0.85 meters | Slide or change lanes |
| Blocker | Tall obstacle spanning the player's standing height | Change lanes |
| Energy cell | Floating amber collectible | Touch to collect |
| Shield | Distinct cyan collectible | Touch to gain one protective charge |

The player collision width is 0.7 meters and its depth is 0.6 meters.
Use forgiving obstacle bounds slightly inside the visible obstacle shape.
Use a swept forward interval so fast objects cannot cross the player without detection.
Remove collected objects immediately from collision checks.
A collectible contributes its value once.

A shield lasts eight seconds or absorbs one collision, whichever occurs first.
Absorbing a collision removes that obstacle and grants one second of collision immunity.
A new shield refreshes the duration and does not stack charges.
An unprotected obstacle collision ends the run once.

### Score and difficulty

Speed starts at 16 meters per second.
Speed rises linearly to 32 meters per second over 120 seconds of active play.
Speed remains capped after 120 seconds.
The score equals whole meters traveled plus 25 points per collected energy cell.
The best score updates only when the final score exceeds the stored best score.

The first four seconds contain no damaging obstacles.
The opening patterns introduce lane movement, jumping, and sliding separately.
Later patterns combine obstacle types and vary their placement.
Obstacle rows remain at least 38 meters apart.
At maximum speed, this spacing gives approximately 1.19 seconds between rows.
Each row preserves at least one lane without a damaging obstacle.
The generator never requires a jump or slide to reach the open lane.
Changing across both lanes must remain possible before the next row arrives.
Collectible trails can suggest a route but must not require a collision.

Use seeded randomness for repeatable tests.
Production runs choose a new seed on restart.

## 8. Visual direction

The working title is Hyper Runner.
The environment uses deep navy structures, cyan track edges, and warm amber energy cells.
Damaging obstacles use red markings plus a distinct silhouette.
Color alone must not communicate an obstacle type.

Use an animated robot with a readable silhouette and visible limbs.
Use existing animation clips for running and idle when the asset provides them.
Use root transforms for jump, slide, lean, and collision feedback when suitable clips are absent.
Keep animation separate from gameplay collision bounds.

The track uses reusable elevated sections, rails, structural supports, and illuminated markings.
Scenery includes layered buildings, overhead structures, and distant vehicle lights.
Fog hides the far recycling boundary.
Lighting changes gradually between cyan and amber accents as distance increases.
These changes do not change collision rules.

Use Babylon.js glow, restrained particles, and one controlled shadow source.
Use a small camera lean during lane changes and a short collision shake.
Keep obstacles readable and the track visible throughout all effects.
Disable camera shake and reduce decorative motion when reduced motion is requested.

The camera sits approximately 8 meters behind and 4 meters above the player.
The camera looks ahead along the track.
Tune its field of view between 55 and 65 degrees during visual verification.
Mobile framing must show all three lanes.

## 9. Interface and audio

Render menus and the heads-up display with HTML and CSS above the canvas.
Use native buttons, visible focus indicators, and readable text contrast.
Use a compact display during play and larger panels for ready and game-over states.
Do not place essential controls over upcoming obstacles.
Touch controls have a minimum target size of 48 CSS pixels.
Support viewport widths from 360 pixels and respect device safe areas.

Display distance in meters and speed in kilometers per hour.
Show a visible sound toggle and persistent quality preference.
Use an accessible status message for state changes.
Do not announce score changes on every frame.

Use local licensed sound files for collection, jump, collision, and interface feedback.
Include a local looping electronic background track or ambient loop with redistribution rights.
Initialize or unlock Babylon.js audio from the Start action.
Allow silent play if audio initialization fails.
Pause background audio while the game is paused or hidden.
The mute setting applies to music and effects.

## 10. Assets

Use the Quaternius Cyberpunk Game Kit as the first asset source.
Its official page lists glTF assets, animation, and the Creative Commons Zero license.
Use suitable character and environment files from that pack.
Inspect the actual archive and animation clips before selecting files.

Use Kenney assets for missing audio or simple props where appropriate.
Record the source URL, author, license, and local filename in `public/assets/ATTRIBUTION.md`.
Retain included license files.
Do not purchase assets or require an account.
Ship only selected assets, not entire source archives.
Avoid runtime downloads from asset providers.

If the primary archive is unavailable, use another verified free asset from the same providers.
Record any replacement and its effect on the intended appearance.
Do not replace the finished player with an unanimated placeholder.
Decorative geometry may use Babylon.js mesh builders when this reduces asset integration work.

## 11. Architecture

| Module | Responsibility |
| --- | --- |
| `src/main.ts` | Create the application and handle startup failures |
| `src/game/Game.ts` | Own lifecycle, timing, input consumption, simulation, and presentation |
| `src/game/types.ts` | Define shared state, commands, objects, and events |
| `src/game/config.ts` | Store gameplay constants and quality presets |
| `src/game/simulation.ts` | Advance movement, scoring, shield, and collisions |
| `src/game/patterns.ts` | Create seeded obstacle and collectible patterns |
| `src/input.ts` | Convert keyboard and pointer events into commands |
| `src/storage.ts` | Validate and save best score and preferences |
| `src/scene/createScene.ts` | Configure engine, camera, lights, fog, and quality |
| `src/scene/assets.ts` | Load and validate local assets |
| `src/scene/RunnerView.ts` | Apply character transforms and animation |
| `src/scene/TrackView.ts` | Recycle track, scenery, obstacles, and collectibles |
| `src/scene/Effects.ts` | Apply particles, glow, and camera feedback |
| `src/audio.ts` | Load audio and respond to gameplay events |
| `src/ui.ts` | Render menus, status, settings, and touch buttons |
| `src/style.css` | Define responsive interface styling |

Input commands enter the simulation through the controller.
The simulation owns gameplay state and emits discrete events.
Scene modules read gameplay state and update existing objects.
Audio and effects consume simulation events.
The interface reads a limited snapshot and sends explicit actions.
Persistence receives validated preferences and final scores.

Use a fixed simulation step of 1/120 second.
Clamp accumulated frame time to 0.1 second and process at most 12 steps per frame.
Reset the accumulator on pause and resume.
Keep simulation rules independent of the document and rendering engine lifecycle.
Avoid per-frame interface rebuilding, asset loading, or unbounded object creation.

## 12. Performance and resilience

Target 60 frames per second on the available desktop browser at 1440 by 900 pixels.
Target 30 frames per second on a representative mobile device at low quality.
These are targets until measured on named hardware and browsers.
Browser viewport emulation does not prove physical mobile performance.

Reuse meshes and materials; instance repeated scenery.
Pool track objects and return expired objects to bounded pools.
Keep at least 180 meters of track visible ahead and recycle objects behind the camera.
Cap rendering pixel ratio at 1.5 for high quality and 1.0 for low quality.
Low quality disables shadows and reduces particles and glow cost.
Keep a manual quality selector available.

Measure frame rate after asset loading and shader warmup.
Inspect draw calls and active mesh counts during a two-minute run.
Confirm that object counts remain bounded after repeated restarts.
Prefer a total initial asset transfer below 15 megabytes.
Record an exception if a required licensed asset exceeds that target.

Use a visible retry path for required asset failures.
Show a clear unsupported-graphics message if WebGL 2 initialization fails.
Pause and request reload if the graphics context cannot recover.
Catch storage access failures and continue with in-memory values.
Reject malformed, negative, or non-finite stored scores.
Dispose event listeners, audio, scene resources, and engine resources when the application closes or reloads during development.

## 13. Acceptance tests

| ID | Requirement | Evidence |
| --- | --- | --- |
| A01 | Start reaches active gameplay without uncaught errors | Desktop browser test |
| A02 | Lane movement respects bounds and responds once per command | Unit tests and keyboard play |
| A03 | Jump and slide clear their matching obstacles | Collision tests and visible play |
| A04 | Tall blockers cause game over without protection | Simulation and browser tests |
| A05 | Energy cells score once and shields absorb one collision | Simulation tests |
| A06 | Speed increases, caps correctly, and score uses active play only | Deterministic tests |
| A07 | Generated patterns remain traversable across seeds and maximum speed | Pattern invariant tests |
| A08 | Pause, blur, and hidden state stop progression | Lifecycle tests |
| A09 | Restart clears transient state without reloading assets | Browser test across ten restarts |
| A10 | Best score survives reload and invalid storage does not crash | Storage and browser tests |
| A11 | Swipe and visible touch controls work at 390 by 844 pixels | Browser interaction tests |
| A12 | Ready, running, paused, and game-over screens remain legible | Desktop and mobile screenshots |
| A13 | Audio starts after interaction and obeys mute and pause | Manual audio verification |
| A14 | Local production build loads required assets successfully | Production preview test |
| A15 | Frame rate and object counts meet documented targets or have stated limitations | Recorded performance sample |
| A16 | Missing assets, unavailable graphics, and denied storage have usable outcomes | Failure-path checks |
| A17 | Reduced motion disables camera shake; keyboard focus remains visible | Preference and keyboard checks |

Run type checking, unit tests, and the production build before reporting completion.
Run browser tests against the production preview.
Capture screenshots from the actual rendered game.
Report any unavailable browser, physical-device check, or audio check explicitly.

## 14. Research references

These sources support the stack and implementation decisions.
Exact package versions come from npm metadata, which can be newer than indexed release pages.

- [Babylon.js features](https://www.babylonjs.com/specifications/): integrated rendering and game features.
- [Babylon.js 9 announcement](https://blogs.windows.com/windowsdeveloper/2026/03/26/announcing-babylon-js-9-0/): current major engine generation.
- [Babylon.js releases](https://github.com/BabylonJS/Babylon.js/releases): release history.
- [Babylon.js optimization guide](https://github.com/BabylonJS/Documentation/blob/master/content/features/featuresDeepDive/scene/optimize_your_scene.md): instances, shared geometry, and instrumentation.
- [Babylon.js instances](https://doc.babylonjs.com/features/featuresDeepDive/mesh/copies/instances): repeated-object rendering.
- [Three.js game guide](https://threejs.org/manual/en/game.html): rendering library boundaries and additional game infrastructure.
- [React Three Fiber introduction](https://r3f.docs.pmnd.rs/getting-started/introduction): declarative scene approach and React version pairing.
- [React Three Fiber performance guide](https://r3f.docs.pmnd.rs/advanced/scaling-performance): instancing and rendering quality controls.
- [Vite guide](https://vite.dev/guide/): TypeScript templates, runtime requirements, and static builds.
- [Vitest guide](https://vitest.dev/guide/): test setup and runtime requirements.
- [Quaternius Cyberpunk Game Kit](https://quaternius.com/packs/cyberpunkgamekit.html): primary character and environment assets.
- [Kenney support](https://kenney.nl/support): asset licensing and attribution policy.

## 15. Remaining verification

Package installation, selected assets, animation clips, and Chromium behavior are verified during implementation.
Physical mobile hardware and audible speaker output remain unverified.
See docs/VERIFICATION.md for the full evidence record.

## 16. Implementation decisions

The renderer uses Babylon.js mesh builders for track sections and city structures.
This preserves exact lane dimensions and supports shared geometry across repeated structures.
The Quaternius character provides the animated player.
Unused environment assets are removed from the delivered assets.

The ambient loop uses original oscillator synthesis because a matching downloadable loop is unnecessary for this demo.
Kenney assets provide the four sound effects.

The simulation adds six center-lane cells during the safe opening.
Each obstacle row includes four preceding cells in a safe lane.
The renderer allocates collectible and obstacle pools during loading to prevent allocation changes across restarts.

Babylon.js loads only its glTF 2.0 loader for this asset.
This removes unused glTF 1.0 and extension modules from the initial bundle.
