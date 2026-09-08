import type { GameEvent } from './types';

let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let musicGain: GainNode | null = null;
let muted = false;
let beatClock = 0;
let stepIndex = 0;

const SCALE = [0, 3, 5, 7, 10, 12, 15, 12, 10, 7, 5, 3];
const ROOT = 55;

export function initAudio(): void {
  if (ctx) return;
  try {
    ctx = new AudioContext();
    master = ctx.createGain();
    master.gain.value = muted ? 0 : 0.8;
    master.connect(ctx.destination);
    musicGain = ctx.createGain();
    musicGain.gain.value = 0.22;
    musicGain.connect(master);
  } catch {
    ctx = null;
  }
}

export function resumeAudio(): void {
  try {
    initAudio();
    void ctx?.resume();
  } catch {
    // ignore
  }
}

export function setAudioMuted(m: boolean): void {
  muted = m;
  try {
    if (master && ctx) master.gain.setTargetAtTime(m ? 0 : 0.8, ctx.currentTime, 0.02);
  } catch {
    // ignore
  }
}

function blip(
  freq: number,
  dur: number,
  type: OscillatorType,
  gain: number,
  destination: AudioNode,
): void {
  if (!ctx) return;
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type;
  o.frequency.value = freq;
  g.gain.setValueAtTime(gain, ctx.currentTime);
  g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
  o.connect(g).connect(destination);
  o.start();
  o.stop(ctx.currentTime + dur + 0.02);
}

export function playEvent(e: GameEvent): void {
  if (!ctx || !master || muted) return;
  try {
    switch (e) {
      case 'lane':
        blip(880, 0.06, 'square', 0.12, master);
        break;
      case 'jump':
        blip(440, 0.18, 'triangle', 0.2, master);
        break;
      case 'slide':
        blip(220, 0.22, 'sawtooth', 0.14, master);
        break;
      case 'land':
        blip(110, 0.08, 'sine', 0.25, master);
        break;
      case 'coin':
        blip(1318, 0.09, 'square', 0.16, master);
        blip(1760, 0.14, 'square', 0.14, master);
        break;
      case 'crash': {
        const len = Math.floor(ctx.sampleRate * 0.4);
        const buf = ctx.createBuffer(1, len, ctx.sampleRate);
        const data = buf.getChannelData(0);
        for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / len);
        const src = ctx.createBufferSource();
        src.buffer = buf;
        const f = ctx.createBiquadFilter();
        f.type = 'lowpass';
        f.frequency.value = 900;
        const g = ctx.createGain();
        g.gain.value = 0.9;
        src.connect(f).connect(g).connect(master);
        src.start();
        break;
      }
    }
  } catch {
    // never throw (SPEC §2.4)
  }
}

export function updateMusic(dt: number, speedFactor: number): void {
  if (!ctx || !musicGain || muted) return;
  try {
    const bpm = 120 + 30 * Math.min(1, Math.max(0, speedFactor));
    const stepDur = 60 / bpm / 2;
    beatClock += dt;
    while (beatClock >= stepDur) {
      beatClock -= stepDur;
      const deg = SCALE[stepIndex % SCALE.length];
      const f = ROOT * Math.pow(2, deg / 12);
      blip(f, stepDur * 1.8, 'triangle', 1, musicGain);
      if (stepIndex % 4 === 0) blip(60, 0.12, 'sine', 1.6, musicGain);
      stepIndex++;
    }
  } catch {
    // ignore
  }
}
