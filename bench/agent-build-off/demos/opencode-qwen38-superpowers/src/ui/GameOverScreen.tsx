import { resumeAudio } from '../game/audio';
import { useGame } from '../game/store';

export function GameOverScreen() {
  const { score, coins, best, seedLabel, confirm } = useGame();
  const isBest = score >= best && score > 0;
  return (
    <div className="overlay">
      <h2 className="panel-title crash-title">SIGNAL LOST</h2>
      <div className="stat-line">
        <span>SCORE {score.toLocaleString('en-US')}</span>
        <span>COINS {coins}</span>
        <span>BEST {best.toLocaleString('en-US')}</span>
      </div>
      {isBest && <p className="new-best">NEW BEST</p>}
      <button
        className="cta"
        onClick={() => {
          resumeAudio();
          confirm();
        }}
      >
        RUN AGAIN
      </button>
      {seedLabel && (
        <p className="seed">
          seed {seedLabel} · console: window.startHyperRun('{seedLabel}')
        </p>
      )}
    </div>
  );
}
