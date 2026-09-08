# Hyper Runner Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task in the current session. Track completed steps with checkboxes.

**Goal:** Build a complete 3D endless runner for desktop browsers with mobile controls.

**Architecture:** A deterministic simulation owns gameplay state. Babylon.js modules present that state through reusable scene objects. HTML controls send commands through one application controller.

**Tech Stack:** Babylon.js 9.25.0, TypeScript 7.0.2, Vite 8.2.2, Vitest 5.0.0, and Playwright 1.63.0.

**Spec:** [SPEC.md](SPEC.md)

**Status:** Implemented after user approval. Verification evidence is recorded in docs/VERIFICATION.md.

## Global constraints

- Use Node.js 22.12 or later within a supported major: 22, 24, or 26.
- Pin direct dependency versions and retain `package-lock.json`.
- Keep Babylon.js core and loaders on the same version.
- Use WebGL 2 for the first release.
- Store required assets locally with source and license records.
- Use a fixed simulation step of 1/120 second.
- Clamp accumulated frame time to 0.1 second and process at most 12 steps per frame.
- Support viewport widths from 360 pixels and touch targets of at least 48 CSS pixels.
- Cap rendering pixel ratio at 1.5 for high quality and 1.0 for low quality.
- Keep the three requested root documents available before implementation starts.
- Follow the output style in AGENTS.md.

## Delivery sequence

Complete each task and verify its deliverable before starting the next task.
Use the current project folder for implementation; it is empty except for planning documents.
Do not create another project or public deployment.
Initialize Git during setup if useful for local checkpoints.
Commit only after the relevant task checks pass.

| Task | Deliverable | Dependencies |
| --- | --- | --- |
| 1 | Reproducible toolchain and deterministic gameplay core | Reviewed design |
| 2 | Fair patterns, collisions, score, and shield | Task 1 |
| 3 | Rendered environment and animated player | Tasks 1 and 2 |
| 4 | Complete interface, controls, lifecycle, and persistence | Tasks 1 through 3 |
| 5 | Audio, effects, quality controls, and failure handling | Tasks 3 and 4 |
| 6 | Verified production demo, screenshots, and documentation | All previous tasks |

## Shared interfaces

Create these definitions in `src/game/types.ts` during Task 1.
Later tasks must use these names or update all affected references together.

```ts
export type Lane = -1 | 0 | 1;
export type Phase = 'loading' | 'error' | 'ready' | 'running' | 'paused' | 'gameover';
export type Command = 'left' | 'right' | 'jump' | 'slide';
export type Quality = 'high' | 'low';
export type ObjectKind = 'barrier' | 'gate' | 'blocker' | 'cell' | 'shield';
export type EventKind = 'jump' | 'slide' | 'cell' | 'shield' | 'impact' | 'gameover';

export interface RunnerState {
  lane: Lane;
  x: number;
  y: number;
  vy: number;
  slideRemaining: number;
  shieldRemaining: number;
  immunityRemaining: number;
}

export interface TrackObject {
  id: number;
  kind: ObjectKind;
  lane: Lane;
  z: number;
  previousZ: number;
  active: boolean;
}

export interface RunState {
  phase: Phase;
  seed: number;
  elapsed: number;
  distance: number;
  speed: number;
  score: number;
  cells: number;
  runner: RunnerState;
  objects: TrackObject[];
}

export interface GameEvent {
  kind: EventKind;
  objectId?: number;
}

export interface Preferences {
  muted: boolean;
  quality: Quality;
  reducedMotion: boolean;
}

export interface SavedData {
  version: 1;
  bestScore: number;
  preferences: Preferences;
}
```

The simulation mutates one run state and returns events for that step.
The controller consumes those events once.
The renderer must never modify gameplay state.

## Task 1: Toolchain and deterministic movement

**Files:** Create `package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`, `index.html`, `.gitignore`, and `.nvmrc`.
Create `src/game/types.ts`, `src/game/config.ts`, `src/game/simulation.ts`, and `tests/simulation.test.ts`.

**Consumes:** The shared definitions and movement requirements from SPEC.md.

**Produces:**

