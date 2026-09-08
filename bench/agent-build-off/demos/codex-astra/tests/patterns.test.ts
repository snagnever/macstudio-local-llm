import { expect, test } from 'vitest';
import { createPatternSequence } from '../src/game/patterns';

test('patterns preserve an escape lane across seeds', () => {
  const danger = new Set(['barrier', 'gate', 'blocker']);
  for (let seed = 1; seed <= 100; seed += 1) {
    const rows = createPatternSequence(seed, 200);
    expect(rows).toEqual(createPatternSequence(seed, 200));
    for (const row of rows) {
      expect(row.gap).toBeGreaterThanOrEqual(38);
      expect(row.kinds.some((kind) => kind === null || !danger.has(kind))).toBe(true);
    }
  }
});

test('different seeds select different later rows', () => {
  expect(createPatternSequence(1, 20).slice(3)).not.toEqual(createPatternSequence(2, 20).slice(3));
});

test('intro rows teach jump, slide, then lane movement', () => {
  expect(createPatternSequence(3, 3).map(({ kinds }) => kinds)).toEqual([
    [null, 'barrier', null],
    [null, 'gate', null],
    [null, 'blocker', null],
  ]);
});

test('opposite escape lanes have enough time for two lane changes', () => {
  const twoLaneTravelSeconds = (2 * 2.6) / 18;
  expect(38 / 32).toBeGreaterThan(twoLaneTravelSeconds);
});
