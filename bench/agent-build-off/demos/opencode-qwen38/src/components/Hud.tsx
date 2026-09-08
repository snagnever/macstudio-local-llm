import { useStore } from '../store'
import { unlockAudio } from '../sfx'

function ActionButton({ label, hint }: { label: string; hint: string }) {
  const start = useStore((s) => s.start)
  return (
    <button
      className="btn"
      onClick={() => {
        unlockAudio()
        start()
      }}
    >
      {label}
      <span className="btn-hint">{hint}</span>
    </button>
  )
}

export function Hud() {
  const status = useStore((s) => s.status)
  const score = useStore((s) => s.score)
  const best = useStore((s) => s.best)
  const coins = useStore((s) => s.coins)
  const speed = useStore((s) => s.speed)
  const muted = useStore((s) => s.muted)

  return (
    <div className="hud">
      {status !== 'ready' && (
        <div className="stats">
          <div className="stat">
            <span className="stat-label">score</span>
            <span className="stat-value score">{score}</span>
          </div>
          <div className="stat right">
            <span className="stat-label">coins</span>
            <span className="stat-value coins">{coins}</span>
          </div>
          <div className="stat right">
            <span className="stat-label">speed</span>
            <span className="stat-value">{speed.toFixed(1)}</span>
          </div>
          <div className="stat right">
            <span className="stat-label">best</span>
            <span className="stat-value best">{best}</span>
          </div>
        </div>
      )}

      {status === 'ready' && (
        <div className="screen">
          <h1 className="title">
            HYPER<span className="title-accent">RUNNER</span>
          </h1>
          <p className="tagline">dodge the grid · grab the coins · outrun the sun</p>
          <ActionButton label="START" hint="press enter" />
          <div className="controls">
            <div>
              <kbd>← →</kbd> / <kbd>A D</kbd> / swipe — change lane
            </div>
            <div>
              <kbd>↑</kbd> / <kbd>space</kbd> / swipe up — jump
            </div>
            <div>
              <kbd>↓</kbd> / <kbd>S</kbd> / swipe down — slide
            </div>
            <div>
              <kbd>M</kbd> — mute
            </div>
          </div>
        </div>
      )}

      {status === 'dead' && (
        <div className="screen">
          <h1 className="title dead">CRASHED</h1>
          <p className="final">
            score <strong>{score}</strong>
            {score > 0 && score >= best ? <em className="record"> · NEW BEST</em> : null}
          </p>
          <p className="tagline">
            {coins} coins · best {best}
          </p>
          <ActionButton label="RUN AGAIN" hint="press R or enter" />
        </div>
      )}

      <div className="mute">{muted ? '♪ off (M)' : '♪ on (M)'}</div>
    </div>
  )
}
