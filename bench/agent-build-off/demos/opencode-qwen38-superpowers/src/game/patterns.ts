import type { ObstacleDef, ObstacleKind, RowDef } from './types';

export interface Pattern {
  name: string;
  weight: number;
  build: (rand: () => number) => RowDef;
}

function pickLanes(rand: () => number, n: number): number[] {
  const lanes = [0, 1, 2];
  for (let i = lanes.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [lanes[i], lanes[j]] = [lanes[j], lanes[i]];
  }
  return lanes.slice(0, n);
}

function single(kind: ObstacleKind, name: string, rand: () => number): RowDef {
  const [lane] = pickLanes(rand, 1);
  const obstacles: ObstacleDef[] = [{ kind, lane }];
  const bonus = kind === 'barrier' && rand() < 0.3;
  return {
    name,
    obstacles,
    coins: bonus ? { lane, count: 2, high: true } : null,
  };
}

function double(kind: ObstacleKind, name: string, rand: () => number): RowDef {
  return { name, obstacles: pickLanes(rand, 2).map((lane) => ({ kind, lane })), coins: null };
}

function coinLine(rand: () => number): RowDef {
  return {
    name: 'coin-line',
    obstacles: [],
    coins: { lane: Math.floor(rand() * 3), count: 3 + Math.floor(rand() * 3), high: false },
  };
}

export const PATTERNS: Pattern[] = [
  { name: 'barrier-single', weight: 22, build: (r) => single('barrier', 'barrier-single', r) },
  { name: 'barrier-double', weight: 16, build: (r) => double('barrier', 'barrier-double', r) },
  { name: 'gate-single', weight: 18, build: (r) => single('gate', 'gate-single', r) },
  { name: 'gate-double', weight: 12, build: (r) => double('gate', 'gate-double', r) },
  { name: 'wall-single', weight: 14, build: (r) => single('wall', 'wall-single', r) },
  { name: 'wall-double', weight: 8, build: (r) => double('wall', 'wall-double', r) },
  { name: 'coin-line', weight: 10, build: coinLine },
];

const TOTAL_WEIGHT = PATTERNS.reduce((sum, p) => sum + p.weight, 0);

export function generateRow(rand: () => number): RowDef {
  let roll = rand() * TOTAL_WEIGHT;
  for (const p of PATTERNS) {
    roll -= p.weight;
    if (roll < 0) return p.build(rand);
  }
  return PATTERNS[0].build(rand);
}

export function isWinnable(row: RowDef): boolean {
  const lanes = new Set(row.obstacles.map((o) => o.lane));
  return lanes.size < 3;
}
