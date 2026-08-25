import React from 'react';
import {AbsoluteFill, Audio, Easing, interpolate, random, staticFile, useCurrentFrame} from 'remotion';
import {useTransparent} from '../alpha';

/**
 * "Adjuster" — kinetic typography over a b-roll window. 60fps, 14.1s.
 *
 * Layout contract: the middle of the frame (28%-70% vertically) stays EMPTY —
 * no type, no ornament, no drawn frame — so the alpha version overlays footage.
 * Graphics live in a top zone and a bottom zone.
 *
 * Motion system, three layers with distinct jobs:
 *  - WORDS enter fast: masked baseline rises, 12-16 frames on an ease-out
 *    bezier, then hold dead still (kinetic-type standard);
 *  - BLOCKS transition with the smooth cinematic blur: a soft defocus push
 *    (blur 0-10px + short travel) whenever a section hands off — fast, but
 *    with the filmic softness a hard swap lacks;
 *  - AMBIENT elements drift continuously on slow sine eases: gold particles,
 *    thin rotating rings, occasional light streaks — smooth, never snapping,
 *    confined to the two zones and the frame edges.
 *
 * Cues are word timestamps of public/audio/vo-adjuster.mp3:
 *   "So an adjuster told you you're 40% at fault."  0.00 - 2.38
 *   "That's their opening position,"                3.48 - 4.00
 *   "not a legal finding."                          4.82 - 5.42
 *   "Awesome attorneys ... Phoenix injury attorney" 6.70 - 9.50
 *   "Get matched," / "get paid,"                    10.46 / 11.32
 *   "awesomeattorneys.com"                          12.36 - 13.10
 */
const FPS = 60;
const at = (sec: number) => Math.round(sec * FPS);
export const ADJUSTER_CINE_FPS = FPS;
export const ADJUSTER_CINE_FRAMES = at(14.106) + 8;

const B = {
  kicker: at(0.3),
  kickerOut: at(3.28),
  forty: at(1.42),
  atFault: at(2.08),
  opening: at(3.42),
  strike: at(4.78),
  finding: at(4.9),
  act1Out: at(6.24),
  brand: at(6.52),
  phoenix: at(8.68),
  matched: at(10.32),
  paid: at(11.18),
  ctaOut: at(12.02),
  url: at(12.26),
};

const PAPER = '#f5f2ea';
const GOLD = '#e3b34c';
const RED = '#e5484d';
const INK = '#0b0b0d';

const OUT = Easing.bezier(0.16, 1, 0.3, 1);
const IN = Easing.bezier(0.55, 0, 0.9, 0.2);

const ease = (frame: number, from: number, dur: number, a: number, b: number, curve = OUT) =>
  interpolate(frame, [from, from + dur], [a, b], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: curve,
  });

/* ------------------------------------------------------ block transitions */

/**
 * The cinematic handoff: blocks arrive and leave through a soft defocus push.
 * Fast (16-18 frames) so pace never sags, blurred so the change feels filmic.
 */
const blockStyle = (frame: number, inAt: number, outAt?: number): React.CSSProperties => {
  const enter = ease(frame, inAt, 18, 0, 1);
  const exit = outAt !== undefined ? ease(frame, outAt, 14, 0, 1, IN) : 0;
  const blur = (1 - enter) * 10 + exit * 10;
  return {
    opacity: enter * (1 - exit),
    transform: `translateY(${(1 - enter) * 42 - exit * 42}px)`,
    filter: blur > 0.3 ? `blur(${blur}px)` : undefined,
  };
};

/* ---------------------------------------------------------------- reveals */

