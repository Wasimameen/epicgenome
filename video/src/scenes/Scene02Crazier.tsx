import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Bloom} from '../components/Bloom';
import {Caption} from '../components/Caption';
import {DustMotes} from '../components/DustMotes';
import {FallingBills} from '../components/FallingBills';
import {Grain} from '../components/Grain';
import {Vignette} from '../components/Vignette';
import {cue} from '../timeline';
import {THEME} from '../theme';

/** "And honestly, how it happened is even crazier than the number." */
const B = {
  how: cue('crazier', 6.82) - 6,
  crazier: cue('crazier', 7.54) - 5,
  number: cue('crazier', 8.6) - 5,
};

export const Scene02Crazier: React.FC = () => {
  const frame = useCurrentFrame();

  const billFade = interpolate(frame, [0, 12, 70, 110], [0, 1, 1, 0.2], {
    extrapolateRight: 'clamp',
  });
  // A slow rotational drift under the copy keeps a talky beat from going static.
  const tilt = interpolate(frame, [0, 121], [-1.6, 1.6], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: THEME.ink}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 66% 44% at 50% 46%, #3a2c11 0%, ${THEME.ink} 72%)`,
        }}
      />
      <FallingBills count={24} seed="crazier" intensity={billFade} />

      <Bloom strength={0.4} radius={24}>
        <AbsoluteFill
          style={{
            alignItems: 'center',
            justifyContent: 'center',
            padding: '0 88px',
            gap: 24,
            transform: `rotate(${tilt}deg)`,
          }}
        >
          <Caption text="HOW IT HAPPENED" startAt={B.how} tone="display" stagger={2} />
          <Caption
            text="IS EVEN CRAZIER"
            startAt={B.crazier}
            tone="heavy"
            stagger={2}
            color={THEME.goldBright}
          />
          <Caption text="THAN THE NUMBER" startAt={B.number} tone="display" stagger={2} />
        </AbsoluteFill>
      </Bloom>

      <DustMotes count={26} seed="crazier" opacity={0.35} />
      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
