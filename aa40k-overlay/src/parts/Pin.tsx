/**
 * The location pin. Flat, single-weight, no illustration — a teardrop outline
 * with a solid centre. It drops in and takes a 2-frame settle at the bottom.
 */

import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {EASE, useRamp} from '../overlays/lib';
import {vectorShadow, type Tone} from '../theme';

export const Pin: React.FC<{
  readonly at: number;
  readonly size: number;
  readonly color: string;
  readonly tone: Tone;
  readonly dropFrom?: number;
}> = ({at, size, color, tone, dropFrom}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const drop = dropFrom ?? size * 2.2;

  // Fall, then a 2-frame squash-and-release at the bottom.
  const p = useRamp(at, 0.42, EASE.expoIn);
  const land = at + 0.42;
  const settle = interpolate(
    frame,
    [land * fps, land * fps + 2, land * fps + 8],
    [1, 0.9, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.expoOut},
  );
  const opacity = useRamp(at, 0.16, EASE.smooth);
  if (opacity <= 0) return null;

  const w = size;
  const h = size * 1.34;

  return (
    <svg
      width={w}
      height={h}
      viewBox="0 0 100 134"
      style={{
        overflow: 'visible',
        filter: vectorShadow(tone),
        opacity,
        transform: `translateY(${(1 - p) * -drop}px) scaleY(${settle}) scaleX(${
          1 + (1 - settle) * 0.6
        })`,
        transformOrigin: '50% 100%',
      }}
    >
      <path
        d="M50 2 C25 2 6 21 6 46 C6 78 40 108 47 129 a3.4 3.4 0 0 0 6 0 C60 108 94 78 94 46 C94 21 75 2 50 2 Z"
        fill="none"
        stroke={color}
        strokeWidth={10}
        strokeLinejoin="round"
      />
      <circle cx={50} cy={45} r={16} fill={color} />
    </svg>
  );
};
