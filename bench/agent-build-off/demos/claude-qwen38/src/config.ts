// Every tuning number in the game lives here. SPEC.md tables mirror this
// object. Change a number here, never in a system.

export const CFG = {
  // Lanes and player body
  laneCount: 3,
  startLane: 1,
  laneWidth: 2.6, // lane x = (lane - 1) * laneWidth
  laneSwitchK: 16, // damping factor for the lane interpolation
  standHeight: 1.7,
  slideHeight: 0.8,
  playerHalfW: 0.4,
  playerHalfD: 0.8,

  // Kinematics
  gravity: 55,
  jumpVy: 13, // apex ~1.5 units, ~0.47 s up
  fastFallVy: -20,
  slideTime: 0.5,
  coyoteTime: 0.1,
  jumpBufferTime: 0.12,
  rampLaunchVy: 16, // from a ramp; ~1.1 s airtime

  // Speed and difficulty
  baseSpeed: 14,
  maxSpeed: 28,
  diffTau: 90, // seconds of the difficulty exponential
  diffCap: 0.95,
  boostExtra: 8, // added speed while boost is active
  boostScoreMult: 2,
  menuSpeed: 8, // idle world drift in the menu
  maxDt: 0.05, // frame delta clamp

  // World layout. The world moves toward -Z (toward the camera).
  segmentLen: 20,
  segments: 12,
  slotsPerSegment: 3,
  slotOffset: 3, // first slot at segment near edge + 3
  slotLen: 6, // distance between slot centers
  spawnZ: 250, // far edge of the track on a reset
  startZ: 30, // near edge of the first segment on a reset
  recycleZ: -20, // segment start point after this
  despawnZ: -14, // released entities behind this

  // Entity sizes (collision half-extents)
  rampAngle: 0.52,
  rampChance: 0.1,
  obstacleChance: 0.45, // at D = 0
  obstacleChanceMax: 0.85, // at D = 1
  powerupChance: 0.08,

  // Pickups
  coinY: 1.05,
  coinRadius: 0.65,
  powerRadius: 0.7,
  pickupDy: 1.15, // vertical reach of a pickup
  magnetRadius: 6,
  magnetPull: 6, // lerp rate toward the player
  comboWindow: 4, // seconds between coins to keep the combo
  comboMultPerCoin: 0.25,
  comboCap: 20,
  powerupDuration: 6,

  // Pool sizes
  poolLow: 80,
  poolHigh: 60,
  poolCoin: 240,
  poolPowerup: 4,
  poolRamp: 8,

  // Look
  fogR: 0.12,
  fogG: 0.01,
  fogB: 0.16,
  fogStart: 80,
  fogEnd: 240,
  glowIntensity: 0.6,

  // Audio
  musicBpmMin: 96,
  musicBpmMax: 144,

  // Storage keys
  bestKey: "hyperRunner.best",
  mutedKey: "hyperRunner.muted",
} as const;
