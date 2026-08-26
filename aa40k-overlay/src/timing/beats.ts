/**
 * The single source of truth for *when* things happen.
 *
 * Everything in the overlay is expressed in seconds and read from here.
 * No scene hard-codes a frame number, and no scene converts to frames itself —
 * that is `useSec()`'s job (src/overlays/lib.tsx), which reads fps from the
 * composition. Change `FPS` in Root.tsx and the whole piece re-times.
 *
 * Word timings come from `vo-words.json`. When that file carries a whisper
 * transcription (`source: "whisper"`, written by `npm run vo`) the sync points
 * are picked out of it by word. Otherwise the spec §4.2 fallback table is used
 * and `VO_SOURCE` reports `"fallback"` so the render report can say so.
 */

import voWords from './vo-words.json';

/** Every visual hit lands this many frames *before* the word is spoken. */
export const LEAD_FRAMES = 3;

export type SyncKey =
  | 'adjuster'
  | 'youre'
  | 'forty'
  | 'percent'
  | 'fault'
  | 'thats'
  | 'opening'
  | 'position'
  | 'not'
  | 'legal'
  | 'finding'
  | 'awesome'
  | 'matches'
  | 'directly'
  | 'phoenix'
  | 'injury'
  | 'attorney'
  | 'getMatched'
  | 'getPaid'
  | 'url'
  | 'end';

export type SyncPoints = Record<SyncKey, number>;

type VoWord = {word: string; start: number; end: number};

/* ------------------------------------------------------------------ *
 * Spec §4.2 fallback table (seconds)
 * ------------------------------------------------------------------ */

const FALLBACK: SyncPoints = {
  adjuster: 0.55,
  youre: 1.25,
  forty: 1.6,
  percent: 2.0,
  fault: 2.65,
  thats: 3.6,
  opening: 4.4,
  position: 4.9,
  not: 5.8,
  legal: 6.1,
  finding: 6.4,
  awesome: 7.4,
  matches: 8.5,
  directly: 9.2,
  phoenix: 10.2,
  injury: 10.7,
  attorney: 11.1,
  getMatched: 12.45,
  getPaid: 13.5,
  url: 14.6,
  end: 15.4,
};

/* ------------------------------------------------------------------ *
 * Deriving sync points from a transcription
 * ------------------------------------------------------------------ */

/** lower-case, strip everything that is not a letter or digit */
const norm = (s: string): string => s.toLowerCase().replace(/[^a-z0-9]/g, '');

type Pick = {match: (w: string) => boolean; take?: 'first' | 'last'};

const exact =
  (target: string) =>
  (w: string): boolean =>
    w === target;

const PICKS: Record<Exclude<SyncKey, 'end'>, Pick> = {
  adjuster: {match: exact('adjuster')},
  // "told you you're" — matching `youre` exactly skips the bare "you"
  youre: {match: exact('youre')},
  forty: {match: (w) => w === 'forty' || w === '40'},
  percent: {match: (w) => w === 'percent' || w === '40percent'},
  fault: {match: exact('fault')},
  thats: {match: exact('thats')},
  opening: {match: exact('opening')},
  position: {match: exact('position')},
  not: {match: exact('not')},
  legal: {match: exact('legal')},
  finding: {match: (w) => w === 'finding' || w === 'findings'},
  awesome: {match: (w) => w.startsWith('awesome'), take: 'first'},
  matches: {match: (w) => w === 'matches' || w === 'match'},
  directly: {match: exact('directly')},
  phoenix: {match: exact('phoenix')},
  injury: {match: exact('injury')},
  attorney: {match: exact('attorney')},
  getMatched: {match: exact('matched')},
  getPaid: {match: exact('paid')},
  // the URL read — the *last* "Awesome…" in the script
  url: {match: (w) => w.startsWith('awesome'), take: 'last'},
};

