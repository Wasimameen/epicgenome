import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Caption} from '../components/Caption';
import {DustMotes} from '../components/DustMotes';
import {FootagePlate} from '../components/FootagePlate';
import {Grain} from '../components/Grain';
import {LightRays} from '../components/LightRays';
import {Stamp} from '../components/Stamp';
import {Vignette} from '../components/Vignette';
import {WalmartLogo} from '../components/WalmartLogo';
import {THEME} from '../theme';

/**
 * "So she takes Walmart to court — and she WINS — but Walmart isn't done —
 * they appeal it all the way to the state Supreme Court —"  (35.41–44.09s)
 *
 * Internal hits sit on the read's own pauses: the win lands at 37.3s, the
 * appeal turn at 40.7s. This is the one beat carrying live-action, and it earns
 * it — the escalation to a higher court is the only literal image in the spot.
 */
export const Scene06Court: React.FC = () => {
  const frame = useCurrentFrame();

  // The court block clears before the stamp lands — the two must never share
  // the frame, or the verdict reads as annotation on a logo.
  const drain = interpolate(frame, [42, 56], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const stampOut = interpolate(frame, [132, 146], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Footage is held back until the appeal — the building appearing at the exact
  // moment of escalation is the point, so it must not be there beforehand.
  const plateIn = interpolate(frame, [150, 178], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#07070a'}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 70% 44% at 50% 46%, #241d10 0%, #06060a 76%)`,
        }}
      />

      <AbsoluteFill style={{opacity: plateIn}}>
        <FootagePlate
          src="video/reference.mp4"
          durationInFrames={261}
          push={[1.34, 1.06]}
          opacity={0.82}
        />
      </AbsoluteFill>

      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: 1 - drain, transform: `scale(${1 - drain * 0.12})`}}>
          <Caption text="SHE TAKES" startAt={4} tone="kicker" stagger={2} />
          <div style={{height: 18}} />
          <div style={{display: 'flex', justifyContent: 'center'}}>
            <WalmartLogo startAt={10} />
          </div>
          <div style={{height: 26}} />
          <Caption text="TO COURT" startAt={24} tone="display" stagger={2} />
        </div>
      </AbsoluteFill>

      {frame >= 60 && frame < 148 ? (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
          <div style={{opacity: stampOut}}>
            <Stamp text="SHE WINS" startAt={60} color="#3fbf6a" angle={-6} />
          </div>
        </AbsoluteFill>
      ) : null}

      <AbsoluteFill
        style={{alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 300}}
      >
        <Caption
          text="WALMART APPEALS"
          startAt={160}
          tone="heavy"
          stagger={2}
          color={THEME.goldBright}
        />
        <div style={{height: 22}} />
        <Caption
          text="ALL THE WAY TO THE STATE SUPREME COURT"
          startAt={196}
          tone="kicker"
          stagger={1}
          style={{fontSize: 38, maxWidth: 860}}
        />
      </AbsoluteFill>

      <LightRays opacity={0.2} />
      <DustMotes seed="court" opacity={0.45} />
      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
