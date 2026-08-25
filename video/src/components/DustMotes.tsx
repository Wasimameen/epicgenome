import React, {useMemo} from 'react';
import {AbsoluteFill, random, useCurrentFrame} from 'remotion';

/**
 * Slow airborne particulate. Present in every scene at low opacity — it is the
 * single cheapest thing that stops flat vector work reading as a slide deck.
 */
export const DustMotes: React.FC<{count?: number; seed?: string; opacity?: number}> = ({
  count = 44,
  seed = 'd',
  opacity = 0.5,
}) => {
  const frame = useCurrentFrame();

  const motes = useMemo(
    () =>
      new Array(count).fill(0).map((_, i) => ({
        x: random(`mx-${seed}-${i}`) * 100,
        y: random(`my-${seed}-${i}`) * 100,
        r: 1 + random(`mr-${seed}-${i}`) * 3.4,
        drift: 0.006 + random(`md-${seed}-${i}`) * 0.02,
        sway: 6 + random(`ms-${seed}-${i}`) * 22,
        rate: 0.006 + random(`mt-${seed}-${i}`) * 0.018,
        o: 0.16 + random(`mo-${seed}-${i}`) * 0.5,
      })),
    [count, seed],
  );

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity, mixBlendMode: 'screen'}}>
      {motes.map((m, i) => {
        const y = (m.y - frame * m.drift * 3 + 200) % 110;
        const x = m.x + Math.sin(frame * m.rate + i) * (m.sway / 20);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${x}%`,
              top: `${y}%`,
              width: m.r * 2,
              height: m.r * 2,
              borderRadius: '50%',
              background: 'rgba(255,232,190,0.9)',
              filter: `blur(${m.r * 0.7}px)`,
              opacity: m.o,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
