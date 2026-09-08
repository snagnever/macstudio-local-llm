/**
 * Every sound is generated here. There are no audio files. The context is created on the
 * first user gesture, which is what browsers require.
 */

let ctx: AudioContext | null = null
let master: GainNode | null = null
let musicGain: GainNode | null = null
let musicTimer: number | null = null
let step = 0

const SCALE = [0, 3, 5, 7, 10, 12, 15, 10]
const ROOT = 110

export function ensureAudio() {
  if (ctx) {
    if (ctx.state === 'suspended') void ctx.resume()
    return ctx
  }
  ctx = new AudioContext()
  master = ctx.createGain()
  master.gain.value = 0.6
  master.connect(ctx.destination)
  musicGain = ctx.createGain()
  musicGain.gain.value = 0.18
  musicGain.connect(master)
  return ctx
}

export function setMuted(muted: boolean) {
  if (!master || !ctx) return
  master.gain.setTargetAtTime(muted ? 0 : 0.6, ctx.currentTime, 0.05)
}

function blip(freq: number, duration: number, type: OscillatorType, gain: number, sweepTo?: number) {
  if (!ctx || !master) return
  const now = ctx.currentTime
  const osc = ctx.createOscillator()
  const env = ctx.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, now)
  if (sweepTo !== undefined) osc.frequency.exponentialRampToValueAtTime(sweepTo, now + duration)
  env.gain.setValueAtTime(0.0001, now)
  env.gain.exponentialRampToValueAtTime(gain, now + 0.012)
  env.gain.exponentialRampToValueAtTime(0.0001, now + duration)
  osc.connect(env)
  env.connect(master)
  osc.start(now)
  osc.stop(now + duration + 0.02)
}

export function playJump() {
  blip(340, 0.22, 'triangle', 0.35, 880)
}

export function playSlide() {
  if (!ctx || !master) return
  const now = ctx.currentTime
  const noise = ctx.createBufferSource()
  const length = Math.floor(ctx.sampleRate * 0.3)
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate)
  const data = buffer.getChannelData(0)
  for (let i = 0; i < length; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / length)
  noise.buffer = buffer
  const filter = ctx.createBiquadFilter()
  filter.type = 'bandpass'
  filter.frequency.setValueAtTime(1800, now)
  filter.frequency.exponentialRampToValueAtTime(400, now + 0.3)
  const env = ctx.createGain()
  env.gain.value = 0.3
  noise.connect(filter)
  filter.connect(env)
  env.connect(master)
  noise.start(now)
}

export function playCoin() {
  blip(1180, 0.09, 'square', 0.16)
  window.setTimeout(() => blip(1760, 0.11, 'square', 0.13), 55)
}

export function playCrash() {
  if (!ctx || !master) return
  blip(180, 0.5, 'sawtooth', 0.4, 40)
  const now = ctx.currentTime
  const noise = ctx.createBufferSource()
  const length = Math.floor(ctx.sampleRate * 0.6)
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate)
  const data = buffer.getChannelData(0)
  for (let i = 0; i < length; i++) data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, 2)
  noise.buffer = buffer
  const env = ctx.createGain()
  env.gain.value = 0.45
  noise.connect(env)
  env.connect(master)
  noise.start(now)
}

/** A sparse arpeggio over a bass drone, scheduled on a timer. */
export function startMusic() {
  ensureAudio()
  if (musicTimer !== null || !ctx || !musicGain) return
  const bass = ctx.createOscillator()
  const bassGain = ctx.createGain()
  bass.type = 'sawtooth'
  bass.frequency.value = ROOT / 2
  const bassFilter = ctx.createBiquadFilter()
  bassFilter.type = 'lowpass'
  bassFilter.frequency.value = 220
  bassGain.gain.value = 0.25
  bass.connect(bassFilter)
  bassFilter.connect(bassGain)
  bassGain.connect(musicGain)
  bass.start()

  musicTimer = window.setInterval(() => {
    if (!ctx || !musicGain) return
    const semitone = SCALE[step % SCALE.length]
    const freq = ROOT * Math.pow(2, semitone / 12) * (step % 16 < 8 ? 2 : 4)
    const now = ctx.currentTime
    const osc = ctx.createOscillator()
    const env = ctx.createGain()
    osc.type = 'square'
    osc.frequency.value = freq
    env.gain.setValueAtTime(0.0001, now)
    env.gain.exponentialRampToValueAtTime(0.12, now + 0.02)
    env.gain.exponentialRampToValueAtTime(0.0001, now + 0.24)
    osc.connect(env)
    env.connect(musicGain)
    osc.start(now)
    osc.stop(now + 0.28)
    step += 1
  }, 220)
}
