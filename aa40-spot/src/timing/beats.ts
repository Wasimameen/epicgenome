/* ------------------------------------------------------------------ *
 * beats.ts — the single source of truth for WHEN anything happens.
 *
 * Every sync point is looked up by word from the Whisper transcript in
 * `vo-words.json`. No scene hard-codes a frame number; nothing here is
 * fps-dependent (everything is seconds).
 *
 * Drop in a new `public/vo.mp3`, run
 *     node scripts/transcribe.mjs
 * and the whole spot re-times itself.
 * ------------------------------------------------------------------ */

import voWords from './vo-words.json';

/** Visual and sound hits land this many frames BEFORE their word. */
export const LEAD = 3;

/** Still end-card hold after the last spoken word. */
export const END_HOLD = 2.6;

export type SyncKey =
	// spec-mandated sync points
	| 'forty'
	| 'percent'
	| 'fault'
	| 'opening'
	| 'position'
	| 'not'
	| 'finding'
	| 'awesome'
	| 'matches'
	| 'directly'
	| 'phoenix'
	| 'attorney'
	| 'getMatched'
	| 'getPaid'
	| 'url'
	| 'end'
	// derived points the scenes need
	| 'line1'
	| 'line2'
	| 'attorneys'
	| 'injury'
	| 'matched'
	| 'paid';

export type Beats = Record<SyncKey, number>;

/* ------------------------------------------------------------------ *
 * Fallback table (30 fps reference, §4 of the brief).
 * Used wholesale when there is no usable transcript, and as the
 * parameterisation for interpolating any single word Whisper missed.
 * ------------------------------------------------------------------ */

const FALLBACK: Beats = {
	line1: 0.0,
	forty: 1.6,
	percent: 2.0,
	fault: 2.65,
	line2: 3.6,
	opening: 4.4,
	position: 4.9,
	not: 5.8,
	finding: 6.4,
	awesome: 7.4,
	attorneys: 7.95,
	matches: 8.5,
	directly: 9.2,
	phoenix: 10.2,
	injury: 10.7,
	attorney: 11.1,
	getMatched: 12.0,
	matched: 12.45,
	getPaid: 13.05,
	paid: 13.5,
	url: 14.6,
	end: 15.4,
};

/* ------------------------------------------------------------------ *
 * Word matching
 *
 * The anchors are walked in script order, so a repeated word ("get"
 * twice, "attorney"/"attorneys", "awesome" in beat 3 and beat 4) can
 * never bind to the wrong occurrence.
 * ------------------------------------------------------------------ */

type Anchor = {key: SyncKey; candidates: string[]};

const ANCHORS: Anchor[] = [
	{key: 'line1', candidates: ['so', 'an', 'adjuster']},
	{key: 'forty', candidates: ['forty', '40', '40%', 'fourty']},
	{key: 'percent', candidates: ['percent', '%', 'percentage']},
	{key: 'fault', candidates: ['fault']},
	{key: 'line2', candidates: ["that's", 'thats', 'that']},
	{key: 'opening', candidates: ['opening']},
	{key: 'position', candidates: ['position']},
	{key: 'not', candidates: ['not']},
	{key: 'finding', candidates: ['finding', 'findings']},
	{key: 'awesome', candidates: ['awesome', 'awesomeattorneys']},
	{key: 'attorneys', candidates: ['attorneys', 'attorney']},
	{key: 'matches', candidates: ['matches', 'match']},
	{key: 'directly', candidates: ['directly', 'direct']},
	{key: 'phoenix', candidates: ['phoenix']},
	{key: 'injury', candidates: ['injury']},
	{key: 'attorney', candidates: ['attorney', 'attorneys']},
	{key: 'getMatched', candidates: ['get']},
	{key: 'matched', candidates: ['matched']},
	{key: 'getPaid', candidates: ['get']},
	{key: 'paid', candidates: ['paid']},
	{key: 'url', candidates: ['awesomeattorneys', 'awesome']},
];

