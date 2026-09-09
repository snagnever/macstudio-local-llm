// Chase camera. A passive FreeCamera — no attachControl, the code drives the
// transform every frame. One scratch Vector3, zero allocations per frame.

import { FreeCamera, Scene, Vector3 } from "@babylonjs/core";
import { CFG } from "./config";

const BASE_FOV = 0.85;

export class CameraRig {
  private cam: FreeCamera;
  private target = new Vector3(0, 1.2, 6);
  private shake = 0;

  constructor(scene: Scene) {
    this.cam = new FreeCamera("cam", new Vector3(0, 4.2, -8), scene);
    this.cam.minZ = 0.5;
    this.cam.maxZ = 1000;
    this.cam.fov = BASE_FOV;
    scene.activeCamera = this.cam;
  }

  addShake(amount: number): void {
    this.shake = Math.min(1.4, this.shake + amount);
  }

  reset(): void {
    this.shake = 0;
    this.cam.position.set(0, 4.2, -8);
    this.cam.rotation.set(0, 0, 0);
    this.cam.fov = BASE_FOV;
  }

  /**
   * @param px player x
   * @param laneVel player lateral velocity, used to bank the camera
   * @param boost true while the boost power-up is active
   * @param time total elapsed time, used by the shake noise
   */
  update(dt: number, px: number, laneVel: number, boost: boolean, time: number): void {
    const k = 1 - Math.exp(-6 * dt);

    this.cam.position.x += (px * 0.45 - this.cam.position.x) * k;
    this.cam.position.y = 4.2;

    this.target.set(px, 1.2, 6);
    this.cam.setTarget(this.target);

    // Shake: decays exponentially, adds a high-frequency wobble.
    if (this.shake > 0.001) {
      this.shake *= Math.exp(-3 * dt);
      this.cam.position.x += Math.sin(time * 67) * this.shake * 0.35;
      this.cam.position.y += Math.cos(time * 61) * this.shake * 0.3;
    } else {
      this.shake = 0;
    }

    // Bank into lane changes, and widen the fov on boost.
    this.cam.rotation.z += -laneVel * 0.012;
    const fovTarget = BASE_FOV + (boost ? 0.14 : 0);
    this.cam.fov += (fovTarget - this.cam.fov) * k;
  }
}
