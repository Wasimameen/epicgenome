import React from 'react';
import {AbsoluteFill, Audio, Easing, interpolate, random, staticFile, useCurrentFrame} from 'remotion';
import {useTransparent} from '../alpha';
import {THEME} from '../theme';

/**
 * "Adjuster" — kinetic typography rebuild. 60fps, 14.1s.
 *
 * Built to the professional kinetic-type standard, not the slow-cinematic one:
 *  - entries are FAST (12-16 frames ≈ 0.2-0.27s) on a strong ease-out curve
 *    (0.16, 1, 0.3, 1), then the type holds DEAD STILL — the research rule is
 *    readable-and-static within half a second of landing;
 *  - every reveal is a masked baseline rise and every exit is a push up:
 *    one motion axis, one motion language, no blur-fades;
 *  - palette is two colors on near-black — off-white type, one gold accent —
 *    with red reserved for the single strike moment;
 *  - no camera drift, no shake: a locked-off frame with one barely
 *    perceptible push across the whole piece.
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
  forty: at(1.42),
  atFault: at(2.08),
  opening: at(3.38),
  strike: at(4.78),
  finding: at(4.9),
  act1Out: at(6.28),
  brand: at(6.56),
  phoenix: at(8.68),
  matched: at(10.32),
  paid: at(11.18),
  ctaOut: at(12.1),
  url: at(12.3),
};

const INK = '#0b0b0d';
const PAPER = '#f5f2ea';
const GOLD = '#e3b34c';
const RED = '#e5484d';

/** The professional entry curve — fast start, long soft settle, no bounce. */
const OUT = Easing.bezier(0.16, 1, 0.3, 1);
/** Exit curve — accelerates away. */
const IN = Easing.bezier(0.55, 0, 0.9, 0.2);

const ease = (frame: number, from: number, dur: number, a: number, b: number, curve = OUT) =>
  interpolate(frame, [from, from + dur], [a, b], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: curve,
  });

/* ---------------------------------------------------------------- reveals */

/**
 * Masked baseline rise, per word. Each word lives in an overflow-hidden box
 * and rises from below its own baseline — the signature kinetic-type reveal.
 */
const Rise: React.FC<{
  text: string;
  atFrame: number;
  /** Frames each word takes to land. */
  dur?: number;
  stagger?: number;
  exitAt?: number;
  style: React.CSSProperties;
}> = ({text, atFrame, dur = 14, stagger = 4, exitAt, style}) => {
  const frame = useCurrentFrame();
  if (frame < atFrame) return null;

  const gone =
    exitAt !== undefined ? ease(frame, exitAt, 10, 0, 1, IN) : 0;
  if (gone >= 1) return null;

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        columnGap: '0.28em',
        ...style,
      }}
    >
      {text.split(' ').map((word, i) => {
        const y = ease(frame, atFrame + i * stagger, dur, 108, 0);
        return (
          <span key={i} style={{display: 'inline-block', overflow: 'hidden', verticalAlign: 'top'}}>
            <span
              style={{
                display: 'inline-block',
                transform: `translateY(${y - gone * -0 + gone * -112}%)`,
              }}
            >
              {word}
            </span>
          </span>
        );
      })}
    </div>
  );
};

/** A thin gold rule that sweeps to full width on its cue. */
const Rule: React.FC<{atFrame: number; width: number; exitAt?: number; color?: string}> = ({
  atFrame,
  width,
  exitAt,
  color = GOLD,
}) => {
  const frame = useCurrentFrame();
  const w = ease(frame, atFrame, 16, 0, width);
  const gone = exitAt !== undefined ? ease(frame, exitAt, 10, 1, 0, IN) : 1;
  if (frame < atFrame || gone <= 0) return null;
  return (
    <div
      style={{
        width: w,
        height: 3,
        background: color,
        opacity: gone,
        borderRadius: 2,
      }}
    />
  );
};

/* ------------------------------------------------------------- background */

