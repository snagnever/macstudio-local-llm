// Entity pools. Every mesh shape is created once (the "master"), hidden,
// and reused through InstancedMesh. Spawning takes an instance from a free
// list; releasing pushes it back. No mesh is created after boot.

import {
  Color3,
  InstancedMesh,
  Mesh,
  MeshBuilder,
  StandardMaterial,
  TransformNode,
  Vector3,
  type Scene,
} from "@babylonjs/core";
import { CFG } from "./config";
import type { PowerupKind } from "./state";

export type EntityKind = "low" | "high" | "coin" | "ramp" | PowerupKind;

export interface Entity {
  mesh: InstancedMesh;
  kind: EntityKind;
  active: boolean;
  x: number;
  y: number;
  z: number;
  /** Rest height for bobbing coins. */
  baseY: number;
  /** Collision slab, world Y. */
  yBase: number;
  yTop: number;
  halfW: number;
  halfD: number;
  /** Per-entity phase so bobs and spins are not synced. */
  phase: number;
}

function emissive(scene: Scene, name: string, r: number, g: number, b: number): StandardMaterial {
  const m = new StandardMaterial(name, scene);
  m.disableLighting = true;
  m.emissiveColor = new Color3(r, g, b);
  m.diffuseColor = new Color3(0, 0, 0);
  m.specularColor = new Color3(0, 0, 0);
  m.freeze();
  return m;
}

export class Factory {
  readonly actives: Entity[] = [];
  private free = new Map<EntityKind, Entity[]>();
  private t = 0;

  constructor(private scene: Scene) {
    for (const kind of ["low", "high", "coin", "ramp", "shield", "magnet", "boost"] as EntityKind[]) {
      this.free.set(kind, []);
    }
    this.buildPools();
  }

  private makeMaster(kind: EntityKind): Mesh {
    const scene = this.scene;
    let mesh: Mesh;
    switch (kind) {
      case "low": {
        mesh = MeshBuilder.CreateBox("low", { width: 2.2, height: 0.9, depth: 0.7 }, scene);
        mesh.position.y = 0.45;
        mesh.material = emissive(scene, "matLow", 1.0, 0.35, 0.05);
        break;
      }
      case "high": {
        mesh = MeshBuilder.CreateBox("high", { width: 2.2, height: 0.55, depth: 0.5 }, scene);
        mesh.position.y = 1.8;
        mesh.material = emissive(scene, "matHigh", 1.0, 0.1, 0.2);
        break;
      }
      case "coin": {
        mesh = MeshBuilder.CreateTorus("coin", { diameter: 0.85, thickness: 0.14, tessellation: 16 }, scene);
        mesh.material = emissive(scene, "matCoin", 1.0, 0.8, 0.15);
        mesh.rotation.x = Math.PI / 2; // ring stands vertical
        mesh.bakeCurrentTransformIntoVertices();
        break;
      }
      case "ramp": {
        mesh = MeshBuilder.CreateBox("ramp", { width: 2.4, height: 0.35, depth: 3 }, scene);
        mesh.material = emissive(scene, "matRamp", 0.1, 0.9, 0.7);
        mesh.rotation.x = -CFG.rampAngle; // toe down at the -Z face
        mesh.bakeCurrentTransformIntoVertices();
        break;
      }
      default: {
        // Power-ups: a glowing gem (4-sided crystal).
        mesh = MeshBuilder.CreateCylinder(kind, { diameter: 0.8, height: 0.8, tessellation: 4 }, scene);
        const colors: Record<PowerupKind, [number, number, number]> = {
          shield: [0.2, 0.9, 1.0],
          magnet: [1.0, 0.3, 0.9],
          boost: [0.7, 0.3, 1.0],
        };
        const c = colors[kind as PowerupKind];
        mesh.material = emissive(scene, `mat_${kind}`, c[0], c[1], c[2]);
        mesh.rotation.set(Math.PI / 6, Math.PI / 4, Math.PI / 6);
        mesh.bakeCurrentTransformIntoVertices();
        break;
      }
    }
    mesh.isVisible = false; // instances render; the master does not
    mesh.isPickable = false;
    mesh.alwaysSelectAsActiveMesh = true;
    return mesh;
  }

  private buildPools(): void {
    const poolSize: Partial<Record<EntityKind, number>> = {
      low: CFG.poolLow,
      high: CFG.poolHigh,
      coin: CFG.poolCoin,
      ramp: CFG.poolRamp,
      shield: CFG.poolPowerup,
      magnet: CFG.poolPowerup,
      boost: CFG.poolPowerup,
    };
    for (const kind of this.free.keys()) {
      const master = this.makeMaster(kind);
      const list = this.free.get(kind)!;
      const n = poolSize[kind] ?? 8;
      for (let i = 0; i < n; i++) {
        const inst = master.createInstance(`${kind}#${i}`);
        inst.isPickable = false;
        inst.setEnabled(false);
        list.push({
          mesh: inst,
          kind,
          active: false,
          x: 0,
          y: 0,
          z: 0,
          baseY: 0,
          yBase: 0,
          yTop: 0,
          halfW: 0,
          halfD: 0,
          phase: 0,
        });
      }
    }
  }

