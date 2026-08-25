import React, {useMemo} from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  interpolate,
  random,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import {useTransparent} from '../alpha';
import {Grain} from '../components/Grain';
import {Vignette} from '../components/Vignette';
import {THEME} from '../theme';

/**
 * "Adjuster" — cinematic rebuild. 60fps, 14.1s.
 *
 * Motion language: one continuous floating camera (slow push-in plus a gentle
 * two-frequency drift), three parallax planes, rack-focus handoffs between the
 * two acts, and ease-in-out curves everywhere. No springs, no shake, no hard
 * cuts — nothing in this file moves linearly and nothing snaps.
 *
 * Element inventory: gradient-mesh background, god rays, three-depth bokeh
 * field, fine dust, two flowing silk ribbons, slow-rotating geometric rings,
 * drifting light streaks, anamorphic flares on title landings, film grain,
 * vignette. Background-only layers (mesh, rays, bokeh, vignette, grain) drop
 * out of the alpha pass; ribbons, rings, streaks, flares and type are the
 * graphics layer and survive it. Type keeps to the upper and lower thirds so
 * the alpha version still leaves the middle clear for footage — with no
 * drawn frame marking it.
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
  kicker: at(0.25),
  forty: at(1.42),
  atFault: at(2.1),
  opening: at(3.4),
  finding: at(4.76),
  actTwo: at(6.4),
  brand: at(6.62),
  phoenix: at(8.72),
  matched: at(10.36),
  paid: at(11.22),
  url: at(12.26),
};

const io = Easing.inOut(Easing.cubic);
const out = Easing.out(Easing.cubic);

/** Eased interpolate with clamping — the only motion primitive in this scene. */
const ease = (
  frame: number,
  from: number,
  dur: number,
  a: number,
  b: number,
  curve = io,
) =>
  interpolate(frame, [from, from + dur], [a, b], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: curve,
  });

/* ------------------------------------------------------------------ camera */

const useCamera = (frame: number) => {
  // One unbroken push across the whole piece; drift is two slow sines summed
  // so it never reads as a loop.
  const push = ease(frame, 0, ADJUSTER_CINE_FRAMES, 1.02, 1.085);
  const dx = Math.sin(frame * 0.004) * 9 + Math.sin(frame * 0.0017 + 1.7) * 6;
  const dy = Math.sin(frame * 0.0031 + 0.6) * 7 + Math.sin(frame * 0.0013) * 5;
  return {push, dx, dy};
};

/** Parallax plane: depth 1 = background (moves most), 0 = screen-locked. */
const Plane: React.FC<{
  depth: number;
  cam: {push: number; dx: number; dy: number};
  children: React.ReactNode;
}> = ({depth, cam, children}) => {
  const scale = 1 + (cam.push - 1) * (0.6 + depth * 0.55);
  return (
    <AbsoluteFill
      style={{
        transform: `scale(${scale}) translate(${cam.dx * depth}px, ${cam.dy * depth}px)`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

/* -------------------------------------------------------------- background */

/** Slow-morphing gradient mesh — the dark teal/gold ground. Opaque pass only. */
const GradientMesh: React.FC = () => {
  const frame = useCurrentFrame();
  const blob = (
    x: number,
    y: number,
    r: number,
    color: string,
    rate: number,
    phase: number,
  ) => (
    <div
      style={{
        position: 'absolute',
        left: `${x + Math.sin(frame * rate + phase) * 6}%`,
        top: `${y + Math.cos(frame * rate * 0.8 + phase) * 5}%`,
        width: r,
        height: r,
        transform: 'translate(-50%, -50%)',
        borderRadius: '50%',
        background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
        filter: 'blur(70px)',
      }}
    />
  );

  return (
    <AbsoluteFill style={{backgroundColor: '#05060a', overflow: 'hidden'}}>
      {blob(30, 22, 900, 'rgba(22,88,100,0.8)', 0.0021, 0)}
      {blob(78, 64, 1100, 'rgba(150,108,40,0.6)', 0.0016, 2.1)}
      {blob(20, 84, 850, 'rgba(14,62,80,0.72)', 0.0025, 4.2)}
      {blob(64, 8, 700, 'rgba(180,128,52,0.4)', 0.0019, 1.2)}
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(4,5,9,0.6) 0%, transparent 30%, transparent 62%, rgba(4,5,9,0.75) 100%)',
        }}
      />
    </AbsoluteFill>
  );
};

/** Volumetric shafts from top-left, breathing slowly. Opaque pass only. */
const GodRays: React.FC = () => {
  const frame = useCurrentFrame();
  const breathe = 0.6 + Math.sin(frame * 0.006) * 0.25;
  return (
    <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'screen', opacity: 0.24 * breathe}}>
      <AbsoluteFill
        style={{
          transformOrigin: '18% -8%',
          transform: `rotate(${-14 + Math.sin(frame * 0.0035) * 2.2}deg)`,
          background:
            'repeating-linear-gradient(101deg, rgba(255,230,180,0.5) 0px, rgba(255,230,180,0.5) 2px, transparent 2px, transparent 70px, rgba(255,230,180,0.26) 70px, rgba(255,230,180,0.26) 82px, transparent 82px, transparent 170px)',
          filter: 'blur(14px)',
        }}
      />
    </AbsoluteFill>
  );
};

