import { describe, expect, it } from 'vitest';
import { formatSeed, mulberry32, randomSeed } from './rng';

describe('mulberry32', () => {
  it('produces a deterministic sequence for a fixed seed', () => {
    const a = mulberry32(123);
    const b = mulberry32(123);
    const seqA = [a(), a(), a(), a(), a()];
    const seqB = [b(), b(), b(), b(), b()];
    expect(seqA).toEqual(seqB);
  });

  it('produces values in [0, 1)', () => {
    const rand = mulberry32(999);
    for (let i = 0; i < 1000; i++) {
      const v = rand();
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(1);
    }
  });

  it('different seeds give different sequences', () => {
    expect(mulberry32(1)()).not.toBe(mulberry32(2)());
  });
});

describe('formatSeed / randomSeed', () => {
  it('formats seeds in base36 uppercase', () => {
    expect(formatSeed(123)).toBe('3F');
  });

  it('round-trips through parseInt base36', () => {
    const seed = randomSeed();
    expect(parseInt(formatSeed(seed), 36)).toBe(seed);
  });
});
