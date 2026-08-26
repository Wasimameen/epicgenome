import {Easing, staticFile} from 'remotion';
import {loadFont} from '@remotion/fonts';

/* ------------------------------------------------------------------ *
 * Fonts — Bebas Neue for the stamp, Sora for everything else. Never
 * system fonts.
 *
 * The files are served from public/fonts rather than fetched from
 * fonts.gstatic.com at render time: a broadcast render must not depend
 * on the network, and a proxied CI box will not have the certificate
 * chain Google Fonts needs. `scripts/fetch-fonts.mjs` refreshes them.
 *
 * Loaded at module scope, so Remotion blocks the render until the
 * faces are ready and measureText() is accurate.
 * ------------------------------------------------------------------ */

const SORA_FAMILY = 'Sora';
const BEBAS_FAMILY = 'Bebas Neue';

const fontsReady = Promise.all([
	loadFont({
		family: BEBAS_FAMILY,
		url: staticFile('fonts/BebasNeue-400.woff2'),
		format: 'woff2',
		weight: '400',
		display: 'block',
	}),
	// Sora ships as one variable file covering 100–800.
	loadFont({
		family: SORA_FAMILY,
		url: staticFile('fonts/Sora-variable.woff2'),
		format: 'woff2',
		weight: '100 800',
		display: 'block',
	}),
]);

export const FONT = {
	stamp: `"${BEBAS_FAMILY}", "Oswald", "Impact", sans-serif`,
	brand: `"${SORA_FAMILY}", "Inter", "Helvetica Neue", Arial, sans-serif`,
} as const;

export const waitForFonts = () => fontsReady;

/* ------------------------------------------------------------------ *
 * Palette
 * ------------------------------------------------------------------ */

export type Brand = {
	navy: string;
	gold: string;
	font?: string;
};

export const BASE_PALETTE = {
	ink: '#0B1220',
	slate: '#1E2A3A',
	steel: '#6B7A90',
	stampRed: '#C8372D',
	navy: '#0F2A4A',
	gold: '#E4B85A',
	coral: '#F26B4E',
	sand: '#F5E6C8',
	white: '#FFFFFF',
} as const;

export type Palette = {[K in keyof typeof BASE_PALETTE]: string};

/** `brand.json` may override navy + gold; everything else is fixed. */
export const makePalette = (brand?: Brand | null): Palette => ({
	...BASE_PALETTE,
	...(brand?.navy ? {navy: brand.navy} : {}),
	...(brand?.gold ? {gold: brand.gold} : {}),
});

