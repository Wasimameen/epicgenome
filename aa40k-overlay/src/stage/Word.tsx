/**
 * Things that live in the 3D world.
 *
 * `<Posed>` is the generic citizen: it holds a world pose and a three-stage
 * envelope — arrive, demote (drift out of focus), leave. `<Word>` is a `<Posed>`
 * with type in it and an optional echo ghost.
 *
 * A demoted item does not cut away. It stays where it was, goes `steel`, blurs,
 * shrinks and dims — so the world behind the current word keeps its depth.
 */

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Pose} from './Camera3D';
import {EASE, MaskReveal, SPRING, mix, useRamp, useSpringAt} from '../overlays/lib';
import {TYPE_BASE} from '../font';
import {TRACKING, textShadow, type Tone} from '../theme';

export type ExitKind = 'tumble' | 'lift' | 'recede' | 'none';

export type PosedProps = {
  readonly pose: Pose;
  readonly enterAt: number;
  readonly enterDur?: number;
  readonly enterConfig?: {damping: number; stiffness: number; mass: number};
  /** arrival depth — the 40% slam comes in from +260 */
  readonly enterFromZ?: number;
  readonly enterScaleFrom?: number;
  /**
   * How long the item takes to reach full opacity, independent of the spring
   * that carries its position. A slam has to be *there* on its frame; letting
   * the alpha ride the settle spring turns every arrival into a slow fade.
   */
  readonly opacityDur?: number;
  /** when this item stops being the subject: steel, blur, shrink, dim */
  readonly demoteAt?: number;
  readonly demoteDur?: number;
  /** extra drop / tilt applied together with the demote (the stamp box) */
  readonly demoteDropY?: number;
  readonly demoteTilt?: number;
  readonly exitAt?: number;
  readonly exitKind?: ExitKind;
  readonly exitDur?: number;
  readonly style?: React.CSSProperties;
  readonly children: React.ReactNode;
};

const EXIT: Record<Exclude<ExitKind, 'none'>, {rx: number; z: number; y: number; blur: number}> = {
  /** the "40%" group falling out of the world once it has been struck through */
  tumble: {rx: -40, z: -600, y: 40, blur: 12},
  /** a light rise-and-away */
  lift: {rx: 8, z: 120, y: -90, blur: 9},
  /** straight back into the depth */
  recede: {rx: 0, z: -520, y: 0, blur: 10},
};

