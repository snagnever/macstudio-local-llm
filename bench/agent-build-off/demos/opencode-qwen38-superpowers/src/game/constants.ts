export const LANE_W = 2.4;
export const LANE_X = [-LANE_W, 0, LANE_W];
export const PLAYER_H = 1.6;
export const PLAYER_SLIDE_H = 0.7;
export const PLAYER_D = 0.6;
export const GRAVITY = 55;
export const JUMP_V = 15.1;
export const SLIDE_TIME = 0.6;
export const SPEED_START = 18;
export const SPEED_MAX = 40;
export const SPEED_RAMP = 0.25;
export const MAX_DT = 0.05;
export const ROW_GAP = 18;
export const SPAWN_Z = -120;
export const DESPAWN_Z = 12;
export const DEPTH = 0.8;
export const BARRIER_H = 1.0;
export const GATE_BOTTOM = 0.9;
export const GATE_TOP = 2.6;
export const WALL_TOP = 4;
export const COIN_Y = 0.9;
export const COIN_Y_HIGH = 2.2;
export const COIN_SPACING = 2.2;
export const COIN_Z_TOL = 1.2;
export const COIN_Y_TOL = 1.1;
export const SCORE_PER_COIN = 10;
export const LANE_LERP = 16;
export const SWIPE_MIN = 30;
export const HUD_SYNC_INTERVAL = 0.25;
export const STORAGE_KEY = 'hyper-runner.best';
export const FOV_BASE = 70;
export const FOV_FAST = 78;
export const FOG_DENSITY = 0.022;
export const BURST_LIFE = 0.45;
export const BURST_POOL = 6;
export const COLOR = {
  bg: '#070311',
  fog: '#2a0b45',
  cyan: '#00f6ff',
  magenta: '#ff2bd6',
  violet: '#8b5cf6',
  yellow: '#ffd93d',
  white: '#f4f0ff',
} as const;
