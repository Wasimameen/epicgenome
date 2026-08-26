import React from 'react';
import {Composition} from 'remotion';
import type {CalculateMetadataFunction} from 'remotion';
import {Overlay} from './Overlay';
import {FrameLayer, type FrameLayerProps} from './FrameLayer';
import {TOTAL_SEC} from './timing/beats';
import type {OverlayProps} from './types';

/**
 * The one frame-rate constant in the project.
 *
 * Change it to 24 or 60 to match your footage and nothing else needs editing:
 * every duration in the piece is authored in seconds and converted through
 * `useSec()` / `useHit()`, and every composition's length is derived from
 * `TOTAL_SEC` below.
 */
export const FPS = 30;

const DURATION = Math.round(TOTAL_SEC * FPS);

/**
 * Makes ProRes 4444 + PNG + yuva444p10le the default for these compositions, so
 * an export started from the Studio carries alpha without anyone remembering
 * the flags.
 */
const alphaDefaults: CalculateMetadataFunction<OverlayProps> = () => ({
  defaultCodec: 'prores',
  defaultVideoImageFormat: 'png',
  defaultPixelFormat: 'yuva444p10le',
  defaultProResProfile: '4444',
});

const alphaDefaultsFrame: CalculateMetadataFunction<FrameLayerProps> = () => ({
  defaultCodec: 'prores',
  defaultVideoImageFormat: 'png',
  defaultPixelFormat: 'yuva444p10le',
  defaultProResProfile: '4444',
});

/**
 * The "-Full" compositions bake the moving photographic background in, so the
 * result is a finished, opaque video rather than a transparent overlay. H.264
 * is the right container for that — and it keeps the files small enough to
 * actually watch and to live in the repo.
 */
const composedDefaults: CalculateMetadataFunction<OverlayProps> = () => ({
  defaultCodec: 'h264',
  defaultVideoImageFormat: 'png',
  defaultPixelFormat: 'yuv420p',
});

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="AA40K-9x16"
        component={Overlay}
        durationInFrames={DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        calculateMetadata={alphaDefaults}
        defaultProps={{
          aspect: '9x16',
          cards: true,
          tone: 'mixed',
          disclaimer: 'Attorney matching service. Not a law firm. Not legal advice.',
        }}
      />

      <Composition
        id="AA40K-16x9"
        component={Overlay}
        durationInFrames={DURATION}
        fps={FPS}
        width={1920}
        height={1080}
        calculateMetadata={alphaDefaults}
        defaultProps={{
          aspect: '16x9',
          cards: true,
          tone: 'mixed',
          disclaimer: 'Attorney matching service. Not a law firm. Not legal advice.',
        }}
      />

      {/* Finished video: the same piece with the moving photography baked in. */}
      <Composition
        id="AA40K-9x16-Full"
        component={Overlay}
        durationInFrames={DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        calculateMetadata={composedDefaults}
        defaultProps={{
          aspect: '9x16',
          cards: true,
          tone: 'mixed',
          disclaimer: 'Attorney matching service. Not a law firm. Not legal advice.',
          backdrop: true,
        }}
      />

      <Composition
        id="AA40K-16x9-Full"
        component={Overlay}
        durationInFrames={DURATION}
        fps={FPS}
        width={1920}
        height={1080}
        calculateMetadata={composedDefaults}
        defaultProps={{
          aspect: '16x9',
          cards: true,
          tone: 'mixed',
          disclaimer: 'Attorney matching service. Not a law firm. Not legal advice.',
          backdrop: true,
        }}
      />

      <Composition
        id="FrameLayer-9x16"
        component={FrameLayer}
        durationInFrames={DURATION}
        fps={FPS}
        width={1080}
        height={1920}
        calculateMetadata={alphaDefaultsFrame}
        defaultProps={{aspect: '9x16', vignette: 0.45, bars: false, fade: false}}
      />

      <Composition
        id="FrameLayer-16x9"
        component={FrameLayer}
        durationInFrames={DURATION}
        fps={FPS}
        width={1920}
        height={1080}
        calculateMetadata={alphaDefaultsFrame}
        defaultProps={{aspect: '16x9', vignette: 0.45, bars: true, fade: false}}
      />
    </>
  );
};
