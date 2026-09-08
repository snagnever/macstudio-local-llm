import { LoadAssetContainerAsync } from '@babylonjs/core/Loading/sceneLoader';
import { AssetContainer } from '@babylonjs/core/assetContainer';
import type { Scene } from '@babylonjs/core/scene';
import '@babylonjs/loaders/glTF/2.0/glTFLoader';

export interface GameAssets {
  runner: AssetContainer;
  props: Map<string, AssetContainer>;
  dispose(): void;
}
export async function loadAssets(scene: Scene, onProgress: (ratio: number) => void): Promise<GameAssets> {
  onProgress(0.05);
  const runner = await LoadAssetContainerAsync(`${import.meta.env.BASE_URL}assets/models/runner.gltf`, scene, {
    onProgress(event) { if (event.lengthComputable) onProgress(0.05 + event.loaded / event.total * 0.9); },
  });
  if (!runner.meshes.length || !runner.animationGroups.some(group => group.name === 'Run')) {
    runner.dispose();
    throw new Error('The runner asset could not load. Retry to reload the game.');
  }
  onProgress(1);
  return { runner, props: new Map(), dispose() { runner.dispose(); } };
}
