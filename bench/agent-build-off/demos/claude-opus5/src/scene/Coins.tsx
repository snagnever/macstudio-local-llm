import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { world } from '../game/world'

const MAX_COINS = 192

export function Coins() {
  const mesh = useRef<THREE.InstancedMesh>(null)
  const dummy = useMemo(() => new THREE.Object3D(), [])

  useFrame(() => {
    const target = mesh.current
    if (!target) return
    let index = 0
    for (const c of world.spawner.coins) {
      if (!c.active || index >= MAX_COINS) continue
      dummy.position.set(c.x, c.y, c.z)
      // The torus hole faces +z, so leaving x at zero keeps the coin upright and facing the run.
      dummy.rotation.set(0, world.elapsed * 3 + c.z * 0.1, 0)
      dummy.scale.setScalar(1)
      dummy.updateMatrix()
      target.setMatrixAt(index, dummy.matrix)
      index += 1
    }
    dummy.position.set(0, -500, 0)
    dummy.scale.setScalar(0.0001)
    dummy.updateMatrix()
    for (let i = index; i < MAX_COINS; i++) target.setMatrixAt(i, dummy.matrix)
    target.instanceMatrix.needsUpdate = true
  })

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, MAX_COINS]} frustumCulled={false}>
      <torusGeometry args={[0.3, 0.1, 6, 14]} />
      <meshStandardMaterial
        color="#ffb020"
        emissive="#ffd45e"
        emissiveIntensity={2.2}
        roughness={0.2}
        metalness={0.8}
      />
    </instancedMesh>
  )
}
