/**
 * Shared motion helpers.
 *
 * Rules encoded here (spec §6):
 *  - every duration is authored in SECONDS and converted through `useSec()`,
 *    so changing `FPS` in Root.tsx re-times the whole piece;
 *  - entrances are overdamped springs, exits are expo-in, camera flights are
 *    expo-in-out, settles are overdamped;
 *  - reveals are compound (mask/translate/scale + opacity), never opacity alone;
 *  - nothing uses CSS transitions/animations, timers or Math.random().
 */

import React from 'react';
import {
  Easing,
  interpolate,
  random,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {Trail} from '@remotion/motion-blur';
import {LEAD_FRAMES} from '../timing/beats';

/* ------------------------------------------------------------------ *
 * Time
 * ------------------------------------------------------------------ */

/** `const sec = useSec(); sec(0.45)` -> frames. fps comes from the composition. */
export const useSec = (): ((seconds: number) => number) => {
  const {fps} = useVideoConfig();
  return React.useCallback((seconds: number) => seconds * fps, [fps]);
};

/** Current frame expressed in seconds. */
export const useNow = (): number => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return frame / fps;
};

/**
 * Inside a beat `<Sequence>`, `useCurrentFrame()` restarts at 0. These convert
 * the global seconds in `beats.ts` into that local clock, so a scene still only
 * ever names a spoken word — never a frame.
 *
 * `useHit` also applies the 3-frame lead: every visual lands `LEAD_FRAMES`
 * before the word is spoken.
 */
export const useHit = (
  windowStart: number,
): ((globalSec: number, extraLeadFrames?: number) => number) => {
  const {fps} = useVideoConfig();
  return React.useCallback(
    (globalSec: number, extraLeadFrames = 0) =>
      globalSec - windowStart - (LEAD_FRAMES + extraLeadFrames) / fps,
    [fps, windowStart],
  );
};

/** Same conversion without the lead — for exits and holds. */
export const useLocal = (windowStart: number): ((globalSec: number) => number) =>
  React.useCallback((globalSec: number) => globalSec - windowStart, [windowStart]);

/* ------------------------------------------------------------------ *
 * Easings & spring configs
 * ------------------------------------------------------------------ */

export const EASE = {
  /** exits, and anything that should leave decisively */
  expoIn: Easing.bezier(0.7, 0, 0.84, 0),
  /** arrivals, wipes, line draws */
  expoOut: Easing.bezier(0.16, 1, 0.3, 1),
  /** camera flights */
  expoInOut: Easing.bezier(0.87, 0, 0.13, 1),
  /** gentle, for drifts and de-emphasis */
  smooth: Easing.bezier(0.4, 0, 0.2, 1),
  /** slow settle used inside beat 1 */
  heavy: Easing.bezier(0.33, 0, 0.15, 1),
} as const;

export const SPRING = {
  /** every ordinary entrance */
  overdamped: {damping: 200, stiffness: 100, mass: 1},
  /** beat 1 — the slowest springs in the spot */
  heavy: {damping: 200, stiffness: 70, mass: 1},
  /** settles after a camera flight */
  settle: {damping: 200, stiffness: 130, mass: 1},
  /** the only three overshoots in the piece: the 40% slam and both card slams */
  overshoot: {damping: 16, stiffness: 200, mass: 1},
} as const;

/* ------------------------------------------------------------------ *
 * Progress helpers — all take seconds
 * ------------------------------------------------------------------ */

export const clamp = (v: number, lo = 0, hi = 1): number =>
  Math.min(hi, Math.max(lo, v));

export const mix = (a: number, b: number, p: number): number => a + (b - a) * p;

type EaseFn = (n: number) => number;

/** Eased 0 -> 1 ramp starting at `atSec`, lasting `durSec`. */
export const useRamp = (
  atSec: number,
  durSec: number,
  easing: EaseFn = EASE.expoOut,
): number => {
  const frame = useCurrentFrame();
  const sec = useSec();
  return interpolate(frame, [sec(atSec), sec(atSec + durSec)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing,
  });
};

/** Spring 0 -> 1 starting at `atSec`. */
export const useSpringAt = (
  atSec: number,
  config: {damping: number; stiffness: number; mass: number} = SPRING.overdamped,
  durationInSec?: number,
): number => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({
    frame: frame - atSec * fps,
    fps,
    config,
    durationInFrames: durationInSec === undefined ? undefined : durationInSec * fps,
  });
};

/**
 * In-and-out envelope. Rises (overdamped spring) at `inAt`, falls (expo-in) at
 * `outAt`. Omit `outAt` for something that never leaves.
 */
export const useInOut = (opts: {
  inAt: number;
  inDur?: number;
  outAt?: number;
  outDur?: number;
  inConfig?: {damping: number; stiffness: number; mass: number};
  outEasing?: EaseFn;
}): {in: number; out: number; value: number} => {
  const {
    inAt,
    inDur = 0.55,
    outAt,
    outDur = 0.4,
    inConfig = SPRING.overdamped,
    outEasing = EASE.expoIn,
  } = opts;
  const inP = useSpringAt(inAt, inConfig, inDur);
  const outP = useRamp(outAt ?? 1e6, outDur, outEasing);
  return {in: inP, out: outP, value: inP * (1 - outP)};
};

