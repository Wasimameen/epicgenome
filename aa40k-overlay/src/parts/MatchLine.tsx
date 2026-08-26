/**
 * The match graphic — the whole argument of beat 3 in one figure.
 *
 * Two gold dots (YOU / ATTORNEY) with a line drawn between them. Two faint
 * steel dots sit in the middle from the start of the beat; on "directly" they
 * shrink to nothing, the line's sag snaps out straight and brightens, and the
 * word DIRECTLY travels along it. No explanatory copy — the figure is the
 * message.
 *
 * The path carries `pathLength={1}`, so every draw and every travelling pulse
 * is expressed in normalised 0..1 units and never has to guess at arc length.
 */

import React from 'react';
import {EASE, useRamp, rgba} from '../overlays/lib';
import {TYPE_BASE} from '../font';
import {TRACKING, labelShadow, textShadow, vectorShadow, type Tone} from '../theme';

export type MatchTimes = {
  /** the two faint steel middlemen, on screen from the start of the beat */
  mid: number;
  dots: number;
  line: number;
  pulse: number;
  ring: number;
  directly: number;
};

const LINE_DUR = 0.5;
const DIRECTLY_DUR = 0.55;

/** px/frame of the fastest edge in this figure — feeds the stage motion blur. */
export const matchSpeed = (
  sec: number,
  times: MatchTimes,
  fps: number,
  span: number,
): number => {
  const draw = (t: number) =>
    EASE.expoOut(Math.min(1, Math.max(0, (t - times.line) / LINE_DUR)));
  const slide = (t: number) =>
    EASE.expoOut(Math.min(1, Math.max(0, (t - times.directly) / DIRECTLY_DUR)));
  const pulse = (t: number) =>
    EASE.smooth(Math.min(1, Math.max(0, (t - times.pulse) / 0.45)));
  const d = 1 / fps;
  return Math.max(
    Math.abs(draw(sec) - draw(sec - d)) * span,
    Math.abs(slide(sec) - slide(sec - d)) * span,
    Math.abs(pulse(sec) - pulse(sec - d)) * span,
  );
};

