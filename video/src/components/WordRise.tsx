import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';

/**
 * Staggered word entry. Words arrive on their own springs so the line reads
 * left-to-right at roughly speaking pace instead of appearing as a block.
 */
export const WordRise: React.FC<{
  text: string;
  startAt: number;
  stagger?: number;
  style?: React.CSSProperties;
}> = ({text, startAt, stagger = 3, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '0 0.3em', ...style}}>
      {text.split(' ').map((word, i) => {
        const s = spring({
          frame: frame - startAt - i * stagger,
          fps,
          config: {damping: 15, mass: 0.7, stiffness: 110},
        });
        return (
          <span
            key={`${word}-${i}`}
            style={{
              display: 'inline-block',
              opacity: s,
              transform: `translateY(${(1 - s) * 38}px)`,
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};