/** Deterministic 0..1 loop phase with period `periodSec`. */
export const useLoop = (periodSec: number, offset = 0): number => {
  const now = useNow();
  const p = (now / periodSec + offset) % 1;
  return p < 0 ? p + 1 : p;
};

/** 0..1 sine at `hz`, for slow breathing glows and pills. */
export const useBreath = (hz: number, offset = 0): number => {
  const now = useNow();
  return 0.5 + 0.5 * Math.sin(2 * Math.PI * (hz * now + offset));
};

/* ------------------------------------------------------------------ *
 * Compound reveals
 * ------------------------------------------------------------------ */

export type WipeDirection = 'up' | 'down' | 'left' | 'right';

const GRADIENT_DIR: Record<WipeDirection, string> = {
  up: 'to top',
  down: 'to bottom',
  left: 'to left',
  right: 'to right',
};

/**
 * A hard-edged mask wipe. Multiplies the child's alpha — it never introduces a
 * background and never blends with the footage underneath.
 *
 * `progress` 0 = fully hidden, 1 = fully revealed.
 */
export const MaskReveal: React.FC<{
  readonly progress: number;
  readonly direction?: WipeDirection;
  /** width of the soft edge, in % of the box */
  readonly softness?: number;
  readonly style?: React.CSSProperties;
  readonly children: React.ReactNode;
}> = ({progress, direction = 'up', softness = 6, style, children}) => {
  const a = progress * (100 + softness) - softness;
  const mask = `linear-gradient(${GRADIENT_DIR[direction]}, #000 ${a}%, rgba(0,0,0,0) ${
    a + softness
  }%)`;
  return (
    <div
      style={{
        ...style,
        WebkitMaskImage: mask,
        maskImage: mask,
        WebkitMaskSize: '100% 100%',
        maskSize: '100% 100%',
        WebkitMaskRepeat: 'no-repeat',
        maskRepeat: 'no-repeat',
      }}
    >
      {children}
    </div>
  );
};

/**
 * The default entrance: a mask wipe plus a short travel and a scale — never an
 * opacity-only fade. `p` is the driving progress (usually an overdamped spring).
 */
export const Reveal: React.FC<{
  readonly p: number;
  readonly direction?: WipeDirection;
  /** px of travel that the element covers as it arrives */
  readonly travel?: number;
  readonly scaleFrom?: number;
  readonly softness?: number;
  readonly style?: React.CSSProperties;
  readonly children: React.ReactNode;
}> = ({p, direction = 'up', travel = 34, scaleFrom = 0.94, softness = 8, style, children}) => {
  const axis = direction === 'up' || direction === 'down' ? 'Y' : 'X';
  const sign = direction === 'up' || direction === 'left' ? 1 : -1;
  const offset = (1 - p) * travel * sign;
  return (
    <MaskReveal progress={p} direction={direction} softness={softness} style={style}>
      <div
        style={{
          transform: `translate${axis}(${offset}px) scale(${mix(scaleFrom, 1, p)})`,
          transformOrigin: 'center',
        }}
      >
        {children}
      </div>
    </MaskReveal>
  );
};

/* ------------------------------------------------------------------ *
 * Motion blur
 * ------------------------------------------------------------------ */

/** px/frame above which a move must carry blur (spec §2.8 / §6). */
export const BLUR_FLOOR = 8;
export const BLUR_CEILING = 95;

/**
 * `<Trail>` driven by measured speed.
 *
 * `<Trail>` stacks frozen copies of its children *behind* the live one. When
 * nothing moves those copies sit exactly under the live copy, so the component
 * is a visual no-op — which means it can stay mounted for the whole piece and
 * never pop in or out. `trailOpacity` ramps continuously with `speed`
 * (px/frame), so the blur appears exactly as fast motion starts and is gone by
 * the time the move settles.
 */
export const SpeedTrail: React.FC<{
  /** px travelled by the fastest element between this frame and the last */
  readonly speed: number;
  readonly layers?: number;
  readonly lagInFrames?: number;
  readonly maxOpacity?: number;
  readonly children: React.ReactNode;
}> = ({speed, layers = 6, lagInFrames = 0.66, maxOpacity = 0.85, children}) => {
  const trailOpacity = interpolate(
    speed,
    [BLUR_FLOOR, BLUR_CEILING],
    [0, maxOpacity],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  return (
    <Trail layers={layers} lagInFrames={lagInFrames} trailOpacity={trailOpacity}>
      {children}
    </Trail>
  );
};

/* ------------------------------------------------------------------ *
 * Deterministic noise
 * ------------------------------------------------------------------ */

/** `random()` from Remotion — seeded, identical on every machine and render. */
export const rnd = (seed: string, lo = 0, hi = 1): number =>
  lo + random(seed) * (hi - lo);

/* ------------------------------------------------------------------ *
 * Small formatting helpers
 * ------------------------------------------------------------------ */

export const px = (n: number): string => `${n}px`;

/** rgba from #rrggbb — re-exported so parts only import from lib. */
export {rgba} from '../theme';
