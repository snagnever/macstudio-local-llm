import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { BASE_SPEED, runtime } from '../store'

const { damp } = THREE.MathUtils

export function Camera() {
  useFrame((state, dt) => {
    const cam = state.camera as THREE.PerspectiveCamera
    const d = Math.min(dt, 0.05)
    const targetX = runtime.playerX * 0.55
    cam.position.x = damp(cam.position.x, targetX, 4, d)
    cam.position.y = 3.1 + Math.sin(runtime.time * 11) * 0.05 * (runtime.speed / BASE_SPEED)
    const targetFov = 55 + (runtime.speed - BASE_SPEED) * 0.9
    if (Math.abs(cam.fov - targetFov) > 0.01) {
      cam.fov = damp(cam.fov, targetFov, 2.5, d)
      cam.updateProjectionMatrix()
    }
    cam.lookAt(targetX * 0.6, 1.1, 18)
  })
  return null
}
