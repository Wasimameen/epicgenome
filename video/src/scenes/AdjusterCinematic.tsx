import React from 'react';
import {AbsoluteFill, Audio, Easing, interpolate, random, staticFile, useCurrentFrame} from 'remotion';
import {useTransparent} from '../alpha';

/**
 * "Adjuster" — sticker-graphic cut. 60fps, 14.1s.
 *
 * Visual system: no naked type. Every message lives inside a designed element —
 * a pill badge, a glass stat card, an angled tag, a stamp badge, CTA buttons,
 * a URL bar — so the frame reads as art-directed graphics, not captions.
 *
 * Motion system: every element enters through a cinematic defocus — blur 14->0
 * with a soft rise and a settle from 104% scale, ~26 frames (0.43s) — and exits
 * back into blur, faster (16 frames). Ambient sparks, particles and rings
 * drift continuously on slow sine eases. Nothing moves linearly, nothing snaps.
 *
 * Layout contract: the centre (28%-70% vertically) stays EMPTY for b-roll.
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
  kicker: at(0.28),
  kickerOut: at(3.2),
  card: at(1.34),
  opening: at(3.4),
  strike: at(4.78),
  stamp: at(4.88),
  act1Out: at(6.2),
  brand: at(6.5),
  phoenix: at(8.66),
  matched: at(10.3),
  paid: at(11.16),
  ctaOut: at(12.0),
  url: at(12.24),
};

const PAPER = '#f5f2ea';
const GOLD = '#e3b34c';
const GOLD_DIM = 'rgba(227,179,76,0.55)';
const RED = '#e5484d';
const INK = '#0b0b0d';
const GLASS = 'rgba(16,16,20,0.6)';

const OUT = Easing.bezier(0.16, 1, 0.3, 1);
const IN = Easing.bezier(0.55, 0, 0.9, 0.2);

const ease = (frame: number, from: number, dur: number, a: number, b: number, curve = OUT) =>
  interpolate(frame, [from, from + dur], [a, b], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: curve,
  });

/* --------------------------------------------------------------- stickers */

/**
 * The one motion wrapper every sticker uses: cinematic blur in, blur out.
 * Enter: defocus resolves over ~0.43s with a soft rise and a settle from 104%.
 * Exit: back into the blur, faster.
 */
const Sticker: React.FC<{
  inAt: number;
  outAt?: number;
  dur?: number;
  children: React.ReactNode;
}> = ({inAt, outAt, dur = 26, children}) => {
  const frame = useCurrentFrame();
  if (frame < inAt) return null;

  const enter = ease(frame, inAt, dur, 0, 1);
  const exit = outAt !== undefined ? ease(frame, outAt, 16, 0, 1, IN) : 0;
  if (exit >= 1) return null;

  const blur = (1 - enter) * 14 + exit * 14;

  return (
    <div
      style={{
        opacity: enter * (1 - exit),
        transform: `translateY(${(1 - enter) * 34 - exit * 30}px) scale(${1.04 - enter * 0.04 + exit * 0.03})`,
        filter: blur > 0.3 ? `blur(${blur}px)` : undefined,
      }}
    >
      {children}
    </div>
  );
};

/** Rounded pill badge with a breathing dot — the kicker treatment. */
const Pill: React.FC<{text: string; color?: string}> = ({text, color = GOLD}) => {
  const frame = useCurrentFrame();
  const pulse = 0.7 + Math.sin(frame * 0.06) * 0.3;
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '16px 34px',
        borderRadius: 999,
        border: `2px solid ${color}66`,
        background: GLASS,
        boxShadow: '0 12px 40px rgba(0,0,0,0.45)',
      }}
    >
      <div style={{width: 10, height: 10, borderRadius: '50%', background: color, opacity: pulse, boxShadow: `0 0 12px ${color}`}} />
      <span
        style={{
          fontFamily: 'var(--body), sans-serif',
          fontWeight: 700,
          fontSize: 30,
          letterSpacing: '0.24em',
          textIndent: '0.05em',
          color: PAPER,
          whiteSpace: 'nowrap',
        }}
      >
        {text}
      </span>
    </div>
  );
};

