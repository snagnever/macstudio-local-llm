import { collides } from './collision';
import {
  BURST_LIFE,
  BURST_POOL,
  COIN_SPACING,
  COIN_Y,
  COIN_Y_HIGH,
  COIN_Z_TOL,
  DEPTH,
  DESPAWN_Z,
  GRAVITY,
  JUMP_V,
  LANE_LERP,
  LANE_X,
  MAX_DT,
  PLAYER_D,
  PLAYER_H,
  PLAYER_SLIDE_H,
  ROW_GAP,
  SCORE_PER_COIN,
  SLIDE_TIME,
  SPAWN_Z,
  SPEED_MAX,
  SPEED_RAMP,
  SPEED_START,
} from './constants';
import { generateRow, isWinnable } from './patterns';
import { formatSeed, mulberry32, randomSeed } from './rng';
import type {
  Burst,
  CoinEntity,
  GameEvent,
  Intent,
  Phase,
  PlayerState,
  RowEntity,
} from './types';

export const PLAYER_Z = 0;

export interface World {
  seed: number;
  seedLabel: string;
  rand: () => number;
  phase: Phase;
  speed: number;
  distance: number;
  coins: number;
  score: number;
  elapsed: number;
  hudTimer: number;
  player: PlayerState;
  rows: RowEntity[];
  spawnAccum: number;
  bursts: Burst[];
  events: GameEvent[];
}

export const world: World = {
  seed: 0,
  seedLabel: '',
  rand: mulberry32(0),
  phase: 'menu',
  speed: SPEED_START,
  distance: 0,
  coins: 0,
  score: 0,
  elapsed: 0,
  hudTimer: 0,
  player: newPlayer(),
  rows: [],
  spawnAccum: 0,
  bursts: [],
  events: [],
};

function newPlayer(): PlayerState {
  return {
    lane: 1,
    x: LANE_X[1],
    y: 0,
    vy: 0,
    height: PLAYER_H,
    sliding: false,
    slideT: 0,
    onGround: true,
  };
}

export function resetWorld(seed = randomSeed()): void {
  world.seed = seed >>> 0;
  world.seedLabel = formatSeed(world.seed);
  world.rand = mulberry32(world.seed);
  world.speed = SPEED_START;
  world.distance = 0;
  world.coins = 0;
  world.score = 0;
  world.elapsed = 0;
  world.hudTimer = 0;
  world.player = newPlayer();
  world.rows = [];
  world.spawnAccum = 0;
  world.bursts = [];
  world.events = [];
}

function endSlide(): void {
  world.player.sliding = false;
  world.player.slideT = 0;
  world.player.height = PLAYER_H;
}

export function pushBurst(x: number, y: number, z: number): void {
  if (world.bursts.length >= BURST_POOL) world.bursts.shift();
  world.bursts.push({ x, y, z, t: 0 });
}

function crash(): void {
  world.phase = 'over';
  world.events.push('crash');
  const p = world.player;
  pushBurst(p.x, p.y + p.height / 2, PLAYER_Z);
}

function applyIntent(intent: Intent): void {
  const p = world.player;
  switch (intent) {
    case 'left':
      if (p.lane > 0) {
        p.lane -= 1;
        world.events.push('lane');
      }
      break;
    case 'right':
      if (p.lane < 2) {
        p.lane += 1;
        world.events.push('lane');
      }
      break;
    case 'jump':
      if (p.onGround) {
        if (p.sliding) endSlide();
        p.vy = JUMP_V;
        p.onGround = false;
        world.events.push('jump');
      }
      break;
    case 'slide':
      if (p.onGround && !p.sliding) {
        p.sliding = true;
        p.slideT = 0;
        p.height = PLAYER_SLIDE_H;
        world.events.push('slide');
      }
      break;
    case 'pause':
    case 'confirm':
      break;
  }
}

export function step(dtRaw: number, intents: Intent[]): void {
  if (world.phase !== 'running') return;
  const dt = Math.min(dtRaw, MAX_DT);
  world.elapsed += dt;
  world.speed = Math.min(SPEED_MAX, world.speed + SPEED_RAMP * dt);
  const travel = world.speed * dt;
  world.distance += travel;

  for (const intent of intents) applyIntent(intent);

  const p = world.player;
  p.x += (LANE_X[p.lane] - p.x) * Math.min(1, LANE_LERP * dt);
  if (!p.onGround) {
    p.vy -= GRAVITY * dt;
    p.y += p.vy * dt;
    if (p.y <= 0) {
      p.y = 0;
      p.vy = 0;
      p.onGround = true;
      world.events.push('land');
    }
  }
  if (p.sliding) {
    p.slideT += dt;
    if (p.slideT >= SLIDE_TIME) endSlide();
  }

  world.spawnAccum += travel;
  if (world.spawnAccum >= ROW_GAP) {
    world.spawnAccum -= ROW_GAP;
    let def = generateRow(world.rand);
    while (!isWinnable(def)) def = generateRow(world.rand);
    const coins: CoinEntity[] = [];
    if (def.coins) {
      const n = def.coins.count;
      for (let i = 0; i < n; i++) {
        coins.push({
          lane: def.coins.lane,
          z: SPAWN_Z - (n - 1 - i) * COIN_SPACING,
          y: def.coins.high ? COIN_Y_HIGH : COIN_Y,
          taken: false,
        });
      }
    }
    world.rows.push({ z: SPAWN_Z, obstacles: def.obstacles, coins });
  }
  for (const row of world.rows) row.z += travel;
  for (const row of world.rows) {
    for (const coin of row.coins) coin.z += travel;
  }
  world.rows = world.rows.filter((r) => r.z < DESPAWN_Z);

  for (const row of world.rows) {
    if (Math.abs(row.z) > PLAYER_D + DEPTH / 2) continue;
    for (const obstacle of row.obstacles) {
      if (collides(obstacle, world.player)) {
        crash();
        break;
      }
    }
    if (world.phase !== 'running') break;
  }
  if (world.phase !== 'running') return;

  for (const row of world.rows) {
    for (const coin of row.coins) {
      if (coin.taken) continue;
      if (Math.abs(coin.z - PLAYER_Z) > COIN_Z_TOL) continue;
      if (coin.lane !== world.player.lane) continue;
      const p = world.player;
      if (coin.y < p.y || coin.y > p.y + p.height) continue;
      coin.taken = true;
      world.coins += 1;
      world.score += SCORE_PER_COIN;
      world.events.push('coin');
      pushBurst(LANE_X[coin.lane], coin.y, coin.z);
    }
  }

  for (const burst of world.bursts) burst.t += dt;
  world.bursts = world.bursts.filter((b) => b.t < BURST_LIFE);
}
