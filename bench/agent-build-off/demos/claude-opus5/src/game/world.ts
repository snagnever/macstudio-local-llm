import { overlaps, nearXZ, type Box } from './collision'
import { PLAYER_DEPTH, PLAYER_WIDTH } from './config'
import { applyIntent, createPlayer, playerHeight, updatePlayer, type Intent, type Player } from './player'
import { mulberry32, type Rng } from './rng'
import { difficultyAt, scoreOf, speedAt } from './scoring'
import { createSpawner, obstacleShape, resetSpawner, updateSpawner, type Spawner } from './spawner'

export type Phase = 'menu' | 'playing' | 'paused' | 'dead'

/** How fast the tunnel drifts behind the menu, in metres per second. */
const MENU_DRIFT_SPEED = 7

export type Crash = { x: number; y: number; z: number }

export type World = {
  phase: Phase
  elapsed: number
  distance: number
  coins: number
  score: number
  speed: number
  difficulty: number
  /** Seconds since the crash, used by the death camera. */
  deadT: number
  shake: number
  crash: Crash | null
  player: Player
  spawner: Spawner
  rng: Rng
  intents: Intent[]
  /** Set by the application so a phase change can reach React. */
  onPhase: ((phase: Phase) => void) | null
  /** Set by the application so the scene can play a sound. */
  onEvent: ((event: 'jump' | 'slide' | 'coin' | 'crash') => void) | null
}

export const world: World = {
  phase: 'menu',
  elapsed: 0,
  distance: 0,
  coins: 0,
  score: 0,
  speed: 0,
  difficulty: 0,
  deadT: 0,
  shake: 0,
  crash: null,
  player: createPlayer(),
  spawner: createSpawner(),
  rng: mulberry32(1),
  intents: [],
  onPhase: null,
  onEvent: null,
}

function setPhase(next: Phase) {
  if (world.phase === next) return
  world.phase = next
  world.onPhase?.(next)
}

export function startRun(seed = Math.floor(Math.random() * 0xffffffff)) {
  world.elapsed = 0
  world.distance = 0
  world.coins = 0
  world.score = 0
  world.speed = speedAt(0)
  world.difficulty = 0
  world.deadT = 0
  world.shake = 0
  world.crash = null
  world.player = createPlayer()
  world.rng = mulberry32(seed)
  world.intents.length = 0
  resetSpawner(world.spawner)
  setPhase('playing')
}

export function toMenu() {
  world.intents.length = 0
  setPhase('menu')
}

export function pauseRun() {
  if (world.phase === 'playing') setPhase('paused')
}

export function resumeRun() {
  if (world.phase === 'paused') setPhase('playing')
}

export function pushIntent(intent: Intent) {
  if (world.phase !== 'playing') return
  world.intents.push(intent)
}

const playerBox: Box = { x: 0, y: 0, z: 0, hx: PLAYER_WIDTH / 2, hy: 0, hz: PLAYER_DEPTH / 2 }
const obstacleBox: Box = { x: 0, y: 0, z: 0, hx: 0, hy: 0, hz: 0 }

export function stepWorld(dt: number) {
  world.shake = Math.max(0, world.shake - dt * 2.4)

  if (world.phase === 'dead') {
    world.deadT += dt
    return
  }
  if (world.phase === 'menu') {
    // Drift the tunnel behind the title screen. startRun resets this before it can score.
    world.distance += MENU_DRIFT_SPEED * dt
    return
  }
  if (world.phase !== 'playing') return

  world.elapsed += dt
  world.speed = speedAt(world.elapsed)
  world.difficulty = difficultyAt(world.elapsed)
  world.distance += world.speed * dt

  const p = world.player
  for (const intent of world.intents) {
    applyIntent(p, intent)
    if (intent === 'jump') world.onEvent?.('jump')
    if (intent === 'slide') world.onEvent?.('slide')
  }
  world.intents.length = 0

  updatePlayer(p, dt)
  updateSpawner(world.spawner, world.rng, dt, world.speed, world.difficulty, world.elapsed)

  const height = playerHeight(p)
  playerBox.x = p.x
  playerBox.y = p.y + height / 2
  playerBox.hy = height / 2

  for (const o of world.spawner.obstacles) {
    if (!o.active || o.z < -6 || o.z > 4) continue
    const shape = obstacleShape(o.type)
    obstacleBox.x = o.x
    obstacleBox.y = shape.cy
    obstacleBox.z = o.z
    obstacleBox.hx = shape.chx
    obstacleBox.hy = shape.hy
    obstacleBox.hz = shape.hz
    if (overlaps(playerBox, obstacleBox)) {
      world.crash = { x: o.x, y: shape.cy, z: o.z }
      world.shake = 1
      world.deadT = 0
      world.score = scoreOf(world.distance, world.coins)
      world.onEvent?.('crash')
      setPhase('dead')
      return
    }
  }

  const chestY = p.y + 0.9
  for (const c of world.spawner.coins) {
    if (!c.active || c.taken || c.z < -4 || c.z > 3) continue
    if (nearXZ(p.x, 0, c.x, c.z, 0.95) && Math.abs(chestY - c.y) < 1) {
      c.taken = true
      c.active = false
      world.coins += 1
      world.onEvent?.('coin')
    }
  }

  world.score = scoreOf(world.distance, world.coins)
}
