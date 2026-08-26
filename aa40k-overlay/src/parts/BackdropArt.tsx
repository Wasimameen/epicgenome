/**
 * The backdrops, drawn rather than photographed.
 *
 * Four scenes built in SVG, one per beat, each echoing the frame it stands in
 * for. They are not placeholders — a flat gradient behind type is exactly the
 * "boring still background" this piece is trying not to have, so these are
 * designed: real banknote guilloche for the money beats, a colonnade for the
 * court, warm panelling for the courtroom.
 *
 * Being vector, they are dead sharp at 4K, weigh nothing, need no network, and
 * are identical on every render. Drop photographs into `assets-in/bg/` and they
 * take over — the Ken Burns, the parallax and the cross-fades are the same
 * either way.
 */

import React from 'react';
import {random} from 'remotion';
import type {BackdropRole} from '../timing/backdrops';

/* ------------------------------------------------------------------ *
 * Guilloche — the engine-turned line-work on a banknote
 * ------------------------------------------------------------------ */

/**
 * A rosette: r(θ) = R + A·sin(kθ). Nested rings with a phase offset each, which
 * is how the interference pattern on currency engraving is actually made.
 */
const rosette = (
  cx: number,
  cy: number,
  ring: number,
  opts: {r0: number; step: number; amp: number; lobes: number; phase: number},
): string => {
  const {r0, step, amp, lobes, phase} = opts;
  const R = r0 + ring * step;
  const STEPS = 140;
  let d = '';
  for (let i = 0; i <= STEPS; i++) {
    const th = (i / STEPS) * Math.PI * 2;
    const r = R + amp * Math.sin(lobes * th + ring * phase);
    const x = cx + r * Math.cos(th);
    const y = cy + r * Math.sin(th) * 0.82; // slightly elliptical, like an iris
    d += `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)} `;
  }
  return `${d}Z`;
};

const Guilloche: React.FC<{
  readonly w: number;
  readonly h: number;
  readonly cx: number;
  readonly cy: number;
  readonly rings: number;
  readonly r0: number;
  readonly step: number;
  readonly amp: number;
  readonly lobes: number;
  readonly stroke: string;
  readonly opacity: number;
}> = ({w, h, cx, cy, rings, r0, step, amp, lobes, stroke, opacity}) => (
  <g opacity={opacity}>
    {new Array(rings).fill(true).map((_, i) => (
      <path
        key={i}
        d={rosette(cx, cy, i, {r0, step, amp, lobes, phase: 0.32})}
        fill="none"
        stroke={stroke}
        strokeWidth={Math.max(0.7, (w + h) * 0.00055)}
      />
    ))}
  </g>
);

/** Straight engraved hatching, the flat fill between rosettes on a banknote. */
const Hatch: React.FC<{
  readonly w: number;
  readonly h: number;
  readonly count: number;
  readonly stroke: string;
  readonly opacity: number;
  readonly angle: number;
  readonly seed: string;
}> = ({w, h, count, stroke, opacity, angle, seed}) => {
  const span = Math.hypot(w, h);
  return (
    <g opacity={opacity} transform={`rotate(${angle} ${w / 2} ${h / 2})`}>
      {new Array(count).fill(true).map((_, i) => {
        const t = i / (count - 1);
        const y = h / 2 - span / 2 + t * span;
        // a little waver, so the lines read as engraved rather than printed
        const wob = (random(`${seed}-${i}`) - 0.5) * span * 0.012;
        return (
          <path
            key={i}
            d={`M${w / 2 - span / 2} ${y + wob} Q ${w / 2} ${y - wob * 3} ${w / 2 + span / 2} ${y + wob}`}
            fill="none"
            stroke={stroke}
            strokeWidth={Math.max(0.6, (w + h) * 0.0004)}
          />
        );
      })}
    </g>
  );
};

/* ------------------------------------------------------------------ *
 * The four scenes
 * ------------------------------------------------------------------ */

