// Typed event bus. The collision module is the only producer; game.ts is the
// only consumer. HUD and audio read game state by polling instead.

import type { Entity } from "./factory";
import type { PowerupKind } from "./state";

export type GameEventMap = {
  coin: void;
  powerup: PowerupKind;
  launch: void;
  hit: Entity;
}

type Handler = (payload: unknown) => void;

export class EventBus<E extends Record<string, unknown>> {
  private handlers = new Map<keyof E, Set<Handler>>();

  on<K extends keyof E>(event: K, fn: (payload: E[K]) => void): () => void {
    let set = this.handlers.get(event);
    if (!set) {
      set = new Set();
      this.handlers.set(event, set);
    }
    set.add(fn as Handler);
    const target = set;
    return () => target.delete(fn as Handler);
  }

  emit<K extends keyof E>(event: K, payload: E[K]): void {
    const set = this.handlers.get(event);
    if (!set) return;
    for (const fn of set) (fn as (p: E[K]) => void)(payload);
  }
}
