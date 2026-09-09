import { describe, expect, it } from 'vitest';
import { PATTERNS, generateRow, isWinnable } from './patterns';
import { mulberry32 } from './rng';

describe('patterns', () => {
  it('every generated row leaves at least one open lane', () => {
    for (let seed = 1; seed <= 200; seed++) {
      const rand = mulberry32(seed);
      for (let i = 0; i < 50; i++) {
        const row = generateRow(rand);
        expect(isWinnable(row)).toBe(true);
      }
    }
  });

  it('all patterns appear in a long sequence', () => {
    const rand = mulberry32(42);
    const names = new Set<string>();
    for (let i = 0; i < 4000; i++) names.add(generateRow(rand).name);
    for (const p of PATTERNS) expect(names.has(p.name)).toBe(true);
  });

  it('observed frequencies match declared weights', () => {
    const rand = mulberry32(7);
    const totalWeight = PATTERNS.reduce((s, p) => s + p.weight, 0);
    const counts = new Map<string, number>();
    const n = 20000;
    for (let i = 0; i < n; i++) {
      const name = generateRow(rand).name;
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
    for (const p of PATTERNS) {
      const share = (counts.get(p.name) ?? 0) / n;
      const expected = p.weight / totalWeight;
      expect(share).toBeGreaterThan(expected - 0.04);
      expect(share).toBeLessThan(expected + 0.04);
    }
  });

  it('barrier-single carries a bonus coin about 30% of the time', () => {
    const rand = mulberry32(9);
    let singles = 0;
    let withCoins = 0;
    for (let i = 0; i < 20000; i++) {
      const row = generateRow(rand);
      if (row.name === 'barrier-single') {
        singles++;
        if (row.coins) withCoins++;
      }
    }
    const share = withCoins / singles;
    expect(share).toBeGreaterThan(0.2);
    expect(share).toBeLessThan(0.4);
  });

  it('coin-line rows have 3-5 coins and no obstacles', () => {
    const rand = mulberry32(5);
    let seen = 0;
    for (let i = 0; i < 20000 && seen < 200; i++) {
      const row = generateRow(rand);
      if (row.name === 'coin-line') {
        seen++;
        expect(row.obstacles).toHaveLength(0);
        expect(row.coins).not.toBeNull();
        expect(row.coins!.count).toBeGreaterThanOrEqual(3);
        expect(row.coins!.count).toBeLessThanOrEqual(5);
        expect(row.coins!.high).toBe(false);
      }
    }
    expect(seen).toBe(200);
  });
});
