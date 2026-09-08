import { beforeEach, describe, expect, it } from 'vitest';
import { resetWorld, step, world } from './runtime';
import {
  COIN_Y,
  COIN_Y_HIGH,
  GRAVITY,
  JUMP_V,
  LANE_X,
  MAX_DT,
  PLAYER_H,
  PLAYER_SLIDE_H,
  SCORE_PER_COIN,
  SLIDE_TIME,
  SPEED_MAX,
  SPEED_RAMP,
  SPEED_START,
} from './constants';

beforeEach(() => {
  resetWorld(123);
  world.phase = 'running';
});

describe('resetWorld', () => {
  it('puts the player in the center lane on the ground', () => {
    expect(world.player.lane).toBe(1);
    expect(world.player.x).toBeCloseTo(LANE_X[1]);
    expect(world.player.y).toBe(0);
    expect(world.player.height).toBe(PLAYER_H);
  });
  it('starts at base speed with zero score/distance', () => {
    expect(world.speed).toBe(SPEED_START);
    expect(world.distance).toBe(0);
    expect(world.score).toBe(0);
    expect(world.coins).toBe(0);
  });
});

describe('lane movement', () => {
  it('left intent moves one lane and lerps x toward the target', () => {
    step(0.016, ['left']);
    expect(world.player.lane).toBe(0);
    expect(world.player.x).toBeLessThan(LANE_X[1]);
    expect(world.player.x).toBeGreaterThan(LANE_X[0]);
    for (let i = 0; i < 200; i++) step(0.016, []);
    expect(world.player.x).toBeCloseTo(LANE_X[0], 2);
  });
  it('clamps at the outer lanes', () => {
    step(0.016, ['left']);
    step(0.016, ['left']);
    expect(world.player.lane).toBe(0);
    step(0.016, ['right']);
    step(0.016, ['right']);
    step(0.016, ['right']);
    expect(world.player.lane).toBe(2);
  });
  it('emits a lane event', () => {
    step(0.016, ['left']);
    expect(world.events).toContain('lane');
  });
});

describe('jump physics', () => {
  it('jump sets vy and leaves the ground', () => {
    step(0.016, ['jump']);
    expect(world.player.onGround).toBe(false);
    expect(world.player.vy).toBeCloseTo(JUMP_V - GRAVITY * 0.016, 1);
    expect(world.events).toContain('jump');
  });
  it('arc peaks near JUMP_V^2/(2g) and lands back on y=0', () => {
    let peak = 0;
    for (let i = 0; i < 600; i++) {
      step(0.016, i === 0 ? ['jump'] : []);
      peak = Math.max(peak, world.player.y);
      if (world.player.onGround && i > 10) break;
    }
    expect(peak).toBeGreaterThan((JUMP_V * JUMP_V) / (2 * GRAVITY) - 0.15);
    expect(peak).toBeLessThan((JUMP_V * JUMP_V) / (2 * GRAVITY) + 0.15);
    expect(world.player.y).toBe(0);
    expect(world.events).toContain('land');
  });
  it('cannot double-jump mid-air', () => {
    step(0.016, ['jump']);
    const vyAfter = world.player.vy;
    for (let i = 0; i < 10; i++) step(0.016, []);
    step(0.016, ['jump']);
    expect(world.player.vy).toBeCloseTo(vyAfter - GRAVITY * 0.016 * 11, 1);
  });
});

describe('slide physics', () => {
  it('slide lowers height for SLIDE_TIME then restores', () => {
    step(0.016, ['slide']);
    expect(world.player.sliding).toBe(true);
    expect(world.player.height).toBe(PLAYER_SLIDE_H);
    expect(world.events).toContain('slide');
    let t = 0.016;
    while (t < SLIDE_TIME + 0.1 && world.player.sliding) {
      step(0.016, []);
      t += 0.016;
    }
    expect(world.player.sliding).toBe(false);
    expect(world.player.height).toBe(PLAYER_H);
  });
  it('jump during a slide cancels the slide early', () => {
    step(0.016, ['slide']);
    step(0.016, ['jump']);
    expect(world.player.sliding).toBe(false);
    expect(world.player.height).toBe(PLAYER_H);
    expect(world.player.onGround).toBe(false);
  });
});

describe('speed and time', () => {
  it('ramps speed by SPEED_RAMP per second up to SPEED_MAX', () => {
    for (let i = 0; i < 60; i++) step(0.016, []);
    expect(world.speed).toBeCloseTo(SPEED_START + SPEED_RAMP * 0.96, 1);
    for (let i = 0; i < 20000; i++) {
      if (world.phase === 'over') world.phase = 'running';
      step(0.016, []);
    }
    expect(world.speed).toBe(SPEED_MAX);
  });
  it('ignores huge dt spikes (max 50ms)', () => {
    const before = world.distance;
    step(5, []);
    const ramped = (SPEED_START + SPEED_RAMP * MAX_DT) * MAX_DT;
    expect(world.distance - before).toBeCloseTo(ramped, 3);
  });
  it('does nothing unless running', () => {
    world.phase = 'paused';
    const before = world.distance;
    step(0.016, ['left', 'jump']);
    expect(world.distance).toBe(before);
    expect(world.player.lane).toBe(1);
  });
});

