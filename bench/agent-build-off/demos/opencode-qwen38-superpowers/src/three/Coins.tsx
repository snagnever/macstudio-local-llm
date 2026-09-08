import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import { COLOR, LANE_X } from '../game/constants';
import { world } from '../game/runtime';

const POOL = 12;

export function Coins() {
  const meshes = useRef<(THREE.Mesh | null)[]>([]);

  useFrame((_, delta) => {
    let i = 0;
    for (const row of world.rows) {
      for (const c of row.coins) {
        if (c.taken) continue;
        const m = meshes.current[i];
        if (!m) continue;
        i++;
        m.visible = true;
        m.position.set(LANE_X[c.lane], c.y, c.z);
        m.rotation.y += delta * 3;
      }
    }
    for (; i < POOL; i++) {
      const m = meshes.current[i];
      if (m) m.visible = false;
    }
  });

  return (
    <group>
      {Array.from({ length: POOL }, (_, i) => (
        <mesh
          key={i}
          ref={(el) => {
            meshes.current[i] = el;
          }}
          visible={false}
        >
          <octahedronGeometry args={[0.35, 0]} />
          <meshStandardMaterial
            color={COLOR.yellow}
            emissive={COLOR.yellow}
            emissiveIntensity={2}
            roughness={0.2}
          />
        </mesh>
      ))}
    </group>
  );
}
