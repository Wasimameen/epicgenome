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
import {THEME} from '../theme';

const STAMP_AT = 90; // "the verdict stands" begins at 49.55s

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

  const stampOut = interpolate(frame, [150, 166], [0, 1], {
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

      {frame >= STAMP_AT && frame < 172 ? (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
          <div style={{opacity: 1 - stampOut, transform: `scale(${1 + stampOut * 0.16})`}}>
            <Stamp text="VERDICT STANDS" startAt={STAMP_AT} color="#3fbf6a" angle={-5} />
          </div>
        </AbsoluteFill>
      ) : null}

      {frame >= 168 ? (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', gap: 30}}>
          <MoneyCounter startAt={176} countFrames={34} target={17_000_000} />
          <div style={{height: 6}} />
          <Caption
            text="UPHELD BY THE HIGHEST COURT IN THE STATE"
            startAt={216}
            tone="kicker"
            stagger={1}
            style={{fontSize: 36, maxWidth: 880}}
          />
        </AbsoluteFill>
      ) : null}

      <FlashCut at={STAMP_AT} frames={5} />
      <LightSweep startAt={208} />
      <LightRays opacity={0.22} />
      <DustMotes seed="verdict" />
      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
