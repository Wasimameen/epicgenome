import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {THEME} from '../theme';

/**
 * Rubber-stamp impact: overshoots in rotated and oversized, then slams flat.
 * Reserved for verdict language — it loses all its weight if reused per beat.
 */
export const Stamp: React.FC<{
  text: string;
  startAt: number;
  color?: string;
  angle?: number;
}> = ({text, startAt, color = '#d8402f', angle = -7}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - startAt;
  if (local < 0) return null;

  const hit = spring({frame: local, fps, config: {damping: 11, mass: 0.5, stiffness: 220}});
  const scale = interpolate(hit, [0, 1], [2.4, 1]);
  const rot = interpolate(hit, [0, 1], [angle - 14, angle]);
  const blur = interpolate(hit, [0, 0.7, 1], [16, 2, 0], {extrapolateRight: 'clamp'});

  return (
    <div
      style={{
        transform: `scale(${scale}) rotate(${rot}deg)`,
        filter: `blur(${blur}px)`,
        opacity: interpolate(local, [0, 3], [0, 1], {extrapolateRight: 'clamp'}),
        border: `9px solid ${color}`,
        borderRadius: 14,
        padding: '20px 44px',
        color,
        fontFamily: 'var(--display), sans-serif',
        fontSize: 92,
        letterSpacing: '0.02em',
        lineHeight: 1,
        background: 'rgba(0,0,0,0.28)',
        boxShadow: `0 0 60px ${color}55`,
        textShadow: `0 0 30px ${color}66`,
        whiteSpace: 'nowrap',
      }}
    >
      {text}
    </div>
  );
};
