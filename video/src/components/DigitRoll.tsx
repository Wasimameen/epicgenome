import React from 'react';
import {Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {THEME} from '../theme';

const DIGITS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];

/**
 * One odometer column. Each digit rides its own strip so higher-order columns
 * settle first, exactly like a mechanical counter spinning down.
 */
const Column: React.FC<{value: number; size: number; settle: number}> = ({
  value,
  size,
  settle,
}) => {
  const cell = size * 1.02;
  // `value` is fractional while rolling; the strip is positioned continuously so
  // digits blur through rather than snapping.
  const y = -value * cell;

  return (
    <span
      style={{
        display: 'inline-block',
        height: cell,
        width: size * 0.6,
        overflow: 'hidden',
        position: 'relative',
        verticalAlign: 'top',
      }}
    >
      <span
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 0,
          transform: `translateY(${y}px)`,
          filter: settle > 0.02 ? `blur(${Math.min(9, settle * 26)}px)` : undefined,
        }}
      >
        {DIGITS.concat(DIGITS[0]).map((d, i) => (
          <span
            key={i}
            style={{
              display: 'block',
              height: cell,
              lineHeight: `${cell}px`,
              textAlign: 'center',
            }}
          >
            {d}
          </span>
        ))}
      </span>
    </span>
  );
};

/**
 * Rolling money counter. Replaces a plain interpolated number — the mechanical
 * settle is what makes the figure feel counted rather than typed.
 */
export const DigitRoll: React.FC<{
  startAt: number;
  countFrames: number;
  target: number;
  size?: number;
}> = ({startAt, countFrames, target, size = 150}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - startAt;

  const progress = interpolate(local, [0, countFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const digits = String(target).split('');
  const land = spring({
    frame: local - countFrames,
    fps,
    config: {damping: 9, mass: 0.55, stiffness: 200},
  });
  const impact = interpolate(land, [0, 1], [1.06, 1]);
  const glow = interpolate(land, [0, 1], [54, 18]);

  // Grouping separators are drawn, not part of any rolling column.
  const withCommas: Array<{digit: string; index: number} | 'comma'> = [];
  digits.forEach((d, i) => {
    const fromEnd = digits.length - i;
    if (i > 0 && fromEnd % 3 === 0) withCommas.push('comma');
    withCommas.push({digit: d, index: i});
  });

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'flex-start',
        fontFamily: 'var(--display), sans-serif',
        fontSize: size,
        lineHeight: 1,
        color: THEME.paper,
        letterSpacing: '-0.01em',
        transform: `scale(${impact})`,
        textShadow: `0 0 ${glow}px rgba(216,178,106,0.6), 0 10px 44px rgba(0,0,0,0.8)`,
      }}
    >
      <span style={{display: 'inline-block', height: size * 1.02, lineHeight: `${size * 1.02}px`}}>
        $
      </span>
      {withCommas.map((item, i) =>
        item === 'comma' ? (
          <span
            key={`c-${i}`}
            style={{
              display: 'inline-block',
              height: size * 1.02,
              lineHeight: `${size * 1.02}px`,
              width: size * 0.24,
              textAlign: 'center',
            }}
          >
            ,
          </span>
        ) : (
          (() => {
            const target = Number(item.digit);
            // Lower-order columns keep spinning longer.
            const lag = (digits.length - item.index) * 0.055;
            const p = Math.min(1, Math.max(0, (progress - lag) / (1 - lag)));
            const spins = 3 + (digits.length - item.index);
            const value = (p * (target + spins * 10)) % 10;
            const settle = 1 - p;
            return (
              <Column
                key={`d-${i}`}
                value={p >= 1 ? target : value}
                size={size}
                settle={settle}
              />
            );
          })()
        ),
      )}
    </span>
  );
};
