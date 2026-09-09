import { Physics, RigidBody } from '@react-three/rapier'
import { useMemo } from 'react'
import { DEBRIS_COUNT } from '../game/config'
import { mulberry32 } from '../game/rng'
import { world } from '../game/world'

/**
 * The physics engine mounts only after a crash. It simulates the wreck while the camera
 * orbits, then unmounts with the phase. Gameplay never touches a solver.
 */
export function Debris() {
  const crash = world.crash
  const pieces = useMemo(() => {
    const rng = mulberry32(Math.floor((crash?.z ?? 0) * 1000) ^ 0x9e37)
    return Array.from({ length: DEBRIS_COUNT }, () => ({
      size: 0.18 + rng() * 0.36,
      offset: [(rng() - 0.5) * 1.6, 0.3 + rng() * 1.3, -0.6 + (rng() - 0.5) * 1.2] as [number, number, number],
      // Mostly up and sideways. A hard shove toward the camera would throw the pieces
      // straight out of frame.
      impulse: [(rng() - 0.5) * 6, 3 + rng() * 5, 0.5 + rng() * 2.5] as [number, number, number],
      hot: rng() > 0.5,
    }))
  }, [crash?.z])

  if (!crash) return null

  return (
    <Physics gravity={[0, -18, 0]} timeStep="vary">
      {pieces.map((piece, i) => (
        <RigidBody
          key={i}
          position={[crash.x + piece.offset[0], crash.y + piece.offset[1], crash.z + piece.offset[2]]}
          linearVelocity={piece.impulse}
          angularVelocity={[piece.impulse[1], piece.impulse[0], piece.impulse[2]]}
          restitution={0.42}
          friction={0.7}
        >
          <mesh castShadow={false}>
            <boxGeometry args={[piece.size, piece.size, piece.size]} />
            <meshStandardMaterial
              color={piece.hot ? '#2a0510' : '#130a2e'}
              emissive={piece.hot ? '#ff4d2f' : '#7b2fff'}
              emissiveIntensity={2.4}
              roughness={0.4}
              metalness={0.5}
            />
          </mesh>
        </RigidBody>
      ))}
      <RigidBody type="fixed" position={[0, -0.5, crash.z]}>
        <mesh visible={false}>
          <boxGeometry args={[40, 1, 40]} />
          <meshBasicMaterial />
        </mesh>
      </RigidBody>
    </Physics>
  )
}
