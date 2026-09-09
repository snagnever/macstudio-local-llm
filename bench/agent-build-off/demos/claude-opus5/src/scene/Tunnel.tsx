import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { RIB_COUNT, RIB_SPACING, TUNNEL_RADIUS } from '../game/config'
import { world } from '../game/world'
import { makeGridTexture } from './textures'

const FLOOR_LENGTH = 420
const TILE_LENGTH = 6

/** The tunnel is a scrolling grid floor, a dark shell, and a treadmill of neon ribs. */
export function Tunnel() {
  const grid = useMemo(makeGridTexture, [])
  const ribs = useRef<THREE.InstancedMesh>(null)
  const dummy = useMemo(() => new THREE.Object3D(), [])

  useMemo(() => {
    grid.repeat.set(4, FLOOR_LENGTH / TILE_LENGTH)
  }, [grid])

  useFrame(() => {
    grid.offset.y = -(world.distance / TILE_LENGTH) % 1

    const mesh = ribs.current
    if (!mesh) return
    const drift = world.distance % RIB_SPACING
    for (let i = 0; i < RIB_COUNT; i++) {
      const z = drift - i * RIB_SPACING + RIB_SPACING
      dummy.position.set(0, TUNNEL_RADIUS * 0.32, z)
      dummy.rotation.z = Math.PI / 8
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
    }
    mesh.instanceMatrix.needsUpdate = true
  })

  return (
    <group>
      <mesh rotation-x={-Math.PI / 2} position={[0, 0, -FLOOR_LENGTH / 2 + 20]} receiveShadow={false}>
        <planeGeometry args={[22, FLOOR_LENGTH]} />
        <meshStandardMaterial
          map={grid}
          color="#ffffff"
          emissive="#3a1060"
          emissiveIntensity={0.35}
          roughness={0.45}
          metalness={0.1}
        />
      </mesh>

      <mesh position={[0, TUNNEL_RADIUS * 0.32, -FLOOR_LENGTH / 2 + 20]} rotation-x={Math.PI / 2}>
        <cylinderGeometry args={[TUNNEL_RADIUS + 0.6, TUNNEL_RADIUS + 0.6, FLOOR_LENGTH, 8, 1, true]} />
        <meshStandardMaterial color="#0a0618" side={THREE.BackSide} roughness={0.9} metalness={0.2} />
      </mesh>

      <instancedMesh ref={ribs} args={[undefined, undefined, RIB_COUNT]} frustumCulled={false}>
        <torusGeometry args={[TUNNEL_RADIUS, 0.075, 4, 8]} />
        <meshBasicMaterial color="#1de9ff" toneMapped={false} />
      </instancedMesh>

      {[-5.4, 5.4].map((x) => (
        <mesh key={x} position={[x, 0.06, -FLOOR_LENGTH / 2 + 20]}>
          <boxGeometry args={[0.12, 0.12, FLOOR_LENGTH]} />
          <meshBasicMaterial color="#ff2fb9" toneMapped={false} />
        </mesh>
      ))}
      {[-1.2, 1.2, -3.6, 3.6].map((x) => (
        <mesh key={x} position={[x, 0.03, -FLOOR_LENGTH / 2 + 20]}>
          <boxGeometry args={[0.05, 0.05, FLOOR_LENGTH]} />
          <meshBasicMaterial color="#1de9ff" toneMapped={false} />
        </mesh>
      ))}
    </group>
  )
}
