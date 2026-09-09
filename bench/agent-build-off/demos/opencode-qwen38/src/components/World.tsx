import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Grid, Stars } from '@react-three/drei'
import { CuboidCollider, RigidBody } from '@react-three/rapier'
import type * as THREE from 'three'
import { runtime } from '../store'

const FOG_COLOR = '#05010f'
const DASH_COUNT = 8
const DASH_SPAN = 90
const DASH_INTERVAL = DASH_SPAN / DASH_COUNT

export function World() {
  const dashGroup = useRef<THREE.Group>(null)

  useFrame(() => {
    if (!dashGroup.current) return
    const children = dashGroup.current.children
    for (let i = 0; i < children.length; i++) {
      const c = children[i]
      const base = c.userData.base as number
      let z = base - (runtime.distance % DASH_SPAN)
      if (z < -35) z += DASH_SPAN
      c.position.z = z
    }
  })

  return (
    <>
      <color attach="background" args={[FOG_COLOR]} />
      <fog attach="fog" args={[FOG_COLOR, 30, 150]} />
      <ambientLight intensity={0.25} />
      <directionalLight position={[6, 18, -8]} intensity={0.7} color="#ff9de2" />

      <Stars radius={240} depth={70} count={2600} factor={5} saturation={0} fade speed={0.5} />

      <mesh position={[0, 16, 168]} rotation={[0, Math.PI, 0]}>
        <circleGeometry args={[26, 48]} />
        <meshBasicMaterial color="#ff5e3a" toneMapped={false} fog={false} />
      </mesh>
      {[8, 12, 16].map((y) => (
        <mesh key={y} position={[0, y, 169]}>
          <planeGeometry args={[62, 1.6]} />
          <meshBasicMaterial color={FOG_COLOR} toneMapped={false} fog={false} />
        </mesh>
      ))}

      <mesh rotation-x={-Math.PI / 2} position-y={0}>
        <planeGeometry args={[700, 700]} />
        <meshBasicMaterial color="#070113" />
      </mesh>

      <Grid
        position={[0, 0.02, 0]}
        infiniteGrid
        cellSize={2}
        cellThickness={0.5}
        cellColor="#5b2a86"
        sectionSize={10}
        sectionThickness={1.2}
        sectionColor="#ff2975"
        fadeDistance={120}
        fadeStrength={2}
      />

      {[-1, 1].map((side) => (
        <mesh key={`edge${side}`} rotation-x={-Math.PI / 2} position={[side * 3.2, 0.03, 60]}>
          <planeGeometry args={[0.08, 520]} />
          <meshBasicMaterial color="#00f0ff" toneMapped={false} />
        </mesh>
      ))}

      <group ref={dashGroup}>
        {[-1, 1].flatMap((side) =>
          Array.from({ length: DASH_COUNT }, (_, j) => (
            <mesh
              key={`${side}-${j}`}
              ref={(m) => {
                if (m) m.userData.base = j * DASH_INTERVAL
              }}
              rotation-x={-Math.PI / 2}
              position={[side * 1.0, 0.03, j * DASH_INTERVAL]}
            >
              <planeGeometry args={[0.14, 2.4]} />
              <meshBasicMaterial color="#ff2975" toneMapped={false} transparent opacity={0.9} />
            </mesh>
          )),
        )}
      </group>

    </>
  )
}

export function GroundCollider() {
  return (
    <RigidBody type="fixed" colliders={false}>
      <CuboidCollider args={[40, 0.5, 280]} position={[0, -0.5, 110]} />
    </RigidBody>
  )
}
