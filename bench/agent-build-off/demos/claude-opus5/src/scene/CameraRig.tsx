import { useFrame, useThree } from '@react-three/fiber'
import { useMemo } from 'react'
import * as THREE from 'three'
import { SPEED_MAX, SPEED_START } from '../game/config'
import { world } from '../game/world'

const BASE = new THREE.Vector3(0, 3.3, 7.4)
const FOV_MIN = 62
const FOV_MAX = 84

/** Follows the player, widens with speed, shakes on impact, and orbits the wreck. */
export function CameraRig() {
  const camera = useThree((state) => state.camera) as THREE.PerspectiveCamera
  const target = useMemo(() => new THREE.Vector3(), [])

  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.05)
    const p = world.player
    const speedRatio = (world.speed - SPEED_START) / (SPEED_MAX - SPEED_START)
    const wantedFov = FOV_MIN + (FOV_MAX - FOV_MIN) * Math.max(0, Math.min(1, speedRatio))

    if (world.phase === 'dead') {
      // Orbit the wreck from inside the tunnel. The radius stays under the shell so the
      // camera never leaves the corridor.
      const t = world.deadT
      // A gentle sway rather than a full orbit, so the wreck stays framed and the camera
      // never swings behind the player.
      const angle = 0.55 + Math.sin(t * 0.45) * 0.25
      const radius = 5.0
      camera.position.lerp(
        target.set(p.x + Math.sin(angle) * radius, 2.9 + Math.sin(t * 0.7) * 0.2, Math.cos(angle) * radius),
        Math.min(1, dt * 2.4),
      )
      camera.lookAt(p.x * 0.6, 1.25, -1.6)
      camera.fov += (FOV_MIN - camera.fov) * Math.min(1, dt * 3)
      camera.updateProjectionMatrix()
      return
    }

    const shake = world.shake * 0.5
    camera.position.lerp(
      target.set(BASE.x + p.x * 0.32, BASE.y + p.y * 0.16, BASE.z),
      Math.min(1, dt * 7),
    )
    camera.position.x += (Math.random() - 0.5) * shake
    camera.position.y += (Math.random() - 0.5) * shake
    camera.lookAt(p.x * 0.42, 1.45 + p.y * 0.28, -12)
    camera.fov += (wantedFov - camera.fov) * Math.min(1, dt * 2.2)
    camera.updateProjectionMatrix()
  })

  return null
}
