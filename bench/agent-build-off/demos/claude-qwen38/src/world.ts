// Static scenery: the scrolling neon grid, the gradient sky, the striped sun,
// the side rails, fog, and the glow layer. Three small ShaderMaterials use
// inline GLSL source (no ShadersStore, no external .fx files).

import {
  Color3,
  GlowLayer,
  Mesh,
  MeshBuilder,
  Scene,
  ShaderMaterial,
  StandardMaterial,
} from "@babylonjs/core";
import { CFG } from "./config";

const GRID_VS = `
precision highp float;
attribute vec3 position;
uniform mat4 world;
uniform mat4 worldViewProjection;
varying vec3 vWorld;
void main(void) {
  vWorld = (world * vec4(position, 1.0)).xyz;
  gl_Position = worldViewProjection * vec4(position, 1.0);
}
`;

const GRID_FS = `
precision highp float;
varying vec3 vWorld;
uniform float uPhase;

// One grid line: 1.0 on the line center, 0 between lines.
// hw grows with distance as an analytic stand-in for fwidth, so the
// shader compiles the same on WebGL 1 and 2.
float gridLine(float coord, float period, float hw) {
  float f = fract(coord / period);
  float d = min(f, 1.0 - f) * period;
  return 1.0 - smoothstep(hw, hw * 3.0, d);
}

void main(void) {
  float z = vWorld.z + uPhase; // the world flows toward -Z
  float dist = max(vWorld.z + 8.0, 0.0);
  float hw = 0.02 + dist * 0.0006;

  float minorZ = gridLine(z, 2.6, hw);
  float majorZ = gridLine(z, 13.0, hw * 1.5);
  float laneX = gridLine(vWorld.x - 1.3, 2.6, hw);
  float majorX = gridLine(vWorld.x, 13.0, hw * 1.5);

  vec3 magenta = vec3(0.85, 0.12, 0.75);
  vec3 cyan = vec3(0.1, 0.8, 1.0);
  vec3 col = vec3(0.015, 0.004, 0.03);
  col = mix(col, magenta, max(minorZ, laneX * 0.9) * 0.7);
  col = mix(col, cyan, max(majorZ, majorX));

  // Manual distance fog. Scene fog does not apply to custom shaders.
  float fade = exp(-dist * 0.011);
  col = mix(vec3(0.12, 0.01, 0.16), col, fade);
  gl_FragColor = vec4(col, 1.0);
}
`;

const SKY_VS = `
precision highp float;
attribute vec3 position;
attribute vec2 uv;
uniform mat4 worldViewProjection;
varying vec2 vUv;
void main(void) {
  vUv = uv;
  gl_Position = worldViewProjection * vec4(position, 1.0);
}
`;

const SKY_FS = `
precision highp float;
varying vec2 vUv;
void main(void) {
  float y = clamp((vUv.y - 0.42) / 0.33, 0.0, 1.0);
  vec3 horizon = vec3(0.45, 0.05, 0.35);
  vec3 mid = vec3(0.10, 0.01, 0.18);
  vec3 top = vec3(0.015, 0.0, 0.04);
  vec3 c = mix(horizon, mid, smoothstep(0.0, 0.45, y));
  c = mix(c, top, smoothstep(0.45, 1.0, y));
  gl_FragColor = vec4(c, 1.0);
}
`;

const SUN_VS = SKY_VS;

const SUN_FS = `
precision highp float;
varying vec2 vUv;
uniform float uTime;
void main(void) {
  vec2 p = (vUv - vec2(0.5, 0.5)) * 2.0;
  float r = length(p);
  if (r > 1.0) discard;
  vec3 col = mix(vec3(1.0, 0.15, 0.45), vec3(1.0, 0.85, 0.2), vUv.y);
  // Horizontal slit stripes, denser near the bottom, drifting down.
  float band = smoothstep(0.35, 0.65, fract(vUv.y * 16.0 - uTime * 0.4));
  float stripe = mix(band, 1.0, smoothstep(0.42, 0.62, vUv.y));
  float edge = 1.0 - smoothstep(0.94, 1.0, r);
  col = mix(vec3(0.03, 0.0, 0.06), col * stripe, edge);
  gl_FragColor = vec4(col, 1.0);
}
`;

