import type { Intent } from './types';
import { SWIPE_MIN } from './constants';

const TAP_MAX = 16;

const KEY_MAP: Record<string, Intent> = {
  ArrowLeft: 'left',
  ArrowRight: 'right',
  ArrowUp: 'jump',
  ArrowDown: 'slide',
  a: 'left',
  d: 'right',
  w: 'jump',
  s: 'slide',
  ' ': 'jump',
  Escape: 'pause',
  p: 'pause',
  Enter: 'confirm',
};

export function attachInput(onIntent: (intent: Intent) => void): () => void {
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const intent = KEY_MAP[e.key];
    if (!intent) return;
    if (e.key === ' ' || e.key.startsWith('Arrow')) e.preventDefault();
    onIntent(intent);
  };

  let startX = 0;
  let startY = 0;

  const onTouchStart = (e: TouchEvent) => {
    const t = e.touches[0];
    if (!t) return;
    startX = t.clientX;
    startY = t.clientY;
  };

  const onTouchEnd = (e: TouchEvent) => {
    const t = e.changedTouches[0];
    if (!t) return;
    const dx = t.clientX - startX;
    const dy = t.clientY - startY;
    const adx = Math.abs(dx);
    const ady = Math.abs(dy);
    if (adx < TAP_MAX && ady < TAP_MAX) {
      onIntent('jump');
      return;
    }
    if (Math.max(adx, ady) < SWIPE_MIN) return;
    if (adx >= ady) onIntent(dx > 0 ? 'right' : 'left');
    else onIntent(dy > 0 ? 'slide' : 'jump');
  };

  window.addEventListener('keydown', onKeyDown);
  window.addEventListener('touchstart', onTouchStart, { passive: true });
  window.addEventListener('touchend', onTouchEnd, { passive: true });

  return () => {
    window.removeEventListener('keydown', onKeyDown);
    window.removeEventListener('touchstart', onTouchStart);
    window.removeEventListener('touchend', onTouchEnd);
  };
}