/** Glass stat card holding the 40% claim. */
const StatCard: React.FC<{struck: number; dimmed: number}> = ({struck, dimmed}) => (
  <div
    style={{
      position: 'relative',
      display: 'flex',
      alignItems: 'center',
      gap: 30,
      padding: '26px 52px',
      borderRadius: 28,
      background: GLASS,
      border: '1px solid rgba(245,242,234,0.14)',
      borderTop: `3px solid ${GOLD}`,
      boxShadow: '0 18px 60px rgba(0,0,0,0.5)',
    }}
  >
    <span
      style={{
        fontFamily: 'var(--display), sans-serif',
        fontSize: 170,
        lineHeight: 0.94,
        color: PAPER,
        letterSpacing: '-0.01em',
        opacity: dimmed,
      }}
    >
      40%
    </span>
    <span
      style={{
        fontFamily: 'var(--display), sans-serif',
        fontSize: 54,
        lineHeight: 1.1,
        color: GOLD,
        letterSpacing: '0.05em',
        maxWidth: 200,
        opacity: dimmed,
      }}
    >
      AT FAULT
    </span>
    {/* red strike drawn across the card on "not a legal finding" */}
    <div
      style={{
        position: 'absolute',
        left: '4%',
        top: '52%',
        width: `${struck * 92}%`,
        height: 9,
        transform: 'rotate(-6deg)',
        background: RED,
        borderRadius: 5,
        boxShadow: `0 0 22px ${RED}88`,
        opacity: struck > 0 ? 1 : 0,
      }}
    />
  </div>
);

/** Angled label tag with a notch — paperwork energy, professionally drawn. */
const Tag: React.FC<{text: string}> = ({text}) => (
  <div style={{display: 'flex', alignItems: 'center', transform: 'rotate(-2deg)'}}>
    <div
      style={{
        width: 0,
        height: 0,
        borderTop: '17px solid transparent',
        borderBottom: '17px solid transparent',
        borderRight: `16px solid ${GOLD}`,
      }}
    />
    <div
      style={{
        padding: '12px 28px 12px 20px',
        background: GOLD,
        color: INK,
        fontFamily: 'var(--body), sans-serif',
        fontWeight: 800,
        fontSize: 27,
        letterSpacing: '0.16em',
        borderRadius: '0 10px 10px 0',
        boxShadow: '0 10px 34px rgba(0,0,0,0.4)',
        whiteSpace: 'nowrap',
      }}
    >
      {text}
    </div>
  </div>
);

/** Stamp badge — official, slightly rotated, red. */
const Stamp: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const breathe = 1 + Math.sin(frame * 0.03) * 0.006;
  return (
    <div
      style={{
        transform: `rotate(-3deg) scale(${breathe})`,
        padding: '20px 44px',
        border: `5px solid ${RED}`,
        borderRadius: 16,
        background: 'rgba(229,72,77,0.08)',
        boxShadow: `0 0 44px ${RED}33, inset 0 0 30px ${RED}14`,
      }}
    >
      <span
        style={{
          fontFamily: 'var(--display), sans-serif',
          fontSize: 72,
          color: RED,
          letterSpacing: '0.03em',
          whiteSpace: 'nowrap',
        }}
      >
        {text}
      </span>
    </div>
  );
};

