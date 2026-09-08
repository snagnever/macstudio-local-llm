import { SceneInstrumentation } from '@babylonjs/core/Instrumentation/sceneInstrumentation';
import { createRun, applyCommand, stepRun } from './simulation';
import type { Command, GameEvent, Preferences, RunState, SavedData } from './types';
import { createScene, type SceneContext } from '../scene/createScene';
import { loadAssets, type GameAssets } from '../scene/assets';
import { RunnerView } from '../scene/RunnerView';
import { TrackView } from '../scene/TrackView';
import { Effects } from '../scene/Effects';
import { createUi, type UiAction } from '../ui';
import { bindInput } from '../input';
import { readSaved, writeSaved } from '../storage';
import { createAudio, type GameAudio } from '../audio';

export class Game {
  private state: RunState = createRun(this.seed());
  private saved: SavedData;
  private context?: SceneContext;
  private instrumentation?: SceneInstrumentation;
  private assets?: GameAssets;
  private runner?: RunnerView;
  private track?: TrackView;
  private effects?: Effects;
  private audio?: GameAudio;
  private ui;
  private input;
  private accumulator = 0;
  private hudElapsed = 0;
  private disposed = false;
  private initialized = false;
  private frameTimes: number[] = [];
  private lastTime = performance.now();
  private storage = {
    getItem(key: string) { return window.localStorage.getItem(key); },
    setItem(key: string, value: string) { window.localStorage.setItem(key, value); },
  };
  constructor(private canvas: HTMLCanvasElement, root: HTMLElement) {
    this.saved = readSaved(this.storage);
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) this.saved.preferences.reducedMotion = true;
    let hasSavedPreferences = false;
    try { hasSavedPreferences = this.storage.getItem('hyper-runner:v1') !== null; } catch { /* Storage is optional. */ }
    if (!hasSavedPreferences && window.matchMedia('(pointer: coarse)').matches) this.saved.preferences.quality = 'low';
    this.state.phase = 'loading';
    this.ui = createUi(root, action => this.action(action), command => this.command(command), preferences => this.preferences(preferences));
    this.input = bindInput(canvas, command => this.command(command), () => this.togglePause(), () => this.state.phase === 'running');
    canvas.tabIndex = 0;
    window.addEventListener('blur', this.onBlur);
    document.addEventListener('visibilitychange', this.onVisibility);
    canvas.addEventListener('webglcontextlost', this.onContextLost);
    this.renderUi();
    // Read-only diagnostics support performance inspection and browser verification.
    Object.defineProperty(window, '__hyperRunner', { configurable: true, get: () => ({
      phase: this.state.phase, distance: this.state.distance, score: this.state.score,
      runner: { ...this.state.runner }, objects: this.state.objects.map(item => ({ ...item })),
      fps: this.context?.engine.getFps() ?? 0,
      drawCalls: this.instrumentation?.drawCallsCounter.current ?? 0,
      gpu: this.context?.engine.getGlInfo().renderer,
      meshes: this.context?.scene.meshes.length ?? 0,
      activeMeshes: this.context?.scene.getActiveMeshes().length ?? 0,
      frameTimes: [...this.frameTimes],
      preferences: { ...this.saved.preferences }, audioReady: Boolean(this.audio), audio: this.audio?.status,
    }) });
  }
  private seed() { return crypto.getRandomValues(new Uint32Array(1))[0]; }
  async init() {
    try {
      this.context = createScene(this.canvas, this.saved.preferences.quality);
      this.instrumentation = new SceneInstrumentation(this.context.scene);
      this.context.engine.runRenderLoop(this.frame);
      void createAudio().then(audio => {
        if (this.disposed) { audio.dispose(); return; }
        this.audio = audio;
        audio.setMuted(this.saved.preferences.muted);
        audio.setPaused(this.state.phase !== 'running');
        if (this.state.phase === 'running') void audio.unlock().catch(() => {});
      }).catch(() => { /* Audio failure does not prevent a run. */ });

      const assets = await loadAssets(this.context.scene, progress => this.ui.setLoading(progress));
      if (this.disposed) { assets.dispose(); return; }
      this.assets = assets;
      this.runner = new RunnerView(this.context.scene, assets);
      for (const mesh of this.runner.meshes) this.context.shadow.addShadowCaster(mesh);
      this.track = new TrackView(this.context.scene, assets);
      this.track.setReducedMotion(this.saved.preferences.reducedMotion);
      this.effects = new Effects(this.context);
      this.effects.setPreferences(this.saved.preferences);
      this.initialized = true;
      this.state.phase = 'ready';
      this.track.sync(this.state);
      this.renderUi();
    } catch (error) {
      if (this.disposed) return;
      this.state.phase = 'error';
      this.renderUi();
      this.ui.showError(error instanceof Error ? error.message : 'The game could not load. Retry to reload the game.');
    }
  }
  private frame = () => {
    if (this.disposed || !this.context) return;
    const now = performance.now();
    const frameDt = Math.min((now - this.lastTime) / 1000, 0.1);
    this.lastTime = now;
    const previous = this.state.phase;
    if (this.state.phase === 'running') {
      this.frameTimes.push(frameDt * 1000);
      if (this.frameTimes.length > 7200) this.frameTimes.shift();
      this.accumulator = Math.min(this.accumulator + frameDt, 0.1);
      let steps = 0;
      while (this.accumulator >= 1 / 120 && steps < 12 && this.state.phase === 'running') {
        this.consumeEvents(stepRun(this.state, 1 / 120));
        this.accumulator -= 1 / 120;
        steps++;
      }
    } else this.accumulator = 0;
    if (previous === 'running' && this.state.phase === 'gameover') {
      this.saved.bestScore = Math.max(this.saved.bestScore, this.state.score);
      writeSaved(this.storage, this.saved);
      this.audio?.setPaused(true);
      this.input.clear();
    }
    if (this.initialized) {
      this.runner?.sync(this.state, frameDt, this.saved.preferences.reducedMotion);
      this.track?.sync(this.state);
      this.effects?.update(this.state, frameDt);
    }
    this.hudElapsed += frameDt;
    if (previous !== this.state.phase || this.hudElapsed >= 0.1) { this.renderUi(); this.hudElapsed = 0; }
    this.context.scene.render();
  };
  private consumeEvents(events: GameEvent[]) { this.audio?.consume(events); this.effects?.consume(events); }
  private command(command: Command) { applyCommand(this.state, command); }
  private renderUi() {
    this.ui.update({ phase: this.state.phase, score: this.state.score, distance: this.state.distance,
      speed: this.state.speed, cells: this.state.cells, bestScore: this.saved.bestScore,
      shieldRemaining: this.state.runner.shieldRemaining, preferences: this.saved.preferences });
  }
  private action(action: UiAction) {
    if (action === 'retry') { window.location.reload(); return; }
    if (!this.initialized) return;
    if (action === 'start' || action === 'restart') {
      this.track?.reset();
      this.state = createRun(this.seed());
      this.state.phase = 'running';
      this.accumulator = 0;
      this.frameTimes = [];
      this.input.clear();
      this.audio?.setPaused(false);
      void this.audio?.unlock().catch(() => {});
      this.canvas.focus({ preventScroll: true });
    }
    if (action === 'pause' && this.state.phase === 'running') this.pause();
    if (action === 'resume' && this.state.phase === 'paused') {
      this.state.phase = 'running';
      this.lastTime = performance.now();
      this.accumulator = 0;
      this.audio?.setPaused(false);
      this.canvas.focus({ preventScroll: true });
    }
    if (action === 'home') {
      this.track?.reset();
      this.state = createRun(this.seed());
      this.audio?.setPaused(true);
    }
    this.renderUi();
  }
  private preferences(preferences: Preferences) {
    this.saved.preferences = preferences;
    writeSaved(this.storage, this.saved);
    this.context?.setQuality(preferences.quality);
    this.effects?.setPreferences(preferences);
    this.track?.setReducedMotion(preferences.reducedMotion);
    this.audio?.setMuted(preferences.muted);
    if (!preferences.muted && this.state.phase === 'running') void this.audio?.unlock().catch(() => {});
    this.renderUi();
    if (this.state.phase === 'running') this.canvas.focus({ preventScroll: true });
  }
  private pause() {
    if (this.state.phase !== 'running') return;
    this.state.phase = 'paused';
    this.state.pendingEvents.length = 0;
    this.input.clear();
    this.accumulator = 0;
    this.audio?.setPaused(true);
    this.renderUi();
  }
  private togglePause() { if (this.state.phase === 'paused') this.action('resume'); else this.pause(); }
  private onBlur = () => this.pause();
  private onVisibility = () => { if (document.hidden) this.pause(); };
  private onContextLost = (event: Event) => {
    event.preventDefault();
    this.pause();
    this.state.phase = 'error';
    this.renderUi();
    this.ui.showError('The graphics connection stopped. Retry to reload the game.');
  };
  dispose() {
    this.disposed = true;
    window.removeEventListener('blur', this.onBlur);
    document.removeEventListener('visibilitychange', this.onVisibility);
    this.canvas.removeEventListener('webglcontextlost', this.onContextLost);
    this.input.dispose(); this.audio?.dispose(); this.ui.dispose();
    this.instrumentation?.dispose(); this.effects?.dispose(); this.runner?.dispose(); this.track?.dispose(); this.assets?.dispose(); this.context?.dispose();
    delete (window as unknown as Record<string, unknown>).__hyperRunner;
  }
}
