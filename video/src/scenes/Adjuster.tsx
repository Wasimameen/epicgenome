import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {useTransparent} from '../alpha';
import {DustMotes} from '../components/DustMotes';
import {Stamp} from '../components/Stamp';
import {THEME} from '../theme';

/**
 * "Adjuster" overlay — a 14s b-roll frame, not a full-screen composition.
 *
 * Layout contract: the middle of the frame (roughly 27%–69% vertically) stays
 * EMPTY so the editor's b-roll shows through the alpha. Graphics live in a top
 * zone and a bottom zone, plus corner brackets that frame the b-roll window.
 * Nothing — including shakes and flashes — may cross into the window.
 *
 * Cues are word timestamps from public/audio/vo-adjuster.mp3 (14.1s):
 *   "So an adjuster told you you're 40% at fault."  0.00 - 2.38
 *   "That's their opening position,"                3.48 - 4.00
 *   "not a legal finding."                          4.82 - 5.42
 *   "Awesome attorneys ... Phoenix injury attorney" 6.70 - 9.50
 *   "Get matched," / "get paid,"                    10.46 / 11.32
 *   "awesomeattorneys.com"                          12.36 - 13.10
 */
const at = (sec: number) => Math.round(sec * 30);

const B = {
  bracketsIn: 0,
  adjusterChip: at(0.3),
  fortySlam: at(1.54) - 4,
  atFault: at(2.22) - 3,
  openingTag: at(3.48) - 3,
  strike: at(4.82) - 4,
  stamp: at(4.82) - 6,
  topExit: at(6.3),
  brand: at(6.7) - 5,
  phoenix: at(8.82) - 5,
  getMatched: at(10.46) - 6,
  getPaid: at(11.32) - 6,
  url: at(12.36) - 6,
};

export const ADJUSTER_FRAMES = at(14.106) + 4;

/** Fast spring — this spot never eases gently. */
const snap = (frame: number, fps: number, delay: number) =>
  spring({frame: frame - delay, fps, config: {damping: 14, mass: 0.45, stiffness: 320}});

