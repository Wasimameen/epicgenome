import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {Bloom} from '../components/Bloom';
import {CameraShake} from '../components/CameraShake';
import {Caption} from '../components/Caption';
import {CartFigure} from '../components/CartFigure';
import {CCTVOverlay} from '../components/CCTVOverlay';
import {ChromaticSplit} from '../components/ChromaticSplit';
import {DustMotes} from '../components/DustMotes';
import {FlashCut} from '../components/FlashCut';
import {Grain} from '../components/Grain';
import {GrandmaFigure} from '../components/GrandmaFigure';
import {RunnerFigure} from '../components/RunnerFigure';
import {SpeedLines} from '../components/SpeedLines';
import {Vignette} from '../components/Vignette';
import {cue} from '../timeline';
import {THEME} from '../theme';

/**
 * "So security tries to stop a shoplifter — the guy BOLTS — runs straight into
 * her shopping cart — and her granddaughter is sitting in that cart."
 *
 * Cues are the frames the words are actually spoken, from the voiceover
 * transcript:
 *   "So security tries to stop a shoplifter."        10.12 - 12.02
 *   "The guy, BOLTS,"                                13.02 - 13.50
 *   "runs straight into her shopping cart,"          14.08 - 15.52
 *   "and her granddaughter is sitting in that cart." 16.36 - 18.18
 *
 * The whole scene is built to land one frame: the runner crosses the full width
 * and the collision is the only moment the camera moves.
 */
const IMPACT = cue('impact', 14.74); // the word "into"

const B = {
  security: cue('impact', 10.12) + 2,
  securityOut: cue('impact', 12.5),
  bolts: cue('impact', 13.02) - 6,
  runFrom: cue('impact', 13.3),
  cart: cue('impact', 15.22) - 6,
  granddaughter: cue('impact', 16.36) - 6,
};

export const Scene03Impact: React.FC = () => {
  const frame = useCurrentFrame();

  // Runner accelerates in, then is stopped dead by the cart at IMPACT.
  const runX = interpolate(frame, [B.runFrom, IMPACT], [-22, 44], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.quad),
  });
  const runAfter = interpolate(frame, [IMPACT, IMPACT + 16], [0, -6], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const runnerVisible = frame > B.runFrom - 6 && frame < IMPACT + 26;

  // Cart is knocked sideways and tips.
  const cartX = interpolate(frame, [IMPACT, IMPACT + 26], [54, 70], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const cartTip = interpolate(frame, [IMPACT, IMPACT + 30], [0, 26], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0d'}}>
      <ChromaticSplit impactAt={IMPACT} maxOffset={20}>
        <CameraShake impactAt={IMPACT} intensity={34}>
          <AbsoluteFill
            style={{
              background: `radial-gradient(ellipse 70% 40% at 50% 58%, #1d2430 0%, #08080b 74%)`,
            }}
          />

          <SpeedLines
            startAt={B.runFrom + 4}
            durationInFrames={IMPACT - B.runFrom}
            color={THEME.paper}
          />

          {/* Floor line grounds all three figures in the same space. */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: '74%',
              height: 3,
              background: `linear-gradient(90deg, transparent, ${THEME.gold}66, transparent)`,
            }}
          />

          {/* Grandmother, standing with the cart until the hit. */}
          <div
            style={{position: 'absolute', left: '76%', top: '74%', transform: 'translate(-50%, -100%)'}}
          >
            <GrandmaFigure height={500} />
          </div>

          <div
            style={{
              position: 'absolute',
              left: `${cartX}%`,
              top: '74%',
              transform: `translate(-50%, -100%) rotate(${cartTip}deg)`,
              transformOrigin: '50% 100%',
            }}
          >
            <CartFigure height={340} />
          </div>

          {runnerVisible ? (
            <div
              style={{
                position: 'absolute',
                left: `${runX + runAfter}%`,
                top: '74%',
                transform: 'translate(-50%, -100%)',
              }}
            >
              <RunnerFigure height={450} />
            </div>
          ) : null}
        </CameraShake>
      </ChromaticSplit>

      <Bloom strength={0.34} radius={22}>
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-start', paddingTop: 260}}>
          <Caption
            text="SECURITY STOPS A SHOPLIFTER"
            startAt={B.security}
            exitAt={B.securityOut}
            tone="display"
            stagger={2}
          />
          <Caption
            text="HE BOLTS"
            startAt={B.bolts}
            exitAt={IMPACT - 6}
            tone="heavy"
            stagger={2}
            color={THEME.goldBright}
          />
          <Caption text="STRAIGHT INTO HER CART" startAt={B.cart} tone="display" stagger={2} />
          <Caption
            text="HER GRANDDAUGHTER WAS SITTING IN IT"
            startAt={B.granddaughter}
            tone="kicker"
            stagger={1}
            style={{fontSize: 38, marginTop: 30}}
          />
        </AbsoluteFill>
      </Bloom>

      {/* Surveillance framing holds until the hit, then the camera stops observing. */}
      <CCTVOverlay endAt={IMPACT} />

      <FlashCut at={IMPACT} frames={5} />
      <DustMotes seed="impact" opacity={0.32} />
      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
