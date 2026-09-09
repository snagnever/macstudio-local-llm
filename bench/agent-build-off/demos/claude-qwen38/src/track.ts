// Procedural track generator. The corridor in front of the player is split
// into fixed-length segments; each segment holds three slots. When the
// oldest segment passes the player, it is regenerated far ahead. Rules keep
// every pattern passable: minimum gaps, a forced clear window after ramps,
// and a rhythm rule that repeats obstacle types in quick succession.

import { CFG } from "./config";
import type { Factory } from "./factory";

const SEG_SPAN = CFG.segmentLen * CFG.segments; // total corridor length

export class Track {
  private cursor = CFG.startZ; // z of the next segment to (re)generate
  private sinceObstacle = 99; // slots since the last obstacle
  private lastType: "low" | "high" = "low";
  private lastLane = 1;
  private d = 0; // difficulty 0..1, set by the game each frame

  constructor(private factory: Factory) {}

  setDifficulty(d: number): void {
    this.d = d;
  }

  reset(): void {
    this.factory.releaseAll();
    this.cursor = CFG.startZ;
    this.sinceObstacle = 99;
    this.lastLane = 1;
    // Fill the whole corridor up front, first two segments gentle.
    for (let i = 0; i < CFG.segments; i++) {
      this.generate(this.cursor, i < 2);
      this.cursor += CFG.segmentLen;
    }
  }

  /** Scroll the generation cursor with the world; recycle passed segments. */
  update(dt: number, speed: number): void {
    this.cursor -= speed * dt;
    while (this.cursor < CFG.recycleZ) {
      this.generate(this.cursor + SEG_SPAN, false);
      this.cursor += CFG.segmentLen;
    }
  }

  private lanePick(): number {
    return Math.floor(Math.random() * CFG.laneCount);
  }

  private lanePickChanged(): number {
    let l = this.lanePick();
    if (l === this.lastLane) l = (l + 1) % CFG.laneCount;
    return l;
  }

  /** Place a line of coins, optionally arced upward. */
  private coinLine(lane: number, z: number, count: number, arc: boolean): void {
    for (let i = 0; i < count; i++) {
      const c = this.factory.spawn("coin", lane, z + i * 2.4);
      if (!c) return;
      if (arc) {
        // Peak in the middle so a jump or ramp launch meets the line.
        const t = Math.sin(((i + 1) / (count + 1)) * Math.PI) * 1.1;
        this.factory.setBaseY(c, CFG.coinY + t);
      }
    }
  }

  private generate(z: number, gentle: boolean): void {
    const d = this.d;
    for (let s = 0; s < CFG.slotsPerSegment; s++) {
      const slotZ = z + CFG.slotOffset + s * CFG.slotLen;
      this.sinceObstacle++;

      if (!gentle && d >= 0.25 && this.sinceObstacle >= 2 && Math.random() < CFG.rampChance) {
        this.factory.spawn("ramp", this.lanePickChanged(), slotZ);
        this.sinceObstacle = -2; // force two clear slots after a launch
        continue;
      }

      const obstacleChance =
        CFG.obstacleChance + (CFG.obstacleChanceMax - CFG.obstacleChance) * d;
      const wantObstacle =
        !gentle && this.sinceObstacle >= 1 && Math.random() < obstacleChance;

      if (wantObstacle) {
        // Rhythm rule: back-to-back obstacles repeat the type, new lane.
        const type: "low" | "high" =
          this.sinceObstacle === 1 ? this.lastType : Math.random() < 0.5 ? "low" : "high";
        const lane = this.lanePickChanged();
        this.factory.spawn(type, lane, slotZ);
        this.lastType = type;
        this.lastLane = lane;

        // At high difficulty, sometimes block a second lane too.
        if (d > 0.55 && Math.random() < 0.35) {
          const second = (lane + 1 + Math.floor(Math.random() * 2)) % CFG.laneCount;
          this.factory.spawn(type, second, slotZ);
          this.lastLane = second;
        }

        // Half the time, reward jumping a low hurdle with a coin arc.
        if (type === "low" && Math.random() < 0.5) {
          this.coinLine(lane, slotZ - 2.4, 3, true);
        }
        this.sinceObstacle = 0;
        continue;
      }

      if (!gentle && d >= 0.25 && Math.random() < CFG.powerupChance) {
        const kind = (["shield", "magnet", "boost"] as const)[Math.floor(Math.random() * 3)];
        this.factory.spawn(kind, this.lanePick(), slotZ);
        continue;
      }

      if (Math.random() < 0.6) {
        this.coinLine(this.lanePick(), slotZ, 2 + Math.floor(Math.random() * 2), false);
      }
    }
  }
}
