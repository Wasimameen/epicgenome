import React from 'react';
import {Easing, interpolate, useCurrentFrame} from 'remotion';

/**
 * Wipe-reveal behind a moving edge, with the edge itself visible as a bright
 * bar. Used for the title cards that need to feel printed rather than typed.
 */
export const MaskReveal: React.FC<{
  startAt: number;
  frames?: number;
  direction?: 'up' | 'left';
  edgeColor?: string;
  children: React.ReactNode;
}> = ({startAt, frames = 18, direction = 'up', edgeColor = '#f5d98a', children}) => {
  const frame = useCurrentFrame();
  const local = frame - startAt;

  const p = interpolate(local, [0, frames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  if (local < 0) return null;

  const clip =
    direction === 'up'
      ? `inset(${(1 - p) * 100}% 0% 0% 0%)`
      : `inset(0% ${(1 - p) * 100}% 0% 0%)`;

  const edgeVisible = p > 0.02 && p < 0.99;

  return (
    <span style={{position: 'relative', display: 'inline-block'}}>
      <span style={{display: 'inline-block', clipPath: clip, WebkitClipPath: clip}}>
        {children}
      </span>
      {edgeVisible ? (
        <span
          style={{
            position: 'absolute',
            pointerEvents: 'none',
            ...(direction === 'up'
              ? {left: 0, right: 0, top: `${(1 - p) * 100}%`, height: 5}
              : {top: 0, bottom: 0, left: `${p * 100}%`, width: 5}),
            background: edgeColor,
            boxShadow: `0 0 26px ${edgeColor}`,
            opacity: 0.9,
          }}
        />
      ) : null}
    </span>
  );
};
