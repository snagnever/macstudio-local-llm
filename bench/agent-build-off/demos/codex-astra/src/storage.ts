import type { Preferences, SavedData } from './game/types';

const STORAGE_KEY = 'hyper-runner:v1';
const DEFAULT_PREFERENCES: Preferences = {
  muted: false,
  quality: 'high',
  reducedMotion: false,
};

function defaults(): SavedData {
  return { version: 1, bestScore: 0, preferences: { ...DEFAULT_PREFERENCES } };
}

function isPreferences(value: unknown): value is Preferences {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Partial<Preferences>;
  return typeof candidate.muted === 'boolean'
    && (candidate.quality === 'high' || candidate.quality === 'low')
    && typeof candidate.reducedMotion === 'boolean';
}

export function readSaved(storage: Pick<Storage, 'getItem'>): SavedData {
  try {
    const stored = storage.getItem(STORAGE_KEY);
    if (stored === null) return defaults();
    const value: unknown = JSON.parse(stored);
    if (typeof value !== 'object' || value === null) return defaults();
    const candidate = value as Partial<SavedData>;
    if (candidate.version !== 1) return defaults();
    if (!Number.isFinite(candidate.bestScore) || (candidate.bestScore ?? -1) < 0) return defaults();
    if (!Number.isSafeInteger(candidate.bestScore) || !isPreferences(candidate.preferences)) return defaults();
    return {
      version: 1,
      bestScore: candidate.bestScore as number,
      preferences: { ...candidate.preferences },
    };
  } catch {
    return defaults();
  }
}

export function writeSaved(storage: Pick<Storage, 'setItem'>, data: SavedData): void {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Storage is optional. The controller retains its in-memory value.
  }
}
