/**
 * Design system for the "40% At Fault" alpha overlay.
 *
 * One typeface (two weights), six colour tokens, and a pair of layout token
 * sets (9x16 / 16x9). Every scene reads from here — no scene hard-codes a
 * colour, a font size or a safe-zone number.
 */

import {BRAND} from './brand.generated';

export type Aspect = '9x16' | '16x9';
export type Tone = 'dark' | 'light' | 'mixed';

/* ------------------------------------------------------------------ *
 * Palette
 * ------------------------------------------------------------------ */

export const PALETTE = {
  white: '#FFFFFF',
  gold: BRAND.gold,
  ink: BRAND.ink,
  red: '#D0483C',
  steel: '#8A94A6',
  scrim: 'rgba(8,12,20,0.55)',
} as const;

export type Palette = {
  white: string;
  gold: string;
  ink: string;
  red: string;
  steel: string;
  scrim: string;
};

/** Resolve the palette, letting the `accent` prop override `gold`. */
export const makePalette = (accent?: string): Palette => ({
  ...PALETTE,
  gold: accent ?? PALETTE.gold,
});

/** `rgba()` from a #rrggbb token. */
export const rgba = (hex: string, alpha: number): string => {
  const h = hex.replace('#', '');
  const full =
    h.length === 3
      ? h
          .split('')
          .map((c) => c + c)
          .join('')
      : h;
  const r = parseInt(full.slice(0, 2), 16);
  const g = parseInt(full.slice(2, 4), 16);
  const b = parseInt(full.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

/* ------------------------------------------------------------------ *
 * Typography — one family, two weights
 * ------------------------------------------------------------------ */

export const FONT_FAMILY = BRAND.font;

export const WEIGHT = {
  hero: 800,
  label: 500,
  url: 700,
} as const;

/**
 * Type sizes are authored in 9x16 pixels (the primary deliverable).
 * 16x9 divides by TYPE_RATIO, i.e. 9x16 is 1.12x larger — per spec §3.
 */
export const TYPE_RATIO = 1.12;

const TYPE_9x16 = {
  /** beat 1 small word — "adjuster" */
  small: 72,
  /** beat 1 second word — "you're" */
  medium: 104,
  /**
   * The "40%" stamp. Spec asks for ~380; 360 is what actually keeps the
   * rotated stamp box inside the 6% side safe area once Manrope 800's real
   * glyph widths (~0.69em, not the 0.62em a rough estimate gives) and the
   * -6 degree tilt are accounted for.
   */
  hero: 360,
  /** "OPENING" */
  heroWord: 150,
  /** "POSITION" */
  secondaryWord: 96,
  /** card headline — "GET MATCHED." */
  card: 150,
  /** "NOT" on the ink card */
  cardHero: 190,
  /** "A LEGAL FINDING" */
  cardSub: 62,
  /** "PHOENIX" */
  place: 96,
  /** "DIRECTLY" — sized so it clears the safe area at the end of its travel */
  travel: 68,
  /** wordmark line */
  wordmark: 86,
  /** the URL */
  url: 62,
  /** small-caps labels — "AT FAULT", "YOU", "ATTORNEY" */
  label: 48,
  /** the smallest label in the piece — dot labels & chip */
  labelSmall: 34,
  /** pill text */
  pill: 40,
  /** disclaimer (spec says 26; raised to 28 so the QA >= 28px floor holds
   *  on 16x9 too, where every size is divided by TYPE_RATIO) */
  disclaimer: 32,
} as const;

export type TypeScale = typeof TYPE_9x16;

export const typeScale = (aspect: Aspect): TypeScale => {
  if (aspect === '9x16') return TYPE_9x16;
  const out = {} as Record<keyof TypeScale, number>;
  (Object.keys(TYPE_9x16) as (keyof TypeScale)[]).forEach((k) => {
    out[k] = Math.round((TYPE_9x16[k] / TYPE_RATIO) * 10) / 10;
  });
  return out as TypeScale;
};

export const TRACKING = {
  hero: '-0.03em',
  label: '0.16em',
  wordmark: '0.12em',
} as const;

/* ------------------------------------------------------------------ *
 * Legibility over unknown footage
 * ------------------------------------------------------------------ */

const TONE_GAIN: Record<Tone, number> = {
  dark: 0.8,
  mixed: 1,
  light: 2,
};

/**
 * The two-part shadow that every piece of type over footage carries.
 * `light` doubles the strength (extra tight layer + raised alphas) so white
 * type still separates from a bright sky.
 */
export const textShadow = (tone: Tone, scale = 1): string => {
  const k = TONE_GAIN[tone];
  const soft = Math.min(0.95, 0.55 * k);
  const tight = Math.min(0.95, 0.4 * k);
  const blur = Math.round(24 * scale);
  const layers = [
    `0 ${Math.round(2 * scale)}px ${blur}px rgba(0,0,0,${soft.toFixed(3)})`,
    `0 0 ${Math.round(2 * scale)}px rgba(0,0,0,${tight.toFixed(3)})`,
  ];
  if (k > 1) {
    // second pass — the "doubled" shadow for light footage
    layers.push(`0 0 ${Math.round(8 * scale)}px rgba(0,0,0,${tight.toFixed(3)})`);
  }
  return layers.join(', ');
};

/**
 * For type below ~40px. A wide soft shadow is what keeps a 150px headline off
 * the footage, but at label size the glyph strokes are thinner than the blur, so
 * the halo washes straight through them. These add a tight, dense ring that acts
 * like an outline — the small-caps labels then hold up even on a white plate.
 */
export const labelShadow = (tone: Tone, scale = 1): string => {
  const k = TONE_GAIN[tone];
  const tight = Math.min(0.95, 0.72 * k);
  const mid = Math.min(0.9, 0.5 * k);
  return [
    textShadow(tone, scale),
    `0 0 ${Math.round(3 * scale)}px rgba(0,0,0,${tight.toFixed(3)})`,
    `0 0 ${Math.round(7 * scale)}px rgba(0,0,0,${mid.toFixed(3)})`,
  ].join(', ');
};

/** Matching drop-shadow filter for vector parts (lines, pins, rings). */
export const vectorShadow = (tone: Tone, scale = 1): string => {
  const k = TONE_GAIN[tone];
  const soft = Math.min(0.95, 0.5 * k);
  const tight = Math.min(0.95, 0.35 * k);
  const base = `drop-shadow(0 ${Math.round(2 * scale)}px ${Math.round(
    18 * scale,
  )}px rgba(0,0,0,${soft.toFixed(3)})) drop-shadow(0 0 ${Math.round(
    2 * scale,
  )}px rgba(0,0,0,${tight.toFixed(3)}))`;
  return k > 1
    ? `${base} drop-shadow(0 0 ${Math.round(6 * scale)}px rgba(0,0,0,${tight.toFixed(3)}))`
    : base;
};

/* ------------------------------------------------------------------ *
 * Layout tokens
 * ------------------------------------------------------------------ */

export type Layout = {
  aspect: Aspect;
  width: number;
  height: number;
  /** safe-area insets in px: nothing may be laid out outside these */
  safe: {top: number; right: number; bottom: number; left: number};
  /** CSS perspective distance on the camera root */
  perspective: number;
  /** how much of a word's world offset the camera travels — see Camera3D */
  camFollowXY: number;
  camFollowZ: number;
  camFollowRot: number;
  /** multiplier on all world-space travel distances */
  travel: number;
  /** stroke widths for the flat icon set */
  stroke: number;
  strokeThin: number;
  /** the YOU <-> ATTORNEY figure */
  match: {span: number; height: number; dotR: number};
  pinSize: number;
  /** 9x16 stacks the wordmark on two lines; 16x9 has room for one */
  wordmarkStack: boolean;
};

export const layoutFor = (aspect: Aspect): Layout => {
  if (aspect === '9x16') {
    return {
      aspect,
      width: 1080,
      height: 1920,
      // spec: keep clear of the top 14% and bottom 22%
      safe: {
        top: Math.round(1920 * 0.14),
        bottom: Math.round(1920 * 0.22),
        left: Math.round(1080 * 0.06),
        right: Math.round(1080 * 0.06),
      },
      perspective: 1600,
      camFollowXY: 0.55,
      camFollowZ: 0.25,
      camFollowRot: 0.12,
      travel: 1,
      stroke: 10,
      strokeThin: 5,
      match: {span: 660, height: 300, dotR: 22},
      pinSize: 78,
      wordmarkStack: true,
    };
  }
  return {
    aspect,
    width: 1920,
    height: 1080,
    // spec: 5% all sides
    safe: {
      top: Math.round(1080 * 0.05),
      bottom: Math.round(1080 * 0.05),
      left: Math.round(1920 * 0.05),
      right: Math.round(1920 * 0.05),
    },
    perspective: 1600,
    camFollowXY: 0.55,
    camFollowZ: 0.25,
    camFollowRot: 0.12,
    // 16x9 is wider but shorter: words spread further sideways, less vertically
    travel: 1,
    stroke: 9,
    strokeThin: 4.5,
    match: {span: 1150, height: 260, dotR: 22},
    pinSize: 70,
    wordmarkStack: false,
  };
};

/** Usable half-width / half-height inside the safe area, from frame centre. */
export const safeBox = (l: Layout) => {
  const left = l.safe.left;
  const right = l.width - l.safe.right;
  const top = l.safe.top;
  const bottom = l.height - l.safe.bottom;
  return {
    left,
    right,
    top,
    bottom,
    cx: (left + right) / 2 - l.width / 2,
    cy: (top + bottom) / 2 - l.height / 2,
    halfW: (right - left) / 2,
    halfH: (bottom - top) / 2,
  };
};
