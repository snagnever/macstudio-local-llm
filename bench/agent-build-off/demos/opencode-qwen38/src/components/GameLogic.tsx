import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { ACCEL, BASE_SPEED, MAX_SPEED, runtime, useStore } from '../store'

export function GameLogic() {
  const hudClock = useRef(0)

  useFrame((_, dt) => {
    const { status, coins, setHud } = useStore.getState()
    if (status !== 'running') return

    const d = Math.min(dt, 0.05)
    runtime.time += d
    runtime.distance += runtime.speed * d
    runtime.speed = Math.min(MAX_SPEED, BASE_SPEED + ACCEL * runtime.time)

    hudClock.current += d
    if (hudClock.current >= 0.1) {
      hudClock.current = 0
      setHud(Math.floor(runtime.distance) + coins * 10, runtime.speed)
    }
  })

  return null
}
