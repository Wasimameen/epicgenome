import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {DigitRoll} from './DigitRoll';
import {THEME} from '../theme';

/**
 * The headline figure: a kicker over a mechanical digit roll.
 *
 * The roll deliberately finishes a beat before the voiceover says the number,
 * so the figure is already still when it is spoken — a number moving under its
 * own read is busy rather than heavy.
 */
export const MoneyCounter: React.FC<{
  startAt: number;
  countFrames: number;
  target: number;
  size?: number;
  kicker?: string;
}> = ({startAt, countFrames, target, size = 148, kicker = 'NEARLY'}) => {
  const frame = useCurrentFrame();
  const local = frame - startAt;

  const rise = interpolate(local, [0, 14], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        transform: `translateY(${(1 - rise) * 40}px)`,
        opacity: rise,
      }}
    >
      <span
        style={{
          fontFamily: 'var(--body), sans-serif',
          fontSize: 44,
          fontWeight: 600,
          letterSpacing: '0.44em',
          textIndent: '0.44em',
          color: THEME.gold,
          marginBottom: 24,
        }}
      >
        {kicker}
      </span>
      <DigitRoll startAt={startAt} countFrames={countFrames} target={target} size={size} />
    </div>
  );
};