const fromWords = (words: VoWord[]): SyncPoints | null => {
  const normed = words.map((w) => ({...w, n: norm(w.word)})).filter((w) => w.n.length > 0);
  if (normed.length === 0) return null;

  const out = {} as SyncPoints;
  for (const key of Object.keys(PICKS) as (keyof typeof PICKS)[]) {
    const {match, take = 'first'} = PICKS[key];
    const hits = normed.filter((w) => match(w.n));
    if (hits.length === 0) return null; // incomplete transcription -> fall back wholesale
    const hit = take === 'last' ? hits[hits.length - 1] : hits[0];
    out[key] = hit.start;
  }
  out.end = normed[normed.length - 1].end;
  return out;
};

/* ------------------------------------------------------------------ *
 * Resolved timing
 * ------------------------------------------------------------------ */

const parsed = (voWords as {source?: string; words?: VoWord[]}).source === 'whisper'
  ? fromWords(((voWords as {words?: VoWord[]}).words ?? []) as VoWord[])
  : null;

export const VO_SOURCE: 'whisper' | 'fallback' = parsed ? 'whisper' : 'fallback';

/** Sync points, in seconds from the first frame of the voice-over. */
export const t: SyncPoints = parsed ?? FALLBACK;

/** End-card hold after the last spoken word. */
export const END_HOLD_SEC = 2.6;

/** Total length of the overlay. Frame 0 == the first frame of the VO. */
export const TOTAL_SEC = t.end + END_HOLD_SEC;

/* ------------------------------------------------------------------ *
 * Beat windows — contiguous, so nothing ever falls into a gap
 * ------------------------------------------------------------------ */

export type Window = {start: number; end: number; duration: number};

const win = (start: number, end: number): Window => ({
  start,
  end,
  duration: end - start,
});

export const BEATS = {
  /** deflated */
  b1: win(0, t.thats - 0.2),
  /** knowing */
  b2: win(t.thats - 0.2, t.awesome - 0.2),
  /** warm, energetic */
  b3: win(t.awesome - 0.2, t.getMatched - 0.45),
  /** decisive + end card */
  b4: win(t.getMatched - 0.45, TOTAL_SEC),
} as const;

/** The three windows where the overlay cuts to an opaque plate. */
export const CARD_WINDOWS = {
  /** "NOT / A LEGAL FINDING" */
  not: win(t.not, BEATS.b2.end),
  /** "GET MATCHED." -> "GET PAID." -> end card: one continuous plate run */
  close: win(t.getMatched, TOTAL_SEC),
} as const;

/* ------------------------------------------------------------------ *
 * Sync sheet data
 * ------------------------------------------------------------------ */

export const KEY_WORDS: {key: SyncKey; spoken: string; beat: string}[] = [
  {key: 'adjuster', spoken: 'adjuster', beat: '1'},
  {key: 'youre', spoken: "you're", beat: '1'},
  {key: 'forty', spoken: 'forty', beat: '1'},
  {key: 'percent', spoken: 'percent', beat: '1'},
  {key: 'fault', spoken: 'fault', beat: '1'},
  {key: 'thats', spoken: "that's", beat: '2'},
  {key: 'opening', spoken: 'opening', beat: '2'},
  {key: 'position', spoken: 'position', beat: '2'},
  {key: 'not', spoken: 'not', beat: '2'},
  {key: 'legal', spoken: 'legal', beat: '2'},
  {key: 'finding', spoken: 'finding', beat: '2'},
  {key: 'awesome', spoken: 'Awesome (Attorneys)', beat: '3'},
  {key: 'matches', spoken: 'matches', beat: '3'},
  {key: 'directly', spoken: 'directly', beat: '3'},
  {key: 'phoenix', spoken: 'Phoenix', beat: '3'},
  {key: 'injury', spoken: 'injury', beat: '3'},
  {key: 'attorney', spoken: 'attorney', beat: '3'},
  {key: 'getMatched', spoken: 'Matched (Get Matched.)', beat: '4'},
  {key: 'getPaid', spoken: 'Paid (Get Paid.)', beat: '4'},
  {key: 'url', spoken: 'AwesomeAttorneys dot com', beat: '4'},
  {key: 'end', spoken: '— end of VO, card holds —', beat: 'end'},
];
