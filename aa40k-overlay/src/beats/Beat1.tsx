/**
 * Beat 1 — deflated. "So an adjuster told you you're forty percent at fault."
 *
 * The heaviest beat: the slowest springs in the piece, one overshoot (the 40%
 * slam) and a long, still hold at the end where only the particles and the
 * stamp glow move.
 *
 * This beat's sequence deliberately outlives its own line. The "40%" group is
 * still in the world through beat 2 — it gets struck through on "opening" and
 * only then tumbles away — so it is owned here, where it was built, rather
 * than handed to the next beat.
 */

import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {Posed, Word} from '../stage/Word';
import {StampBox} from '../parts/StampBox';
import {Strike} from '../parts/Strike';
import {Burst} from '../parts/Particles';
import {STRIKE_AT, TUMBLE_AT, TUMBLE_DUR} from '../stage/flight';
import {
  EASE,
  MaskReveal,
  SPRING,
  useHit,
  useLocal,
  useRamp,
} from '../overlays/lib';
import {TYPE_BASE} from '../font';
import {BEATS, t} from '../timing/beats';
import {TRACKING, textShadow} from '../theme';
import type {BeatProps} from '../types';

export const Beat1: React.FC<BeatProps> = ({layout, type, palette, tone, poses}) => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();
  const h = useHit(BEATS.b1.start);
  const local = useLocal(BEATS.b1.start);

  const strikeAt = local(STRIKE_AT(fps));
  const tumbleAt = local(TUMBLE_AT(fps));

  /* the stamp -------------------------------------------------------- */
  const padX = type.hero * 0.09;
  const padY = type.hero * 0.095;
  const boxH = type.hero + padY * 2 + layout.stroke * 2;
  const gap = type.hero * 0.16;
  const groupH = boxH + gap + type.label;
  // put the strike through the mark, not through the gap below it
  const strikeOffsetY = boxH / 2 - groupH / 2;

  /* the "%" brightens for 6 frames on "percent", then settles --------- */
  const pctFrame = h(t.percent) * fps;
  const pctGlow = interpolate(
    frame,
    [pctFrame, pctFrame + 6, pctFrame + 16],
    [0, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.smooth},
  );

  /* red desaturates to steel once it has been struck through ---------- */
  const desat = useRamp(strikeAt + 0.1, 0.5, EASE.smooth);

  const pFault = useRamp(h(t.fault), 0.45, EASE.expoOut);

  const hero: React.CSSProperties = {
    ...TYPE_BASE,
    fontSize: type.hero,
    fontWeight: 800,
    letterSpacing: TRACKING.hero,
    lineHeight: 1,
  };

  return (
    <>
      {/* "adjuster" — small, low-left, the first thing in the world */}
      <Word
        pose={poses.adjuster}
        text="Adjuster"
        uppercase
        size={type.small}
        weight={500}
        color={palette.white}
        demoteColor={palette.steel}
        tracking={TRACKING.label}
        tone={tone}
        echo
        echoOpacity={0.09}
        wipe="up"
        enterAt={h(t.adjuster)}
        enterDur={0.75}
        enterConfig={SPRING.heavy}
        demoteAt={h(t.youre)}
        demoteDur={0.6}
        exitAt={h(t.forty) + 0.5}
        exitKind="recede"
        exitDur={0.9}
      />

      {/* "you're" — centre-right, tilted away */}
      <Word
        pose={poses.youre}
        text="You're"
        uppercase
        size={type.medium}
        weight={800}
        color={palette.white}
        demoteColor={palette.steel}
        tone={tone}
        echo
        echoOpacity={0.1}
        wipe="up"
        enterAt={h(t.youre)}
        enterDur={0.7}
        enterConfig={SPRING.heavy}
        demoteAt={h(t.forty)}
        demoteDur={0.5}
        exitAt={h(t.forty) + 0.7}
        exitKind="recede"
        exitDur={0.9}
      />

      {/* the "40%" stamp — the only overshoot in this beat */}
      <Posed
        pose={poses.forty}
        enterAt={h(t.forty)}
        enterDur={0.85}
        enterConfig={SPRING.overshoot}
        enterFromZ={260}
        enterScaleFrom={0.82}
        demoteAt={strikeAt}
        demoteDur={0.4}
        demoteDropY={14}
        demoteTilt={-2}
        exitAt={tumbleAt}
        exitKind="tumble"
        exitDur={TUMBLE_DUR}
      >
        <div
          style={{
            position: 'relative',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <StampBox
            color={palette.red}
            stroke={layout.stroke}
            radius={type.hero * 0.09}
            padX={padX}
            padY={padY}
            tone={tone}
            drawAt={h(t.forty) + 0.02}
            breathFrom={h(t.fault) + 0.5}
          >
            {/* no text-shadow here: StampBox already puts a drop-shadow on the
                whole group, and stacking the two turned the glyphs into mud */}
            <div style={{...hero, position: 'relative'}}>
              {/* a real cross-fade from red to steel, not a swap */}
              <span style={{color: palette.red, opacity: 1 - desat}}>
                40
                <span
                  style={{
                    textShadow: `0 0 ${26 * pctGlow}px rgba(255,255,255,${0.55 * pctGlow})`,
                    filter: `brightness(${1 + 0.5 * pctGlow})`,
                  }}
                >
                  %
                </span>
              </span>
              <span
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  color: palette.steel,
                  opacity: desat,
                }}
              >
                40%
              </span>
            </div>
          </StampBox>

          <div style={{height: gap}} />

          <MaskReveal progress={pFault} direction="up" softness={12}>
            <div
              style={{
                ...TYPE_BASE,
                fontSize: type.label,
                fontWeight: 500,
                letterSpacing: TRACKING.label,
                textTransform: 'uppercase',
                lineHeight: 1,
                color: palette.white,
                textShadow: textShadow(tone),
                transform: `translateY(${(1 - pFault) * 18}px)`,
              }}
            >
              At Fault
            </div>
          </MaskReveal>

          {/* the gold strike that arrives with "opening" in beat 2 */}
          <Strike
            at={strikeAt}
            width={type.hero * 2.4}
            thickness={layout.stroke * 1.1}
            color={palette.gold}
            tone={tone}
            offsetY={strikeOffsetY}
          />
        </div>
      </Posed>

      {/* the red particles thrown off by the slam */}
      <Posed pose={poses.forty} enterAt={h(t.forty)} enterDur={0.1} enterScaleFrom={1} exitKind="none">
        <Burst
          at={h(t.forty)}
          color={palette.red}
          count={12}
          radius={type.hero * 1.35}
          dotSize={layout.stroke * 1.4}
          seed="forty-slam"
        />
      </Posed>
    </>
  );
};
