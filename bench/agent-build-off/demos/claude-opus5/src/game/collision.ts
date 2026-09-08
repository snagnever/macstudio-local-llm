/** Axis-aligned bounding box overlap. Centres and half extents. */
export type Box = {
  x: number
  y: number
  z: number
  hx: number
  hy: number
  hz: number
}

export function overlaps(a: Box, b: Box): boolean {
  return (
    Math.abs(a.x - b.x) < a.hx + b.hx &&
    Math.abs(a.y - b.y) < a.hy + b.hy &&
    Math.abs(a.z - b.z) < a.hz + b.hz
  )
}

/** Squared distance in the ground plane, used for coin pickup. */
export function nearXZ(ax: number, az: number, bx: number, bz: number, radius: number): boolean {
  const dx = ax - bx
  const dz = az - bz
  return dx * dx + dz * dz < radius * radius
}
