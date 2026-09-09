import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import { stepWorld } from '../game/world'
import { useStore } from '../state/store'

const LOW_QUALITY_FPS = 45
const LOW_QUALITY_SECONDS = 2

/**
 * Advances the simulation once per frame, before anything reads it, and drops quality if
 * the frame rate stays low.
 */
export function GameLoop() {
  const slowFor = useRef(0)
  const setLowQuality = useStore((s) => s.setLowQuality)

  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.05)
    stepWorld(dt)

    if (delta > 0 && 1 / delta < LOW_QUALITY_FPS) slowFor.current += delta
    else slowFor.current = Math.max(0, slowFor.current - delta)
    if (slowFor.current > LOW_QUALITY_SECONDS && !useStore.getState().lowQuality) {
      setLowQuality(true)
    }
  })

  return null
}
