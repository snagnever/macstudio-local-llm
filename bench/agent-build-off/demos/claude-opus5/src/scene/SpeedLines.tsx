import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { SPEED_LINE_COUNT, SPEED_MAX, SPEED_START } from '../game/config'
import { world } from '../game/world'

type Line = { x: number; y: number; z: number; len: number }

const RESET_Z = -150

/** Thin streaks that stream past the camera. Density and length follow the speed. */
export function SpeedLines() {
  const mesh = useRef<THREE.InstancedMesh>(null)
  const dummy = useMemo(() => new THREE.Object3D(), [])
  const lines = useMemo<Line[]>(
    () =>
      Array.from({ length: SPEED_LINE_COUNT }, () => {
        const angle = Math.random() * Math.PI * 2
        const radius = 2.6 + Math.random() * 3.6
        return {
          x: Math.cos(angle) * radius,
          y: 1.2 + Math.abs(Math.sin(angle)) * 4.2,
          z: -Math.random() * 150,
          len: 0.6 + Math.random() * 2.4,
        }
      }),
    [],
  )

  useFrame((_, delta) => {
    const target = mesh.current
    if (!target) return
    const dt = Math.min(delta, 0.05)
    const speed = world.phase === 'playing' ? world.speed : SPEED_START * 0.35
    const intensity = (speed - SPEED_START) / (SPEED_MAX - SPEED_START)
    const visible = Math.floor(SPEED_LINE_COUNT * (0.25 + 0.75 * Math.max(0, intensity)))

    for (let i = 0; i < SPEED_LINE_COUNT; i++) {
      const line = lines[i]
      line.z += speed * dt * 2.1
      if (line.z > 14) line.z = RESET_Z - Math.random() * 40
      if (i < visible) {
        dummy.position.set(line.x, line.y, line.z)
        dummy.rotation.set(0, 0, 0)
        dummy.scale.set(1, 1, line.len * (0.5 + Math.max(0, intensity)))
      } else {
        dummy.position.set(0, -500, 0)
        dummy.scale.setScalar(0.0001)
      }
      dummy.updateMatrix()
      target.setMatrixAt(i, dummy.matrix)
    }
    target.instanceMatrix.needsUpdate = true
  })

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, SPEED_LINE_COUNT]} frustumCulled={false}>
      <boxGeometry args={[0.035, 0.035, 1]} />
      <meshBasicMaterial color="#9be9ff" toneMapped={false} transparent opacity={0.55} />
    </instancedMesh>
  )
}
