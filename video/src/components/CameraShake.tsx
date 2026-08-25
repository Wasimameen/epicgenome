import React from 'react';
import {AbsoluteFill, interpolate, random, useCurrentFrame} from 'remotion';

/**
 * Decaying handheld jolt. Used on collision frames only — shake that never
 * settles stops reading as impact and starts reading as a broken camera.
 */
export const CameraShake: React.FC<{
  impactAt: number;
  intensity?: number;
  decay?: number;
  children: React.ReactNode;
}> = ({impactAt, intensity = 26, decay = 22, children}) => {
  const frame = useCurrentFrame();
  const local = frame - impactAt;

  const falloff =
    local < 0 ? 0 : interpolate(local, [0, decay], [1, 0], {extrapolateRight: 'clamp'});
  const amp = intensity * falloff * falloff;

  const x = (random(`shx-${frame}`) - 0.5) * 2 * amp;
  const y = (random(`shy-${frame}`) - 0.5) * 2 * amp;
  const r = (random(`shr-${frame}`) - 0.5) * 2 * amp * 0.06;

  return (
    <AbsoluteFill style={{transform: `translate(${x}px, ${y}px) rotate(${r}deg)`}}>
      {children}
    </AbsoluteFill>
  );
};
