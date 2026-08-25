import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, random, useCurrentFrame} from 'remotion';

/** Horizontal motion streaks — sells lateral speed behind a moving subject. */
export const SpeedLines: React.FC<{
  startAt: number;
  durationInFrames: number;
  color?: string;
  count?: number;
}> = ({startAt, durationInFrames, color = '#ffffff', count = 26}) => {
  const frame = useCurrentFrame();
  const local = frame - startAt;

  const lines = useMemo(
    () =>
      new Array(count).fill(0).map((_, i) => ({
        y: random(`sly-${i}`) * 100,
        len: 18 + random(`sll-${i}`) * 46,
        speed: 2.2 + random(`sls-${i}`) * 3.4,
        offset: random(`slo-${i}`) * 140,
        w: 2 + random(`slw-${i}`) * 5,
      })),
    [count],
  );

  if (local < 0 || local > durationInFrames) return null;
  const fade = interpolate(
    local,
    [0, 6, durationInFrames - 8, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: fade * 0.5, mixBlendMode: 'screen'}}>
      {lines.map((l, i) => {
        const x = 130 - ((local * l.speed + l.offset) % 260);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${x}%`,
              top: `${l.y}%`,
              width: `${l.len}%`,
              height: l.w,
              background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
              filter: 'blur(1px)',
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
