/**
 * AWESOME ATTORNEYS.
 *
 * Typographic by default — "AWESOME" white 800 over "ATTORNEYS" gold 800,
 * tracked +0.12em. If `assets-in/logo.svg|png` was supplied, `prepare-assets`
 * records it in `brand.generated.ts` and it is used instead at the same height.
 *
 * The light scan is a duplicate of the type in a brighter tint, revealed by a
 * narrow moving gradient mask, so the highlight lands inside the glyphs and is
 * made of real pixels — no `mix-blend-mode`, nothing that would interact with
 * the footage underneath.
 */

import React from 'react';
import {Img, staticFile} from 'remotion';
import {EASE, MaskReveal, useRamp, rgba} from '../overlays/lib';
import {BRAND} from '../brand.generated';
import {TYPE_BASE} from '../font';
import {TRACKING, textShadow, type Tone} from '../theme';

const Scan: React.FC<{
  readonly at: number;
  readonly children: React.ReactNode;
}> = ({at, children}) => {
  const p = useRamp(at, 0.75, EASE.smooth);
  if (p <= 0 || p >= 1) return null;
  const a = p * 150 - 25;
  const mask = `linear-gradient(105deg, rgba(0,0,0,0) ${a - 16}%, #000 ${a}%, rgba(0,0,0,0) ${
    a + 16
  }%)`;
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        WebkitMaskImage: mask,
        maskImage: mask,
        WebkitMaskSize: '100% 100%',
        maskSize: '100% 100%',
        pointerEvents: 'none',
        opacity: Math.sin(Math.PI * p),
      }}
    >
      {children}
    </div>
  );
};

export const Wordmark: React.FC<{
  readonly at: number;
  readonly size: number;
  readonly white: string;
  readonly gold: string;
  readonly tone: Tone;
  readonly stack?: boolean;
  /** set false on the ink end card, where there is no footage to fight */
  readonly shadow?: boolean;
  readonly scanAt?: number;
}> = ({at, size, white, gold, tone, stack = true, shadow = true, scanAt}) => {
  const p = useRamp(at, 0.5, EASE.expoOut);

  if (BRAND.logo) {
    return (
      <MaskReveal progress={p} direction="up" softness={10}>
        <Img
          src={staticFile(BRAND.logo)}
          style={{
            height: size * (stack ? 2.4 : 1.3),
            width: 'auto',
            transform: `translateY(${(1 - p) * 26}px) scale(${0.95 + 0.05 * p})`,
          }}
        />
      </MaskReveal>
    );
  }

  const base: React.CSSProperties = {
    ...TYPE_BASE,
    fontSize: size,
    fontWeight: 800,
    letterSpacing: TRACKING.wordmark,
    textTransform: 'uppercase',
    lineHeight: 1.06,
    textShadow: shadow ? textShadow(tone) : undefined,
  };

  const content = (whiteCol: string, goldCol: string) => (
    <div style={{display: stack ? 'block' : 'flex', gap: size * 0.34, textAlign: 'center'}}>
      <div style={{...base, color: whiteCol}}>Awesome</div>
      <div style={{...base, color: goldCol}}>Attorneys</div>
    </div>
  );

  return (
    <MaskReveal progress={p} direction="up" softness={10}>
      <div
        style={{
          position: 'relative',
          transform: `translateY(${(1 - p) * 30}px) scale(${0.94 + 0.06 * p})`,
        }}
      >
        {content(white, gold)}
        {/* the scan copy is white on white, so the gold word momentarily
            catches the light as the band crosses it */}
        {scanAt === undefined ? null : (
          <Scan at={scanAt}>{content('#FFFFFF', rgba('#FFFFFF', 0.96))}</Scan>
        )}
      </div>
    </MaskReveal>
  );
};