/** Out-of-focus discs on a given depth band. Opaque pass only. */
const BokehField: React.FC<{seed: string; count?: number}> = ({seed, count = 22}) => {
  const frame = useCurrentFrame();
  const discs = useMemo(
    () =>
      new Array(count).fill(0).map((_, i) => ({
        x: random(`bkx-${seed}-${i}`) * 100,
        y: random(`bky-${seed}-${i}`) * 100,
        r: 14 + random(`bkr-${seed}-${i}`) * 58,
        rise: 0.006 + random(`bks-${seed}-${i}`) * 0.012,
        sway: random(`bkw-${seed}-${i}`) * 2.4,
        phase: random(`bkp-${seed}-${i}`) * Math.PI * 2,
        warm: random(`bkc-${seed}-${i}`) > 0.45,
        o: 0.09 + random(`bko-${seed}-${i}`) * 0.16,
      })),
    [count, seed],
  );

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {discs.map((d, i) => {
        const y = (((d.y - frame * d.rise) % 112) + 112) % 112 - 6;
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
              background: d.warm ? 'rgba(235,190,120,1)' : 'rgba(130,190,205,1)',
              opacity: d.o * (0.75 + Math.sin(frame * 0.01 + d.phase) * 0.25),
              filter: `blur(${d.r * 0.35}px)`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/* -------------------------------------------------- graphics-layer elements */

/** Flowing silk ribbon — a wide bezier sheet, slowly undulating. */
const Ribbon: React.FC<{
  y: number;
  amp: number;
  rate: number;
  phase: number;
  opacity?: number;
  hue?: string;
}> = ({y, amp, rate, phase, opacity = 0.4, hue = '215,175,105'}) => {
  const frame = useCurrentFrame();
  const t = frame * rate + phase;

  const y0 = y + Math.sin(t) * amp;
  const y1 = y + Math.sin(t + 1.4) * amp * 1.35;
  const y2 = y + Math.sin(t + 2.9) * amp * 0.9;
  const y3 = y + Math.sin(t + 4.1) * amp * 1.2;
  const w = 130 + Math.sin(t * 0.7 + 1) * 45;

  const d = `M -80 ${y0} C 340 ${y1}, 700 ${y2}, 1180 ${y3}`;
  const gid = `rib-${y}-${phase}`;

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity}}>
      <svg viewBox="0 0 1080 1920" style={{width: '100%', height: '100%'}} preserveAspectRatio="xMidYMid slice">
        <defs>
          <linearGradient id={gid} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={`rgba(${hue},0)`} />
            <stop offset="30%" stopColor={`rgba(${hue},0.55)`} />
            <stop offset="55%" stopColor={`rgba(255,240,210,0.8)`} />
            <stop offset="78%" stopColor={`rgba(${hue},0.45)`} />
            <stop offset="100%" stopColor={`rgba(${hue},0)`} />
          </linearGradient>
        </defs>
        <path d={d} fill="none" stroke={`url(#${gid})`} strokeWidth={w} strokeLinecap="round" style={{filter: 'blur(26px)'}} />
        <path d={d} fill="none" stroke={`url(#${gid})`} strokeWidth={Math.max(3, w * 0.06)} style={{filter: 'blur(2px)', opacity: 0.85}} />
      </svg>
    </AbsoluteFill>
  );
};

/** Thin geometric rings, slowly rotating and breathing. */
const Rings: React.FC = () => {
  const frame = useCurrentFrame();
  const ring = (x: number, y: number, r: number, rate: number, o: number, dash?: string) => (
    <div
      style={{
        position: 'absolute',
        left: `${x}%`,
        top: `${y}%`,
        transform: `translate(-50%,-50%) rotate(${frame * rate}deg) scale(${1 + Math.sin(frame * 0.008 + r) * 0.03})`,
        opacity: o,
      }}
    >
      <svg width={r * 2} height={r * 2} viewBox={`0 0 ${r * 2} ${r * 2}`}>
        <circle
          cx={r}
          cy={r}
          r={r - 3}
          fill="none"
          stroke={THEME.gold}
          strokeWidth="1.6"
          strokeDasharray={dash}
        />
      </svg>
    </div>
  );

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {ring(87, 15, 150, 0.05, 0.4)}
      {ring(87, 15, 108, -0.08, 0.3, '5 9')}
      {ring(10, 82, 190, -0.04, 0.32)}
      {ring(10, 82, 132, 0.06, 0.24, '2 12')}
      {ring(6, 12, 70, 0.09, 0.25, '4 7')}
    </AbsoluteFill>
  );
};