/** Filled CTA button sticker with arrow. */
const Button: React.FC<{text: string; filled?: boolean}> = ({text, filled}) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: 18,
      padding: '20px 40px',
      borderRadius: 18,
      background: filled ? GOLD : GLASS,
      border: filled ? 'none' : `2px solid ${GOLD}88`,
      boxShadow: filled ? `0 14px 44px ${GOLD}44` : '0 12px 40px rgba(0,0,0,0.45)',
    }}
  >
    <span
      style={{
        fontFamily: 'var(--display), sans-serif',
        fontSize: 54,
        color: filled ? INK : PAPER,
        letterSpacing: '0.02em',
        whiteSpace: 'nowrap',
      }}
    >
      {text}
    </span>
    <svg width="34" height="34" viewBox="0 0 34 34">
      <path
        d="M6 17 h20 M18 8 l9 9 -9 9"
        stroke={filled ? INK : GOLD}
        strokeWidth="3.5"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  </div>
);

/** URL bar sticker. */
const UrlBar: React.FC = () => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: 20,
      padding: '22px 46px',
      borderRadius: 999,
      background: GLASS,
      border: '1.5px solid rgba(245,242,234,0.16)',
      boxShadow: '0 18px 60px rgba(0,0,0,0.5)',
    }}
  >
    <svg width="34" height="34" viewBox="0 0 34 34">
      <circle cx="17" cy="17" r="13" fill="none" stroke={GOLD} strokeWidth="2.5" />
      <ellipse cx="17" cy="17" rx="6" ry="13" fill="none" stroke={GOLD} strokeWidth="2" />
      <path d="M4.5 17 h25" stroke={GOLD} strokeWidth="2" />
    </svg>
    <span
      style={{
        fontFamily: 'var(--body), sans-serif',
        fontWeight: 800,
        fontSize: 56,
        letterSpacing: '-0.01em',
        color: PAPER,
        whiteSpace: 'nowrap',
      }}
    >
      Awesome<span style={{color: GOLD}}>Attorneys</span>.com
    </span>
  </div>
);

/** Four-point spark mark — decorative sticker, breathing. */
const Spark: React.FC<{x: number; y: number; size: number; phase: number}> = ({x, y, size, phase}) => {
  const frame = useCurrentFrame();
  const breathe = 0.8 + Math.sin(frame * 0.025 + phase) * 0.2;
  const spin = Math.sin(frame * 0.006 + phase) * 10;
  return (
    <div
      style={{
        position: 'absolute',
        left: `${x}%`,
        top: `${y}%`,
        transform: `translate(-50%,-50%) rotate(${spin}deg) scale(${breathe})`,
        opacity: 0.6,
        pointerEvents: 'none',
      }}
    >
      <svg width={size} height={size} viewBox="0 0 40 40">
        <path
          d="M20 2 C21.5 12 24 15.5 34 17 L38 20 L34 23 C24 24.5 21.5 28 20 38 L20 38 C18.5 28 16 24.5 6 23 L2 20 L6 17 C16 15.5 18.5 12 20 2 Z"
          fill={GOLD}
        />
      </svg>
    </div>
  );
};

/* ------------------------------------------------------- ambient graphics */

