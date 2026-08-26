/**
 * The strike line that sweeps through "40% AT FAULT" on the word "opening".
 *
 * Left-to-right, 0.35s, expo-out. It scales from its left edge rather than
 * animating width, so the move stays on the compositor and stays sub-pixel.
 * Its edge speed is reported through `strikeSpeed()` so the beat can feed the
 * stage's motion blur.
 */

import React from 'react';
import {EASE, useRamp, rgba} from '../overlays/lib';
import {vectorShadow, type Tone} from '../theme';

export const STRIKE_DUR = 0.35;

/** px/frame the leading edge travels — feed this to `<Camera3D speedHint>`. */
export const strikeSpeed = (
  sec: number,
  at: number,
  fps: number,
  width: number,
): number => {
  const p = (t: number) =>
    EASE.expoOut(Math.min(1, Math.max(0, (t - at) / STRIKE_DUR)));
  return Math.abs(p(sec) - p(sec - 1 / fps)) * width;
};

export const Strike: React.FC<{
  readonly at: number;
  readonly width: number;
  readonly thickness: number;
  readonly color: string;
  readonly tone: Tone;
  readonly tilt?: number;
  /** px from the container's vertical centre — put it through the mark itself */
  readonly offsetY?: number;
}> = ({at, width, thickness, color, tone, tilt = 0, offsetY = 0}) => {
  const p = useRamp(at, STRIKE_DUR, EASE.expoOut);
  if (p <= 0) return null;
  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        width,
        height: thickness,
        marginLeft: -width / 2,
        marginTop: -thickness / 2 + offsetY,
        transform: `rotate(${tilt}deg) scaleX(${p})`,
        transformOrigin: 'left center',
        backgroundColor: color,
        borderRadius: thickness / 2,
        filter: vectorShadow(tone),
        boxShadow: `0 0 ${thickness * 2.2}px ${rgba(color, 0.45)}`,
      }}
    />
  );
};
