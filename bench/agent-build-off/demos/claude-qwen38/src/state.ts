// Shared enums for the whole game. No imports here.

export type GameStateName = "menu" | "playing" | "gameover";

export type PowerupKind = "shield" | "magnet" | "boost";

export const POWERUP_KINDS: readonly PowerupKind[] = ["shield", "magnet", "boost"];
