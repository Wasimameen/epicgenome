import React from 'react';
import {Img, staticFile} from 'remotion';
import {ASSETS} from '../assets';
import {THEME} from '../theme';

/**
 * Shopping cart. Drawn as a hard silhouette when no cutout is supplied — a
 * stylised shape reads as deliberate at reel pace, a bad photo tracing does not.
 */
export const CartFigure: React.FC<{height: number; flip?: boolean}> = ({height, flip}) => {
  const style: React.CSSProperties = {
    height,
    display: 'block',
    transform: flip ? 'scaleX(-1)' : undefined,
  };

  if (ASSETS.cart) {
    return <Img src={staticFile(ASSETS.cart)} style={style} />;
  }

  return (
    <svg viewBox="0 0 300 240" style={{...style, width: height * 1.25}}>
      <g fill="none" stroke={THEME.paper} strokeWidth="9" strokeLinecap="round" strokeLinejoin="round">
        {/* handle */}
        <path d="M18 30 h34 l14 22" />
        <path d="M66 52 h150" />
        {/* basket */}
        <path d="M66 52 L104 158 h132 L272 52 Z" />
        {/* basket grid */}
        <path d="M84 100 h172M96 130 h150" strokeWidth="5" opacity="0.75" />
        <path d="M118 55 l10 100M158 55 l4 100M198 55 l-4 100M238 55 l-12 100" strokeWidth="5" opacity="0.75" />
        {/* legs */}
        <path d="M110 158 l-8 42M232 158 l6 42" />
      </g>
      <circle cx="100" cy="212" r="18" fill="none" stroke={THEME.paper} strokeWidth="9" />
      <circle cx="240" cy="212" r="18" fill="none" stroke={THEME.paper} strokeWidth="9" />
    </svg>
  );
};
