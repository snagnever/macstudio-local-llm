import { useStore } from '../state/store'

type Props = {
  onStart: () => void
  onResume: () => void
  onQuit: () => void
  /** False for the first moment after a crash, so the wreck is not covered up. */
  deadReady: boolean
}

export function Overlays({ onStart, onResume, onQuit, deadReady }: Props) {
  const phase = useStore((s) => s.phase)
  const best = useStore((s) => s.best)
  const finalScore = useStore((s) => s.finalScore)
  const finalCoins = useStore((s) => s.finalCoins)

  if (phase === 'menu') {
    return (
      <div className="panel">
        <h1 className="title">
          HYPER<span>RUNNER</span>
        </h1>
        <p className="lede">Three lanes. One tunnel. No brakes.</p>
        <div className="keys">
          <span>&larr; &rarr; lane</span>
          <span>&uarr; / space jump</span>
          <span>&darr; slide</span>
          <span>esc pause</span>
        </div>
        <p className="hint">On a phone, swipe.</p>
        <button className="primary" onClick={onStart}>
          START RUN
        </button>
        {best > 0 && <p className="best">BEST {best}</p>}
      </div>
    )
  }

  if (phase === 'paused') {
    return (
      <div className="panel">
        <h2 className="title small">PAUSED</h2>
        <button className="primary" onClick={onResume}>
          RESUME
        </button>
        <button className="ghost wide" onClick={onQuit}>
          QUIT TO MENU
        </button>
      </div>
    )
  }

  if (phase === 'dead') {
    if (!deadReady) return null
    return (
      <div className="panel">
        <h2 className="title small">WRECKED</h2>
        <div className="result">
          <div>
            <b>{finalScore}</b>
            <span>SCORE</span>
          </div>
          <div>
            <b>{finalCoins}</b>
            <span>COINS</span>
          </div>
          <div>
            <b>{best}</b>
            <span>BEST</span>
          </div>
        </div>
        {finalScore >= best && finalScore > 0 && <p className="record">NEW RECORD</p>}
        <button className="primary" onClick={onStart}>
          RUN AGAIN
        </button>
        <button className="ghost wide" onClick={onQuit}>
          MENU
        </button>
      </div>
    )
  }

  return null
}
