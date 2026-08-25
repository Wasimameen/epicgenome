import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

/** Two-frame white blowout. Hides a hard cut and punctuates an impact. */
export const FlashCut: React.FC<{at: number; frames?: number; color?: string}> = ({
  at,
  frames = 4,
  color = '#fff',
}) => {
  const frame = useCurrentFrame();
  const local = frame - at;
  if (local < 0 || local > frames) return null;

  const o = interpolate(local, [0, 1, frames], [0, 0.92, 0], {extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{backgroundColor: color, opacity: o, pointerEvents: 'none'}} />;
};
