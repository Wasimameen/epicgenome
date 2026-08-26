import React from 'react';
import {AbsoluteFill, Audio, Easing, interpolate, random, staticFile, useCurrentFrame} from 'remotion';
import {useTransparent} from '../alpha';

/**
 * "Adjuster" — minimal cinematic cut. 60fps, 14.1s.
 *
 * Direction: minimalistic, no containers. Every message is clean type carrying
 * a two-part shadow (per the alpha-overlays skill's legibility rule) so it
 * stays readable over any footage without a single box. The only drawn marks
 * are hairline rules, one red strike, and a sparse particle field.
 *
 * Motion: every element enters through a cinematic defocus — blur 12->0, rise
 * 30px, settle from 103% — and exits back into blur at ~75% of the entrance
 * duration (slow in, quicker out reads as intentional). Ambient particles
 * drift on slow sines. Nothing linear, nothing snapping.
 *
 * Layout per the skill's 9:16 safe zones: graphics keep clear of the top 11%
 * and bottom 21% where platform UI sits, and the centre (30%-66%) stays empty
 * for b-roll.
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
  claim: at(1.34),
  opening: at(3.4),
  strike: at(4.78),
  finding: at(4.88),
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
const RED = '#e5484d';
const INK = '#0b0b0d';

/** Two-part shadow: reads over bright and dark footage alike. */
const LEGIBLE = '0 2px 24px rgba(0,0,0,0.55), 0 0 2px rgba(0,0,0,0.4)';

const OUT = Easing.bezier(0.16, 1, 0.3, 1);
const IN = Easing.bezier(0.7, 0, 0.84, 0);

const ease = (frame: number, from: number, dur: number, a: number, b: number, curve = OUT) =>
  interpolate(frame, [from, from + dur], [a, b], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: curve,
  });

/** Cinematic defocus wrapper: blur in, blur out, compound transform. */
const Blur: React.FC<{
  inAt: number;
  outAt?: number;
  dur?: number;
  children: React.ReactNode;
}> = ({inAt, outAt, dur = 26, children}) => {
  const frame = useCurrentFrame();
  if (frame < inAt) return null;

  const enter = ease(frame, inAt, dur, 0, 1);
  const exit = outAt !== undefined ? ease(frame, outAt, Math.round(dur * 0.75), 0, 1, IN) : 0;
  if (exit >= 1) return null;

  const blur = (1 - enter) * 12 + exit * 12;
  return (
    <div
      style={{
        opacity: enter * (1 - exit),
        transform: `translateY(${(1 - enter) * 30 - exit * 26}px) scale(${1.03 - enter * 0.03 + exit * 0.02})`,
        filter: blur > 0.3 ? `blur(${blur}px)` : undefined,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 18,
      }}
    >
      {children}
    </div>
  );
};

/** Hairline rule sweeping to width. */
const Rule: React.FC<{atFrame: number; width: number; color?: string}> = ({atFrame, width, color = GOLD}) => {
  const frame = useCurrentFrame();
  if (frame < atFrame) return null;
  return (
    <div
      style={{
        width: ease(frame, atFrame, 20, 0, width),
        height: 2,
        background: color,
        boxShadow: '0 1px 8px rgba(0,0,0,0.5)',
      }}
    />
  );
};

