/**
 * The overlay.
 *
 * Layer order, bottom to top:
 *   1. ambient particles      (behind everything, so never in front of type)
 *   2. the 3D stage           (beats 1-3 live in one world, one camera)
 *   3. the card beats         (flat, opaque, above the stage — a cut, not a move)
 *
 * The whole thing is wrapped in `<FramePunch>` so the three 1-frame hits land
 * on the stage and the plates alike.
 *
 * There is no background anywhere. The only opaque pixels in the file are the
 * card plates; every other frame is transparent and composites straight over
 * the footage underneath (spec §7).
 */

import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {Camera3D, FramePunch} from './stage/Camera3D';
import {
  TUMBLE_AT,
  TUMBLE_DUR,
  driftsFor,
  flightFor,
  hintSpeed,
  posesFor,
  punchesFor,
} from './stage/flight';
import {Beat1} from './beats/Beat1';
import {Beat2, Beat2Card} from './beats/Beat2';
import {Beat3} from './beats/Beat3';
import {Beat4} from './beats/Beat4';
import {Particles} from './parts/Particles';
import {Backdrop} from './parts/Backdrop';
import {BEATS, CARD_WINDOWS} from './timing/beats';
import {layoutFor, makePalette, typeScale} from './theme';
import type {BeatProps, OverlayProps} from './types';

export const Overlay: React.FC<OverlayProps> = ({
  aspect,
  cards,
  tone,
  disclaimer,
  accent,
  backdrop = false,
}) => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();
  const sec = frame / fps;

  const layout = layoutFor(aspect);
  const type = typeScale(aspect);
  const palette = makePalette(accent);
  const poses = posesFor(layout);

  const keys = flightFor(layout, fps);
  const drifts = driftsFor(fps);
  const punches = punchesFor(fps);
  const speedHint = hintSpeed(sec, fps, layout);

  const beat: BeatProps = {layout, type, palette, tone, poses, cards, disclaimer};

  const f = (seconds: number) => Math.round(seconds * fps);

  // Beat 1 outlives its own line: it still owns the "40%" group while beat 2
  // strikes it through and tumbles it out of the world.
  const beat1End = TUMBLE_AT(fps) + TUMBLE_DUR + 0.2;

  return (
    <FramePunch punches={punches}>
      <AbsoluteFill>
        {/* 0 — the moving photographic background, when this is a finished
            video rather than a transparent overlay. It sits inside
            <FramePunch> so the three 1-frame hits land on it too. */}
        {backdrop ? <Backdrop layout={layout} /> : null}

        {/* 1 — ambient particles, always behind the type */}
        <Particles
          layout={layout}
          color={palette.gold}
          fadeInAt={0.35}
          fadeOutAt={BEATS.b4.start}
          opacity={0.9}
          paused={cards ? [CARD_WINDOWS.not] : []}
        />

        {/* 2 — the 3D world */}
        <Camera3D layout={layout} keys={keys} drifts={drifts} speedHint={speedHint}>
          <Sequence
            name="Beat 1 — deflated"
            layout="none"
            from={f(BEATS.b1.start)}
            durationInFrames={f(beat1End - BEATS.b1.start)}
          >
            <Beat1 {...beat} />
          </Sequence>

          <Sequence
            name="Beat 2 — knowing"
            layout="none"
            from={f(BEATS.b2.start)}
            durationInFrames={f(BEATS.b2.duration)}
          >
            <Beat2 {...beat} />
          </Sequence>

          <Sequence
            name="Beat 3 — warm"
            layout="none"
            from={f(BEATS.b3.start)}
            durationInFrames={f(BEATS.b3.duration)}
          >
            <Beat3 {...beat} />
          </Sequence>
        </Camera3D>

        {/* 3 — the card beats, above the stage */}
        <Sequence
          name="Card — NOT A LEGAL FINDING"
          layout="none"
          from={f(BEATS.b2.start)}
          durationInFrames={f(BEATS.b2.duration)}
        >
          <Beat2Card {...beat} />
        </Sequence>

        <Sequence
          name="Beat 4 — decisive + end card"
          layout="none"
          from={f(BEATS.b4.start)}
          durationInFrames={f(BEATS.b4.duration)}
        >
          <Beat4 {...beat} />
        </Sequence>
      </AbsoluteFill>
    </FramePunch>
  );
};
