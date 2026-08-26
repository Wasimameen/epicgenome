/**
 * Beat 2 — knowing. "That's their opening position — not a legal finding."
 *
 * The turn of the whole piece is the word "opening": the camera reverses into
 * a push-in, OPENING flies into the upper third, and the gold strike sweeps
 * through "40% AT FAULT" (owned by Beat1, which is still on screen). The red
 * desaturates, the stamp drops and tilts, and the group tumbles out of the
 * world.
 *
 * `Beat2` is the part that lives in the 3D world. `Beat2Card` is the flat card
 * beat on "not" — it sits above the stage, and with `cards: false` it plays the
 * same type over the footage with shadows instead of on a plate.
 */

import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Posed} from '../stage/Word';
import {CardPlate} from '../stage/CardPlate';
import {EASE, MaskReveal, SPRING, useHit, useLocal, useRamp, useSpringAt} from '../overlays/lib';
import {TYPE_BASE} from '../font';
import {BEATS, t} from '../timing/beats';
import {TRACKING, textShadow} from '../theme';
import type {BeatProps} from '../types';

/* ------------------------------------------------------------------ *
 * In the world
 * ------------------------------------------------------------------ */

export const Beat2: React.FC<BeatProps> = ({type, palette, tone, poses}) => {
  const h = useHit(BEATS.b2.start);

  const pOpening = useSpringAt(h(t.opening), SPRING.overdamped, 0.55);
  // POSITION lands four frames behind its own cue — secondary weight *and*
  // secondary timing, so "opening" stays the point of the line.
  const pPosition = useSpringAt(h(t.position, -4), SPRING.overdamped, 0.5);
  const pOut = useRamp(h(t.not), 0.4, EASE.expoIn);

  return (
    <Posed
      pose={poses.opening}
      enterAt={h(t.opening)}
      enterDur={0.6}
      enterScaleFrom={0.9}
      exitAt={h(t.not)}
      exitKind="lift"
      exitDur={0.4}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: type.heroWord * 0.3,
        }}
      >
        <MaskReveal progress={pOpening} direction="up" softness={10}>
          <div
            style={{
              ...TYPE_BASE,
              fontSize: type.heroWord,
              fontWeight: 800,
              letterSpacing: TRACKING.hero,
              textTransform: 'uppercase',
              lineHeight: 1,
              color: palette.white,
              textShadow: textShadow(tone),
              transform: `translateY(${(1 - pOpening) * 40}px) scale(${
                0.93 + 0.07 * pOpening
              })`,
            }}
          >
            Opening
          </div>
        </MaskReveal>

        <MaskReveal progress={pPosition} direction="up" softness={12}>
          <div
            style={{
              ...TYPE_BASE,
              fontSize: type.secondaryWord,
              fontWeight: 500,
              letterSpacing: TRACKING.label,
              textTransform: 'uppercase',
              lineHeight: 1,
              color: palette.steel,
              textShadow: textShadow(tone),
              transform: `translateY(${(1 - pPosition) * 26}px)`,
              opacity: 1 - pOut * 0.5,
            }}
          >
            Position
          </div>
        </MaskReveal>
      </div>
    </Posed>
  );
};

/* ------------------------------------------------------------------ *
 * Card beat #1 — "NOT / A LEGAL FINDING"
 * ------------------------------------------------------------------ */

export const Beat2Card: React.FC<BeatProps> = ({layout, type, palette, tone, cards}) => {
  const h = useHit(BEATS.b2.start);
  const local = useLocal(BEATS.b2.start);

  const enterAt = h(t.not);
  const exitAt = local(BEATS.b2.end) - 0.3;

  const pNot = useSpringAt(enterAt + 0.1, SPRING.overdamped, 0.5);
  const pLegal = useRamp(h(t.legal), 0.42, EASE.expoOut);
  const pRule = useRamp(h(t.finding), 0.4, EASE.expoOut);
  const pOut = useRamp(exitAt, 0.3, EASE.expoIn);

  const onPlate = cards;
  const shadow = onPlate ? undefined : textShadow(tone);

  const body = (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        // the words leave with the plate
        transform: `translateX(${pOut * layout.width * 0.35}px)`,
      }}
    >
      {/* NOT, with its echo ghost behind */}
      <div style={{position: 'relative'}}>
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
          <div
            style={{
              ...TYPE_BASE,
              fontSize: type.cardHero,
              fontWeight: 800,
              letterSpacing: TRACKING.hero,
              textTransform: 'uppercase',
              lineHeight: 1,
              color: palette.gold,
              opacity: 0.1 * pNot,
              transform: `translateX(${-26 * pNot}px) scale(2.2)`,
            }}
          >
            Not
          </div>
        </div>
        <MaskReveal
          progress={pNot}
          direction="up"
          softness={9}
          style={{position: 'relative', zIndex: 1}}
        >
          <div
            style={{
              ...TYPE_BASE,
              fontSize: type.cardHero,
              fontWeight: 800,
              letterSpacing: TRACKING.hero,
              textTransform: 'uppercase',
              lineHeight: 1,
              color: palette.gold,
              textShadow: shadow,
              transform: `translateY(${(1 - pNot) * 44}px) scale(${0.9 + 0.1 * pNot})`,
            }}
          >
            Not
          </div>
        </MaskReveal>
      </div>

      <div style={{height: type.cardHero * 0.34}} />

      {/* A LEGAL FINDING, with the rule drawn under the last word */}
      <MaskReveal progress={pLegal} direction="up" softness={12}>
        <div
          style={{
            ...TYPE_BASE,
            fontSize: type.cardSub,
            fontWeight: 500,
            letterSpacing: TRACKING.label,
            textTransform: 'uppercase',
            lineHeight: 1.1,
            color: palette.white,
            textShadow: shadow,
            transform: `translateY(${(1 - pLegal) * 20}px)`,
            display: 'flex',
            gap: type.cardSub * 0.42,
            // The rule under FINDING hangs below the text box; without this the
            // wipe mask (sized to the box) clipped it away entirely.
            paddingBottom: type.cardSub * 0.5,
          }}
        >
          <span>A</span>
          <span>Legal</span>
          <span style={{position: 'relative', display: 'inline-block'}}>
            Finding
            <div
              style={{
                position: 'absolute',
                left: 0,
                right: 0,
                bottom: -type.cardSub * 0.34,
                height: layout.strokeThin,
                borderRadius: layout.strokeThin,
                backgroundColor: palette.gold,
                transform: `scaleX(${pRule})`,
                transformOrigin: 'left center',
              }}
            />
          </span>
        </div>
      </MaskReveal>
    </div>
  );

  if (!onPlate) {
    // No plate: the same type, over the footage, carrying its shadows.
    if (pNot <= 0 || pOut >= 1) return null;
    return (
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        {body}
      </AbsoluteFill>
    );
  }

  return (
    <CardPlate
      layout={layout}
      color={palette.ink}
      enterAt={enterAt}
      enterDur={0.25}
      entry="wipe-left"
      exitAt={exitAt}
      exitDur={0.3}
      exit="wipe-right"
    >
      {body}
    </CardPlate>
  );
};
