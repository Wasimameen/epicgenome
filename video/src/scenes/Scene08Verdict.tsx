import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Caption} from '../components/Caption';
import {FallingBills} from '../components/FallingBills';
import {FlashCut} from '../components/FlashCut';
import {DustMotes} from '../components/DustMotes';
import {Grain} from '../components/Grain';
import {LightRays} from '../components/LightRays';
import {LightSweep} from '../components/LightSweep';
import {MoneyBackdrop} from '../components/MoneyBackdrop';
import {MoneyCounter} from '../components/MoneyCounter';
import {Stamp} from '../components/Stamp';
import {Vignette} from '../components/Vignette';
import {cue} from '../timeline';
import {THEME} from '../theme';

/**
 * Cues from the voiceover transcript:
 *   "The court said,"                          44.04 - 44.34
 *   "the verdict stands."                      45.16 - 45.46
 *   "All of it, nearly $17 million,"           46.58 - 47.96
 *   "upheld by the highest court in the state." 49.60 - 51.18
 *
 * The stamp's spring peaks about 8 frames after it starts, so it is placed
 * early enough to land exactly on the word "stands".
 */
const STAMP_AT = cue('verdict', 45.46) - 8;
const STAMP_OUT = cue('verdict', 46.4);
const ROLL_AT = cue('verdict', 46.58);
const ROLL_LAND = cue('verdict', 47.5);
const UPHELD_AT = cue('verdict', 49.6) - 5;

/**
 * "The court said… the verdict stands. All of it — nearly seventeen million
 * dollars — upheld by the highest court in the state."
 *
 * Payoff beat: the figure from the hook returns, this time earned. The cash
 * fall only starts after the stamp lands, so the celebration reads as a
 * consequence of the ruling rather than decoration running underneath it.
 */
export const Scene08Verdict: React.FC = () => {
  const frame = useCurrentFrame();

  const stampOut = interpolate(frame, [STAMP_OUT, STAMP_OUT + 14], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const goldRise = interpolate(frame, [STAMP_AT, STAMP_AT + 30], [0, 0.3], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: THEME.ink}}>
      <MoneyBackdrop durationInFrames={253} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 66% 40% at 50% 46%, ${THEME.goldBright} 0%, transparent 70%)`,
          opacity: goldRise,
          mixBlendMode: 'screen',
        }}
      />

      {frame > STAMP_AT ? (
        <FallingBills startAt={STAMP_AT + 4} count={30} seed="verdict" />
      ) : null}

      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <Caption
          text="THE COURT SAID"
          startAt={2}
          exitAt={STAMP_AT - 4}
          tone="kicker"
          stagger={3}
        />
      </AbsoluteFill>

      {frame >= STAMP_AT && frame < STAMP_OUT + 18 ? (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
          <div style={{opacity: 1 - stampOut, transform: `scale(${1 + stampOut * 0.16})`}}>
            <Stamp text="VERDICT STANDS" startAt={STAMP_AT} color="#3fbf6a" angle={-5} />
          </div>
        </AbsoluteFill>
      ) : null}

      {frame >= ROLL_AT - 4 ? (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', gap: 30}}>
          <MoneyCounter startAt={ROLL_AT} countFrames={ROLL_LAND - ROLL_AT} target={17_000_000} />
          <div style={{height: 6}} />
          <Caption
            text="UPHELD BY THE HIGHEST COURT IN THE STATE"
            startAt={UPHELD_AT}
            tone="kicker"
            stagger={1}
            style={{fontSize: 36, maxWidth: 880}}
          />
        </AbsoluteFill>
      ) : null}

      <FlashCut at={STAMP_AT} frames={5} />
      <LightSweep startAt={ROLL_LAND + 4} />
      <LightRays opacity={0.22} />
      <DustMotes seed="verdict" />
      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
