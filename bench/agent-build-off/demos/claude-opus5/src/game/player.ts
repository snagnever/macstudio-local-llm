import {
  INPUT_BUFFER,
  JUMP_HEIGHT,
  JUMP_TIME,
  LANES,
  LANE_CHANGE_TIME,
  PLAYER_HEIGHT,
  PLAYER_SLIDE_HEIGHT,
  SLIDE_TIME,
} from './config'

export type Intent = 'left' | 'right' | 'jump' | 'slide'

/** Cosmetic lean, in radians. */
const MAX_TILT = 0.28

export type Player = {
  lane: number
  x: number
  /** Lane change interpolation, from laneFromX to LANES[lane]. */
  laneFromX: number
  laneT: number
  y: number
  jumpT: number
  airborne: boolean
  slideT: number
  sliding: boolean
  /** Lean angle in radians, purely cosmetic. */
  tilt: number
  buffered: Intent | null
  bufferT: number
}

export function createPlayer(): Player {
  return {
    lane: 1,
    x: LANES[1],
    laneFromX: LANES[1],
    laneT: 1,
    y: 0,
    jumpT: 0,
    airborne: false,
    slideT: 0,
    sliding: false,
    tilt: 0,
    buffered: null,
    bufferT: 0,
  }
}

/** Height of the collision box while standing, sliding, or in between. */
export function playerHeight(p: Player): number {
  return p.sliding ? PLAYER_SLIDE_HEIGHT : PLAYER_HEIGHT
}

function startLaneChange(p: Player, delta: number) {
  const target = p.lane + delta
  if (target < 0 || target > LANES.length - 1) return
  p.lane = target
  p.laneFromX = p.x
  p.laneT = 0
}

/** Applies an intent now, or buffers it when the player is busy. */
export function applyIntent(p: Player, intent: Intent) {
  switch (intent) {
    case 'left':
    case 'right':
      startLaneChange(p, intent === 'left' ? -1 : 1)
      return
    case 'jump': {
      if (p.airborne) {
        p.buffered = 'jump'
        p.bufferT = INPUT_BUFFER
        return
      }
      p.sliding = false
      p.slideT = 0
      p.airborne = true
      p.jumpT = 0
      return
    }
    case 'slide': {
      if (p.airborne) {
        // A slide press in the air cuts the jump short and lands into the slide.
        p.buffered = 'slide'
        p.bufferT = INPUT_BUFFER
        p.jumpT = Math.max(p.jumpT, JUMP_TIME * 0.62)
        return
      }
      p.sliding = true
      p.slideT = 0
      return
    }
  }
}

export function updatePlayer(p: Player, dt: number) {
  if (p.laneT < 1) {
    p.laneT = Math.min(1, p.laneT + dt / LANE_CHANGE_TIME)
    const e = easeOutCubic(p.laneT)
    p.x = p.laneFromX + (LANES[p.lane] - p.laneFromX) * e
  } else {
    p.x = LANES[p.lane]
  }

  const drift = LANES[p.lane] - p.x
  const wanted = Math.max(-MAX_TILT, Math.min(MAX_TILT, drift * 0.16))
  p.tilt += (wanted - p.tilt) * Math.min(1, dt * 12)

  if (p.airborne) {
    p.jumpT += dt
    if (p.jumpT >= JUMP_TIME) {
      p.airborne = false
      p.jumpT = 0
      p.y = 0
    } else {
      p.y = JUMP_HEIGHT * Math.sin((Math.PI * p.jumpT) / JUMP_TIME)
    }
  } else {
    p.y = 0
  }

  if (p.sliding) {
    p.slideT += dt
    if (p.slideT >= SLIDE_TIME) {
      p.sliding = false
      p.slideT = 0
    }
  }

  if (p.buffered) {
    p.bufferT -= dt
    const ready = !p.airborne
    if (ready) {
      const intent = p.buffered
      p.buffered = null
      p.bufferT = 0
      applyIntent(p, intent)
    } else if (p.bufferT <= 0) {
      p.buffered = null
    }
  }
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}
