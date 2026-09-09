import { CreateAudioEngineAsync } from '@babylonjs/core/AudioV2/webAudio/webAudioEngine';
import { CreateSoundAsync } from '@babylonjs/core/AudioV2/abstractAudio/audioEngineV2';
import type { StaticSound } from '@babylonjs/core/AudioV2/abstractAudio/staticSound';
import type { GameEvent } from './game/types';

export interface GameAudio {
  readonly status: { ready: boolean; unlocked: boolean; paused: boolean; loopState?: number };
  unlock(): Promise<void>;
  consume(events: GameEvent[]): void;
  setMuted(muted: boolean): void;
  setPaused(paused: boolean): void;
  dispose(): void;
}
export async function createAudio(): Promise<GameAudio> {
  const engine = await CreateAudioEngineAsync({ disableDefaultUI: true, resumeOnInteraction: false, resumeOnPause: false, volume: 0.5 });
  let sounds: { collect: StaticSound; jump: StaticSound; impact: StaticSound; ui: StaticSound; loop: StaticSound } | undefined;
  let paused = true;
  let unlocked = false;
  let started = false;
  let disposed = false;
  const playLoop = () => {
    if (!sounds || !unlocked || paused || disposed) return;
    if (started) sounds.loop.resume();
    else { sounds.loop.play(); started = true; }
  };
  const base = `${import.meta.env.BASE_URL}assets/audio/`;
  void Promise.all([
    CreateSoundAsync('collect', `${base}collect.ogg`, { volume: 0.3 }, engine),
    CreateSoundAsync('jump', `${base}jump.ogg`, { volume: 0.15 }, engine),
    CreateSoundAsync('impact', `${base}collision.ogg`, { volume: 0.35 }, engine),
    CreateSoundAsync('ui', `${base}interface.ogg`, { volume: 0.16 }, engine),
    CreateSoundAsync('ambient', `${base}ambient-loop.wav`, { loop: true, volume: 0.22 }, engine),
  ]).then(([collect, jump, impact, ui, loop]) => {
    if (disposed) { for (const sound of [collect, jump, impact, ui, loop]) sound.dispose(); return; }
    sounds = { collect, jump, impact, ui, loop };
    playLoop();
  }).catch(() => { /* Missing audio files do not prevent a run. */ });
  return {
    get status() { return { ready: Boolean(sounds), unlocked, paused, loopState: sounds?.loop.state }; },
    async unlock() {
      await engine.unlockAsync();
      if (disposed) return;
      unlocked = true;
      sounds?.ui.play();
      playLoop();
    },
    consume(events) {
      if (!unlocked || paused || !sounds) return;
      for (const event of events) {
        if (event.kind === 'cell' || event.kind === 'shield') sounds.collect.play();
        if (event.kind === 'jump' || event.kind === 'slide') sounds.jump.play();
        if (event.kind === 'impact') sounds.impact.play();
      }
    },
    setMuted(muted) { engine.volume = muted ? 0 : 0.5; },
    setPaused(next) {
      if (next === paused) return;
      paused = next;
      if (paused) { sounds?.loop.pause(); sounds?.jump.stop(); sounds?.collect.stop(); }
      else playLoop();
    },
    dispose() { disposed = true; engine.dispose(); },
  };
}
