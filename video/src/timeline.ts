/**
 * Beat map derived from the actual voiceover, not estimated.
 *
 * Scene boundaries and every in-scene cue below were taken from word-level
 * timestamps of public/audio/vo.mp3 (62.04s). `at()` converts a VO timestamp in
 * seconds to a frame, so cues stay readable against the script.
 *
 * If the voiceover is ever re-recorded, re-derive these numbers rather than
 * nudging them by eye — the whole reel hangs off this table.
 */
export const FPS = 30;

/** Seconds in the voiceover -> absolute frame in the reel. */
export const at = (seconds: number) => Math.round(seconds * FPS);

type Scene = {
  id: string;
  /** VO timestamp this scene cuts in on. */
  startSec: number;
  frames: number;
  line: string;
};

const BOUNDS = [0, 6.1, 10.12, 19.32, 26.26, 31.96, 40.7, 44.04, 52.32, 62.5];

const LINES = [
  ['hook', 'Nearly seventeen million dollars… because a grandmother went shopping at Walmart.'],
  ['crazier', 'And honestly — how it happened is even crazier than the number.'],
  ['impact', 'So security tries to stop a shoplifter — the guy BOLTS — runs straight into her shopping cart — and her granddaughter is sitting in that cart.'],
  ['down', 'The little girl was completely fine — but grandma went down hard, and the cart came down right on top of her.'],
  ['surgeries', "She needed multiple surgeries. She's been in the hospital more than twenty times."],
  ['court', "So she takes Walmart to court — and she WINS — but Walmart isn't done — they appeal it all the way to the state Supreme Court —"],
  ['online', 'and now every single dollar is on the line.'],
  ['verdict', 'The court said… the verdict stands. All of it — nearly seventeen million dollars — upheld by the highest court in the state.'],
  ['cta', "That's what happens when the facts hold up. Awesome Attorneys matches you directly with a Phoenix injury attorney. Get Matched. Get Paid. AwesomeAttorneys dot com."],
] as const;

export const SCENES: Scene[] = LINES.map(([id, line], i) => ({
  id,
  line,
  startSec: BOUNDS[i],
  frames: at(BOUNDS[i + 1]) - at(BOUNDS[i]),
}));

export const SCENE_START: Record<string, number> = Object.fromEntries(
  SCENES.map((s) => [s.id, at(s.startSec)]),
);

/**
 * Turns an absolute VO timestamp into a frame local to the given scene, so a cue
 * can be written as the moment a word is actually spoken.
 */
export const cue = (sceneId: string, seconds: number) => at(seconds) - SCENE_START[sceneId];

export const TOTAL_FRAMES = at(BOUNDS[BOUNDS.length - 1]);
