import { Canvas } from '@react-three/fiber';
import { Suspense } from 'react';
import { COLOR, FOV_BASE, FOG_DENSITY } from '../game/constants';
import { CameraRig } from './CameraRig';
import { Coins } from './Coins';
import { Effects } from './Effects';
import { GameLoop } from './GameLoop';
import { Obstacles } from './Obstacles';
import { Particles } from './Particles';
import { Player } from './Player';
import { Track } from './Track';

export function Scene() {
  return (
    <Canvas
      camera={{ position: [0, 3.2, 7.5], fov: FOV_BASE, near: 0.1, far: 220 }}
      gl={{ antialias: true }}
      dpr={[1, 2]}
    >
      <color attach="background" args={[COLOR.bg]} />
      <fogExp2 attach="fog" args={[COLOR.fog, FOG_DENSITY]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[6, 12, 4]} intensity={0.6} color={COLOR.violet} />
      <Suspense fallback={null}>
        <GameLoop />
        <Track />
        <Obstacles />
        <Coins />
        <Particles />
        <CameraRig />
        <Player />
      </Suspense>
      <Effects />
    </Canvas>
  );
}
