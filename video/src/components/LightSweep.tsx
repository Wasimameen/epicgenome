import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

/** A single specular pass — used once, on the logo landing, and never repeated. */
export const LightSweep: React.FC<{startAt: number; durationInFrames?: number}> = ({
  startAt,
  durationInFrames = 22,
}) => {
  const frame = useCurrentFrame();
  const local = frame - startAt;
  if (local < 0 || local > durationInFrames) return null;

  const x = interpolate(local, [0, durationInFrames], [-60, 160]);
  const fade = interpolate(local, [0, 4, durationInFrames - 6, durationInFrames], [0, 1, 1, 0]);

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: fade * 0.26, mixBlendMode: 'screen'}}>
      <AbsoluteFill
        style={{
          background: `linear-gradient(104deg, transparent ${x - 9}%, rgba(255,255,255,0.85) ${x}%, transparent ${
            x + 9
          }%)`,
        }}
      />
    </AbsoluteFill>
  );
};
