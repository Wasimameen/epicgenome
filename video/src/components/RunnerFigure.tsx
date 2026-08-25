import React from 'react';
import {THEME} from '../theme';

/** Sprinting silhouette for the fleeing shoplifter. */
export const RunnerFigure: React.FC<{height: number; flip?: boolean}> = ({height, flip}) => (
  <svg
    viewBox="0 0 200 340"
    style={{height, width: height * 0.588, display: 'block', transform: flip ? 'scaleX(-1)' : undefined}}
  >
    <g fill={THEME.paper}>
      <circle cx="128" cy="40" r="26" />
      {/* torso pitched forward into the run */}
      <path d="M118 66 q-30 10 -36 44 l-8 46 q30 12 62 6 l14 -50 q6 -34 -32 -46 Z" />
      {/* trailing and leading arms */}
      <path
        d="M96 96 q-40 12 -58 -14"
        fill="none"
        stroke={THEME.paper}
        strokeWidth="19"
        strokeLinecap="round"
      />
      <path
        d="M142 100 q38 18 40 54"
        fill="none"
        stroke={THEME.paper}
        strokeWidth="19"
        strokeLinecap="round"
      />
      {/* stride */}
      <path
        d="M92 158 q-34 44 -66 56"
        fill="none"
        stroke={THEME.paper}
        strokeWidth="23"
        strokeLinecap="round"
      />
      <path
        d="M126 160 q22 54 6 100"
        fill="none"
        stroke={THEME.paper}
        strokeWidth="23"
        strokeLinecap="round"
      />
      <ellipse cx="20" cy="222" rx="22" ry="11" transform="rotate(-24 20 222)" />
      <ellipse cx="130" cy="272" rx="22" ry="11" transform="rotate(8 130 272)" />
    </g>
  </svg>
);