/** Minimal premium ground: dark radial, a whisper of warm bokeh, grain. */
const Ground: React.FC = () => {
  const frame = useCurrentFrame();
  const discs = React.useMemo(
    () =>
      new Array(9).fill(0).map((_, i) => ({
        x: random(`gx-${i}`) * 100,
        y: random(`gy-${i}`) * 100,
        r: 90 + random(`gr-${i}`) * 200,
        rate: 0.004 + random(`gs-${i}`) * 0.006,
        phase: random(`gp-${i}`) * 6.28,
      })),
    [],
  );

  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 120% 70% at 50% 38%, #16161a 0%, ${INK} 68%, #070708 100%)`,
        }}
      />
      {discs.map((d, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${d.x + Math.sin(frame * d.rate + d.phase) * 3}%`,
            top: `${d.y + Math.cos(frame * d.rate * 0.7 + d.phase) * 2.5}%`,
            width: d.r,
            height: d.r,
            transform: 'translate(-50%,-50%)',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(227,179,76,0.05) 0%, transparent 70%)',
            filter: 'blur(30px)',
          }}
        />
      ))}
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(ellipse 90% 62% at 50% 46%, transparent 55%, rgba(0,0,0,0.55) 100%)',
        }}
      />
    </AbsoluteFill>
  );
};

/** Fine, fast-cycling monochrome grain — texture, not noise. */
const FilmGrain: React.FC = () => {
  const frame = useCurrentFrame();
  const seed = Math.floor(frame / 2);
  const specks = React.useMemo(
    () =>
      new Array(240).fill(0).map((_, i) => ({
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

export const AdjusterCinematic: React.FC<{withAudio?: boolean}> = ({withAudio = true}) => {
  const alpha = useTransparent();
  const frame = useCurrentFrame();

  // Locked-off with one imperceptible push — premium stillness.
  const push = ease(frame, 0, ADJUSTER_CINE_FRAMES, 1.0, 1.028, Easing.inOut(Easing.quad));

  // Act 1 exits as a block: a fast push up, gone in a quarter second.
  const act1Y = ease(frame, B.act1Out, 16, 0, -110, IN);
  const act1O = ease(frame, B.act1Out + 4, 12, 1, 0, IN);

  // CTA lines clear before the URL takes the frame.
  const strike = ease(frame, B.strike, 9, 0, 1);
  const dimmed = ease(frame, B.strike, 12, 1, 0.3);

  return (
    <AbsoluteFill style={{backgroundColor: alpha ? 'transparent' : INK}}>
      {withAudio ? <Audio src={staticFile('audio/vo-adjuster.mp3')} /> : null}
      {!alpha && <Ground />}

      <AbsoluteFill style={{transform: `scale(${push})`}}>
        {/* ============================ ACT 1 ============================ */}
        <AbsoluteFill
          style={{
            alignItems: 'center',
            justifyContent: 'center',
            transform: `translateY(${act1Y}%)`,
            opacity: act1O,
          }}
        >
          <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 30}}>
            <Rule atFrame={B.kicker} width={64} />
            <Rise
              text="THE ADJUSTER SAYS"
              atFrame={B.kicker + 3}
              stagger={3}
              style={{
                fontFamily: 'var(--body), sans-serif',
                fontWeight: 700,
                fontSize: 38,
                letterSpacing: '0.34em',
                textIndent: '0.34em',
                color: GOLD,
              }}
            />

            {/* the claim */}
            <div style={{position: 'relative', marginTop: 8}}>
              <div style={{opacity: dimmed}}>
                <Rise
                  text="40%"
                  atFrame={B.forty}
                  dur={16}
                  style={{
                    fontFamily: 'var(--display), sans-serif',
                    fontSize: 360,
                    lineHeight: 0.96,
                    color: PAPER,
                    letterSpacing: '-0.01em',
                  }}
                />
              </div>
              {/* the strike — one clean red line, drawn in 0.15s */}
              <div
                style={{
                  position: 'absolute',
                  left: '50%',
                  top: '50%',
                  width: strike * 620,
                  height: 14,
                  transform: 'translate(-50%,-50%) rotate(-8deg)',
                  background: RED,
                  borderRadius: 7,
                  opacity: strike > 0 ? 1 : 0,
                }}
              />
            </div>
            <div style={{opacity: dimmed, marginTop: -14}}>
              <Rise
                text="AT FAULT"
                atFrame={B.atFault}
                stagger={4}
                style={{
                  fontFamily: 'var(--display), sans-serif',
                  fontSize: 96,
                  color: PAPER,
                  letterSpacing: '0.04em',
                }}
              />
            </div>

            <div style={{marginTop: 14}}>
              <Rise
                text="THAT'S THEIR OPENING POSITION"
                atFrame={B.opening}
                stagger={3}
                exitAt={B.strike - 2}
                style={{
                  fontFamily: 'var(--body), sans-serif',
                  fontWeight: 700,
                  fontSize: 36,
                  letterSpacing: '0.22em',
                  textIndent: '0.22em',
                  color: GOLD,
                }}
              />
            </div>

            {/* the truth */}
            <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 22, marginTop: 4}}>
              <Rise
                text="NOT A LEGAL FINDING"
                atFrame={B.finding}
                dur={13}
                stagger={4}
                style={{
                  fontFamily: 'var(--display), sans-serif',
                  fontSize: 104,
                  color: PAPER,
                  letterSpacing: '0.015em',
                }}
              />
              <Rule atFrame={B.finding + 14} width={420} color={RED} />
            </div>
          </div>
        </AbsoluteFill>

        {/* ============================ ACT 2 ============================ */}
        {frame >= B.act1Out + 10 ? (
          <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
            <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 30}}>
              <Rise
                text="AWESOME"
                atFrame={B.brand}
                dur={15}
                exitAt={B.ctaOut}
                style={{
                  fontFamily: 'var(--display), sans-serif',
                  fontSize: 176,
                  lineHeight: 0.98,
                  color: PAPER,
                  letterSpacing: '0.01em',
                }}
              />
              <Rise
                text="ATTORNEYS"
                atFrame={B.brand + 6}
                dur={15}
                exitAt={B.ctaOut}
                style={{
                  fontFamily: 'var(--display), sans-serif',
                  fontSize: 176,
                  lineHeight: 0.98,
                  color: GOLD,
                  letterSpacing: '0.01em',
                }}
              />
              <Rule atFrame={B.brand + 16} width={340} exitAt={B.ctaOut} />
              <Rise
                text="PHOENIX INJURY ATTORNEY"
                atFrame={B.phoenix}
                stagger={3}
                exitAt={B.ctaOut}
                style={{
                  fontFamily: 'var(--body), sans-serif',
                  fontWeight: 700,
                  fontSize: 36,
                  letterSpacing: '0.28em',
                  textIndent: '0.28em',
                  color: PAPER,
                  opacity: 0.85,
                }}
              />

              <div style={{display: 'flex', gap: 34, marginTop: 16}}>
                <Rise
                  text="GET MATCHED."
                  atFrame={B.matched}
                  dur={13}
                  exitAt={B.ctaOut}
                  style={{
                    fontFamily: 'var(--display), sans-serif',
                    fontSize: 76,
                    color: PAPER,
                  }}
                />
                <Rise
                  text="GET PAID."
                  atFrame={B.paid}
                  dur={13}
                  exitAt={B.ctaOut}
                  style={{
                    fontFamily: 'var(--display), sans-serif',
                    fontSize: 76,
                    color: GOLD,
                  }}
                />
              </div>
            </div>
          </AbsoluteFill>
        ) : null}

        {/* ============================ URL CARD ============================ */}
        {frame >= B.url ? (
          <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
            <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 26}}>
              <Rise
                text="AwesomeAttorneys.com"
                atFrame={B.url}
                dur={15}
                style={{
                  fontFamily: 'var(--body), sans-serif',
                  fontWeight: 800,
                  fontSize: 76,
                  letterSpacing: '-0.01em',
                  color: PAPER,
                }}
              />
              <Rule atFrame={B.url + 12} width={560} />
              <Rise
                text="GET MATCHED · GET PAID"
                atFrame={B.url + 18}
                stagger={2}
                style={{
                  fontFamily: 'var(--body), sans-serif',
                  fontWeight: 700,
                  fontSize: 33,
                  letterSpacing: '0.3em',
                  textIndent: '0.3em',
                  color: GOLD,
                }}
              />
            </div>
          </AbsoluteFill>
        ) : null}
      </AbsoluteFill>

      {!alpha && <FilmGrain />}
    </AbsoluteFill>
  );
};
