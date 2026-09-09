// Entry point: create the engine, attach the game, handle window events.

import { Engine } from "@babylonjs/core";
import { Game } from "./game";
import "../hud.css";

const canvas = document.getElementById("c") as HTMLCanvasElement | null;
if (!canvas) throw new Error("canvas #c missing from index.html");

const engine = new Engine(canvas, true, {
  antialias: false,
  stencil: false,
  alpha: false,
});

// Cap the render resolution on HiDPI screens; the neon look does not need 2x.
engine.setHardwareScalingLevel(Math.max(1, window.devicePixelRatio / 1.5));

const game = new Game(engine);

window.addEventListener("resize", () => engine.resize());

canvas.addEventListener("webglcontextlost", (ev) => {
  ev.preventDefault();
  const ui = document.getElementById("ui");
  if (ui) ui.dataset.state = "lost";
});

// Keep a reference so devtools can poke at it.
declare global {
  interface Window {
    hyperRunner?: Game;
  }
}
window.hyperRunner = game;
