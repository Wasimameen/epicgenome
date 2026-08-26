/**
 * The signature end card.
 *
 * This is a supplied brand asset, so it is placed rather than rebuilt — no type
 * is redrawn over it and nothing is cropped into it. All it gets is a slow
 * push-in that comes to a complete stop before the last half second, so the
 * card is alive when it lands and dead still when it holds.
 *
 * It arrives on the same maroon the "GET PAID." plate is painted in (sampled
 * from the card itself by `prepare-assets`), so the plate becoming the end card
 * is a dissolve of the *content* only — the background never changes colour and
 * the join is invisible.
 *
 * 9x16 fills the frame. 16x9 centres the portrait card on its own maroon bed
 * rather than cropping a supplied asset.
 */

import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {EASE, mix, useRamp} from '../overlays/lib';
import {BRAND} from '../brand.generated';
import type {Layout} from '../theme';

export const SignatureEndCard: React.FC<{
  readonly layout: Layout;
  readonly at: number;
  /** seconds at which all motion must have stopped */
  readonly stillFrom: number;
}> = ({layout, at, stillFrom}) => {
  // arrival: a short scale/fade settle onto the plate already underneath
  const arrive = useRamp(at, 0.5, EASE.expoOut);
  // and then a long, slow push that finishes before the hold does
  const push = useRamp(at + 0.2, Math.max(0.6, stillFrom - at - 0.2), EASE.smooth);

  if (arrive <= 0.002 || !BRAND.endCard) return null;

  const scale = mix(1.055, 1, push) * mix(1.03, 1, arrive);
  const fill = layout.aspect === '9x16';

  return (
    <AbsoluteFill style={{backgroundColor: BRAND.endCardBg, overflow: 'hidden'}}>
      <AbsoluteFill
        style={{
          opacity: arrive,
          alignItems: 'center',
          justifyContent: 'center',
          transform: `scale(${scale})`,
          transformOrigin: '50% 50%',
        }}
      >
        <Img
          src={staticFile(BRAND.endCard)}
          style={
            fill
              ? {width: '100%', height: '100%', objectFit: 'cover'}
              : {height: '100%', width: 'auto', objectFit: 'contain'}
          }
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
