import { useGame } from './game/store';
import { Scene } from './three/Scene';
import { ErrorBoundary } from './ui/ErrorBoundary';
import { GameOverScreen } from './ui/GameOverScreen';
import { Hud } from './ui/Hud';
import { PauseOverlay } from './ui/PauseOverlay';
import { TitleScreen } from './ui/TitleScreen';

export default function App() {
  const phase = useGame((s) => s.phase);
  return (
    <div className="stage">
      <ErrorBoundary>
        <Scene />
        {phase === 'menu' && <TitleScreen />}
        {phase === 'running' && <Hud />}
        {phase === 'paused' && <PauseOverlay />}
        {phase === 'over' && <GameOverScreen />}
      </ErrorBoundary>
    </div>
  );
}