const Adjuster: React.FC<{w: number; h: number}> = ({w, h}) => (
  <>
    <defs>
      <radialGradient id="adj-bed" cx="50%" cy="44%" r="72%">
        <stop offset="0%" stopColor="#2a2620" />
        <stop offset="58%" stopColor="#16141199" stopOpacity={1} />
        <stop offset="100%" stopColor="#0a0908" />
      </radialGradient>
    </defs>
    <rect width={w} height={h} fill="url(#adj-bed)" />
    <Hatch w={w} h={h} count={130} stroke="#c9b184" opacity={0.09} angle={-14} seed="adj-h" />
    <Hatch w={w} h={h} count={96} stroke="#c9b184" opacity={0.05} angle={72} seed="adj-v" />
    {/* the iris: concentric engraving tightening toward the centre */}
    <Guilloche
      w={w}
      h={h}
      cx={w * 0.5}
      cy={h * 0.44}
      rings={26}
      r0={w * 0.05}
      step={w * 0.028}
      amp={w * 0.017}
      lobes={11}
      stroke="#e8d3a6"
      opacity={0.3}
    />
    <ellipse cx={w * 0.5} cy={h * 0.44} rx={w * 0.055} ry={w * 0.045} fill="#070605" opacity={0.9} />
  </>
);

const Silenced: React.FC<{w: number; h: number}> = ({w, h}) => (
  <>
    <defs>
      <linearGradient id="sil-bed" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#111319" />
        <stop offset="50%" stopColor="#080a0e" />
        <stop offset="100%" stopColor="#040507" />
      </linearGradient>
    </defs>
    <rect width={w} height={h} fill="url(#sil-bed)" />
    <Guilloche
      w={w}
      h={h}
      cx={w * 0.5}
      cy={h * 0.4}
      rings={22}
      r0={w * 0.07}
      step={w * 0.031}
      amp={w * 0.014}
      lobes={7}
      stroke="#9fb0c4"
      opacity={0.16}
    />
    <Hatch w={w} h={h} count={170} stroke="#9fb0c4" opacity={0.07} angle={84} seed="sil-h" />
    {/* the band across the mouth — the whole point of the frame */}
    <rect x={-w * 0.1} y={h * 0.52} width={w * 1.2} height={h * 0.1} fill="#000" opacity={0.86} transform={`rotate(-4 ${w / 2} ${h * 0.57})`} />
    <rect x={-w * 0.1} y={h * 0.5} width={w * 1.2} height={h * 0.012} fill="#3a4250" opacity={0.5} transform={`rotate(-4 ${w / 2} ${h * 0.57})`} />
  </>
);

/**
 * Atmosphere, not architecture. A first pass drew a bright, literal colonnade
 * with a hard pediment; it read as an illustration and fought the wordmark
 * sitting in the upper third. This keeps the *idea* of a marble colonnade —
 * tall vertical rhythm, cold stone, light from above — but pushes it down the
 * frame, drops the contrast and leaves the top third as clean dark sky.
 */
const Court: React.FC<{w: number; h: number}> = ({w, h}) => {
  const COLS = 9;
  const top = h * 0.44;
  const colW = (w * 1.16) / COLS;
  return (
    <>
      <defs>
        <linearGradient id="crt-sky" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#151d27" />
          <stop offset="45%" stopColor="#101821" />
          <stop offset="100%" stopColor="#080c11" />
        </linearGradient>
        <linearGradient id="crt-col" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#2f3944" />
          <stop offset="28%" stopColor="#55606d" />
          <stop offset="72%" stopColor="#252d36" />
          <stop offset="100%" stopColor="#151a20" />
        </linearGradient>
        <linearGradient id="crt-fade" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#000" stopOpacity={0.85} />
          <stop offset="34%" stopColor="#000" stopOpacity={0} />
          <stop offset="100%" stopColor="#000" stopOpacity={0.7} />
        </linearGradient>
      </defs>
      <rect width={w} height={h} fill="url(#crt-sky)" />
      {new Array(COLS).fill(true).map((_, i) => (
        <rect
          key={i}
          x={-w * 0.08 + i * colW}
          y={top}
          width={colW * 0.52}
          height={h}
          fill="url(#crt-col)"
          opacity={0.4}
        />
      ))}
      {/* the entablature the columns carry — a line, not a slab */}
      <rect x={-w * 0.1} y={top - h * 0.03} width={w * 1.2} height={h * 0.03} fill="#3d4650" opacity={0.42} />
      <rect x={-w * 0.1} y={top - h * 0.034} width={w * 1.2} height={h * 0.004} fill="#69747f" opacity={0.34} />
      {/* keeps the top third clean for the wordmark and grounds the bottom */}
      <rect width={w} height={h} fill="url(#crt-fade)" />
    </>
  );
};

