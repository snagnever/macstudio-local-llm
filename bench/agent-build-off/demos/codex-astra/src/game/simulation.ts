import { BoundingBox } from '@babylonjs/core/Culling/boundingBox';
import { Vector3 } from '@babylonjs/core/Maths/math.vector';
import {
  DESPAWN_BEHIND,
  GRAVITY,
  IMMUNITY_DURATION,
  INITIAL_SPEED,
  JUMP_VELOCITY,
  LANE_CENTERS,
  LANE_MOVE_SPEED,
  MAX_SPEED,
  PATTERN_BUFFER_SIZE,
  SAFE_OPENING_DISTANCE,
  SHIELD_DURATION,
  SLIDE_DURATION,
  SPAWN_AHEAD,
  SPEED_RAMP_SECONDS,
} from './config';
import { createPatternSequence } from './patterns';
import type { Command, GameEvent, Lane, ObjectKind, RunState, TrackObject } from './types';

const RUNNER_HALF_WIDTH = 0.35;
const RUNNER_HALF_DEPTH = 0.3;
const OBJECT_HALF_WIDTH = 0.92;
const OBJECT_HALF_DEPTH = 0.38;

export function createRun(seed: number): RunState {
  return {
    phase: 'ready', seed, elapsed: 0, distance: 0, speed: INITIAL_SPEED, score: 0, cells: 0,
    runner: { lane: 0, x: 0, y: 0, vy: 0, slideRemaining: 0, shieldRemaining: 0, immunityRemaining: 0 },
    objects: [], nextObjectId: 1, nextRowIndex: 0,
    nextRowZ: SAFE_OPENING_DISTANCE,
    patterns: createPatternSequence(seed, PATTERN_BUFFER_SIZE), pendingEvents: [],
  };
}

export function applyCommand(state: RunState, command: Command): void {
  if (state.phase !== 'running') return;
  if (command === 'left') state.runner.lane = Math.max(-1, state.runner.lane - 1) as Lane;
  if (command === 'right') state.runner.lane = Math.min(1, state.runner.lane + 1) as Lane;
  if (command === 'jump' && state.runner.y === 0 && state.runner.vy === 0 && state.runner.slideRemaining === 0) {
    state.runner.vy = JUMP_VELOCITY;
    state.pendingEvents.push({ kind: 'jump' });
  }
  if (command === 'slide' && state.runner.y === 0 && state.runner.vy === 0 && state.runner.slideRemaining === 0) {
    state.runner.slideRemaining = SLIDE_DURATION;
    state.pendingEvents.push({ kind: 'slide' });
  }
}

function approach(value: number, target: number, amount: number): number {
  if (value < target) return Math.min(value + amount, target);
  return Math.max(value - amount, target);
}

function spawnRows(state: RunState): void {
  const spawnObject = (kind: ObjectKind, lane: Lane, z: number): void => {
    state.objects.push({
      id: state.nextObjectId,
      kind,
      lane,
      z,
      previousZ: z,
      active: true,
    });
    state.nextObjectId += 1;
  };

  if (state.nextRowIndex === 0 && state.objects.length === 0) {
    for (const z of [8, 12, 16, 20, 24, 28]) spawnObject('cell', 0, z);
  }

  while (state.nextRowZ <= SPAWN_AHEAD) {
    const row = state.patterns[state.nextRowIndex % state.patterns.length];
    const safeLaneIndex = row.kinds.findIndex((kind) => kind === null || kind === 'cell' || kind === 'shield');
    const safeLane = (safeLaneIndex - 1) as Lane;
    for (const distance of [15, 12, 9, 6]) spawnObject('cell', safeLane, state.nextRowZ - distance);
    row.kinds.forEach((kind, laneIndex) => {
      if (kind === null) return;
      spawnObject(kind, (laneIndex - 1) as Lane, state.nextRowZ);
    });
    state.nextRowIndex += 1;
    state.nextRowZ += row.gap;
  }
}

