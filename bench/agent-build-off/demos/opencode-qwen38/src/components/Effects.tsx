import {
  Bloom,
  ChromaticAberration,
  EffectComposer,
  Vignette,
} from '@react-three/postprocessing'
import { Vector2 } from 'three'

const ABERRATION_OFFSET = new Vector2(0.0006, 0.0009)

export function Effects() {
  return (
    <EffectComposer multisampling={0}>
      <Bloom intensity={1.15} luminanceThreshold={0.2} luminanceSmoothing={0.4} mipmapBlur />
      <ChromaticAberration offset={ABERRATION_OFFSET} />
      <Vignette darkness={0.72} offset={0.28} />
    </EffectComposer>
  )
}
