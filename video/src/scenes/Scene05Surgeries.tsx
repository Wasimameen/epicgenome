import React from 'react';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Caption} from '../components/Caption';
import {DustMotes} from '../components/DustMotes';
import {Grain} from '../components/Grain';
import {Vignette} from '../components/Vignette';
import {THEME} from '../theme';

/** A slow cardiac trace — the only motion in an otherwise still, heavy beat. */
const Heartline: React.FC<{startAt: number}> = ({startAt}) => {
  const frame = useCurrentFrame();
  const local = frame - startAt;
  const draw = interpolate(local, [0, 70], [0, 1], {extrapolateRight: 'clamp'});

  const d =
    'M0 60 H150 l22 -46 l20 92 l22 -70 l18 24 H420 l24 -34 l18 60 l20 -26 H1080';

  return (
    <svg viewBox="0 0 1080 120" style={{width: '100%', height: 120, opacity: 0.5}}>
      <path
        d={d}
        fill="none"
        stroke={THEME.gold}
        strokeWidth="4"
        strokeLinecap="round"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - draw}
      />
    </svg>
  );
};

const BigStat: React.FC<{value: string; label: string; startAt: number}> = ({
  value,
  label,
  startAt,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - startAt, fps, config: {damping: 14, mass: 0.8}});

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        opacity: s,
        transform: `translateY(${(1 - s) * 34}px)`,
      }}
    >
      <span
        style={{
          fontFamily: 'var(--display), sans-serif',
          fontSize: 158,
          lineHeight: 0.94,
          color: THEME.paper,
          textShadow: '0 0 40px rgba(216,178,106,0.35)',
        }}
      >
        {value}
      </span>
      <span
        style={{
          fontFamily: 'var(--body), sans-serif',
          fontSize: 36,
          fontWeight: 600,
          letterSpacing: '0.24em',
          textIndent: '0.24em',
          color: THEME.gold,
          marginTop: 12,
        }}
      >
        {label}
      </span>
    </div>
  );
};

/** "She needed multiple surgeries. She's been in the hospital more than twenty times." */
export const Scene05Surgeries: React.FC = () => {
  const frame = useCurrentFrame();
  // Nothing here should feel energetic — the push is barely perceptible.
  const drift = interpolate(frame, [0, 208], [0, -30], {
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.ease),
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#07070a'}}>
      <AbsoluteFill
        style={{
          background: 'radial-gradient(ellipse 62% 36% at 50% 44%, #16161f 0%, #06060a 76%)',
          transform: `translateY(${drift}px)`,
        }}
      />

      <AbsoluteFill
        style={{alignItems: 'center', justifyContent: 'center', gap: 60, padding: '0 80px'}}
      >
        <Caption text="MULTIPLE SURGERIES" startAt={4} tone="display" stagger={3} />
        <Heartline startAt={18} />
        <BigStat value="20+" label="HOSPITAL VISITS" startAt={112} />
      </AbsoluteFill>

      <DustMotes seed="surg" count={30} opacity={0.3} />
      <Vignette strength={0.96} />
      <Grain opacity={0.08} />
    </AbsoluteFill>
  );
};
