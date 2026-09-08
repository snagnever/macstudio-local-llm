import { Suspense, lazy, useEffect, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { ensureAudio, playCoin, playCrash, playJump, playSlide, setMuted, startMusic } from './audio/synth'
import { validateChunks, CHUNKS } from './game/chunks'
import { installControls, type MetaAction } from './input/controls'
import { pauseRun, resumeRun, startRun, stepWorld, toMenu, world } from './game/world'
import { CameraRig } from './scene/CameraRig'
import { Coins } from './scene/Coins'
import { Effects } from './scene/Effects'
import { GameLoop } from './scene/GameLoop'
import { Obstacles } from './scene/Obstacles'
import { PlayerModel } from './scene/PlayerModel'
import { SpeedLines } from './scene/SpeedLines'
import { Tunnel } from './scene/Tunnel'
import { useStore } from './state/store'
import { Hud } from './ui/Hud'
import { Overlays } from './ui/Overlays'

/** Rapier only loads once the first crash happens, keeping it out of the first paint. */
const Debris = lazy(() => import('./scene/Debris').then((m) => ({ default: m.Debris })))

if (import.meta.env.DEV) {
  const problems = validateChunks(CHUNKS)
  if (problems.length > 0) console.error('Chunk validation failed:\n' + problems.join('\n'))
  // Development hook: lets you drive the simulation from the console without the renderer.
  Object.assign(window, { hyper: { world, startRun, stepWorld } })
}

function beginRun() {
  // Warm the physics chunk during the run so the crash never waits on a download.
  void import('./scene/Debris')
  ensureAudio()
  startMusic()
  setMuted(useStore.getState().muted)
  startRun()
}

function handleMeta(action: MetaAction) {
  const phase = world.phase
  if (action === 'mute') {
    useStore.getState().toggleMute()
    return
  }
  if (action === 'pause') {
    if (phase === 'playing') pauseRun()
    else if (phase === 'paused') resumeRun()
    return
  }
  if (phase === 'paused') resumeRun()
  else if (phase !== 'playing') beginRun()
}

export function App() {
  const phase = useStore((s) => s.phase)
  const muted = useStore((s) => s.muted)
  const [deadReady, setDeadReady] = useState(false)

  useEffect(() => {
    world.onPhase = (next) => {
      const store = useStore.getState()
      store.setPhase(next)
      if (next === 'dead') store.finishRun(world.score, world.coins)
    }
    world.onEvent = (event) => {
      if (event === 'jump') playJump()
      else if (event === 'slide') playSlide()
      else if (event === 'coin') playCoin()
      else playCrash()
    }
    return () => {
      world.onPhase = null
      world.onEvent = null
    }
  }, [])

  useEffect(() => installControls(handleMeta), [])

  /** Hold the game over panel back so the crash and the debris are visible first. */
  useEffect(() => {
    if (phase !== 'dead') {
      setDeadReady(false)
      return
    }
    const timer = window.setTimeout(() => setDeadReady(true), 1800)
    return () => window.clearTimeout(timer)
  }, [phase])
  useEffect(() => setMuted(muted), [muted])

  return (
    <>
      <div className="stage">
        <Canvas
          dpr={[1, 2]}
          gl={{ antialias: false, powerPreference: 'high-performance' }}
          camera={{ fov: 70, near: 0.1, far: 420, position: [0, 3.3, 7.4] }}
        >
          <GameLoop />
          <color attach="background" args={['#05030c']} />
          <fogExp2 attach="fog" args={['#05030c', 0.0145]} />
          <ambientLight intensity={0.4} />
          <directionalLight position={[5, 12, 6]} intensity={1.1} color="#8fd4ff" />
          <pointLight position={[0, 4, -14]} intensity={40} distance={40} color="#7b2fff" />
          <Tunnel />
          <Obstacles />
          <Coins />
          <SpeedLines />
          <Suspense fallback={null}>
            <PlayerModel />
          </Suspense>
          {phase === 'dead' && (
            <Suspense fallback={null}>
              <Debris />
            </Suspense>
          )}
          <CameraRig />
          <Effects />
        </Canvas>
      </div>
      {phase === 'playing' && <Hud />}
      <div className="overlay">
        <Overlays onStart={beginRun} onResume={resumeRun} onQuit={toMenu} deadReady={deadReady} />
      </div>
    </>
  )
}
