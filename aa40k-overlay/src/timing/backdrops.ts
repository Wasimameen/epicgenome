/**
 * The shot list for the moving background.
 *
 * Four photographic backdrops behind the footage beats, then the signature end
 * card. Like everything else in this piece the timings are derived from
 * `beats.ts` in seconds, so a new voice-over re-cuts the background with the
 * rest of the piece and nothing here needs editing.
 *
 * Two of the three transitions are deliberately hidden:
 *
 *  - `franklin` -> `court` cross-fades entirely *underneath* the opaque
 *    "NOT / A LEGAL FINDING" plate, so the Supreme Court is simply *there* when
 *    the card wipes away. A cut you never see is the most seamless kind.
 *  - `courtroom` -> end card is covered by the gold "GET MATCHED." slam.
 *
 * Only `eye` -> `franklin` is an exposed dissolve, and it sits in beat 1's
 * still hold where it becomes the event that keeps the hold alive rather than
 * competing with anything.
 */

import {t} from './beats';

/** Which photograph plays when. Roles are mapped to files in brand.generated. */
export type BackdropRole = 'adjuster' | 'silenced' | 'court' | 'counsel';

export type KenBurns = {
  /** scale at the start / end of the shot. Never below 1.10: the parallax and
   *  the frame punch both need headroom before an edge would show. */
  scaleFrom: number;
  scaleTo: number;
  /** drift across the shot, as a fraction of the frame's width / height */
  xFrom: number;
  xTo: number;
  yFrom: number;
  yTo: number;
};

export type Shot = {
  role: BackdropRole;
  /** seconds — when it starts fading up */
  in: number;
  /** seconds — when it has finished fading out */
  out: number;
  /** cross-fade length in seconds */
  fade: number;
  /** fade-up length; defaults to `fade`. The opening shot uses 0 — there is
   *  nothing behind it to dissolve from, and fading it up would leave the
   *  background still arriving when the first word lands at 0.55s. */
  fadeIn?: number;
  ken: KenBurns;
  /** what the frame is, for the report and for anyone re-cutting it */
  note: string;
};

const XFADE = 0.6;

export const SHOTS: Shot[] = [
  {
    role: 'adjuster',
    in: 0,
    out: t.thats + 0.1,
    fade: XFADE,
    fadeIn: 0,
    // pushes in and settles — the beat is heavy, so the move is the slowest
    ken: {scaleFrom: 1.28, scaleTo: 1.12, xFrom: 0.02, xTo: -0.01, yFrom: -0.02, yTo: 0.01},
    note: 'an eye through a torn banknote — the adjuster sizing you up through money',
  },
  {
    role: 'silenced',
    in: t.thats - 0.5,
    out: t.legal + 0.75,
    fade: XFADE,
    // pulls back the other way, so two shots running together never drift alike
    ken: {scaleFrom: 1.12, scaleTo: 1.26, xFrom: -0.02, xTo: 0.02, yFrom: 0.02, yTo: -0.02},
    note: 'Franklin gagged — what their "opening position" is really doing to you',
  },
  {
    role: 'court',
    in: t.legal + 0.25,
    out: t.matches + 0.45,
    fade: XFADE,
    ken: {scaleFrom: 1.26, scaleTo: 1.12, xFrom: 0.03, xTo: -0.02, yFrom: 0.01, yTo: -0.01},
    note: 'the Supreme Court — what an actual legal finding looks like',
  },
  {
    role: 'counsel',
    in: t.matches - 0.15,
    out: t.getMatched + 0.15,
    fade: XFADE,
    // drifts toward the standing attorney as the beat warms up
    ken: {scaleFrom: 1.12, scaleTo: 1.3, xFrom: -0.03, xTo: 0.02, yFrom: -0.01, yTo: 0.02},
    note: 'counsel on his feet in court — the attorney you get matched with',
  },
];

/** The signature end card takes over from the last "GET PAID." plate. */
export const END_CARD_AT = t.url - 0.1;
