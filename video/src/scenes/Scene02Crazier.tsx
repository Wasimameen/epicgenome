import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Caption} from '../components/Caption';
import {FallingBills} from '../components/FallingBills';
import {Grain} from '../components/Grain';
import {Vignette} from '../components/Vignette';
import {THEME} from '../theme';

/** "And honestly — how it happened is even crazier than the number." */
export const Scene02Crazier: React.FC = () => {
  const frame = useCurrentFrame();

  // Bills keep falling from the hook's payoff, thinning as the copy takes over.
  const billFade = interpolate(frame, [0, 14, 62, 96], [0, 1, 1, 0.25], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: THEME.ink}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 66% 44% at 50% 46%, #33280f 0%, ${THEME.ink} 72%)`,
        }}
      />
      <FallingBills count={22} seed="crazier" intensity={billFade} />

      <AbsoluteFill
        style={{alignItems: 'center', justifyContent: 'center', padding: '0 88px', gap: 26}}
      >
        <Caption text="HOW IT HAPPENED" startAt={6} tone="display" stagger={2} />
        <Caption
          text="IS EVEN CRAZIER"
          startAt={16}
          tone="heavy"
          stagger={2}
          color={THEME.goldBright}
        />
        <Caption text="THAN THE NUMBER" startAt={30} tone="display" stagger={2} />
      </AbsoluteFill>

      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
