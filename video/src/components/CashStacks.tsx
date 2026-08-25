import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {ASSETS} from '../assets';
import {THEME} from '../theme';

/** One banded bundle, drawn in rough isometric. */
const Bundle: React.FC<{x: number; y: number; w: number; lift: number}> = ({x, y, w, lift}) => (
  <g transform={`translate(${x} ${y - lift})`}>
    <path d={`M0 0 l${w} -${w * 0.34} l${w * 0.62} ${w * 0.2} l-${w} ${w * 0.34} Z`} fill="#e8e2cf" />
    <path d={`M0 0 l0 ${w * 0.2} l${w * 0.62} ${w * 0.2} l0 -${w * 0.2} Z`} fill="#b8ae90" />
    <path
      d={`M${w} -${w * 0.34} l${w * 0.62} ${w * 0.2} l0 ${w * 0.2} l-${w * 0.62} -${w * 0.2} Z`}
      fill="#cfc6a8"
    />
    <path
      d={`M${w * 0.44} -${w * 0.15} l${w * 0.62} ${w * 0.2} l-${w * 0.17} ${w * 0.06} l-${w * 0.62} -${w * 0.2} Z`}
      fill={THEME.walmartYellow}
      opacity="0.75"
    />
  </g>
);

/**
 * The lamp-lit table of bundles. Falls back to a drawn grid of bundles lit by a
 * single warm pool, matching the supplied photograph's staging.
 */
export const CashStacks: React.FC<{startAt?: number; durationInFrames: number}> = ({
  startAt = 0,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const local = frame - startAt;
  const push = interpolate(local, [0, durationInFrames], [1.04, 1.16], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  if (ASSETS.cashStacks) {
    return (
      <AbsoluteFill style={{overflow: 'hidden'}}>
        <Img
          src={staticFile(ASSETS.cashStacks)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${push})`,
          }}
        />
      </AbsoluteFill>
    );
  }

  const rows = 5;
  const cols = 4;

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0906', overflow: 'hidden'}}>
      <AbsoluteFill style={{transform: `scale(${push})`, transformOrigin: '48% 62%'}}>
        <AbsoluteFill
          style={{
            background:
              'radial-gradient(ellipse 46% 30% at 30% 46%, rgba(255,196,90,0.5) 0%, transparent 70%)',
          }}
        />
        <svg viewBox="0 0 1080 1920" style={{width: '100%', height: '100%'}}>
          <defs>
            <radialGradient id="lampPool" cx="34%" cy="46%" r="58%">
              <stop offset="0%" stopColor="#fff" stopOpacity="1" />
              <stop offset="55%" stopColor="#fff" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#fff" stopOpacity="0.06" />
            </radialGradient>
            <mask id="lampMask">
              <rect width="1080" height="1920" fill="url(#lampPool)" />
            </mask>
          </defs>
          {/* table */}
          <path d="M0 1010 L1080 840 L1080 1920 L0 1920 Z" fill="#3b2415" />
          <g mask="url(#lampMask)">
            {new Array(rows).fill(0).map((_, r) =>
              new Array(cols).fill(0).map((_, c) => {
                const i = r * cols + c;
                // Bundles settle in a stagger so the pile assembles rather than appears.
                const lift = interpolate(local - i * 2.5, [0, 18], [70, 0], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                });
                return (
                  <Bundle
                    key={i}
                    x={120 + c * 210 - r * 34}
                    y={1130 + r * 96}
                    w={190}
                    lift={lift}
                  />
                );
              }),
            )}
          </g>
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