```ts
export function createRun(seed: number): RunState;
export function applyCommand(state: RunState, command: Command): void;
export function stepRun(state: RunState, dt: number): GameEvent[];
```

- [x] Confirm design approval before creating game code.
- [x] Create a vanilla TypeScript Vite project without overwriting the planning documents.
- [x] Install the pinned packages below and retain their lockfile.

```bash
npm install --save-exact @babylonjs/core@9.25.0 @babylonjs/loaders@9.25.0
npm install --save-dev --save-exact vite@8.2.2 typescript@7.0.2 vitest@5.0.0 @playwright/test@1.63.0
```

- [x] Use strict TypeScript, ES modules, browser libraries, and bundler module resolution.
- [x] Set `.nvmrc` to `26` and document the supported runtime majors.
- [x] Add the following scripts to `package.json`.

```json
{
  "dev": "vite --host 127.0.0.1",
  "typecheck": "tsc --noEmit",
  "test": "vitest run",
  "build": "tsc --noEmit && vite build",
  "preview": "vite preview --host 127.0.0.1",
  "test:e2e": "playwright test"
}
```

- [x] Exclude dependency directories, build output, and test reports from Git.
- [x] Create the shared types and export numeric constants from `config.ts`.
- [x] Write movement tests before implementing movement.

```ts
import { expect, test } from 'vitest';
import { applyCommand, createRun, stepRun } from '../src/game/simulation';

test('lane commands remain inside the track', () => {
  const state = createRun(7);
  state.phase = 'running';
  applyCommand(state, 'left');
  applyCommand(state, 'left');
  expect(state.runner.lane).toBe(-1);
  for (let i = 0; i < 60; i++) stepRun(state, 1 / 120);
  expect(state.runner.x).toBeCloseTo(-2.6);
});

test('pause stops movement and scoring', () => {
  const state = createRun(7);
  state.phase = 'paused';
  const before = structuredClone(state);
  stepRun(state, 1 / 120);
  expect(state).toEqual(before);
});

test('jump lands and cannot restart in the air', () => {
  const state = createRun(7);
  state.phase = 'running';
  applyCommand(state, 'jump');
  stepRun(state, 1 / 120);
  const velocity = state.runner.vy;
  applyCommand(state, 'jump');
  expect(state.runner.vy).toBe(velocity);
  for (let i = 0; i < 120; i++) stepRun(state, 1 / 120);
  expect(state.runner.y).toBe(0);
  expect(state.runner.vy).toBe(0);
});
```

- [x] Run `npm test -- tests/simulation.test.ts` and confirm the missing behavior fails.
- [x] Implement horizontal movement using a bounded approach to the selected lane center.
- [x] Integrate jump velocity and gravity; clamp landing height and velocity to zero.
- [x] Implement exclusive jump and slide states with the specified slide timer.
- [x] Advance elapsed time, distance, speed, and score only while running.
- [x] Add tests for slide expiry, input outside running, and speed capping after 120 seconds.
- [x] Run `npm run typecheck` and `npm test`.

**Acceptance:** Movement and scoring operate without a canvas or document.
**Coverage:** A02, A06, and simulation portions of A08.

## Task 2: Fair patterns and collision behavior

**Files:** Create `src/game/patterns.ts` and `tests/patterns.test.ts`.
Extend `src/game/simulation.ts` and `tests/simulation.test.ts`.

**Consumes:** `RunState`, `TrackObject`, and gameplay constants.

**Produces:**

```ts
export interface PatternRow {
  kinds: [ObjectKind | null, ObjectKind | null, ObjectKind | null];
  gap: number;
}
export function createPatternSequence(seed: number, count: number): PatternRow[];
```

- [x] Write pattern tests for identical seeds, distinct sequences, legal lane contents, and minimum spacing.

```ts
import { expect, test } from 'vitest';
import { createPatternSequence } from '../src/game/patterns';

test('patterns preserve an escape lane across seeds', () => {
  const danger = new Set(['barrier', 'gate', 'blocker']);
  for (let seed = 1; seed <= 100; seed++) {
    const rows = createPatternSequence(seed, 200);
    expect(rows).toEqual(createPatternSequence(seed, 200));
    for (const row of rows) {
      expect(row.gap).toBeGreaterThanOrEqual(38);
      expect(row.kinds.some(kind => kind === null || !danger.has(kind))).toBe(true);
    }
  }
});
```