export const Posed: React.FC<PosedProps> = ({
  pose,
  enterAt,
  enterDur = 0.6,
  enterConfig = SPRING.overdamped,
  enterFromZ = 0,
  enterScaleFrom = 0.92,
  opacityDur = 0.2,
  demoteAt,
  demoteDur = 0.55,
  demoteDropY = 0,
  demoteTilt = 0,
  exitAt,
  exitKind = 'recede',
  exitDur = 0.6,
  style,
  children,
}) => {
  const pIn = useSpringAt(enterAt, enterConfig, enterDur);
  const pShow = useRamp(enterAt, opacityDur, EASE.expoOut);
  const pDemote = useRamp(demoteAt ?? 1e6, demoteDur, EASE.smooth);
  const pExit = useRamp(exitAt ?? 1e6, exitDur, EASE.expoIn);

  const e = exitKind === 'none' ? {rx: 0, z: 0, y: 0, blur: 0} : EXIT[exitKind];

  const x = pose.x;
  const y = pose.y + demoteDropY * pDemote + e.y * pExit;
  const z = pose.z + enterFromZ * (1 - pIn) + e.z * pExit;
  const rx = pose.rx + e.rx * pExit;
  const ry = pose.ry;
  const rz = pose.rz + demoteTilt * pDemote;
  const scale = mix(enterScaleFrom, 1, pIn) * mix(1, 0.9, pDemote);

  // A demoted word has to read as depth, not as a legible word clipped by the
  // frame edge — but push this much past ~6px and a beat with two demoted
  // elements turns the whole frame to mush.
  const blur = 6 * pDemote + e.blur * pExit;
  const opacity = pShow * (1 - pExit) * mix(1, 0.45, pDemote);

  return (
    <AbsoluteFill
      style={{
        transformStyle: 'preserve-3d',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          position: 'relative',
          transformStyle: 'preserve-3d',
          transform: [
            `translate3d(${x}px, ${y}px, ${z}px)`,
            `rotateX(${rx}deg)`,
            `rotateY(${ry}deg)`,
            `rotateZ(${rz}deg)`,
            `scale(${scale})`,
          ].join(' '),
          opacity,
          filter: blur > 0.01 ? `blur(${blur}px)` : undefined,
          ...style,
        }}
      >
        {children}
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ *
 * Type in the world
 * ------------------------------------------------------------------ */

export type WordProps = Omit<PosedProps, 'children'> & {
  readonly text: string;
  readonly size: number;
  readonly weight?: 500 | 700 | 800;
  readonly color: string;
  /** colour it fades to once demoted — `steel` for everything that has passed */
  readonly demoteColor?: string;
  readonly tracking?: string;
  readonly uppercase?: boolean;
  readonly tone: Tone;
  /** the 2.2x, ~10% ghost that sits behind and drifts the other way */
  readonly echo?: boolean;
  readonly echoOpacity?: number;
  readonly echoColor?: string;
  /** mask-wipe direction for the arrival */
  readonly wipe?: 'up' | 'down' | 'left' | 'right';
  readonly shadowScale?: number;
};

export const Word: React.FC<WordProps> = ({
  text,
  size,
  weight = 800,
  color,
  demoteColor,
  tracking,
  uppercase = false,
  tone,
  echo = false,
  echoOpacity = 0.1,
  echoColor,
  wipe = 'up',
  shadowScale = 1,
  ...posed
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sec = frame / fps;

  const pIn = useSpringAt(posed.enterAt, posed.enterConfig ?? SPRING.overdamped, 0.5);
  const pDemote = useRamp(posed.demoteAt ?? 1e6, posed.demoteDur ?? 0.55, EASE.smooth);

  // The word creeps a few px one way; its ghost creeps the other. Deterministic,
  // slow, and it keeps nothing on screen perfectly frozen mid-beat.
  const elapsed = Math.max(0, sec - posed.enterAt);
  const drift = Math.min(elapsed, 6) * 3.5;
  const ghostDrift = -Math.min(elapsed, 6) * 9;

  const type: React.CSSProperties = {
    ...TYPE_BASE,
    fontSize: size,
    fontWeight: weight,
    letterSpacing: tracking ?? (weight === 800 ? TRACKING.hero : TRACKING.label),
    lineHeight: 1,
    textTransform: uppercase ? 'uppercase' : 'none',
  };

  return (
    <Posed {...posed}>
      {echo ? (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              ...type,
              color: echoColor ?? color,
              opacity: echoOpacity * pIn,
              transform: `translateX(${ghostDrift}px) scale(2.2)`,
            }}
          >
            {text}
          </div>
        </div>
      ) : null}

      <MaskReveal
        progress={pIn}
        direction={wipe}
        softness={10}
        style={{position: 'relative', zIndex: 1}}
      >
        <div
          style={{
            ...type,
            color,
            transform: `translateX(${drift}px)`,
            textShadow: textShadow(tone, shadowScale),
          }}
        >
          {demoteColor ? (
            // A real cross-fade between the live colour and `steel`, so the
            // de-emphasis reads as a grade rather than a swap on one frame.
            <span style={{position: 'relative', display: 'inline-block'}}>
              <span style={{opacity: 1 - pDemote}}>{text}</span>
              <span
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  color: demoteColor,
                  opacity: pDemote,
                }}
              >
                {text}
              </span>
            </span>
          ) : (
            text
          )}
        </div>
      </MaskReveal>
    </Posed>
  );
};
