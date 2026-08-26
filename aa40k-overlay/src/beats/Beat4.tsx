/**
 * Beat 4 — decisive. "Get Matched. Get Paid. AwesomeAttorneys dot com."
 *
 * Two card slams back to back with nothing moving between them, then the ink
 * plate stays and becomes the end card. Both slams use the overshoot spring
 * (the second and third of the only three in the piece) and a 1-frame frame
 * punch.
 *
 * Everything here is flat and sits above the 3D stage — a card is a cut, not a
 * camera move. With `cards: false` the plates are gone, the ink type is
 * re-coloured so it still reads over footage, and the end card gains the bottom
 * scrim gradient so the URL survives any grade underneath.
 *
 * The last half second is completely still: the pill's breath is damped to a
 * stop before it (spec §11.4).
 */

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {CardPlate, ScrimGradient} from '../stage/CardPlate';
import {SignatureEndCard} from '../parts/EndCard';
import {EASE, MaskReveal, SPRING, mix, useHit, useLocal, useRamp, useSpringAt} from '../overlays/lib';
import {BRAND} from '../brand.generated';
import {TYPE_BASE} from '../font';
import {BEATS, TOTAL_SEC, t} from '../timing/beats';
import {END_CARD_AT} from '../timing/backdrops';
import {TRACKING, textShadow} from '../theme';
import type {BeatProps} from '../types';

/** "GET" over "MATCHED." — stacked so the hero size survives the safe area. */
const SlamType: React.FC<{
  readonly lines: [string, string];
  readonly size: number;
  readonly color: string;
  readonly p: number;
  readonly shadow?: string;
  readonly echoColor?: string;
  readonly echoOpacity?: number;
}> = ({lines, size, color, p, shadow, echoColor, echoOpacity = 0.06}) => {
  const type: React.CSSProperties = {
    ...TYPE_BASE,
    fontSize: size,
    fontWeight: 800,
    letterSpacing: TRACKING.hero,
    textTransform: 'uppercase',
    lineHeight: 0.96,
    textAlign: 'center',
  };
  return (
    <div style={{position: 'relative'}}>
      {echoColor ? (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {/* The ghost is stacked exactly like the live type, at 1.9x — set on
              one line it read as a different, half-cropped word rather than an
              echo of the lockup. */}
          <div
            style={{
              ...type,
              color: echoColor,
              opacity: echoOpacity * p,
              transform: `translateX(${-24 * p}px) scale(1.9)`,
            }}
          >
            <div>{lines[0]}</div>
            <div>{lines[1]}</div>
          </div>
        </div>
      ) : null}
      <MaskReveal
        progress={p}
        direction="up"
        softness={8}
        style={{position: 'relative', zIndex: 1}}
      >
        <div
          style={{
            ...type,
            color,
            textShadow: shadow,
            transform: `translateY(${(1 - p) * 52}px) scale(${mix(0.88, 1, p)})`,
          }}
        >
          <div>{lines[0]}</div>
          <div>{lines[1]}</div>
        </div>
      </MaskReveal>
    </div>
  );
};

