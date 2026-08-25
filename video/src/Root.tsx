import React from 'react';
import {Composition} from 'remotion';
import {FONT_STACK, loadFonts} from './fonts';
import {Reel} from './Reel';
import {Scene01Hook} from './scenes/Scene01Hook';
import {VIDEO} from './theme';
import {TOTAL_FRAMES} from './timeline';

loadFonts();

/**
 * Typefaces are exposed as CSS variables so components stay font-agnostic and a
 * brand face can be swapped in from one place later.
 */
const FontVars: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div
    style={{
      width: '100%',
      height: '100%',
      ['--display' as string]: FONT_STACK.display,
      ['--body' as string]: FONT_STACK.body,
    }}
  >
    {children}
  </div>
);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Reel"
      component={() => (
        <FontVars>
          <Reel />
        </FontVars>
      )}
      durationInFrames={TOTAL_FRAMES}
      fps={VIDEO.fps}
      width={VIDEO.width}
      height={VIDEO.height}
    />
    {/* Kept standalone so the opening can be iterated without a full render. */}
    <Composition
      id="Scene01Hook"
      component={() => (
        <FontVars>
          <Scene01Hook />
        </FontVars>
      )}
      durationInFrames={VIDEO.hookDuration}
      fps={VIDEO.fps}
      width={VIDEO.width}
      height={VIDEO.height}
    />
  </>
);
