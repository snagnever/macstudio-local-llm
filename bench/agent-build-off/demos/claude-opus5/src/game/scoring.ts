import { BEST_KEY, COIN_VALUE, DIFFICULTY_RAMP, SPEED_GAIN, SPEED_MAX, SPEED_START } from './config'

export function speedAt(elapsed: number): number {
  return Math.min(SPEED_MAX, SPEED_START + SPEED_GAIN * elapsed)
}

/** Runs from 0 to 1 and drives which chunks are in the pool. */
export function difficultyAt(elapsed: number): number {
  return Math.min(1, elapsed / DIFFICULTY_RAMP)
}

export function scoreOf(distance: number, coins: number): number {
  return Math.floor(distance) + coins * COIN_VALUE
}

export function readBest(): number {
  try {
    const raw = localStorage.getItem(BEST_KEY)
    const value = raw === null ? 0 : Number.parseInt(raw, 10)
    return Number.isFinite(value) && value > 0 ? value : 0
  } catch {
    return 0
  }
}

export function writeBest(score: number) {
  try {
    localStorage.setItem(BEST_KEY, String(Math.floor(score)))
  } catch {
    // Private browsing blocks storage. The run still counts on screen.
  }
}
