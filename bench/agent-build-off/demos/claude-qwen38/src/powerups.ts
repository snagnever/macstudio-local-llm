// Timed power-up state. Plain timers, no events; the game polls each frame.

import { CFG } from "./config";
import { POWERUP_KINDS, type PowerupKind } from "./state";

export class Powerups {
  private timers: Record<PowerupKind, number> = { shield: 0, magnet: 0, boost: 0 };

  reset(): void {
    for (const k of POWERUP_KINDS) this.timers[k] = 0;
  }

  collect(kind: PowerupKind): void {
    this.timers[kind] = CFG.powerupDuration;
  }

  update(dt: number): void {
    for (const k of POWERUP_KINDS) {
      if (this.timers[k] > 0) this.timers[k] -= dt;
    }
  }

  active(kind: PowerupKind): boolean {
    return this.timers[kind] > 0;
  }

  /** Seconds left, for HUD bars. */
  remaining(kind: PowerupKind): number {
    return Math.max(0, this.timers[kind]);
  }

  /** Spend the shield to absorb one hit. */
  consumeShield(): boolean {
    if (this.timers.shield <= 0) return false;
    this.timers.shield = 0;
    return true;
  }
}
