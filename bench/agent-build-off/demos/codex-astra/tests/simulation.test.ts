import { describe, expect, test } from 'vitest';
import { applyCommand, createRun, stepRun } from '../src/game/simulation';
import type { ObjectKind, RunState } from '../src/game/types';

const STEP = 1 / 120;

function runningRun(seed = 7): RunState {
  const state = createRun(seed);
  state.phase = 'running';
  return state;
}

function addObject(state: RunState, kind: ObjectKind, z: number, lane = 0): void {
  state.objects.push({ id: 99, kind, lane: lane as -1 | 0 | 1, z, previousZ: z, active: true });
}

test('lane commands remain inside the track', () => {
  const state = runningRun();
  applyCommand(state, 'left');
  applyCommand(state, 'left');
  expect(state.runner.lane).toBe(-1);
  for (let i = 0; i < 60; i += 1) stepRun(state, STEP);
  expect(state.runner.x).toBeCloseTo(-2.6);
});

test('pause stops movement and scoring', () => {
  const state = createRun(7);
  state.phase = 'paused';
  const before = structuredClone(state);
  stepRun(state, STEP);
  expect(state).toEqual(before);
});

test('jump lands and cannot restart in the air', () => {
  const state = runningRun();
  applyCommand(state, 'jump');
  stepRun(state, STEP);
  const velocity = state.runner.vy;
  applyCommand(state, 'jump');
  expect(state.runner.vy).toBe(velocity);
  for (let i = 0; i < 120; i += 1) stepRun(state, STEP);
  expect(state.runner.y).toBe(0);
  expect(state.runner.vy).toBe(0);
});

test('duplicate jump commands before a step emit one jump', () => {
  const state = runningRun();
  applyCommand(state, 'jump');
  applyCommand(state, 'jump');
  expect(stepRun(state, STEP).filter(({ kind }) => kind === 'jump')).toHaveLength(1);
});

test('jump and slide remain exclusive', () => {
  const jumping = runningRun();
  applyCommand(jumping, 'jump');
  applyCommand(jumping, 'slide');
  expect(jumping.runner.slideRemaining).toBe(0);

  const sliding = runningRun();
  applyCommand(sliding, 'slide');
  applyCommand(sliding, 'jump');
  expect(sliding.runner.vy).toBe(0);
  for (let i = 0; i < 84; i += 1) stepRun(sliding, STEP);
  expect(sliding.runner.slideRemaining).toBe(0);
});

test('movement commands emit one event on the next step', () => {
  const jumping = runningRun();
  applyCommand(jumping, 'jump');
  expect(stepRun(jumping, STEP).map(({ kind }) => kind)).toContain('jump');
  expect(stepRun(jumping, STEP).map(({ kind }) => kind)).not.toContain('jump');

  const sliding = runningRun();
  applyCommand(sliding, 'slide');
  expect(stepRun(sliding, STEP).map(({ kind }) => kind)).toContain('slide');
});

test('commands outside running do not change the runner', () => {
  const state = createRun(1);
  const before = structuredClone(state.runner);
  for (const command of ['left', 'right', 'jump', 'slide'] as const) applyCommand(state, command);
  expect(state.runner).toEqual(before);
});

test('speed caps after 120 active seconds', () => {
  const state = runningRun();
  state.runner.immunityRemaining = 1_000;
  for (let i = 0; i < 121; i += 1) stepRun(state, 1);
  expect(state.speed).toBe(32);
  expect(state.score).toBe(Math.floor(state.distance) + state.cells * 25);
});

test('stepRun creates a safe four-second opening and bounded objects', () => {
  const state = runningRun(4);
  state.runner.immunityRemaining = 1_000;
  stepRun(state, STEP);
  const dangers = state.objects.filter(({ kind }) => ['barrier', 'gate', 'blocker'].includes(kind));
  expect(Math.min(...dangers.map(({ z }) => z))).toBeGreaterThanOrEqual(16 * 4 - 0.2);
  for (let i = 0; i < 6000; i += 1) stepRun(state, STEP);
  expect(state.objects.length).toBeLessThan(80);
});

test('objects stay bounded with unique identifiers for 120 seconds', () => {
  const state = runningRun(4);
  state.runner.immunityRemaining = 1_000;
  let maximumObjectCount = 0;
  for (let i = 0; i < 120 / STEP; i += 1) {
    stepRun(state, STEP);
    maximumObjectCount = Math.max(maximumObjectCount, state.objects.length);
    expect(new Set(state.objects.map(({ id }) => id)).size).toBe(state.objects.length);
  }
  expect(maximumObjectCount).toBeLessThan(80);
});

