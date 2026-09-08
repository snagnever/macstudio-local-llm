/** @vitest-environment jsdom */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGame } from './store';
import { resetWorld, world } from './runtime';

beforeEach(() => {
  localStorage.clear();
  useGame.setState({
    phase: 'menu',
    score: 0,
    coins: 0,
    speed: 18,
    best: 0,
    seedLabel: '',
    muted: false,
  });
  resetWorld(5);
});

describe('store phases', () => {
  it('confirm starts a run', () => {
    useGame.getState().confirm();
    expect(useGame.getState().phase).toBe('running');
    expect(world.phase).toBe('running');
  });
  it('pause then resume round-trips', () => {
    useGame.getState().confirm();
    useGame.getState().pause();
    expect(useGame.getState().phase).toBe('paused');
    expect(world.phase).toBe('paused');
    useGame.getState().resume();
    expect(useGame.getState().phase).toBe('running');
    expect(world.phase).toBe('running');
  });
  it('confirm from over starts a fresh run', () => {
    useGame.getState().confirm();
    world.phase = 'over';
    useGame.setState({ phase: 'over' });
    useGame.getState().confirm();
    expect(useGame.getState().phase).toBe('running');
    expect(world.distance).toBe(0);
  });
});

describe('intents queue', () => {
  it('drain returns queued intents once', () => {
    useGame.getState().queueIntent('left');
    useGame.getState().queueIntent('jump');
    expect(useGame.getState().drainIntents()).toEqual(['left', 'jump']);
    expect(useGame.getState().drainIntents()).toEqual([]);
  });
});

describe('best score persistence', () => {
  it('syncHud on over persists best to localStorage', () => {
    useGame.getState().confirm();
    world.distance = 500;
    world.coins = 4;
    world.score = 40 + 500;
    world.phase = 'over';
    useGame.getState().syncHud();
    expect(useGame.getState().phase).toBe('over');
    expect(useGame.getState().best).toBe(1040);
    expect(localStorage.getItem('hyper-runner.best')).toBe('1040');
  });
  it('a lower run does not overwrite best', () => {
    localStorage.setItem('hyper-runner.best', '9999');
    useGame.setState({ best: 9999 });
    useGame.getState().confirm();
    world.score = 100;
    world.phase = 'over';
    useGame.getState().syncHud();
    expect(useGame.getState().best).toBe(9999);
    expect(localStorage.getItem('hyper-runner.best')).toBe('9999');
  });
  it('garbage storage value yields best 0 without throwing', async () => {
    localStorage.setItem('hyper-runner.best', 'not-a-number');
    vi.resetModules();
    const fresh = await import('./store');
    expect(fresh.useGame.getState().best).toBe(0);
    vi.resetModules();
  });
});