/** Slow diagonal glints drifting through the frame. */
const LightStreaks: React.FC = () => {
  const frame = useCurrentFrame();
  const streaks = useMemo(
    () =>
      new Array(5).fill(0).map((_, i) => ({
        y: 8 + random(`sty-${i}`) * 84,
        len: 24 + random(`stl-${i}`) * 30,
        period: 480 + random(`stp-${i}`) * 420,
        offset: random(`sto-${i}`) * 900,
        tilt: -18 - random(`stt-${i}`) * 10,
        w: 1.6 + random(`stw-${i}`) * 2.2,
      })),
    [],
  );

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: 0.5}}>
      {streaks.map((s, i) => {
        const p = ((frame + s.offset) % s.period) / s.period;
        const x = interpolate(p, [0, 1], [-40, 130]);
        const fade = Math.sin(p * Math.PI);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${x}%`,
              top: `${s.y}%`,
              width: `${s.len}%`,
              height: s.w,
              transform: `rotate(${s.tilt}deg)`,
              background: 'linear-gradient(90deg, transparent, rgba(255,238,200,0.8), transparent)',
              filter: 'blur(1.5px)',
              opacity: fade * 0.6,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/** Anamorphic flare that blooms behind a title landing, then decays. */
const Flare: React.FC<{atFrame: number; y: number; hold?: number}> = ({atFrame, y, hold = 70}) => {
  const frame = useCurrentFrame();
  const rise = ease(frame, atFrame, 22, 0, 1, out);
  const fall = ease(frame, atFrame + hold, 60, 1, 0);
  const o = rise * fall;
  if (o <= 0.01) return null;

  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: `${y}%`, pointerEvents: 'none', opacity: o}}>
      <div
        style={{
          margin: '0 auto',
          width: `${44 + rise * 40}%`,
          height: 3,
          background: 'linear-gradient(90deg, transparent, rgba(160,215,235,0.9), rgba(255,246,220,1), rgba(160,215,235,0.9), transparent)',
          filter: 'blur(2px)',
          boxShadow: '0 0 40px rgba(190,225,240,0.6)',
        }}
      />
      <div
        style={{
          margin: '-30px auto 0',
          width: 300,
          height: 60,
          background: 'radial-gradient(ellipse, rgba(255,244,214,0.5) 0%, transparent 70%)',
          filter: 'blur(10px)',
        }}
      />
    </div>
  );
};

/* --------------------------------------------------------------------- type */

/** Cinematic text: fades up through a tracking ease with a soft focus pull. */
const CineText: React.FC<{
  text: string;
  atFrame: number;
  dur?: number;
  size: number;
  display?: boolean;
  color?: string;
  trackFrom?: number;
  trackTo?: number;
  glow?: number;
}> = ({text, atFrame, dur = 46, size, display, color = THEME.paper, trackFrom = 0.42, trackTo = 0.14, glow = 0}) => {
  const frame = useCurrentFrame();
  if (frame < atFrame) return null;

  const p = ease(frame, atFrame, dur, 0, 1);
  const track = trackFrom + (trackTo - trackFrom) * p;

  return (
    <div
      style={{
        fontFamily: display ? 'var(--display), sans-serif' : 'var(--body), sans-serif',
        fontWeight: display ? 400 : 600,
        fontSize: size,
        lineHeight: 1.06,
        color,
        letterSpacing: `${track}em`,
        textIndent: `${track}em`,
        textAlign: 'center',
        opacity: p,
        transform: `translateY(${(1 - p) * 34}px) scale(${1.035 - p * 0.035})`,
        filter: `blur(${(1 - p) * 7}px)`,
        textShadow: glow
          ? `0 0 ${28 + glow * 26}px rgba(245,217,138,${0.3 + glow * 0.3}), 0 8px 44px rgba(0,0,0,0.7)`
          : '0 8px 44px rgba(0,0,0,0.7)',
        whiteSpace: 'pre-line',
      }}
    >
      {text}
    </div>
  );
};

/* -------------------------------------------------------------------- scene */

export const AdjusterCinematic: React.FC<{withAudio?: boolean}> = ({withAudio = true}) => {
  const alpha = useTransparent();
  const frame = useCurrentFrame();
  const cam = useCamera(frame);

  // Rack-focus handoff between the two acts — a defocus, never a cut.
  const act1Out = ease(frame, B.actTwo - 26, 40, 0, 1);
  const act2In = ease(frame, B.actTwo, 48, 0, 1);

  // The invalidation: the claim softens and recedes as the truth arrives.
  const invalidate = ease(frame, B.finding, 50, 0, 1);
  const lineSweep = ease(frame, B.finding + 6, 34, 0, 1);

  const glowPulse = 0.5 + Math.sin(frame * 0.02) * 0.5;

  return (
    <AbsoluteFill style={{backgroundColor: alpha ? 'transparent' : '#05060a'}}>
      {withAudio ? <Audio src={staticFile('audio/vo-adjuster.mp3')} /> : null}

      {/* background planes — opaque render only */}
      {!alpha && (
        <>
          <Plane depth={1} cam={cam}>
            <GradientMesh />
          </Plane>
          <Plane depth={0.85} cam={cam}>
            <BokehField seed="far" count={16} />
          </Plane>
          <GodRays />
          <Plane depth={0.55} cam={cam}>
            <BokehField seed="mid" count={12} />
          </Plane>
        </>
      )}

      {!alpha && (
        <AbsoluteFill
          style={{
            background:
              'radial-gradient(ellipse 70% 26% at 50% 18%, rgba(214,178,110,0.16) 0%, transparent 70%), radial-gradient(ellipse 64% 20% at 50% 82%, rgba(214,178,110,0.1) 0%, transparent 70%)',
          }}
        />
      )}

      {/* graphics ambience — survives the alpha pass */}
      <Plane depth={0.5} cam={cam}>
        <Ribbon y={330} amp={60} rate={0.011} phase={0} opacity={0.44} />
        <Ribbon y={1610} amp={72} rate={0.009} phase={2.6} opacity={0.38} hue="150,185,195" />
        <Rings />
      </Plane>
      <Plane depth={0.35} cam={cam}>
        <LightStreaks />
      </Plane>

      {/* ============================== ACT 1 ============================== */}
      <Plane depth={0.22} cam={cam}>
        <AbsoluteFill
          style={{
            opacity: 1 - act1Out,
            filter: `blur(${act1Out * 12}px)`,
            transform: `scale(${1 + act1Out * 0.04})`,
          }}
        >
          <Flare atFrame={B.forty + 16} y={17.5} />

          {/* upper third */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: '8%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 22,
            }}
          >
            <CineText text="THE ADJUSTER SAYS" atFrame={B.kicker} size={34} color={THEME.gold} trackFrom={0.6} trackTo={0.3} />
            <div style={{position: 'relative'}}>
              <div
                style={{
                  opacity: 1 - invalidate * 0.62,
                  filter: `blur(${invalidate * 2.5}px) saturate(${1 - invalidate * 0.5})`,
                  transform: `scale(${1 - invalidate * 0.05})`,
                }}
              >
                <CineText text={'40%\nAT FAULT'} atFrame={B.forty} size={132} display glow={glowPulse * 0.5} />
              </div>
              {/* a single gold line draws through the claim — graceful, not violent */}
              <div
                style={{
                  position: 'absolute',
                  left: '-8%',
                  top: '48%',
                  width: `${lineSweep * 116}%`,
                  height: 5,
                  transform: 'rotate(-6deg)',
                  background: `linear-gradient(90deg, transparent, ${THEME.goldBright}, transparent)`,
                  boxShadow: `0 0 24px ${THEME.goldBright}aa`,
                  opacity: lineSweep > 0 ? 0.95 : 0,
                }}
              />
            </div>
            <CineText
              text="THEIR OPENING POSITION"
              atFrame={B.opening}
              size={33}
              color={THEME.gold}
              trackFrom={0.5}
              trackTo={0.26}
            />
          </div>

          {/* lower third */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: '76%',
              display: 'flex',
              justifyContent: 'center',
            }}
          >
            <CineText
              text="NOT A LEGAL FINDING"
              atFrame={B.finding}
              dur={54}
              size={72}
              display
              color={THEME.goldBright}
              glow={1}
            />
          </div>
        </AbsoluteFill>
      </Plane>

      {/* ============================== ACT 2 ============================== */}
      <Plane depth={0.22} cam={cam}>
        <AbsoluteFill
          style={{
            opacity: act2In,
            filter: `blur(${(1 - act2In) * 12}px)`,
            transform: `scale(${1.05 - act2In * 0.05})`,
          }}
        >
          <Flare atFrame={B.brand + 14} y={15.5} hold={110} />
          <Flare atFrame={B.url + 10} y={83} hold={90} />

          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: '9%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 26,
            }}
          >
            <CineText text={'AWESOME\nATTORNEYS'} atFrame={B.brand} dur={56} size={112} display glow={glowPulse * 0.7} />
            <CineText
              text="PHOENIX INJURY ATTORNEY"
              atFrame={B.phoenix}
              size={31}
              color={THEME.gold}
              trackFrom={0.55}
              trackTo={0.3}
            />
          </div>

          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: '74%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 20,
            }}
          >
            <div style={{display: 'flex', alignItems: 'center', gap: 26}}>
              <CineText text="GET MATCHED" atFrame={B.matched} size={52} display color={THEME.paper} />
              {frame >= B.paid ? (
                <div
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    background: THEME.gold,
                    opacity: ease(frame, B.paid, 30, 0, 0.9),
                  }}
                />
              ) : null}
              <CineText text="GET PAID" atFrame={B.paid} size={52} display color={THEME.paper} />
            </div>
            <CineText
              text="AwesomeAttorneys.com"
              atFrame={B.url}
              dur={52}
              size={47}
              color={THEME.goldBright}
              trackFrom={0.2}
              trackTo={0.03}
              glow={0.8}
            />
          </div>
        </AbsoluteFill>
      </Plane>

      {/* finishing — opaque render only (both early-return in alpha) */}
      <Vignette strength={0.55} />
      <Grain opacity={0.07} cycle={2} />
    </AbsoluteFill>
  );
};
