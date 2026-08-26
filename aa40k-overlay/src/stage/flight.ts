/**
 * One world, one camera.
 *
 * Every word's place in 3D and every leg of the camera's flight is declared
 * here, so a word and the camera can never disagree about where the word is.
 * The beats import `posesFor()` and render type at those poses; the `<Camera3D>`
 * at the top of the overlay imports `flightFor()` and flies between the same
 * ones.
 *
 * Positions are authored as the screen offset (px from frame centre) a word
 * holds when the camera is resting on it — `poseFromScreen()` inverts the
 * projection — which is what makes the safe zones in §5 checkable numbers
 * rather than guesses.
 *
 * 9x16 stacks: the frame is tall, so beats read top-to-bottom.
 * 16x9 spreads: the frame is wide and short, so the same beats read
 * left-to-right. Same components, same timing — only the layout tokens differ.
 */

import {LEAD_FRAMES, BEATS, t} from '../timing/beats';
import {EASE} from '../overlays/lib';
import {poseFromScreen, type CameraDrift, type CameraKey, type Pose} from './Camera3D';
import {STRIKE_DUR} from '../parts/Strike';
import type {Aspect, Layout} from '../theme';

/** Lead, in seconds, for a given fps. Every hit lands here. */
export const leadSec = (fps: number): number => LEAD_FRAMES / fps;

/** The frame a spoken word's visual actually lands on. */
export const hit = (spokenSec: number, fps: number): number =>
  spokenSec - leadSec(fps);

/* ------------------------------------------------------------------ *
 * Screen positions
 * ------------------------------------------------------------------ */

type Spot = {sx: number; sy: number; z?: number; rx?: number; ry?: number; rz?: number};

export type PoseName =
  | 'adjuster'
  | 'youre'
  | 'forty'
  | 'opening'
  | 'wordmark'
  | 'match'
  | 'matchClose'
  | 'phoenix'
  | 'chip'
  | 'neutral';

const SPOTS: Record<Aspect, Record<PoseName, Spot>> = {
  '9x16': {
    adjuster: {sx: -215, sy: 305, z: -120, rx: 6, ry: 14, rz: -3},
    youre: {sx: 205, sy: -70, z: 60, rx: -4, ry: -18, rz: 2},
    // `sy` sits high on purpose. The camera only travels `camFollowXY` (55%) of
    // a word's offset, so an *un-focused* word's screen offset works out at
    // (sy - 0.55*focusSy)/0.45 — an amplification of ~2.2x. At sy:60 that put
    // the retiring stamp 184px below the bottom safe line during "opening".
    forty: {sx: 0, sy: -170, z: 0, rz: -6},
    opening: {sx: 0, sy: -400, z: 90, rx: 14},
    wordmark: {sx: 0, sy: -430, z: 40, rx: 6},
    match: {sx: 0, sy: 40, z: 0},
    matchClose: {sx: 0, sy: 40, z: 90},
    phoenix: {sx: -40, sy: 330, z: 20, ry: 12},
    chip: {sx: 140, sy: 195, z: -30, ry: 8},
    neutral: {sx: 0, sy: 0, z: 0},
  },
  '16x9': {
    adjuster: {sx: -520, sy: 210, z: -120, rx: 6, ry: 14, rz: -3},
    youre: {sx: 430, sy: -110, z: 60, rx: -4, ry: -18, rz: 2},
    forty: {sx: 250, sy: -10, z: 0, rz: -6},
    opening: {sx: -520, sy: -60, z: 90, rx: 14},
    wordmark: {sx: 0, sy: -250, z: 40, rx: 6},
    match: {sx: 0, sy: 30, z: 0},
    matchClose: {sx: 0, sy: 30, z: 90},
    // Kept closer together than the frame width would suggest: the camera only
    // travels `camFollowXY` of a word's offset, so a wide separation here threw
    // the previous subject clean off the side of a 16x9 frame.
    phoenix: {sx: -200, sy: 250, z: 20, ry: 12},
    chip: {sx: 140, sy: 230, z: -30, ry: 8},
    neutral: {sx: 0, sy: 0, z: 0},
  },
};

export type Poses = Record<PoseName, Pose>;

export const posesFor = (l: Layout): Poses => {
  const spots = SPOTS[l.aspect];
  const out = {} as Poses;
  (Object.keys(spots) as PoseName[]).forEach((k) => {
    out[k] = poseFromScreen(spots[k], l);
  });
  return out;
};

/** The screen offset a pose was authored at — used by the safe-zone report. */
export const spotsFor = (aspect: Aspect): Record<PoseName, Spot> => SPOTS[aspect];

/* ------------------------------------------------------------------ *
 * The flight plan
 * ------------------------------------------------------------------ */

/**
 * How much of a flight happens *before* its cue.
 *
 * A flight that only starts when the word appears leaves the word sliding into
 * place for another half second — it never lands on the frame it is spoken on.
 * Starting half a flight early means the camera is at its fastest exactly on the
 * cue (expo-in-out peaks in the middle, so the blur peaks there too) and has
 * settled about six frames later. The word arrives with the whip, not after it.
 */
