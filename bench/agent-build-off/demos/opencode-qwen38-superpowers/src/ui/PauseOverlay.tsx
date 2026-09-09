import { useGame } from '../game/store';

export function PauseOverlay() {
  const resume = useGame((s) => s.resume);
  return (
    <div className="overlay">
      <h2 className="panel-title">PAUSED</h2>
      <button className="cta" onClick={resume}>
        RESUME
      </button>
    </div>
  );
}
