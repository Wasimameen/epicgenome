/**
 * Beat 3 — warm, energetic. "Awesome Attorneys matches you directly with a
 * Phoenix injury attorney."
 *
 * The fastest camera flights in the spot (0.45s) and the airiest layout: this
 * is where the footage underneath does the cinematic lifting, so the overlay
 * keeps to one figure at a time.
 *
 * The beat leaves clean. Everything eases out over the last 0.25s so the final
 * frame of the segment is fully transparent before card #2 slams in — a hard
 * cut back to footage, no dissolve.
 */

import React from 'react';
import {interpolateColors, useVideoConfig} from 'remotion';
import {Posed} from '../stage/Word';
import {MatchLine} from '../parts/MatchLine';
import {Pin} from '../parts/Pin';
import {Chip} from '../parts/Chip';
import {Wordmark} from '../parts/Wordmark';
import {EASE, MaskReveal, useHit, useLocal, useRamp} from '../overlays/lib';
import {TYPE_BASE} from '../font';
import {BEATS, t} from '../timing/beats';
import {TRACKING, textShadow} from '../theme';
import type {BeatProps} from '../types';

export const Beat3: React.FC<BeatProps> = ({layout, type, palette, tone, poses}) => {
  const {fps} = useVideoConfig();
  const h = useHit(BEATS.b3.start);
  const local = useLocal(BEATS.b3.start);

  const end = local(BEATS.b3.end);
  const f = (n: number) => n / fps;

  /**
   * Everything is off two frames before the beat ends, so the segment's last
   * frames are genuinely transparent (spec §6) — a hard cut back to bare
   * footage before card #2 slams in, rather than a dissolve into it.
   */
  const clear = end - f(2);

  const pPhoenix = useRamp(h(t.phoenix) + 0.1, 0.5, EASE.expoOut);
  /** the pin and PHOENIX drift back to steel once the chip takes over */
  const toSteel = useRamp(h(t.injury) + 0.45, 0.6, EASE.smooth);
  const pinColor = interpolateColors(toSteel, [0, 1], [palette.gold, palette.steel]);
  const placeColor = interpolateColors(toSteel, [0, 1], [palette.white, palette.steel]);

  return (
    <>
      {/* the wordmark, with a light scan crossing it as it lands */}
      <Posed
        pose={poses.wordmark}
        enterAt={h(t.awesome)}
        enterDur={0.5}
        enterScaleFrom={0.94}
        exitAt={clear - 0.34}
        exitKind="lift"
        exitDur={0.34}
      >
        <Wordmark
          at={h(t.awesome)}
          scanAt={h(t.awesome) + 0.22}
          size={type.wordmark}
          white={palette.white}
          gold={palette.gold}
          tone={tone}
          stack={layout.wordmarkStack}
        />
      </Posed>

      {/* YOU <-> ATTORNEY */}
      <Posed
        pose={poses.match}
        enterAt={0.05}
        enterDur={0.5}
        enterScaleFrom={0.97}
        // demotes early and quickly: by the time the camera is on the pin this
        // figure has to read as depth, not as a half-legible word at the edge
        demoteAt={h(t.phoenix) - 0.15}
        demoteDur={0.35}
        exitAt={clear - 0.3}
        exitKind="recede"
        exitDur={0.3}
      >
        <MatchLine
          span={layout.match.span}
          height={layout.match.height}
          dotR={layout.match.dotR}
          stroke={layout.stroke}
          gold={palette.gold}
          steel={palette.steel}
          white={palette.white}
          tone={tone}
          labelSize={type.labelSmall}
          travelSize={type.travel}
          leftLabel="You"
          rightLabel="Attorney"
          travelLabel="Directly"
          times={{
            // the middlemen are there before the claim is made
            mid: 0.15,
            dots: h(t.matches),
            line: h(t.matches) + f(5),
            pulse: h(t.matches) + f(13),
            ring: h(t.matches) + f(18),
            directly: h(t.directly),
          }}
        />
      </Posed>

      {/* the pin and the place */}
      <Posed
        pose={poses.phoenix}
        enterAt={h(t.phoenix)}
        enterDur={0.5}
        enterScaleFrom={0.95}
        // No blur-demote here: "the pin and PHOENIX drift back to steel" is a
        // grade, not a defocus, and blurring it too left the whole beat soft.
        exitAt={clear - 0.26}
        exitKind="recede"
        exitDur={0.26}
      >
        <div style={{display: 'flex', alignItems: 'center', gap: layout.pinSize * 0.36}}>
          <Pin at={h(t.phoenix)} size={layout.pinSize} color={pinColor} tone={tone} />
          {/* reveals left-to-right, so the word grows out of the pin */}
          <MaskReveal progress={pPhoenix} direction="right" softness={10}>
            <div
              style={{
                ...TYPE_BASE,
                fontSize: type.place,
                fontWeight: 800,
                letterSpacing: TRACKING.hero,
                textTransform: 'uppercase',
                lineHeight: 1,
                color: placeColor,
                textShadow: textShadow(tone),
                transform: `translateX(${(1 - pPhoenix) * -22}px)`,
              }}
            >
              Phoenix
            </div>
          </MaskReveal>
        </div>
      </Posed>

      {/* the qualifier, under the ATTORNEY end of the line */}
      <Posed
        pose={poses.chip}
        enterAt={h(t.injury)}
        enterDur={0.45}
        enterScaleFrom={0.96}
        exitAt={clear - 0.22}
        exitKind="recede"
        exitDur={0.22}
      >
        <Chip
          at={h(t.injury)}
          text="Phoenix Injury Attorney"
          size={type.labelSmall}
          borderColor={palette.gold}
          textColor={palette.white}
          stroke={layout.stroke}
          tone={tone}
        />
      </Posed>
    </>
  );
};
