/**
 * The call-to-action pill: solid gold, ink text, scales in and breathes at
 * 0.6 Hz. The breath stops before the last 0.5s so the end card comes to a
 * complete stop (spec §11.4).
 */

import React from 'react';
import {EASE, useBreath, useRamp, useSpringAt, SPRING, mix} from '../overlays/lib';
import {TYPE_BASE} from '../font';
import {TRACKING} from '../theme';

export const Pill: React.FC<{
  readonly at: number;
  readonly text: string;
  readonly size: number;
  readonly bg: string;
  readonly fg: string;
  /** seconds at which the breath eases to a stop */
  readonly stillFrom: number;
}> = ({at, text, size, bg, fg, stillFrom}) => {
  const p = useSpringAt(at, SPRING.overdamped, 0.55);
  const breath = useBreath(0.6);
  const damp = 1 - useRamp(stillFrom - 0.7, 0.7, EASE.smooth);
  const s = mix(0.88, 1, p) * (1 + 0.018 * (breath - 0.5) * 2 * damp);
  if (p <= 0.001) return null;

  return (
    <div
      style={{
        backgroundColor: bg,
        borderRadius: size * 2,
        padding: `${size * 0.62}px ${size * 1.5}px`,
        transform: `scale(${s})`,
        transformOrigin: 'center',
        opacity: p,
      }}
    >
      <div
        style={{
          ...TYPE_BASE,
          fontSize: size,
          fontWeight: 800,
          letterSpacing: TRACKING.label,
          textTransform: 'uppercase',
          lineHeight: 1,
          color: fg,
        }}
      >
        {text}
      </div>
    </div>
  );
};