- [x] Confirm the tests fail before implementing the seeded generator.
- [x] Select from a small authored pattern catalog using seeded randomness.
- [x] Introduce the three obstacle types separately after the four-second safe opening.
- [x] Spawn rows ahead of the camera and remove inactive objects behind it.
- [x] Keep object identifiers unique within a run and reset them on restart.
- [x] Use actual runner x, jump height, and slide height for collision bounds.
- [x] Reuse Babylon.js bounding-box overlap with an interval covering previous and current forward positions.
- [x] Emit collection, shield, impact, and game-over events once per object.
- [x] Implement eight-second shield expiry and one-second immunity after an absorbed impact.
- [x] Write tests for jump clearance, slide clearance, blocker impact, and crossing collisions at maximum speed.
- [x] Test one-time collection with the same object present across successive steps.

```ts
test('an energy cell contributes points once', () => {
  const state = createRun(1);
  state.phase = 'running';
  state.objects.push({
    id: 1, kind: 'cell', lane: 0, z: 0.1,
    previousZ: 0.1, active: true,
  });
  stepRun(state, 1 / 120);
  stepRun(state, 1 / 120);
  expect(state.cells).toBe(1);
  expect(state.score).toBe(Math.floor(state.distance) + 25);
});
```

- [x] Test an unprotected impact, one protected impact, immunity expiry, and shield refresh.
- [x] Test traversability at maximum speed with consecutive opposite escape lanes.
- [x] Run `npm test` and `npm run typecheck`.

**Acceptance:** The generator produces repeatable, traversable patterns with verified collisions.
**Coverage:** A03 through A07.

## Task 3: Environment and animated player

**Files:** Create `src/main.ts`, `src/game/Game.ts`, `src/scene/createScene.ts`, `src/scene/assets.ts`, `src/scene/RunnerView.ts`, and `src/scene/TrackView.ts`.
Create `public/assets/models/`, license records, and `public/assets/ATTRIBUTION.md`.

**Consumes:** Simulation state, events, and the primary asset source from SPEC.md.

**Produces:**

```ts
// createScene.ts
export interface SceneContext {
  engine: Engine;
  scene: Scene;
  camera: FreeCamera;
  setQuality(quality: Quality): void;
  dispose(): void;
}
export function createScene(canvas: HTMLCanvasElement, quality: Quality): SceneContext;

// assets.ts
export interface GameAssets {
  runner: AssetContainer;
  props: Map<string, AssetContainer>;
  dispose(): void;
}
export function loadAssets(scene: Scene, onProgress: (ratio: number) => void): Promise<GameAssets>;

// View classes
export class RunnerView {
  constructor(scene: Scene, assets: GameAssets);
  sync(state: RunState, frameDt: number): void;
  dispose(): void;
}
export class TrackView {
  constructor(scene: Scene, assets: GameAssets);
  sync(state: RunState): void;
  reset(): void;
  dispose(): void;
}
```

Import `Engine`, `Scene`, `FreeCamera`, and `AssetContainer` from their Babylon.js modules.
Import `Quality` and `RunState` from `src/game/types.ts`.

- [x] Download and inspect the primary asset archive using its official download link.
- [x] Record the archive source and verify the included license.
- [x] Inspect glTF files, mesh bounds, materials, and animation names before selecting the runner.
- [x] Copy selected files and licenses into `public/assets/`.
- [x] Record actual runner idle and run clip names in the asset loader.
- [x] Add a load failure if required meshes or animations are missing.
- [x] Create a full-window canvas and basic loading status for the first rendering check.
- [x] Configure WebGL 2, a chase camera, fog, shared materials, and a controlled shadow source.
- [x] Build reusable track sections using the selected assets and Babylon.js mesh builders.
- [x] Instance repeated buildings, rails, lights, and supports.
- [x] Bind the runner view to actual x, jump height, and slide state.
- [x] Blend idle and running animation; apply root lean and slide transforms separately.
- [x] Pool obstacle and collectible views by object kind.
- [x] Hide or recycle views as simulation objects become inactive.
- [x] Add the fixed-step controller with the specified accumulator limits.

