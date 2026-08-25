import React from 'react';
import {AbsoluteFill, Composition} from 'remotion';
import {FONT_STACK, loadFonts} from './fonts';
import {Reel} from './Reel';
import {TransparentContext} from './alpha';
import {Adjuster, ADJUSTER_FRAMES} from './scenes/Adjuster';
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
    {/*
      Alpha pass for compositing: identical timing, with every background-only
      layer dropped (ground fills, money plate, live footage, vignette, grain).
      Render with:
        npx remotion render ReelAlpha out/reel-alpha.mov \
          --codec=prores --prores-profile=4444 --image-format=png
    */}
    <Composition
      id="ReelAlpha"
      component={() => (
        <FontVars>
          <Reel transparent />
        </FontVars>
      )}
      durationInFrames={TOTAL_FRAMES}
      fps={VIDEO.fps}
      width={VIDEO.width}
      height={VIDEO.height}
    />

    {/*
      The alpha graphics laid on pure black, for editors that cannot read an
      alpha channel. Set the clip's blend mode to Screen and the black drops
      out — for graphics this bright on this dark a ground, it keeps the glows
      and soft edges that a chroma key would fringe. Ships as ordinary H.264.
    */}
    <Composition
      id="ReelScreenBlend"
      component={() => (
        <AbsoluteFill style={{backgroundColor: '#000'}}>
          <FontVars>
            <Reel transparent />
          </FontVars>
        </AbsoluteFill>
      )}
      durationInFrames={TOTAL_FRAMES}
      fps={VIDEO.fps}
      width={VIDEO.width}
      height={VIDEO.height}
    />

    {/*
      "Adjuster" spot — a 14s b-roll overlay: graphics top and bottom, the
      centre window left empty for footage. Adjuster previews on a dark card;
      AdjusterAlpha is the transparent deliverable.
    */}
    <Composition
      id="Adjuster"
      component={() => (
        <FontVars>
          <Adjuster />
        </FontVars>
      )}
      durationInFrames={ADJUSTER_FRAMES}
      fps={VIDEO.fps}
      width={VIDEO.width}
      height={VIDEO.height}
    />
    <Composition
      id="AdjusterAlpha"
      component={() => (
        <TransparentContext.Provider value={true}>
          <FontVars>
            <Adjuster />
          </FontVars>
        </TransparentContext.Provider>
      )}
      durationInFrames={ADJUSTER_FRAMES}
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
