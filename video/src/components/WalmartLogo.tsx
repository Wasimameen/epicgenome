import React from 'react';
import {Img, interpolate, staticFile, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {ASSETS} from '../assets';
import {THEME} from '../theme';

/** The six-blade spark, drawn as capsules on 60-degree centres. */
const Spark: React.FC<{size: number; spin: number; bloom: number}> = ({size, spin, bloom}) => (
  <svg viewBox="-60 -60 120 120" style={{width: size, height: size, overflow: 'visible'}}>
    <g transform={`rotate(${spin})`}>
      {new Array(6).fill(0).map((_, i) => (
        <g key={i} transform={`rotate(${i * 60})`}>
          <rect
            x={-5.6}
            y={-47}
            width={11.2}
            height={28}
            rx={5.6}
            fill={THEME.walmartYellow}
            style={{
              // Blades stagger outward so the mark snaps together rather than fading in.
              transform: `translateY(${(1 - bloom) * 22}px)`,
              opacity: bloom,
            }}
          />
        </g>
      ))}
    </g>
  </svg>
);

/**
 * Walmart lockup for the logo beat.
 *
 * NOTE: with no supplied logo file this falls back to a redrawn spark plus a
 * substitute wordmark face — Walmart's actual type is Bogle, which is not a
 * licensed font here. Drop walmart-logo.png into public/assets for the real mark.
 */
export const WalmartLogo: React.FC<{startAt: number}> = ({startAt}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - startAt;

  const pop = spring({frame: local, fps, config: {damping: 13, mass: 0.7, stiffness: 120}});
  const bloom = spring({frame: local - 3, fps, config: {damping: 12, mass: 0.5}});
  const spin = interpolate(pop, [0, 1], [-55, 0]);

  if (local < 0) return null;

  if (ASSETS.walmartLogo) {
    return (
      <Img
        src={staticFile(ASSETS.walmartLogo)}
        style={{width: 620, transform: `scale(${0.86 + pop * 0.14})`, opacity: pop}}
      />
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 22,
        transform: `scale(${0.86 + pop * 0.14})`,
        opacity: interpolate(local, [0, 5], [0, 1], {extrapolateRight: 'clamp'}),
      }}
    >
      <span
        style={{
          // Deliberately the body face, not the display one: Walmart's mark is a
          // wide humanist sans, and setting it condensed makes it unrecognisable.
          fontFamily: 'var(--body), sans-serif',
          fontSize: 118,
          fontWeight: 700,
          letterSpacing: '-0.028em',
          color: THEME.walmartBlue,
          lineHeight: 1,
        }}
      >
        Walmart
      </span>
      <Spark size={128} spin={spin} bloom={bloom} />
    </div>
  );
};