```ts
accumulator = Math.min(accumulator + frameDt, 0.1);
let steps = 0;
while (accumulator >= 1 / 120 && steps < 12) {
  const events = stepRun(state, 1 / 120);
  consumeEvents(events);
  accumulator -= 1 / 120;
  steps += 1;
}
runnerView.sync(state, frameDt);
trackView.sync(state);
```

Define `consumeEvents(events: GameEvent[]): void` as a controller method.
It dispatches events to presentation consumers added in Task 5.

- [x] Reset the accumulator outside active gameplay and after resume.
- [x] Start the development server and inspect the scene in an actual browser.
- [x] Check runner scale, facing direction, shadow placement, track seams, and all three lanes.
- [x] Run a two-minute observation and check that active object counts remain bounded.
- [x] Run `npm run build` and `npm test`.

**Acceptance:** The actual simulation appears as an animated 3D runner scene without placeholder character geometry.
**Coverage:** Visual foundation for A01, A12, A14, and A15.

## Task 4: Interface, input, lifecycle, and persistence

**Files:** Create `src/input.ts`, `src/storage.ts`, `src/ui.ts`, `src/style.css`, and `tests/storage.test.ts`.
Extend `src/game/Game.ts` and `src/main.ts`.
Create `playwright.config.ts` and `tests/e2e/game.spec.ts`.

**Consumes:** Simulation functions, scene context, shared state, and preferences.

**Produces:**

```ts
export function bindInput(
  canvas: HTMLCanvasElement,
  onCommand: (command: Command) => void,
  onPause: () => void,
): { clear(): void; dispose(): void };

export function readSaved(storage: Pick<Storage, 'getItem'>): SavedData;
export function writeSaved(storage: Pick<Storage, 'setItem'>, data: SavedData): void;

export type UiAction = 'start' | 'pause' | 'resume' | 'restart' | 'home' | 'retry';
export interface UiSnapshot {
  phase: Phase;
  score: number;
  distance: number;
  speed: number;
  cells: number;
  bestScore: number;
  shieldRemaining: number;
  preferences: Preferences;
}
export function createUi(
  root: HTMLElement,
  onAction: (action: UiAction) => void,
  onCommand: (command: Command) => void,
  onPreferences: (preferences: Preferences) => void,
): {
  update(snapshot: UiSnapshot): void;
  setLoading(progress: number): void;
  showError(message: string): void;
  dispose(): void;
};
```

- [x] Write storage tests for missing data, malformed JSON, invalid scores, unsupported versions, and access exceptions.

```ts
import { expect, test } from 'vitest';
import { readSaved } from '../src/storage';

test('storage failure returns safe defaults', () => {
  const storage = { getItem() { throw new Error('Access denied'); } };
  const saved = readSaved(storage);
  expect(saved.bestScore).toBe(0);
  expect(saved.version).toBe(1);
});
```

- [x] Implement versioned persistence under `hyper-runner:v1` with guarded reads and writes.
- [x] Implement keyboard and pointer commands with repeat suppression and gesture cancellation.
- [x] Add native HTML buttons for all menus and touch controls.
- [x] Implement the full state table from SPEC.md in the controller.
- [x] Pause on blur and hidden state; require explicit resume.
- [x] Update numeric interface values at most ten times per second during gameplay.
- [x] Update menu state immediately after lifecycle transitions.
- [x] Preserve focus visibility and return focus to the relevant primary button after state changes.
- [x] Add responsive styling, safe-area padding, and the navy, cyan, and amber visual system.
- [x] Configure Playwright to run against `npm run preview -- --port 4173`.
- [x] Write a browser test for start, pause, stable paused distance, and resume.