/** Masked baseline rise, per word — fast in, then dead still. */
const Rise: React.FC<{
  text: string;
  atFrame: number;
  dur?: number;
  stagger?: number;
  style: React.CSSProperties;
}> = ({text, atFrame, dur = 14, stagger = 4, style}) => {
  const frame = useCurrentFrame();
  if (frame < atFrame) return null;
  return (
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', columnGap: '0.28em', ...style}}>
      {text.split(' ').map((word, i) => {
        const y = ease(frame, atFrame + i * stagger, dur, 108, 0);
        return (
          <span key={i} style={{display: 'inline-block', overflow: 'hidden', verticalAlign: 'top'}}>
            <span style={{display: 'inline-block', transform: `translateY(${y}%)`}}>{word}</span>
          </span>
        );
      })}
    </div>
  );
};

/** A thin gold rule that sweeps to width on cue. */
const Rule: React.FC<{atFrame: number; width: number; color?: string}> = ({atFrame, width, color = GOLD}) => {
  const frame = useCurrentFrame();
  if (frame < atFrame) return null;
  return (
    <div style={{width: ease(frame, atFrame, 16, 0, width), height: 3, background: color, borderRadius: 2}} />
  );
};

/* ------------------------------------------------------- ambient graphics */

/** Gold particles drifting in the two zones — smooth sine motion, no snaps. */
const Particles: React.FC = () => {
  const frame = useCurrentFrame();
  const dots = React.useMemo(
    () =>
      new Array(30).fill(0).map((_, i) => {
        const topBand = random(`pb-${i}`) > 0.5;
        return {
          x: random(`px-${i}`) * 100,
          y: topBand ? random(`py-${i}`) * 24 + 1 : 72 + random(`py-${i}`) * 25,
          r: 2 + random(`pr-${i}`) * 4.5,
          rise: 0.008 + random(`ps-${i}`) * 0.012,
          sway: 1 + random(`pw-${i}`) * 2.2,
          phase: random(`pp-${i}`) * 6.28,
          band: topBand ? [1, 25] : [72, 97],
          o: 0.2 + random(`po-${i}`) * 0.45,
        };
      }),
    [],
  );

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {dots.map((d, i) => {
        const span = d.band[1] - d.band[0];
        const y = d.band[0] + ((((d.y - d.band[0] - frame * d.rise) % span) + span) % span);
        const x = d.x + Math.sin(frame * 0.006 + d.phase) * d.sway;
        const twinkle = 0.55 + Math.sin(frame * 0.02 + d.phase) * 0.45;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${x}%`,
              top: `${y}%`,
              width: d.r,
              height: d.r,
              borderRadius: '50%',
              background: GOLD,
              opacity: d.o * twinkle,
              filter: d.r > 4.5 ? 'blur(1.5px)' : undefined,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/** Thin rings rotating slowly at the frame corners — outside the window. */
const Rings: React.FC = () => {
  const frame = useCurrentFrame();
  const ring = (x: number, y: number, r: number, rate: number, o: number, dash?: string) => (
    <div
      style={{
        position: 'absolute',
        left: `${x}%`,
        top: `${y}%`,
        transform: `translate(-50%,-50%) rotate(${frame * rate}deg) scale(${1 + Math.sin(frame * 0.006 + r) * 0.025})`,
        opacity: o,
        pointerEvents: 'none',
      }}
    >
      <svg width={r * 2} height={r * 2} viewBox={`0 0 ${r * 2} ${r * 2}`}>
        <circle cx={r} cy={r} r={r - 2} fill="none" stroke={GOLD} strokeWidth="1.4" strokeDasharray={dash} />
      </svg>
    </div>
  );
  return (
    <>
      {ring(91, 6.5, 110, 0.05, 0.4)}
      {ring(91, 6.5, 78, -0.08, 0.3, '4 8')}
      {ring(8, 94, 130, -0.045, 0.35)}
      {ring(8, 94, 92, 0.07, 0.25, '2 10')}
    </>
  );
};

/** Occasional soft glints sweeping through the zones. */
const Streaks: React.FC = () => {
  const frame = useCurrentFrame();
  const rows = React.useMemo(
    () =>
      new Array(4).fill(0).map((_, i) => ({
        y: i < 2 ? 4 + random(`sy-${i}`) * 20 : 74 + random(`sy-${i}`) * 20,
        len: 20 + random(`sl-${i}`) * 22,
        period: 460 + random(`sp-${i}`) * 380,
        offset: random(`so-${i}`) * 800,
        tilt: -14 - random(`st-${i}`) * 8,
      })),
    [],
  );
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: 0.4}}>
      {rows.map((s, i) => {
        const p = ((frame + s.offset) % s.period) / s.period;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${interpolate(p, [0, 1], [-35, 125])}%`,
              top: `${s.y}%`,
              width: `${s.len}%`,
              height: 2,
              transform: `rotate(${s.tilt}deg)`,
              background: 'linear-gradient(90deg, transparent, rgba(245,238,215,0.75), transparent)',
              filter: 'blur(1px)',
              opacity: Math.sin(p * Math.PI) * 0.7,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------- background */

const Ground: React.FC = () => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(ellipse 120% 70% at 50% 40%, #16161a 0%, ${INK} 68%, #070708 100%)`,
    }}
  />
);

const FilmGrain: React.FC = () => {
  const frame = useCurrentFrame();
  const seed = Math.floor(frame / 2);
  const specks = React.useMemo(
    () =>
      new Array(220).fill(0).map((_, i) => ({
        x: random(`fx-${seed}-${i}`) * 100,
        y: random(`fy-${seed}-${i}`) * 100,
        o: random(`fo-${seed}-${i}`),
      })),
    [seed],
  );
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: 0.05, mixBlendMode: 'overlay'}}>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{width: '100%', height: '100%'}}>
        {specks.map((s, i) => (
          <rect key={i} x={s.x} y={s.y} width={0.22} height={0.22} fill="#fff" opacity={s.o} />
        ))}
      </svg>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ scene */