/** Small angled tag — insurance-paperwork energy. */
const Tag: React.FC<{text: string; delay: number; color?: string; angle?: number}> = ({
  text,
  delay,
  color = THEME.gold,
  angle = -3,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = snap(frame, fps, delay);
  if (frame < delay) return null;

  return (
    <div
      style={{
        display: 'inline-block',
        transform: `rotate(${angle}deg) scale(${0.6 + s * 0.4})`,
        opacity: s,
        border: `4px solid ${color}`,
        padding: '10px 26px',
        fontFamily: 'var(--body), sans-serif',
        fontWeight: 700,
        fontSize: 34,
        letterSpacing: '0.18em',
        textIndent: '0.18em',
        color,
        background: 'rgba(8,7,10,0.55)',
        boxShadow: `0 0 26px ${color}44`,
      }}
    >
      {text}
    </div>
  );
};

const Pill: React.FC<{text: string; delay: number}> = ({text, delay}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = snap(frame, fps, delay);
  if (frame < delay) return null;
  return (
    <div
      style={{
        opacity: s,
        transform: `scale(${0.7 + s * 0.3})`,
        border: `4px solid ${THEME.goldBright}`,
        borderRadius: 999,
        padding: '14px 38px',
        fontFamily: 'var(--display), sans-serif',
        fontSize: 46,
        color: THEME.goldBright,
        whiteSpace: 'nowrap',
        background: 'rgba(8,7,10,0.5)',
        boxShadow: `0 0 34px ${THEME.goldBright}33`,
      }}
    >
      {text}
    </div>
  );
};

export const Adjuster: React.FC<{withAudio?: boolean}> = ({withAudio = true}) => {
  const alpha = useTransparent();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const chipIn = snap(frame, fps, B.adjusterChip);
  const fortyIn = snap(frame, fps, B.fortySlam);
  const faultIn = snap(frame, fps, B.atFault);
  const brandIn = snap(frame, fps, B.brand);
  const urlIn = snap(frame, fps, B.url);

  // Top block whips out hard before the CTA claims the frame.
  const topOut = interpolate(frame, [B.topExit, B.topExit + 9], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.quad),
  });

  // Zone-local jolt on the stamp; never leaks into the b-roll window.
  const jolt = frame >= B.stamp ? Math.max(0, 1 - (frame - B.stamp) / 12) : 0;
  const joltY = Math.sin(frame * 2.1) * jolt * 9;

  const struck = frame >= B.strike;
  const glow = interpolate(Math.sin(frame * 0.18), [-1, 1], [0.3, 0.6]);

  return (
    <AbsoluteFill style={{backgroundColor: alpha ? 'transparent' : '#0b0a0e'}}>
      {withAudio ? <Audio src={staticFile('audio/vo-adjuster.mp3')} /> : null}
      <DustMotes count={16} seed="adj" opacity={0.3} />

      {/* ============ TOP ZONE (6% - 26%) ============ */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: '5.5%',
          height: '20.5%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 14,
          opacity: 1 - topOut,
          transform: `translateY(${-topOut * 90 + joltY}px)`,
        }}
      >
        <div style={{opacity: chipIn, transform: `translateY(${(1 - chipIn) * -26}px)`}}>
          <Tag text="THE ADJUSTER SAYS" delay={B.adjusterChip} angle={-2} />
        </div>

        <div style={{display: 'flex', alignItems: 'baseline', gap: 22, position: 'relative'}}>
          <span
            style={{
              fontFamily: 'var(--display), sans-serif',
              fontSize: 128,
              lineHeight: 1,
              color: struck ? '#d8402f' : THEME.paper,
              opacity: fortyIn,
              transform: `scale(${0.5 + fortyIn * 0.5})`,
              textShadow: struck ? '0 0 34px rgba(216,64,47,0.5)' : '0 6px 30px rgba(0,0,0,0.8)',
            }}
          >
            40%
          </span>
          <span
            style={{
              fontFamily: 'var(--display), sans-serif',
              fontSize: 62,
              color: THEME.gold,
              opacity: faultIn,
              transform: `translateX(${(1 - faultIn) * 40}px)`,
            }}
          >
            AT FAULT
          </span>
          {/* red strike whips across the number on "not a legal finding" */}
          {struck ? (
            <div
              style={{
                position: 'absolute',
                left: '-4%',
                top: '52%',
                width: `${interpolate(frame, [B.strike, B.strike + 6], [0, 108], {extrapolateRight: 'clamp'})}%`,
                height: 10,
                background: '#d8402f',
                transform: 'rotate(-7deg)',
                boxShadow: '0 0 22px rgba(216,64,47,0.8)',
              }}
            />
          ) : null}
        </div>

        {frame >= B.openingTag && frame < B.stamp ? (
          <Tag text="THEIR OPENING POSITION" delay={B.openingTag} angle={2} />
        ) : null}
        {frame >= B.stamp ? (
          <div style={{transform: 'scale(0.62)', transformOrigin: 'center top', marginTop: -8}}>
            <Stamp text="NOT A LEGAL FINDING" startAt={B.stamp} color="#d8402f" angle={-4} />
          </div>
        ) : null}
      </div>

      {/* ============ BOTTOM ZONE (72% - 96%) ============ */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: '72%',
          height: '24%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 18,
        }}
      >
        {frame < B.brand ? null : (
          <>
            <div
              style={{
                fontFamily: 'var(--display), sans-serif',
                fontSize: 78,
                lineHeight: 1,
                color: THEME.paper,
                opacity: brandIn,
                transform: `scale(${0.7 + brandIn * 0.3})`,
                textShadow: `0 0 40px rgba(245,217,138,${glow})`,
                whiteSpace: 'nowrap',
              }}
            >
              AWESOME ATTORNEYS
            </div>
            {frame >= B.phoenix ? (
              <div
                style={{
                  fontFamily: 'var(--body), sans-serif',
                  fontWeight: 700,
                  fontSize: 30,
                  letterSpacing: '0.24em',
                  textIndent: '0.24em',
                  color: THEME.gold,
                  opacity: snap(frame, fps, B.phoenix),
                }}
              >
                PHOENIX INJURY ATTORNEY
              </div>
            ) : null}
            <div style={{display: 'flex', gap: 20}}>
              <Pill text="GET MATCHED" delay={B.getMatched} />
              <Pill text="GET PAID" delay={B.getPaid} />
            </div>
            {frame >= B.url ? (
              <div
                style={{
                  fontFamily: 'var(--body), sans-serif',
                  fontWeight: 700,
                  fontSize: 44,
                  color: THEME.goldBright,
                  opacity: urlIn,
                  transform: `scale(${0.85 + urlIn * 0.15})`,
                  textShadow: `0 0 34px ${THEME.goldBright}66`,
                }}
              >
                AwesomeAttorneys.com
              </div>
            ) : null}
          </>
        )}
      </div>
    </AbsoluteFill>
  );
};
