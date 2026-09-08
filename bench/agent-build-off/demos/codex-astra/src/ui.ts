import type { Command, Phase, Preferences } from './game/types';

export type UiAction = 'start' | 'pause' | 'resume' | 'restart' | 'home' | 'retry';

export interface UiSnapshot {
  phase: Phase;
  score: number;
  distance: number;
  speed: number;
  cells: number;
  bestScore: number;
  shieldRemaining: number;
  preferences: Preferences;
}

export function createUi(
  root: HTMLElement,
  onAction: (action: UiAction) => void,
  onCommand: (command: Command) => void,
  onPreferences: (preferences: Preferences) => void,
): {
  update(snapshot: UiSnapshot): void;
  setLoading(progress: number): void;
  showError(message: string): void;
  dispose(): void;
} {
  root.innerHTML = `
    <div class="interface" data-phase="loading">
      <header class="topbar">
        <div class="wordmark" aria-label="Hyper Runner">HYPER <span>RUNNER</span></div>
        <div class="preferences" aria-label="Game preferences">
          <button class="icon-button" data-preference="sound" type="button">Sound on</button>
          <button class="icon-button" data-preference="quality" type="button">Quality high</button>
          <button class="icon-button motion-button" data-preference="motion" type="button">Motion full</button>
        </div>
      </header>

      <section class="loading-screen" aria-labelledby="loading-title">
        <p id="loading-title">Preparing the track</p>
        <div class="load-track" aria-hidden="true"><span></span></div>
        <output class="load-value">0%</output>
      </section>

      <main class="ready-screen">
        <div class="hero-copy">
          <h1><span>HYPER</span><span>RUNNER</span></h1>
          <p class="hero-description">Run above the city. Clear the barriers and collect energy.</p>
          <button class="primary-button" data-action="start" type="button">Start run</button>
          <p class="best-line">Local best <strong data-value="ready-best">0</strong></p>
          <p class="key-guide"><kbd>A</kbd><kbd>D</kbd> move&nbsp;&nbsp; <kbd>W</kbd> jump&nbsp;&nbsp; <kbd>S</kbd> slide</p>
        </div>
      </main>

      <section class="hud" aria-label="Run status">
        <div class="hud-primary"><span>Score</span><strong data-value="score">0</strong></div>
        <div class="hud-metric"><span>Energy</span><strong data-value="cells">0</strong></div>
        <div class="hud-metric"><span>Speed</span><strong data-value="speed">0 km/h</strong></div>
        <div class="shield-status"><span>Shield</span><strong data-value="shield">Ready</strong></div>
        <button class="pause-button" data-action="pause" type="button">Pause</button>
      </section>

      <div class="run-footer">
        <p><kbd>←</kbd><kbd>→</kbd> move <kbd>↑</kbd> jump <kbd>↓</kbd> slide</p>
        <strong data-testid="distance" data-value="distance">0 m</strong>
      </div>

      <nav class="touch-controls" aria-label="Touch controls">
        <div><button data-command="left" type="button" aria-label="Move left">Left</button><button data-command="right" type="button" aria-label="Move right">Right</button></div>
        <div><button data-command="jump" type="button">Jump</button><button data-command="slide" type="button">Slide</button></div>
      </nav>

      <section class="menu-panel pause-panel" role="dialog" aria-modal="true" aria-labelledby="pause-title">
        <p class="panel-label">Run paused</p><h2 id="pause-title">Run paused.</h2>
        <button class="primary-button" data-action="resume" type="button">Resume</button>
        <button class="text-button" data-action="restart" type="button">Restart</button>
        <button class="text-button" data-action="home" type="button">Back to menu</button>
      </section>

      <section class="menu-panel result-panel" role="dialog" aria-modal="true" aria-labelledby="result-title">
        <p class="panel-label">Run complete</p><h2 id="result-title">Distance logged.</h2>
        <div class="result-grid"><span>Score <strong data-value="final-score">0</strong></span><span>Distance <strong data-value="final-distance">0 m</strong></span><span>Energy <strong data-value="final-cells">0</strong></span><span>Best <strong data-value="final-best">0</strong></span></div>
        <button class="primary-button" data-action="restart" type="button">Restart</button>
        <button class="text-button" data-action="home" type="button">Back to menu</button>
      </section>

      <section class="menu-panel error-panel" role="alertdialog" aria-modal="true" aria-labelledby="error-title">
        <p class="panel-label">Track unavailable</p><h2 id="error-title">The game could not start.</h2>
        <p data-value="error-message"></p><button class="primary-button" data-action="retry" type="button">Retry</button>
      </section>
      <p class="sr-status" aria-live="polite" aria-atomic="true"></p>
    </div>`;

  const shell = root.querySelector<HTMLElement>('.interface')!;
  const values = new Map<string, HTMLElement>();
  root.querySelectorAll<HTMLElement>('[data-value]').forEach((node) => values.set(node.dataset.value!, node));
  let snapshot: UiSnapshot | undefined;
  let previousPhase: Phase | undefined;

  const setText = (key: string, value: string) => {
    const node = values.get(key);
    if (node && node.textContent !== value) node.textContent = value;
  };

  const onClick = (event: Event) => {
    const button = (event.target as Element).closest<HTMLButtonElement>('button');
    if (!button) return;
    const action = button.dataset.action as UiAction | undefined;
    const command = button.dataset.command as Command | undefined;
    if (action) onAction(action);
    if (command) onCommand(command);
    if (!snapshot) return;
    const preference = button.dataset.preference;
    if (preference === 'sound') onPreferences({ ...snapshot.preferences, muted: !snapshot.preferences.muted });
    if (preference === 'quality') onPreferences({ ...snapshot.preferences, quality: snapshot.preferences.quality === 'high' ? 'low' : 'high' });
    if (preference === 'motion') onPreferences({ ...snapshot.preferences, reducedMotion: !snapshot.preferences.reducedMotion });
  };
  root.addEventListener('click', onClick);

  return {
    update(next) {
      snapshot = next;
      shell.dataset.phase = next.phase;
      setText('score', Math.floor(next.score).toLocaleString());
      setText('cells', String(next.cells));
      setText('speed', `${Math.round(next.speed * 3.6)} km/h`);
      setText('distance', `${Math.floor(next.distance)} m`);
      setText('shield', next.shieldRemaining > 0 ? `${next.shieldRemaining.toFixed(1)} s` : 'Inactive');
      setText('ready-best', next.bestScore.toLocaleString());
      setText('final-score', Math.floor(next.score).toLocaleString());
      setText('final-distance', `${Math.floor(next.distance)} m`);
      setText('final-cells', String(next.cells));
      setText('final-best', next.bestScore.toLocaleString());
      const sound = root.querySelector<HTMLButtonElement>('[data-preference="sound"]')!;
      const quality = root.querySelector<HTMLButtonElement>('[data-preference="quality"]')!;
      const motion = root.querySelector<HTMLButtonElement>('[data-preference="motion"]')!;
      sound.textContent = next.preferences.muted ? 'Sound off' : 'Sound on';
      sound.setAttribute('aria-pressed', String(next.preferences.muted));
      quality.textContent = `Quality ${next.preferences.quality}`;
      quality.setAttribute('aria-pressed', String(next.preferences.quality === 'low'));
      motion.textContent = next.preferences.reducedMotion ? 'Motion reduced' : 'Motion full';
      motion.setAttribute('aria-pressed', String(next.preferences.reducedMotion));
      root.classList.toggle('reduced-motion', next.preferences.reducedMotion);

      if (previousPhase !== next.phase) {
        root.querySelector<HTMLElement>('.sr-status')!.textContent = {
          loading: 'Loading game.', error: 'The game could not start.', ready: 'Ready to start.',
          running: 'Run started.', paused: 'Run paused.', gameover: 'Run complete.',
        }[next.phase];
        const selector = next.phase === 'ready' ? '[data-action="start"]' : next.phase === 'paused' ? '[data-action="resume"]' : next.phase === 'gameover' ? '.result-panel [data-action="restart"]' : next.phase === 'error' ? '[data-action="retry"]' : '';
        if (selector) requestAnimationFrame(() => root.querySelector<HTMLButtonElement>(selector)?.focus());
        previousPhase = next.phase;
      }
    },
    setLoading(progress) {
      shell.dataset.phase = 'loading';
      const percent = Math.round(Math.max(0, Math.min(1, progress)) * 100);
      root.querySelector<HTMLElement>('.load-track span')!.style.width = `${percent}%`;
      root.querySelector<HTMLOutputElement>('.load-value')!.value = `${percent}%`;
    },
    showError(message) {
      shell.dataset.phase = 'error';
      setText('error-message', message);
      requestAnimationFrame(() => root.querySelector<HTMLButtonElement>('[data-action="retry"]')?.focus());
    },
    dispose() {
      root.removeEventListener('click', onClick);
      root.replaceChildren();
    },
  };
}