export const Beat4: React.FC<BeatProps> = ({
  layout,
  type,
  palette,
  tone,
  cards,
  disclaimer: disclaimerText,
}) => {
  const {fps} = useVideoConfig();
  const h = useHit(BEATS.b4.start);
  const local = useLocal(BEATS.b4.start);

  const matchedAt = h(t.getMatched);
  const paidAt = h(t.getPaid);
  const urlAt = h(t.url);
  const stillFrom = local(TOTAL_SEC) - 0.5;

  /**
   * The signature card *is* the close: "GET PAID." lifts away and the card
   * settles onto the plate it was already sitting on. Supplied artwork is used
   * when it exists, otherwise the card is drawn (EndCardArt) — this beat
   * behaves identically either way.
   */
  const signatureAt = local(END_CARD_AT);

  const pMatched = useSpringAt(matchedAt + 0.06, SPRING.overshoot, 0.7);
  const pPaid = useSpringAt(paidAt + 0.06, SPRING.overshoot, 0.7);
  /** "GET PAID." lifts clean away as the signature card takes over */
  const pLift = useRamp(signatureAt, 0.4, EASE.expoIn);
  const pLiftPrev = useRamp(signatureAt + 1 / fps, 0.4, EASE.expoIn);

  const onInk = cards;
  const shadow = onInk ? undefined : textShadow(tone);
  // With no plate under it, ink type would vanish into the footage.
  const matchedColor = onInk ? palette.ink : palette.white;
  const paidColor = palette.gold;

  /**
   * The last plate is painted in the end card's own background colour (sampled
   * from the card by `prepare-assets`), so the plate becoming the card is a
   * dissolve of the content only — the background never changes and the join
   * cannot be seen.
   */
  const plateColor = BRAND.endCardBg;

  // "GET PAID." moving into or out of the end card is the one fast move that
  // happens *on* a plate rather than in the 3D stage.
  const settleSpeed = Math.abs(pLift - pLiftPrev) * layout.height * 0.14 * 1.6;

  const paid = (
    /* GET PAID. — slams in centred, then lifts clean away for the card */
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: '50%',
        display: 'flex',
        justifyContent: 'center',
        opacity: 1 - pLift,
        transform: `translateY(${-layout.height * 0.14 * pLift}px) scale(${mix(1, 0.94, pLift)})`,
      }}
    >
      <div style={{transform: 'translateY(-50%)'}}>
        <SlamType
          lines={['Get', 'Paid.']}
          size={type.card}
          color={paidColor}
          p={pPaid}
          shadow={shadow}
          echoColor={onInk ? palette.gold : undefined}
          echoOpacity={0.055}
        />
      </div>
    </div>
  );

  const endCard = (
    <>
      {paid}
      <SignatureEndCard
        layout={layout}
        at={signatureAt}
        stillFrom={stillFrom}
        finePrint={disclaimerText}
      />
    </>
  );

  if (!onInk) {
    return (
      <AbsoluteFill>
        <ScrimGradient layout={layout} scrim={palette.scrim} enterAt={urlAt} />
        <AbsoluteFill>
          {/* GET MATCHED. holds only until GET PAID. takes over */}
          <MatchedOverFootage
            type={type}
            color={matchedColor}
            shadow={shadow}
            p={pMatched}
            outAt={paidAt}
          />
          {endCard}
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill>
      {/* card #2 — gold plate from below */}
      <CardPlate
        layout={layout}
        color={palette.gold}
        enterAt={matchedAt}
        enterDur={0.28}
        entry="slam-up"
      >
        <SlamType
          lines={['Get', 'Matched.']}
          size={type.card}
          color={matchedColor}
          p={pMatched}
          echoColor={palette.ink}
          echoOpacity={0.06}
        />
      </CardPlate>

      {/* card #3 — from above; it never leaves, it becomes the end card */}
      <CardPlate
        layout={layout}
        color={plateColor}
        enterAt={paidAt}
        enterDur={0.28}
        entry="slam-down"
        speedHint={settleSpeed}
      >
        {endCard}
      </CardPlate>
    </AbsoluteFill>
  );
};

/** The `cards: false` stand-in for card #2 — same type, over the footage. */
const MatchedOverFootage: React.FC<{
  type: BeatProps['type'];
  color: string;
  shadow?: string;
  p: number;
  outAt: number;
}> = ({type, color, shadow, p, outAt}) => {
  const out = useRamp(outAt, 0.28, EASE.expoIn);
  if (p <= 0 || out >= 1) return null;
  return (
    <AbsoluteFill
      style={{
        alignItems: 'center',
        justifyContent: 'center',
        opacity: 1 - out,
        transform: `translateY(${-out * 70}px)`,
      }}
    >
      <SlamType lines={['Get', 'Matched.']} size={type.card} color={color} p={p} shadow={shadow} />
    </AbsoluteFill>
  );
};
