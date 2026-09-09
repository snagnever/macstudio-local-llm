import { BARRIER_H, GATE_BOTTOM, GATE_TOP, WALL_TOP } from './constants';
import type { ObstacleDef, ObstacleKind, PlayerState } from './types';

export interface Box {
  bottom: number;
  top: number;
}

export function obstacleBox(kind: ObstacleKind): Box {
  switch (kind) {
    case 'barrier':
      return { bottom: 0, top: BARRIER_H };
    case 'gate':
      return { bottom: GATE_BOTTOM, top: GATE_TOP };
    case 'wall':
      return { bottom: 0, top: WALL_TOP };
  }
}

export function collides(obstacle: ObstacleDef, player: PlayerState): boolean {
  if (obstacle.lane !== player.lane) return false;
  const box = obstacleBox(obstacle.kind);
  const playerTop = player.y + player.height;
  return player.y < box.top && box.bottom < playerTop;
}
