/**
 * Ambient particles.
 *
 * 16 small gold dots, soft-edged (a radial gradient, so the softness is real
 * pixels and not a filter), slow, and seeded with Remotion's `random()` so
 * every render is identical. They are the first thing in the DOM inside each
 * beat, so they are always behind the type — never in front of it.
 *
 * They stop dead during card beats and resume where they left off: `paused`
 * windows are subtracted from the clock rather than clamping it, so nothing
 * jumps when a card ends.
 */

import React from 'react';
import {AbsoluteFill, random} from 'remotion';
import {EASE, useNow, useRamp, rgba} from '../overlays/lib';
import type {Layout} from '../theme';

export type PauseWindow = {start: number; end: number};

const COUNT = 16;

/** Wall-clock seconds with every elapsed paused window removed. */
const activeTime = (now: number, paused: PauseWindow[]): number => {
  let t = now;
  for (const w of paused) {
    if (now <= w.start) continue;
    t -= Math.min(now, w.end) - w.start;
  }
  return t;
};

export const Particles: React.FC<{
  readonly layout: Layout;
  readonly color: string;
  readonly seed?: string;
  readonly fadeInAt?: number;
  readonly fadeOutAt?: number;
  readonly paused?: PauseWindow[];
  readonly opacity?: number;
  /** keeps them out of the middle band where the type lives */
  readonly avoidBand?: number;
}> = ({
  layout,
  color,
  seed = 'aa40k',
  fadeInAt = 0.25,
  fadeOutAt,
  paused = [],
  opacity = 1,
  avoidBand = 0.34,
}) => {
  const now = useNow();
  const t = activeTime(now, paused);
  const fadeIn = useRamp(fadeInAt, 0.9, EASE.smooth);
  const fadeOut = useRamp(fadeOutAt ?? 1e6, 0.6, EASE.smooth);
  const alpha = fadeIn * (1 - fadeOut) * opacity;
  if (alpha <= 0.002) return null;

  return (
    <AbsoluteFill>
      {new Array(COUNT).fill(true).map((_, i) => {
        const k = `${seed}-${i}`;
        const size = 5 + random(`${k}-s`) * 11;
        const speed = 5 + random(`${k}-v`) * 13;
        const angle = random(`${k}-a`) * Math.PI * 2;
        const phase = random(`${k}-p`);

        // Vertical placement skips the central band so nothing drifts across
        // the hero type; horizontal wraps so the field never empties.
        const half = avoidBand / 2;
        const band = random(`${k}-y`);
        const yNorm =
          band < 0.5
            ? band * (0.5 - half) * 2
            : 1 - (1 - band) * (0.5 - half) * 2;

        const x =
          ((random(`${k}-x`) + ((t * speed) / layout.width) * Math.cos(angle) + 2) % 1) *
          layout.width;
        const y =
          yNorm * layout.height + Math.sin(t * 0.28 + phase * 6.283) * 26 * Math.sin(angle);

        const twinkle = 0.45 + 0.55 * (0.5 + 0.5 * Math.sin(t * 0.7 + phase * 6.283));

        return (
          <div
            key={k}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: size * 4,
              height: size * 4,
              marginLeft: -size * 2,
              marginTop: -size * 2,
              transform: `translate3d(${x}px, ${y}px, 0)`,
              borderRadius: '50%',
              backgroundImage: `radial-gradient(circle, ${rgba(
                color,
                0.85 * alpha * twinkle,
              )} 0%, ${rgba(color, 0.35 * alpha * twinkle)} 26%, ${rgba(color, 0)} 68%)`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/**
 * The one-off burst thrown off by the "40%" slam — 12 dots that fly out and
 * settle. Seeded, so the pattern is identical on every render.
 */
export const Burst: React.FC<{
  readonly at: number;
  readonly color: string;
  readonly count?: number;
  readonly radius: number;
  readonly seed?: string;
  readonly dotSize?: number;
}> = ({at, color, count = 12, radius, seed = 'slam', dotSize = 12}) => {
  const fly = useRamp(at, 0.55, EASE.expoOut);
  const settle = useRamp(at + 0.35, 0.9, EASE.smooth);
  const fade = useRamp(at + 0.7, 0.8, EASE.smooth);
  if (fly <= 0 || fade >= 1) return null;

  // Anchored on its parent's origin rather than on a flex box, so it emits from
  // exactly the point it is posed at whatever the parent's size is.
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 0, height: 0}}>
      {new Array(count).fill(true).map((_, i) => {
        const k = `${seed}-${i}`;
        const angle = (i / count) * Math.PI * 2 + random(`${k}-a`) * 0.5;
        const reach = radius * (0.55 + random(`${k}-r`) * 0.65);
        // out fast, then easing back a little as they settle
        const d = reach * fly * (1 - 0.16 * settle);
        const s = dotSize * (0.55 + random(`${k}-s`) * 0.9);
        return (
          <div
            key={k}
            style={{
              position: 'absolute',
              left: -s / 2,
              top: -s / 2,
              width: s,
              height: s,
              borderRadius: '50%',
              backgroundColor: color,
              opacity: (1 - fade) * (0.35 + 0.65 * (1 - settle * 0.5)),
              transform: `translate3d(${Math.cos(angle) * d}px, ${
                Math.sin(angle) * d
              }px, 0) scale(${1 - 0.35 * settle})`,
            }}
          />
        );
      })}
    </div>
  );
};
