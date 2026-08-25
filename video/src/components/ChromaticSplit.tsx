import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

/**
 * RGB fringing that spikes on impact and decays. Applied as two tinted copies
 * of the scene offset in opposite directions — cheap, and reads as lens stress
 * rather than as a filter.
 */
export const ChromaticSplit: React.FC<{
  impactAt: number;
  decay?: number;
  maxOffset?: number;
  children: React.ReactNode;
}> = ({impactAt, decay = 20, maxOffset = 16, children}) => {
  const frame = useCurrentFrame();
  const local = frame - impactAt;
  const amount =
    local < 0 ? 0 : interpolate(local, [0, decay], [1, 0], {extrapolateRight: 'clamp'}) ** 2;
  const off = amount * maxOffset;

  if (off < 0.4) return <AbsoluteFill>{children}</AbsoluteFill>;

  return (
    <AbsoluteFill>
      <AbsoluteFill>{children}</AbsoluteFill>
      <AbsoluteFill
        style={{
          transform: `translateX(${-off}px)`,
          mixBlendMode: 'screen',
          opacity: amount * 0.55,
          filter: 'url(#redOnly)',
          background: 'rgba(255,0,0,0.001)',
        }}
      >
        <AbsoluteFill style={{filter: 'sepia(1) saturate(6) hue-rotate(-40deg)', opacity: 0.5}}>
          {children}
        </AbsoluteFill>
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          transform: `translateX(${off}px)`,
          mixBlendMode: 'screen',
          opacity: amount * 0.55,
        }}
      >
        <AbsoluteFill style={{filter: 'sepia(1) saturate(6) hue-rotate(150deg)', opacity: 0.5}}>
          {children}
        </AbsoluteFill>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
