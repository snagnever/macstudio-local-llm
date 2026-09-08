import { Engine } from '@babylonjs/core/Engines/engine';
import { Scene } from '@babylonjs/core/scene';
import { FreeCamera } from '@babylonjs/core/Cameras/freeCamera';
import { Vector3 } from '@babylonjs/core/Maths/math.vector';
import { Color3, Color4 } from '@babylonjs/core/Maths/math.color';
import { HemisphericLight } from '@babylonjs/core/Lights/hemisphericLight';
import { DirectionalLight } from '@babylonjs/core/Lights/directionalLight';
import { ShadowGenerator } from '@babylonjs/core/Lights/Shadows/shadowGenerator';
import { GlowLayer } from '@babylonjs/core/Layers/glowLayer';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import { MeshBuilder } from '@babylonjs/core/Meshes/meshBuilder';
import '@babylonjs/core/Lights/Shadows/shadowGeneratorSceneComponent';
import type { Quality } from '../game/types';

export interface SceneContext {
  engine: Engine;
  scene: Scene;
  camera: FreeCamera;
  shadow: ShadowGenerator;
  glow: GlowLayer;
  setQuality(quality: Quality): void;
  dispose(): void;
}

export function material(scene: Scene, name: string, hex: string, emission = 0): StandardMaterial {
  const result = new StandardMaterial(name, scene);
  result.diffuseColor = Color3.FromHexString(hex);
  result.emissiveColor = result.diffuseColor.scale(emission);
  result.specularColor = new Color3(0.18, 0.22, 0.26);
  return result;
}

export function createScene(canvas: HTMLCanvasElement, quality: Quality): SceneContext {
  const engine = new Engine(canvas, true, { stencil: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  if (engine.webGLVersion < 2) { engine.dispose(); throw new Error('This game needs WebGL 2. Try a browser with hardware acceleration.'); }
  const scene = new Scene(engine);
  scene.clearColor = new Color4(0.075, 0.13, 0.19, 1);
  scene.fogMode = Scene.FOGMODE_EXP2;
  scene.fogDensity = 0.007;
  scene.fogColor = new Color3(0.14, 0.23, 0.29);
  scene.skipPointerMovePicking = true;
  scene.autoClear = true;
  const camera = new FreeCamera('chase', new Vector3(0, 4.5, -9), scene);
  camera.setTarget(new Vector3(0, 1.5, 18));
  camera.fov = 1.03;
  camera.minZ = 0.15;
  camera.maxZ = 500;
  const ambient = new HemisphericLight('sky-light', new Vector3(0, 1, 0), scene);
  ambient.intensity = 0.9;
  ambient.diffuse = new Color3(0.54, 0.79, 0.88);
  ambient.groundColor = new Color3(0.11, 0.15, 0.23);
  const sun = new DirectionalLight('sunlight', new Vector3(-0.6, -1, 0.35), scene);
  sun.position = new Vector3(20, 40, -20);
  sun.diffuse = new Color3(1, 0.78, 0.55);
  sun.intensity = 2.0;
  const shadow = new ShadowGenerator(1024, sun);
  shadow.useBlurExponentialShadowMap = true;
  shadow.blurKernel = 12;
  shadow.darkness = 0.22;
  shadow.bias = 0.001;
  const glow = new GlowLayer('neon-glow', scene, { mainTextureRatio: 0.35, blurKernelSize: 32 });
  glow.intensity = 0.55;
  const sunDisc = MeshBuilder.CreateDisc('distant-sun', { radius: 17, tessellation: 64, sideOrientation: 2 }, scene);
  sunDisc.position.set(25, 30, 260);
  const sunMaterial = material(scene, 'sun-disc', '#e8b184', 1);
  sunMaterial.disableLighting = true;
  sunDisc.material = sunMaterial;
  sunDisc.applyFog = false;
  const setQuality = (next: Quality) => {
    engine.setHardwareScalingLevel(1 / Math.min(window.devicePixelRatio || 1, next === 'high' ? 1.5 : 1));
    scene.shadowsEnabled = next === 'high';
    glow.intensity = next === 'high' ? 0.55 : 0.3;
    engine.resize();
  };
  setQuality(quality);
  const resize = () => setQuality(currentQuality);
  let currentQuality = quality;
  window.addEventListener('resize', resize);
  return { engine, scene, camera, shadow, glow,
    setQuality(next) { currentQuality = next; setQuality(next); },
    dispose() { window.removeEventListener('resize', resize); scene.dispose(); engine.dispose(); },
  };
}
