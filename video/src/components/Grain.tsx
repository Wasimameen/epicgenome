import React, {useMemo} from 'react';
import {AbsoluteFill, random, useCurrentFrame} from 'remotion';

/**
 * Deterministic film grain. The pattern is regenerated every `cycle` frames so
 * it shimmers like real stock rather than sitting frozen on top of the image.
 */
export const Grain: React.FC<{opacity?: number; cycle?: number}> = ({
  opacity = 0.10,
  cycle = 3,
}) => {
  const frame = useCurrentFrame();
  const seed = Math.floor(frame / cycle);

  const specks = useMemo(() => {
    return new Array(520).fill(0).map((_, i) => ({
      x: random(`gx-${seed}-${i}`) * 100,
      y: random(`gy-${seed}-${i}`) * 100,
      r: 0.4 + random(`gr-${seed}-${i}`) * 1.1,
      o: 0.25 + random(`go-${seed}-${i}`) * 0.75,
    }));
  }, [seed]);

  return (
    <AbsoluteFill style={{opacity, mixBlendMode: 'overlay', pointerEvents: 'none'}}>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{width: '100%', height: '100%'}}>
        {specks.map((s, i) => (
          <circle key={i} cx={s.x} cy={s.y} r={s.r * 0.085} fill="#fff" opacity={s.o} />
        ))}
      </svg>
    </AbsoluteFill>
  );
};
