// Raw WebAudio sound: procedural SFX and a lookahead-scheduled synthwave
// music loop. No samples, no Babylon audio module. The AudioContext is
// created on the first user gesture (unlock).

import { CFG } from "./config";

function loadMuted(): boolean {
  try {
    return localStorage.getItem(CFG.mutedKey) === "1";
  } catch {
    return false;
  }
}

const midi2freq = (m: number): number => 440 * Math.pow(2, (m - 69) / 12);

// One bar of bass notes and one bar of lead notes per chord (Am, F, C, G).
const BASS_ROOTS = [45, 41, 48, 43];
const LEAD_CHORDS = [
  [57, 60, 64, 69],
  [53, 57, 60, 65],
  [48, 52, 55, 60],
  [55, 59, 62, 67],
];

export class Audio {
  muted = loadMuted();
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private noise: AudioBuffer | null = null;
  private timer = 0;
  private nextTime = 0;
  private step = 0;
  private bpm: number = CFG.musicBpmMin;

  /** Call from any user gesture. Safe to call repeatedly. */
  unlock(): void {
    if (!this.ctx) {
      const AC: typeof AudioContext =
        window.AudioContext ??
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AC) return;
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.master.gain.value = this.muted ? 0 : 0.9;
      const comp = this.ctx.createDynamicsCompressor();
      comp.threshold.value = -12;
      comp.ratio.value = 6;
      this.master.connect(comp);
      comp.connect(this.ctx.destination);
      // One reusable white-noise buffer for hats, slides, and crashes.
      const len = Math.floor(this.ctx.sampleRate * 0.5);
      this.noise = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
      const data = this.noise.getChannelData(0);
      for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    }
    if (this.ctx.state === "suspended") void this.ctx.resume();
  }

  setMuted(m: boolean): void {
    this.muted = m;
    if (this.master && this.ctx) {
      this.master.gain.setTargetAtTime(m ? 0 : 0.9, this.ctx.currentTime, 0.02);
    }
    try {
      localStorage.setItem(CFG.mutedKey, m ? "1" : "0");
    } catch {
      // ignore storage failures
    }
  }

  /** Difficulty 0..1 drives the tempo. */
  setDifficulty(d: number): void {
    this.bpm = CFG.musicBpmMin + (CFG.musicBpmMax - CFG.musicBpmMin) * d;
  }

  // ---- music scheduler ----------------------------------------------------

  startMusic(): void {
    if (!this.ctx || this.timer !== 0) return;
    this.step = 0;
    this.nextTime = this.ctx.currentTime + 0.06;
    this.timer = window.setInterval(() => this.schedule(), 25);
  }

  stopMusic(): void {
    if (this.timer !== 0) {
      clearInterval(this.timer);
      this.timer = 0;
    }
  }

  private schedule(): void {
    if (!this.ctx) return;
    const ahead = this.ctx.currentTime + 0.12;
    const stepDur = 60 / this.bpm / 4; // sixteenth notes
    while (this.nextTime < ahead) {
      this.playStep(this.step, this.nextTime);
      this.nextTime += stepDur;
      this.step = (this.step + 1) % 64;
    }
  }

  private playStep(s: number, t: number): void {
    const bar = Math.floor(s / 16) % 4;
    if (s % 8 === 0) this.kick(t);
    if (s % 16 === 4 || s % 16 === 12) this.snare(t);
    if (s % 2 === 1) this.hat(t);
    if (s % 4 !== 3) this.bass(midi2freq(BASS_ROOTS[bar]!), t);
    if (s % 2 === 1) {
      const chord = LEAD_CHORDS[bar]!;
      this.lead(midi2freq(chord[Math.floor(s / 2) % 4]!), t);
    }
  }

  // ---- voices -------------------------------------------------------------

  private env(t: number, peak: number, dur: number): GainNode | null {
    if (!this.ctx || !this.master) return null;
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(peak, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    g.connect(this.master);
    return g;
  }

  private osc(
    type: OscillatorType,
    f0: number,
    f1: number,
    t: number,
    dur: number,
    peak: number,
  ): void {
    if (!this.ctx) return;
    const g = this.env(t, peak, dur);
    if (!g) return;
    const o = this.ctx.createOscillator();
    o.type = type;
    o.frequency.setValueAtTime(f0, t);
    if (f1 !== f0) o.frequency.exponentialRampToValueAtTime(Math.max(f1, 1), t + dur);
    o.connect(g);
    o.start(t);
    o.stop(t + dur + 0.02);
  }

  private noiseBurst(t: number, dur: number, peak: number, filterHz: number): void {
    if (!this.ctx || !this.noise || !this.master) return;
    const src = this.ctx.createBufferSource();
    src.buffer = this.noise;
    const f = this.ctx.createBiquadFilter();
    f.type = "lowpass";
    f.frequency.value = filterHz;
    const g = this.env(t, peak, dur);
    if (!g) return;
    src.connect(f);
    f.connect(g);
    src.start(t);
    src.stop(t + dur + 0.02);
  }

  private kick(t: number): void {
    this.osc("sine", 150, 40, t, 0.22, 0.9);
  }
  private snare(t: number): void {
    this.noiseBurst(t, 0.14, 0.35, 4000);
  }
  private hat(t: number): void {
    this.noiseBurst(t, 0.04, 0.12, 9000);
  }
  private bass(f: number, t: number): void {
    if (!this.ctx) return;
    const g = this.env(t, 0.22, 0.12);
    if (!g) return;
    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 380;
    const o = this.ctx.createOscillator();
    o.type = "sawtooth";
    o.frequency.value = f;
    o.connect(filter);
    filter.connect(g);
    o.start(t);
    o.stop(t + 0.14);
  }
  private lead(f: number, t: number): void {
    this.osc("triangle", f, f, t, 0.16, 0.12);
  }

  // ---- SFX ----------------------------------------------------------------

  coin(combo: number): void {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.osc("square", 1200 + Math.min(combo, 16) * 45, 1600 + Math.min(combo, 16) * 45, t, 0.07, 0.2);
  }

  jump(): void {
    if (!this.ctx) return;
    this.osc("sine", 300, 700, this.ctx.currentTime, 0.15, 0.3);
  }

  land(): void {
    if (!this.ctx) return;
    this.osc("sine", 160, 60, this.ctx.currentTime, 0.12, 0.3);
  }

  slide(): void {
    if (!this.ctx) return;
    this.noiseBurst(this.ctx.currentTime, 0.25, 0.2, 2200);
  }

  pickup(): void {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.osc("triangle", 660, 660, t, 0.09, 0.3);
    this.osc("triangle", 990, 990, t + 0.08, 0.12, 0.3);
  }

  shieldBreak(): void {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.noiseBurst(t, 0.3, 0.4, 3000);
    this.osc("square", 200, 80, t, 0.25, 0.3);
  }

  crash(): void {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.noiseBurst(t, 0.5, 0.5, 1200);
    this.osc("sawtooth", 110, 40, t, 0.5, 0.4);
  }

  gameOver(): void {
    if (!this.ctx) return;
    this.osc("triangle", 440, 110, this.ctx.currentTime, 0.6, 0.3);
  }

  ui(): void {
    if (!this.ctx) return;
    this.osc("square", 520, 520, this.ctx.currentTime, 0.05, 0.15);
  }
}
