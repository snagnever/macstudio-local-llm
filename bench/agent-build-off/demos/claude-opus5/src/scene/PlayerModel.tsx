import { useEffect, useMemo, useRef } from 'react'
import { useAnimations, useGLTF } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { PLAYER_HEIGHT } from '../game/config'
import { world } from '../game/world'

const MODEL_URL = `${import.meta.env.BASE_URL}models/robot.glb`

/** Clip names are resolved through this table, so a renamed clip cannot crash the demo. */
const ALIASES = {
  run: ['Running', 'Run', 'Walking'],
  jump: ['Jump', 'WalkJump'],
  death: ['Death', 'Die'],
  idle: ['Idle', 'Standing'],
} as const

type ClipRole = keyof typeof ALIASES

export function PlayerModel() {
  const group = useRef<THREE.Group>(null)
  const inner = useRef<THREE.Group>(null)
  const gltf = useGLTF(MODEL_URL)
  const { actions, names } = useAnimations(gltf.animations, group)
  const current = useRef<string | null>(null)

  const resolve = useMemo(() => {
    const map = {} as Record<ClipRole, string>
    for (const role of Object.keys(ALIASES) as ClipRole[]) {
      const found = ALIASES[role].find((name) => names.includes(name))
      map[role] = found ?? names[0]
    }
    return map
  }, [names])

  /** Scale to the collision height and drop the feet onto the floor, rather than guessing. */
  const fit = useMemo(() => {
    const box = new THREE.Box3().setFromObject(gltf.scene)
    const height = box.max.y - box.min.y
    const scale = height > 0 ? PLAYER_HEIGHT / height : 1
    return { scale, footOffset: -box.min.y * scale }
  }, [gltf.scene])

  useEffect(() => {
    for (const object of gltf.scene.children) object.frustumCulled = false
  }, [gltf.scene])

  function play(name: string, loop: boolean, fade = 0.18) {
    if (current.current === name) return
    const next = actions[name]
    if (!next) return
    const previous = current.current ? actions[current.current] : null
    next.reset()
    next.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, loop ? Infinity : 1)
    next.clampWhenFinished = !loop
    next.fadeIn(fade).play()
    previous?.fadeOut(fade)
    current.current = name
  }

  useFrame((_, delta) => {
    const g = group.current
    const body = inner.current
    if (!g || !body) return
    const p = world.player

    g.position.set(p.x, p.y, 0)
    g.rotation.z = -p.tilt
    g.rotation.y = Math.PI + p.tilt * 0.5

    const slideLean = p.sliding ? 1 : 0
    body.rotation.x += (slideLean * -1.15 - body.rotation.x) * Math.min(1, delta * 14)
    body.position.y = fit.footOffset + (p.sliding ? 0.28 : 0)

    if (world.phase === 'dead') play(resolve.death, false)
    else if (world.phase === 'playing') play(p.airborne ? resolve.jump : resolve.run, !p.airborne)
    else play(resolve.idle, true)

    const runAction = actions[resolve.run]
    if (runAction) runAction.timeScale = world.phase === 'playing' ? 0.9 + world.speed / 26 : 1
  })

  return (
    <group ref={group} dispose={null}>
      <group ref={inner}>
        <primitive object={gltf.scene} scale={fit.scale} />
      </group>
      <pointLight position={[0, 1.6, 0.8]} color="#9be9ff" intensity={6} distance={7} />
    </group>
  )
}

useGLTF.preload(MODEL_URL)