export const MatchLine: React.FC<{
  readonly span: number;
  readonly height: number;
  readonly dotR: number;
  readonly stroke: number;
  readonly gold: string;
  readonly steel: string;
  readonly white: string;
  readonly tone: Tone;
  readonly times: MatchTimes;
  readonly labelSize: number;
  readonly travelSize: number;
  readonly leftLabel: string;
  readonly rightLabel: string;
  readonly travelLabel: string;
}> = ({
  span,
  height,
  dotR,
  stroke,
  gold,
  steel,
  white,
  tone,
  times,
  labelSize,
  travelSize,
  leftLabel,
  rightLabel,
  travelLabel,
}) => {
  const pad = dotR * 4;
  const w = span + pad * 2;
  const h = height;
  const cx = w / 2;
  const cy = h / 2;

  const pMid = useRamp(times.mid, 0.6, EASE.expoOut);
  const pDots = useRamp(times.dots, 0.45, EASE.expoOut);
  const pLine = useRamp(times.line, LINE_DUR, EASE.expoOut);
  const pPulse = useRamp(times.pulse, 0.45, EASE.smooth);
  const pRing = useRamp(times.ring, 0.45, EASE.expoOut);
  const pFlash = useRamp(times.pulse, 0.3, EASE.expoOut);
  const pDirect = useRamp(times.directly, DIRECTLY_DUR, EASE.expoOut);

  // The bow straightens on "directly"; the line brightens as it does.
  const sag = (1 - pDirect) * dotR * 2.6;
  const x0 = cx - span / 2;
  const x1 = cx + span / 2;
  const ctrlY = cy + sag * 2;
  const d = `M ${x0} ${cy} Q ${cx} ${ctrlY} ${x1} ${cy}`;

  const at = (u: number) => ({
    x: (1 - u) * (1 - u) * x0 + 2 * (1 - u) * u * cx + u * u * x1,
    y: (1 - u) * (1 - u) * cy + 2 * (1 - u) * u * ctrlY + u * u * cy,
  });

  // DIRECTLY stops short of the right-hand dot: centred on the dot itself, its
  // second half hangs past the frame edge.
  const travel = at(pDirect * 0.78);
  const lineWidth = stroke * (1 + 0.35 * pDirect);

  const label: React.CSSProperties = {
    ...TYPE_BASE,
    fontSize: labelSize,
    fontWeight: 500,
    letterSpacing: TRACKING.label,
    textTransform: 'uppercase',
    lineHeight: 1,
    // label-size type gets the tight ring, not just the wide soft shadow
    textShadow: labelShadow(tone),
  };

  return (
    <div style={{position: 'relative', width: w, height: h}}>
      <svg
        width={w}
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', filter: vectorShadow(tone)}}
      >
        {/* the connection */}
        <path
          d={d}
          pathLength={1}
          fill="none"
          stroke={rgba(gold, 0.55 + 0.45 * pDirect)}
          strokeWidth={lineWidth}
          strokeLinecap="round"
          strokeDasharray="1 1"
          strokeDashoffset={1 - pLine}
        />
        {/* the bright pulse that runs along it */}
        {pPulse > 0 && pPulse < 1 ? (
          <path
            d={d}
            pathLength={1}
            fill="none"
            stroke={white}
            strokeWidth={lineWidth * 1.15}
            strokeLinecap="round"
            strokeDasharray="0.09 0.91"
            strokeDashoffset={-(pPulse * 1.09 - 0.09)}
            opacity={0.9 * Math.sin(Math.PI * pPulse)}
          />
        ) : null}

        {/* the two faint middlemen: there from the start of the beat, gone by
            the end of "directly" — the whole argument of the figure */}
        {[0.36, 0.64].map((u, i) => {
          const p = at(u);
          const r = dotR * 0.42 * (1 - pDirect) * pMid;
          return r <= 0.01 ? null : (
            <circle
              key={`mid-${i}`}
              cx={p.x}
              cy={p.y}
              r={r}
              fill={rgba(steel, 0.75 * (1 - pDirect))}
            />
          );
        })}

        {/* the two ends. The ATTORNEY dot shrinks back as the check ring draws
            around it, so the ring and tick read as one badge instead of the
            tick sitting muddily on top of a same-coloured disc. */}
        {[
          {x: x0, key: 'l', shrink: 0},
          {x: x1, key: 'r', shrink: 0.5},
        ].map(({x, key, shrink}) => (
          <circle
            key={key}
            cx={x}
            cy={cy}
            r={
              dotR *
              pDots *
              (1 + 0.28 * Math.sin(Math.PI * pFlash)) *
              (1 - shrink * pRing)
            }
            fill={gold}
          />
        ))}

        {/* check ring around ATTORNEY */}
        {pRing > 0 ? (
          <>
            <circle
              cx={x1}
              cy={cy}
              r={dotR * 2.35}
              fill="none"
              stroke={gold}
              strokeWidth={stroke * 0.75}
              strokeLinecap="round"
              pathLength={1}
              strokeDasharray="1 1"
              strokeDashoffset={1 - pRing}
              transform={`rotate(-90 ${x1} ${cy})`}
            />
            <path
              d={`M ${x1 - dotR * 1.05} ${cy + dotR * 0.05} L ${x1 - dotR * 0.28} ${
                cy + dotR * 0.82
              } L ${x1 + dotR * 1.15} ${cy - dotR * 0.95}`}
              fill="none"
              stroke={gold}
              strokeWidth={stroke * 0.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              pathLength={1}
              strokeDasharray="1 1"
              strokeDashoffset={1 - Math.max(0, (pRing - 0.35) / 0.65)}
            />
          </>
        ) : null}
      </svg>

      {/* end labels */}
      <div
        style={{
          ...label,
          position: 'absolute',
          left: x0,
          top: cy + dotR * 2.6,
          transform: `translate(-50%, 0) translateY(${(1 - pDots) * 14}px)`,
          color: white,
          opacity: pDots,
        }}
      >
        {leftLabel}
      </div>
      <div
        style={{
          ...label,
          position: 'absolute',
          left: x1,
          top: cy + dotR * 3.4,
          transform: `translate(-50%, 0) translateY(${(1 - pDots) * 14}px)`,
          color: white,
          opacity: pDots,
        }}
      >
        {rightLabel}
      </div>

      {/* the word that travels the line — anchored statically at the left dot
          and moved with `transform` only, never by animating left/top */}
      {pDirect > 0 ? (
        <div
          style={{
            ...TYPE_BASE,
            position: 'absolute',
            left: x0,
            top: cy,
            fontSize: travelSize,
            fontWeight: 800,
            letterSpacing: TRACKING.hero,
            textTransform: 'uppercase',
            lineHeight: 1,
            color: white,
            textShadow: textShadow(tone),
            transform: `translate3d(${travel.x - x0}px, ${travel.y - cy}px, 0) translate(-50%, -160%) scale(${
              0.88 + 0.12 * pDirect
            })`,
            opacity: Math.min(1, pDirect * 4),
          }}
        >
          {travelLabel}
        </div>
      ) : null}
    </div>
  );
};
