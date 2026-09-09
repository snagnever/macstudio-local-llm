// DOM HUD overlay. A 125 ms interval polls game state for text; state
// switches (menu / playing / gameover) are pushed by the game.

import { CFG } from "./config";
import type { Powerups } from "./powerups";
import type { Score } from "./score";
import type { GameStateName } from "./state";

export class Hud {
  private ui: HTMLElement;
  private scoreEl: HTMLElement;
  private comboEl: HTMLElement;
  private bestEl: HTMLElement;
  private coinEls: HTMLElement[];
  private bars: Record<string, HTMLElement>;
  private finalScore: HTMLElement;
  private finalBest: HTMLElement;
  private recordEl: HTMLElement;
  private muteBtn: HTMLButtonElement;

  score: Score | null = null;
  powerups: Powerups | null = null;

  constructor(onConfirm: () => void, onMute: () => void) {
    const el = (id: string): HTMLElement => {
      const found = document.getElementById(id);
      if (!found) throw new Error(`HUD element #${id} missing`);
      return found;
    };
    this.ui = el("ui");
    this.scoreEl = el("score");
    this.comboEl = el("combo");
    this.bestEl = el("best");
    this.coinEls = Array.from(document.querySelectorAll<HTMLElement>(".coin-count"));
    this.bars = {
      shield: el("bar-shield"),
      magnet: el("bar-magnet"),
      boost: el("bar-boost"),
    };
    this.finalScore = el("final-score");
    this.finalBest = el("final-best");
    this.recordEl = el("new-record");
    this.muteBtn = el("btn-mute") as HTMLButtonElement;

    for (const id of ["btn-start", "btn-restart"]) {
      const btn = document.getElementById(id) as HTMLButtonElement | null;
      btn?.addEventListener("click", () => {
        btn.blur(); // so Enter/Space does not re-trigger the focused button
        onConfirm();
      });
    }
    this.muteBtn.addEventListener("click", () => {
      this.muteBtn.blur();
      onMute();
    });

    setInterval(() => this.poll(), 125);
  }

  setState(state: GameStateName): void {
    this.ui.dataset.state = state;
  }

  setMuted(muted: boolean): void {
    this.muteBtn.textContent = muted ? "AUDIO: OFF" : "AUDIO: ON";
  }

  private poll(): void {
    if (!this.score) return;
    this.scoreEl.textContent = String(this.score.display).padStart(6, "0");
    this.bestEl.textContent = String(Math.max(this.score.best, this.score.display)).padStart(6, "0");
    this.comboEl.textContent = this.score.combo >= 2 ? `x${this.score.mult.toFixed(2)}` : "";
    for (const el of this.coinEls) el.textContent = String(this.score.coins);
    if (this.powerups) {
      for (const kind of ["shield", "magnet", "boost"] as const) {
        const pct = (this.powerups.remaining(kind) / CFG.powerupDuration) * 100;
        this.bars[kind]!.style.width = `${pct.toFixed(0)}%`;
      }
    }
  }

  showGameOver(score: number, best: number, newRecord: boolean): void {
    this.finalScore.textContent = String(score);
    this.finalBest.textContent = String(best);
    this.recordEl.style.display = newRecord ? "block" : "none";
  }
}
