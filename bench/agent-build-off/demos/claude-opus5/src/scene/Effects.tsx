import { Bloom, ChromaticAberration, EffectComposer, Vignette } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import { useMemo } from 'react'
import * as THREE from 'three'
import { useStore } from '../state/store'

export function Effects() {
  const lowQuality = useStore((s) => s.lowQuality)
  const offset = useMemo(() => new THREE.Vector2(0.0006, 0.0009), [])

  if (lowQuality) return null

  return (
    <EffectComposer multisampling={0}>
      <Bloom intensity={1.15} luminanceThreshold={0.22} luminanceSmoothing={0.5} mipmapBlur radius={0.72} />
      <ChromaticAberration offset={offset} radialModulation={false} modulationOffset={0} />
      <Vignette offset={0.28} darkness={0.82} blendFunction={BlendFunction.NORMAL} />
    </EffectComposer>
  )
}
