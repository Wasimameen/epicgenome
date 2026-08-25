import React from 'react';
import {AbsoluteFill, interpolate, random, useCurrentFrame} from 'remotion';
import {Caption} from '../components/Caption';
import {CashStacks} from '../components/CashStacks';
import {DustMotes} from '../components/DustMotes';
import {Grain} from '../components/Grain';
import {Vignette} from '../components/Vignette';
import {THEME} from '../theme';

/**
 * "and now every single dollar is on the line."
 *
 * The tension device is a pulse that quickens: a slow throb early, tightening
 * toward the cut, so the beat feels like it is running out of time.
 */
export const Scene07OnTheLine: React.FC = () => {
  const frame = useCurrentFrame();

  const rate = interpolate(frame, [0, 74], [0.2, 0.52], {extrapolateRight: 'clamp'});
  const pulse = (Math.sin(frame * rate) + 1) / 2;

  // Occasional single-frame dropouts, increasing in frequency — instability.
  const glitch = frame > 30 && random(`g-${frame}`) > 0.9 ? 1 : 0;

  return (
    <AbsoluteFill style={{backgroundColor: '#07060a'}}>
      <CashStacks durationInFrames={74} />

      <AbsoluteFill
        style={{
          background: 'radial-gradient(ellipse 58% 34% at 50% 40%, #b3202a 0%, transparent 72%)',
          opacity: 0.1 + pulse * 0.2,
          mixBlendMode: 'screen',
        }}
      />

      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          paddingBottom: 420,
          transform: glitch ? `translateX(${(random(`gx-${frame}`) - 0.5) * 30}px)` : undefined,
        }}
      >
        <Caption text="EVERY SINGLE DOLLAR" startAt={4} tone="display" stagger={2} />
        <div style={{height: 20}} />
        <Caption
          text="ON THE LINE"
          startAt={18}
          tone="heavy"
          stagger={2}
          color={THEME.goldBright}
          style={{
            textShadow: `0 0 ${30 + pulse * 50}px rgba(245,217,138,${0.35 + pulse * 0.4}), 0 8px 42px rgba(0,0,0,0.85)`,
          }}
        />
      </AbsoluteFill>

      <DustMotes seed="line" opacity={0.5} />
      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
