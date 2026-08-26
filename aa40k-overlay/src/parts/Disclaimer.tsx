/**
 * The disclaimer line, pinned to the bottom safe area. Text comes from the
 * `disclaimer` prop so the wording can be changed without touching a scene.
 */

import React from 'react';
import {EASE, MaskReveal, useRamp} from '../overlays/lib';
import {TYPE_BASE} from '../font';
import {TRACKING, textShadow, type Tone} from '../theme';

export const Disclaimer: React.FC<{
  readonly at: number;
  readonly text: string;
  readonly size: number;
  readonly color: string;
  readonly tone: Tone;
  /** on an ink card there is no footage to fight, so the shadow comes off */
  readonly shadow?: boolean;
  readonly maxWidth: number;
}> = ({at, text, size, color, tone, shadow = false, maxWidth}) => {
  const p = useRamp(at, 0.6, EASE.expoOut);
  if (p <= 0) return null;
  return (
    <MaskReveal progress={p} direction="up" softness={14}>
      <div
        style={{
          ...TYPE_BASE,
          whiteSpace: 'normal',
          maxWidth,
          textAlign: 'center',
          fontSize: size,
          fontWeight: 500,
          letterSpacing: TRACKING.label,
          textTransform: 'uppercase',
          lineHeight: 1.45,
          color,
          textShadow: shadow ? textShadow(tone) : undefined,
          transform: `translateY(${(1 - p) * 16}px)`,
        }}
      >
        {text}
      </div>
    </MaskReveal>
  );
};
