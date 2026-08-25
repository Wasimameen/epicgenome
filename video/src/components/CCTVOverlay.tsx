import React from 'react';
import {AbsoluteFill, interpolate, random, useCurrentFrame} from 'remotion';

const pad = (n: number, w = 2) => String(Math.floor(n)).padStart(w, '0');

/**
 * Security-camera treatment for the opening of the collision beat.
 *
 * Doubles as motion and as staging: the line is "security tries to stop a
 * shoplifter", so the surveillance frame is what the moment actually looked
 * like from the store's side. It drops away on impact, when the camera stops
 * being an observer.
 */
export const CCTVOverlay: React.FC<{
  endAt: number;
  fadeFrames?: number;
}> = ({endAt, fadeFrames = 14}) => {
  const frame = useCurrentFrame();
  if (frame > endAt) return null;

  const fade = interpolate(frame, [0, 8, endAt - fadeFrames, endAt], [0, 1, 1, 0], {
    extrapolateRight: 'clamp',
  });

  // Timecode runs at real speed from an arbitrary store-hours offset.
  const secs = 14 * 3600 + 37 * 60 + 12 + frame / 30;
  const tc = `${pad((secs / 3600) % 24)}:${pad((secs / 60) % 60)}:${pad(secs % 60)}:${pad(
    (frame % 30) * (100 / 30),
  )}`;

  const recOn = Math.floor(frame / 18) % 2 === 0;
  // Occasional tracking tear, as a cheap VHS-era artifact.
  const tearY = random(`tear-${Math.floor(frame / 7)}`) * 100;
  const tearOn = random(`ton-${Math.floor(frame / 7)}`) > 0.82;

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: fade}}>
      {/* scanlines */}
      <AbsoluteFill
        style={{
          background:
            'repeating-linear-gradient(180deg, rgba(0,0,0,0.32) 0px, rgba(0,0,0,0.32) 1px, transparent 1px, transparent 4px)',
          mixBlendMode: 'multiply',
        }}
      />
      {tearOn ? (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: `${tearY}%`,
            height: 14,
            background: 'rgba(255,255,255,0.09)',
            filter: 'blur(3px)',
          }}
        />
      ) : null}

      {/* corner brackets */}
      {[
        {top: 70, left: 60, rot: 0},
        {top: 70, right: 60, rot: 90},
        {bottom: 70, right: 60, rot: 180},
        {bottom: 70, left: 60, rot: 270},
      ].map((pos, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            ...pos,
            width: 74,
            height: 74,
            borderTop: '4px solid rgba(255,255,255,0.5)',
            borderLeft: '4px solid rgba(255,255,255,0.5)',
            transform: `rotate(${pos.rot}deg)`,
          }}
        />
      ))}

      <div
        style={{
          position: 'absolute',
          top: 96,
          left: 96,
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          fontFamily: 'var(--body), monospace',
          fontSize: 30,
          fontWeight: 600,
          letterSpacing: '0.12em',
          color: 'rgba(255,255,255,0.82)',
        }}
      >
        <span
          style={{
            width: 18,
            height: 18,
            borderRadius: '50%',
            background: '#e03a3a',
            opacity: recOn ? 1 : 0.15,
          }}
        />
        REC
      </div>

      <div
        style={{
          position: 'absolute',
          bottom: 96,
          left: 96,
          fontFamily: 'var(--body), monospace',
          fontSize: 32,
          fontWeight: 600,
          letterSpacing: '0.08em',
          color: 'rgba(255,255,255,0.82)',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {tc}
      </div>

      <div
        style={{
          position: 'absolute',
          bottom: 96,
          right: 96,
          fontFamily: 'var(--body), monospace',
          fontSize: 30,
          fontWeight: 600,
          letterSpacing: '0.14em',
          color: 'rgba(255,255,255,0.6)',
        }}
      >
        CAM 04
      </div>
    </AbsoluteFill>
  );
};
