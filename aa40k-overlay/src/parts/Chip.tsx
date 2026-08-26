/**
 * A bordered chip — "PHOENIX INJURY ATTORNEY". Gold border, white 500 small
 * caps, no fill, so the footage still reads through it.
 */

import React from 'react';
import {MaskReveal, EASE, useRamp, rgba} from '../overlays/lib';
import {TYPE_BASE} from '../font';
import {TRACKING, labelShadow, vectorShadow, type Tone} from '../theme';

export const Chip: React.FC<{
  readonly at: number;
  readonly text: string;
  readonly size: number;
  readonly borderColor: string;
  readonly textColor: string;
  readonly stroke: number;
  readonly tone: Tone;
}> = ({at, text, size, borderColor, textColor, stroke, tone}) => {
  const p = useRamp(at, 0.42, EASE.expoOut);
  if (p <= 0) return null;
  return (
    <MaskReveal progress={p} direction="right" softness={12}>
      <div
        style={{
          borderStyle: 'solid',
          borderWidth: stroke * 0.6,
          borderColor: rgba(borderColor, 0.9),
          borderRadius: size * 1.1,
          padding: `${size * 0.52}px ${size * 1.05}px`,
          filter: vectorShadow(tone),
          transform: `translateX(${(1 - p) * -26}px) scale(${0.95 + 0.05 * p})`,
        }}
      >
        <div
          style={{
            ...TYPE_BASE,
            fontSize: size,
            fontWeight: 500,
            letterSpacing: TRACKING.label,
            textTransform: 'uppercase',
            lineHeight: 1,
            color: textColor,
            textShadow: labelShadow(tone),
          }}
        >
          {text}
        </div>
      </div>
    </MaskReveal>
  );
};