/** #RRGGBB -> rgba() with alpha. */
export const rgba = (hex: string, alpha: number) => {
	const h = hex.replace('#', '');
	const full =
		h.length === 3
			? h
					.split('')
					.map((c) => c + c)
					.join('')
			: h;
	const r = parseInt(full.slice(0, 2), 16);
	const g = parseInt(full.slice(2, 4), 16);
	const b = parseInt(full.slice(4, 6), 16);
	return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

/* ------------------------------------------------------------------ *
 * Motion language
 *
 * Entrances are overdamped springs (no bounce). Exits use expo easing.
 * Two deliberate exceptions carry a hint of overshoot: the stamp impact
 * and the two CTA slams.
 * ------------------------------------------------------------------ */

export const SPRING = {
	/** Default entrance — overdamped, arrives and stays. */
	entrance: {damping: 200, stiffness: 100, mass: 1},
	/** Slightly faster overdamped entrance for small elements. */
	entranceQuick: {damping: 200, stiffness: 180, mass: 0.6},
	/** Settle for things that land (pin drop, chip). */
	settle: {damping: 26, stiffness: 190, mass: 0.9},
	/** Exception 1: the stamp impact. */
	stampImpact: {damping: 14, stiffness: 220, mass: 1},
	/** Smaller, quicker stamp for "AT FAULT". */
	stampImpactSmall: {damping: 17, stiffness: 300, mass: 0.7},
	/** Exception 2: the two CTA slams. */
	ctaSlam: {damping: 16, stiffness: 200, mass: 1},
} as const;

export const EASE = {
	/** Exits, wipes, anything that should leave decisively. */
	expoOut: Easing.bezier(0.16, 1, 0.3, 1),
	expoIn: Easing.bezier(0.7, 0, 0.84, 0),
	expoInOut: Easing.bezier(0.87, 0, 0.13, 1),
	standard: Easing.bezier(0.4, 0, 0.2, 1),
	linear: Easing.linear,
} as const;

/* ------------------------------------------------------------------ *
 * Layout tokens
 *
 * Sizes below are authored for 9:16 (1080x1920). 16:9 divides type by
 * TEXT_RATIO so that "9:16 text scales x1.12" relative to 1080p holds.
 * ------------------------------------------------------------------ */

export type Aspect = '9x16' | '16x9';
export type Mode = 'full' | 'overlay';

const TEXT_RATIO = 1.12;

export type Layout = ReturnType<typeof getLayout>;

export const getLayout = (aspect: Aspect) => {
	const tall = aspect === '9x16';
	const width = tall ? 1080 : 1920;
	const height = tall ? 1920 : 1080;

	/** Multiply any 9:16-authored type size by this. */
	const type = tall ? 1 : 1 / TEXT_RATIO;

	/**
	 * The camera never sits still, so a box that only just fits the safe
	 * area at scale 1.00 leaves it under the push. `sideCam` is the same
	 * margin pre-shrunk by the largest scale any act reaches (beat 3's
	 * 1.04 push times its 1.03 cut push), so anything clamped to it stays
	 * inside the safe area for the whole spot.
	 */
	const CAM_MAX = 1.08;

	const baseSafe = tall
		? {top: height * 0.14, bottom: height * 0.22, side: width * 0.074}
		: {top: height * 0.08, bottom: height * 0.1, side: width * 0.06};

	const safe = {
		...baseSafe,
		sideCam: baseSafe.side + (width / 2 - baseSafe.side) * (CAM_MAX - 1),
	};

	/** Vertical centre of the usable band. */
	const bandTop = safe.top;
	const bandBottom = height - safe.bottom;
	const bandMid = (bandTop + bandBottom) / 2;

	return {
		aspect,
		tall,
		width,
		height,
		type,
		safe,
		bandTop,
		bandBottom,
		bandMid,

		/* Beat 1/2 — the claim form */
		form: tall
			? {w: 800, h: 860, cx: width / 2, cy: 900, r: 26}
			: {w: 780, h: 560, cx: width / 2, cy: 500, r: 22},

		/* Beat 1/2 — the stamp. blockW/blockH bound the "40%" + "AT FAULT"
		   unit so the strike-through and the shatter shards register to it
		   without measuring the DOM. */
		stamp: tall
			? {
					cx: width / 2,
					cy: 890,
					pct: 420,
					fault: 150,
					blockW: 420 * 1.72,
					blockH: 420 * 0.8 + 150 * 1.05,
				}
			: {
					cx: width / 2,
					cy: 495,
					pct: 300,
					fault: 108,
					blockW: 300 * 1.72,
					blockH: 300 * 0.8 + 108 * 1.05,
				},

		/* Small-caps label above the form */
		labelY: tall ? 402 : 150,
		labelSize: tall ? 34 : 30,

		/* The gold rule beat 2 draws under the form. Beat 3 continues the
		   very same line as its horizon, so the two must match exactly. */
		ruleY: tall ? 1382 : 840,

		/* Beat 3. The wordmark stacks in 9:16 — one line of
		   "AWESOME ATTORNEYS" at +0.16em cannot fit 1080px at a size worth
		   having. */
		wordmark: tall
			? {cy: 470, size: 92, stacked: true}
			: {cy: 240, size: 76, stacked: false},
		match: tall
			? {cy: 920, nodeR: 42, spread: 320, chipY: 1080}
			: {cy: 490, nodeR: 40, spread: 460, chipY: 620},
		/* The horizon sits on `ruleY`. Peaks are how far the ridges rise
		   above it; the sun sits just behind them. */
		horizon: tall
			? {sunR: 150, sunCx: width * 0.64, sunLift: 30, backPeak: 215, frontPeak: 138}
			: {sunR: 112, sunCx: width * 0.7, sunLift: 24, backPeak: 150, frontPeak: 96},

		/* Beat 4. `size` is a CAP — fitText() shrinks it to whatever the
		   safe width actually allows, so the type can never clip. */
		cta: tall
			? {size: 132, x: width * 0.1, line1Y: 690, gap: 1.18, lift: 90}
			: {size: 134, x: width * 0.11, line1Y: 330, gap: 1.18, lift: 78},
		url: tall ? {y: 1010, size: 62} : {y: 690, size: 56},
		pill: tall
			? {y: 1148, w: 430, h: 108, size: 40}
			: {y: 796, w: 380, h: 92, size: 36},
		disclaimer: {
			// Inside the bottom safe edge, never past it.
			y: tall ? 1400 : 930,
			size: tall ? 28 : 26,
		},
		endWordmark: tall
			? {cy: 760, size: 96, stacked: true}
			: {cy: 455, size: 84, stacked: false},
	};
};

/* ------------------------------------------------------------------ *
 * Legibility
 *
 * In overlay mode the spot is composited over unknown B-roll, so every
 * piece of type carries a two-part shadow: a tight dark contact shadow
 * for edge definition plus a wide soft one to lift it off busy footage.
 * In full mode the background is ours, so the shadow is a whisper.
 * ------------------------------------------------------------------ */

export const typeShadow = (mode: Mode, strength = 1) =>
	mode === 'overlay'
		? // A tight, dark contact shadow gives white type an edge against
			// bright footage; the wide soft one lifts it off busy footage.
			// Without the contact layer, white-on-white is unreadable.
			[
				`0 0 ${2 * strength}px rgba(0,0,0,0.85)`,
				`0 ${2 * strength}px ${5 * strength}px rgba(0,0,0,0.7)`,
				`0 ${10 * strength}px ${44 * strength}px rgba(0,0,0,0.55)`,
			].join(', ')
		: `0 ${2 * strength}px ${18 * strength}px rgba(0,0,0,0.35)`;

export const shapeShadow = (mode: Mode) =>
	mode === 'overlay'
		? 'drop-shadow(0 0 2px rgba(0,0,0,0.8)) drop-shadow(0 2px 6px rgba(0,0,0,0.6)) drop-shadow(0 10px 40px rgba(0,0,0,0.45))'
		: 'drop-shadow(0 8px 30px rgba(0,0,0,0.35))';
