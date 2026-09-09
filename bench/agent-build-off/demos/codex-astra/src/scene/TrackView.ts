import { MeshBuilder } from '@babylonjs/core/Meshes/meshBuilder';
import { Mesh } from '@babylonjs/core/Meshes/mesh';
import { DynamicTexture } from '@babylonjs/core/Materials/Textures/dynamicTexture';
import { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import type { Scene } from '@babylonjs/core/scene';
import type { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import type { GameAssets } from './assets';
import type { ObjectKind, RunState } from '../game/types';
import { material } from './createScene';

export class TrackView {
  private prototypes = new Map<string, Mesh>();
  private segments: TransformNode[] = [];
  private buildings: { root: TransformNode; z: number }[] = [];
  private portals: TransformNode[] = [];
  private active = new Map<number, { kind: ObjectKind; root: TransformNode }>();
  private pools = new Map<ObjectKind, TransformNode[]>();
  private mats: Record<string, StandardMaterial>;
  private time = 0;
  private reducedMotion = false;
  constructor(private scene: Scene, _assets: GameAssets) {
    this.mats = {
      road: material(scene, 'road-metal', '#243642'),
      side: material(scene, 'edge-metal', '#152735'),
      steel: material(scene, 'structural-steel', '#334c5c'),
      tower: material(scene, 'tower-glass', '#193444'),
      towerAlt: material(scene, 'tower-concrete', '#284550'),
      cyan: material(scene, 'cyan-light', '#47d8d9', 0.9),
      amber: material(scene, 'amber-light', '#ffce74', 0.95),
      dim: material(scene, 'soft-window', '#438389', 0.38),
      red: material(scene, 'danger-light', '#ff6d58', 0.8),
      obstacle: material(scene, 'obstacle-body', '#824f48'),
      white: material(scene, 'white-marking', '#b2cdd0', 0.15),
    };
    for (let i = 0; i < 20; i++) {
      const root = new TransformNode(`track-section-${i}`, scene);
      this.box(root, 'road', 8.6, 0.38, 12, 0, -0.24, 0);
      this.box(root, 'side', 10.2, 0.5, 11.95, 0, -0.65, 0);
      for (const x of [-1.3, 1.3]) this.box(root, 'dim', 0.035, 0.008, 11.8, x, -0.045, 0);
      for (const x of [-4.38, 4.38]) {
        this.box(root, 'steel', 0.25, 0.35, 12, x, 0.03, 0);
        this.box(root, 'cyan', 0.06, 0.025, 11.4, x, 0.22, 0);
        this.box(root, 'steel', 0.12, 0.8, 0.22, x, 0.4, 0);
        this.box(root, 'steel', 0.08, 0.1, 12, x, 0.77, 0);
      }
      this.box(root, 'side', 8.6, 0.014, 0.13, 0, -0.04, 5.93);
      for (const x of [-2.6, 0, 2.6]) this.box(root, 'white', 0.06, 0.01, 0.7, x, -0.035, 4.6);
      this.segments.push(root);
    }
    let rand = 421;
    const random = () => { rand = (rand * 1664525 + 1013904223) >>> 0; return rand / 4294967296; };
    for (let i = 0; i < 48; i++) {
      const side = i % 2 ? 1 : -1;
      const root = new TransformNode(`city-building-${i}`, scene);
      const height = 9 + random() * 35;
      const width = 3 + random() * 5;
      const depth = 5 + random() * 7;
      root.position.x = side * (8 + random() * 22);
      const z = Math.floor(i / 2) * 11 - 12;
      this.box(root, i % 3 ? 'tower' : 'towerAlt', width, height, depth, 0, height / 2 - 6, 0);
      this.box(root, 'side', width + 0.25, 0.4, depth + 0.25, 0, height - 6, 0);
      this.box(root, 'side', width * 0.65, 1.6, depth * 0.7, 0, height - 5.2, 0);
      const front = -depth / 2 - 0.012;
      for (let strip = 0; strip < 3; strip++) {
        this.box(root, i % 7 === 0 ? 'amber' : 'dim', 0.08 + random() * 0.14, height * 0.72, 0.025,
          -width * 0.3 + strip * width * 0.3, height * 0.5 - 6, front);
      }
      for (let floor = 1; floor <= 5; floor++) {
        this.box(root, i % 9 === 0 ? 'amber' : 'dim', width * 0.75, 0.055, 0.04, 0, height * floor / 6 - 6, front - 0.015);
      }
      if (i % 5 === 0) {
        this.box(root, 'cyan', width * 0.92, 0.1, 0.05, 0, height * 0.7 - 6, front - 0.02);
        this.box(root, 'steel', 0.18, 4, 0.18, 0, height - 4, 0);
        this.box(root, 'red', 0.2, 0.2, 0.2, 0, height - 2, 0);
      }
      this.buildings.push({ root, z });
    }
    const signTexture = new DynamicTexture('skyway-sign', { width: 512, height: 128 }, scene, false);
    const signCtx = signTexture.getContext();
    signCtx.fillStyle = '#112936'; signCtx.fillRect(0, 0, 512, 128);
    signCtx.font = 'bold 38px sans-serif'; signCtx.fillStyle = '#abe5df';
    signCtx.fillText('SKYWAY', 28, 65);
    signCtx.font = '24px sans-serif'; signCtx.fillStyle = '#ffd081';
    signCtx.fillText('↑     ↑     ↑', 305, 66);
    signCtx.fillStyle = '#4bb5b8'; signCtx.fillRect(28, 90, 452, 3); signTexture.update();
    const signMaterial = material(scene, 'sign', '#ffffff', 0.6);
    signMaterial.diffuseTexture = signTexture; signMaterial.emissiveTexture = signTexture;
    for (let i = 0; i < 5; i++) {
      const root = new TransformNode(`overhead-frame-${i}`, scene);
      for (const side of [-1, 1]) {
        this.box(root, 'steel', 0.4, 6, 0.6, side * 5, 2.4, 0);
        this.box(root, 'cyan', 0.065, 3, 0.05, side * 4.77, 3.5, -0.35);
      }
      this.box(root, 'steel', 10.4, 0.45, 0.7, 0, 5.6, 0);
      this.box(root, 'cyan', 8.8, 0.035, 0.05, 0, 5.36, -0.37);
      this.box(root, 'side', 2.4, 0.65, 0.16, 0, 5.08, 0);
      const sign = MeshBuilder.CreatePlane('skyway-panel', { width: 2.4, height: 0.6 }, scene);
      sign.material = signMaterial; sign.parent = root; sign.position.set(0, 5.08, -0.1);
      this.portals.push(root);
    }
    const capacities: Record<ObjectKind, number> = { cell: 40, shield: 8, barrier: 8, gate: 8, blocker: 8 };
    for (const [kind, count] of Object.entries(capacities)) {
      const pool = Array.from({ length: count }, () => {
        const root = this.makeObject(kind as ObjectKind);
        root.setEnabled(false);
        return root;
      });
      this.pools.set(kind as ObjectKind, pool);
    }
  }
  private box(parent: TransformNode, mat: string, w: number, h: number, d: number, x = 0, y = 0, z = 0) {
    let source = this.prototypes.get(mat);
    if (!source) {
      source = MeshBuilder.CreateBox(`source-${mat}`, { size: 1 }, this.scene);
      source.material = this.mats[mat];
      source.isVisible = false;
      source.isPickable = false;
      this.prototypes.set(mat, source);
    }
    const mesh = source.createInstance(`${parent.name}-${mat}`);
    mesh.parent = parent;
    mesh.scaling.set(w, h, d);
    mesh.position.set(x, y, z);
    mesh.isPickable = false;
    mesh.receiveShadows = mat === 'road';
    return mesh;
  }
  private makeObject(kind: ObjectKind) {
    const root = new TransformNode(`pooled-${kind}`, this.scene);
    if (kind === 'cell' || kind === 'shield') {
      const mesh = MeshBuilder.CreatePolyhedron(kind, { type: kind === 'cell' ? 1 : 3, size: kind === 'cell' ? 0.3 : 0.52 }, this.scene);
      mesh.material = this.mats[kind === 'cell' ? 'amber' : 'cyan'];
      mesh.parent = root;
      mesh.position.y = 0.95;
      const ring = MeshBuilder.CreateTorus('pickup-ring', { diameter: kind === 'cell' ? 0.85 : 1.4, thickness: 0.035, tessellation: 16 }, this.scene);
      ring.material = mesh.material;
      ring.parent = root;
      ring.position.y = 0.95;
      ring.rotation.x = Math.PI / 2;
    } else if (kind === 'gate') {
      for (const x of [-0.96, 0.96]) this.box(root, 'steel', 0.15, 2.7, 0.45, x, 1.35);
      this.box(root, 'obstacle', 2.05, 1.6, 0.65, 0, 1.65);
      this.box(root, 'red', 2.08, 0.075, 0.07, 0, 0.89, -0.38);
      for (const x of [-0.6, 0, 0.6]) this.box(root, 'white', 0.13, 0.25, 0.02, x, 1.28, -0.34).rotation.z = Math.PI / 4;
    } else {
      const height = kind === 'barrier' ? 0.75 : 2.65;
      this.box(root, 'obstacle', 1.95, height, 0.9, 0, height / 2);
      this.box(root, 'side', 2.1, 0.12, 1.0, 0, 0.07);
      this.box(root, 'red', 1.97, 0.07, 0.04, 0, height - 0.06, -0.47);
      for (const x of [-0.64, 0, 0.64]) {
        const stripe = this.box(root, 'amber', 0.22, kind === 'barrier' ? 0.35 : 1.8, 0.025, x, height / 2, -0.465);
        stripe.rotation.z = -0.35;
      }
      if (kind === 'blocker') this.box(root, 'red', 0.06, height, 0.04, -0.9, height / 2, -0.48);
    }
    return root;
  }
  sync(state: RunState) {
    const distance = state.distance;
    this.time = this.reducedMotion ? 0 : state.elapsed;
    this.segments.forEach((root, i) => { root.position.z = i * 12 - (distance % 12) - 18; });
    this.buildings.forEach(({ root, z }) => { root.position.z = ((z - distance * 0.75 + 1040) % 264 + 264) % 264 - 24; });
    this.portals.forEach((root, i) => { root.position.z = i * 48 - (distance % 48) - 20; });
    const live = new Set<number>();
    for (const object of state.objects) {
      if (!object.active || object.z < -10 || object.z > 200) continue;
      live.add(object.id);
      let view = this.active.get(object.id);
      if (!view) {
        const root = this.pools.get(object.kind)?.pop() ?? this.makeObject(object.kind);
        root.setEnabled(true);
        view = { kind: object.kind, root };
        this.active.set(object.id, view);
      }
      view.root.position.set(object.lane * 2.6, 0, object.z);
      if (object.kind === 'cell' || object.kind === 'shield') {
        view.root.rotation.y = this.time * 2 + object.id;
        view.root.position.y = this.reducedMotion ? 0 : Math.sin(this.time * 3 + object.id) * 0.1;
      }
    }
    for (const [id, view] of this.active) {
      if (live.has(id)) continue;
      view.root.setEnabled(false);
      if (!this.pools.has(view.kind)) this.pools.set(view.kind, []);
      this.pools.get(view.kind)!.push(view.root);
      this.active.delete(id);
    }
  }
  setReducedMotion(value: boolean) { this.reducedMotion = value; }
  reset() {
    for (const view of this.active.values()) {
      view.root.setEnabled(false);
      if (!this.pools.has(view.kind)) this.pools.set(view.kind, []);
      this.pools.get(view.kind)!.push(view.root);
    }
    this.active.clear();
  }
  dispose() {
    for (const root of this.segments) root.dispose();
    for (const { root } of this.buildings) root.dispose();
    for (const root of this.portals) root.dispose();
    for (const { root } of this.active.values()) root.dispose();
    for (const pool of this.pools.values()) for (const root of pool) root.dispose();
    for (const source of this.prototypes.values()) source.dispose();
  }
}
