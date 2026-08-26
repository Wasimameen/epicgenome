/**
 * The moving background.
 *
 * Three things happen at once here, and they are what stop a photograph behind
 * type from reading as wallpaper:
 *
 *  1. **Ken Burns.** Every shot pushes in or pulls back across its whole life,
 *     alternating direction so two consecutive shots never drift the same way.
 *  2. **Camera parallax.** The backdrop is driven by the *same* camera that
 *     flies between the words — at about a twentieth of the travel. When the
 *     camera whips to "OPENING" the background leans with it, so the type and
 *     the photograph read as one shot rather than two layers.
 *  3. **The frame punch.** It sits inside `<FramePunch>`, so the three 1-frame
 *     hits land on the photograph too.
 *
 * Everything is then graded down — desaturated, darkened, ink-tinted and
 * vignetted — so the palette stays white/gold/ink and the type keeps its
 * contrast over whatever is underneath.
 *
 * With no images supplied the same motion plays over procedural gradients, so
 * the timing and the moves can be judged before the photographs land.
 */

import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {poseAt} from '../stage/Camera3D';
import {driftsFor, flightFor} from '../stage/flight';
import {SHOTS, type BackdropRole, type Shot} from '../timing/backdrops';
import {BRAND} from '../brand.generated';
import {EASE, rgba} from '../overlays/lib';
import type {Layout} from '../theme';

/* ------------------------------------------------------------------ *
 * Grade
 * ------------------------------------------------------------------ */

const GRADE = {
  /** most of the source photography is already monochrome; this brings the
   *  colour frames into the same world without killing them outright */
  saturate: 0.35,
  contrast: 1.06,
  brightness: 0.72,
  /** flat ink laid over the top, tying every frame to the palette */
  tint: 0.22,
  /** corner falloff, so the type always sits on the darkest part of the frame */
  vignette: 0.45,
} as const;

/** How much of the camera's travel the backdrop inherits. */
const PARALLAX = 0.05;
const PARALLAX_SCALE = 0.35;

/* ------------------------------------------------------------------ *
 * One shot
 * ------------------------------------------------------------------ */

const shotOpacity = (sec: number, shot: Shot): number => {
  const fadeIn = shot.fadeIn ?? shot.fade;
  const up =
    fadeIn <= 0
      ? sec >= shot.in
        ? 1
        : 0
      : interpolate(sec, [shot.in, shot.in + fadeIn], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: EASE.smooth,
        });
  const down = interpolate(sec, [shot.out - shot.fade, shot.out], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE.smooth,
  });
  return up * (1 - down);
};

/** Placeholder used until the photographs are dropped into `assets-in/bg/`. */
const PLACEHOLDER: Record<BackdropRole, [string, string]> = {
  adjuster: ['#14181f', '#3a3027'],
  silenced: ['#0d1016', '#2b2b33'],
  court: ['#101720', '#33404f'],
  counsel: ['#161018', '#3d2f28'],
};

const ShotLayer: React.FC<{
  readonly shot: Shot;
  readonly sec: number;
  readonly layout: Layout;
  readonly src: string | null;
  readonly parallax: {x: number; y: number; scale: number};
}> = ({shot, sec, layout, src, parallax}) => {
  const opacity = shotOpacity(sec, shot);
  if (opacity <= 0.002) return null;

  const life = Math.max(1e-6, shot.out - shot.in);
  const p = EASE.smooth(Math.min(1, Math.max(0, (sec - shot.in) / life)));
  const k = shot.ken;

  const scale = (k.scaleFrom + (k.scaleTo - k.scaleFrom) * p) * parallax.scale;
  const x = (k.xFrom + (k.xTo - k.xFrom) * p) * layout.width + parallax.x;
  const y = (k.yFrom + (k.yTo - k.yFrom) * p) * layout.height + parallax.y;

  const [a, b] = PLACEHOLDER[shot.role];

  return (
    <AbsoluteFill style={{opacity, overflow: 'hidden'}}>
      <AbsoluteFill
        style={{
          transform: `translate3d(${x}px, ${y}px, 0) scale(${scale})`,
          transformOrigin: '50% 50%',
        }}
      >
        {src ? (
          <Img
            src={staticFile(src)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              filter: `saturate(${GRADE.saturate}) contrast(${GRADE.contrast}) brightness(${GRADE.brightness})`,
            }}
          />
        ) : (
          <AbsoluteFill
            style={{
              backgroundImage: `linear-gradient(148deg, ${a} 0%, ${b} 58%, ${a} 100%)`,
            }}
          />
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ *
 * The layer
 * ------------------------------------------------------------------ */

export const Backdrop: React.FC<{readonly layout: Layout}> = ({layout}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sec = frame / fps;

  // The same flight plan the words are hung on — so the background leans into
  // every whip instead of sitting still behind them.
  const {cam, scale: camScale} = poseAt(sec, flightFor(layout, fps), layout, driftsFor(fps));
  const parallax = {
    x: -cam.x * PARALLAX,
    y: -cam.y * PARALLAX,
    scale: 1 + (camScale - 1) * PARALLAX_SCALE,
  };

  const files = BRAND.backdrops;

  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      {/* An opaque floor. The composed video must never have a transparent
          pixel — without this, any gap between shots would punch a hole
          straight through the finished file. */}
      <AbsoluteFill style={{backgroundColor: '#000'}} />

      {SHOTS.map((shot) => (
        <ShotLayer
          key={shot.role}
          shot={shot}
          sec={sec}
          layout={layout}
          src={files ? files[shot.role] ?? null : null}
          parallax={parallax}
        />
      ))}

      {/* ink tint — ties every frame to the palette */}
      <AbsoluteFill style={{backgroundColor: rgba(BRAND.ink, GRADE.tint)}} />

      {/* vignette — the type always lands on the darkest part of the frame */}
      <AbsoluteFill
        style={{
          backgroundImage: `radial-gradient(ellipse at 50% 46%, rgba(0,0,0,0) 34%, rgba(0,0,0,${(
            GRADE.vignette * 0.5
          ).toFixed(3)}) 72%, rgba(0,0,0,${GRADE.vignette.toFixed(3)}) 100%)`,
        }}
      />
    </AbsoluteFill>
  );
};