const PREROLL = 0.5;

const leg = (cue: number, pose: Pose, flight: number): CameraKey => ({
  at: cue - flight * PREROLL,
  pose,
  flight,
});

export const flightFor = (l: Layout, fps: number): CameraKey[] => {
  const p = posesFor(l);
  const h = (s: number) => hit(s, fps);
  return [
    // beat 1 — heavy, few moves
    {at: 0, pose: p.adjuster, flight: 0},
    leg(h(t.youre), p.youre, 0.5),
    leg(h(t.forty), p.forty, 0.42),
    // beat 2 — the turn
    leg(h(t.opening), p.opening, 0.55),
    // beat 3 — the fastest flights in the spot
    leg(h(t.awesome), p.wordmark, 0.45),
    leg(h(t.matches), p.match, 0.45),
    leg(h(t.directly), p.matchClose, 0.5),
    leg(h(t.phoenix), p.phoenix, 0.45),
    leg(h(t.injury), p.chip, 0.45),
    // beat 4 — cards take over; settle the world back to neutral underneath
    leg(h(t.getMatched), p.neutral, 0.4),
  ];
};

/* ------------------------------------------------------------------ *
 * Drifts — the slow, continuous part of the camera
 * ------------------------------------------------------------------ */

export const driftsFor = (fps: number): CameraDrift[] => {
  const h = (s: number) => hit(s, fps);
  return [
    // beat 1: the frame sinks and eases off the subject. Slowest move in the
    // piece — about 0.4 px/frame — so the whole beat feels heavy.
    {
      start: 0,
      end: BEATS.b1.end,
      from: {y: 22, scale: 1.03},
      to: {y: -22, scale: 1},
    },
    // beat 2: the camera reverses into a slow push-in on "that's".
    {
      start: h(t.thats),
      end: h(t.opening),
      from: {y: 0, scale: 1},
      to: {y: 12, scale: 1.05},
    },
    // beat 3: airy — barely there, just enough that nothing is truly frozen.
    {
      start: BEATS.b3.start,
      end: BEATS.b3.end,
      from: {y: 6, scale: 1},
      to: {y: -6, scale: 1.015},
    },
  ];
};

/* ------------------------------------------------------------------ *
 * Frame punches
 * ------------------------------------------------------------------ */

export type Punch = {at: number; amount: number};

export const punchesFor = (fps: number): Punch[] => {
  const h = (s: number) => hit(s, fps);
  return [
    {at: h(t.forty), amount: 0.02}, // the 40% slam
    {at: h(t.getMatched), amount: 0.02}, // card #2
    {at: h(t.getPaid), amount: 0.02}, // card #3
    {at: BEATS.b3.end - 0.1, amount: 0.03}, // hard cut out of beat 3
  ];
};

/* ------------------------------------------------------------------ *
 * Motion-blur hints
 * ------------------------------------------------------------------ */

const ramp = (sec: number, at: number, dur: number, ease: (n: number) => number): number =>
  ease(Math.min(1, Math.max(0, (sec - at) / dur)));

const speedOf = (
  sec: number,
  fps: number,
  at: number,
  dur: number,
  ease: (n: number) => number,
  distance: number,
): number => {
  const d = 1 / fps;
  return Math.abs(ramp(sec, at, dur, ease) - ramp(sec - d, at, dur, ease)) * distance;
};

/** When the "40%" group is struck through and falls out of the world. */
export const TUMBLE_AT = (fps: number): number => hit(t.opening, fps) + 0.5;
export const TUMBLE_DUR = 0.6;
export const STRIKE_AT = (fps: number): number => hit(t.opening, fps) + 0.12;

/**
 * px/frame contributed by elements that move on their own inside the 3D stage.
 * Fed to `<Camera3D speedHint>` so a fast element is blurred even when the
 * camera itself is holding still — the 40px/frame rule in §2.8 applies to
 * everything, not just camera moves.
 */
export const hintSpeed = (sec: number, fps: number, l: Layout): number => {
  const h = (s: number) => hit(s, fps);
  const wide = l.aspect === '9x16' ? 1 : 1.4;
  return Math.max(
    // the "40%" arriving from translateZ +260 — the perspective scale change
    // sweeps the outer glyphs several hundred px in well under half a second
    speedOf(sec, fps, h(t.forty), 0.5, EASE.expoOut, 320),
    // the gold strike sweeping through "40% AT FAULT"
    speedOf(sec, fps, STRIKE_AT(fps), STRIKE_DUR, EASE.expoOut, 820 * wide),
    // the "40%" group tumbling away
    speedOf(sec, fps, TUMBLE_AT(fps), TUMBLE_DUR, EASE.expoIn, 760),
    // the match line drawing, its pulse, and DIRECTLY travelling it
    speedOf(sec, fps, h(t.matches) + 0.18, 0.5, EASE.expoOut, 700 * wide),
    speedOf(sec, fps, h(t.directly), 0.55, EASE.expoOut, 700 * wide),
    // the pin dropping
    speedOf(sec, fps, h(t.phoenix), 0.42, EASE.expoIn, 210),
  );
};