export class World {
  private gridMat: ShaderMaterial;
  private sunMat: ShaderMaterial;
  private glow: GlowLayer;
  private phase = 0;

  constructor(private scene: Scene) {
    scene.clearColor.set(0.02, 0.0, 0.05, 1);
    scene.fogMode = Scene.FOGMODE_LINEAR;
    scene.fogColor = new Color3(CFG.fogR, CFG.fogG, CFG.fogB);
    scene.fogStart = CFG.fogStart;
    scene.fogEnd = CFG.fogEnd;
    scene.skipPointerMovePicking = true;

    // Grid floor. It sits at y = 0 and extends past the fog end.
    const ground = MeshBuilder.CreateGround(
      "ground",
      { width: 26, height: 420 },
      scene,
    );
    ground.position.z = 190;
    this.gridMat = new ShaderMaterial(
      "gridMat",
      scene,
      {
        vertexSource: GRID_VS,
        fragmentSource: GRID_FS,
      },
      {
        attributes: ["position"],
        uniforms: ["world", "worldViewProjection", "uPhase"],
      },
    );
    ground.material = this.gridMat;
    ground.freezeWorldMatrix();

    // Sky dome: a big sphere seen from the inside.
    const sky = MeshBuilder.CreateSphere("sky", { diameter: 900, segments: 12, sideOrientation: Mesh.BACKSIDE }, scene);
    sky.infiniteDistance = true;
    sky.applyFog = false;
    const skyMat = new ShaderMaterial(
      "skyMat",
      scene,
      {
        vertexSource: SKY_VS,
        fragmentSource: SKY_FS,
      },
      {
        attributes: ["position", "uv"],
        uniforms: ["worldViewProjection"],
      },
    );
    sky.material = skyMat;

    // Striped sun on the horizon.
    const sun = MeshBuilder.CreatePlane("sun", { size: 60 }, scene);
    sun.position.set(0, 10, 280);
    sun.billboardMode = Mesh.BILLBOARDMODE_ALL;
    sun.applyFog = false;
    this.sunMat = new ShaderMaterial(
      "sunMat",
      scene,
      {
        vertexSource: SUN_VS,
        fragmentSource: SUN_FS,
      },
      {
        attributes: ["position", "uv"],
        uniforms: ["worldViewProjection", "uTime"],
      },
    );
    sun.material = this.sunMat;

    // Side rails. They pick up the glow layer and read as light lines.
    const railMat = new StandardMaterial("railMat", scene);
    railMat.disableLighting = true;
    railMat.emissiveColor = new Color3(1.0, 0.15, 0.8);
    railMat.diffuseColor = new Color3(0, 0, 0);
    railMat.specularColor = new Color3(0, 0, 0);
    railMat.freeze();
    for (const side of [-1, 1]) {
      const rail = MeshBuilder.CreateBox("rail", { width: 0.12, height: 0.12, depth: 420 }, scene);
      rail.position.set(side * 3.6, 0.06, 190);
      rail.material = railMat;
      rail.freezeWorldMatrix();
    }

    this.glow = new GlowLayer("glow", scene, { mainTextureRatio: 0.5 });
    this.glow.intensity = CFG.glowIntensity;
  }

  update(dt: number, speed: number, time: number): void {
    this.phase += speed * dt;
    this.gridMat.setFloat("uPhase", this.phase);
    this.sunMat.setFloat("uTime", time);
  }

  /** Cheap fallback when the frame rate drops. */
  degradeGlow(): void {
    this.glow.intensity = 0.2;
  }
}
