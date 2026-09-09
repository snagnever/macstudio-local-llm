// Axis-aligned overlap tests between the player box and every active
// entity. Pickups release themselves; a hit only emits an event so the
// game can decide between shield absorb and crash.

import { CFG } from "./config";
import type { EventBus } from "./events";
import type { GameEventMap } from "./events";
import type { Factory } from "./factory";
import type { Player } from "./player";
import type { PowerupKind } from "./state";

export function checkCollisions(
  factory: Factory,
  player: Player,
  bus: EventBus<GameEventMap>,
): void {
  const actives = factory.actives;
  const px = player.x;
  const pYmin = player.y + 0.05;
  const pYmax = player.y + player.height * 0.92;
  const pCenter = player.y + player.height * 0.5;

  for (let i = actives.length - 1; i >= 0; i--) {
    const e = actives[i]!;
    const dx = Math.abs(e.x - px);
    const dz = Math.abs(e.z);

    switch (e.kind) {
      case "coin": {
        if (
          dx < e.halfW + CFG.playerHalfW &&
          dz < e.halfD + 0.4 &&
          Math.abs(e.y - pCenter) < CFG.pickupDy
        ) {
          bus.emit("coin", undefined);
          factory.releaseAt(i);
        }
        break;
      }
      case "shield":
      case "magnet":
      case "boost": {
        if (
          dx < e.halfW + CFG.playerHalfW &&
          dz < e.halfD + 0.4 &&
          Math.abs(e.y - pCenter) < CFG.pickupDy + 0.3
        ) {
          bus.emit("powerup", e.kind as PowerupKind);
          factory.releaseAt(i);
        }
        break;
      }
      case "ramp": {
        // Launch only when driven onto the ramp from the ground.
        if (
          player.grounded &&
          dx < e.halfW + CFG.playerHalfW &&
          dz < e.halfD + CFG.playerHalfD
        ) {
          bus.emit("launch", undefined);
          factory.releaseAt(i);
        }
        break;
      }
      default: {
        // Obstacle: lane box overlap plus a Y-slab overlap.
        if (
          dx < e.halfW + CFG.playerHalfW * 0.8 &&
          dz < e.halfD + CFG.playerHalfD &&
          pYmax > e.yBase &&
          pYmin < e.yTop
        ) {
          bus.emit("hit", e);
        }
        break;
      }
    }
  }
}
