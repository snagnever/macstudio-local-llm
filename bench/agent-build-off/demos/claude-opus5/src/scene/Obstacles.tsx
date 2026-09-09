import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { OBSTACLE_SHAPE, type ObstacleType } from '../game/config'
import { world } from '../game/world'

const PER_TYPE = 40

const LOOK: Record<ObstacleType, { color: string; emissive: string; glow: number }> = {
  barrier: { color: '#2a0f05', emissive: '#ff6a2f', glow: 1.6 },
  beam: { color: '#2a0520', emissive: '#ff2fb9', glow: 1.6 },
  // The wall is the largest surface, so it glows less or it flattens into a slab.
  wall: { color: '#130a2e', emissive: '#6a24e0', glow: 0.75 },
  drone: { color: '#2a0510', emissive: '#ff2f4f', glow: 2 },
}

const TYPES = Object.keys(OBSTACLE_SHAPE) as ObstacleType[]

/** One instanced mesh per obstacle type. Nothing is allocated per frame. */
export function Obstacles() {
  const refs = useRef<Record<string, THREE.InstancedMesh | null>>({})
  const dummy = useMemo(() => new THREE.Object3D(), [])
  const counts = useMemo<Record<string, number>>(() => ({}), [])

  useFrame((_, delta) => {
    for (const type of TYPES) counts[type] = 0

    for (const o of world.spawner.obstacles) {
      if (!o.active) continue
      const mesh = refs.current[o.type]
      if (!mesh) continue
      const index = counts[o.type]
      if (index >= PER_TYPE) continue
      const shape = OBSTACLE_SHAPE[o.type]
      dummy.position.set(o.x, shape.cy, o.z)
      dummy.rotation.set(0, 0, 0)
      if (o.type === 'drone') {
        dummy.rotation.y = world.elapsed * 2 + o.phase
        dummy.rotation.x = world.elapsed * 1.3
        dummy.position.y = shape.cy + Math.sin(world.elapsed * 2.2 + o.phase) * 0.2
      }
      dummy.scale.setScalar(1)
      dummy.updateMatrix()
      mesh.setMatrixAt(index, dummy.matrix)
      counts[o.type] = index + 1
    }

    for (const type of TYPES) {
      const mesh = refs.current[type]
      if (!mesh) continue
      dummy.position.set(0, -500, 0)
      dummy.rotation.set(0, 0, 0)
      dummy.scale.setScalar(0.0001)
      dummy.updateMatrix()
      for (let i = counts[type]; i < PER_TYPE; i++) mesh.setMatrixAt(i, dummy.matrix)
      mesh.instanceMatrix.needsUpdate = true
    }
    void delta
  })

  return (
    <group>
      {TYPES.map((type) => {
        const shape = OBSTACLE_SHAPE[type]
        const look = LOOK[type]
        return (
          <instancedMesh
            key={type}
            ref={(node) => {
              refs.current[type] = node
            }}
            args={[undefined, undefined, PER_TYPE]}
            frustumCulled={false}
          >
            {type === 'drone' ? (
              <octahedronGeometry args={[shape.hx * 1.1, 0]} />
            ) : (
              <boxGeometry args={[shape.hx * 2, shape.hy * 2, shape.hz * 2]} />
            )}
            <meshStandardMaterial
              color={look.color}
              emissive={look.emissive}
              emissiveIntensity={look.glow}
              roughness={0.35}
              metalness={0.4}
            />
          </instancedMesh>
        )
      })}
    </group>
  )
}
