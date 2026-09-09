// Lane state machine and jump/slide kinematics. Pure TypeScript — no Babylon
// import. The visual mesh lives in game.ts, which mirrors these numbers.

import { CFG } from "./config";

export class Player {
  lane: number = CFG.startLane;
  x = (CFG.startLane - 1) * CFG.laneWidth;
  y = 0;
  vy = 0;
  /** Horizontal velocity in u/s, used for camera and ship banking. */
  vx = 0;
  grounded = true;
  sliding = false;

  private coyote = 0;
  private jumpBuffer = 0;
  private slideTimer = 0;

  reset(): void {
    this.lane = CFG.startLane;
    this.x = (CFG.startLane - 1) * CFG.laneWidth;
    this.y = 0;
    this.vy = 0;
    this.vx = 0;
    this.grounded = true;
    this.sliding = false;
    this.coyote = 0;
    this.jumpBuffer = 0;
    this.slideTimer = 0;
  }

  /** Returns true when the lane actually changed. */
  moveLane(dir: number): boolean {
    const next = this.lane + dir;
    if (next < 0 || next >= CFG.laneCount) return false;
    this.lane = next;
    return true;
  }

  jump(): void {
    if (this.grounded || this.coyote > 0) {
      this.doJump(CFG.jumpVy);
    } else {
      // Remember the press for a moment; it fires on landing.
      this.jumpBuffer = CFG.jumpBufferTime;
    }
  }

  /** External vertical impulse (ramp launch). */
  launch(vy: number): void {
    this.doJump(vy);
  }

  startSlide(): void {
    this.sliding = true;
    this.slideTimer = CFG.slideTime;
    if (!this.grounded) {
      // Air slide becomes a fast fall, so the player lands into the slide.
      this.vy = Math.min(this.vy, CFG.fastFallVy);
    }
  }

  update(dt: number): void {
    const prevX = this.x;
    const k = 1 - Math.exp(-CFG.laneSwitchK * dt);
    const targetX = (this.lane - 1) * CFG.laneWidth;
    this.x += (targetX - this.x) * k;
    this.vx = (this.x - prevX) / Math.max(dt, 1e-4);

    if (!this.grounded) {
      this.vy -= CFG.gravity * dt;
      this.y += this.vy * dt;
      if (this.y <= 0) {
        this.y = 0;
        this.vy = 0;
        this.grounded = true;
        if (this.jumpBuffer > 0) {
          this.jumpBuffer = 0;
          this.doJump(CFG.jumpVy);
        }
      }
    }

    this.coyote = this.grounded ? CFG.coyoteTime : this.coyote - dt;
    if (this.jumpBuffer > 0) this.jumpBuffer -= dt;
    if (this.sliding) {
      this.slideTimer -= dt;
      if (this.slideTimer <= 0) this.sliding = false;
    }
  }

  get height(): number {
    return this.sliding ? CFG.slideHeight : CFG.standHeight;
  }

  private doJump(vy: number): void {
    this.vy = vy;
    this.grounded = false;
    this.sliding = false;
    this.coyote = 0;
    this.jumpBuffer = 0;
  }
}
