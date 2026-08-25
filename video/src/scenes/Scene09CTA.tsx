import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Caption} from '../components/Caption';
import {FallingBills} from '../components/FallingBills';
import {DustMotes} from '../components/DustMotes';
import {Grain} from '../components/Grain';
import {LightRays} from '../components/LightRays';
import {Vignette} from '../components/Vignette';
import {THEME} from '../theme';

const Pill: React.FC<{text: string; startAt: number}> = ({text, startAt}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - startAt, fps, config: {damping: 12, mass: 0.6, stiffness: 150}});

  return (
    <div
      style={{
        opacity: s,
        transform: `scale(${0.82 + s * 0.18})`,
        border: `4px solid ${THEME.goldBright}`,
        borderRadius: 999,
        padding: '18px 46px',
        fontFamily: 'var(--display), sans-serif',
        fontSize: 56,
        color: THEME.goldBright,
        letterSpacing: '0.01em',
        whiteSpace: 'nowrap',
        boxShadow: `0 0 44px ${THEME.goldBright}33`,
      }}
    >
      {text}
    </div>
  );
};

/**
 * "That's what happens when the facts hold up. Awesome Attorneys matches you
 * directly with a Phoenix injury attorney. Get Matched. Get Paid.
 * AwesomeAttorneys dot com."
 *
 * NOTE: the brand lockup here is set in type. Drop a real Awesome Attorneys
 * logo into public/assets as `brand-logo.png` and it should replace this block.
 */
export const Scene09CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const urlPop = spring({frame: frame - 190, fps, config: {damping: 13, mass: 0.7}});
  const glow = interpolate(Math.sin(frame * 0.16), [-1, 1], [0.25, 0.6]);

  return (
    <AbsoluteFill style={{backgroundColor: '#07060a'}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 72% 46% at 50% 44%, #2c2210 0%, #06060a 76%)`,
        }}
      />
      <FallingBills count={16} seed="cta" intensity={0.5} />

      <AbsoluteFill
        style={{alignItems: 'center', justifyContent: 'center', gap: 30, padding: '0 70px'}}
      >
        <Caption
          text="THAT'S WHAT HAPPENS WHEN THE FACTS HOLD UP"
          startAt={2}
          exitAt={96}
          tone="display"
          stagger={2}
          style={{fontSize: 76, maxWidth: 900}}
        />
      </AbsoluteFill>

      <AbsoluteFill
        style={{alignItems: 'center', justifyContent: 'center', gap: 26, padding: '0 70px'}}
      >
        {frame >= 106 ? (
          <>
            <div
              style={{
                fontFamily: 'var(--display), sans-serif',
                fontSize: 104,
                lineHeight: 0.98,
                color: THEME.paper,
                textAlign: 'center',
                textShadow: `0 0 46px rgba(245,217,138,${glow})`,
                opacity: interpolate(frame, [106, 120], [0, 1], {extrapolateRight: 'clamp'}),
                transform: `translateY(${interpolate(frame, [106, 124], [30, 0], {
                  extrapolateRight: 'clamp',
                })}px)`,
              }}
            >
              AWESOME
              <br />
              ATTORNEYS
            </div>
            <Caption
              text="MATCHED DIRECTLY WITH A PHOENIX INJURY ATTORNEY"
              startAt={126}
              tone="kicker"
              stagger={1}
              style={{fontSize: 34, maxWidth: 820}}
            />
            <div style={{display: 'flex', gap: 22, marginTop: 16}}>
              <Pill text="GET MATCHED" startAt={168} />
              <Pill text="GET PAID" startAt={180} />
            </div>
            <div
              style={{
                marginTop: 34,
                fontFamily: 'var(--body), sans-serif',
                fontWeight: 700,
                fontSize: 56,
                letterSpacing: '0.01em',
                color: THEME.goldBright,
                opacity: urlPop,
                transform: `scale(${0.9 + urlPop * 0.1})`,
                textShadow: `0 0 40px ${THEME.goldBright}55`,
              }}
            >
              AwesomeAttorneys.com
            </div>
          </>
        ) : null}
      </AbsoluteFill>

      <LightRays opacity={0.18} />
      <DustMotes seed="cta" />
      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
