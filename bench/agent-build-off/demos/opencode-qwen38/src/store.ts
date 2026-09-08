import { create } from 'zustand'

export type Status = 'ready' | 'running' | 'dead'

export const BASE_SPEED = 12
export const MAX_SPEED = 30
export const ACCEL = (MAX_SPEED - BASE_SPEED) / 90
export const LANE_WIDTH = 2

export const OBSTACLE_COUNT = 16
export const OBSTACLE_START_Z = 45
export const OBSTACLE_PITCH = 13
export const COIN_COUNT = 24
export const COIN_START_Z = 62
export const COIN_PITCH = 9

export const runtime = {
  time: 0,
  distance: 0,
  speed: BASE_SPEED,
  lane: 0,
  playerX: 0,
  playerY: 0,
  jumpQueuedAt: -10,
  slideQueuedAt: -10,
  groundedAt: -10,
  slideEnd: -10,
  slideCoolEnd: -10,
  nextObstacleZ: 0,
  nextCoinZ: 0,
}

const BEST_KEY = 'hyper-runner-best'

type Store = {
  status: Status
  score: number
  coins: number
  best: number
  speed: number
  sliding: boolean
  muted: boolean
  start: () => void
  crash: () => void
  coin: () => void
  setHud: (score: number, speed: number) => void
  setSliding: (sliding: boolean) => void
  toggleMute: () => void
}

const loadBest = () => Number(localStorage.getItem(BEST_KEY) ?? 0) || 0

export const useStore = create<Store>((set, get) => ({
  status: 'ready',
  score: 0,
  coins: 0,
  best: loadBest(),
  speed: BASE_SPEED,
  sliding: false,
  muted: false,
  start: () => {
    runtime.time = 0
    runtime.distance = 0
    runtime.speed = BASE_SPEED
    runtime.lane = 0
    runtime.playerX = 0
    runtime.playerY = 0
    runtime.jumpQueuedAt = -10
    runtime.slideQueuedAt = -10
    runtime.groundedAt = -10
    runtime.slideEnd = -10
    runtime.slideCoolEnd = -10
    runtime.nextObstacleZ = OBSTACLE_START_Z + OBSTACLE_COUNT * OBSTACLE_PITCH
    runtime.nextCoinZ = COIN_START_Z + COIN_COUNT * COIN_PITCH
    set({ status: 'running', score: 0, coins: 0, sliding: false })
  },
  crash: () => {
    const { best } = get()
    const live = Math.floor(runtime.distance) + get().coins * 10
    const newBest = Math.max(live, best)
    localStorage.setItem(BEST_KEY, String(newBest))
    set({ status: 'dead', score: live, best: newBest })
  },
  coin: () => set((s) => ({ coins: s.coins + 1 })),
  setHud: (score, speed) => set({ score, speed }),
  setSliding: (sliding) => set({ sliding }),
  toggleMute: () => set((s) => ({ muted: !s.muted })),
}))