```ts
import { expect, test } from '@playwright/test';

test('a paused run retains its distance', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Start run', exact: true }).click();
  await expect(page.getByTestId('distance')).not.toHaveText('0 m');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeVisible();
  const distance = await page.getByTestId('distance').textContent();
  await page.waitForTimeout(350);
  await expect(page.getByTestId('distance')).toHaveText(distance!);
  await page.getByRole('button', { name: 'Resume', exact: true }).click();
  await expect(page.getByTestId('distance')).not.toHaveText(distance!);
});
```

Use `data-testid="distance"` only on the visible distance value.
Use accessible role queries for buttons.
Add narrowly scoped read-only diagnostics for tests if visual state cannot otherwise verify an action.
Do not expose gameplay mutation commands in the production interface.

- [x] Test game over, restart, and best-score persistence through real controls.
- [x] Test mobile swipe gestures and visible touch buttons at 390 by 844 pixels.
- [x] Run `npm run build`, `npm test`, and `npm run test:e2e`.

**Acceptance:** A player can complete the entire game flow through keyboard or touch controls.
**Coverage:** A01, A08 through A12, and persistence portions of A16.

## Task 5: Audio, effects, quality, and resilience

**Files:** Create `src/audio.ts`, `src/scene/Effects.ts`, and local files under `public/assets/audio/`.
Extend `src/scene/createScene.ts`, `src/game/Game.ts`, `src/ui.ts`, and asset attribution.

**Consumes:** `GameEvent[]`, `Preferences`, scene context, and run state.

**Produces:**

```ts
export interface GameAudio {
  unlock(): Promise<void>;
  consume(events: GameEvent[]): void;
  setMuted(muted: boolean): void;
  setPaused(paused: boolean): void;
  dispose(): void;
}
export function createAudio(): Promise<GameAudio>;

export class Effects {
  constructor(context: SceneContext);
  consume(events: GameEvent[]): void;
  update(state: RunState, frameDt: number): void;
  setPreferences(preferences: Preferences): void;
  dispose(): void;
}
```

- [x] Select local audio files with verified redistribution rights and record their licenses.
- [x] Use Babylon.js audio APIs supported by the installed version.
- [x] Unlock audio directly from Start or another explicit user interaction.
- [x] Catch unlock failures and preserve silent gameplay.
- [x] Route jump, collection, impact, and game-over events to distinct sounds.
- [x] Add the licensed ambient or music loop and enforce pause and mute behavior.
- [x] Add bounded particle bursts and restrained glow for energy cells and the shield.
- [x] Add a visible shield state and short impact response.
- [x] Honor reduced motion by disabling camera shake and reducing decorative motion.
- [x] Implement quality presets through `SceneContext.setQuality`.
- [x] Cap resolution and disable shadows in low quality.
- [x] Provide visible loading failure, retry, and unsupported-graphics states.
- [x] Remove all installed listeners and dispose audio, scene, and engine resources during teardown.
- [ ] Verify mute, pause, and resume through actual audible playback. Speaker output is unavailable; engine playback is tested.
- [x] Verify denied storage and missing assets through browser failure injection.
- [x] Inspect visual effects during play; reduce effects that obscure obstacle silhouettes.
- [x] Run the unit tests, type checks, production build, and affected browser tests.

**Acceptance:** Effects improve feedback without hiding obstacles or preventing play after optional audio failure.
**Coverage:** A13, A16, A17, and quality portions of A15.

## Task 6: Production verification and delivery

**Files:** Create `README.md`, `docs/VERIFICATION.md`, and screenshots under `docs/screenshots/`.
Extend browser tests and update the implementation record below.

**Consumes:** The complete demo and acceptance matrix from SPEC.md.
**Produces:** A reproducible local demo, static production build, evidence, and recorded limitations.

- [x] Run the final automated checks.

```bash
npm run typecheck
npm test
npm run build
npm run test:e2e
```

