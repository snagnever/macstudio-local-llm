import { ParticleSystem } from '@babylonjs/core/Particles/particleSystem';
import { DynamicTexture } from '@babylonjs/core/Materials/Textures/dynamicTexture';
import { Vector3 } from '@babylonjs/core/Maths/math.vector';
import { Color4 } from '@babylonjs/core/Maths/math.color';
import type { SceneContext } from './createScene';
import type { GameEvent, Preferences, RunState } from '../game/types';

export class Effects {
  private particles: ParticleSystem;
  private preferences: Preferences = { muted: false, quality: 'high', reducedMotion: false };
  private shake = 0;
  private runnerX = 0;
  private target = new Vector3();
  constructor(private context: SceneContext) {
    const texture = new DynamicTexture('spark-texture', 32, context.scene, false);
    const canvas = texture.getContext();
    const gradient = canvas.createRadialGradient(16, 16, 0, 16, 16, 16);
    gradient.addColorStop(0, 'white'); gradient.addColorStop(0.35, '#fff9d9'); gradient.addColorStop(1, 'transparent');
    canvas.fillStyle = gradient; canvas.fillRect(0, 0, 32, 32); texture.update();
    this.particles = new ParticleSystem('pickup-sparks', 128, context.scene);
    this.particles.particleTexture = texture;
    this.particles.emitter = new Vector3(0, 1, 0);
    this.particles.color1 = new Color4(1, 0.81, 0.4, 1);
    this.particles.color2 = new Color4(0.4, 1, 0.9, 1);
    this.particles.colorDead = new Color4(0.2, 0.5, 0.5, 0);
    this.particles.minSize = 0.04; this.particles.maxSize = 0.12;
    this.particles.minLifeTime = 0.15; this.particles.maxLifeTime = 0.45;
    this.particles.minEmitPower = 1.5; this.particles.maxEmitPower = 4;
    this.particles.direction1 = new Vector3(-1, 1, -1);
    this.particles.direction2 = new Vector3(1, 3, 1);
    this.particles.gravity = new Vector3(0, -6, 0);
    this.particles.emitRate = 0;
    this.particles.start();
  }
  consume(events: GameEvent[]) {
    for (const event of events) {
      if (event.kind === 'cell' || event.kind === 'shield') {
        this.particles.emitter = new Vector3(this.runnerX, 0.95, 0);
        this.particles.manualEmitCount = this.preferences.quality === 'high' ? 20 : 8;
      }
      if (event.kind === 'impact' && !this.preferences.reducedMotion) this.shake = 0.3;
    }
  }
  update(state: RunState, frameDt: number) {
    this.runnerX = state.runner.x;
    const ready = state.phase === 'ready' || state.phase === 'loading';
    const mobile = window.innerWidth < 700;
    const targetPosition = ready && !mobile ? new Vector3(-4.8, 2.8, -5.5) : new Vector3(state.runner.x * 0.1, mobile ? 5.2 : 4.5, mobile ? -11 : -9);
    const camera = this.context.camera;
    Vector3.LerpToRef(camera.position, targetPosition, this.preferences.reducedMotion ? 1 : Math.min(1, frameDt * 3.5), camera.position);
    this.target.set(0, ready && !mobile ? 0.8 : 1.15, ready && !mobile ? 7 : 17);
    camera.setTarget(this.target);
    this.shake = Math.max(0, this.shake - frameDt);
    if (this.shake > 0 && !this.preferences.reducedMotion && state.phase !== 'paused') {
      camera.position.x += Math.sin(this.shake * 90) * this.shake * 0.2;
      camera.position.y += Math.cos(this.shake * 70) * this.shake * 0.12;
    }
    const phase = (Math.sin(state.distance / 400) + 1) / 2;
    this.context.glow.intensity = (this.preferences.quality === 'high' ? 0.46 : 0.25) + phase * 0.06;
  }
  setPreferences(preferences: Preferences) { this.preferences = preferences; if (preferences.reducedMotion) this.shake = 0; }
  dispose() { this.particles.dispose(); }
}