const norm = (s: string) =>
	s
		.toLowerCase()
		.replace(/[‘’]/g, "'")
		.replace(/[^a-z0-9'%]/g, '');

type RawWord = {word: string; startMs: number; endMs: number};

type Resolution = {
	beats: Beats;
	source: 'whisper' | 'fallback';
	matched: SyncKey[];
	missed: SyncKey[];
	transcript: string;
	words: {word: string; start: number; end: number}[];
};

const resolve = (): Resolution => {
	const raw = voWords as unknown as {
		source?: string;
		text?: string;
		words?: RawWord[];
	};

	const words = (raw.words ?? [])
		.filter((w) => norm(w.word).length > 0)
		.map((w) => ({
			word: w.word,
			n: norm(w.word),
			start: w.startMs / 1000,
			end: w.endMs / 1000,
		}));

	const emptyResult: Resolution = {
		beats: {...FALLBACK},
		source: 'fallback',
		matched: [],
		missed: ANCHORS.map((a) => a.key).concat('end'),
		transcript: raw.text ?? '',
		words: [],
	};

	if (raw.source !== 'whisper' || words.length < 12) {
		return emptyResult;
	}

	const hit: Partial<Beats> = {};
	const matched: SyncKey[] = [];
	const missed: SyncKey[] = [];
	const hitIndex: Partial<Record<SyncKey, number>> = {};

	let cursor = 0;
	for (const anchor of ANCHORS) {
		let found = -1;
		for (let i = cursor; i < words.length; i++) {
			const w = words[i].n;
			if (
				anchor.candidates.some(
					(c) => w === c || (c.length >= 4 && (w.startsWith(c) || c.startsWith(w))),
				)
			) {
				found = i;
				break;
			}
		}
		if (found === -1) {
			missed.push(anchor.key);
			continue;
		}
		hit[anchor.key] = words[found].start;
		hitIndex[anchor.key] = found;
		matched.push(anchor.key);
		cursor = found + 1;
	}

	// Whisper writes "forty percent" as the single token "40%", so the
	// `percent` anchor has nothing of its own to bind to. Split the token:
	// "forty" and "percent" are near-equal syllable-weight, and the "%"
	// glyph reads a beat later than the number in this read.
	if (hit.percent === undefined && hitIndex.forty !== undefined) {
		const w = words[hitIndex.forty];
		if (/%|percent/i.test(w.word)) {
			hit.percent = w.start + 0.54 * (w.end - w.start);
			matched.push('percent');
			const i = missed.indexOf('percent');
			if (i !== -1) missed.splice(i, 1);
		}
	}

	// The spot ends when the last spoken word ends.
	hit.end = words[words.length - 1].end;
	matched.push('end');

	// Too little signal to trust — fall back wholesale rather than mix.
	if (matched.length < ANCHORS.length * 0.8) {
		return {...emptyResult, missed: ANCHORS.map((a) => a.key)};
	}

	// Fill any single missed anchor by interpolating between its matched
	// neighbours, parameterised by the fallback spacing. Keeps monotonicity.
	const order: SyncKey[] = ANCHORS.map((a) => a.key).concat('end');
	for (let i = 0; i < order.length; i++) {
		const key = order[i];
		if (hit[key] !== undefined) continue;
		let lo = i - 1;
		while (lo >= 0 && hit[order[lo]] === undefined) lo--;
		let hiIdx = i + 1;
		while (hiIdx < order.length && hit[order[hiIdx]] === undefined) hiIdx++;

		if (lo < 0) {
			hit[key] = 0;
			continue;
		}
		if (hiIdx >= order.length) {
			hit[key] = (hit[order[lo]] as number) + 0.3;
			continue;
		}
		const loKey = order[lo];
		const hiKey = order[hiIdx];
		const fSpan = FALLBACK[hiKey] - FALLBACK[loKey];
		const p = fSpan === 0 ? 0.5 : (FALLBACK[key] - FALLBACK[loKey]) / fSpan;
		hit[key] =
			(hit[loKey] as number) +
			p * ((hit[hiKey] as number) - (hit[loKey] as number));
	}

	// Line 1 always begins at t=0 for the composition.
	hit.line1 = 0;

	// Enforce strict monotonicity — a DTW hiccup must never invert an order.
	let prev = -1;
	for (const key of order) {
		const v = hit[key] as number;
		hit[key] = v <= prev ? prev + 0.02 : v;
		prev = hit[key] as number;
	}

	return {
		beats: hit as Beats,
		source: 'whisper',
		matched,
		missed,
		transcript: raw.text ?? '',
		words: words.map((w) => ({word: w.word, start: w.start, end: w.end})),
	};
};

const resolved = resolve();

/** Sync points, in seconds. */
export const t: Beats = resolved.beats;

export const timingSource = resolved.source;
export const timingMatched = resolved.matched;
export const timingMissed = resolved.missed;
export const transcript = resolved.transcript;
export const words = resolved.words;

/** Total spot length in seconds: last word + the end-card hold. */
export const TOTAL_SEC = t.end + END_HOLD;

/** Duration in frames for a given fps. */
export const totalFrames = (fps: number) => Math.round(TOTAL_SEC * fps);

/** Length of the warm light sweep that reveals beat 3. */
export const SWEEP_SEC = 0.42;

/**
 * Beat windows, in seconds, for a given fps.
 *
 * Scene changes are keyed to the *visual hit* (word − LEAD), not to the
 * word, so a beat is always mounted before the first thing it has to
 * draw. The beat 2 → 3 change is a light-sweep reveal, so beat 3 mounts
 * behind the still-visible cold scene; the beat 3 → 4 change is a hard
 * cut, so the two never overlap.
 *
 * Beats 1 and 2 share one <Sequence>: beat 2 transforms beat 1's scene
 * in place rather than replacing it.
 */
export const beatWindows = (fps: number) => {
	const lead = LEAD / fps;
	const sweepEnd = t.awesome - lead; // warm scene fully revealed
	const sweepStart = sweepEnd - SWEEP_SEC;
	const cut34 = t.getMatched - lead; // hard cut into the CTA

	return {
		lead,
		one: {start: 0, end: t.line2},
		two: {start: t.line2, end: sweepEnd},
		three: {start: sweepStart - 0.12, end: cut34},
		four: {start: cut34, end: TOTAL_SEC},
		/** Beats 1+2 — one continuous scene, wiped away by the sweep. */
		cold: {start: 0, end: sweepEnd + 0.08},
		sweep: {start: sweepStart, end: sweepEnd},
	};
};

/** 30 fps convenience view, for scripts and docs. */
export const BEAT = beatWindows(30);

if (typeof console !== 'undefined' && resolved.source === 'fallback') {
	// eslint-disable-next-line no-console
	console.warn(
		'[beats] No usable Whisper transcript — using the §4 fallback timing table. ' +
			'Run `node scripts/transcribe.mjs` after placing public/vo.mp3.',
	);
}
