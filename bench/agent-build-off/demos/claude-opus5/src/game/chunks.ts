import type { ObstacleType } from './config'

/**
 * A chunk is authored in seconds of travel, not metres. The spawner converts a time
 * offset into a distance with the current speed, so a pattern reads the same at 14 m/s
 * and at 42 m/s.
 */
export type Row = {
  t: number
  /** One entry per lane, left to right. */
  cells: (ObstacleType | null)[]
}

export type CoinSpec = {
  t: number
  lane: number
  /** Sits on the jump arc rather than at running height. */
  air?: boolean
}

export type Chunk = {
  name: string
  /** Chunk enters the pool once difficulty reaches this value. */
  minDifficulty: number
  weight: number
  /** Seconds of travel the chunk occupies, including its trailing breathing room. */
  duration: number
  rows: Row[]
  coins: CoinSpec[]
}

/** Five coins in a line, 0.09 s apart. */
function arc(t: number, lane: number, air = false): CoinSpec[] {
  return [0, 1, 2, 3, 4].map((i) => ({ t: t + i * 0.09, lane, air }))
}

export const CHUNKS: Chunk[] = [
  {
    name: 'breather',
    minDifficulty: 0,
    weight: 2,
    duration: 1.8,
    rows: [],
    coins: [...arc(0.4, 1), ...arc(1.0, 0)],
  },
  {
    name: 'hop',
    minDifficulty: 0,
    weight: 3,
    duration: 2.4,
    rows: [{ t: 0.6, cells: [null, 'barrier', null] }],
    coins: arc(0.45, 1, true),
  },
  {
    name: 'duck',
    minDifficulty: 0,
    weight: 3,
    duration: 2.4,
    rows: [{ t: 0.6, cells: ['beam', 'beam', 'beam'] }],
    coins: arc(1.1, 1),
  },
  {
    name: 'sidestep-left',
    minDifficulty: 0,
    weight: 3,
    duration: 2.2,
    rows: [{ t: 0.6, cells: ['wall', null, null] }],
    coins: arc(0.55, 2),
  },
  {
    name: 'sidestep-right',
    minDifficulty: 0,
    weight: 3,
    duration: 2.2,
    rows: [{ t: 0.6, cells: [null, null, 'wall'] }],
    coins: arc(0.55, 0),
  },
  {
    name: 'full-hurdle',
    minDifficulty: 0.15,
    weight: 3,
    duration: 2.6,
    rows: [{ t: 0.7, cells: ['barrier', 'barrier', 'barrier'] }],
    coins: arc(0.55, 1, true),
  },
  {
    name: 'gate',
    minDifficulty: 0.25,
    weight: 3,
    duration: 3.2,
    rows: [
      { t: 0.6, cells: ['wall', null, 'wall'] },
      { t: 1.7, cells: [null, 'wall', 'wall'] },
    ],
    coins: [...arc(0.55, 1), ...arc(1.65, 0)],
  },
  {
    name: 'hop-duck',
    minDifficulty: 0.3,
    weight: 3,
    duration: 3.4,
    rows: [
      { t: 0.7, cells: ['barrier', 'barrier', 'barrier'] },
      { t: 1.9, cells: ['beam', 'beam', 'beam'] },
    ],
    coins: [...arc(0.55, 1, true), ...arc(2.4, 1)],
  },
  {
    name: 'patrol',
    minDifficulty: 0.4,
    weight: 2,
    duration: 3.2,
    rows: [
      { t: 0.7, cells: [null, 'drone', null] },
      { t: 1.9, cells: ['wall', null, null] },
    ],
    coins: arc(1.85, 2),
  },
  {
    name: 'slalom',
    minDifficulty: 0.55,
    weight: 3,
    duration: 3.8,
    rows: [
      { t: 0.6, cells: [null, 'wall', 'wall'] },
      { t: 1.5, cells: ['wall', 'wall', null] },
      { t: 2.4, cells: [null, 'wall', 'wall'] },
    ],
    coins: [...arc(0.55, 0), ...arc(1.45, 2), ...arc(2.35, 0)],
  },
  {
    name: 'gauntlet',
    minDifficulty: 0.65,
    weight: 3,
    duration: 4.0,
    rows: [
      { t: 0.6, cells: ['barrier', 'barrier', 'barrier'] },
      { t: 1.6, cells: ['wall', null, 'wall'] },
      { t: 2.6, cells: ['beam', 'beam', 'beam'] },
    ],
    coins: [...arc(0.45, 1, true), ...arc(1.55, 1)],
  },
  {
    name: 'swarm',
    minDifficulty: 0.8,
    weight: 2,
    duration: 4.0,
    rows: [
      { t: 0.6, cells: ['drone', null, 'drone'] },
      { t: 1.6, cells: [null, 'wall', null] },
      { t: 2.5, cells: ['barrier', 'barrier', 'barrier'] },
    ],
    coins: arc(2.4, 1, true),
  },
  {
    name: 'squeeze',
    minDifficulty: 0.85,
    weight: 2,
    duration: 4.2,
    rows: [
      { t: 0.6, cells: ['wall', 'beam', 'wall'] },
      { t: 1.5, cells: ['barrier', 'barrier', 'wall'] },
      { t: 2.5, cells: ['wall', null, 'wall'] },
      { t: 3.4, cells: ['beam', 'beam', 'beam'] },
    ],
    coins: [...arc(2.45, 1), ...arc(3.4, 1)],
  },
]

/** A lane the player cannot pass at all, whatever they do. */
const BLOCKING: ReadonlySet<ObstacleType | null> = new Set<ObstacleType | null>(['wall', 'drone'])

/**
 * Two guarantees, checked once at boot: every row leaves a passable lane, and rows are far
 * enough apart in time for a jump or a slide to finish before the next one arrives.
 */
export function validateChunks(chunks: readonly Chunk[]): string[] {
  const problems: string[] = []
  for (const chunk of chunks) {
    for (const row of chunk.rows) {
      if (row.cells.length !== 3) problems.push(`${chunk.name}: a row does not have 3 lanes`)
      if (row.cells.every((cell) => BLOCKING.has(cell))) {
        problems.push(`${chunk.name}: row at t=${row.t} has no passable lane`)
      }
    }
    const times = chunk.rows.map((row) => row.t).sort((a, b) => a - b)
    for (let i = 1; i < times.length; i++) {
      if (times[i] - times[i - 1] < 0.8) {
        problems.push(`${chunk.name}: rows at ${times[i - 1]} and ${times[i]} are less than 0.8 s apart`)
      }
    }
    const last = times.length ? times[times.length - 1] : 0
    if (chunk.duration < last + 0.6) {
      problems.push(`${chunk.name}: duration leaves less than 0.6 s of run-out`)
    }
  }
  return problems
}
