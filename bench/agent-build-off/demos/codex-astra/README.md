# Hyper Runner

Hyper Runner is a browser-based 3D endless runner.
Control an animated robot on an elevated city track.
Change lanes, clear obstacles, collect energy, and improve your local best score.

## Start the game

Use Node.js 22.12 or later within major version 22, 24, or 26.

```bash
npm ci
npm run dev
```

Open the URL printed by Vite.
Do not open `index.html` directly through a file URL.
The local server loads TypeScript modules and game assets.

## Controls

| Action | Keyboard | Touch |
| --- | --- | --- |
| Move left | A or left arrow | Swipe left or Left button |
| Move right | D or right arrow | Swipe right or Right button |
| Jump | W, up arrow, or Space | Swipe up or Jump button |
| Slide | S or down arrow | Swipe down or Slide button |
| Pause or resume | Escape or P | Pause or Resume button |

Jump over low barriers.
Slide under overhead gates.
Change lanes to avoid tall blockers.
Collect amber energy cells for 25 points each.
Collect a cyan shield to absorb one impact within eight seconds.

The game increases speed over the first two minutes.
The score adds whole meters traveled and energy points.
The game stores your best score and preferences in this browser.
The game pauses when its page loses focus.

Use the sound and quality controls at the top of the screen.
Low quality reduces rendering resolution and disables shadows.
Reduced motion disables camera shake and decorative movement.
Mobile devices use low quality initially and retain later quality choices.

## Production build

```bash
npm run build
npm run preview -- --port 4173
```

Open [the local preview](http://127.0.0.1:4173).
The `dist` directory contains the static production build.
The relative asset paths support hosting under a subdirectory.
No account, backend, or external asset request is required during play.

## Verification

```bash
npm run typecheck
npm test
npx playwright install chromium
npm run build
npm run test:e2e
```

Browser tests use Chromium and the production preview.
The performance script controls the game through keyboard events.
Start the preview before this check:

```bash
node scripts/performance.mjs
```

Read [the verification record](docs/VERIFICATION.md) for results and limitations.
View the captured game states in [docs/screenshots](docs/screenshots).

## Structure

| Location | Responsibility |
| --- | --- |
| `src/game/` | Fixed-step simulation, patterns, and lifecycle |
| `src/scene/` | Babylon.js scene, animated character, reusable track objects, and effects |
| `src/ui.ts` and `src/style.css` | Menus, game status, preferences, and responsive layout |
| `src/input.ts` | Keyboard and pointer controls |
| `src/storage.ts` | Validated local storage |
| `src/audio.ts` | Babylon.js audio and local sounds |
| `public/assets/` | Licensed models, sounds, and attribution |
| `tests/` | Simulation, storage, and browser tests |

The simulation owns gameplay state.
The renderer reads that state and reuses preallocated objects.
Babylon.js provides rendering, animation, collision bounds, particles, audio, and instancing.
The read-only `window.__hyperRunner` object exposes runtime diagnostics.
It cannot change gameplay state.

Read [SPEC.md](SPEC.md), [PLAN.md](PLAN.md), and [AGENTS.md](AGENTS.md) for project requirements.
Read [asset attribution](public/assets/ATTRIBUTION.md) for sources and licenses.
