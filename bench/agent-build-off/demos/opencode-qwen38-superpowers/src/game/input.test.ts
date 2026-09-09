/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { attachInput } from './input';
import type { Intent } from './types';

let intents: Intent[];
let detach: () => void;

function key(k: string) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: k }));
}

function touchSwipe(dx: number, dy: number) {
  const start = new Event('touchstart') as Event & {
    touches: { clientX: number; clientY: number }[];
  };
  start.touches = [{ clientX: 100, clientY: 100 }];
  const end = new Event('touchend') as Event & {
    changedTouches: { clientX: number; clientY: number }[];
  };
  end.changedTouches = [{ clientX: 100 + dx, clientY: 100 + dy }];
  window.dispatchEvent(start);
  window.dispatchEvent(end);
}

beforeEach(() => {
  intents = [];
  detach = attachInput((i) => intents.push(i));
});

afterEach(() => detach());

describe('keyboard', () => {
  it('maps arrows and wasd to intents', () => {
    key('ArrowLeft');
    key('ArrowRight');
    key('ArrowUp');
    key('ArrowDown');
    key('a');
    key('d');
    key('w');
    key('s');
    expect(intents).toEqual(['left', 'right', 'jump', 'slide', 'left', 'right', 'jump', 'slide']);
  });

  it('maps space, escape/p and enter', () => {
    key(' ');
    key('Escape');
    key('p');
    key('Enter');
    expect(intents).toEqual(['jump', 'pause', 'pause', 'confirm']);
  });

  it('ignores unmapped keys and modifier combos', () => {
    key('q');
    key('F5');
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', metaKey: true }));
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'r', ctrlKey: true }));
    expect(intents).toEqual([]);
  });

  it('stop listening after detach', () => {
    detach();
    key('ArrowLeft');
    expect(intents).toEqual([]);
  });
});

describe('touch', () => {
  it('horizontal swipes map to lane changes', () => {
    touchSwipe(-60, 5);
    touchSwipe(80, -10);
    expect(intents).toEqual(['left', 'right']);
  });

  it('vertical swipes map to jump/slide', () => {
    touchSwipe(5, -70);
    touchSwipe(-5, 90);
    expect(intents).toEqual(['jump', 'slide']);
  });

  it('a tap jumps', () => {
    touchSwipe(4, -6);
    expect(intents).toEqual(['jump']);
  });

  it('swipes shorter than SWIPE_MIN (except taps) do nothing', () => {
    touchSwipe(-20, 0);
    touchSwipe(0, 25);
    expect(intents).toEqual([]);
  });
});
