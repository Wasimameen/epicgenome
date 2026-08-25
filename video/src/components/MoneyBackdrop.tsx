import React, {useMemo} from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {ASSETS} from '../assets';
import {THEME} from '../theme';

/**
 * Intaglio-style engraved linework, generated rather than drawn, so the hook has
 * a banknote texture even before the real macro photograph is dropped in.
 */
const EngravedLines: React.FC = () => {
  const paths = useMemo(() => {
    const rows: string[] = [];
    for (let i = 0; i < 64; i++) {
      const y = i * 16 - 40;
      const amp = 14 + (i % 7) * 3;
      const period = 150 + (i % 5) * 45;
      let d = `M -40 ${y}`;
      for (let x = -40; x <= 1160; x += 24) {
        const yy = y + Math.sin((x / period) * Math.PI * 2 + i * 0.6) * amp;
        d += ` L ${x} ${yy.toFixed(1)}`;
      }
      rows.push(d);
    }
    return rows;
  }, []);

  return (
    <svg
      viewBox="0 0 1080 1920"
      preserveAspectRatio="xMidYMid slice"
      style={{width: '100%', height: '100%'}}
    >
      <defs>
        <radialGradient id="engraveFade" cx="50%" cy="42%" r="62%">
          <stop offset="0%" stopColor="#fff" stopOpacity="0.55" />
          <stop offset="60%" stopColor="#fff" stopOpacity="0.12" />
          <stop offset="100%" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
        <mask id="engraveMask">
          <rect width="1080" height="1920" fill="url(#engraveFade)" />
        </mask>
      </defs>
      <g mask="url(#engraveMask)" fill="none" stroke={THEME.gold} strokeWidth="1.5">
        {paths.map((d, i) => (
          <path key={i} d={d} opacity={0.5 + (i % 3) * 0.16} />
        ))}
      </g>
    </svg>
  );
};

/**
 * Full-frame money plate with a slow push-in. Uses the supplied Franklin macro
 * when present, otherwise the generated engraving above.
 */
export const MoneyBackdrop: React.FC<{
  /** Frame the push-in starts from, so scenes can share one continuous move. */
  from?: number;
  durationInFrames: number;
}> = ({from = 0, durationInFrames}) => {
  const frame = useCurrentFrame();

  // Slow, unbroken Ken Burns — dread builds when the camera never quite settles.
  const scale = interpolate(frame - from, [0, durationInFrames], [1.12, 1.26], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const drift = interpolate(frame - from, [0, durationInFrames], [0, -34], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: THEME.ink, overflow: 'hidden'}}>
      <AbsoluteFill
        style={{transform: `scale(${scale}) translateY(${drift}px)`, transformOrigin: '50% 44%'}}
      >
        {/* Warm sepia ground the engraving and the photo both sit on. */}
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse 70% 52% at 50% 42%, #6b5530 0%, #2e2415 45%, ${THEME.ink} 100%)`,
          }}
        />
        {ASSETS.franklin ? (
          <Img
            src={staticFile(ASSETS.franklin)}
            style={{width: '100%', height: '100%', objectFit: 'cover', opacity: 0.95}}
          />
        ) : (
          <AbsoluteFill style={{opacity: 0.42}}>
            <EngravedLines />
          </AbsoluteFill>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
