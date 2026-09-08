import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import { COLOR, PLAYER_H } from '../game/constants';
import { world } from '../game/runtime';

export function Player() {
  const group = useRef<THREE.Group>(null);
  const body = useRef<THREE.Mesh>(null);

  useFrame(() => {
    const g = group.current;
    if (!g) return;
    const p = world.player;
    g.position.set(p.x, p.y + p.height / 2, 0);
    g.scale.set(1, p.height / PLAYER_H, 1);
    g.rotation.z = -p.x * 0.08;
    if (body.current) {
      const m = body.current.material as THREE.MeshStandardMaterial;
      m.emissiveIntensity = world.phase === 'over' ? 0.2 : 1.6;
    }
  });

  return (
    <group ref={group}>
      <mesh ref={body}>
        <coneGeometry args={[0.45, 1.2, 4]} />
        <meshStandardMaterial
          color={COLOR.cyan}
          emissive={COLOR.cyan}
          emissiveIntensity={1.6}
          roughness={0.2}
        />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, -0.5, 0]}>
        <torusGeometry args={[0.6, 0.07, 8, 32]} />
        <meshStandardMaterial
          color={COLOR.magenta}
          emissive={COLOR.magenta}
          emissiveIntensity={2.2}
        />
      </mesh>
      <pointLight color={COLOR.cyan} intensity={6} distance={8} position={[0, 0.4, 0]} />
    </group>
  );
}
