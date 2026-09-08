import { resumeAudio } from '../game/audio';
import { useGame } from '../game/store';

export function TitleScreen() {
  const confirm = useGame((s) => s.confirm);
  const best = useGame((s) => s.best);
  return (
    <div className="overlay">
      <h1 className="wordmark">
        HYPER<span>RUNNER</span>
      </h1>
      <p className="tagline">a neon endless run through the grid</p>
      <button
        className="cta"
        onClick={() => {
          resumeAudio();
          confirm();
        }}
      >
        PRESS START
      </button>
      {best > 0 && <p className="seed">BEST {best.toLocaleString('en-US')}</p>}
      <p className="keys">
        ◀ ▶ / A D lanes · ▲ / W / Space jump · ▼ / S slide · Esc pause · swipe on touch
      </p>
    </div>
  );
}
