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
import {Wordmark} from '../parts/Wordmark';
import {Pill} from '../parts/Pill';
import {Disclaimer} from '../parts/Disclaimer';
import {EASE, MaskReveal, SPRING, mix, useHit, useLocal, useRamp, useSpringAt} from '../overlays/lib';
import {TYPE_BASE} from '../font';
import {BEATS, TOTAL_SEC, t} from '../timing/beats';
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
  const endAt = local(t.end);
  const stillFrom = local(TOTAL_SEC) - 0.5;

  const pMatched = useSpringAt(matchedAt + 0.06, SPRING.overshoot, 0.7);
  const pPaid = useSpringAt(paidAt + 0.06, SPRING.overshoot, 0.7);
  /** GET PAID. eases up and shrinks to 70% to become the end-card headline */
  const pSettle = useRamp(urlAt, 0.5, EASE.expoOut);
  const pSettlePrev = useRamp(urlAt + 1 / fps, 0.5, EASE.expoOut);
  const pUrl = useRamp(urlAt + 0.18, 0.5, EASE.expoOut);

  // End-card slots, in units of the card type size so both aspects scale.
  // Chosen so the headline/wordmark/URL/pill stack sits centred on the frame
  // with the disclaimer pinned to the bottom safe area — anchored lower, the
  // card reads bottom-heavy with a dead third above it.
  const slot = {
    paid: -type.card * 1.4,
    wordmark: -type.card * 0.09,
    url: type.card * 0.69,
    pill: type.card * 1.76,
  };

  const onInk = cards;
  const shadow = onInk ? undefined : textShadow(tone);
  // With no plate under it, ink type would vanish into the footage.
  const matchedColor = onInk ? palette.ink : palette.white;
  const paidColor = palette.gold;

  const disclaimerBottom = layout.safe.bottom + layout.height * 0.012;

  // "GET PAID." rising and shrinking into the end card is the one fast move
  // that happens *on* a plate rather than in the 3D stage.
  const settleSpeed = Math.abs(pSettle - pSettlePrev) * Math.abs(slot.paid) * 1.6;

  const endCard = (
    <>
      {/* GET PAID. — slams in centred, then rises and shrinks in place */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: '50%',
          display: 'flex',
          justifyContent: 'center',
          transform: `translateY(${slot.paid * pSettle}px) scale(${mix(1, 0.7, pSettle)})`,
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

      {/* the wordmark */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: '50%',
          display: 'flex',
          justifyContent: 'center',
          transform: `translateY(${slot.wordmark}px)`,
        }}
      >
        <div style={{transform: 'translateY(-50%)'}}>
          <Wordmark
            at={urlAt + 0.1}
            size={type.wordmark * 0.58}
            white={palette.white}
            gold={palette.gold}
            tone={tone}
            stack={false}
            shadow={!onInk}
          />
        </div>
      </div>

      {/* the URL */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: '50%',
          display: 'flex',
          justifyContent: 'center',
          transform: `translateY(${slot.url}px)`,
        }}
      >
        <div style={{transform: 'translateY(-50%)'}}>
          <MaskReveal progress={pUrl} direction="up" softness={12}>
            <div
              style={{
                ...TYPE_BASE,
                fontSize: type.url,
                fontWeight: 700,
                letterSpacing: '-0.01em',
                lineHeight: 1,
                textShadow: shadow,
                transform: `translateY(${(1 - pUrl) * 22}px)`,
              }}
            >
              <span style={{color: palette.white}}>Awesome</span>
              <span style={{color: palette.gold}}>Attorneys</span>
              <span style={{color: palette.white}}>.com</span>
            </div>
          </MaskReveal>
        </div>
      </div>

      {/* the call to action */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: '50%',
          display: 'flex',
          justifyContent: 'center',
          transform: `translateY(${slot.pill}px)`,
        }}
      >
        <div style={{transform: 'translateY(-50%)'}}>
          <Pill
            at={urlAt + 0.45}
            text="Get Matched"
            size={type.pill}
            bg={palette.gold}
            fg={palette.ink}
            stillFrom={stillFrom}
          />
        </div>
      </div>
    </>
  );

  const disclaimer = (
    <div
      style={{
        position: 'absolute',
        left: layout.safe.left,
        right: layout.safe.right,
        bottom: disclaimerBottom,
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      <Disclaimer
        at={endAt}
        text={disclaimerText}
        size={type.disclaimer}
        color={palette.steel}
        tone={tone}
        shadow={!onInk}
        maxWidth={layout.width - layout.safe.left - layout.safe.right}
      />
    </div>
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
          {disclaimer}
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

      {/* card #3 — ink plate from above; it never leaves, it becomes the end card */}
      <CardPlate
        layout={layout}
        color={palette.ink}
        enterAt={paidAt}
        enterDur={0.28}
        entry="slam-down"
        speedHint={settleSpeed}
      >
        {endCard}
        {disclaimer}
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
