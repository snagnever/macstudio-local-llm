import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import {
  BARRIER_H,
  COLOR,
  DEPTH,
  GATE_BOTTOM,
  GATE_TOP,
  LANE_W,
  LANE_X,
  WALL_TOP,
} from '../game/constants';
import { world } from '../game/runtime';

const POOL = 24;

export function Obstacles() {
  const meshes = useRef<(THREE.Mesh | null)[]>([]);

  useFrame(() => {
    let i = 0;
    for (const row of world.rows) {
      for (const o of row.obstacles) {
        const m = meshes.current[i];
        if (!m) continue;
        i++;
        const boxH =
          o.kind === 'barrier'
            ? BARRIER_H
            : o.kind === 'gate'
              ? GATE_TOP - GATE_BOTTOM
              : WALL_TOP;
        m.visible = true;
        m.position.set(
          LANE_X[o.lane],
          o.kind === 'gate' ? GATE_BOTTOM + boxH / 2 : boxH / 2,
          row.z,
        );
        m.scale.set(LANE_W * 0.8, boxH, DEPTH);
        const mat = m.material as THREE.MeshStandardMaterial;
        mat.emissiveIntensity = world.phase === 'over' ? 0.5 : 1.4;
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
          <boxGeometry args={[1, 1, 1]} />
          <meshStandardMaterial
            color={COLOR.white}
            emissive={COLOR.cyan}
            emissiveIntensity={1.4}
            roughness={0.3}
          />
        </mesh>
      ))}
    </group>
  );
}
