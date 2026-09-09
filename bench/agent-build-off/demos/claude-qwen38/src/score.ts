// Score accumulation, coin combo, and the persisted high score.

import { CFG } from "./config";

function loadBest(): number {
  try {
    return Number(localStorage.getItem(CFG.bestKey)) || 0;
  } catch {
    return 0;
  }
}

export class Score {
  score = 0;
  coins = 0;
  combo = 0;
  mult = 1;
  best = loadBest();
  private comboTimer = 0;

  reset(): void {
    this.score = 0;
    this.coins = 0;
    this.combo = 0;
    this.mult = 1;
    this.comboTimer = 0;
  }

  addCoin(): void {
    this.coins++;
    this.combo++;
    this.comboTimer = CFG.comboWindow;
    this.mult = 1 + Math.min(this.combo, CFG.comboCap) * CFG.comboMultPerCoin;
  }

  update(dt: number, speed: number, boostActive: boolean): void {
    if (this.comboTimer > 0) {
      this.comboTimer -= dt;
      if (this.comboTimer <= 0) {
        this.combo = 0;
        this.mult = 1;
      }
    }
    const boost = boostActive ? CFG.boostScoreMult : 1;
    this.score += speed * dt * boost * this.mult;
  }

  get display(): number {
    return Math.floor(this.score);
  }

  /** Persist the run. Returns true when this run beat the old record. */
  submit(): boolean {
    const run = Math.floor(this.score);
    if (run <= this.best) return false;
    this.best = run;
    try {
      localStorage.setItem(CFG.bestKey, String(run));
    } catch {
      // Private browsing mode: keep the record in memory only.
    }
    return true;
  }
}
