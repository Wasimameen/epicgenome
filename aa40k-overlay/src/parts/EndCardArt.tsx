/**
 * The signature end card, rebuilt.
 *
 * This is a reconstruction of the supplied artwork, drawn rather than placed —
 * the original arrived as a picture in conversation, not as a file, so it could
 * not be vendored. Built this way it is dead sharp at 4K, re-colours from the
 * brand tokens and can be animated; drop the real card at `assets-in/endcard.png`
 * and it is used instead, untouched.
 *
 * Everything scales from one unit — the 9:16-equivalent width — so the 16:9
 * card is the same design rather than a stretched one.
 */

import React from 'react';
import {SERIF_BASE, TYPE_BASE} from '../font';
import type {Layout} from '../theme';

const CREAM = '#F6F0E4';
const GOLD = '#D8AE49';
const PILL = '#171210';

/** Circular mark: cream disc, thin gold ring, A/X monogram, five stars. */
const Mark: React.FC<{size: number; ink: string}> = ({size, ink}) => {
  const c = 50;
  const star = (cx: number, cy: number, r: number) => {
    let d = '';
    for (let i = 0; i < 10; i++) {
      const rr = i % 2 === 0 ? r : r * 0.44;
      const a = (Math.PI / 5) * i - Math.PI / 2;
      d += `${i === 0 ? 'M' : 'L'}${(cx + rr * Math.cos(a)).toFixed(2)} ${(cy + rr * Math.sin(a)).toFixed(2)} `;
    }
    return `${d}Z`;
  };

  return (
    <svg width={size} height={size} viewBox="0 0 100 100" style={{display: 'block'}}>
      <circle cx={c} cy={c} r={49} fill={CREAM} />
      <circle cx={c} cy={c} r={44.5} fill="none" stroke={GOLD} strokeWidth={1.1} />
      {/* the monogram: an A crossed by an inverted chevron */}
      <path
        d="M31 62 L50 27 L69 62"
        fill="none"
        stroke={ink}
        strokeWidth={6.4}
        strokeLinecap="square"
        strokeLinejoin="miter"
      />
      <path
        d="M38 38 L50 60 L62 38"
        fill="none"
        stroke={ink}
        strokeWidth={6.4}
        strokeLinecap="square"
        strokeLinejoin="miter"
      />
      {[0, 1, 2, 3, 4].map((i) => (
        <path key={i} d={star(35 + i * 7.5, 74, 3)} fill={GOLD} />
      ))}
    </svg>
  );
};

export const EndCardArt: React.FC<{
  readonly layout: Layout;
  readonly bg: string;
  readonly disclaimer?: string;
}> = ({layout, bg}) => {
  // One unit for both aspects: the 9:16-equivalent width. Keeps the 16:9 card
  // the same design at the same proportions rather than a stretched one.
  const u = Math.min(layout.width, layout.height * (9 / 16));

  const label: React.CSSProperties = {
    ...TYPE_BASE,
    color: CREAM,
    fontWeight: 800,
    letterSpacing: '0.24em',
    textTransform: 'uppercase',
    fontSize: u * 0.041,
    lineHeight: 1,
  };

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        backgroundColor: bg,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: u * 0.032,
      }}
    >
      <Mark size={u * 0.185} ink={bg} />

      <div style={{...label, marginTop: u * 0.012}}>Awesome Attorneys</div>

      <div style={{width: u * 0.1, height: Math.max(1.5, u * 0.0028), backgroundColor: GOLD}} />

      <div
        style={{
          ...SERIF_BASE,
          fontSize: u * 0.079,
          fontWeight: 500,
          lineHeight: 1.12,
          letterSpacing: '-0.005em',
        }}
      >
        <span style={{color: CREAM}}>Get Matched. </span>
        <span style={{color: GOLD}}>Get Paid.</span>
      </div>

      <div
        style={{
          ...TYPE_BASE,
          color: CREAM,
          fontWeight: 800,
          fontSize: u * 0.027,
          letterSpacing: '0.005em',
        }}
      >
        Matching you directly with a Phoenix injury attorney
      </div>

      <div
        style={{
          backgroundColor: PILL,
          borderRadius: u * 0.03,
          padding: `${u * 0.016}px ${u * 0.036}px`,
          marginTop: u * 0.004,
        }}
      >
        <span
          style={{
            ...TYPE_BASE,
            color: GOLD,
            fontWeight: 800,
            fontSize: u * 0.026,
            letterSpacing: '0.06em',
          }}
        >
          @AWESOMEATTYS
        </span>
        <span
          style={{
            ...TYPE_BASE,
            color: CREAM,
            fontWeight: 500,
            fontSize: u * 0.026,
            letterSpacing: '0.06em',
          }}
        >
          {'  ·  AWESOMEATTORNEYS.COM'}
        </span>
      </div>
    </div>
  );
};

/** The fine print, pinned to the bottom safe area. */
export const EndCardFinePrint: React.FC<{
  readonly layout: Layout;
  readonly lines: string[];
}> = ({layout, lines}) => {
  const u = Math.min(layout.width, layout.height * (9 / 16));
  return (
    <div
      style={{
        position: 'absolute',
        left: layout.safe.left,
        right: layout.safe.right,
        bottom: layout.safe.bottom * 0.42,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: u * 0.012,
      }}
    >
      {lines.map((line) => (
        <div
          key={line}
          style={{
            ...TYPE_BASE,
            whiteSpace: 'normal',
            textAlign: 'center',
            maxWidth: u * 0.84,
            color: CREAM,
            opacity: 0.72,
            fontWeight: 500,
            fontSize: u * 0.0195,
            lineHeight: 1.5,
          }}
        >
          {line}
        </div>
      ))}
    </div>
  );
};
