import { Grid } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import { COLOR, LANE_W } from '../game/constants';
import { world } from '../game/runtime';

export function Track() {
  const grid = useRef<THREE.Group>(null);

  useFrame(() => {
    if (!grid.current) return;
    const period = 4;
    grid.current.position.z = world.distance % period;
  });

  return (
    <group>
      <group ref={grid}>
        <Grid
          position={[0, 0, -40]}
          args={[200, 200]}
          cellSize={1}
          cellThickness={0.6}
          cellColor={COLOR.violet}
          sectionSize={4}
          sectionThickness={1.4}
          sectionColor={COLOR.cyan}
          fadeDistance={130}
          fadeStrength={1.5}
          infiniteGrid
        />
      </group>
      <mesh position={[0, -0.02, -1]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[LANE_W * 3 + 2, 240]} />
        <meshStandardMaterial color="#120726" roughness={0.9} />
      </mesh>
      <mesh position={[0, 18, -170]}>
        <circleGeometry args={[26, 48]} />
        <meshBasicMaterial color={COLOR.magenta} fog={false} />
      </mesh>
      <mesh position={[0, 16, -168]}>
        <circleGeometry args={[22, 48]} />
        <meshBasicMaterial color={COLOR.bg} fog={false} />
      </mesh>
    </group>
  );
}