  /** Take one entity from the pool. Returns null if the pool is empty. */
  spawn(kind: EntityKind, lane: number, z: number): Entity | null {
    const list = this.free.get(kind);
    const e = list?.pop();
    if (!e) return null;
    e.active = true;
    e.x = (lane - (CFG.laneCount - 1) / 2) * CFG.laneWidth;
    e.z = z;
    e.phase = this.t + lane * 1.7;
    switch (kind) {
      case "low":
        e.y = 0.45; e.baseY = 0.45; e.yBase = 0; e.yTop = 0.9; e.halfW = 1.1; e.halfD = 0.35;
        break;
      case "high":
        e.y = 1.8; e.baseY = 1.8; e.yBase = 1.52; e.yTop = 2.08; e.halfW = 1.1; e.halfD = 0.25;
        break;
      case "coin":
        e.y = CFG.coinY; e.baseY = CFG.coinY; e.yBase = CFG.coinY - 0.4; e.yTop = CFG.coinY + 0.4;
        e.halfW = CFG.coinRadius; e.halfD = CFG.coinRadius;
        break;
      case "ramp":
        e.y = 0.55; e.baseY = 0.55; e.yBase = 0; e.yTop = 1.0; e.halfW = 1.2; e.halfD = 1.4;
        break;
      default:
        e.y = 1.15; e.baseY = 1.15; e.yBase = 0.6; e.yTop = 1.7;
        e.halfW = CFG.powerRadius; e.halfD = CFG.powerRadius;
        break;
    }
    e.mesh.setEnabled(true);
    this.actives.push(e);
    return e;
  }

  /** Override the rest Y (used for coin arcs). Call right after spawn. */
  setBaseY(e: Entity, y: number): void {
    e.baseY = y;
    e.yBase = y - 0.4;
    e.yTop = y + 0.4;
  }

  release(e: Entity): void {
    if (!e.active) return;
    e.active = false;
    e.mesh.setEnabled(false);
    this.free.get(e.kind)!.push(e);
  }

  /** Swap-remove from actives and release. Order is not preserved. */
  releaseAt(i: number): void {
    const a = this.actives;
    const e = a[i]!;
    const last = a.length - 1;
    a[i] = a[last]!;
    a.pop();
    this.release(e);
  }

  releaseAll(): void {
    while (this.actives.length > 0) {
      this.releaseAt(this.actives.length - 1);
    }
  }

  /** Scroll all actives toward the player, animate, and despawn. */
  update(dt: number, speed: number, time: number, magnetActive: boolean, playerX: number): void {
    this.t += dt;
    const a = this.actives;
    for (let i = a.length - 1; i >= 0; i--) {
      const e = a[i]!;
      e.z -= speed * dt;
      if (e.z < CFG.despawnZ) {
        this.releaseAt(i);
        continue;
      }
      const m = e.mesh;
      switch (e.kind) {
        case "coin": {
          if (magnetActive) {
            // Magnet: pull nearby coins toward the player column.
            const dx = playerX - e.x;
            const dz = e.z;
            if (dx * dx + dz * dz < CFG.magnetRadius * CFG.magnetRadius) {
              const k = 1 - Math.exp(-CFG.magnetPull * dt);
              e.x += dx * k;
              e.baseY += (CFG.coinY - e.baseY) * k;
            }
          }
          e.y = e.baseY + Math.sin(time * 2 + e.phase) * 0.14;
          m.rotation.y = time * 2.4 + e.phase;
          break;
        }
        case "shield":
        case "magnet":
        case "boost": {
          e.y = e.baseY + Math.sin(time * 2.2 + e.phase) * 0.12;
          m.rotation.y = time * 1.6 + e.phase;
          break;
        }
        default:
          break;
      }
      // Obstacles and ramps do not bob; coins and gems carry their own y.
      m.position.x = e.x;
      m.position.y = e.y;
      m.position.z = e.z;
    }
  }

  /** The player ship. Built once; moved as a group each frame. */
  buildShip(): TransformNode {
    const scene = this.scene;
    const root = new TransformNode("ship", scene);
    const cyan = emissive(scene, "matShip", 0.2, 0.9, 1.0);
    const magenta = emissive(scene, "matShip2", 1.0, 0.2, 0.8);

    const hull = MeshBuilder.CreateBox("hull", { width: 0.8, height: 0.45, depth: 1.6 }, scene);
    hull.position.y = 0.35;
    hull.material = cyan;
    hull.parent = root;

    const glow = MeshBuilder.CreateBox("underglow", { width: 0.9, height: 0.06, depth: 1.4 }, scene);
    glow.position.y = 0.08;
    glow.material = magenta;
    glow.parent = root;

    const cockpit = MeshBuilder.CreateBox("cockpit", { width: 0.4, height: 0.28, depth: 0.8 }, scene);
    cockpit.position.set(0, 0.62, 0.1);
    cockpit.material = magenta;
    cockpit.parent = root;

    const fin = MeshBuilder.CreateBox("fin", { width: 0.06, height: 0.4, depth: 0.5 }, scene);
    fin.position.set(0, 0.75, -0.7);
    fin.material = magenta;
    fin.parent = root;

    for (const child of root.getChildMeshes()) child.isPickable = false;
    return root;
  }

  /** Transparent shield bubble for the shield power-up. Hidden by default. */
  buildShieldBubble(): Mesh {
    const scene = this.scene;
    const bubble = MeshBuilder.CreateSphere("bubble", { diameter: 2.4, segments: 12 }, scene);
    const m = new StandardMaterial("matBubble", scene);
    m.disableLighting = true;
    m.emissiveColor = new Color3(0.2, 0.9, 1.0);
    m.diffuseColor = new Color3(0, 0, 0);
    m.specularColor = new Color3(0, 0, 0);
    m.alpha = 0.22;
    m.freeze();
    bubble.material = m;
    bubble.isPickable = false;
    bubble.isVisible = false;
    return bubble;
  }
}
