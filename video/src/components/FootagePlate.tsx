import React from 'react';
import {AbsoluteFill, interpolate, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import {useTransparent} from '../alpha';
import {THEME} from '../theme';

/**
 * Live-action plate, graded to sit inside the reel's palette.
 *
 * The supplied Capitol footage is bright daylight on blue sky, which would blow
 * a hole in a dark cut. It is crushed, desaturated and warmed so it reads as
 * the same world as the vector scenes, then pushed in slowly.
 */
export const FootagePlate: React.FC<{
  src: string;
  startFrom?: number;
  durationInFrames: number;
  push?: [number, number];
  opacity?: number;
}> = ({src, startFrom = 0, durationInFrames, push = [1.08, 1.2], opacity = 0.7}) => {
  const transparent = useTransparent();
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, durationInFrames], push, {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Live plates are ground, not graphics — omitted from the alpha pass so the
  // titles can be laid over the client's own footage instead.
  if (transparent) return null;

  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: THEME.ink}}>
      <AbsoluteFill style={{transform: `scale(${scale})`, transformOrigin: '50% 42%'}}>
        <OffthreadVideo
          src={staticFile(src)}
          startFrom={startFrom}
          muted
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            filter: 'saturate(0.28) contrast(1.22) brightness(0.52) sepia(0.42)',
            opacity,
          }}
        />
      </AbsoluteFill>
      {/* Warm the highlights back up so the grade does not read as grey. */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, rgba(216,178,106,0.22) 0%, transparent 45%, rgba(8,7,10,0.85) 100%)`,
          mixBlendMode: 'multiply',
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 60% 40% at 50% 30%, rgba(232,184,75,0.28) 0%, transparent 70%)`,
          mixBlendMode: 'screen',
        }}
      />
    </AbsoluteFill>
  );
};