/** Sparse ambient particles — the only decoration. */
const Particles: React.FC = () => {
  const frame = useCurrentFrame();
  const dots = React.useMemo(
    () =>
      new Array(14).fill(0).map((_, i) => {
        const topBand = random(`pb-${i}`) > 0.5;
        return {
          x: random(`px-${i}`) * 100,
          y: topBand ? 11 + random(`py-${i}`) * 18 : 66 + random(`py-${i}`) * 13,
          band: topBand ? [11, 29] : [66, 79],
          r: 2 + random(`pr-${i}`) * 3,
          rise: 0.006 + random(`ps-${i}`) * 0.008,
          sway: 0.8 + random(`pw-${i}`) * 1.6,
          phase: random(`pp-${i}`) * 6.28,
          o: 0.12 + random(`po-${i}`) * 0.28,
        };
      }),
    [],
  );
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {dots.map((d, i) => {
        const span = d.band[1] - d.band[0];
        const y = d.band[0] + ((((d.y - d.band[0] - frame * d.rise) % span) + span) % span);
        const x = d.x + Math.sin(frame * 0.005 + d.phase) * d.sway;
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
              opacity: d.o * (0.5 + Math.sin(frame * 0.018 + d.phase) * 0.5),
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

const Ground: React.FC = () => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(ellipse 120% 70% at 50% 40%, #16161a 0%, ${INK} 68%, #070708 100%)`,
    }}
  />
);

/* ------------------------------------------------------------------ scene */

// Safe zones per the alpha-overlays skill: clear of top 11% and bottom 21%.
const TOP: React.CSSProperties = {
  position: 'absolute',
  left: 0,
  right: 0,
  top: '11%',
  height: '19%',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
};

const BOTTOM: React.CSSProperties = {
  position: 'absolute',
  left: 0,
  right: 0,
  top: '66%',
  height: '13%',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
};

const kickerType: React.CSSProperties = {
  fontFamily: 'var(--body), sans-serif',
  fontWeight: 700,
  fontSize: 32,
  letterSpacing: '0.3em',
  textIndent: '0.3em',
  color: GOLD,
  textShadow: LEGIBLE,
  whiteSpace: 'nowrap',
};

export const AdjusterCinematic: React.FC<{withAudio?: boolean}> = ({withAudio = true}) => {
  const alpha = useTransparent();
  const frame = useCurrentFrame();

  const struck = ease(frame, B.strike, 10, 0, 1);
  const dimmed = ease(frame, B.strike, 14, 1, 0.45);

  return (
    <AbsoluteFill style={{backgroundColor: alpha ? 'transparent' : INK}}>
      {withAudio ? <Audio src={staticFile('audio/vo-adjuster.mp3')} /> : null}
      {!alpha && <Ground />}
      <Particles />

      {/* =========================== ACT 1 — TOP =========================== */}
      <div style={TOP}>
        <div style={{position: 'relative', height: 52, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14}}>
          <div style={{position: 'absolute'}}>
            <Blur inAt={B.kicker} outAt={B.kickerOut}>
              <span style={kickerType}>THE ADJUSTER SAYS</span>
            </Blur>
          </div>
          <div style={{position: 'absolute'}}>
            <Blur inAt={B.opening} outAt={B.act1Out}>
              <span style={kickerType}>THEIR OPENING POSITION</span>
            </Blur>
          </div>
        </div>

        <Blur inAt={B.claim} outAt={B.act1Out} dur={30}>
          <div style={{position: 'relative', display: 'flex', alignItems: 'baseline', gap: 26, opacity: dimmed}}>
            <span
              style={{
                fontFamily: 'var(--display), sans-serif',
                fontSize: 190,
                lineHeight: 0.94,
                color: PAPER,
                letterSpacing: '-0.01em',
                textShadow: LEGIBLE,
              }}
            >
              40%
            </span>
            <span
              style={{
                fontFamily: 'var(--display), sans-serif',
                fontSize: 74,
                color: GOLD,
                letterSpacing: '0.04em',
                textShadow: LEGIBLE,
              }}
            >
              AT FAULT
            </span>
            <div
              style={{
                position: 'absolute',
                left: '-3%',
                top: '54%',
                width: `${struck * 106}%`,
                height: 8,
                transform: 'rotate(-6deg)',
                background: RED,
                borderRadius: 4,
                boxShadow: `0 0 18px ${RED}77`,
                opacity: struck > 0 ? 1 : 0,
              }}
            />
          </div>
        </Blur>
      </div>

      {/* ========================= ACT 1 — BOTTOM ========================= */}
      <div style={BOTTOM}>
        <Blur inAt={B.finding} outAt={B.act1Out} dur={24}>
          <span
            style={{
              fontFamily: 'var(--display), sans-serif',
              fontSize: 82,
              color: PAPER,
              letterSpacing: '0.02em',
              textShadow: LEGIBLE,
              whiteSpace: 'nowrap',
            }}
          >
            NOT A LEGAL FINDING
          </span>
          <Rule atFrame={B.finding + 16} width={340} color={RED} />
        </Blur>
      </div>

      {/* =========================== ACT 2 — TOP =========================== */}
      <div style={TOP}>
        <Blur inAt={B.brand} dur={30}>
          <div style={{display: 'flex', alignItems: 'baseline', gap: 30}}>
            <span style={{fontFamily: 'var(--display), sans-serif', fontSize: 104, lineHeight: 1, color: PAPER, textShadow: LEGIBLE}}>
              AWESOME
            </span>
            <span style={{fontFamily: 'var(--display), sans-serif', fontSize: 104, lineHeight: 1, color: GOLD, textShadow: LEGIBLE}}>
              ATTORNEYS
            </span>
          </div>
          <Rule atFrame={B.brand + 18} width={260} />
        </Blur>
        <div style={{height: 16}} />
        <Blur inAt={B.phoenix} dur={24}>
          <span style={kickerType}>PHOENIX INJURY ATTORNEY</span>
        </Blur>
      </div>

      {/* ========================= ACT 2 — BOTTOM ========================= */}
      <div style={BOTTOM}>
        <div style={{position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <div style={{position: 'absolute', display: 'flex', alignItems: 'center', gap: 28}}>
            <Blur inAt={B.matched} outAt={B.ctaOut} dur={24}>
              <span style={{fontFamily: 'var(--display), sans-serif', fontSize: 72, color: PAPER, textShadow: LEGIBLE, whiteSpace: 'nowrap'}}>
                GET MATCHED
              </span>
            </Blur>
            <Blur inAt={B.paid} outAt={B.ctaOut} dur={24}>
              <div style={{display: 'flex', alignItems: 'center', gap: 28}}>
                <div style={{width: 9, height: 9, borderRadius: '50%', background: GOLD}} />
                <span style={{fontFamily: 'var(--display), sans-serif', fontSize: 72, color: GOLD, textShadow: LEGIBLE, whiteSpace: 'nowrap'}}>
                  GET PAID
                </span>
              </div>
            </Blur>
          </div>
          <div style={{position: 'absolute'}}>
            <Blur inAt={B.url} dur={28}>
              <span
                style={{
                  fontFamily: 'var(--body), sans-serif',
                  fontWeight: 800,
                  fontSize: 62,
                  letterSpacing: '-0.01em',
                  color: PAPER,
                  textShadow: LEGIBLE,
                  whiteSpace: 'nowrap',
                }}
              >
                Awesome<span style={{color: GOLD}}>Attorneys</span>.com
              </span>
              <Rule atFrame={B.url + 14} width={420} />
            </Blur>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
