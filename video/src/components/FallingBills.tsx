import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, random, useCurrentFrame} from 'remotion';
import {Banknote} from './Banknote';

/**
 * Cash fall with three depth bands. Near bills are larger, faster and blurred;
 * far bills drift. Each note tumbles on its own axis so the field never pulses
 * in unison, which is what makes a particle system look canned.
 */
export const FallingBills: React.FC<{
  startAt?: number;
  count?: number;
  /** Seed suffix so two scenes using bills do not share an identical pattern. */
  seed?: string;
  intensity?: number;
}> = ({startAt = 0, count = 26, seed = 'a', intensity = 1}) => {
  const frame = useCurrentFrame();
  const local = frame - startAt;

  const bills = useMemo(
    () =>
      new Array(count).fill(0).map((_, i) => {
        const depth = random(`bd-${seed}-${i}`); // 0 = far, 1 = near
        return {
          depth,
          x: random(`bx-${seed}-${i}`) * 112 - 6,
          delay: random(`bt-${seed}-${i}`) * 150,
          fall: 190 + depth * 240,
          spin: (random(`bs-${seed}-${i}`) - 0.5) * 900,
          sway: 3 + random(`bw-${seed}-${i}`) * 9,
          swayRate: 0.02 + random(`br-${seed}-${i}`) * 0.05,
          width: 90 + depth * 210,
          tilt: random(`bl-${seed}-${i}`) * 360,
        };
      }),
    [count, seed],
  );

  if (local < 0) return null;

  return (
    <AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden'}}>
      {bills.map((b, i) => {
        const t = ((local + b.delay) % 240) / 240;
        const y = interpolate(t, [0, 1], [-18, 118]);
        const sway = Math.sin((local + b.delay) * b.swayRate) * b.sway;
        const rot = b.tilt + t * b.spin;
        // Bills tumble edge-on, so scaleX through zero reads as a real flip.
        const flip = Math.cos((rot * Math.PI) / 180);

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${b.x + sway}%`,
              top: `${y}%`,
              transform: `rotate(${rot * 0.35}deg) scaleX(${Math.max(0.12, Math.abs(flip))})`,
              filter: b.depth > 0.72 ? `blur(${(b.depth - 0.72) * 14}px)` : undefined,
              opacity: (0.5 + b.depth * 0.5) * intensity,
            }}
          >
            <Banknote width={b.width} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
