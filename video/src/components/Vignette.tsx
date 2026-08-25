import React from 'react';
import {AbsoluteFill} from 'remotion';

/** Heavy cinematic falloff — keeps the eye pinned to centre frame. */
export const Vignette: React.FC<{strength?: number}> = ({strength = 0.92}) => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      background: `radial-gradient(ellipse 62% 48% at 50% 44%, rgba(0,0,0,0) 0%, rgba(0,0,0,${
        strength * 0.35
      }) 52%, rgba(0,0,0,${strength}) 100%)`,
    }}
  />
);
