import { Bloom, EffectComposer, Vignette } from '@react-three/postprocessing';

export function Effects() {
  return (
    <EffectComposer multisampling={4}>
      <Bloom intensity={0.9} luminanceThreshold={0.2} luminanceSmoothing={0.6} mipmapBlur />
      <Vignette offset={0.3} darkness={0.85} />
    </EffectComposer>
  );
}