const TOP: React.CSSProperties = {
  position: 'absolute',
  left: 0,
  right: 0,
  top: '4.5%',
  height: '23%',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 18,
};

const BOTTOM: React.CSSProperties = {
  position: 'absolute',
  left: 0,
  right: 0,
  top: '71.5%',
  height: '24%',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 18,
};

export const AdjusterCinematic: React.FC<{withAudio?: boolean}> = ({withAudio = true}) => {
  const alpha = useTransparent();
  const frame = useCurrentFrame();

  const strike = ease(frame, B.strike, 9, 0, 1);
  const dimmed = ease(frame, B.strike, 12, 1, 0.32);

  return (
    <AbsoluteFill style={{backgroundColor: alpha ? 'transparent' : INK}}>
      {withAudio ? <Audio src={staticFile('audio/vo-adjuster.mp3')} /> : null}
      {!alpha && <Ground />}

      {/* ambient graphics — smooth continuous motion, zones and edges only */}
      <Particles />
      <Rings />
      <Streaks />

      {/* =========================== ACT 1 — TOP =========================== */}
      <div style={{...TOP, ...blockStyle(frame, B.kicker, B.act1Out)}}>
        {/* kicker hands off to the opening-position line through the blur push */}
        <div style={{position: 'relative', height: 46, width: '100%'}}>
          <div style={{position: 'absolute', inset: 0, display: 'flex', justifyContent: 'center', ...blockStyle(frame, B.kicker, B.kickerOut)}}>
            <Rise
              text="THE ADJUSTER SAYS"
              atFrame={B.kicker + 2}
              stagger={3}
              style={{fontFamily: 'var(--body), sans-serif', fontWeight: 700, fontSize: 33, letterSpacing: '0.32em', textIndent: '0.32em', color: GOLD}}
            />
          </div>
          <div style={{position: 'absolute', inset: 0, display: 'flex', justifyContent: 'center', ...blockStyle(frame, B.opening)}}>
            <Rise
              text="THAT'S THEIR OPENING POSITION"
              atFrame={B.opening + 2}
              stagger={3}
              style={{fontFamily: 'var(--body), sans-serif', fontWeight: 700, fontSize: 33, letterSpacing: '0.2em', textIndent: '0.2em', color: GOLD}}
            />
          </div>
        </div>

        <div style={{display: 'flex', alignItems: 'center', gap: 30}}>
          <div style={{position: 'relative', opacity: dimmed}}>
            <Rise
              text="40%"
              atFrame={B.forty}
              dur={16}
              style={{fontFamily: 'var(--display), sans-serif', fontSize: 210, lineHeight: 0.94, color: PAPER, letterSpacing: '-0.01em'}}
            />
            <div
              style={{
                position: 'absolute',
                left: '50%',
                top: '50%',
                width: strike * 420,
                height: 11,
                transform: 'translate(-50%,-50%) rotate(-8deg)',
                background: RED,
                borderRadius: 6,
                opacity: strike > 0 ? 1 : 0,
              }}
            />
          </div>
          <div style={{opacity: dimmed}}>
            <Rise
              text="AT FAULT"
              atFrame={B.atFault}
              stagger={4}
              style={{fontFamily: 'var(--display), sans-serif', fontSize: 66, lineHeight: 1.08, color: PAPER, letterSpacing: '0.04em', maxWidth: 260}}
            />
          </div>
        </div>
      </div>

      {/* ========================= ACT 1 — BOTTOM ========================= */}
      <div style={{...BOTTOM, ...blockStyle(frame, B.finding, B.act1Out)}}>
        <Rise
          text="NOT A LEGAL FINDING"
          atFrame={B.finding + 2}
          dur={13}
          stagger={4}
          style={{fontFamily: 'var(--display), sans-serif', fontSize: 88, color: PAPER, letterSpacing: '0.015em'}}
        />
        <Rule atFrame={B.finding + 16} width={380} color={RED} />
      </div>

      {/* =========================== ACT 2 — TOP =========================== */}
      <div style={{...TOP, ...blockStyle(frame, B.brand)}}>
        <Rise
          text="AWESOME"
          atFrame={B.brand + 2}
          dur={15}
          style={{fontFamily: 'var(--display), sans-serif', fontSize: 118, lineHeight: 0.98, color: PAPER, letterSpacing: '0.01em'}}
        />
        <Rise
          text="ATTORNEYS"
          atFrame={B.brand + 8}
          dur={15}
          style={{fontFamily: 'var(--display), sans-serif', fontSize: 118, lineHeight: 0.98, color: GOLD, letterSpacing: '0.01em'}}
        />
        <Rule atFrame={B.brand + 18} width={280} />
        <Rise
          text="PHOENIX INJURY ATTORNEY"
          atFrame={B.phoenix}
          stagger={3}
          style={{fontFamily: 'var(--body), sans-serif', fontWeight: 700, fontSize: 30, letterSpacing: '0.26em', textIndent: '0.26em', color: PAPER, opacity: 0.85}}
        />
      </div>

      {/* ========================= ACT 2 — BOTTOM ========================= */}
      <div style={{...BOTTOM, ...blockStyle(frame, B.matched, B.ctaOut)}}>
        <div style={{display: 'flex', gap: 30}}>
          <Rise
            text="GET MATCHED."
            atFrame={B.matched}
            dur={13}
            style={{fontFamily: 'var(--display), sans-serif', fontSize: 72, color: PAPER}}
          />
          <Rise
            text="GET PAID."
            atFrame={B.paid}
            dur={13}
            style={{fontFamily: 'var(--display), sans-serif', fontSize: 72, color: GOLD}}
          />
        </div>
      </div>

      <div style={{...BOTTOM, ...blockStyle(frame, B.url)}}>
        <Rise
          text="AwesomeAttorneys.com"
          atFrame={B.url + 2}
          dur={15}
          style={{fontFamily: 'var(--body), sans-serif', fontWeight: 800, fontSize: 66, letterSpacing: '-0.01em', color: PAPER}}
        />
        <Rule atFrame={B.url + 14} width={480} />
      </div>

      {!alpha && <FilmGrain />}
    </AbsoluteFill>
  );
};
