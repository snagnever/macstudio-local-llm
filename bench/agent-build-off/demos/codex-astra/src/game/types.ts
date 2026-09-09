export type Lane = -1 | 0 | 1;
export type Phase = 'loading' | 'error' | 'ready' | 'running' | 'paused' | 'gameover';
export type Command = 'left' | 'right' | 'jump' | 'slide';
export type Quality = 'high' | 'low';
export type ObjectKind = 'barrier' | 'gate' | 'blocker' | 'cell' | 'shield';
export type EventKind = 'jump' | 'slide' | 'cell' | 'shield' | 'impact' | 'gameover';

export interface RunnerState {
  lane: Lane;
  x: number;
  y: number;
  vy: number;
  slideRemaining: number;
  shieldRemaining: number;
  immunityRemaining: number;
}

export interface TrackObject {
  id: number;
  kind: ObjectKind;
  lane: Lane;
  z: number;
  previousZ: number;
  active: boolean;
}

export interface PatternRow {
  kinds: [ObjectKind | null, ObjectKind | null, ObjectKind | null];
  gap: number;
}

export interface RunState {
  phase: Phase;
  seed: number;
  elapsed: number;
  distance: number;
  speed: number;
  score: number;
  cells: number;
  runner: RunnerState;
  objects: TrackObject[];
  nextObjectId: number;
  nextRowIndex: number;
  nextRowZ: number;
  patterns: PatternRow[];
  pendingEvents: GameEvent[];
}

export interface GameEvent {
  kind: EventKind;
  objectId?: number;
}

export interface Preferences {
  muted: boolean;
  quality: Quality;
  reducedMotion: boolean;
}

export interface SavedData {
  version: 1;
  bestScore: number;
  preferences: Preferences;
}