- [x] Test the production preview at 1440 by 900 and 390 by 844 pixels.
- [x] Capture ready, running, paused, and game-over screenshots from the real canvas.
- [x] Inspect screenshot layout, character animation, obstacle readability, and touch control placement.
- [x] Test keyboard focus, reduced motion, mute, pause, restart, and page reload.
- [x] Complete ten restart cycles and inspect object and listener counts.
- [x] Measure frame rate over a two-minute active run after warmup. See docs/performance.json.
- [x] Record browser, hardware, viewport, quality, frame rate, and active object counts.
- [x] Separate physical mobile evidence from browser viewport emulation.
- [x] Inspect production asset requests and total transfer size.
- [x] Check that selected assets load locally and that no required asset uses a provider URL at runtime.
- [x] Record the result for every acceptance identifier from A01 through A17.
- [x] Fix failed acceptance checks and rerun only the affected checks plus the final build.
- [x] Document setup, controls, quality settings, architecture, and asset sources in README.md.
- [x] Record any unavailable check or remaining limitation in docs/VERIFICATION.md.
- [x] Update completed checkboxes and record deviations in both planning documents where necessary.
- [x] Leave the local development or preview server accessible and provide its URL.

**Acceptance:** The production demo works through its complete flow and its verification record matches the observed results.

## Risks and responses

| Risk | Response | Verification point |
| --- | --- | --- |
| Primary asset archive is unavailable | Use another licensed asset from the approved providers and record the replacement | Task 3 |
| Animation names or orientation differ | Inspect actual clips and bounds before integrating the runner | Task 3 |
| Latest packages have incompatible types or APIs | Check installation and type errors; pin a verified compatible release if required | Task 1 |
| Effects reduce mobile frame rate | Apply low quality and bounded particles | Tasks 5 and 6 |
| Random placement creates an impossible sequence | Use an authored catalog and test escape-lane reachability | Task 2 |
| Audio requires browser interaction | Unlock from Start and preserve silent play on failure | Task 5 |
| Frame stalls cause missed collisions | Use fixed steps and swept forward intervals | Tasks 1 and 2 |
| Storage is blocked | Continue with validated in-memory defaults | Task 4 |

## Planning verification

- [x] Inspect the repository and confirm that it contains no application code.
- [x] Confirm the browser target and endless-runner structure with the user.
- [x] State the futuristic city theme as an assumption.
- [x] Compare three implementation approaches and select Babylon.js.
- [x] Research current official documentation and query exact package versions.
- [x] Save SPEC.md, PLAN.md, and AGENTS.md before implementation.
- [x] Map all specification acceptance tests to implementation tasks.
- [x] Obtain review of the concrete design before implementation.

## Implementation record

The user approves implementation with “implement”.
All six implementation tasks are complete.
The current project folder contains the game, dependencies, production build, tests, and verification evidence.
No Git repository existed, so implementation stays in the approved folder without creating a branch or remote.

The execution skill directs independent agent work.
The parent integrates the scene, lifecycle, audio, and final verification.
Agents implement gameplay, acquire assets, implement the interface, and review code.

Task 1: Pinned packages install successfully. Movement and storage tests pass.
Task 2: Seeded patterns, collision rules, shields, safe energy trails, and bounded spawning pass 36 unit tests.
Task 3: The renderer uses the licensed Quaternius character and repeated Babylon.js geometry.
Task 4: Keyboard, swipe, menus, pause, restart, and preference persistence pass browser tests.
Task 5: Audio starts after interaction. Quality controls, reduced motion, and failure paths are implemented.
Task 6: Type checks, production build, browser checks, screenshots, and desktop performance evidence are recorded.

### Decisions and deviations

- The renderer builds exact track dimensions with Babylon.js mesh builders instead of importing fixed platform geometry.
- Unused environment assets are removed from the delivered files.
- Original oscillator synthesis supplies the ambient loop; Kenney supplies four sound effects.
- Read-only runtime diagnostics support reproducible browser and performance checks.
- The glTF 2.0 loader replaces the full loader bundle because the selected model uses no extensions.
- View pools allocate during loading to keep mesh counts stable across restarts.
- Browser-history verification covers the persisted lifecycle event, not every browser's history-cache policy.
- Physical mobile performance and audible speaker output remain unverified.

### Final evidence

Read [docs/VERIFICATION.md](docs/VERIFICATION.md) for acceptance coverage.
Read [docs/performance.json](docs/performance.json) for the 125-second desktop measurement.
Read [README.md](README.md) for setup and controls.
