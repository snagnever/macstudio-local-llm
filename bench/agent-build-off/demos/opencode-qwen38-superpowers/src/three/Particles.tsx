import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import { BURST_LIFE, BURST_POOL, COLOR } from '../game/constants';
import { world } from '../game/runtime';

export function Particles() {
  const meshes = useRef<(THREE.Mesh | null)[]>([]);

  useFrame(() => {
    const bursts = world.bursts;
    for (let i = 0; i < BURST_POOL; i++) {
      const m = meshes.current[i];
      if (!m) continue;
      const b = bursts[i];
      if (!b) {
        m.visible = false;
        continue;
      }
      const age = b.t / BURST_LIFE;
      m.visible = age < 1;
      m.position.set(b.x, b.y, b.z);
      const s = 0.2 + age * 2.4;
      m.scale.set(s, s, s);
      const mat = m.material as THREE.MeshBasicMaterial;
      mat.opacity = Math.max(0, 1 - age);
      mat.color.set(world.phase === 'over' ? COLOR.magenta : COLOR.yellow);
    }
  });

  return (
    <group>
      {Array.from({ length: BURST_POOL }, (_, i) => (
        <mesh
          key={i}
          ref={(el) => {
            meshes.current[i] = el;
          }}
          visible={false}
        >
          <sphereGeometry args={[0.5, 12, 12]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      ))}
    </group>
  );
}
