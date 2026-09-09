/** Every tunable in the game. Nothing else should hold a magic number. */

export const LANES = [-2.4, 0, 2.4]

/** Forward is -z. The player stays at z = 0 and the track moves toward it. */
export const SPAWN_Z = -190
export const RECYCLE_Z = 12
/** A run starts with this much clear track, then the spawner fills everything beyond it. */
export const RUNWAY_Z = -55

export const SPEED_START = 14
export const SPEED_GAIN = 0.35
export const SPEED_MAX = 42

export const LANE_CHANGE_TIME = 0.12
export const JUMP_TIME = 0.62
export const JUMP_HEIGHT = 2.2
export const SLIDE_TIME = 0.55
export const INPUT_BUFFER = 0.15

/** Drawn size is the model; this is the collision box, kept forgiving on purpose. */
export const PLAYER_WIDTH = 0.6
export const PLAYER_DEPTH = 0.8
export const PLAYER_HEIGHT = 1.7
export const PLAYER_SLIDE_HEIGHT = 0.8

export const TUNNEL_RADIUS = 6.2
export const RIB_SPACING = 7
export const RIB_COUNT = 34

export const COIN_VALUE = 10
export const BEST_KEY = 'hyper-runner.best'

/**
 * Obstacle boxes, given as half extents plus the centre height of the box. `hx` is the
 * drawn width; `chx` is the narrower width used for collision, so a lane change that is
 * still in flight can squeeze past a neighbouring wall.
 */
export const OBSTACLE_SHAPE = {
  barrier: { hx: 1.0, chx: 0.78, hy: 0.45, hz: 0.35, cy: 0.45 },
  beam: { hx: 1.0, chx: 0.78, hy: 0.55, hz: 0.35, cy: 2.05 },
  wall: { hx: 1.0, chx: 0.78, hy: 1.6, hz: 0.35, cy: 1.6 },
  drone: { hx: 0.5, chx: 0.42, hy: 0.5, hz: 0.5, cy: 1.5 },
} as const

export type ObstacleType = keyof typeof OBSTACLE_SHAPE

/** Drone lateral sweep. */
export const DRONE_SWEEP = 2.4
export const DRONE_RATE = 1.1

/** Difficulty runs from 0 to 1 over this many seconds. */
export const DIFFICULTY_RAMP = 90

export const SPEED_LINE_COUNT = 220
export const DEBRIS_COUNT = 14
