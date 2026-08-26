/**
 * The optional "film frame": a vignette, plus 2.39 letterbox bars on 16x9.
 *
 * Shipped as its own `.mov` so the frame can be added or dropped per cut in the
 * edit without re-rendering the overlay. It is completely static — `fade` is
 * false by default, so frame 0 looks exactly like the last frame and the clip
 * can be looped, held or trimmed to any length.
 *
 * The vignette is semi-transparent alpha, which is expected; the letterbox bars
 * are the only opaque pixels.
 */

import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {EASE} from './overlays/lib';
import {layoutFor} from './theme';
import type {Aspect} from './theme';

export type FrameLayerProps = {
  readonly aspect: Aspect;
  readonly vignette: number;
  readonly bars: boolean;
  /** leave false to keep the clip loopable */
  readonly fade: boolean;
};

/** 2.39:1 bar height for a given frame. */
const barHeight = (width: number, height: number): number =>
  Math.max(0, Math.round((height - width / 2.39) / 2));

export const FrameLayer: React.FC<FrameLayerProps> = ({aspect, vignette, bars, fade}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const layout = layoutFor(aspect);

  const alpha = fade
    ? interpolate(
        frame,
        [0, 0.5 * fps, durationInFrames - 0.5 * fps, durationInFrames],
        [0, 1, 1, 0],
        {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.smooth},
      )
    : 1;

  const h = bars ? barHeight(layout.width, layout.height) : 0;

  return (
    <AbsoluteFill style={{opacity: alpha}}>
      <AbsoluteFill
        style={{
          backgroundImage: `radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 42%, rgba(0,0,0,${(
            vignette * 0.45
          ).toFixed(3)}) 78%, rgba(0,0,0,${vignette.toFixed(3)}) 100%)`,
        }}
      />
      {h > 0 ? (
        <>
          <div
            style={{position: 'absolute', left: 0, right: 0, top: 0, height: h, backgroundColor: '#000'}}
          />
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              bottom: 0,
              height: h,
              backgroundColor: '#000',
            }}
          />
        </>
      ) : null}
    </AbsoluteFill>
  );
};
