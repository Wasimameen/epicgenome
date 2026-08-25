import React from 'react';
import {Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {THEME} from '../theme';

const format = (n: number) => `$${Math.round(n).toLocaleString('en-US')}`;

/**
 * The headline figure, ticking up and then landing hard.
 *
 * The count deliberately finishes early and holds, so the number is already
 * still by the time the voiceover reaches "dollars" — a number moving under a
 * spoken figure reads as busy rather than heavy.
 */
export const MoneyCounter: React.FC<{
  startAt: number;
  countFrames: number;
  target: number;
}> = ({startAt, countFrames, target}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - startAt;

  const value = interpolate(local, [0, countFrames], [0, target], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  // A small impact scale on the landing frame gives the figure its weight.
  const land = spring({
    frame: local - countFrames,
    fps,
    config: {damping: 9, mass: 0.55, stiffness: 190},
  });
  const impact = interpolate(land, [0, 1], [1.055, 1]);
  const glow = interpolate(land, [0, 1], [46, 16]);

  const rise = spring({frame: local, fps, config: {damping: 16, mass: 0.8}});

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        transform: `translateY(${(1 - rise) * 44}px) scale(${impact})`,
      }}
    >
      <span
        style={{
          fontFamily: 'var(--body), sans-serif',
          fontSize: 46,
          fontWeight: 600,
          letterSpacing: '0.44em',
          textIndent: '0.44em',
          color: THEME.gold,
          opacity: interpolate(local, [0, 10], [0, 0.95], {extrapolateRight: 'clamp'}),
          marginBottom: 26,
        }}
      >
        NEARLY
      </span>
      <span
        style={{
          fontFamily: 'var(--display), sans-serif',
          fontSize: 152,
          lineHeight: 0.94,
          color: THEME.paper,
          letterSpacing: '-0.02em',
          textShadow: `0 0 ${glow}px rgba(216,178,106,0.55), 0 10px 44px rgba(0,0,0,0.75)`,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {format(value)}
      </span>
    </div>
  );
};
