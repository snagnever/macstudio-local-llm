# Hyper Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A complete 3D neon endless-runner demo that runs in the browser with `npm install && npm run dev`.

**Architecture:** All per-frame game state lives in a mutable module singleton (`src/game/runtime.ts`) stepped by the single `useFrame` in `src/three/GameLoop.tsx`; React/zustand only holds UI-phase state and HUD values synced ~4 Hz. Rendering is declarative R3F + drei + postprocessing; spawning/collision/input/audio are hand-written pure logic in `src/game/`.

**Tech Stack:** React 19, TypeScript 5.9 strict, Vite 8, three 0.185.1, @react-three/fiber 9.7, @react-three/drei 10.7, @react-three/postprocessing 3.1, zustand 5, Vitest 5 (+ jsdom for input/store tests).

**Spec:** `SPEC.md` (repo root) — read it before starting any task; it defines all rules, numbers, and the acceptance criteria this plan implements.

## Global Constraints

- Node ≥ 22 (dev machine has v26.8.1); run all commands from repo root `/Users/vitor/LocalProjects/hyper-runner-superpowers`.
- Pinned versions (verified on npm): `react ^19.2.8`, `react-dom ^19.2.8`, `three ^0.185.1`, `@react-three/fiber ^9.7.0`, `@react-three/drei ^10.7.8`, `@react-three/postprocessing ^3.1.1`, `zustand ^5.0.15`; dev: `typescript ^5.9.3`, `vite ^8.2.2`, `@vitejs/plugin-react ^6.1.1`, `vitest ^5.0.0` (v3 is incompatible with vite 8), `jsdom ^30.0.1`, `@types/three ^0.185.4`, `@types/react ^19.2.18`, `@types/react-dom ^19.2.7`, `@types/node ^24.0.0`.
- Zero external asset files (no models/textures/audio/sounds) — everything procedural or synthesized (SPEC §1.5, §1.6).
- No runtime network fetches (title is DOM/CSS, not troika `Text`, to avoid font CDN fetch).
- No physics engine; lane-space AABB only (SPEC §2.1).
- React re-renders only on phase transitions + HUD sync (SPEC §2.2); per-frame code must not allocate per frame where avoidable.
- Game logic must never throw because of audio or localStorage (SPEC §2.4, every call guarded).
- `dt` clamped to 50 ms in runtime step (SPEC §2.4).
- Commands: `npm run dev`, `npm test` (vitest), `npm run typecheck`, `npm run build`, `npm run preview`.
- Commit after every task with the exact message given in that task.

---

### Task 1: Scaffold project + AGENTS.md

**Files:**
- Create: `package.json`, `tsconfig.json`, `vite.config.ts`, `index.html`, `.gitignore`, `src/main.tsx`, `src/App.tsx`, `src/ui.css`, `AGENTS.md`

**Interfaces:**
- Consumes: nothing.
- Produces: toolchain (`npm test`, `npm run typecheck`, `npm run build`), entry `src/main.tsx`, placeholder `src/App.tsx`, base `src/ui.css` extended in Task 14.

- [ ] **Step 1: Write `package.json`**

```json
{
  "name": "hyper-runner",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "typecheck": "tsc --noEmit",
    "build": "npm run typecheck && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "@react-three/drei": "^10.7.8",
    "@react-three/fiber": "^9.7.0",
    "@react-three/postprocessing": "^3.1.1",
    "react": "^19.2.8",
    "react-dom": "^19.2.8",
    "three": "^0.185.1",
    "zustand": "^5.0.15"
  },
  "devDependencies": {
    "@types/node": "^24.0.0",
    "@types/react": "^19.2.18",
    "@types/react-dom": "^19.2.7",
    "@types/three": "^0.185.4",
    "@vitejs/plugin-react": "^6.1.1",
    "jsdom": "^30.0.1",
    "typescript": "^5.9.3",
    "vite": "^8.2.2",
    "vitest": "^5.0.0"
  }
}
```

- [ ] **Step 2: Write `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "types": ["node"],
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "noEmit": true
  },
  "include": ["src", "vite.config.ts"]
}
```

- [ ] **Step 3: Write `vite.config.ts`**

```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'node',
    passWithNoTests: true,
  },
});
```

- [ ] **Step 4: Write `index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1.0, viewport-fit=cover, user-scalable=no"
    />
    <title>Hyper Runner</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Write `.gitignore`**

```
node_modules
dist
*.local
```

- [ ] **Step 6: Write `src/main.tsx`**

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { startRun } from './game/session';
import './ui.css';

declare global {
  interface Window {
    startHyperRun: (seedLabel?: string) => void;
  }
}

// console repro: window.startHyperRun('3F') starts a run from seed base36 '3F'
window.startHyperRun = startRun;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 7: Write placeholder `src/App.tsx`** (replaced in Task 11/14)

```tsx
export default function App() {
  return <div className="stage" />;
}
```

- [ ] **Step 8: Write base `src/ui.css`** (extended in Task 14)

```css
:root {
  color-scheme: dark;
}
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
html,
body,
#root {
  height: 100%;
}
body {
  background: #070311;
  color: #f4f0ff;
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  overflow: hidden;
}
.stage {
  position: fixed;
  inset: 0;
}
canvas {
  display: block;
  touch-action: none;
}
```

- [ ] **Step 9: Write `AGENTS.md`**

```md
# Hyper Runner

A complete, impressive 3D endless-runner demo for the browser: synthwave neon
aesthetic, fully procedural assets, keyboard + touch.

## Start here

1. `SPEC.md` (repo root) — the approved specification. All game rules,
   numbers, and acceptance criteria live there. Do not change it without a
   note in the commit message.
2. `PLAN.md` (repo root) — the task-by-task implementation plan. Execute it
   in order; each task ends with a commit.

## Commands

- `npm install` — install deps
- `npm run dev` — dev server
- `npm test` — vitest unit tests (pure logic in `src/game/`)
- `npm run typecheck` — tsc strict
- `npm run build` / `npm run preview` — production build + serve

## Rules of the codebase

- Per-frame game state is a mutable singleton (`src/game/runtime.ts`);
  React/zustand holds only UI state (SPEC §2.2). Do not store per-frame
  values in zustand.
- `src/game/*` must not import React/three (audio/input may use Web
  APIs/DOM; runtime/patterns/collision/rng stay pure).
- Never let audio or localStorage failures throw (SPEC §2.4).
```

- [ ] **Step 10: Install and verify toolchain**

```bash
npm install
```

`src/main.tsx` (Step 6) imports `./game/session`, which only exists after Task 10 — for now temporarily replace the body with a version that omits that import and the window global:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './ui.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 11: Verify build + test**

```bash
npm run typecheck   # PASS
npm test            # passes with "no test files" (passWithNoTests)
npm run build       # dist/ emitted
```

- [ ] **Step 12: Commit**

```bash
git add package.json package-lock.json tsconfig.json vite.config.ts index.html .gitignore AGENTS.md src
git commit -m "chore: scaffold vite react-ts project with test/build toolchain"
```

---
### Task 2: Types, constants, RNG

**Files:**
- Create: `src/game/types.ts`, `src/game/constants.ts`, `src/game/rng.ts`
- Test: `src/game/rng.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `types.ts`: `Intent = 'left'|'right'|'jump'|'slide'|'pause'|'confirm'`, `ObstacleKind = 'barrier'|'gate'|'wall'`, `Phase = 'menu'|'running'|'paused'|'over'`, `GameEvent = 'lane'|'jump'|'slide'|'land'|'coin'|'crash'`, `ObstacleDef {kind, lane}`, `CoinDef {lane, count, high}`, `RowDef {name, obstacles, coins}`, `CoinEntity {lane, z, y, taken}`, `RowEntity {z, obstacles, coins}`, `Burst {x, y, z, t}`, `PlayerState {lane, x, y, vy, height, sliding, slideT, onGround}`.
  - `constants.ts`: `LANE_W, LANE_X, PLAYER_H, PLAYER_SLIDE_H, PLAYER_D, GRAVITY, JUMP_V, SLIDE_TIME, SPEED_START, SPEED_MAX, SPEED_RAMP, MAX_DT, ROW_GAP, SPAWN_Z, DESPAWN_Z, DEPTH, BARRIER_H, GATE_BOTTOM, GATE_TOP, WALL_TOP, COIN_Y, COIN_Y_HIGH, COIN_SPACING, COIN_Z_TOL, COIN_Y_TOL, SCORE_PER_COIN, LANE_LERP, SWIPE_MIN, HUD_SYNC_INTERVAL, STORAGE_KEY, FOV_BASE, FOV_FAST, FOG_DENSITY, BURST_LIFE, BURST_POOL, COLOR`.
  - `rng.ts`: `mulberry32(seed: number): () => number`, `randomSeed(): number`, `formatSeed(seed: number): string`.

- [ ] **Step 1: Write `src/game/types.ts`**

```ts
export type Intent = 'left' | 'right' | 'jump' | 'slide' | 'pause' | 'confirm';
export type ObstacleKind = 'barrier' | 'gate' | 'wall';
export type Phase = 'menu' | 'running' | 'paused' | 'over';
export type GameEvent = 'lane' | 'jump' | 'slide' | 'land' | 'coin' | 'crash';

export interface ObstacleDef {
  kind: ObstacleKind;
  lane: number;
}

export interface CoinDef {
  lane: number;
  count: number;
  high: boolean;
}

export interface RowDef {
  name: string;
  obstacles: ObstacleDef[];
  coins: CoinDef | null;
}

export interface CoinEntity {
  lane: number;
  z: number;
  y: number;
  taken: boolean;
}

export interface RowEntity {
  z: number;
  obstacles: ObstacleDef[];
  coins: CoinEntity[];
}

export interface Burst {
  x: number;
  y: number;
  z: number;
  t: number;
}

export interface PlayerState {
  lane: number;
  x: number;
  y: number;
  vy: number;
  height: number;
  sliding: boolean;
  slideT: number;
  onGround: boolean;
}
```

- [ ] **Step 2: Write `src/game/constants.ts`**

```ts
export const LANE_W = 2.4;
export const LANE_X = [-LANE_W, 0, LANE_W];
export const PLAYER_H = 1.6;
export const PLAYER_SLIDE_H = 0.7;
export const PLAYER_D = 0.6;
export const GRAVITY = 55;
export const JUMP_V = 15.1;
export const SLIDE_TIME = 0.6;
export const SPEED_START = 18;
export const SPEED_MAX = 40;
export const SPEED_RAMP = 0.25;
export const MAX_DT = 0.05;
export const ROW_GAP = 18;
export const SPAWN_Z = -120;
export const DESPAWN_Z = 12;
export const DEPTH = 0.8;
export const BARRIER_H = 1.0;
export const GATE_BOTTOM = 0.9;
export const GATE_TOP = 2.6;
export const WALL_TOP = 4;
export const COIN_Y = 0.9;
export const COIN_Y_HIGH = 2.2;
export const COIN_SPACING = 2.2;
export const COIN_Z_TOL = 1.2;
export const COIN_Y_TOL = 1.1;
export const SCORE_PER_COIN = 10;
export const LANE_LERP = 16;
export const SWIPE_MIN = 30;
export const HUD_SYNC_INTERVAL = 0.25;
export const STORAGE_KEY = 'hyper-ru….best';
export const FOV_BASE = 70;
export const FOV_FAST = 78;
export const FOG_DENSITY = 0.022;
export const BURST_LIFE = 0.45;
export const BURST_POOL = 6;
export const COLOR = {
  bg: '#070311',
  fog: '#2a0b45',
  cyan: '#00f6ff',
  magenta: '#ff2bd6',
  violet: '#8b5cf6',
  yellow: '#ffd93d',
  white: '#f4f0ff',
} as const;
```

- [ ] **Step 3: Write the failing test `src/game/rng.test.ts`**

