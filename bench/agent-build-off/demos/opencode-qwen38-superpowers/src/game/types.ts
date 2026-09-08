export type Intent = 'left' | 'right' | 'jump' | 'slide' | 'pause' | 'confirm';
export type ObstacleKind = 'barrier' | 'gate' | 'wall';
export type Phase = 'menu' | 'running' | 'paused' | 'over';
export type GameEvent = 'lane' | 'jump' | 'slide' | 'land' | 'coin' | 'crash';

export interface ObstacleDef {
  kind: ObstacleKind;
  lane: number;
}

export interface CoinDef {
  lane: number;
  count: number;
  high: boolean;
}

export interface RowDef {
  name: string;
  obstacles: ObstacleDef[];
  coins: CoinDef | null;
}

export interface CoinEntity {
  lane: number;
  z: number;
  y: number;
  taken: boolean;
}

export interface RowEntity {
  z: number;
  obstacles: ObstacleDef[];
  coins: CoinEntity[];
}

export interface Burst {
  x: number;
  y: number;
  z: number;
  t: number;
}

export interface PlayerState {
  lane: number;
  x: number;
  y: number;
  vy: number;
  height: number;
  sliding: boolean;
  slideT: number;
  onGround: boolean;
}
