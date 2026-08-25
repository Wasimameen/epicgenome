import React from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {Grain} from '../components/Grain';
import {LightSweep} from '../components/LightSweep';
import {MoneyBackdrop} from '../components/MoneyBackdrop';
import {MoneyCounter} from '../components/MoneyCounter';
import {Vignette} from '../components/Vignette';
import {WalmartLogo} from '../components/WalmartLogo';
import {WordRise} from '../components/WordRise';
import {THEME} from '../theme';

/**
 * Beat map for the 5s hook, keyed to the read:
 *   "[dramatic][slow] Nearly seventeen million dollars…
 *    because a grandmother went shopping at Walmart."
 *
 * Visuals lead the voiceover by a few frames throughout — a title that lands on
 * the word feels late, one that lands just before it feels intentional.
 */
const BEAT = {
  fadeUp: 0,
  counterIn: 8,
  counterCount: 48, // lands on frame 56
  counterOut: 74,
  grandmother: 78,
  shoppingAt: 104,
  logo: 114,
} as const;

export const Scene01Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const fadeUp = interpolate(frame, [BEAT.fadeUp, 12], [0, 1], {extrapolateRight: 'clamp'});

  // The number does not cut — it recedes, blurs and hands the frame to the copy.
  const exit = interpolate(frame, [BEAT.counterOut, BEAT.counterOut + 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.quad),
  });

  // Brand blue seeps in only for the final beat, under the logo.
  const blueWash = interpolate(frame, [BEAT.logo - 8, BEAT.logo + 16], [0, 0.22], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: THEME.ink}}>
      <AbsoluteFill style={{opacity: fadeUp}}>
        <MoneyBackdrop durationInFrames={durationInFrames} />

        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse 78% 40% at 50% 74%, ${THEME.walmartBlue} 0%, transparent 70%)`,
            opacity: blueWash,
            mixBlendMode: 'screen',
          }}
        />

        {/* Beat 1 — the number. */}
        <Sequence from={BEAT.counterIn} durationInFrames={BEAT.counterOut + 14 - BEAT.counterIn}>
          <AbsoluteFill
            style={{
              alignItems: 'center',
              justifyContent: 'center',
              opacity: 1 - exit,
              filter: `blur(${exit * 14}px)`,
              transform: `scale(${1 - exit * 0.13})`,
            }}
          >
            <MoneyCounter startAt={0} countFrames={BEAT.counterCount} target={17_000_000} />
          </AbsoluteFill>
        </Sequence>

        {/* Beats 2 and 3 — the cause, then the brand. */}
        <AbsoluteFill
          style={{
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            padding: '0 90px',
            gap: 34,
          }}
        >
          <WordRise
            text="BECAUSE A GRANDMOTHER"
            startAt={BEAT.grandmother}
            style={{
              fontFamily: 'var(--display), sans-serif',
              fontSize: 96,
              lineHeight: 1.02,
              color: THEME.paper,
              letterSpacing: '-0.015em',
              textAlign: 'center',
              textShadow: '0 8px 40px rgba(0,0,0,0.8)',
            }}
          />
          <WordRise
            text="WENT SHOPPING AT"
            startAt={BEAT.shoppingAt}
            stagger={2}
            style={{
              fontFamily: 'var(--body), sans-serif',
              fontSize: 46,
              fontWeight: 600,
              letterSpacing: '0.22em',
              textIndent: '0.22em',
              color: THEME.gold,
              textAlign: 'center',
            }}
          />
          <div style={{marginTop: 10}}>
            <WalmartLogo startAt={BEAT.logo} />
          </div>
        </AbsoluteFill>

        <LightSweep startAt={BEAT.logo + 2} />
      </AbsoluteFill>

      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