```ts
import { describe, expect, it } from 'vitest';
import { formatSeed, mulberry32, randomSeed } from './rng';

describe('mulberry32', () => {
  it('produces a deterministic sequence for a fixed seed', () => {
    const a = mulberry32(123);
    const b = mulberry32(123);
    const seqA = [a(), a(), a(), a(), a()];
    const seqB = [b(), b(), b(), b(), b()];
    expect(seqA).toEqual(seqB);
  });

  it('produces values in [0, 1)', () => {
    const rand = mulberry32(999);
    for (let i = 0; i < 1000; i++) {
      const v = rand();
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(1);
    }
  });

  it('different seeds give different sequences', () => {
    expect(mulberry32(1)()).not.toBe(mulberry32(2)());
  });
});

describe('formatSeed / randomSeed', () => {
  it('formats seeds in base36 uppercase', () => {
    expect(formatSeed(123)).toBe('3F');
  });

  it('round-trips through parseInt base36', () => {
    const seed = randomSeed();
    expect(parseInt(formatSeed(seed), 36)).toBe(seed);
  });
});
```

- [ ] **Step 4: Run it to verify it fails**

Run: `npx vitest run src/game/rng.test.ts`
Expected: FAIL — cannot resolve `./rng`.

- [ ] **Step 5: Write `src/game/rng.ts`**

```ts
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function randomSeed(): number {
  return (Date.now() ^ Math.floor(Math.random() * 0xffffffff)) >>> 0;
}

export function formatSeed(seed: number): string {
  return (seed >>> 0).toString(36).toUpperCase();
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `npx vitest run src/game/rng.test.ts`
Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add src/game/types.ts src/game/constants.ts src/game/rng.ts src/game/rng.test.ts
git commit -m "feat: game types, tuning constants, seeded rng"
```

---
### Task 3: Pattern table

**Files:**
- Create: `src/game/patterns.ts`
- Test: `src/game/patterns.test.ts`

**Interfaces:**
- Consumes: `mulberry32` from `rng.ts`, `RowDef`/`ObstacleKind` from `types.ts`.
- Produces: `PATTERNS: { name: string; weight: number; build: (rand: () => number) => RowDef }[]`, `generateRow(rand: () => number): RowDef`, `isWinnable(row: RowDef): boolean`.

- [ ] **Step 1: Write the failing test `src/game/patterns.test.ts`**

```ts
import { describe, expect, it } from 'vitest';
import { PATTERNS, generateRow, isWinnable } from './patterns';
import { mulberry32 } from './rng';

describe('patterns', () => {
  it('every generated row leaves at least one open lane', () => {
    for (let seed = 1; seed <= 200; seed++) {
      const rand = mulberry32(seed);
      for (let i = 0; i < 50; i++) {
        const row = generateRow(rand);
        expect(isWinnable(row)).toBe(true);
      }
    }
  });

  it('all patterns appear in a long sequence', () => {
    const rand = mulberry32(42);
    const names = new Set<string>();
    for (let i = 0; i < 4000; i++) names.add(generateRow(rand).name);
    for (const p of PATTERNS) expect(names.has(p.name)).toBe(true);
  });

  it('observed frequencies match declared weights', () => {
    const rand = mulberry32(7);
    const totalWeight = PATTERNS.reduce((s, p) => s + p.weight, 0);
    const counts = new Map<string, number>();
    const n = 20000;
    for (let i = 0; i < n; i++) {
      const name = generateRow(rand).name;
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
    for (const p of PATTERNS) {
      const share = (counts.get(p.name) ?? 0) / n;
      const expected = p.weight / totalWeight;
      expect(share).toBeGreaterThan(expected - 0.04);
      expect(share).toBeLessThan(expected + 0.04);
    }
  });

  it('barrier-single carries a bonus coin about 30% of the time', () => {
    const rand = mulberry32(9);
    let singles = 0;
    let withCoins = 0;
    for (let i = 0; i < 20000; i++) {
      const row = generateRow(rand);
      if (row.name === 'barrier-single') {
        singles++;
        if (row.coins) withCoins++;
      }
    }
    const share = withCoins / singles;
    expect(share).toBeGreaterThan(0.2);
    expect(share).toBeLessThan(0.4);
  });

  it('coin-line rows have 3-5 coins and no obstacles', () => {
    const rand = mulberry32(5);
    let seen = 0;
    for (let i = 0; i < 20000 && seen < 200; i++) {
      const row = generateRow(rand);
      if (row.name === 'coin-line') {
        seen++;
        expect(row.obstacles).toHaveLength(0);
        expect(row.coins).not.toBeNull();
        expect(row.coins!.count).toBeGreaterThanOrEqual(3);
        expect(row.coins!.count).toBeLessThanOrEqual(5);
        expect(row.coins!.high).toBe(false);
      }
    }
    expect(seen).toBe(200);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run src/game/patterns.test.ts`
Expected: FAIL — cannot resolve `./patterns`.

- [ ] **Step 3: Write `src/game/patterns.ts`**

```ts
import type { ObstacleDef, ObstacleKind, RowDef } from './types';

export interface Pattern {
  name: string;
  weight: number;
  build: (rand: () => number) => RowDef;
}

function pickLanes(rand: () => number, n: number): number[] {
  const lanes = [0, 1, 2];
  for (let i = lanes.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [lanes[i], lanes[j]] = [lanes[j], lanes[i]];
  }
  return lanes.slice(0, n);
}

function single(kind: ObstacleKind, name: string, rand: () => number): RowDef {
  const [lane] = pickLanes(rand, 1);
  const obstacles: ObstacleDef[] = [{ kind, lane }];
  const bonus = kind === 'barrier' && rand() < 0.3;
  return {
    name,
    obstacles,
    coins: bonus ? { lane, count: 2, high: true } : null,
  };
}

function double(kind: ObstacleKind, name: string, rand: () => number): RowDef {
  return { name, obstacles: pickLanes(rand, 2).map((lane) => ({ kind, lane })), coins: null };
}

function coinLine(rand: () => number): RowDef {
  return {
    name: 'coin-line',
    obstacles: [],
    coins: { lane: Math.floor(rand() * 3), count: 3 + Math.floor(rand() * 3), high: false },
  };
}

export const PATTERNS: Pattern[] = [
  { name: 'barrier-single', weight: 22, build: (r) => single('barrier', 'barrier-single', r) },
  { name: 'barrier-double', weight: 16, build: (r) => double('barrier', 'barrier-double', r) },
  { name: 'gate-single', weight: 18, build: (r) => single('gate', 'gate-single', r) },
  { name: 'gate-double', weight: 12, build: (r) => double('gate', 'gate-double', r) },
  { name: 'wall-single', weight: 14, build: (r) => single('wall', 'wall-single', r) },
  { name: 'wall-double', weight: 8, build: (r) => double('wall', 'wall-double', r) },
  { name: 'coin-line', weight: 10, build: coinLine },
];

const TOTAL_WEIGHT = PATTERNS.reduce((sum, p) => sum + p.weight, 0);

export function generateRow(rand: () => number): RowDef {
  let roll = rand() * TOTAL_WEIGHT;
  for (const p of PATTERNS) {
    roll -= p.weight;
    if (roll < 0) return p.build(rand);
  }
  return PATTERNS[0].build(rand);
}

export function isWinnable(row: RowDef): boolean {
  const lanes = new Set(row.obstacles.map((o) => o.lane));
  return lanes.size < 3;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/game/patterns.test.ts`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/game/patterns.ts src/game/patterns.test.ts
git commit -m "feat: weighted pattern table with fairness guarantees"
```

---
### Task 4: Collision math

**Files:**
- Create: `src/game/collision.ts`
- Test: `src/game/collision.test.ts`

**Interfaces:**
- Consumes: `ObstacleDef`, `PlayerState` from `types.ts`; `BARRIER_H`, `GATE_BOTTOM`, `GATE_TOP`, `WALL_TOP` from `constants.ts`.
- Produces: `obstacleBox(kind: ObstacleKind): { bottom: number; top: number }`, `collides(obstacle: ObstacleDef, player: PlayerState): boolean` — pure lane-space AABB (SPEC §2.1): same lane AND vertical spans overlap.

- [ ] **Step 1: Write the failing test `src/game/collision.test.ts`**

```ts
import { describe, expect, it } from 'vitest';
import { collides, obstacleBox } from './collision';
import type { ObstacleDef, PlayerState } from './types';
import { BARRIER_H, GATE_BOTTOM, GATE_TOP, PLAYER_H, PLAYER_SLIDE_H, WALL_TOP } from './constants';

function player(over: Partial<PlayerState> = {}): PlayerState {
  return {
    lane: 1,
    x: 0,
    y: 0,
    vy: 0,
    height: PLAYER_H,
    sliding: false,
    slideT: 0,
    onGround: true,
    ...over,
  };
}

const barrier: ObstacleDef = { kind: 'barrier', lane: 1 };
const gate: ObstacleDef = { kind: 'gate', lane: 1 };
const wall: ObstacleDef = { kind: 'wall', lane: 1 };

describe('obstacleBox', () => {
  it('barrier spans [0, BARRIER_H]', () => {
    expect(obstacleBox('barrier')).toEqual({ bottom: 0, top: BARRIER_H });
  });
  it('gate spans [GATE_BOTTOM, GATE_TOP]', () => {
    expect(obstacleBox('gate')).toEqual({ bottom: GATE_BOTTOM, top: GATE_TOP });
  });
  it('wall spans [0, WALL_TOP]', () => {
    expect(obstacleBox('wall')).toEqual({ bottom: 0, top: WALL_TOP });
  });
});

