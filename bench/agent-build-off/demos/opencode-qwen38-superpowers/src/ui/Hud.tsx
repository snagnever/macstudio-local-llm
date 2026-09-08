import { useGame } from '../game/store';

export function Hud() {
  const score = useGame((s) => s.score);
  const coins = useGame((s) => s.coins);
  const speed = useGame((s) => s.speed);
  const muted = useGame((s) => s.muted);
  const toggleMute = useGame((s) => s.toggleMute);
  return (
    <div className="hud">
      <div className="hud-score">{score.toLocaleString('en-US')}</div>
      <div className="hud-right">
        <span className="hud-coins">{coins} ◈</span>
        <span className="hud-speed">{speed.toFixed(0)} u/s</span>
        <button className="hud-mute" onClick={toggleMute}>
          {muted ? '🔇' : '🔊'}
        </button>
      </div>
    </div>
  );
}
