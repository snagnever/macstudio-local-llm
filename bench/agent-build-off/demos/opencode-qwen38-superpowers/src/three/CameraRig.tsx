import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { FOV_BASE, FOV_FAST, SPEED_MAX, SPEED_START } from '../game/constants';
import { world } from '../game/runtime';

export function CameraRig() {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;

  useFrame((_, delta) => {
    const f = (world.speed - SPEED_START) / (SPEED_MAX - SPEED_START);
    const target = FOV_BASE + (FOV_FAST - FOV_BASE) * Math.min(1, Math.max(0, f));
    if (Math.abs(camera.fov - target) > 0.05) {
      camera.fov = target;
      camera.updateProjectionMatrix();
    }
    const px = world.player.x;
    const k = Math.min(1, 6 * delta);
    camera.position.x += (px * 0.35 - camera.position.x) * k;
    camera.position.y += (3.2 + world.player.y * 0.4 - camera.position.y) * k;
    camera.position.z = 7.5;
    camera.lookAt(px * 0.5, 1 + world.player.y * 0.3, -10);
  });

  return null;
}
