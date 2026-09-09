import { useEffect, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import {
  CapsuleCollider,
  CuboidCollider,
  RigidBody,
  type RapierRigidBody,
} from '@react-three/rapier'
import * as THREE from 'three'
import { LANE_WIDTH, runtime, useStore } from '../store'
import { sfx } from '../sfx'

const GRAVITY = -16
const JUMP_V = 8.5
const CAPSULE_HALF = 0.37
const CAPSULE_RADIUS = 0.22
const SLIDE_HALF = 0.2
const SLIDE_OFFSET = -0.39
const SLIDE_DURATION = 0.55
const SLIDE_COOLDOWN = 1.0
const INPUT_BUFFER = 0.18
const COYOTE_TIME = 0.12
const STAND_Y = CAPSULE_HALF + CAPSULE_RADIUS
const LANE_DAMPING = 10
const MAX_LANE_SPEED = 14

export const PHYSICS_GRAVITY: [number, number, number] = [0, GRAVITY, 0]

const clamp = THREE.MathUtils.clamp

export function Player() {
  const body = useRef<RapierRigidBody>(null)
  const status = useStore((s) => s.status)
  const sliding = useStore((s) => s.sliding)

  useEffect(() => {
    if (status !== 'running' || !body.current) return
    body.current.setTranslation({ x: 0, y: STAND_Y + 0.01, z: 0 }, true)
    body.current.setLinvel({ x: 0, y: 0, z: 0 }, true)
    runtime.playerX = 0
  }, [status])

  useFrame(() => {
    const b = body.current
    if (!b) return
    const running = useStore.getState().status === 'running'
    const t = b.translation()
    runtime.playerX = t.x
    runtime.playerY = t.y
    const lv = b.linvel()

    if (!running) return

    const setSliding = useStore.getState().setSliding
    const slideBuffered = runtime.time - runtime.slideQueuedAt < INPUT_BUFFER
    if (slideBuffered && runtime.time >= runtime.slideCoolEnd) {
      runtime.slideQueuedAt = -10
      runtime.slideEnd = runtime.time + SLIDE_DURATION
      runtime.slideCoolEnd = runtime.time + SLIDE_COOLDOWN
      setSliding(true)
      sfx.slide()
    }
    if (sliding && runtime.time >= runtime.slideEnd) setSliding(false)

    const grounded = t.y < STAND_Y + 0.25 && Math.abs(lv.y) < 0.5
    if (grounded) runtime.groundedAt = runtime.time
    const canJump = grounded || runtime.time - runtime.groundedAt < COYOTE_TIME
    const jumpBuffered = runtime.time - runtime.jumpQueuedAt < INPUT_BUFFER
    if (jumpBuffered && canJump) {
      runtime.jumpQueuedAt = -10
      lv.y = JUMP_V
      sfx.jump()
    }

    const targetX = runtime.lane * LANE_WIDTH
    const vx = clamp((targetX - t.x) * LANE_DAMPING, -MAX_LANE_SPEED, MAX_LANE_SPEED)
    b.setLinvel({ x: vx, y: lv.y, z: 0 }, true)
  })

  return (
    <RigidBody
      ref={body}
      position={[0, STAND_Y + 0.01, 0]}
      type="dynamic"
      lockRotations
      enabledRotations={[false, false, false]}
      ccd
    >
      {sliding ? (
        <CuboidCollider args={[0.3, SLIDE_HALF, 0.3]} position={[0, SLIDE_OFFSET, 0]} />
      ) : (
        <CapsuleCollider args={[CAPSULE_HALF, CAPSULE_RADIUS]} />
      )}

      <pointLight color="#00f0ff" intensity={6} distance={7} position={[0, 0.4, 0]} />

      {sliding ? (
        <mesh position={[0, SLIDE_OFFSET, 0]} castShadow>
          <boxGeometry args={[0.64, 0.4, 0.64]} />
          <meshStandardMaterial
            color="#001a1f"
            emissive="#00f0ff"
            emissiveIntensity={2.4}
            toneMapped={false}
          />
        </mesh>
      ) : (
        <mesh castShadow>
          <capsuleGeometry args={[0.25, 0.8, 6, 16]} />
          <meshStandardMaterial
            color="#001a1f"
            emissive="#00f0ff"
            emissiveIntensity={2.4}
            toneMapped={false}
          />
        </mesh>
      )}
    </RigidBody>
  )
}