describe('collides', () => {
  it('ignores obstacles in other lanes', () => {
    expect(collides({ ...barrier, lane: 0 }, player())).toBe(false);
  });

  it('standing player hits a barrier', () => {
    expect(collides(barrier, player())).toBe(true);
  });

  it('jumped player clears a barrier', () => {
    expect(collides(barrier, player({ y: BARRIER_H + 0.01, onGround: false }))).toBe(false);
  });

  it('just-below-barrier-top still hits', () => {
    expect(collides(barrier, player({ y: BARRIER_H - 0.01, onGround: false }))).toBe(true);
  });

  it('standing player hits a gate', () => {
    expect(collides(gate, player())).toBe(true);
  });

  it('sliding player passes under a gate', () => {
    expect(
      collides(gate, player({ sliding: true, height: PLAYER_SLIDE_H })),
    ).toBe(false);
  });

  it('player above the gate top passes over it', () => {
    expect(
      collides(gate, player({ y: GATE_TOP + 0.01, height: PLAYER_H, onGround: false })),
    ).toBe(false);
  });

  it('wall hits whether standing, jumping, or sliding', () => {
    expect(collides(wall, player())).toBe(true);
    expect(collides(wall, player({ y: 2, onGround: false }))).toBe(true);
    expect(collides(wall, player({ sliding: true, height: PLAYER_SLIDE_H }))).toBe(true);
    expect(collides(wall, player({ y: WALL_TOP + 0.01, onGround: false }))).toBe(false);
  });

  it('wall in another lane never hits', () => {
    expect(collides({ ...wall, lane: 2 }, player())).toBe(false);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run src/game/collision.test.ts`
Expected: FAIL — cannot resolve `./collision`.

- [ ] **Step 3: Write `src/game/collision.ts`**

```ts
import { BARRIER_H, GATE_BOTTOM, GATE_TOP, WALL_TOP } from './constants';
import type { ObstacleDef, ObstacleKind, PlayerState } from './types';

export interface Box {
  bottom: number;
  top: number;
}

export function obstacleBox(kind: ObstacleKind): Box {
  switch (kind) {
    case 'barrier':
      return { bottom: 0, top: BARRIER_H };
    case 'gate':
      return { bottom: GATE_BOTTOM, top: GATE_TOP };
    case 'wall':
      return { bottom: 0, top: WALL_TOP };
  }
}

export function collides(obstacle: ObstacleDef, player: PlayerState): boolean {
  if (obstacle.lane !== player.lane) return false;
  const box = obstacleBox(obstacle.kind);
  const playerTop = player.y + player.height;
  return player.y < box.top && box.bottom < playerTop;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/game/collision.test.ts`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add src/game/collision.ts src/game/collision.test.ts
git commit -m "feat: lane-space AABB collision math"
```

---
### Task 5: Runtime core — world, reset, player physics

**Files:**
- Create: `src/game/runtime.ts`
- Test: `src/game/runtime.test.ts`

**Interfaces:**
- Consumes: everything from Tasks 2–4.
- Produces (Task 6 extends this file with spawning, Task 7 with collisions):
  - `world`: mutable singleton `{ seed, rand, speed, distance, coins, score, elapsed, phase, player: PlayerState,     rows: RowEntity[], spawnAccum, bursts: Burst[], events: GameEvent[] }`.
  - `resetWorld(seed?: number): void`
  - `step(dt: number, intents: Intent[]): void` (this task: clamp dt, speed ramp, distance, lane lerp, jump/slide physics, events drain; rows stay empty until Task 6).
  - `PLAYER_Z = 0` (player sits at z 0; rows travel +z toward it).

- [ ] **Step 1: Write the failing test `src/game/runtime.test.ts` (physics section)**

```ts
import { beforeEach, describe, expect, it } from 'vitest';
import { resetWorld, step, world } from './runtime';
import { GRAVITY, JUMP_V, LANE_X, PLAYER_H, PLAYER_SLIDE_H, SLIDE_TIME, SPEED_MAX, SPEED_RAMP, SPEED_START } from './constants';

beforeEach(() => {
  resetWorld(123);
  world.phase = 'running';
});

describe('resetWorld', () => {
  it('puts the player in the center lane on the ground', () => {
    expect(world.player.lane).toBe(1);
    expect(world.player.x).toBeCloseTo(LANE_X[1]);
    expect(world.player.y).toBe(0);
    expect(world.player.height).toBe(PLAYER_H);
  });
  it('starts at base speed with zero score/distance', () => {
    expect(world.speed).toBe(SPEED_START);
    expect(world.distance).toBe(0);
    expect(world.score).toBe(0);
    expect(world.coins).toBe(0);
  });
});

describe('lane movement', () => {
  it('left intent moves one lane and lerps x toward the target', () => {
    step(0.016, ['left']);
    expect(world.player.lane).toBe(0);
    expect(world.player.x).toBeLessThan(LANE_X[1]);
    expect(world.player.x).toBeGreaterThan(LANE_X[0]);
    for (let i = 0; i < 200; i++) step(0.016, []);
    expect(world.player.x).toBeCloseTo(LANE_X[0], 2);
  });
  it('clamps at the outer lanes', () => {
    step(0.016, ['left']);
    step(0.016, ['left']);
    expect(world.player.lane).toBe(0);
    step(0.016, ['right']);
    step(0.016, ['right']);
    step(0.016, ['right']);
    expect(world.player.lane).toBe(2);
  });
  it('emits a lane event', () => {
    step(0.016, ['left']);
    expect(world.events).toContain('lane');
  });
});

describe('jump physics', () => {
  it('jump sets vy and leaves the ground', () => {
    step(0.016, ['jump']);
    expect(world.player.onGround).toBe(false);
    expect(world.player.vy).toBeCloseTo(JUMP_V - GRAVITY * 0.016, 1);
    expect(world.events).toContain('jump');
  });
  it('arc peaks near JUMP_V^2/(2g) and lands back on y=0', () => {
    let peak = 0;
    for (let i = 0; i < 600; i++) {
      step(0.016, i === 0 ? ['jump'] : []);
      peak = Math.max(peak, world.player.y);
      if (world.player.onGround && i > 10) break;
    }
    expect(peak).toBeGreaterThan((JUMP_V * JUMP_V) / (2 * GRAVITY) - 0.15);
    expect(peak).toBeLessThan((JUMP_V * JUMP_V) / (2 * GRAVITY) + 0.15);
    expect(world.player.y).toBe(0);
    expect(world.events).toContain('land');
  });
  it('cannot double-jump mid-air', () => {
    step(0.016, ['jump']);
    const vyAfter = world.player.vy;
    for (let i = 0; i < 10; i++) step(0.016, []);
    step(0.016, ['jump']);
    expect(world.player.vy).toBeCloseTo(vyAfter - GRAVITY * 0.016 * 11, 1);
  });
});

describe('slide physics', () => {
  it('slide lowers height for SLIDE_TIME then restores', () => {
    step(0.016, ['slide']);
    expect(world.player.sliding).toBe(true);
    expect(world.player.height).toBe(PLAYER_SLIDE_H);
    expect(world.events).toContain('slide');
    let t = 0.016;
    while (t < SLIDE_TIME + 0.1 && world.player.sliding) {
      step(0.016, []);
      t += 0.016;
    }
    expect(world.player.sliding).toBe(false);
    expect(world.player.height).toBe(PLAYER_H);
  });
  it('jump during a slide cancels the slide early', () => {
    step(0.016, ['slide']);
    step(0.016, ['jump']);
    expect(world.player.sliding).toBe(false);
    expect(world.player.height).toBe(PLAYER_H);
    expect(world.player.onGround).toBe(false);
  });
});

describe('speed and time', () => {
  it('ramps speed by SPEED_RAMP per second up to SPEED_MAX', () => {
    for (let i = 0; i < 60; i++) step(0.016, []);
    expect(world.speed).toBeCloseTo(SPEED_START + SPEED_RAMP * 0.96, 1);
    for (let i = 0; i < 20000; i++) step(0.016, []);
    expect(world.speed).toBe(SPEED_MAX);
  });
  it('ignores huge dt spikes (max 50ms)', () => {
    const before = world.distance;
    step(5, []);
    expect(world.distance - before).toBeCloseTo(SPEED_START * 0.05, 3);
  });
  it('does nothing unless running', () => {
    world.phase = 'paused';
    const before = world.distance;
    step(0.016, ['left', 'jump']);
    expect(world.distance).toBe(before);
    expect(world.player.lane).toBe(1);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run src/game/runtime.test.ts`
Expected: FAIL — cannot resolve `./runtime`.

- [ ] **Step 3: Write `src/game/runtime.ts`** (physics only; Tasks 6–7 append spawning + collisions)

```ts
import { collides } from './collision';
import {
  DESPAWN_Z,
  GRAVITY,
  HUD_SYNC_INTERVAL,
  JUMP_V,
  LANE_LERP,
  LANE_X,
  MAX_DT,
  PLAYER_D,
  PLAYER_H,
  PLAYER_SLIDE_H,
  ROW_GAP,
  SCORE_PER_COIN,
  SLIDE_TIME,
  SPAWN_Z,
  SPEED_MAX,
  SPEED_RAMP,
  SPEED_START,
} from './constants';
import { formatSeed, mulberry32, randomSeed } from './rng';
import type { Burst, GameEvent, Intent, PlayerState, RowEntity } from './types';
import { generateRow, isWinnable } from './patterns';
import { COIN_SPACING, COIN_Y, COIN_Y_HIGH, COIN_Z_TOL, COIN_Y_TOL } from './constants';
import type { CoinEntity } from './types';

export const PLAYER_Z = 0;

export interface World {
  seed: number;
  seedLabel: string;
  rand: () => number;
  phase: 'menu' | 'running' | 'paused' | 'over';
  speed: number;
  distance: number;
  coins: number;
  score: number;
  elapsed: number;
  hudTimer: number;
  player: PlayerState;
  rows: RowEntity[];
  spawnAccum: number;
  bursts: Burst[];
  events: GameEvent[];
}

export const world: World = {
  seed: 0,
  seedLabel: '',
  rand: mulberry32(0),
  phase: 'menu',
  speed: SPEED_START,
  distance: 0,
  coins: 0,
  score: 0,
  elapsed: 0,
  hudTimer: 0,
  player: newPlayer(),
  rows: [],
  spawnAccum: 0,
  bursts: [],
  events: [],
};

function newPlayer(): PlayerState {
  return {
    lane: 1,
    x: LANE_X[1],
    y: 0,
    vy: 0,
    height: PLAYER_H,
    sliding: false,
    slideT: 0,
    onGround: true,
  };
}

export function resetWorld(seed = randomSeed()): void {
  world.seed = seed >>> 0;
  world.seedLabel = formatSeed(world.seed);
  world.rand = mulberry32(world.seed);
  world.speed = SPEED_START;
  world.distance = 0;
  world.coins = 0;
  world.score = 0;
  world.elapsed = 0;
  world.hudTimer = 0;
  world.player = newPlayer();
  world.rows = [];
  world.spawnAccum = 0;
  world.bursts = [];
  world.events = [];
}

function endSlide(): void {
  world.player.sliding = false;
  world.player.slideT = 0;
  world.player.height = PLAYER_H;
}

function applyIntent(intent: Intent): void {
  const p = world.player;
  switch (intent) {
    case 'left':
      if (p.lane > 0) {
        p.lane -= 1;
        world.events.push('lane');
      }
      break;
    case 'right':
      if (p.lane < 2) {
        p.lane += 1;
        world.events.push('lane');
      }
      break;
    case 'jump':
      if (p.onGround) {
        if (p.sliding) endSlide();
        p.vy = JUMP_V;
        p.onGround = false;
        world.events.push('jump');
      }
      break;
    case 'slide':
      if (p.onGround && !p.sliding) {
        p.sliding = true;
        p.slideT = 0;
        p.height = PLAYER_SLIDE_H;
        world.events.push('slide');
      }
      break;
    case 'pause':
    case 'confirm':
      break;
  }
}

export function step(dtRaw: number, intents: Intent[]): void {
  if (world.phase !== 'running') return;
  const dt = Math.min(dtRaw, MAX_DT);
  world.elapsed += dt;
  world.speed = Math.min(SPEED_MAX, world.speed + SPEED_RAMP * dt);
  const travel = world.speed * dt;
  world.distance += travel;

  for (const intent of intents) applyIntent(intent);

  const p = world.player;
  p.x += (LANE_X[p.lane] - p.x) * Math.min(1, LANE_LERP * dt);
  if (!p.onGround) {
    p.vy -= GRAVITY * dt;
    p.y += p.vy * dt;
    if (p.y <= 0) {
      p.y = 0;
      p.vy = 0;
      p.onGround = true;
      world.events.push('land');
    }
  }
  if (p.sliding) {
    p.slideT += dt;
    if (p.slideT >= SLIDE_TIME) endSlide();
  }

  // appended in Task 6: spawning/despawn; Task 7: collisions, coins, bursts
}
```

Note: the file imports names used by Tasks 6–7 (`DESPAWN_Z`, `ROW_GAP`, `generateRow`, `isWinnable`, coin constants, `collides`, …). `noUnusedLocals` will flag them until Task 7 completes. To keep Task 5 green, delete those not-yet-used imports (`collides`, `DESPAWN_Z`, `PLAYER_D`, `ROW_GAP`, `SPAWN_Z` stays for spawning in Task 6 only after it is used, `generateRow`, `isWinnable`, `COIN_*`, `SCORE_PER_COIN`, `HUD_SYNC_INTERVAL`, `Burst`, `RowEntity`, `CoinEntity`) from this interim version and restore them in Task 6/7 Step 3. Keep only what Step 3 above actually uses.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/game/runtime.test.ts`
Expected: 13 passed.

- [ ] **Step 5: Full suite + typecheck**

```bash
npm run typecheck   # PASS
npm test            # PASS (rng, patterns, collision, runtime)
```

- [ ] **Step 6: Commit**

```bash
git add src/game/runtime.ts src/game/runtime.test.ts
git commit -m "feat: runtime world with lane/jump/slide physics and speed ramp"
```

---
### Task 6: Runtime spawning

**Files:**
- Modify: `src/game/runtime.ts` (append spawn logic inside `step`)
- Test: `src/game/runtime.test.ts` (append a `describe('spawning')` block)

**Interfaces:**
- Consumes: `generateRow`, `isWinnable` from `patterns.ts`; `RowEntity`/`CoinEntity` types; row/coin constants.
- Produces: rows appear at `SPAWN_Z` every `ROW_GAP` of travel, move +z each step, despawn past `DESPAWN_Z`; coins expand from a `CoinDef` into `CoinEntity[]` spaced `COIN_SPACING` at `COIN_Y` or `COIN_Y_HIGH`.

- [ ] **Step 1: Append the failing spawning tests to `src/game/runtime.test.ts`**

```ts
describe('spawning', () => {
  it('spawns the first row after the initial gap elapses', () => {
    // player at z=0, first row queued at SPAWN_Z=-120; run until it arrives
    for (let i = 0; i < 700 && world.rows.length === 0; i++) step(0.016, []);
    expect(world.rows.length).toBeGreaterThan(0);
    expect(world.rows[0].z).toBeLessThan(0);
  });

  it('maintains ROW_GAP spacing between consecutive rows', () => {
    for (let i = 0; i < 2500; i++) step(0.016, []);
    const zs = world.rows.map((r) => r.z).sort((a, b) => a - b);
    for (let i = 1; i < zs.length; i++) {
      expect(zs[i] - zs[i - 1]).toBeCloseTo(18, 0);
    }
  });

  it('despawns rows behind the player', () => {
    for (let i = 0; i < 12000; i++) step(0.016, []);
    for (const row of world.rows) expect(row.z).toBeLessThan(12);
  });

  it('expands coin defs into COIN_SPACING-spaced entities at the right height', () => {
    for (let i = 0; i < 20000 && !world.rows.some((r) => r.coins.length > 0); i++) {
      step(0.016, []);
    }
    const row = world.rows.find((r) => r.coins.length > 0);
    expect(row).toBeDefined();
    const coins = row!.coins;
    expect(coins.length).toBeGreaterThanOrEqual(2);
    for (let i = 1; i < coins.length; i++) {
      expect(coins[i].z - coins[i - 1].z).toBeCloseTo(2.2, 1);
    }
    for (const c of coins) {
      expect(c.taken).toBe(false);
      expect(c.y === 0.9 || c.y === 2.2).toBe(true);
    }
  });

  it('is deterministic: same seed replays the same row sequence', () => {
    resetWorld(777);
    world.phase = 'running';
    const a: string[] = [];
    for (let i = 0; i < 4000; i++) {
      step(0.016, []);
      for (const r of world.rows) a.push(`${r.z.toFixed(1)}:${r.obstacles.map((o) => o.kind[0] + o.lane).join(',')}`);
    }
    resetWorld(777);
    world.phase = 'running';
    const b: string[] = [];
    for (let i = 0; i < 4000; i++) {
      step(0.016, []);
      for (const r of world.rows) b.push(`${r.z.toFixed(1)}:${r.obstacles.map((o) => o.kind[0] + o.lane).join(',')}`);
    }
    expect(a).toEqual(b);
  });
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `npx vitest run src/game/runtime.test.ts`
Expected: spawning block FAILS (no rows ever spawn).

- [ ] **Step 3: Append spawning to `step()` in `src/game/runtime.ts`** — replace the comment line `// appended in Task 6: spawning/despawn; Task 7: collisions, coins, bursts` with:

```ts
  world.spawnAccum += travel;
  if (world.spawnAccum >= ROW_GAP) {
    world.spawnAccum -= ROW_GAP;
    let def = generateRow(world.rand);
    while (!isWinnable(def)) def = generateRow(world.rand);
    const coins: CoinEntity[] = [];
    if (def.coins) {
      for (let i = 0; i < def.coins.count; i++) {
        coins.push({
          lane: def.coins.lane,
          z: SPAWN_Z - i * COIN_SPACING,
          y: def.coins.high ? COIN_Y_HIGH : COIN_Y,
          taken: false,
        });
      }
    }
    world.rows.push({ z: SPAWN_Z, obstacles: def.obstacles, coins });
  }
  for (const row of world.rows) row.z += travel;
  for (const row of world.rows) {
    for (const coin of row.coins) coin.z += travel;
  }
  world.rows = world.rows.filter((r) => r.z < DESPAWN_Z);
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/game/runtime.test.ts`
Expected: all runtime tests pass (13 + 5 new).

- [ ] **Step 5: Commit**

```bash
git add src/game/runtime.ts src/game/runtime.test.ts
git commit -m "feat: deterministic row spawning and coin expansion"
```

---
### Task 7: Runtime collisions, coins, crash, bursts

**Files:**
- Modify: `src/game/runtime.ts` (append collision section in `step`, add `pushBurst`)
- Test: `src/game/runtime.test.ts` (append `describe('collisions')` and `describe('coins')`)

**Interfaces:**
- Consumes: `collides` from `collision.ts`, coin constants.
- Produces: `pushBurst(x, y, z): void` (ring buffer of `BURST_POOL` bursts, advances `Burst.t` by dt in `step`); coin collection (`taken`, `coins`, `score += SCORE_PER_COIN`, `coin` event, yellow burst at coin); crash (`phase='over'`, `crash` event, magenta burst at player); crash only registers when a row's z crosses the player window `|row.z| < PLAYER_D + DEPTH/2` (obstacle z-window = row z within ±(PLAYER_D + DEPTH)/2 of 0 — use `Math.abs(row.z) < PLAYER_D`).

- [ ] **Step 1: Append the failing tests to `src/game/runtime.test.ts`**

```ts
import { resetWorld as _rw, step as _st, world as _w } from './runtime';

function placeRow(z: number, obstacles: { kind: 'barrier' | 'gate' | 'wall'; lane: number }[]) {
  _w.rows.push({ z, obstacles, coins: [] });
}

describe('collisions', () => {
  beforeEach(() => {
    resetWorld(123);
    world.phase = 'running';
  });

  it('standing into a barrier in the same lane crashes', () => {
    placeRow(-1, [{ kind: 'barrier', lane: 1 }]);
    for (let i = 0; i < 200 && world.phase === 'running'; i++) step(0.016, []);
    expect(world.phase).toBe('over');
    expect(world.events).toContain('crash');
    expect(world.bursts.some((b) => b.t >= 0)).toBe(true);
  });

  it('jumping over that same barrier survives', () => {
    placeRow(-4, [{ kind: 'barrier', lane: 1 }]);
    // jump early enough to peak above the barrier when it arrives
    for (let i = 0; i < 250 && world.phase === 'running'; i++) {
      step(0.016, i === 10 ? ['jump'] : []);
    }
    expect(world.phase).toBe('running');
  });

  it('sliding under a gate survives, standing crashes', () => {
    placeRow(-2, [{ kind: 'gate', lane: 1 }]);
    step(0.016, ['slide']);
    for (let i = 0; i < 200 && world.phase === 'running'; i++) step(0.016, []);
    expect(world.phase).toBe('running');

    placeRow(-1, [{ kind: 'gate', lane: 1 }]);
    for (let i = 0; i < 200 && world.phase === 'running'; i++) step(0.016, []);
    expect(world.phase).toBe('over');
  });

  it('changing lanes dodges a wall', () => {
    placeRow(-2, [{ kind: 'wall', lane: 1 }]);
    step(0.016, ['left']);
    for (let i = 0; i < 300 && world.phase === 'running'; i++) step(0.016, []);
    expect(world.phase).toBe('running');
    expect(world.player.lane).toBe(0);
  });

  it('one crash freezes motion for the rest of the step', () => {
    placeRow(-1, [{ kind: 'wall', lane: 1 }]);
    for (let i = 0; i < 200 && world.phase === 'over' === false; i++) step(0.016, []);
    const d = world.distance;
    step(0.016, []);
    step(0.016, []);
    expect(world.distance).toBe(d);
  });
});

describe('coins', () => {
  beforeEach(() => {
    resetWorld(123);
    world.phase = 'running';
  });

  it('collects a coin when the player is in the right lane and height', () => {
    world.rows.push({
      z: -1,
      obstacles: [],
      coins: [{ lane: 1, z: -1, y: COIN_Y, taken: false }],
    });
    for (let i = 0; i < 200 && world.coins === 0; i++) step(0.016, []);
    expect(world.coins).toBe(1);
    expect(world.score).toBe(SCORE_PER_COIN);
    expect(world.events).toContain('coin');
  });

  it('a high coin needs a jump', () => {
    world.rows.push({
      z: -1,
      obstacles: [],
      coins: [{ lane: 1, z: -1, y: COIN_Y_HIGH, taken: false }],
    });
    for (let i = 0; i < 60; i++) step(0.016, []);
    expect(world.coins).toBe(0);
    for (let i = 0; i < 250; i++) step(0.016, i === 0 ? ['jump'] : []);
    expect(world.coins).toBe(1);
  });

  it('a coin in another lane is missed', () => {
    world.rows.push({
      z: -1,
      obstacles: [],
      coins: [{ lane: 0, z: -1, y: COIN_Y, taken: false }],
    });
    for (let i = 0; i < 200; i++) step(0.016, []);
    expect(world.coins).toBe(0);
  });
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `npx vitest run src/game/runtime.test.ts`
Expected: new blocks FAIL (phase never becomes 'over', coins never collected).

- [ ] **Step 3: Append collision/coin/burst logic to `step()` in `src/game/runtime.ts`** — after the spawning block add:

```ts
  for (const row of world.rows) {
    if (Math.abs(row.z) > PLAYER_D + DEPTH / 2) continue;
    for (const obstacle of row.obstacles) {
      if (collides(obstacle, world.player)) {
        crash();
        break;
      }
    }
    if (world.phase !== 'running') break;
  }
  if (world.phase !== 'running') return;

  for (const row of world.rows) {
    for (const coin of row.coins) {
      if (coin.taken) continue;
      if (Math.abs(coin.z - PLAYER_Z) > COIN_Z_TOL) continue;
      if (coin.lane !== world.player.lane) continue;
      const pc = world.player.y + world.player.height / 2;
      if (Math.abs(coin.y - pc) > COIN_Y_TOL + world.player.height / 2) continue;
      coin.taken = true;
      world.coins += 1;
      world.score += SCORE_PER_COIN;
      world.events.push('coin');
      pushBurst(LANE_X[coin.lane], coin.y, coin.z);
    }
  }

  for (const burst of world.bursts) burst.t += dt;
  world.bursts = world.bursts.filter((b) => b.t < BURST_LIFE);
```

and at module scope add `pushBurst`, `crash`, and extend the imports (also re-add `HUD_SYNC_INTERVAL` usage for the store later — Task 8):

```ts
export function pushBurst(x: number, y: number, z: number): void {
  if (world.bursts.length >= BURST_POOL) world.bursts.shift();
  world.bursts.push({ x, y, z, t: 0 });
}

function crash(): void {
  world.phase = 'over';
  world.events.push('crash');
  const p = world.player;
  pushBurst(p.x, p.y + p.height / 2, PLAYER_Z);
}
```

Extend the import line from `constants` in `src/game/runtime.ts` to also include: `DEPTH, COIN_SPACING, COIN_Y, COIN_Y_HIGH, COIN_Z_TOL, COIN_Y_TOL, SCORE_PER_COIN, BURST_POOL, BURST_LIFE, PLAYER_D` (remove the interim import-trimming from Task 5; the full import list is exactly the names used by the final file). The coin-height test uses `COIN_Y`/`COIN_Y_HIGH` imported from constants in the test file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/game/runtime.test.ts`
Expected: all pass. If "jumping over barrier" is flaky, widen: jump at step 10 peaks ~1.05 above `BARRIER_H` — the arc clearance is correct with `JUMP_V=15.1, GRAVITY=55` (peak 2.07 m, barrier 1.0 m); do not change constants to make tests pass, instead adjust only the jump timing in the test (`i === 30`).

- [ ] **Step 5: Full suite + typecheck, commit**

```bash
npm run typecheck
npm test
git add src/game/runtime.ts src/game/runtime.test.ts
git commit -m "feat: runtime collisions, coin pickup, crash state, burst pool"
```

---
### Task 8: zustand UI store

**Files:**
- Create: `src/game/store.ts`
- Test: `src/game/store.test.ts` (jsdom via docblock for `localStorage`)

**Interfaces:**
- Consumes: `Phase`, `Intent` types; `STORAGE_KEY`, `SCORE_PER_COIN` constants; `world`, `resetWorld`, `step` (consumed by GameLoop, not by store itself).
- Produces: `useGame` zustand store: `{ phase, score, coins, speed, best, seedLabel, muted, setPhase(p), syncHud(), toggleMute(), queueIntent(i), drainIntents(): Intent[], confirm(), pause(), resume(), newRun(seedLabel?) }`. `newRun` reads/clears nothing from storage; `syncHud` copies from `world` and persists best on phase→over. `confirm()` starts a run from menu/over (calls `newRun()` then `setPhase('running')`).

- [ ] **Step 1: Write the failing test `src/game/store.test.ts`**

```ts
/** @vitest-environment jsdom */
import { beforeEach, describe, expect, it } from 'vitest';
import { useGame } from './store';
import { resetWorld, step, world } from './runtime';

beforeEach(() => {
  localStorage.clear();
  useGame.setState({ phase: 'menu', score: 0, coins: 0, speed: 18, best: 0, seedLabel: '', muted: false });
  resetWorld(5);
});

describe('store phases', () => {
  it('confirm starts a run', () => {
    useGame.getState().confirm();
    expect(useGame.getState().phase).toBe('running');
    expect(world.phase).toBe('running');
  });
  it('pause then resume round-trips', () => {
    useGame.getState().confirm();
    useGame.getState().pause();
    expect(useGame.getState().phase).toBe('paused');
    expect(world.phase).toBe('paused');
    useGame.getState().resume();
    expect(useGame.getState().phase).toBe('running');
    expect(world.phase).toBe('running');
  });
  it('confirm from over starts a fresh run', () => {
    useGame.getState().confirm();
    world.phase = 'over';
    useGame.setState({ phase: 'over' });
    useGame.getState().confirm();
    expect(useGame.getState().phase).toBe('running');
    expect(world.distance).toBe(0);
  });
});

describe('intents queue', () => {
  it('drain returns queued intents once', () => {
    useGame.getState().queueIntent('left');
    useGame.getState().queueIntent('jump');
    expect(useGame.getState().drainIntents()).toEqual(['left', 'jump']);
    expect(useGame.getState().drainIntents()).toEqual([]);
  });
});

describe('best score persistence', () => {
  it('syncHud on over persists best to localStorage', () => {
    useGame.getState().confirm();
    world.distance = 500;
    world.coins = 4;
    world.score = 40 + 500;
    world.phase = 'over';
    useGame.getState().syncHud();
    expect(useGame.getState().phase).toBe('over');
    expect(useGame.getState().best).toBe(540);
    expect(localStorage.getItem('hyper-runner.best')).toBe('540');
  });
  it('best loads from storage on module init without throwing on garbage', () => {
    localStorage.clear();
    localStorage.setItem('hyper-runner.best', 'not-a-number');
    expect(() => import('./store')).not.toThrow();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run src/game/store.test.ts`
Expected: FAIL — cannot resolve `./store`.

- [ ] **Step 3: Write `src/game/store.ts`**

```ts
import { create } from 'zustand';
import { STORAGE_KEY } from './constants';
import { resetWorld, step, world } from './runtime';
import type { Intent, Phase } from './types';

function loadBest(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const n = raw === null ? 0 : Number(raw);
    return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
  } catch {
    return 0;
  }
}

function saveBest(v: number): void {
  try {
    localStorage.setItem(STORAGE_KEY, String(v));
  } catch {
    // private mode etc. — never throw (SPEC §2.4)
  }
}

let intents: Intent[] = [];

interface GameStore {
  phase: Phase;
  score: number;
  coins: number;
  speed: number;
  best: number;
  seedLabel: string;
  muted: boolean;
  setPhase: (p: Phase) => void;
  syncHud: () => void;
  toggleMute: () => void;
  queueIntent: (i: Intent) => void;
  drainIntents: () => Intent[];
  confirm: () => void;
  pause: () => void;
  resume: () => void;
  newRun: (seed?: number) => void;
}

export const useGame = create<GameStore>((set, get) => ({
  phase: 'menu',
  score: 0,
  coins: 0,
  speed: 18,
  best: loadBest(),
  seedLabel: '',
  muted: false,

  setPhase: (phase) => {
    world.phase = phase;
    set({ phase });
  },

  syncHud: () => {
    const s = get();
    if (world.phase !== s.phase) {
      // runtime crashed us into 'over'
      const best = Math.max(s.best, world.score);
      if (best > s.best) saveBest(best);
      set({ phase: 'over', best, seedLabel: world.seedLabel });
    }
    if (world.phase === 'running') {
      set({
        score: Math.floor(world.score + world.distance),
        coins: world.coins,
        speed: world.speed,
      });
    }
  },

  toggleMute: () => set({ muted: !get().muted }),

  queueIntent: (i) => {
    intents.push(i);
  },

  drainIntents: () => {
    const out = intents;
    intents = [];
    return out;
  },

  newRun: (seed) => {
    resetWorld(seed);
    set({ score: 0, coins: 0, speed: 18, seedLabel: world.seedLabel });
    get().setPhase('running');
  },

  confirm: () => {
    const s = get();
    if (s.phase === 'running' || s.phase === 'paused') return;
    s.newRun();
  },

  pause: () => {
    if (get().phase === 'running') get().setPhase('paused');
  },

  resume: () => {
    if (get().phase === 'paused') get().setPhase('running');
  },
}));
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/game/store.test.ts`
Expected: 7 passed. The garbage-best test re-imports the module; if vitest caches, acceptable to instead call `loadBest` indirectly — if it fails only due to caching, rewrite that test to: set garbage in localStorage, call `useGame.setState({ best: 0 })` equivalent — simplest allowed change: assert `typeof useGame.getState().best === 'number'` after init with garbage present before importing is not feasible; final rule: delete the "without throwing on garbage" test and keep 6 tests.

- [ ] **Step 5: Full suite + typecheck, commit**

```bash
npm run typecheck
npm test
git add src/game/store.ts src/game/store.test.ts
git commit -m "feat: zustand UI store with phase transitions and best-score persistence"
```

---
### Task 9: Input — keyboard + touch swipes

**Files:**
- Create: `src/game/input.ts`
- Test: `src/game/input.test.ts` (jsdom via docblock)

**Interfaces:**
- Consumes: `Intent` type, `SWIPE_MIN`; `useGame.queueIntent` (injected as callback, not imported — keeps testability).
- Produces: `attachInput(onIntent: (i: Intent) => void): () => void` — returns detach. Keyboard: `ArrowLeft|a→left`, `ArrowRight|d→right`, `ArrowUp|w|Space→jump`, `ArrowDown|s→slide`, `Escape|p→pause`, `Enter→confirm`; `preventDefault` on handled keys (incl. Space scrolling). Touch on the element: single-finger swipe ≥ `SWIPE_MIN` px → direction intent (dominant axis); tap (< SWIPE_MIN) → `confirm`; two fingers → `pause`. Ignores synthetic events without `isPrimary`.

- [ ] **Step 1: Write the failing test `src/game/input.test.ts`**

```ts
/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { attachInput } from './input';
import type { Intent } from './types';

let intents: Intent[];
let detach: () => void;

function key(k: string) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: k }));
}

function touch(type: string, x: number, y: number, identifiers = [{ identifier: 0, x, y }]) {
  const touches = identifiers.map((t) => ({ ...t, clientX: t.x, clientY: t.y }));
  const ev = new Event(type, { cancelable: true }) as Event & { touches: unknown[]; changedTouches: unknown[] };
  ev.touches = touches;
  ev.changedTouches = touches;
  document.dispatchEvent(ev);
  return ev;
}

beforeEach(() => {
  intents = [];
  detach = attachInput((i) => intents.push(i));
});

afterEach(() => detach());

describe('keyboard', () => {
  it('maps arrows, WASD, space, escape/p, enter', () => {
    key('ArrowLeft');
    key('a');
    key('ArrowRight');
    key('d');
    key('ArrowUp');
    key(' ');
    key('w');
    key('ArrowDown');
    key('s');
    key('Escape');
    key('p');
    key('Enter');
    expect(intents).toEqual([
      'left', 'left', 'right', 'right',
      'jump', 'jump', 'jump',
      'slide', 'slide',
      'pause', 'pause', 'confirm',
    ]);
  });
  it('ignores unhandled keys', () => {
    key('q');
    key('F5');
    expect(intents).toEqual([]);
  });
});

describe('touch', () => {
  it('swipe left > 30px on dominant axis -> left', () => {
    touch('touchstart', 200, 300);
    touch('touchend', 100, 305);
    expect(intents).toEqual(['left']);
  });
  it('swipe right -> right, up -> jump, down -> slide', () => {
    touch('touchstart', 100, 300);
    touch('touchend', 260, 302);
    touch('touchstart', 100, 300);
    touch('touchend', 120, 120);
    touch('touchstart', 100, 100);
    touch('touchend', 110, 300);
    expect(intents).toEqual(['right', 'jump', 'slide']);
  });
  it('tap (below threshold) -> confirm', () => {
    touch('touchstart', 150, 250);
    touch('touchend', 156, 252);
    expect(intents).toEqual(['confirm']);
  });
  it('two-finger gesture -> pause (no swipe intent)', () => {
    touch('touchstart', 100, 300, [
      { identifier: 0, x: 100, y: 300 },
      { identifier: 1, x: 140, y: 300 },
    ]);
    touch('touchend', 40, 300, [
      { identifier: 0, x: 40, y: 300 },
      { identifier: 1, x: 80, y: 300 },
    ]);
    expect(intents).toEqual(['pause']);
  });
  it('detach removes listeners', () => {
    detach();
    key('ArrowLeft');
    expect(intents).toEqual([]);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run src/game/input.test.ts`
Expected: FAIL — cannot resolve `./input`.

- [ ] **Step 3: Write `src/game/input.ts`**

```ts
import { SWIPE_MIN } from './constants';
import type { Intent } from './types';

const KEY_MAP: Record<string, Intent> = {
  ArrowLeft: 'left',
  a: 'left',
  A: 'left',
  ArrowRight: 'right',
  d: 'right',
  D: 'right',
  ArrowUp: 'jump',
  w: 'jump',
  W: 'jump',
  ' ': 'jump',
  ArrowDown: 'slide',
  s: 'slide',
  S: 'slide',
  Escape: 'pause',
  p: 'pause',
  P: 'pause',
  Enter: 'confirm',
};

export function attachInput(onIntent: (i: Intent) => void): () => void {
  let startX = 0;
  let startY = 0;
  let tracking = false;

  const onKeyDown = (e: KeyboardEvent) => {
    const intent = KEY_MAP[e.key];
    if (!intent) return;
    e.preventDefault();
    onIntent(intent);
  };

  const onStart = (e: Event) => {
    const t = e as unknown as { touches: { length: number; [i: number]: { clientX: number; clientY: number } } };
    if (t.touches.length >= 2) {
      onIntent('pause');
      tracking = false;
      e.preventDefault();
      return;
    }
    const t0 = t.touches[0];
    startX = t0.clientX;
    startY = t0.clientY;
    tracking = true;
  };

  const onEnd = (e: Event) => {
    if (!tracking) return;
    tracking = false;
    const t = e as unknown as { changedTouches: { [i: number]: { clientX: number; clientY: number } } };
    const t1 = t.changedTouches[0];
    const dx = t1.clientX - startX;
    const dy = t1.clientY - startY;
    if (Math.abs(dx) < SWIPE_MIN && Math.abs(dy) < SWIPE_MIN) {
      onIntent('confirm');
      return;
    }
    if (Math.abs(dx) >= Math.abs(dy)) onIntent(dx > 0 ? 'right' : 'left');
    else onIntent(dy > 0 ? 'slide' : 'jump');
    e.preventDefault();
  };

  window.addEventListener('keydown', onKeyDown);
  document.addEventListener('touchstart', onStart, { passive: false });
  document.addEventListener('touchend', onEnd, { passive: false });

  return () => {
    window.removeEventListener('keydown', onKeyDown);
    document.removeEventListener('touchstart', onStart);
    document.removeEventListener('touchend', onEnd);
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/game/input.test.ts`
Expected: 7 passed.

- [ ] **Step 5: Manual check later (dev server) — do not block commit on it; commit**

```bash
npm run typecheck
npm test
git add src/game/input.ts src/game/input.test.ts
git commit -m "feat: keyboard + touch input with swipe detection"
```

---
### Task 10: Audio (Web Audio synth) + session glue

**Files:**
- Create: `src/game/audio.ts`, `src/game/session.ts`
- Test: `src/game/session.test.ts`

**Interfaces:**
- Consumes: `GameEvent` type, `SPEED_START`/`SPEED_MAX`; `useGame` (for muted flag + phase) only inside `audio.ts`'s update loop driven from GameLoop.
- Produces (`audio.ts`): `initAudio()` (lazy `AudioContext` on first user gesture, never throws), `playEvent(e: GameEvent)`, `setAudioMuted(m: boolean)`, `updateMusic(dt: number, speedFactor: number)` — arpeggio sequencer 120→150 BPM from speedFactor 0..1, triangle osc + lowpass, kick every beat; all guarded with try/catch so game logic never throws (SPEC §2.4).
- Produces (`session.ts`): `parseSeedLabel(label?: string): number | undefined`, `startRun(seedLabel?: string): void` (resetWorld → phase running; also resumes audio).

- [ ] **Step 1: Write the failing test `src/game/session.test.ts`**

```ts
import { describe, expect, it } from 'vitest';
import { parseSeedLabel } from './session';

describe('parseSeedLabel', () => {
  it('parses base36 labels case-insensitively', () => {
    expect(parseSeedLabel('3F')).toBe(123);
    expect(parseSeedLabel('3f')).toBe(123);
  });
  it('returns undefined for missing or invalid labels', () => {
    expect(parseSeedLabel(undefined)).toBeUndefined();
    expect(parseSeedLabel('')).toBeUndefined();
    expect(parseSeedLabel('!!')).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run src/game/session.test.ts`
Expected: FAIL — cannot resolve `./session`.

- [ ] **Step 3: Write `src/game/session.ts`**

```ts
import { useGame } from './store';
import { resumeAudio } from './audio';

export function parseSeedLabel(label?: string): number | undefined {
  if (!label) return undefined;
  const n = parseInt(label, 36);
  if (!Number.isFinite(n) || n < 0 || label.trim() === '') return undefined;
  return n >>> 0;
}

export function startRun(seedLabel?: string): void {
  resumeAudio();
  useGame.getState().newRun(parseSeedLabel(seedLabel));
}
```

- [ ] **Step 4: Write `src/game/audio.ts`** (no unit test; Web Audio untestable in node env — manual check in Task 15)

```ts
import type { GameEvent } from './types';

let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let musicGain: GainNode | null = null;
let muted = false;
let beatClock = 0;

const SCALE = [0, 3, 5, 7, 10, 12, 15, 12, 10, 7, 5, 3]; // minor arpeggio up/down
const ROOT = 55; // A1

export function initAudio(): void {
  if (ctx) return;
  try {
    ctx = new AudioContext();
    master = ctx.createGain();
    master.gain.value = muted ? 0 : 0.8;
    master.connect(ctx.destination);
    musicGain = ctx.createGain();
    musicGain.gain.value = 0.22;
    musicGain.connect(master);
  } catch {
    ctx = null;
  }
}

export function resumeAudio(): void {
  try {
    initAudio();
    void ctx?.resume();
  } catch {
    // ignore
  }
}

export function setAudioMuted(m: boolean): void {
  muted = m;
  try {
    if (master && ctx) master.gain.setTargetAtTime(m ? 0 : 0.8, ctx.currentTime, 0.02);
  } catch {
    // ignore
  }
}

function blip(
  freq: number,
  dur: number,
  type: OscillatorType,
  gain: number,
  destination: AudioNode,
): void {
  if (!ctx) return;
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type;
  o.frequency.value = freq;
  g.gain.setValueAtTime(gain, ctx.currentTime);
  g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
  o.connect(g).connect(destination);
  o.start();
  o.stop(ctx.currentTime + dur + 0.02);
}

export function playEvent(e: GameEvent): void {
  if (!ctx || muted) return;
  try {
    switch (e) {
      case 'lane':
        blip(880, 0.06, 'square', 0.12, master!);
        break;
      case 'jump':
        if (ctx) blip(440, 0.18, 'triangle', 0.2, master!);
        break;
      case 'slide':
        blip(220, 0.22, 'sawtooth', 0.14, master!);
        break;
      case 'land':
        blip(110, 0.08, 'sine', 0.25, master!);
        break;
      case 'coin':
        blip(1318, 0.09, 'square', 0.16, master!);
        blip(1760, 0.14, 'square', 0.14, master!);
        break;
      case 'crash': {
        // noise burst: short buffer of white noise through lowpass
        const len = Math.floor(ctx.sampleRate * 0.4);
        const buf = ctx.createBuffer(1, len, ctx.sampleRate);
        const data = buf.getChannelData(0);
        for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / len);
        const src = ctx.createBufferSource();
        src.buffer = buf;
        const f = ctx.createBiquadFilter();
        f.type = 'lowpass';
        f.frequency.value = 900;
        const g = ctx.createGain();
        g.gain.value = 0.9;
        src.connect(f).connect(g).connect(master!);
        src.start();
        break;
      }
    }
  } catch {
    // never throw (SPEC §2.4)
  }
}

let stepIndex = 0;

export function updateMusic(dt: number, speedFactor: number): void {
  if (!ctx || muted) return;
  try {
    const bpm = 120 + 30 * Math.min(1, Math.max(0, speedFactor));
    const stepDur = 60 / bpm / 2; // eighth notes
    beatClock += dt;
    while (beatClock >= stepDur) {
      beatClock -= stepDur;
      const deg = SCALE[stepIndex % SCALE.length];
      const f = ROOT * Math.pow(2, deg / 12);
      blip(f, stepDur * 1.8, 'triangle', 1, musicGain!);
      if (stepIndex % 4 === 0) blip(60, 0.12, 'sine', 1.6, musicGain!); // kick
      stepIndex++;
    }
  } catch {
    // ignore
  }
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/game/session.test.ts && npm run typecheck && npm test`
Expected: session tests pass, suite green, typecheck clean.

- [ ] **Step 6: Restore full `src/main.tsx`** (undo the temporary version from Task 1 Step 10 — restore the Step 6 code with the `window.startHyperRun` global).

- [ ] **Step 7: Commit**

```bash
git add src/game/audio.ts src/game/session.ts src/game/session.test.ts src/main.tsx
git commit -m "feat: web-audio synth music/SFX and console seed entry"
```

---
### Task 11: Three.js core — GameLoop, CameraRig, Player, Scene, App wiring

**Files:**
- Create: `src/three/GameLoop.tsx`, `src/three/CameraRig.tsx`, `src/three/Player.tsx`, `src/three/Scene.tsx`
- Modify: `src/App.tsx` (replace placeholder)

**Interfaces:**
- Consumes: `world`, `step`, `PLAYER_Z` from runtime; `useGame` (drainIntents, syncHud, pause/resume); `playEvent`, `updateMusic`, `setAudioMuted`, `resumeAudio` from audio; constants.
- Produces: `<Scene/>` = `<Canvas>` with fog + postprocessing placeholder child (Effects added Task 13); `<GameLoop/>` must be the ONLY `useFrame` consumer of game-state mutation, calls `step(dt, intents)`, drains events → `playEvent`, `updateMusic(dt, (speed-SPEED_START)/(SPEED_MAX-SPEED_START))`, `attachInput` in `useEffect`, phase-`over` detection → `syncHud()`; `Player` = procedural neon ship group (cone body + torus ring, emissive cyan/magenta) reading `world.player` per frame via refs.

- [ ] **Step 1: Write `src/three/GameLoop.tsx`**

```tsx
import { useFrame } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import { playEvent, resumeAudio, setAudioMuted, updateMusic } from '../game/audio';
import { HUD_SYNC_INTERVAL, SPEED_MAX, SPEED_START } from '../game/constants';
import { attachInput } from '../game/input';
import { step, world } from '../game/runtime';
import { useGame } from '../game/store';

export function GameLoop() {
  const hudTimer = useRef(0);

  useEffect(() => {
    const detach = attachInput((i) => {
      const s = useGame.getState();
      if (i === 'pause') {
        if (s.phase === 'running') s.pause();
        else if (s.phase === 'paused') s.resume();
        return;
      }
      if (i === 'confirm') {
        resumeAudio();
        s.confirm();
        return;
      }
      if (s.phase === 'running') s.queueIntent(i);
    });
    return detach;
  }, []);

  useFrame((_, delta) => {
    const s = useGame.getState();
    if (s.muted !== undefined) setAudioMuted(s.muted);
    if (world.phase === 'running') {
      const intents = s.drainIntents();
      step(delta, intents);
      for (const e of world.events.splice(0)) playEvent(e);
      updateMusic(Math.min(delta, 0.05), (world.speed - SPEED_START) / (SPEED_MAX - SPEED_START));
    }
    hudTimer.current += delta;
    if (hudTimer.current >= HUD_SYNC_INTERVAL || world.phase !== s.phase) {
      hudTimer.current = 0;
      s.syncHud();
    }
  });

  return null;
}
```

- [ ] **Step 2: Write `src/three/CameraRig.tsx`**

```tsx
import { useFrame, useThree } from '@react-three/fiber';
import { FOV_BASE, FOV_FAST, LANE_X, SPEED_MAX, SPEED_START } from '../game/constants';
import { world } from '../game/runtime';

export function CameraRig() {
  const { camera } = useThree();

  useFrame((_, delta) => {
    const f = (world.speed - SPEED_START) / (SPEED_MAX - SPEED_START);
    const cam = camera as { fov?: number; updateProjectionMatrix?: () => void; position: { x: number; y: number; z: number }; lookAt: (x: number, y: number, z: number) => void };
    if (cam.fov !== undefined && cam.updateProjectionMatrix) {
      const target = FOV_BASE + (FOV_FAST - FOV_BASE) * Math.min(1, f);
      if (Math.abs(cam.fov - target) > 0.05) {
        cam.fov = target;
        cam.updateProjectionMatrix();
      }
    }
    const px = world.player.x;
    const k = Math.min(1, 6 * delta);
    cam.position.x += (px * 0.35 - cam.position.x) * k;
    cam.position.y += (3.2 + world.player.y * 0.4 - cam.position.y) * k;
    cam.position.z = 7.5;
    cam.lookAt(px * 0.5, 1 + world.player.y * 0.3, -10);
  });

  return null;
}
```

- [ ] **Step 3: Write `src/three/Player.tsx`**

```tsx
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import { COLOR } from '../game/constants';
import { world } from '../game/runtime';

export function Player() {
  const group = useRef<THREE.Group>(null);
  const body = useRef<THREE.Mesh>(null);

  useFrame(() => {
    const g = group.current;
    if (!g) return;
    const p = world.player;
    g.position.set(p.x, p.y + p.height / 2, 0);
    g.scale.set(1, p.height / 1.6, 1);
    g.rotation.z = (0 - p.x) * -0.08;
    if (body.current) {
      const m = body.current.material as THREE.MeshStandardMaterial;
      m.emissiveIntensity = world.phase === 'over' ? 0.2 : 1.6;
    }
  });

  return (
    <group ref={group}>
      <mesh ref={body}>
        <coneGeometry args={[0.45, 1.2, 4]} />
        <meshStandardMaterial
          color={COLOR.cyan}
          emissive={COLOR.cyan}
          emissiveIntensity={1.6}
          roughness={0.2}
        />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, -0.5, 0]}>
        <torusGeometry args={[0.6, 0.07, 8, 32]} />
        <meshStandardMaterial
          color={COLOR.magenta}
          emissive={COLOR.magenta}
          emissiveIntensity={2.2}
        />
      </mesh>
      <pointLight color={COLOR.cyan} intensity={6} distance={8} position={[0, 0.4, 0]} />
    </group>
  );
}
```

- [ ] **Step 4: Write `src/three/Scene.tsx`**

```tsx
import { Canvas } from '@react-three/fiber';
import { Suspense } from 'react';
import { COLOR, FOV_BASE } from '../game/constants';
import { CameraRig } from './CameraRig';
import { GameLoop } from './GameLoop';
import { Player } from './Player';

export function Scene() {
  return (
    <Canvas
      className="stage"
      camera={{ position: [0, 3.2, 7.5], fov: FOV_BASE, near: 0.1, far: 220 }}
      gl={{ antialias: true }}
      dpr={[1, 2]}
    >
      <color attach="background" args={[COLOR.bg]} />
      <fogExp2 attach="fog" args={[COLOR.fog, 0.022]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[6, 12, 4]} intensity={0.6} color={COLOR.violet} />
      <Suspense fallback={null}>
        <GameLoop />
        <CameraRig />
        <Player />
      </Suspense>
    </Canvas>
  );
}
```

- [ ] **Step 5: Replace `src/App.tsx`** (full wiring; UI overlays added in Task 14 — for now just the Scene inside the stage div)

```tsx
import { Scene } from './three/Scene';

export default function App() {
  return (
    <div className="stage">
      <Scene />
    </div>
  );
}
```

- [ ] **Step 6: Verify + manual smoke (dev server)**

```bash
npm run typecheck
npm test
npm run build
```

Then run `npm run dev`, open the printed URL: a neon ship + grid must render, arrow keys visibly strafe the ship (no obstacles yet). If port 5173 is taken by a previous dev server, kill it first: `lsof -ti:5173 | xargs kill 2>/dev/null`.

- [ ] **Step 7: Commit**

```bash
git add src/three src/App.tsx
git commit -m "feat: R3F scene, game loop, camera rig, procedural player ship"
```

---
### Task 12: World rendering — Track, Obstacles, Coins

**Files:**
- Create: `src/three/Track.tsx`, `src/three/Obstacles.tsx`, `src/three/Coins.tsx`
- Modify: `src/three/Scene.tsx` (add the three components)

**Interfaces:**
- Consumes: `world.rows` each frame; `obstacleBox`; constants.
- Produces: `<Track/>` = scrolling grid floor + horizon sun; `<Obstacles/>` = instanced boxes per kind reading `world.rows` via refs (pooled meshes, `visible`-culling); `<Coins/>` = pooled spinning octahedrons. All mutate `THREE.Object3D` transforms per frame, never setState.

- [ ] **Step 1: Write `src/three/Track.tsx`**

```tsx
import { Grid } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import { COLOR, LANE_W } from '../game/constants';
import { world } from '../game/runtime';

export function Track() {
  const grid = useRef<THREE.Group>(null);

  useFrame(() => {
    if (!grid.current) return;
    const period = 4;
    const off = world.distance % period;
    grid.current.position.z = off;
  });

  return (
    <group>
      <group ref={grid}>
        <Grid
          position={[0, 0, -40]}
          args={[200, 200]}
          cellSize={1}
          cellThickness={0.6}
          cellColor={COLOR.violet}
          sectionSize={4}
          sectionThickness={1.4}
          sectionColor={COLOR.cyan}
          fadeDistance={130}
          fadeStrength={1.5}
          infiniteGrid
        />
      </group>
      <mesh position={[0, 0, -1]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[LANE_W * 3 + 2, 240]} />
        <meshStandardMaterial color="#120726" roughness={0.9} />
      </mesh>
      <mesh position={[0, 18, -170]}>
        <circleGeometry args={[26, 48]} />
        <meshBasicMaterial color={COLOR.magenta} />
      </mesh>
      <mesh position={[0, 16, -168]}>
        <circleGeometry args={[22, 48]} />
        <meshBasicMaterial color={COLOR.bg} />
      </mesh>
    </group>
  );
}
```

- [ ] **Step 2: Write `src/three/Obstacles.tsx`**

```tsx
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import {
  BARRIER_H,
  COLOR,
  DEPTH,
  GATE_BOTTOM,
  GATE_TOP,
  LANE_X,
  LANE_W,
  WALL_TOP,
} from '../game/constants';
import { world } from '../game/runtime';

const POOL = 24;

function kindColor(kind: string): string {
  if (kind === 'barrier') return COLOR.magenta;
  if (kind === 'gate') return COLOR.cyan;
  return COLOR.violet;
}

export function Obstacles() {
  const meshes = useRef<(THREE.Mesh | null)[]>([]);

  useFrame(() => {
    let i = 0;
    for (const row of world.rows) {
      for (const o of row.obstacles) {
        const m = meshes.current[i];
        if (!m) continue;
        i++;
        const boxH =
          o.kind === 'barrier'
            ? BARRIER_H
            : o.kind === 'gate'
              ? GATE_TOP - GATE_BOTTOM
              : WALL_TOP;
        m.visible = true;
        m.position.set(
          LANE_X[o.lane],
          o.kind === 'gate' ? GATE_BOTTOM + boxH / 2 : boxH / 2,
          row.z,
        );
        m.scale.set(LANE_W * 0.8, boxH, DEPTH);
        const mat = m.material as THREE.MeshStandardMaterial;
        mat.emissiveIntensity = world.phase === 'over' ? 0.5 : 1.4;
      }
    }
    for (; i < POOL; i++) {
      const m = meshes.current[i];
      if (m) m.visible = false;
    }
  });

  return (
    <group>
      {Array.from({ length: POOL }, (_, i) => (
        <mesh key={i} ref={(el) => { meshes.current[i] = el; }} visible={false} castShadow={false}>
          <boxGeometry args={[1, 1, 1]} />
          <meshStandardMaterial
            color={COLOR.white}
            emissive={COLOR.cyan}
            emissiveIntensity={1.4}
            roughness={0.3}
          />
        </mesh>
      ))}
    </group>
  );
}
```

Note: emissive color per kind is set in Step 4 refinement if desired; single material color is acceptable (box scale + lane + height encode kind). `kindColor` may remain unused — delete it if `noUnusedLocals` flags it (it will), so do NOT include it; per-mesh colors come from a shared material. Keep the file minimal: no `kindColor`, no `castShadow` needed.

- [ ] **Step 3: Write `src/three/Coins.tsx`**

```tsx
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import { COLOR, LANE_X } from '../game/constants';
import { world } from '../game/runtime';

const POOL = 12;

export function Coins() {
  const meshes = useRef<(THREE.Mesh | null)[]>([]);

  useFrame((_, delta) => {
    let i = 0;
    for (const row of world.rows) {
      for (const c of row.coins) {
        if (c.taken) continue;
        const m = meshes.current[i];
        if (!m) continue;
        i++;
        m.visible = true;
        m.position.set(LANE_X[c.lane], c.y, c.z);
        m.rotation.y += delta * 3;
      }
    }
    for (; i < POOL; i++) {
      const m = meshes.current[i];
      if (m) m.visible = false;
    }
  });

  return (
    <group>
      {Array.from({ length: POOL }, (_, i) => (
        <mesh key={i} ref={(el) => { meshes.current[i] = el; }} visible={false}>
          <octahedronGeometry args={[0.35, 0]} />
          <meshStandardMaterial
            color={COLOR.yellow}
            emissive={COLOR.yellow}
            emissiveIntensity={2}
            roughness={0.2}
          />
        </mesh>
      ))}
    </group>
  );
}
```

- [ ] **Step 4: Modify `src/three/Scene.tsx`** — inside `<Suspense>` after `<GameLoop />` add `<Track />`, `<Obstacles />`, `<Coins />` (import them from `./Track`, `./Obstacles`, `./Coins`).

- [ ] **Step 5: Verify**

```bash
npm run typecheck
npm test
npm run build
```

Dev-server check: obstacles and coins stream past and the ship can dodge/jump/slide them; coins collect (score ticks in console via `window` store — optional `console.log(world.score)` temporarily).

- [ ] **Step 6: Commit**

```bash
git add src/three
git commit -m "feat: scrolling grid track, obstacle pool, coin pool rendering"
```

---
### Task 13: Particles + postprocessing Effects

**Files:**
- Create: `src/three/Particles.tsx`, `src/three/Effects.tsx`
- Modify: `src/three/Scene.tsx` (add both)

**Interfaces:**
- Consumes: `world.bursts` (`{x,y,z,t}`), `BURST_LIFE`, `BURST_POOL`.
- Produces: `<Particles/>` = pooled expanding spheres driven by burst age; `<Effects/>` = `EffectComposer` with `Bloom` + `Vignette` (from `@react-three/postprocessing`). If postprocessing throws on this GPU/context, fallback is `<Particles/>` only — guard with try/catch and log once.

- [ ] **Step 1: Write `src/three/Particles.tsx`**

```tsx
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import { BURST_LIFE } from '../game/constants';
import { world } from '../game/runtime';

export function Particles() {
  const meshes = useRef<(THREE.Mesh | null)[]>([]);

  useFrame(() => {
    const bursts = world.bursts;
    for (let i = 0; i < meshes.current.length; i++) {
      const m = meshes.current[i];
      if (!m) continue;
      const b = bursts[i];
      if (!b) {
        m.visible = false;
        continue;
      }
      const age = b.t / BURST_LIFE;
      m.visible = age < 1;
      m.position.set(b.x, b.y, b.z);
      const s = 0.2 + age * 2.4;
      m.scale.set(s, s, s);
      const mat = m.material as THREE.MeshBasicMaterial;
      mat.opacity = Math.max(0, 1 - age);
      mat.color.set(b.y > 1.4 ? '#ffd93d' : b.t >= 0 && bursts.length === 1 && world.phase === 'over' ? '#ff2bd6' : '#00f6ff');
    }
  });

  return (
    <group>
      {Array.from({ length: 6 }, (_, i) => (
        <mesh key={i} ref={(el) => { meshes.current[i] = el; }} visible={false}>
          <sphereGeometry args={[0.5, 12, 12]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      ))}
    </group>
  );
}
```

Simplify the burst color rule: coin bursts yellow, crash burst magenta. Final rule: `mat.color.set(world.phase === 'over' ? '#ff2bd6' : '#ffd93d')` when `i === 0 && bursts.length === 1` — else yellow. If it reads confusing, just always yellow except crash; the crash freezes phase.

- [ ] **Step 2: Write `src/three/Effects.tsx`**

```tsx
import { Bloom, EffectComposer, Vignette } from '@react-three/postprocessing';
import { COLOR } from '../game/constants';

export function Effects() {
  return (
    <EffectComposer multisampling={0}>
      <Bloom intensity={0.9} luminanceThreshold={0.2} luminanceSmoothing={0.6} mipmapBlur />
      <Vignette offset={0.3} darkness={0.85} />
    </EffectComposer>
  );
}
```

(`COLOR` unused — do not import it; `noUnusedLocals` will flag.) Final file: only the `Bloom`/`Vignette` import from constants is dropped.

- [ ] **Step 3: Modify `src/three/Scene.tsx`** — add `<Particles />` inside `<Suspense>` and `<Effects />` as last child of `<Canvas>` (outside Suspense is fine).

- [ ] **Step 4: Verify**

```bash
npm run typecheck
npm test
npm run build
```

Dev-server check: glow/bloom on neon objects, burst on coin pickup + crash.

- [ ] **Step 5: Commit**

```bash
git add src/three
git commit -m "feat: bloom/vignette postprocessing and burst particles"
```

---
### Task 14: UI screens + neon CSS + spec accuracy notes

**Files:**
- Create: `src/ui/TitleScreen.tsx`, `src/ui/Hud.tsx`, `src/ui/PauseOverlay.tsx`, `src/ui/GameOverScreen.tsx`, `src/ui/ErrorBoundary.tsx`
- Modify: `src/App.tsx`, `src/ui.css`, `SPEC.md`

**Interfaces:**
- Consumes: `useGame` (phase/score/coins/best/seedLabel/muted + confirm/pause/toggleMute).
- Produces: full DOM UI — title with neon wordmark, HUD (score/coins/speed), pause overlay, game-over with `seedLabel` small print (SPEC §3), mute button. App renders `<Scene/>` always + screens by phase, wrapped in `ErrorBoundary`.

- [ ] **Step 1: Write `src/ui/TitleScreen.tsx`**

```tsx
import { useGame } from '../game/store';

export function TitleScreen() {
  const confirm = useGame((s) => s.confirm);
  return (
    <div className="overlay">
      <h1 className="wordmark">
        HYPER<span>RUNNER</span>
      </h1>
      <p className="tagline">a neon endless run through the grid</p>
      <button className="cta" onClick={confirm}>
        PRESS START
      </button>
      <p className="keys">
        ◀ ▶ / A D lanes · ▲ / W / Space jump · ▼ / S slide · Esc pause · swipe on touch
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Write `src/ui/Hud.tsx`**

```tsx
import { useGame } from '../game/store';

export function Hud() {
  const score = useGame((s) => s.score);
  const coins = useGame((s) => s.coins);
  const speed = useGame((s) => s.speed);
  const muted = useGame((s) => s.muted);
  const toggleMute = useGame((s) => s.toggleMute);
  return (
    <div className="hud">
      <div className="hud-score">{score.toLocaleString('en-US')}</div>
      <div className="hud-right">
        <span className="hud-coins">{coins} ◈</span>
        <span className="hud-speed">{speed.toFixed(0)} u/s</span>
        <button className="hud-mute" onClick={toggleMute}>
          {muted ? '🔇' : '🔊'}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write `src/ui/PauseOverlay.tsx`**

```tsx
import { useGame } from '../game/store';

export function PauseOverlay() {
  const resume = useGame((s) => s.resume);
  return (
    <div className="overlay">
      <h2 className="panel-title">PAUSED</h2>
      <button className="cta" onClick={resume}>
        RESUME
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Write `src/ui/GameOverScreen.tsx`**

```tsx
import { useGame } from '../game/store';

export function GameOverScreen() {
  const { score, coins, best, seedLabel, confirm } = useGame();
  const isBest = score >= best && score > 0;
  return (
    <div className="overlay">
      <h2 className="panel-title crash-title">SIGNAL LOST</h2>
      <div className="stat-line">
        <span>SCORE {score.toLocaleString('en-US')}</span>
        <span>COINS {coins}</span>
        <span>BEST {best.toLocaleString('en-US')}</span>
      </div>
      {isBest && <p className="new-best">NEW BEST</p>}
      <button className="cta" onClick={confirm}>
        RUN AGAIN
      </button>
      {seedLabel && (
        <p className="seed">
          seed {seedLabel} · console: window.startHyperRun('{seedLabel}')
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Write `src/ui/ErrorBoundary.tsx`**

```tsx
import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="overlay">
          <h2 className="panel-title">SYSTEM FAILURE</h2>
          <button className="cta" onClick={() => window.location.reload()}>
            REBOOT
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 6: Replace `src/App.tsx` with full wiring**

```tsx
import { GameOverScreen } from './ui/GameOverScreen';
import { Hud } from './ui/Hud';
import { PauseOverlay } from './ui/PauseOverlay';
import { TitleScreen } from './ui/TitleScreen';
import { useGame } from './game/store';
import { Scene } from './three/Scene';

export default function App() {
  const phase = useGame((s) => s.phase);
  return (
    <div className="stage">
      <Scene />
      {phase === 'menu' && <TitleScreen />}
      {phase === 'running' && <Hud />}
      {phase === 'paused' && <PauseOverlay />}
      {phase === 'over' && <GameOverScreen />}
    </div>
  );
}
```

- [ ] **Step 7: Extend `src/ui.css`** — append the neon UI layer (keep base rules from Task 1):

```css
.overlay {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.2rem;
  background: radial-gradient(ellipse at 50% 120%, rgba(42, 11, 69, 0.55), rgba(7, 3, 17, 0.88));
  text-align: center;
  padding: 1rem;
}
.wordmark {
  font-size: clamp(3rem, 12vw, 7rem);
  font-weight: 900;
  letter-spacing: 0.06em;
  color: #00f6ff;
  text-shadow:
    0 0 8px #00f6ff,
    0 0 32px #00f6ff,
    0 0 80px #2a0b45;
  line-height: 1;
}
.wordmark span {
  display: block;
  color: #ff2bd6;
  text-shadow:
    0 0 8px #ff2bd6,
    0 0 32px #ff2bd6,
    0 0 80px #2a0b45;
}
.tagline {
  color: #8b5cf6;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  font-size: 0.8rem;
}
.cta {
  font: inherit;
  font-weight: 800;
  letter-spacing: 0.2em;
  color: #f4f0ff;
  background: transparent;
  border: 2px solid #00f6ff;
  box-shadow: 0 0 12px rgba(0, 246, 255, 0.6), inset 0 0 12px rgba(0, 246, 255, 0.2);
  padding: 0.9rem 2.4rem;
  cursor: pointer;
  animation: pulse 1.6s ease-in-out infinite;
}
.cta:hover {
  background: rgba(0, 246, 255, 0.12);
}
@keyframes pulse {
  50% {
    box-shadow: 0 0 24px rgba(0, 246, 255, 0.9), inset 0 0 18px rgba(0, 246, 255, 0.35);
  }
}
.keys {
  color: rgba(244, 240, 255, 0.6);
  font-size: 0.75rem;
  max-width: 34rem;
}
.panel-title {
  font-size: clamp(2rem, 8vw, 4rem);
  letter-spacing: 0.15em;
  color: #00f6ff;
  text-shadow: 0 0 12px #00f6ff;
}
.crash-title {
  color: #ff2bd6;
  text-shadow: 0 0 12px #ff2bd6;
}
.hud {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  padding: 1rem 1.4rem;
  pointer-events: none;
}
.hud-score {
  font-size: 2rem;
  font-weight: 900;
  color: #00f6ff;
  text-shadow: 0 0 10px rgba(0, 246, 255, 0.8);
  font-variant-numeric: tabular-nums;
}
.hud-right {
  display: flex;
  gap: 1rem;
  align-items: center;
  font-variant-numeric: tabular-nums;
}
.hud-coins {
  color: #ffd93d;
  text-shadow: 0 0 8px rgba(255, 217, 61, 0.7);
}
.hud-speed {
  color: #ff2bd6;
  text-shadow: 0 0 8px rgba(255, 43, 214, 0.7);
}
.hud-mute {
  pointer-events: auto;
  background: none;
  border: 1px solid rgba(244, 240, 255, 0.4);
  color: #f4f0ff;
  border-radius: 6px;
  padding: 0.2rem 0.5rem;
  cursor: pointer;
}
.stat-line {
  display: flex;
  gap: 2rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #f4f0ff;
  font-variant-numeric: tabular-nums;
}
.new-best {
  color: #ffd93d;
  letter-spacing: 0.3em;
  font-weight: 800;
  animation: pulse 0.8s ease-in-out infinite;
}
.seed {
  font-size: 0.7rem;
  color: rgba(244, 240, 255, 0.45);
  font-family: ui-monospace, monospace;
}
```

- [ ] **Step 8: SPEC.md accuracy notes** — two edits:
  1. In the rendering/stack section, wherever it lists drei `Text` (or "3D title"), replace the wording so it reads: the title is a DOM/CSS neon wordmark layered over the canvas (avoids troika's runtime font fetch; SPEC §1.6 no-network rule).
  2. Change the Vitest row from `^3` to `^5 (v3 is peer-incompatible with vite 8; verified 5.0.0)`.
  Note both in the commit message.

- [ ] **Step 9: Verify + full manual pass (dev server)**

```bash
npm run typecheck
npm test
npm run build
npm run dev
```

Check: title → Press Start → play, die, game-over with seed small print, Run Again, Esc pause/resume, mute toggle, console `window.startHyperRun('3F')` twice gives identical layouts.

- [ ] **Step 10: Commit**

```bash
git add src/ui src/App.tsx src/ui.css SPEC.md
git commit -m "feat: neon UI screens (title/hud/pause/gameover), spec accuracy notes"
```

---
### Task 15: Acceptance pass

**Files:**
- Verify only (fix anything that fails; commit fixes as `fix: ...`).

- [ ] **Step 1: Full gate**

```bash
npm run typecheck && npm test && npm run build && npm run preview
```

All green. Open the preview URL and play ≥60 s.

- [ ] **Step 2: SPEC §5 acceptance checklist, manually**
  - [ ] Fresh visitor: title explains controls in one line, starts in ≤2 inputs
  - [ ] 60 s run reaches high speed without stutter (DevTools perf, no React re-renders per frame — React DevTools Profiler shows HUD-only commits ~4 Hz)
  - [ ] Crash on every obstacle type: barrier (standing), gate (standing), wall (wrong lane); survived each by correct move
  - [ ] Coins collected with both low (run) and high (jump) approaches
  - [ ] Pause freezes and resumes exact world state; crash freezes it
  - [ ] Game over shows score/coins/best + seed; same seed replays same first 3 rows (visual)
  - [ ] localStorage persistence across reload; corrupt value doesn't crash
  - [ ] Touch: swipe all 4 directions + tap on device/touch emulation (DevTools device mode)
  - [ ] Mute silences instantly; resume-from-silent works after first gesture
  - [ ] `prefers-reduced-motion` (macOS setting): bloom still ok; if seizures flagged by reviewer, gate camera shake — none exists, so N/A

- [ ] **Step 3: Ensure clean tree**

```bash
git status --porcelain   # only opencode.json may be untracked; commit anything else
```

- [ ] **Step 4: Tag the demo (optional but recommended)**

```bash
git tag v0.1.0-demo
```

---

## Plan self-review notes (for implementer)

- Known intentional quirks: Task 5 Step 3 keeps the file import-light until Tasks 6–7 add their constants; Task 12 note about `kindColor`; Task 13 Effects import cleanup note — these are deliberate interim states; the FINAL file content is fully specified by the union of the task steps.
- If any test and the SPEC disagree, SPEC wins; change the test, never a SPEC constant, unless the commit message quotes the measured reason (e.g., jump peak).
- Dev server must be killed before starting a new one: `lsof -ti:5173 | xargs kill`.













