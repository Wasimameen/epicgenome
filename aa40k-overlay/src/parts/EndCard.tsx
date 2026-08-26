/**
 * The signature end card.
 *
 * If the real artwork is at `assets-in/endcard.*` it is *placed* — no type is
 * redrawn over it and nothing is cropped into it (9:16 fills the frame, 16:9
 * centres the portrait card on its own colour). Otherwise the card is drawn
 * from the reference by `EndCardArt`, which is sharp at any resolution.
 *
 * Either way it gets the same treatment: a short settle onto the plate already
 * underneath, then a slow push that comes to a complete stop before the last
 * half second — alive when it lands, dead still when it holds.
 *
 * It arrives on the same colour the "GET PAID." plate is painted in, so the
 * plate becoming the card is a dissolve of the content only; the background
 * never changes and the join cannot be seen.
 */

import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {EASE, mix, useRamp} from '../overlays/lib';
import {EndCardArt, EndCardFinePrint} from './EndCardArt';
import {BRAND} from '../brand.generated';
import type {Layout} from '../theme';


export const SignatureEndCard: React.FC<{
  readonly layout: Layout;
  readonly at: number;
  /** seconds at which all motion must have stopped */
  readonly stillFrom: number;
  /** the card's fine print, newline-separated. Comes from the `disclaimer`
   *  prop, so the wording is changeable without touching a scene. Ignored when
   *  supplied artwork is used — that carries its own. */
  readonly finePrint: string;
}> = ({layout, at, stillFrom, finePrint}) => {
  // arrival: a short scale/fade settle onto the plate already underneath
  const arrive = useRamp(at, 0.5, EASE.expoOut);
  // and then a long, slow push that finishes before the hold does
  const push = useRamp(at + 0.2, Math.max(0.6, stillFrom - at - 0.2), EASE.smooth);

  if (arrive <= 0.002) return null;

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
        {BRAND.endCard ? (
          <Img
            src={staticFile(BRAND.endCard)}
            style={
              fill
                ? {width: '100%', height: '100%', objectFit: 'cover'}
                : {height: '100%', width: 'auto', objectFit: 'contain'}
            }
          />
        ) : (
          <AbsoluteFill>
            <EndCardArt layout={layout} bg={BRAND.endCardBg} />
            <EndCardFinePrint
              layout={layout}
              lines={finePrint.split('\n').map((l) => l.trim()).filter(Boolean)}
            />
          </AbsoluteFill>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
