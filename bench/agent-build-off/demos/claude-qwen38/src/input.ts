// Keyboard and touch input. Each action fires once, delivered straight to
// the game. The browser must see Space and the arrow keys as game keys, so
// preventDefault stops page scrolling.

export type InputAction =
  | "left"
  | "right"
  | "jump"
  | "slide"
  | "confirm"
  | "mute"
  | "tap";

function keyToAction(code: string): InputAction | null {
  switch (code) {
    case "ArrowLeft":
    case "KeyA":
      return "left";
    case "ArrowRight":
    case "KeyD":
      return "right";
    case "ArrowUp":
    case "KeyW":
    case "Space":
      return "jump";
    case "ArrowDown":
    case "KeyS":
      return "slide";
    case "Enter":
      return "confirm";
    case "KeyM":
      return "mute";
    default:
      return null;
  }
}

export class InputManager {
  private startX = 0;
  private startY = 0;
  private touching = false;

  constructor(private onAction: (action: InputAction) => void) {
    window.addEventListener("keydown", (e) => {
      if (e.repeat) return;
      const action = keyToAction(e.code);
      if (!action) return;
      if (e.code === "Space" || e.code.startsWith("Arrow")) e.preventDefault();
      this.onAction(action);
    });

    const el = document.documentElement;
    el.addEventListener(
      "touchstart",
      (e) => {
        const t = e.touches[0];
        this.startX = t.clientX;
        this.startY = t.clientY;
        this.touching = true;
      },
      { passive: true },
    );
    el.addEventListener(
      "touchend",
      (e) => {
        if (!this.touching) return;
        this.touching = false;
        const t = e.changedTouches[0];
        const dx = t.clientX - this.startX;
        const dy = t.clientY - this.startY;
        const ax = Math.abs(dx);
        const ay = Math.abs(dy);
        if (Math.max(ax, ay) < 30) {
          this.onAction("tap");
          return;
        }
        if (ax > ay) this.onAction(dx > 0 ? "right" : "left");
        else this.onAction(dy > 0 ? "slide" : "jump");
      },
      { passive: true },
    );
  }
}
