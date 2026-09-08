import * as THREE from 'three'

/** A neon grid drawn once into a canvas, then tiled and scrolled along the floor. */
export function makeGridTexture(): THREE.CanvasTexture {
  const size = 256
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#05030c'
  ctx.fillRect(0, 0, size, size)

  ctx.strokeStyle = '#ff2fb9'
  ctx.lineWidth = 6
  ctx.shadowColor = '#ff2fb9'
  ctx.shadowBlur = 16
  ctx.beginPath()
  ctx.moveTo(0, size - 3)
  ctx.lineTo(size, size - 3)
  ctx.stroke()

  ctx.strokeStyle = '#1de9ff'
  ctx.lineWidth = 3
  ctx.shadowColor = '#1de9ff'
  for (const x of [0, size / 2]) {
    ctx.beginPath()
    ctx.moveTo(x + 1.5, 0)
    ctx.lineTo(x + 1.5, size)
    ctx.stroke()
  }

  const texture = new THREE.CanvasTexture(canvas)
  texture.wrapS = THREE.RepeatWrapping
  texture.wrapT = THREE.RepeatWrapping
  texture.anisotropy = 4
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}
