import React from 'react';
import {AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {Bloom} from '../components/Bloom';
import {DustMotes} from '../components/DustMotes';
import {LightRays} from '../components/LightRays';
import {Grain} from '../components/Grain';
import {LightSweep} from '../components/LightSweep';
import {MaskReveal} from '../components/MaskReveal';
import {MoneyBackdrop} from '../components/MoneyBackdrop';
import {MoneyCounter} from '../components/MoneyCounter';
import {Vignette} from '../components/Vignette';
import {WalmartLogo} from '../components/WalmartLogo';
import {WordRise} from '../components/WordRise';
import {useTransparent} from '../alpha';
import {cue} from '../timeline';
import {THEME} from '../theme';

/**
 * "Nearly $17 million, because a grandmother went shopping at Walmart."
 *
 * Cues below are the frames at which each word is actually spoken, taken from
 * the voiceover transcript. Titles are placed a few frames ahead of their word —
 * a title landing exactly on its read feels late.
 */
const B = {
  rollStart: 2,
  rollEnd: 38, // figure is still by the time "$17 million" is said at 0.46-1.38s
  because: cue('hook', 2.6) - 6,
  shopping: cue('hook', 3.82) - 5,
  logo: cue('hook', 4.86) - 8,
};

export const Scene01Hook: React.FC = () => {
  const alpha = useTransparent();
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const fadeUp = interpolate(frame, [0, 14], [0, 1], {extrapolateRight: 'clamp'});

  const exit = interpolate(frame, [B.because - 12, B.because], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.quad),
  });

  const blueWash = interpolate(frame, [B.logo - 8, B.logo + 18], [0, 0.24], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: alpha ? 'transparent' : THEME.ink}}>
      <AbsoluteFill style={{opacity: fadeUp}}>
        <MoneyBackdrop durationInFrames={durationInFrames} />
        <LightRays opacity={0.2} origin="50% -12%" angle={-8} />

        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse 78% 40% at 50% 76%, ${THEME.walmartBlue} 0%, transparent 70%)`,
            opacity: blueWash,
            mixBlendMode: 'screen',
          }}
        />

        <Bloom strength={0.42} radius={30}>
          <Sequence from={B.rollStart} durationInFrames={B.because + 12 - B.rollStart}>
            <AbsoluteFill
              style={{
                alignItems: 'center',
                justifyContent: 'center',
                opacity: 1 - exit,
                filter: `blur(${exit * 16}px)`,
                transform: `scale(${1 - exit * 0.14})`,
              }}
            >
              <MoneyCounter startAt={0} countFrames={B.rollEnd - B.rollStart} target={17_000_000} />
            </AbsoluteFill>
          </Sequence>

          <AbsoluteFill
            style={{
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column',
              padding: '0 90px',
              gap: 32,
            }}
          >
            <WordRise
              text="BECAUSE A GRANDMOTHER"
              startAt={B.because}
              stagger={3}
              style={{
                fontFamily: 'var(--display), sans-serif',
                fontSize: 94,
                lineHeight: 1.02,
                color: THEME.paper,
                textAlign: 'center',
                textShadow: '0 8px 40px rgba(0,0,0,0.85)',
              }}
            />
            <MaskReveal startAt={B.shopping} frames={16}>
              <span
                style={{
                  fontFamily: 'var(--body), sans-serif',
                  fontSize: 44,
                  fontWeight: 600,
                  letterSpacing: '0.22em',
                  color: THEME.gold,
                  whiteSpace: 'nowrap',
                }}
              >
                WENT SHOPPING AT
              </span>
            </MaskReveal>
            <div style={{marginTop: 8}}>
              <WalmartLogo startAt={B.logo} />
            </div>
          </AbsoluteFill>
        </Bloom>

        <LightSweep startAt={B.logo + 3} />
        <DustMotes count={34} seed="hook" opacity={0.42} />
      </AbsoluteFill>

      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
