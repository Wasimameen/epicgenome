import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {THEME} from '../theme';
import {WordRise} from './WordRise';

type Tone = 'display' | 'kicker' | 'heavy';

const TONE: Record<Tone, React.CSSProperties> = {
  display: {
    fontFamily: 'var(--display), sans-serif',
    fontSize: 92,
    lineHeight: 1.02,
    color: THEME.paper,
    letterSpacing: '-0.015em',
  },
  kicker: {
    fontFamily: 'var(--body), sans-serif',
    fontSize: 42,
    fontWeight: 600,
    letterSpacing: '0.22em',
    textIndent: '0.22em',
    color: THEME.gold,
  },
  heavy: {
    fontFamily: 'var(--display), sans-serif',
    fontSize: 122,
    lineHeight: 0.98,
    color: THEME.paper,
    letterSpacing: '-0.02em',
  },
};

/**
 * Scene copy. Rises in word by word, and optionally drops back out so the next
 * beat starts on a clean frame rather than stacking text.
 */
export const Caption: React.FC<{
  text: string;
  startAt: number;
  exitAt?: number;
  tone?: Tone;
  stagger?: number;
  color?: string;
  style?: React.CSSProperties;
}> = ({text, startAt, exitAt, tone = 'display', stagger = 3, color, style}) => {
  const frame = useCurrentFrame();

  const exit =
    exitAt === undefined
      ? 0
      : interpolate(frame, [exitAt, exitAt + 10], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });

  return (
    <div
      style={{
        opacity: 1 - exit,
        transform: `translateY(${-exit * 26}px)`,
        filter: exit > 0 ? `blur(${exit * 10}px)` : undefined,
      }}
    >
      <WordRise
        text={text}
        startAt={startAt}
        stagger={stagger}
        style={{
          ...TONE[tone],
          ...(color ? {color} : {}),
          textAlign: 'center',
          textShadow: '0 8px 42px rgba(0,0,0,0.85)',
          ...style,
        }}
      />
    </div>
  );
};
