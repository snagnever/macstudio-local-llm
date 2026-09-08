import { Suspense, useEffect, useRef } from 'react'
import { Canvas } from '@react-three/fiber'
import { Physics } from '@react-three/rapier'
import { Camera } from './components/Camera'
import { Effects } from './components/Effects'
import { GameLogic } from './components/GameLogic'
import { Hud } from './components/Hud'
import { Player, PHYSICS_GRAVITY } from './components/Player'
import { Pools } from './components/Pools'
import { GroundCollider, World } from './components/World'
import { useKeyboard, useSwipes } from './hooks/useControls'
import { setMuted } from './sfx'
import { runtime, useStore } from './store'

if (import.meta.env.DEV) {
  ;(window as unknown as Record<string, unknown>).__hr = runtime
  ;(window as unknown as Record<string, unknown>).__hrStore = useStore
}

function App() {
  const root = useRef<HTMLDivElement>(null)
  const running = useStore((s) => s.status === 'running')

  useKeyboard()
  useSwipes(root)

  useEffect(
    () =>
      useStore.subscribe((s) => {
        setMuted(s.muted)
      }),
    [],
  )

  return (
    <div className="game" ref={root}>
      <Canvas
        dpr={[1, 2]}
        camera={{ fov: 55, position: [0, 3.1, -7], near: 0.5, far: 400 }}
      >
        <Suspense fallback={null}>
          <World />
          <Physics gravity={PHYSICS_GRAVITY} paused={!running}>
            <GroundCollider />
            <Player />
            <Pools />
          </Physics>
          <Camera />
          <GameLogic />
          <Effects />
        </Suspense>
      </Canvas>
      <Hud />
    </div>
  )
}

export default App
