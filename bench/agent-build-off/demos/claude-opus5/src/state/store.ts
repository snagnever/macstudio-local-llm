import { create } from 'zustand'
import type { Phase } from '../game/world'
import { readBest, writeBest } from '../game/scoring'

type Store = {
  phase: Phase
  best: number
  /** Frozen at the moment of the crash, for the game over panel. */
  finalScore: number
  finalCoins: number
  muted: boolean
  lowQuality: boolean
  setPhase: (phase: Phase) => void
  finishRun: (score: number, coins: number) => void
  toggleMute: () => void
  setLowQuality: (low: boolean) => void
}

export const useStore = create<Store>((set, get) => ({
  phase: 'menu',
  best: readBest(),
  finalScore: 0,
  finalCoins: 0,
  muted: false,
  lowQuality: false,
  setPhase: (phase) => set({ phase }),
  finishRun: (score, coins) => {
    const best = Math.max(get().best, score)
    if (best > get().best) writeBest(best)
    set({ finalScore: score, finalCoins: coins, best })
  },
  toggleMute: () => set({ muted: !get().muted }),
  setLowQuality: (lowQuality) => set({ lowQuality }),
}))
