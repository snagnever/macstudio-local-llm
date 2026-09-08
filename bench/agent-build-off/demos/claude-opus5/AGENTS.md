# AGENTS.md

## What this repository is

Hyper Runner is a browser 3D endless runner demo. A robot runs down a neon tunnel, dodges
obstacles, and collects coins. The run ends on the first crash. The demo is a static site with no
backend and no runtime network call.

## Read these first

- [SPEC.md](SPEC.md) — what the game is: stack, art direction, gameplay rules, acceptance criteria.
- [PLAN.md](PLAN.md) — how it gets built: file layout, build steps, and the development hook for
  driving the simulation from the browser console.
- [README.md](README.md) — the short version, for a person who just wants to run it.
- [STATS.md](STATS.md) — how this repository was built: time, tokens, lines, and the defects
  found during verification.

Treat `SPEC.md` as the source of truth. If code and spec disagree, fix one of them and say which.

## Commands

```bash
npm install        # install dependencies
npm run dev        # development server
npm run build      # static build to dist/
npm run preview    # serve the build
npm run typecheck  # tsc --noEmit
```

## Rules for changing this repository

1. Keep `src/game/` pure. Those files import neither `three` nor React. Rendering reads their state.
2. Put every tunable in `src/game/config.ts`. Do not scatter magic numbers through the scene code.
3. Allocate nothing per frame. Instance and pool anything that repeats.
4. The physics engine runs only for crash debris. Gameplay collision stays in `src/game/collision.ts`.
5. There is no test suite by design. Verify by running the game and checking `SPEC.md` section 11.
   For rule changes, drive the simulation through `window.hyper` in a development build instead of
   playing by hand. `PLAN.md` shows how.
6. Keep the collision box narrower than the mesh. `SPEC.md` section 5.7 explains why.

## Credits

`public/models/robot.glb` is the `RobotExpressive` model from the three.js examples. CC0, by
Tomás Laulhé, modified by Don McCurdy.
