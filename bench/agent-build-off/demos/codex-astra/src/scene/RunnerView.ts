import { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import { MeshBuilder } from '@babylonjs/core/Meshes/meshBuilder';
import type { AnimationGroup } from '@babylonjs/core/Animations/animationGroup';
import type { Scene } from '@babylonjs/core/scene';
import type { Mesh } from '@babylonjs/core/Meshes/mesh';
import type { GameAssets } from './assets';
import type { RunState } from '../game/types';
import { material } from './createScene';

export class RunnerView {
  readonly root: TransformNode;
  readonly meshes;
  private current?: AnimationGroup;
  private paused = false;
  private shield: Mesh;
  private contact: Mesh;
  private groups: AnimationGroup[];
  constructor(scene: Scene, assets: GameAssets) {
    assets.runner.addAllToScene();
    this.root = new TransformNode('runner-pose', scene);
    for (const node of assets.runner.rootNodes) node.parent = this.root;
    this.root.scaling.setAll(1.18);
    this.root.rotation.y = 0;
    for (const mesh of assets.runner.meshes) if (mesh.name.startsWith('Sword')) mesh.setEnabled(false);
    this.meshes = assets.runner.meshes;
    this.groups = assets.runner.animationGroups;
    for (const group of this.groups) group.stop();
    this.shield = MeshBuilder.CreateSphere('shield-shell', { diameter: 2.1, segments: 16 }, scene);
    const shieldMaterial = material(scene, 'shield-material', '#65ffeb', 0.8);
    shieldMaterial.alpha = 0.12;
    shieldMaterial.wireframe = true;
    this.shield.material = shieldMaterial;
    this.shield.setEnabled(false);
    this.contact = MeshBuilder.CreateDisc('runner-contact', { radius: 0.65, tessellation: 24 }, scene);
    this.contact.rotation.x = Math.PI / 2;
    const contactMaterial = material(scene, 'contact-shadow', '#071019');
    contactMaterial.alpha = 0.4;
    contactMaterial.disableLighting = true;
    this.contact.material = contactMaterial;
  }
  sync(state: RunState, frameDt: number, reducedMotion = false) {
    const runner = state.runner;
    const running = state.phase === 'running' || state.phase === 'paused';
    const clip = state.phase === 'gameover' ? 'Death' : running ? 'Run' : 'Idle_Neutral';
    const group = this.groups.find(item => item.name === clip) ?? this.groups.find(item => item.name === 'Run');
    if (group && group !== this.current) {
      this.current?.stop();
      this.current = group;
      group.start(clip !== 'Death', running ? state.speed / 12 : 1);
    }
    if (this.current) {
      this.current.speedRatio = running ? state.speed / 12 : 1;
      if (state.phase === 'paused') { this.current.pause(); this.paused = true; }
      else if ((!this.current.isPlaying || this.paused) && state.phase !== 'gameover') { this.current.play(true); this.paused = false; }
    }
    this.root.position.set(runner.x, runner.y, 0);
    const slide = runner.slideRemaining > 0;
    const blend = Math.min(frameDt * 22, 1);
    this.root.scaling.y += ((slide ? 0.48 : 1.18) - this.root.scaling.y) * blend;
    this.root.rotation.z += ((runner.lane * 2.6 - runner.x) * 0.09 - this.root.rotation.z) * blend;
    this.root.rotation.x += ((slide ? -0.35 : 0) - this.root.rotation.x) * blend;
    this.shield.setEnabled(runner.shieldRemaining > 0 || runner.immunityRemaining > 0);
    this.shield.position.set(runner.x, runner.y + 0.9, 0);
    if (!reducedMotion) this.shield.rotation.y += frameDt;
    this.contact.position.set(runner.x, 0.008, 0);
    this.contact.visibility = 1 / (1 + runner.y);
    this.contact.scaling.y = 0.65;
  }
  dispose() { this.shield.dispose(); this.contact.dispose(); this.root.dispose(); }
}
