/**
 * The percent stamp: a rounded-rect outline around the "40%".
 *
 * Flat, single-weight, no fill. Its only life during the beat-1 hold is a
 * 0.4 Hz breath on the glow — a real box-shadow in the accent colour, never a
 * backdrop-filter (spec §7).
 */

import React from 'react';
import {useBreath, useRamp, EASE, rgba} from '../overlays/lib';
import {vectorShadow, type Tone} from '../theme';

export const StampBox: React.FC<{
  readonly color: string;
  readonly stroke: number;
  readonly radius: number;
  readonly padX: number;
  readonly padY: number;
  readonly tone: Tone;
  /** when the outline finishes drawing itself in */
  readonly drawAt: number;
  readonly drawDur?: number;
  /** start of the still hold where the glow breathes */
  readonly breathFrom?: number;
  readonly glowStrength?: number;
  readonly children: React.ReactNode;
}> = ({
  color,
  stroke,
  radius,
  padX,
  padY,
  tone,
  drawAt,
  drawDur = 0.35,
  breathFrom,
  glowStrength = 1,
  children,
}) => {
  const p = useRamp(drawAt, drawDur, EASE.expoOut);
  const holding = useRamp(breathFrom ?? 1e6, 0.5, EASE.smooth);
  const breath = useBreath(0.4);
  const glow = holding * (0.35 + 0.65 * breath) * glowStrength;

  return (
    <div
      style={{
        position: 'relative',
        padding: `${padY}px ${padX}px`,
        borderStyle: 'solid',
        borderWidth: stroke,
        borderColor: rgba(color, p),
        borderRadius: radius,
        // The glow is real pixels: an inner and outer shadow in the accent.
        boxShadow:
          glow > 0.002
            ? `0 0 ${28 * glow}px ${rgba(color, 0.42 * glow)}, inset 0 0 ${
                22 * glow
              }px ${rgba(color, 0.16 * glow)}`
            : undefined,
        filter: vectorShadow(tone),
        // grows into place rather than fading in
        transform: `scaleX(${0.965 + 0.035 * p}) scaleY(${0.9 + 0.1 * p})`,
        transformOrigin: 'center',
      }}
    >
      {children}
    </div>
  );
};
