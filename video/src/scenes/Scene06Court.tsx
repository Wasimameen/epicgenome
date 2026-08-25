import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Caption} from '../components/Caption';
import {Grain} from '../components/Grain';
import {Stamp} from '../components/Stamp';
import {Vignette} from '../components/Vignette';
import {WalmartLogo} from '../components/WalmartLogo';
import {THEME} from '../theme';

/** Neoclassical courthouse front, drawn columns rising into place. */
const Courthouse: React.FC<{startAt: number}> = ({startAt}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <svg viewBox="0 0 1080 620" style={{width: '100%', opacity: 0.3}}>
      <g fill={THEME.gold}>
        <path d="M120 200 L540 70 L960 200 Z" opacity="0.85" />
        <rect x="120" y="200" width="840" height="34" />
        {new Array(6).fill(0).map((_, i) => {
          const s = spring({
            frame: frame - startAt - i * 3,
            fps,
            config: {damping: 15, mass: 0.7},
          });
          return (
            <rect
              key={i}
              x={182 + i * 140}
              y={244}
              width="56"
              height={300 * s}
              rx="6"
              opacity="0.9"
            />
          );
        })}
        <rect x="120" y="548" width="840" height="30" />
        <rect x="86" y="578" width="908" height="26" opacity="0.8" />
      </g>
    </svg>
  );
};

/**
 * "So she takes Walmart to court — and she WINS — but Walmart isn't done — they
 * appeal it all the way to the state Supreme Court —"
 *
 * Three turns in one beat, so each gets its own frame: win, then the appeal
 * yanking it away, then the escalation.
 */
export const Scene06Court: React.FC = () => {
  const frame = useCurrentFrame();

  // The court block clears before the stamp lands — the two must never share
  // the frame, or the verdict reads as annotation on a logo.
  const drain = interpolate(frame, [44, 58], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const stampOut = interpolate(frame, [92, 104], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const climb = interpolate(frame, [112, 180], [0, -120], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#07070a'}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 70% 44% at 50% 52%, #241d10 0%, #06060a 76%)`,
        }}
      />

      <AbsoluteFill
        style={{
          justifyContent: 'center',
          transform: `translateY(${climb}px) scale(${1 + Math.max(0, -climb) * 0.0012})`,
          opacity: 0.9,
        }}
      >
        <Courthouse startAt={8} />
      </AbsoluteFill>

      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', gap: 34}}>
        <div style={{opacity: 1 - drain, transform: `scale(${1 - drain * 0.12})`}}>
          <Caption text="SHE TAKES" startAt={6} tone="kicker" stagger={2} />
          <div style={{height: 18}} />
          <div style={{display: 'flex', justifyContent: 'center'}}>
            <WalmartLogo startAt={14} />
          </div>
          <div style={{height: 26}} />
          <Caption text="TO COURT" startAt={30} tone="display" stagger={2} />
        </div>
      </AbsoluteFill>

      {frame >= 58 && frame < 106 ? (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
          <div style={{opacity: stampOut}}>
            <Stamp text="SHE WINS" startAt={58} color="#3fbf6a" angle={-6} />
          </div>
        </AbsoluteFill>
      ) : null}

      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', paddingTop: 120}}>
        <Caption
          text="WALMART APPEALS"
          startAt={106}
          tone="heavy"
          stagger={2}
          color={THEME.goldBright}
        />
        <div style={{height: 22}} />
        <Caption
          text="ALL THE WAY TO THE STATE SUPREME COURT"
          startAt={130}
          tone="kicker"
          stagger={1}
          style={{fontSize: 38, maxWidth: 860}}
        />
      </AbsoluteFill>

      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
