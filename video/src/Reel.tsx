import React from 'react';
import {AbsoluteFill, Audio, Series, staticFile} from 'remotion';
import {Scene01Hook} from './scenes/Scene01Hook';
import {Scene02Crazier} from './scenes/Scene02Crazier';
import {Scene03Impact} from './scenes/Scene03Impact';
import {Scene04Down} from './scenes/Scene04Down';
import {Scene05Surgeries} from './scenes/Scene05Surgeries';
import {Scene06Court} from './scenes/Scene06Court';
import {Scene07OnTheLine} from './scenes/Scene07OnTheLine';
import {Scene08Verdict} from './scenes/Scene08Verdict';
import {Scene09CTA} from './scenes/Scene09CTA';
import {TransparentContext} from './alpha';
import {SCENES} from './timeline';
import {THEME} from './theme';

const COMPONENTS: Record<string, React.FC> = {
  hook: Scene01Hook,
  crazier: Scene02Crazier,
  impact: Scene03Impact,
  down: Scene04Down,
  surgeries: Scene05Surgeries,
  court: Scene06Court,
  online: Scene07OnTheLine,
  verdict: Scene08Verdict,
  cta: Scene09CTA,
};

/**
 * Full 9:16 reel. Scenes hard-cut rather than cross-dissolve — at this pace a
 * dissolve reads as a stumble, and each scene already opens on its own move.
 *
 * The voiceover is laid across the whole timeline rather than per scene, so the
 * read stays continuous no matter how the scene boundaries are nudged.
 */
export const Reel: React.FC<{transparent?: boolean; withAudio?: boolean}> = ({
  transparent = false,
  withAudio = true,
}) => (
  <TransparentContext.Provider value={transparent}>
    <AbsoluteFill style={{backgroundColor: transparent ? 'transparent' : THEME.ink}}>
      {withAudio ? <Audio src={staticFile('audio/vo.mp3')} /> : null}
      <Series>
        {SCENES.map((scene) => {
          const Component = COMPONENTS[scene.id];
          return (
            <Series.Sequence key={scene.id} durationInFrames={scene.frames}>
              <Component />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  </TransparentContext.Provider>
);
