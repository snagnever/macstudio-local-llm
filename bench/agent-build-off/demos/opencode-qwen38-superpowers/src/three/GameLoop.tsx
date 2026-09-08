import { useFrame } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import { playEvent, resumeAudio, setAudioMuted, updateMusic } from '../game/audio';
import { HUD_SYNC_INTERVAL, MAX_DT, SPEED_MAX, SPEED_START } from '../game/constants';
import { attachInput } from '../game/input';
import { step, world } from '../game/runtime';
import { useGame } from '../game/store';

export function GameLoop() {
  const hudTimer = useRef(0);

  useEffect(() => {
    const detach = attachInput((i) => {
      const s = useGame.getState();
      if (i === 'pause') {
        if (s.phase === 'running') s.pause();
        else if (s.phase === 'paused') s.resume();
        return;
      }
      if (i === 'confirm') {
        resumeAudio();
        s.confirm();
        return;
      }
      if (s.phase === 'running') s.queueIntent(i);
    });
    return detach;
  }, []);

  useFrame((_, delta) => {
    setAudioMuted(useGame.getState().muted);
    if (world.phase === 'running') {
      const intents = useGame.getState().drainIntents();
      step(delta, intents);
      for (const e of world.events.splice(0)) playEvent(e);
      updateMusic(Math.min(delta, MAX_DT), (world.speed - SPEED_START) / (SPEED_MAX - SPEED_START));
    }
    hudTimer.current += delta;
    if (hudTimer.current >= HUD_SYNC_INTERVAL || world.phase !== useGame.getState().phase) {
      hudTimer.current = 0;
      useGame.getState().syncHud();
    }
  });

  return null;
}