test('spawned rows include safe collectible trails', () => {
  const state = runningRun(4);
  stepRun(state, STEP);
  expect(state.objects.filter(({ kind, lane }) => kind === 'cell' && lane === 0).map(({ z }) => z))
    .toEqual(expect.arrayContaining([8, 12, 16, 20, 24, 28]));

  const damagingKinds = new Set<ObjectKind>(['barrier', 'gate', 'blocker']);
  const rowPositions = [...new Set(state.objects.filter(({ kind }) => damagingKinds.has(kind)).map(({ z }) => z))];
  for (const rowZ of rowPositions) {
    const damagingLanes = new Set(state.objects
      .filter(({ kind, z }) => z === rowZ && damagingKinds.has(kind))
      .map(({ lane }) => lane));
    const trail = state.objects.filter(({ kind, z }) => kind === 'cell' && [6, 9, 12, 15].includes(rowZ - z));
    expect(trail).toHaveLength(4);
    expect(new Set(trail.map(({ lane }) => lane)).size).toBe(1);
    expect(damagingLanes.has(trail[0].lane)).toBe(false);
  }
});

test('damaging objects cannot end the run during the first four seconds', () => {
  const state = runningRun(4);
  for (let i = 0; i < 479; i += 1) stepRun(state, STEP);
  expect(state.elapsed).toBeLessThan(4);
  expect(state.phase).toBe('running');
});

describe('collisions', () => {
  test('uses the runner actual x position', () => {
    const state = runningRun();
    state.runner.lane = 1;
    state.runner.x = 0;
    addObject(state, 'blocker', 0.1);
    expect(stepRun(state, STEP).map(({ kind }) => kind)).toContain('gameover');
  });

  test('detects an obstacle that crosses the runner in one step', () => {
    const state = runningRun();
    state.speed = 32;
    addObject(state, 'blocker', 1);
    expect(stepRun(state, 0.05).map(({ kind }) => kind)).toContain('gameover');
  });

  test('a jump clears a barrier', () => {
    const state = runningRun();
    state.runner.y = 0.8;
    addObject(state, 'barrier', 0.1);
    expect(stepRun(state, STEP).map(({ kind }) => kind)).not.toContain('gameover');
  });

  test('a timed jump clears an approaching barrier', () => {
    const state = runningRun();
    state.nextRowZ = 1_000;
    addObject(state, 'barrier', 8);
    applyCommand(state, 'jump');
    for (let i = 0; i < 75; i += 1) stepRun(state, STEP);
    expect(state.phase).toBe('running');
    expect(state.objects[0].z).toBeLessThan(-0.3);
  });

  test('a slide clears a gate', () => {
    const state = runningRun();
    applyCommand(state, 'slide');
    addObject(state, 'gate', 0.1);
    expect(stepRun(state, STEP).map(({ kind }) => kind)).not.toContain('gameover');
  });

  test('a timed slide clears an approaching gate', () => {
    const state = runningRun();
    state.nextRowZ = 1_000;
    addObject(state, 'gate', 8);
    applyCommand(state, 'slide');
    for (let i = 0; i < 75; i += 1) stepRun(state, STEP);
    expect(state.phase).toBe('running');
    expect(state.objects[0].z).toBeLessThan(-0.3);
  });

  test('actual movement reaches the opposite escape lane at maximum speed', () => {
    const state = runningRun();
    state.elapsed = 120;
    state.speed = 32;
    state.runner.lane = -1;
    state.runner.x = -2.6;
    state.nextRowZ = 1_000;
    addObject(state, 'blocker', 38, -1);
    state.objects.push({ id: 100, kind: 'blocker', lane: 0, z: 38, previousZ: 38, active: true });
    applyCommand(state, 'right');
    applyCommand(state, 'right');
    for (let i = 0; i < 150; i += 1) stepRun(state, STEP);
    expect(state.phase).toBe('running');
    expect(state.runner.x).toBe(2.6);
  });

  test('an energy cell contributes points once', () => {
    const state = runningRun(1);
    addObject(state, 'cell', 0.1);
    stepRun(state, STEP);
    stepRun(state, STEP);
    expect(state.cells).toBe(1);
    expect(state.score).toBe(Math.floor(state.distance) + 25);
  });

  test('a shield absorbs one impact and grants immunity', () => {
    const state = runningRun();
    state.runner.shieldRemaining = 8;
    addObject(state, 'blocker', 0.1);
    const events = stepRun(state, STEP);
    expect(events.map(({ kind }) => kind)).toEqual(['impact']);
    expect(state.runner.shieldRemaining).toBe(0);
    expect(state.runner.immunityRemaining).toBeGreaterThan(0.9);
    expect(state.phase).toBe('running');
  });

  test('immunity prevents impact until it expires', () => {
    const state = runningRun();
    state.runner.immunityRemaining = 0.01;
    addObject(state, 'blocker', 0.1);
    expect(stepRun(state, STEP)).toEqual([]);
    addObject(state, 'blocker', 0.1);
    expect(stepRun(state, STEP).map(({ kind }) => kind)).toContain('gameover');
  });

  test('collecting a shield refreshes its duration', () => {
    const state = runningRun();
    state.runner.shieldRemaining = 2;
    addObject(state, 'shield', 0.1);
    expect(stepRun(state, STEP).map(({ kind }) => kind)).toContain('shield');
    expect(state.runner.shieldRemaining).toBeGreaterThan(7.9);
  });
});
