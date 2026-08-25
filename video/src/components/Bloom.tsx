import React from 'react';
import {AbsoluteFill} from 'remotion';

/**
 * Cheap optical bloom: the subtree is drawn twice, the lower copy blurred and
 * screened back over itself so highlights spill the way a real lens does.
 * Doubles the cost of whatever it wraps, so wrap scenes, never the whole reel.
 */
export const Bloom: React.FC<{
  strength?: number;
  radius?: number;
  children: React.ReactNode;
}> = ({strength = 0.5, radius = 26, children}) => (
  <AbsoluteFill>
    <AbsoluteFill>{children}</AbsoluteFill>
    <AbsoluteFill
      style={{
        filter: `blur(${radius}px) brightness(1.25) saturate(1.15)`,
        opacity: strength,
        mixBlendMode: 'screen',
        pointerEvents: 'none',
      }}
    >
      {children}
    </AbsoluteFill>
  </AbsoluteFill>
);
