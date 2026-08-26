/**
 * The card beats.
 *
 * A card is a flat, fully opaque colour plate that cuts in over the footage,
 * carries big type and one flat icon, and cuts back out. It is the only thing
 * in the whole piece that is allowed to fill the frame with alpha 1 — the
 * checkerboard must be visible on every other frame (spec §7).
 *
 * With `cards: false` the plate is simply not rendered; the beats then play the
 * same type over the footage with their shadows, so the prop is a real switch
 * rather than a second edit.
 */

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {EASE, SpeedTrail, useRamp} from '../overlays/lib';
import type {Layout} from '../theme';

export type PlateEntry = 'wipe-left' | 'wipe-right' | 'slam-up' | 'slam-down';
export type PlateExit = 'wipe-right' | 'wipe-left' | 'none';

/**
 * How far (in px) the plate edge travels per frame during its wipe — used to
 * drive the plate's own motion blur, since it is outside the 3D stage.
 */
const edgeSpeed = (
  progress: number,
  prevProgress: number,
  distance: number,
): number => Math.abs(progress - prevProgress) * distance;

export const CardPlate: React.FC<{
  readonly layout: Layout;
  readonly color: string;
  readonly enterAt: number;
  readonly enterDur?: number;
  readonly entry?: PlateEntry;
  readonly exitAt?: number;
  readonly exitDur?: number;
  readonly exit?: PlateExit;
  /**
   * px/frame contributed by content moving *on* the plate (the end-card settle).
   * The plate itself is static once it has landed, and `<Trail>` is a no-op for
   * static opaque pixels, so this only ever blurs what actually moves.
   */
  readonly speedHint?: number;
  readonly children?: React.ReactNode;
}> = ({
  layout,
  color,
  enterAt,
  enterDur = 0.25,
  entry = 'wipe-left',
  exitAt,
  exitDur = 0.3,
  exit = 'none',
  speedHint = 0,
  children,
}) => {
  const {fps} = useVideoConfig();

  const pIn = useRamp(enterAt, enterDur, EASE.expoOut);
  const pInPrev = useRamp(enterAt + 1 / fps, enterDur, EASE.expoOut);
  const pOut = useRamp(exitAt ?? 1e6, exitDur, EASE.expoIn);
  const pOutPrev = useRamp((exitAt ?? 1e6) + 1 / fps, exitDur, EASE.expoIn);

  const horizontal = entry === 'wipe-left' || entry === 'wipe-right';
  const distance = horizontal ? layout.width : layout.height;

  // Travel: the plate slides its full dimension into place, then (optionally)
  // slides the rest of the way out. Transform only — never left/top.
  const dir = {
    'wipe-left': {ax: -1, ay: 0},
    'wipe-right': {ax: 1, ay: 0},
    'slam-up': {ax: 0, ay: 1},
    'slam-down': {ax: 0, ay: -1},
  }[entry];

  const outDir = exit === 'wipe-right' ? 1 : exit === 'wipe-left' ? -1 : 0;

  const tx = dir.ax * (1 - pIn) * layout.width + outDir * pOut * layout.width;
  const ty = dir.ay * (1 - pIn) * layout.height;

  const speed = Math.max(
    edgeSpeed(pIn, pInPrev, distance),
    edgeSpeed(pOut, pOutPrev, layout.width),
    speedHint,
  );

  // Fully out of frame and no longer wanted: render nothing at all, so the
  // frame is genuinely transparent rather than covered by an off-screen plate.
  if (pIn <= 0 || (exit !== 'none' && pOut >= 1)) return null;

  return (
    <SpeedTrail speed={speed} maxOpacity={0.7}>
      <AbsoluteFill style={{transform: `translate3d(${tx}px, ${ty}px, 0)`}}>
        <AbsoluteFill style={{backgroundColor: color}} />
        {/* Content rides with the plate, so words leave when it leaves. */}
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
          {children}
        </AbsoluteFill>
      </AbsoluteFill>
    </SpeedTrail>
  );
};

/**
 * The bottom scrim used on the end card when `cards` is off — a transparent →
 * `scrim` gradient so the URL still reads over anything. Semi-transparent alpha
 * here is expected and correct.
 */
export const ScrimGradient: React.FC<{
  readonly layout: Layout;
  readonly scrim: string;
  readonly enterAt: number;
  readonly heightRatio?: number;
}> = ({layout, scrim, enterAt, heightRatio = 0.5}) => {
  const p = useRamp(enterAt, 0.6, EASE.expoOut);
  if (p <= 0) return null;
  return (
    <AbsoluteFill style={{opacity: p}}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: layout.height * heightRatio,
          backgroundImage: `linear-gradient(to bottom, rgba(8,12,20,0) 0%, ${scrim} 62%, ${scrim} 100%)`,
          transform: `translateY(${(1 - p) * 40}px)`,
        }}
      />
    </AbsoluteFill>
  );
};
