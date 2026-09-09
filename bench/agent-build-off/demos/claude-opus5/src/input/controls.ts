import { pushIntent, world } from '../game/world'
import type { Intent } from '../game/player'

export type MetaAction = 'start' | 'pause' | 'mute'

const KEY_INTENT: Record<string, Intent> = {
  ArrowLeft: 'left',
  KeyA: 'left',
  ArrowRight: 'right',
  KeyD: 'right',
  ArrowUp: 'jump',
  KeyW: 'jump',
  Space: 'jump',
  ArrowDown: 'slide',
  KeyS: 'slide',
}

const SWIPE_THRESHOLD = 30

/** Keyboard and swipe both end up as one Intent, or one meta action. */
export function installControls(onMeta: (action: MetaAction) => void): () => void {
  function onKeyDown(event: KeyboardEvent) {
    if (event.repeat) return
    if (event.code === 'Escape' || event.code === 'KeyP') {
      event.preventDefault()
      onMeta('pause')
      return
    }
    if (event.code === 'KeyM') {
      onMeta('mute')
      return
    }
    const intent = KEY_INTENT[event.code]
    if (!intent) return
    event.preventDefault()
    if (world.phase === 'playing') pushIntent(intent)
    else if (event.code === 'Space') onMeta('start')
  }

  let startX = 0
  let startY = 0
  let tracking = false

  function onPointerDown(event: PointerEvent) {
    if (event.target instanceof HTMLElement && event.target.closest('button')) return
    tracking = true
    startX = event.clientX
    startY = event.clientY
  }

  function onPointerUp(event: PointerEvent) {
    if (!tracking) return
    tracking = false
    const dx = event.clientX - startX
    const dy = event.clientY - startY
    if (Math.abs(dx) < SWIPE_THRESHOLD && Math.abs(dy) < SWIPE_THRESHOLD) {
      if (world.phase !== 'playing') onMeta('start')
      return
    }
    if (world.phase !== 'playing') return
    if (Math.abs(dx) > Math.abs(dy)) pushIntent(dx > 0 ? 'right' : 'left')
    else pushIntent(dy > 0 ? 'slide' : 'jump')
  }

  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('pointerdown', onPointerDown)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', () => (tracking = false))

  return () => {
    window.removeEventListener('keydown', onKeyDown)
    window.removeEventListener('pointerdown', onPointerDown)
    window.removeEventListener('pointerup', onPointerUp)
  }
}
