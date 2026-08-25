import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

/** Volumetric shafts from an off-frame source. Slowly breathing, never static. */
export const LightRays: React.FC<{
  angle?: number;
  opacity?: number;
  origin?: string;
}> = ({angle = -18, opacity = 0.16, origin = '62% -10%'}) => {
  const frame = useCurrentFrame();
  const breathe = interpolate(Math.sin(frame * 0.014), [-1, 1], [0.72, 1.12]);

  return (
    <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'screen', opacity: opacity * breathe}}>
      <AbsoluteFill
        style={{
          transformOrigin: origin,
          transform: `rotate(${angle + Math.sin(frame * 0.008) * 1.6}deg)`,
          background:
            'repeating-linear-gradient(96deg, rgba(255,226,170,0.5) 0px, rgba(255,226,170,0.5) 3px, transparent 3px, transparent 58px, rgba(255,226,170,0.28) 58px, rgba(255,226,170,0.28) 70px, transparent 70px, transparent 150px)',
          filter: 'blur(22px)',
          maskImage: 'radial-gradient(ellipse 70% 60% at 60% 0%, #000 0%, transparent 72%)',
          WebkitMaskImage:
            'radial-gradient(ellipse 70% 60% at 60% 0%, #000 0%, transparent 72%)',
        }}
      />
    </AbsoluteFill>
  );
};
