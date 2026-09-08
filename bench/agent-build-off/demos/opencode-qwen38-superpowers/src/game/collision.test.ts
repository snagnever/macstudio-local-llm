import { describe, expect, it } from 'vitest';
import { collides, obstacleBox } from './collision';
import type { ObstacleDef, PlayerState } from './types';
import { BARRIER_H, GATE_BOTTOM, GATE_TOP, PLAYER_H, PLAYER_SLIDE_H, WALL_TOP } from './constants';

function player(over: Partial<PlayerState> = {}): PlayerState {
  return {
    lane: 1,
    x: 0,
    y: 0,
    vy: 0,
    height: PLAYER_H,
    sliding: false,
    slideT: 0,
    onGround: true,
    ...over,
  };
}

const barrier: ObstacleDef = { kind: 'barrier', lane: 1 };
const gate: ObstacleDef = { kind: 'gate', lane: 1 };
const wall: ObstacleDef = { kind: 'wall', lane: 1 };

describe('obstacleBox', () => {
  it('barrier spans [0, BARRIER_H]', () => {
    expect(obstacleBox('barrier')).toEqual({ bottom: 0, top: BARRIER_H });
  });
  it('gate spans [GATE_BOTTOM, GATE_TOP]', () => {
    expect(obstacleBox('gate')).toEqual({ bottom: GATE_BOTTOM, top: GATE_TOP });
  });
  it('wall spans [0, WALL_TOP]', () => {
    expect(obstacleBox('wall')).toEqual({ bottom: 0, top: WALL_TOP });
  });
});

describe('collides', () => {
  it('ignores obstacles in other lanes', () => {
    expect(collides({ ...barrier, lane: 0 }, player())).toBe(false);
  });

  it('standing player hits a barrier', () => {
    expect(collides(barrier, player())).toBe(true);
  });

  it('jumped player clears a barrier', () => {
    expect(collides(barrier, player({ y: BARRIER_H + 0.01, onGround: false }))).toBe(false);
  });

  it('just-below-barrier-top still hits', () => {
    expect(collides(barrier, player({ y: BARRIER_H - 0.01, onGround: false }))).toBe(true);
  });

  it('standing player hits a gate', () => {
    expect(collides(gate, player())).toBe(true);
  });

  it('sliding player passes under a gate', () => {
    expect(
      collides(gate, player({ sliding: true, height: PLAYER_SLIDE_H })),
    ).toBe(false);
  });

  it('player above the gate top passes over it', () => {
    expect(
      collides(gate, player({ y: GATE_TOP + 0.01, height: PLAYER_H, onGround: false })),
    ).toBe(false);
  });

  it('wall hits whether standing, jumping, or sliding', () => {
    expect(collides(wall, player())).toBe(true);
    expect(collides(wall, player({ y: 2, onGround: false }))).toBe(true);
    expect(collides(wall, player({ sliding: true, height: PLAYER_SLIDE_H }))).toBe(true);
    expect(collides(wall, player({ y: WALL_TOP + 0.01, onGround: false }))).toBe(false);
  });

  it('wall in another lane never hits', () => {
    expect(collides({ ...wall, lane: 2 }, player())).toBe(false);
  });
});
