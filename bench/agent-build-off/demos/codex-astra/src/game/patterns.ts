import { MINIMUM_ROW_GAP } from './config';
import type { PatternRow } from './types';

export type { PatternRow } from './types';

const INTRO: PatternRow[] = [
  { kinds: [null, 'barrier', null], gap: MINIMUM_ROW_GAP },
  { kinds: [null, 'gate', null], gap: MINIMUM_ROW_GAP },
  { kinds: [null, 'blocker', null], gap: MINIMUM_ROW_GAP },
];

const CATALOG: PatternRow[] = [
  { kinds: ['blocker', null, 'cell'], gap: 38 },
  { kinds: [null, 'barrier', 'blocker'], gap: 40 },
  { kinds: ['gate', 'cell', null], gap: 39 },
  { kinds: ['cell', 'blocker', 'barrier'], gap: 42 },
  { kinds: [null, 'shield', 'gate'], gap: 44 },
  { kinds: ['barrier', null, 'gate'], gap: 41 },
  { kinds: ['blocker', 'cell', null], gap: 38 },
  { kinds: [null, 'cell', 'blocker'], gap: 43 },
];

function nextRandom(value: number): number {
  let next = value | 0;
  next ^= next << 13;
  next ^= next >>> 17;
  next ^= next << 5;
  return next >>> 0;
}

export function createPatternSequence(seed: number, count: number): PatternRow[] {
  const rows = INTRO.slice(0, count).map((row) => ({
    ...row,
    kinds: [row.kinds[0], row.kinds[1], row.kinds[2]] as PatternRow['kinds'],
  }));
  let random = seed >>> 0 || 0x9e3779b9;
  while (rows.length < count) {
    random = nextRandom(random);
    const source = CATALOG[random % CATALOG.length];
    rows.push({
      ...source,
      kinds: [source.kinds[0], source.kinds[1], source.kinds[2]],
    });
  }
  return rows;
}