const Particles: React.FC = () => {
  const frame = useCurrentFrame();
  const dots = React.useMemo(
    () =>
      new Array(26).fill(0).map((_, i) => {
        const topBand = random(`pb-${i}`) > 0.5;
        return {
          x: random(`px-${i}`) * 100,
          y: topBand ? random(`py-${i}`) * 24 + 1 : 72 + random(`py-${i}`) * 25,
          r: 2 + random(`pr-${i}`) * 4,
          rise: 0.007 + random(`ps-${i}`) * 0.011,
          sway: 1 + random(`pw-${i}`) * 2,
          phase: random(`pp-${i}`) * 6.28,
          band: topBand ? [1, 25] : [72, 97],
          o: 0.18 + random(`po-${i}`) * 0.4,
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
              opacity: d.o * (0.55 + Math.sin(frame * 0.02 + d.phase) * 0.45),
              filter: d.r > 4 ? 'blur(1.5px)' : undefined,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

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
        <circle cx={r} cy={r} r={r - 2} fill="none" stroke={GOLD_DIM} strokeWidth="1.4" strokeDasharray={dash} />
      </svg>
    </div>
  );
  return (
    <>
      {ring(92, 6, 100, 0.05, 0.5)}
      {ring(92, 6, 70, -0.08, 0.35, '4 8')}
      {ring(7, 95, 120, -0.045, 0.45)}
      {ring(7, 95, 84, 0.07, 0.3, '2 10')}
    </>
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
  gap: 20,
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
  gap: 20,
};

export const AdjusterCinematic: React.FC<{withAudio?: boolean}> = ({withAudio = true}) => {
  const alpha = useTransparent();
  const frame = useCurrentFrame();

  const struck = ease(frame, B.strike, 10, 0, 1);
  const dimmed = ease(frame, B.strike, 14, 1, 0.4);

  return (
    <AbsoluteFill style={{backgroundColor: alpha ? 'transparent' : INK}}>
      {withAudio ? <Audio src={staticFile('audio/vo-adjuster.mp3')} /> : null}
      {!alpha && <Ground />}

      <Particles />
      <Rings />
      <Spark x={13} y={8} size={34} phase={0} />
      <Spark x={86} y={22} size={26} phase={2} />
      <Spark x={90} y={78} size={30} phase={4} />

      {/* =========================== ACT 1 — TOP =========================== */}
      <div style={TOP}>
        <div style={{position: 'relative', height: 70, display: 'flex', justifyContent: 'center', alignItems: 'center'}}>
          <div style={{position: 'absolute'}}>
            <Sticker inAt={B.kicker} outAt={B.kickerOut}>
              <Pill text="THE ADJUSTER SAYS" />
            </Sticker>
          </div>
          <div style={{position: 'absolute'}}>
            <Sticker inAt={B.opening} outAt={B.act1Out}>
              <Tag text="THAT'S THEIR OPENING POSITION" />
            </Sticker>
          </div>
        </div>
        <Sticker inAt={B.card} outAt={B.act1Out} dur={30}>
          <StatCard struck={struck} dimmed={dimmed} />
        </Sticker>
      </div>

      {/* ========================= ACT 1 — BOTTOM ========================= */}
      <div style={BOTTOM}>
        <Sticker inAt={B.stamp} outAt={B.act1Out} dur={22}>
          <Stamp text="NOT A LEGAL FINDING" />
        </Sticker>
      </div>

      {/* =========================== ACT 2 — TOP =========================== */}
      <div style={{...TOP, gap: 16}}>
        <Sticker inAt={B.brand} dur={30}>
          <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6}}>
            <span style={{fontFamily: 'var(--display), sans-serif', fontSize: 120, lineHeight: 0.98, color: PAPER, letterSpacing: '0.01em'}}>
              AWESOME
            </span>
            <span style={{fontFamily: 'var(--display), sans-serif', fontSize: 120, lineHeight: 0.98, color: GOLD, letterSpacing: '0.01em'}}>
              ATTORNEYS
            </span>
          </div>
        </Sticker>
        <Sticker inAt={B.phoenix} dur={24}>
          <Pill text="PHOENIX INJURY ATTORNEY" />
        </Sticker>
      </div>

      {/* ========================= ACT 2 — BOTTOM ========================= */}
      <div style={BOTTOM}>
        <div style={{position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <div style={{position: 'absolute', display: 'flex', gap: 26}}>
            <Sticker inAt={B.matched} outAt={B.ctaOut} dur={24}>
              <Button text="GET MATCHED" filled />
            </Sticker>
            <Sticker inAt={B.paid} outAt={B.ctaOut} dur={24}>
              <Button text="GET PAID" />
            </Sticker>
          </div>
          <div style={{position: 'absolute'}}>
            <Sticker inAt={B.url} dur={28}>
              <UrlBar />
            </Sticker>
          </div>
        </div>
      </div>

      {!alpha && <FilmGrain />}
    </AbsoluteFill>
  );
};
