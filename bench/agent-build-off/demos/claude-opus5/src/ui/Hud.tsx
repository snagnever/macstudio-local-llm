import { useEffect, useRef } from 'react'
import { SPEED_MAX, SPEED_START } from '../game/config'
import { world } from '../game/world'
import { useStore } from '../state/store'

/** Written straight to the document on every frame, so the score never re-renders React. */
export function Hud() {
  const score = useRef<HTMLSpanElement>(null)
  const coins = useRef<HTMLSpanElement>(null)
  const speed = useRef<HTMLDivElement>(null)
  const muted = useStore((s) => s.muted)
  const toggleMute = useStore((s) => s.toggleMute)

  useEffect(() => {
    let frame = 0
    const tick = () => {
      if (score.current) score.current.textContent = String(Math.floor(world.score))
      if (coins.current) coins.current.textContent = String(world.coins)
      if (speed.current) {
        const ratio = (world.speed - SPEED_START) / (SPEED_MAX - SPEED_START)
        speed.current.style.width = `${Math.max(0, Math.min(1, ratio)) * 100}%`
      }
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <div className="hud">
      <div className="hud-left">
        <div className="hud-score">
          <span ref={score}>0</span>
        </div>
        <div className="hud-coins">
          <i className="coin-dot" />
          <span ref={coins}>0</span>
        </div>
        <div className="speed-track">
          <div className="speed-fill" ref={speed} />
        </div>
      </div>
      <button className="ghost" onClick={toggleMute} aria-label={muted ? 'Unmute' : 'Mute'}>
        {muted ? 'SOUND OFF' : 'SOUND ON'}
      </button>
    </div>
  )
}