describe('spawning', () => {
  it('spawns the first row after the initial gap elapses', () => {
    for (let i = 0; i < 700 && world.rows.length === 0; i++) step(0.016, []);
    expect(world.rows.length).toBeGreaterThan(0);
    expect(world.rows[0].z).toBeLessThan(0);
  });

  it('maintains ROW_GAP spacing between consecutive rows', () => {
    for (let i = 0; i < 2500; i++) step(0.016, []);
    const zs = world.rows.map((r) => r.z).sort((a, b) => a - b);
    for (let i = 1; i < zs.length; i++) {
      expect(zs[i] - zs[i - 1]).toBeCloseTo(18, 0);
    }
  });

  it('despawns rows behind the player', () => {
    for (let i = 0; i < 12000; i++) step(0.016, []);
    for (const row of world.rows) expect(row.z).toBeLessThan(12);
  });

  it('expands coin defs into COIN_SPACING-spaced entities at the right height', () => {
    const hasUntaken = () =>
      world.rows.some((r) => r.coins.length > 0 && r.coins.every((c) => !c.taken));
    for (let i = 0; i < 20000 && !hasUntaken(); i++) {
      if (world.phase === 'over') world.phase = 'running';
      step(0.016, []);
    }
    const row = world.rows.find((r) => r.coins.length > 0 && r.coins.every((c) => !c.taken));
    expect(row).toBeDefined();
    const coins = row!.coins;
    expect(coins.length).toBeGreaterThanOrEqual(2);
    for (let i = 1; i < coins.length; i++) {
      expect(coins[i].z - coins[i - 1].z).toBeCloseTo(2.2, 1);
    }
    for (const c of coins) {
      expect(c.taken).toBe(false);
      expect(c.y === 0.9 || c.y === 2.2).toBe(true);
    }
  });

  it('is deterministic: same seed replays the same row sequence', () => {
    resetWorld(777);
    world.phase = 'running';
    const a: string[] = [];
    for (let i = 0; i < 4000; i++) {
      step(0.016, []);
      for (const r of world.rows) a.push(`${r.z.toFixed(1)}:${r.obstacles.map((o) => o.kind[0] + o.lane).join(',')}`);
    }
    resetWorld(777);
    world.phase = 'running';
    const b: string[] = [];
    for (let i = 0; i < 4000; i++) {
      step(0.016, []);
      for (const r of world.rows) b.push(`${r.z.toFixed(1)}:${r.obstacles.map((o) => o.kind[0] + o.lane).join(',')}`);
    }
    expect(a).toEqual(b);
  });
});

function placeRow(z: number, obstacles: { kind: 'barrier' | 'gate' | 'wall'; lane: number }[]) {
  world.rows.push({ z, obstacles, coins: [] });
}

describe('collisions', () => {
  it('standing into a barrier in the same lane crashes', () => {
    placeRow(-1, [{ kind: 'barrier', lane: 1 }]);
    for (let i = 0; i < 200 && world.phase === 'running'; i++) step(0.016, []);
    expect(world.phase).toBe('over');
    expect(world.events).toContain('crash');
    expect(world.bursts.some((b) => b.t >= 0)).toBe(true);
  });

  it('jumping over that same barrier survives', () => {
    placeRow(-4, [{ kind: 'barrier', lane: 1 }]);
    // jump immediately so the peak (~2.07 m) covers the barrier window arrival
    for (let i = 0; i < 250 && world.phase === 'running'; i++) {
      step(0.016, i === 0 ? ['jump'] : []);
    }
    expect(world.phase).toBe('running');
  });

  it('sliding under a gate survives, standing crashes', () => {
    placeRow(-2, [{ kind: 'gate', lane: 1 }]);
    step(0.016, ['slide']);
    for (let i = 0; i < 200 && world.phase === 'running'; i++) step(0.016, []);
    expect(world.phase).toBe('running');

    placeRow(-1, [{ kind: 'gate', lane: 1 }]);
    for (let i = 0; i < 200 && world.phase === 'running'; i++) step(0.016, []);
    expect(world.phase).toBe('over');
  });

  it('changing lanes dodges a wall', () => {
    placeRow(-2, [{ kind: 'wall', lane: 1 }]);
    step(0.016, ['left']);
    for (let i = 0; i < 300 && world.phase === 'running'; i++) step(0.016, []);
    expect(world.phase).toBe('running');
    expect(world.player.lane).toBe(0);
  });

  it('one crash freezes motion for the rest of the step', () => {
    placeRow(-1, [{ kind: 'wall', lane: 1 }]);
    for (let i = 0; i < 200 && world.phase !== 'over'; i++) step(0.016, []);
    const d = world.distance;
    step(0.016, []);
    step(0.016, []);
    expect(world.distance).toBe(d);
  });
});

describe('coins', () => {
  it('collects a coin when the player is in the right lane and height', () => {
    world.rows.push({
      z: -1,
      obstacles: [],
      coins: [{ lane: 1, z: -1, y: COIN_Y, taken: false }],
    });
    for (let i = 0; i < 200 && world.coins === 0; i++) step(0.016, []);
    expect(world.coins).toBe(1);
    expect(world.score).toBe(SCORE_PER_COIN);
    expect(world.events).toContain('coin');
  });

  it('a high coin needs a jump', () => {
    const placeCoin = () => {
      world.rows.push({
        z: -1,
        obstacles: [],
        coins: [{ lane: 1, z: -1, y: COIN_Y_HIGH, taken: false }],
      });
    };
    placeCoin();
    for (let i = 0; i < 300 && world.coins === 0 && world.rows.length > 0; i++) step(0.016, []);
    expect(world.coins).toBe(0);
    placeCoin();
    for (let i = 0; i < 250 && world.coins === 0; i++) {
      step(0.016, i === 0 ? ['jump'] : []);
    }
    expect(world.coins).toBe(1);
  });

  it('a coin in another lane is missed', () => {
    world.rows.push({
      z: -1,
      obstacles: [],
      coins: [{ lane: 0, z: -1, y: COIN_Y, taken: false }],
    });
    for (let i = 0; i < 200; i++) step(0.016, []);
    expect(world.coins).toBe(0);
  });
});
