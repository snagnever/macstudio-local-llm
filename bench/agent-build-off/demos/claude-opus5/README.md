# Hyper Runner

A browser 3D endless runner. A robot runs down a neon tunnel, dodges obstacles, and collects
coins. The run ends on the first crash.

```bash
npm install
npm run dev      # development server
npm run build    # static build to dist/
npm run preview  # serve the build
```

Arrow keys or WASD to move, space to jump, escape to pause. On a phone, swipe.

See [SPEC.md](SPEC.md) for what the game is, [PLAN.md](PLAN.md) for how it was built, and
[AGENTS.md](AGENTS.md) for the rules that apply when changing it.

`public/models/robot.glb` is the `RobotExpressive` model from the three.js examples. CC0, by
Tomás Laulhé, modified by Don McCurdy.
