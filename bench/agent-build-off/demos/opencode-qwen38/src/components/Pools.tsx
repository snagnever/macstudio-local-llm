import { memo, useEffect, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import {
  CuboidCollider,
  RigidBody,
  type RapierCollider,
  type RapierRigidBody,
} from '@react-three/rapier'
import * as THREE from 'three'
import { LANE_WIDTH, runtime, useStore } from '../store'
import {
  COIN_COUNT,
  COIN_PITCH,
  COIN_START_Z,
  OBSTACLE_COUNT,
  OBSTACLE_PITCH,
  OBSTACLE_START_Z,
} from '../store'
import { sfx } from '../sfx'

const RECYCLE_Z = -14
const KIND_COLORS = ['#ff9100', '#ff2975', '#39ff14']
const COIN_COLOR = '#ffd21f'
const GRAZE_NORMAL_Y = 0.55
const COL_POS = [
  { x: 0, y: 0.3, z: 0 },
  { x: 0, y: 1.2, z: 0 },
  { x: 0, y: 1.175, z: 0 },
]
const VOID_Y = -999

const devSlots: { z: number; lane: number; kind: number }[] = []
if (import.meta.env.DEV) {
  ;(window as unknown as Record<string, unknown>).__hrObs = devSlots
}

const pickLane = () => Math.floor(Math.random() * 3) - 1
const pickKind = () => {
  const r = Math.random()
  return r < 0.4 ? 0 : r < 0.72 ? 1 : 2
}

const Obstacle = memo(function Obstacle({ index }: { index: number }) {
  const body = useRef<RapierRigidBody>(null)
  const meshes = useRef<(THREE.Group | null)[]>([])
  const cols = useRef<(RapierCollider | null)[]>([])
  const slot = useRef({ z: 0, lane: 0, kind: 0 })

  const apply = (kind: number, lane: number, z: number) => {
    const s = slot.current
    s.kind = kind
    s.lane = lane
    s.z = z
    meshes.current.forEach((m, k) => {
      if (m) m.visible = k === kind
    })
    cols.current.forEach((c, k) => {
      if (!c) return
      c.setTranslationWrtParent(k === kind ? COL_POS[k] : { x: 0, y: VOID_Y, z: 0 })
    })
    body.current?.setTranslation({ x: lane * LANE_WIDTH, y: 0, z }, true)
    body.current?.setNextKinematicTranslation({ x: lane * LANE_WIDTH, y: 0, z })
  }

  useEffect(() => {
    devSlots[index] = slot.current
  }, [index])

  useEffect(() => {
    let prev = useStore.getState().status
    return useStore.subscribe((s) => {
      if (s.status === prev) return
      prev = s.status
      if (s.status === 'running') {
        const kind = index < 3 ? 0 : pickKind()
        apply(kind, pickLane(), OBSTACLE_START_Z + index * OBSTACLE_PITCH)
      }
    })
  }, [index])

  useFrame((_, dt) => {
    if (useStore.getState().status !== 'running') return
    const s = slot.current
    s.z -= runtime.speed * Math.min(dt, 0.05)
    if (s.z < RECYCLE_Z) {
      const gap = Math.max(11, runtime.speed * 0.72) + Math.random() * 6
      s.z = runtime.nextObstacleZ
      runtime.nextObstacleZ += gap
      apply(pickKind(), pickLane(), s.z)
    } else {
      body.current?.setNextKinematicTranslation({
        x: s.lane * LANE_WIDTH,
        y: 0,
        z: s.z,
      })
    }
  })

  return (
    <RigidBody
      ref={body}
      type="kinematicPosition"
      colliders={false}
      position={[0, 0, OBSTACLE_START_Z + index * OBSTACLE_PITCH]}
      onCollisionEnter={(payload) => {
        const st = useStore.getState()
        if (st.status !== 'running') return
        const n = payload.manifold?.normal()
        if (n && Math.abs(n.y) > GRAZE_NORMAL_Y) return
        const s = slot.current
        if (Math.abs(s.z) > 1.6 || Math.abs(runtime.playerX - s.lane * LANE_WIDTH) > 1.4) return
        sfx.crash()
        st.crash()
      }}
    >
      <CuboidCollider
        ref={(c) => {
          cols.current[0] = c
        }}
        args={[0.66, 0.3, 0.32]}
        position={[0, 0.3, 0]}
      />
      <CuboidCollider
        ref={(c) => {
          cols.current[1] = c
        }}
        args={[0.66, 1.2, 0.32]}
        position={[0, 1.2, 0]}
      />
      <CuboidCollider
        ref={(c) => {
          cols.current[2] = c
        }}
        args={[0.9, 0.25, 0.45]}
        position={[0, 1.175, 0]}
      />

      <group
        ref={(g) => {
          meshes.current[0] = g
        }}
        visible={index < 3}
      >
        <mesh position={[0, 0.35, 0]}>
          <boxGeometry args={[1.5, 0.7, 0.8]} />
          <meshStandardMaterial
            color="#140a00"
            emissive={KIND_COLORS[0]}
            emissiveIntensity={1.6}
            toneMapped={false}
          />
        </mesh>
      </group>

      <group
        ref={(g) => {
          meshes.current[1] = g
        }}
        visible={index >= 3}
      >
        <mesh position={[0, 1.1, 0]}>
          <boxGeometry args={[1.5, 2.2, 0.8]} />
          <meshStandardMaterial
            color="#14000a"
            emissive={KIND_COLORS[1]}
            emissiveIntensity={1.6}
            toneMapped={false}
          />
        </mesh>
      </group>

      <group
        ref={(g) => {
          meshes.current[2] = g
        }}
        visible={false}
      >
        <mesh position={[0, 1.175, 0]}>
          <boxGeometry args={[2.0, 0.45, 0.9]} />
          <meshStandardMaterial
            color="#001400"
            emissive={KIND_COLORS[2]}
            emissiveIntensity={1.6}
            toneMapped={false}
          />
        </mesh>
        {[-1.15, 1.15].map((x) => (
          <mesh key={x} position={[x, 0.95, 0]}>
            <boxGeometry args={[0.12, 1.9, 0.12]} />
            <meshStandardMaterial
              color="#001400"
              emissive={KIND_COLORS[2]}
              emissiveIntensity={0.9}
              toneMapped={false}
            />
          </mesh>
        ))}
      </group>
    </RigidBody>
  )
})

const Coin = memo(function Coin({ index }: { index: number }) {
  const body = useRef<RapierRigidBody>(null)
  const visual = useRef<THREE.Group>(null)
  const mesh = useRef<THREE.Mesh>(null)
  const slot = useRef({ z: 0, lane: 0, y: 0.95, collected: false })

  const place = (z: number) => {
    const s = slot.current
    s.z = z
    s.lane = pickLane()
    s.y = Math.random() < 0.3 ? 2.1 : 0.95
    s.collected = false
    if (visual.current) visual.current.visible = true
    body.current?.setNextKinematicTranslation({ x: s.lane * LANE_WIDTH, y: s.y, z })
  }

  useEffect(() => {
    let prev = useStore.getState().status
    return useStore.subscribe((s) => {
      if (s.status === prev) return
      prev = s.status
      if (s.status === 'running') place(COIN_START_Z + index * COIN_PITCH)
    })
  }, [index])

  useFrame((_, dt) => {
    if (mesh.current) mesh.current.rotation.y += dt * 4
    if (useStore.getState().status !== 'running') return
    const s = slot.current
    s.z -= runtime.speed * Math.min(dt, 0.05)
    if (s.z < RECYCLE_Z) {
      s.z = runtime.nextCoinZ
      runtime.nextCoinZ += 9 + Math.random() * 11
      place(s.z)
    } else {
      body.current?.setNextKinematicTranslation({
        x: s.lane * LANE_WIDTH,
        y: s.y,
        z: s.z,
      })
    }
  })

  return (
    <RigidBody
      ref={body}
      type="kinematicPosition"
      colliders={false}
      position={[0, 0.95, COIN_START_Z + index * COIN_PITCH]}
      onIntersectionEnter={() => {
        const s = slot.current
        const { status, coin } = useStore.getState()
        if (status !== 'running' || s.collected) return
        s.collected = true
        if (visual.current) visual.current.visible = false
        coin()
        sfx.coin()
      }}
    >
      <CuboidCollider args={[0.5, 0.5, 0.5]} sensor />
      <group ref={visual}>
        <mesh ref={mesh}>
          <torusGeometry args={[0.32, 0.12, 10, 24]} />
          <meshStandardMaterial
            color="#3a2e00"
            emissive={COIN_COLOR}
            emissiveIntensity={2.6}
            toneMapped={false}
          />
        </mesh>
      </group>
    </RigidBody>
  )
})

export function Pools() {
  return (
    <>
      {Array.from({ length: OBSTACLE_COUNT }, (_, i) => (
        <Obstacle key={`o${i}`} index={i} />
      ))}
      {Array.from({ length: COIN_COUNT }, (_, i) => (
        <Coin key={`c${i}`} index={i} />
      ))}
    </>
  )
}
