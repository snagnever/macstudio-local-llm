import { useEffect, type RefObject } from 'react'
import { useDrag } from '@use-gesture/react'
import { runtime, useStore } from '../store'
import { sfx, unlockAudio } from '../sfx'

// camera faces +z, so world +x appears on screen LEFT: screen dirs are negated into lane dirs
const moveLane = (screenDir: number) => {
  const { status } = useStore.getState()
  if (status !== 'running') return
  const next = Math.min(1, Math.max(-1, runtime.lane - screenDir))
  if (next !== runtime.lane) {
    runtime.lane = next
    sfx.lane()
  }
}

const jump = () => {
  const { status } = useStore.getState()
  if (status !== 'running') return
  runtime.jumpQueuedAt = runtime.time
}

const slide = () => {
  const { status } = useStore.getState()
  if (status !== 'running') return
  runtime.slideQueuedAt = runtime.time
}

const startOrRestart = () => {
  const { status, start } = useStore.getState()
  if (status === 'running') return
  unlockAudio()
  start()
}

const handleSwipe = (mx: number, my: number) => {
  if (Math.abs(mx) > Math.abs(my)) moveLane(mx > 0 ? 1 : -1)
  else if (my < 0) jump()
  else slide()
}

export function useKeyboard() {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase()
      if (['arrowleft', 'arrowright', 'arrowup', 'arrowdown', ' '].includes(key))
        e.preventDefault()
      switch (key) {
        case 'arrowleft':
        case 'a':
          moveLane(-1)
          break
        case 'arrowright':
        case 'd':
          moveLane(1)
          break
        case 'arrowup':
        case 'w':
        case ' ':
          jump()
          break
        case 'arrowdown':
        case 's':
          slide()
          break
        case 'enter':
        case 'r':
          startOrRestart()
          break
        case 'm':
          useStore.getState().toggleMute()
          break
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
}

const SWIPE_THRESHOLD = 40

export function useSwipes(target: RefObject<HTMLElement | null>) {
  useDrag(
    ({ movement: [mx, my], dragging }) => {
      if (dragging) return
      if (Math.abs(mx) < SWIPE_THRESHOLD && Math.abs(my) < SWIPE_THRESHOLD) return
      handleSwipe(mx, my)
    },
    { target, pointerEvents: 'auto', filterTaps: true },
  )
}
