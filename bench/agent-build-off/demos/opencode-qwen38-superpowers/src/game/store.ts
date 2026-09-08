import { create } from 'zustand';
import type { Intent, Phase } from './types';
import { resetWorld, world } from './runtime';
import { STORAGE_KEY } from './constants';

const MAX_QUEUED_INTENTS = 8;

function loadBest(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return 0;
    const n = Number(raw);
    return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
  } catch {
    return 0;
  }
}

function saveBest(best: number): void {
  try {
    localStorage.setItem(STORAGE_KEY, String(best));
  } catch {
    // storage unavailable (Safari private mode etc.) — best lives in memory only
  }
}

export interface GameState {
  phase: Phase;
  score: number;
  coins: number;
  speed: number;
  best: number;
  seedLabel: string;
  muted: boolean;
  intents: Intent[];
  confirm: (seed?: number) => void;
  pause: () => void;
  resume: () => void;
  toMenu: () => void;
  queueIntent: (intent: Intent) => void;
  drainIntents: () => Intent[];
  syncHud: () => void;
  toggleMute: () => void;
}

export const useGame = create<GameState>()((set, get) => ({
  phase: 'menu',
  score: 0,
  coins: 0,
  speed: 0,
  best: loadBest(),
  seedLabel: '',
  muted: false,
  intents: [],

  confirm: (seed?: number) => {
    resetWorld(seed);
    world.phase = 'running';
    set({
      phase: 'running',
      score: 0,
      coins: 0,
      speed: world.speed,
      seedLabel: world.seedLabel,
      intents: [],
    });
  },

  pause: () => {
    if (world.phase !== 'running') return;
    world.phase = 'paused';
    set({ phase: 'paused' });
  },

  resume: () => {
    if (world.phase !== 'paused') return;
    world.phase = 'running';
    set({ phase: 'running' });
  },

  toMenu: () => {
    world.phase = 'menu';
    set({ phase: 'menu', intents: [] });
  },

  queueIntent: (intent) => {
    const intents = get().intents;
    if (intents.length < MAX_QUEUED_INTENTS) set({ intents: [...intents, intent] });
  },

  drainIntents: () => {
    const intents = get().intents;
    if (intents.length === 0) return intents;
    set({ intents: [] });
    return intents;
  },

  syncHud: () => {
    const s = get();
    const total = Math.floor(world.score + world.distance);
    if (world.phase === 'over' && s.phase !== 'over') {
      const best = Math.max(s.best, total);
      saveBest(best);
      set({ phase: 'over', best, score: total, coins: world.coins });
      return;
    }
    if (world.phase === 'running' && s.phase === 'running') {
      set({ score: total, coins: world.coins, speed: world.speed });
    }
    if (s.seedLabel !== world.seedLabel) set({ seedLabel: world.seedLabel });
  },

  toggleMute: () => set({ muted: !get().muted }),
}));
