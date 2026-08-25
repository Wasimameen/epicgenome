import React from 'react';
import {Img, staticFile} from 'remotion';
import {ASSETS} from '../assets';

/**
 * A single bill. Falls back to a drawn note when no cutout is supplied — at reel
 * scale the silhouette and colour do the work, the engraving detail never reads.
 */
export const Banknote: React.FC<{width: number; opacity?: number}> = ({width, opacity = 1}) => {
  if (ASSETS.bill) {
    return <Img src={staticFile(ASSETS.bill)} style={{width, opacity, display: 'block'}} />;
  }

  const h = width * 0.425;
  return (
    <svg width={width} height={h} viewBox="0 0 240 102" style={{display: 'block', opacity}}>
      <rect width="240" height="102" rx="4" fill="#cfd9c0" />
      <rect x="5" y="5" width="230" height="92" rx="3" fill="none" stroke="#5d7355" strokeWidth="2" />
      <ellipse cx="120" cy="51" rx="33" ry="41" fill="#b3c1a3" stroke="#5d7355" strokeWidth="2" />
      <circle cx="120" cy="40" r="12" fill="#94a685" />
      <path d="M100 78 q20 -20 40 0 z" fill="#94a685" />
      {[
        [20, 20],
        [220, 20],
        [20, 82],
        [220, 82],
      ].map(([cx, cy], i) => (
        <text
          key={i}
          x={cx}
          y={cy}
          fill="#4f6349"
          fontSize="17"
          fontWeight="700"
          fontFamily="Georgia, serif"
          textAnchor="middle"
          dominantBaseline="middle"
        >
          100
        </text>
      ))}
    </svg>
  );
};
