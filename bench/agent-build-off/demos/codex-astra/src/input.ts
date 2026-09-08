import type { Command } from './game/types';

const SWIPE_DISTANCE = 32;
const SWIPE_TIME = 500;

function isInteractiveTarget(target: EventTarget | null): boolean {
  return target instanceof Element && Boolean(target.closest('button, a, input, select, textarea, [contenteditable="true"]'));
}

export function bindInput(
  canvas: HTMLCanvasElement,
  onCommand: (command: Command) => void,
  onPause: () => void,
  isActive: () => boolean = () => true,
): { clear(): void; dispose(): void } {
  let pointerId: number | null = null;
  let startX = 0;
  let startY = 0;
  let startTime = 0;
  let emitted = false;

  const clear = () => {
    pointerId = null;
    emitted = false;
  };

  const onKeyDown = (event: KeyboardEvent) => {
    const pauseKey = event.key === 'Escape' || event.key.toLowerCase() === 'p';
    if (pauseKey) {
      if (!event.repeat) onPause();
      if (isActive()) event.preventDefault();
      return;
    }

    if (!isActive() || event.repeat || isInteractiveTarget(event.target)) return;

    const command: Command | undefined = {
      ArrowLeft: 'left', a: 'left', A: 'left',
      ArrowRight: 'right', d: 'right', D: 'right',
      ArrowUp: 'jump', w: 'jump', W: 'jump', ' ': 'jump',
      ArrowDown: 'slide', s: 'slide', S: 'slide',
    }[event.key] as Command | undefined;

    if (!command) return;
    event.preventDefault();
    onCommand(command);
  };

  const onPointerDown = (event: PointerEvent) => {
    if (!isActive() || pointerId !== null) return;
    event.preventDefault();
    pointerId = event.pointerId;
    startX = event.clientX;
    startY = event.clientY;
    startTime = performance.now();
    emitted = false;
    canvas.setPointerCapture?.(event.pointerId);
  };

  const onPointerMove = (event: PointerEvent) => {
    if (!isActive() || emitted || event.pointerId !== pointerId) return;
    const dx = event.clientX - startX;
    const dy = event.clientY - startY;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < SWIPE_DISTANCE) return;
    if (performance.now() - startTime > SWIPE_TIME) {
      clear();
      return;
    }
    emitted = true;
    event.preventDefault();
    if (Math.abs(dx) > Math.abs(dy)) onCommand(dx < 0 ? 'left' : 'right');
    else onCommand(dy < 0 ? 'jump' : 'slide');
  };

  const onPointerEnd = (event: PointerEvent) => {
    if (event.pointerId === pointerId) clear();
  };

  window.addEventListener('keydown', onKeyDown);
  window.addEventListener('blur', clear);
  canvas.addEventListener('pointerdown', onPointerDown, { passive: false });
  canvas.addEventListener('pointermove', onPointerMove, { passive: false });
  canvas.addEventListener('pointerup', onPointerEnd);
  canvas.addEventListener('pointercancel', onPointerEnd);

  return {
    clear,
    dispose() {
      clear();
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('blur', clear);
      canvas.removeEventListener('pointerdown', onPointerDown);
      canvas.removeEventListener('pointermove', onPointerMove);
      canvas.removeEventListener('pointerup', onPointerEnd);
      canvas.removeEventListener('pointercancel', onPointerEnd);
    },
  };
}