function objectVerticalBounds(kind: ObjectKind): [number, number] {
  if (kind === 'barrier') return [0, 0.72];
  if (kind === 'gate') return [0.85, 2.4];
  if (kind === 'blocker') return [0, 2.2];
  return [0.55, 1.45];
}

function intersectsRunner(state: RunState, object: TrackObject): boolean {
  const minimumZ = Math.min(object.previousZ, object.z) - OBJECT_HALF_DEPTH;
  const maximumZ = Math.max(object.previousZ, object.z) + OBJECT_HALF_DEPTH;
  if (maximumZ < -RUNNER_HALF_DEPTH || minimumZ > RUNNER_HALF_DEPTH) return false;

  const runnerHeight = state.runner.slideRemaining > 0 ? 0.65 : 1.6;
  const runner = new BoundingBox(
    new Vector3(state.runner.x - RUNNER_HALF_WIDTH, state.runner.y, -RUNNER_HALF_DEPTH),
    new Vector3(state.runner.x + RUNNER_HALF_WIDTH, state.runner.y + runnerHeight, RUNNER_HALF_DEPTH),
  );
  const [minimumY, maximumY] = objectVerticalBounds(object.kind);
  const x = LANE_CENTERS[object.lane + 1];
  const target = new BoundingBox(
    new Vector3(x - OBJECT_HALF_WIDTH, minimumY, minimumZ),
    new Vector3(x + OBJECT_HALF_WIDTH, maximumY, maximumZ),
  );
  return BoundingBox.Intersects(runner, target);
}

function processCollision(state: RunState, object: TrackObject, events: GameEvent[]): void {
  if (!object.active || !intersectsRunner(state, object)) return;
  if (object.kind === 'cell') {
    object.active = false;
    state.cells += 1;
    events.push({ kind: 'cell', objectId: object.id });
    return;
  }
  if (object.kind === 'shield') {
    object.active = false;
    state.runner.shieldRemaining = SHIELD_DURATION;
    events.push({ kind: 'shield', objectId: object.id });
    return;
  }
  if (state.runner.immunityRemaining > 0) {
    object.active = false;
    return;
  }
  object.active = false;
  if (state.runner.shieldRemaining > 0) {
    state.runner.shieldRemaining = 0;
    state.runner.immunityRemaining = IMMUNITY_DURATION;
    events.push({ kind: 'impact', objectId: object.id });
    return;
  }
  state.phase = 'gameover';
  events.push({ kind: 'impact', objectId: object.id }, { kind: 'gameover', objectId: object.id });
}

export function stepRun(state: RunState, dt: number): GameEvent[] {
  if (state.phase !== 'running' || !Number.isFinite(dt) || dt <= 0) return [];
  const events = state.pendingEvents.splice(0);
  const runner = state.runner;
  state.elapsed += dt;
  state.speed = Math.min(MAX_SPEED, INITIAL_SPEED + ((MAX_SPEED - INITIAL_SPEED) * state.elapsed) / SPEED_RAMP_SECONDS);
  state.distance += state.speed * dt;
  runner.x = approach(runner.x, LANE_CENTERS[runner.lane + 1], LANE_MOVE_SPEED * dt);
  if (runner.y > 0 || runner.vy > 0) {
    runner.y += runner.vy * dt;
    runner.vy -= GRAVITY * dt;
    if (runner.y <= 0) { runner.y = 0; runner.vy = 0; }
  }
  runner.slideRemaining = Math.max(0, runner.slideRemaining - dt);
  runner.shieldRemaining = Math.max(0, runner.shieldRemaining - dt);
  runner.immunityRemaining = Math.max(0, runner.immunityRemaining - dt);
  for (const object of state.objects) {
    object.previousZ = object.z;
    object.z -= state.speed * dt;
    processCollision(state, object, events);
    if (events.some((event) => event.kind === 'gameover')) break;
  }
  state.nextRowZ -= state.speed * dt;
  spawnRows(state);
  state.objects = state.objects.filter((object) => object.active && object.z >= DESPAWN_BEHIND);
  state.score = Math.floor(state.distance) + state.cells * 25;
  return events;
}
