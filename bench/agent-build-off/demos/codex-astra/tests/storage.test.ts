import { expect, test } from 'vitest';
import { readSaved, writeSaved } from '../src/storage';

const defaults = {
  version: 1 as const,
  bestScore: 0,
  preferences: { muted: false, quality: 'high' as const, reducedMotion: false },
};

test.each([null, '{', '{"version":2}', '{"version":1,"bestScore":-1}', '{"version":1,"bestScore":null}'])(
  'invalid stored value %s returns safe defaults',
  (value) => {
    expect(readSaved({ getItem: () => value })).toEqual(defaults);
  },
);

test('storage failure returns safe defaults', () => {
  const storage = { getItem(): string | null { throw new Error('Access denied'); } };
  expect(readSaved(storage)).toEqual(defaults);
});

test('readSaved accepts a complete valid value', () => {
  const value = JSON.stringify({
    version: 1,
    bestScore: 125,
    preferences: { muted: true, quality: 'low', reducedMotion: true },
  });
  expect(readSaved({ getItem: () => value }).bestScore).toBe(125);
});

test('readSaved rejects an unsafe integer score', () => {
  const value = JSON.stringify({
    version: 1,
    bestScore: 1e100,
    preferences: { muted: false, quality: 'high', reducedMotion: false },
  });
  expect(readSaved({ getItem: () => value })).toEqual(defaults);
});

test('writeSaved uses the versioned key and suppresses access errors', () => {
  let key = '';
  let value = '';
  writeSaved({ setItem(nextKey, nextValue) { key = nextKey; value = nextValue; } }, defaults);
  expect(key).toBe('hyper-runner:v1');
  expect(JSON.parse(value)).toEqual(defaults);
  expect(() => writeSaved({ setItem() { throw new Error('denied'); } }, defaults)).not.toThrow();
});
