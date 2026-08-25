import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {CameraShake} from '../components/CameraShake';
import {ChromaticSplit} from '../components/ChromaticSplit';
import {DustMotes} from '../components/DustMotes';
import {Caption} from '../components/Caption';
import {CartFigure} from '../components/CartFigure';
import {FlashCut} from '../components/FlashCut';
import {Grain} from '../components/Grain';
import {GrandmaFigure} from '../components/GrandmaFigure';
import {Vignette} from '../components/Vignette';
import {useTransparent} from '../alpha';
import {cue} from '../timeline';
import {THEME} from '../theme';

/**
 * Cues from the voiceover transcript:
 *   "The little girl was completely fine,"        19.32 - 20.46
 *   "but grandma went down hard"                  21.44 - 22.76
 *   "and the cart came down right on top of her." 23.10 - 25.56
 *
 * The two falls are deliberately separated — the script lands them as separate
 * events, and dropping both at once wastes the second half of the line.
 */
const LANDING = cue('down', 22.6); // "down hard"
const CART_LAND = cue('down', 25.2); // "on top of her"
const B = {
  girl: cue('down', 19.32) + 1,
  girlOut: cue('down', 21.1),
  grandmaFrom: cue('down', 21.44),
  cartFrom: cue('down', 23.1),
};

/**
 * "The little girl was completely fine — but grandma went down hard, and the
 * cart came down right on top of her."
 *
 * Relief first, in green, then the fall. The tonal switch is the point of the
 * beat, so the two halves never share the screen.
 */
export const Scene04Down: React.FC = () => {
  const alpha = useTransparent();
  const frame = useCurrentFrame();

  // Grandmother rotates to the floor with gravity easing, not a linear tip.
  const fall = interpolate(frame, [B.grandmaFrom, LANDING], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.quad),
  });
  const cartFall = interpolate(frame, [B.cartFrom, CART_LAND], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic),
  });

  const redWash = interpolate(frame, [LANDING - 4, LANDING + 20], [0, 0.2], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: alpha ? 'transparent' : '#09080b'}}>
      <ChromaticSplit impactAt={LANDING} maxOffset={24}>
      <CameraShake impactAt={LANDING} intensity={40} decay={26}>
        <AbsoluteFill
          style={{
            background: alpha ? 'none' : 'radial-gradient(ellipse 68% 40% at 50% 62%, #1b1520 0%, #08070a 74%)',
          }}
        />
        <AbsoluteFill
          style={{
            background: 'radial-gradient(ellipse 60% 30% at 50% 72%, #b3202a 0%, transparent 70%)',
            opacity: redWash,
            mixBlendMode: 'screen',
          }}
        />

        <div
          style={{
            position: 'absolute',
            left: '38%',
            top: '72%',
            transform: `translate(-50%, -100%) rotate(${fall * 80}deg) translateY(${fall * 18}px)`,
            transformOrigin: '50% 100%',
          }}
        >
          <GrandmaFigure height={520} />
        </div>

        <div
          style={{
            position: 'absolute',
            left: '60%',
            top: '72%',
            transform: `translate(-50%, -100%) rotate(${cartFall * 96}deg) translateY(${
              cartFall * 30
            }px)`,
            transformOrigin: '50% 100%',
          }}
        >
          <CartFigure height={340} />
        </div>
      </CameraShake>
      </ChromaticSplit>

      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-start', paddingTop: 250}}>
        <Caption
          text="THE LITTLE GIRL WAS FINE"
          startAt={2}
          exitAt={52}
          tone="display"
          stagger={2}
          color="#7fd8a4"
        />
        <Caption
          text="GRANDMA WENT DOWN HARD"
          startAt={LANDING - 2}
          tone="heavy"
          stagger={2}
        />
        <Caption
          text="THE CART CAME DOWN ON TOP OF HER"
          startAt={B.cartFrom + 6}
          tone="kicker"
          stagger={1}
          style={{fontSize: 38, marginTop: 28}}
        />
      </AbsoluteFill>

      <FlashCut at={LANDING} frames={4} color="#ffd9d9" />
      <FlashCut at={CART_LAND} frames={3} color="#ffd9d9" />
      <DustMotes count={20} seed="down" opacity={0.28} />
      <DustMotes seed="down" opacity={0.4} />
      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
