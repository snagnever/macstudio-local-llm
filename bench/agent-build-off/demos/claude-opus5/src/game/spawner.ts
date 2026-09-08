import { CHUNKS, type Chunk } from './chunks'
import { DRONE_RATE, DRONE_SWEEP, LANES, OBSTACLE_SHAPE, RECYCLE_Z, RUNWAY_Z, SPAWN_Z, type ObstacleType } from './config'
import type { Rng } from './rng'
import { speedAt } from './scoring'

export type ActiveObstacle = {
  active: boolean
  type: ObstacleType
  lane: number
  x: number
  z: number
  /** Phase offset so drones do not sweep in lockstep. */
  phase: number
}

export type ActiveCoin = {
  active: boolean
  x: number
  y: number
  z: number
  taken: boolean
}

const OBSTACLE_POOL = 96
const COIN_POOL = 192

export const COIN_GROUND_Y = 0.95
export const COIN_AIR_Y = 1.95

export type Spawner = {
  obstacles: ActiveObstacle[]
  coins: ActiveCoin[]
  /** Far edge of the track built so far, in world z. */
  frontierZ: number
  lastChunk: string
}

export function createSpawner(): Spawner {
  return {
    obstacles: Array.from({ length: OBSTACLE_POOL }, () => ({
      active: false,
      type: 'barrier' as ObstacleType,
      lane: 1,
      x: 0,
      z: 0,
      phase: 0,
    })),
    coins: Array.from({ length: COIN_POOL }, () => ({ active: false, x: 0, y: 0, z: 0, taken: false })),
    frontierZ: RUNWAY_Z,
    lastChunk: '',
  }
}

export function resetSpawner(s: Spawner) {
  for (const o of s.obstacles) o.active = false
  for (const c of s.coins) c.active = false
  s.frontierZ = RUNWAY_Z
  s.lastChunk = ''
}

function takeObstacle(s: Spawner): ActiveObstacle | null {
  for (const o of s.obstacles) if (!o.active) return o
  return null
}

function takeCoin(s: Spawner): ActiveCoin | null {
  for (const c of s.coins) if (!c.active) return c
  return null
}

/** Weighted pick among the chunks unlocked at this difficulty, never the same one twice. */
function chooseChunk(rng: Rng, difficulty: number, lastChunk: string): Chunk {
  const pool = CHUNKS.filter((c) => c.minDifficulty <= difficulty && c.name !== lastChunk)
  const usable = pool.length > 0 ? pool : CHUNKS.filter((c) => c.minDifficulty <= difficulty)
  const total = usable.reduce((sum, c) => sum + c.weight, 0)
  let roll = rng() * total
  for (const chunk of usable) {
    roll -= chunk.weight
    if (roll <= 0) return chunk
  }
  return usable[usable.length - 1]
}

function spawnChunk(s: Spawner, rng: Rng, speed: number, difficulty: number) {
  const chunk = chooseChunk(rng, difficulty, s.lastChunk)
  const startZ = s.frontierZ
  for (const row of chunk.rows) {
    row.cells.forEach((type, lane) => {
      if (type === null) return
      const o = takeObstacle(s)
      if (o === null) return
      o.active = true
      o.type = type
      o.lane = lane
      o.x = LANES[lane]
      o.z = startZ - row.t * speed
      o.phase = rng() * Math.PI * 2
    })
  }
  for (const spec of chunk.coins) {
    const c = takeCoin(s)
    if (c === null) continue
    c.active = true
    c.taken = false
    c.x = LANES[spec.lane]
    c.y = spec.air ? COIN_AIR_Y : COIN_GROUND_Y
    c.z = startZ - spec.t * speed
  }
  s.frontierZ = startZ - chunk.duration * speed
  s.lastChunk = chunk.name
}

/** Moves the track toward the player, recycles what went past, and builds more ahead. */
export function updateSpawner(s: Spawner, rng: Rng, dt: number, speed: number, difficulty: number, elapsed: number) {
  const travel = speed * dt
  for (const o of s.obstacles) {
    if (!o.active) continue
    o.z += travel
    if (o.type === 'drone') {
      o.x = LANES[o.lane] + Math.sin(elapsed * DRONE_RATE + o.phase) * DRONE_SWEEP
    }
    if (o.z > RECYCLE_Z) o.active = false
  }
  for (const c of s.coins) {
    if (!c.active) continue
    c.z += travel
    if (c.z > RECYCLE_Z) c.active = false
  }
  s.frontierZ += travel
  // Author time gaps hold at the moment the player arrives, not the moment of spawning, so
  // convert with the speed the run will have reached by then.
  const arrivalSpeed = speedAt(elapsed + Math.abs(s.frontierZ) / Math.max(speed, 1))
  let guard = 0
  while (s.frontierZ > SPAWN_Z && guard++ < 12) {
    spawnChunk(s, rng, arrivalSpeed, difficulty)
  }
}

export function obstacleShape(type: ObstacleType) {
  return OBSTACLE_SHAPE[type]
}
