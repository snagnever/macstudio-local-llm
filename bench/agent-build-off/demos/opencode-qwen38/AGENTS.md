# AGENTS.md — Hyper Runner

## Repo objective
A polished 3D endless-runner browser demo (neon synthwave theme) built to
demonstrate rapid game development with the pmndrs ecosystem: React 19 +
Vite + TypeScript + @react-three/fiber + Rapier physics, using procedural
primitives (no downloaded assets) and off-the-shelf libraries wherever possible.

## Read first
- SPEC.md — game design: mechanics, controls, visual direction, scope.
  The source of truth for WHAT to build.
- PLAN.md — technical approach: stack versions, architecture, file map,
  implementation steps, risks. The source of truth for HOW to build.

## Commands
- npm install          install dependencies
- npm run dev          dev server with HMR
- npm run build        typecheck (tsc -b) + production build
- npm run preview      serve the production build

## Conventions
- Keep per-frame logic in useFrame mutating refs; never setState per frame
  (zustand is for low-frequency game state: status, score, speed, lane).
- Obstacles/coins are fixed recycling pools of rapier bodies — do not mount
  entities at runtime.
- Game logic is driven by rapier collision/intersection events, not AABB math.
- All tuning constants (speed ramp, jump force, pool sizes, colors) live at
  the top of their module for easy playtesting tweaks.
