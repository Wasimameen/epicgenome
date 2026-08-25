import React from 'react';
import {Img, staticFile} from 'remotion';
import {ASSETS} from '../assets';
import {THEME} from '../theme';

/**
 * Standing figure for the grandmother. Silhouette fallback, same reasoning as
 * the cart — shape and posture carry the beat, detail does not.
 */
export const GrandmaFigure: React.FC<{height: number}> = ({height}) => {
  if (ASSETS.grandma) {
    return <Img src={staticFile(ASSETS.grandma)} style={{height, display: 'block'}} />;
  }

  return (
    <svg viewBox="0 0 140 380" style={{height, width: height * 0.368, display: 'block'}}>
      <g fill={THEME.paper}>
        {/* hair and head */}
        <ellipse cx="70" cy="34" rx="30" ry="27" opacity="0.85" />
        <ellipse cx="70" cy="42" rx="23" ry="26" />
        {/* neck and shoulders */}
        <rect x="61" y="64" width="18" height="16" rx="7" />
        <path d="M70 74 q-38 8 -43 44 l-6 62 q22 8 49 8 q27 0 49 -8 l-6 -62 q-5 -36 -43 -44 Z" />
        {/* cardigan opening */}
        <path d="M70 78 v106" stroke={THEME.ink} strokeWidth="4" opacity="0.35" />
        {/* arms folded at the waist */}
        <path
          d="M31 132 q-9 40 4 62 q22 12 35 12 q13 0 35 -12 q13 -22 4 -62"
          fill="none"
          stroke={THEME.paper}
          strokeWidth="15"
          strokeLinecap="round"
        />
        {/* long skirt */}
        <path d="M27 186 q43 12 86 0 l20 150 q-63 16 -126 0 Z" opacity="0.92" />
        {/* shoes */}
        <ellipse cx="52" cy="344" rx="15" ry="9" />
        <ellipse cx="88" cy="344" rx="15" ry="9" />
      </g>
    </svg>
  );
};