const Counsel: React.FC<{w: number; h: number}> = ({w, h}) => {
  const BANDS = 16;
  return (
    <>
      <defs>
        <radialGradient id="cns-key" cx="30%" cy="24%" r="86%">
          <stop offset="0%" stopColor="#6b4b2e" />
          <stop offset="52%" stopColor="#3a2718" />
          <stop offset="100%" stopColor="#150e08" />
        </radialGradient>
      </defs>
      <rect width={w} height={h} fill="url(#cns-key)" />
      {/* panelling */}
      {new Array(BANDS).fill(true).map((_, i) => {
        const t = i / BANDS;
        const y = t * h;
        const bh = (h / BANDS) * (0.62 + random(`cns-${i}`) * 0.5);
        return (
          <rect
            key={i}
            x={-w * 0.05}
            y={y}
            width={w * 1.1}
            height={bh}
            fill={i % 2 === 0 ? '#2a1c11' : '#3d2a19'}
            opacity={0.34}
          />
        );
      })}
      <Hatch w={w} h={h} count={80} stroke="#d8ad78" opacity={0.05} angle={2} seed="cns-g" />
      {/* the rail across the middle third, where the counsel table would sit */}
      <rect x={-w * 0.05} y={h * 0.66} width={w * 1.1} height={h * 0.014} fill="#8a6438" opacity={0.42} />
      <rect x={-w * 0.05} y={h * 0.68} width={w * 1.1} height={h * 0.32} fill="#120c07" opacity={0.55} />
    </>
  );
};

const SCENES: Record<BackdropRole, React.FC<{w: number; h: number}>> = {
  adjuster: Adjuster,
  silenced: Silenced,
  court: Court,
  counsel: Counsel,
};

/* ------------------------------------------------------------------ *
 * The drawn backdrop
 * ------------------------------------------------------------------ */

export const BackdropArt: React.FC<{
  readonly role: BackdropRole;
  readonly width: number;
  readonly height: number;
  /** 0..1 through the shot — drives the light sweep */
  readonly progress: number;
}> = ({role, width, height, progress}) => {
  // Oversized so the Ken Burns push never reaches an edge of the artwork.
  const w = Math.round(width * 1.5);
  const h = Math.round(height * 1.5);
  const Scene = SCENES[role];
  const sweep = -30 + progress * 160;

  return (
    <svg
      width="100%"
      height="100%"
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="xMidYMid slice"
      style={{display: 'block'}}
    >
      <defs>
        {/* deterministic film grain — a fixed seed, so every render matches */}
        <filter id={`grain-${role}`} x="0" y="0" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={7} result="n" />
          <feColorMatrix in="n" type="saturate" values="0" />
        </filter>
        <linearGradient id={`sweep-${role}`} x1="0%" y1="0%" x2="100%" y2="60%">
          <stop offset={`${Math.max(0, sweep - 22)}%`} stopColor="#fff" stopOpacity={0} />
          <stop offset={`${sweep}%`} stopColor="#fff" stopOpacity={0.055} />
          <stop offset={`${Math.min(100, sweep + 22)}%`} stopColor="#fff" stopOpacity={0} />
        </linearGradient>
      </defs>

      <Scene w={w} h={h} />

      {/* a slow raking light, so the drawn scenes breathe like lit surfaces */}
      <rect width={w} height={h} fill={`url(#sweep-${role})`} />

      {/* grain last — it is what stops vector art reading as vector art */}
      <rect width={w} height={h} filter={`url(#grain-${role})`} opacity={0.11} />
    </svg>
  );
};
