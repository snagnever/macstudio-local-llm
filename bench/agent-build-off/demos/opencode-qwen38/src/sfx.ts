let ctx: AudioContext | null = null
let muted = false

export const setMuted = (m: boolean) => {
  muted = m
}

export const unlockAudio = () => {
  ctx ??= new AudioContext()
  void ctx.resume()
}

function tone(
  freqStart: number,
  freqEnd: number,
  duration: number,
  type: OscillatorType = 'square',
  gain = 0.12,
) {
  if (muted || !ctx || ctx.state !== 'running') return
  const t0 = ctx.currentTime
  const osc = ctx.createOscillator()
  const g = ctx.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freqStart, t0)
  osc.frequency.exponentialRampToValueAtTime(Math.max(freqEnd, 1), t0 + duration)
  g.gain.setValueAtTime(gain, t0)
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + duration)
  osc.connect(g).connect(ctx.destination)
  osc.start(t0)
  osc.stop(t0 + duration)
}

export const sfx = {
  coin: () => {
    tone(880, 880, 0.06, 'square', 0.09)
    setTimeout(() => tone(1318, 1318, 0.09, 'square', 0.09), 60)
  },
  jump: () => tone(280, 720, 0.18, 'triangle', 0.14),
  slide: () => tone(520, 140, 0.22, 'sawtooth', 0.08),
  lane: () => tone(420, 480, 0.05, 'triangle', 0.05),
  crash: () => tone(220, 40, 0.5, 'sawtooth', 0.22),
}
