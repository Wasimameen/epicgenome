/* ------------------------------------------------------------------ *
 * lib.tsx — shared motion + legibility helpers.
 *
 * Motion rules enforced here:
 *   · everything is expressed in SECONDS, converted to frames at use
 *     time, so the spot is frame-rate independent
 *   · entrances are overdamped springs, exits are expo easing
 *   · reveals are mask wipes, never a bare opacity fade
 *   · every reveal is a compound transform (translate + scale + mask)
 *   · deterministic only: `random(seed)`, never Math.random()
 * ------------------------------------------------------------------ */

import React, {createContext, useContext, useMemo} from 'react';
import {
	Easing,
	interpolate,
	random,
	Sequence,
	spring,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';
import {Trail} from '@remotion/motion-blur';
import {
	type Aspect,
	EASE,
	getLayout,
	type Layout,
	makePalette,
	type Mode,
	type Palette,
	SPRING,
	type Brand,
} from '../theme';

export {rgba} from '../theme';

/* ------------------------------------------------------------------ *
 * Spot context — aspect, mode, palette and layout tokens
 * ------------------------------------------------------------------ */

export type SpotConfig = {
	aspect: Aspect;
	mode: Mode;
	palette: Palette;
	layout: Layout;
	disclaimer: string;
};

const SpotContext = createContext<SpotConfig | null>(null);

export const SpotProvider: React.FC<{
	readonly aspect: Aspect;
	readonly mode: Mode;
	readonly brand?: Brand | null;
	readonly disclaimer: string;
	readonly children: React.ReactNode;
}> = ({aspect, mode, brand, disclaimer, children}) => {
	const value = useMemo<SpotConfig>(
		() => ({
			aspect,
			mode,
			palette: makePalette(brand),
			layout: getLayout(aspect),
			disclaimer,
		}),
		[aspect, mode, brand, disclaimer],
	);
	return <SpotContext.Provider value={value}>{children}</SpotContext.Provider>;
};

export const useSpot = (): SpotConfig => {
	const ctx = useContext(SpotContext);
	if (!ctx) throw new Error('useSpot() used outside <SpotProvider>');
	return ctx;
};

/* ------------------------------------------------------------------ *
 * Absolute time
 *
 * Beats are <Sequence>s, so useCurrentFrame() inside them is relative.
 * <Beat> republishes its own offset so every child can keep talking in
 * absolute seconds straight out of beats.ts.
 * ------------------------------------------------------------------ */

const BeatOffset = createContext(0);

export const Beat: React.FC<{
	readonly name: string;
	readonly startSec: number;
	readonly endSec: number;
	readonly children: React.ReactNode;
}> = ({name, startSec, endSec, children}) => {
	const {fps} = useVideoConfig();
	const from = Math.max(0, Math.round(startSec * fps));
	const durationInFrames = Math.max(1, Math.round(endSec * fps) - from);
	return (
		<Sequence
			name={name}
			from={from}
			durationInFrames={durationInFrames}
			layout="none"
		>
			<BeatOffset.Provider value={from}>{children}</BeatOffset.Provider>
		</Sequence>
	);
};

/** Frame index counted from the start of the composition. */
export const useAbsFrame = () => useCurrentFrame() + useContext(BeatOffset);

/** Seconds since the start of the composition. */
export const useAbsSec = () => useAbsFrame() / useVideoConfig().fps;

/** Everything in this spot is authored in seconds, never in frames. */
export const useSec = useAbsSec;

/** Everything a scene needs in one call. */
export const useClock = () => {
	const {fps} = useVideoConfig();
	const frame = useAbsFrame();
	return useMemo(
		() => ({
			fps,
			frame,
			sec: frame / fps,
			/** Seconds elapsed since `s` (negative before it). */
			since: (s: number) => frame / fps - s,
			/** Frame index of second `s`. */
			at: (s: number) => s * fps,
			/** `frames` frames expressed in seconds. */
			f: (frames: number) => frames / fps,
		}),
		[fps, frame],
	);
};

/* ------------------------------------------------------------------ *
 * Timing primitives (pure functions — no hook-order hazards)
 * ------------------------------------------------------------------ */

export type SpringConfig = {damping: number; stiffness: number; mass?: number};

/** Spring driven from an absolute second. Returns 0 before `startSec`. */
export const springAt = (
	frame: number,
	fps: number,
	startSec: number,
	config: SpringConfig = SPRING.entrance,
	durationSec?: number,
) =>
	spring({
		frame: frame - startSec * fps,
		fps,
		config,
		durationInFrames: durationSec ? Math.round(durationSec * fps) : undefined,
	});

/** Eased 0→1 ramp between two absolute seconds. */
export const ramp = (
	sec: number,
	fromSec: number,
	toSec: number,
	easing: (n: number) => number = EASE.expoOut,
) =>
	interpolate(sec, [fromSec, Math.max(toSec, fromSec + 0.0001)], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing,
	});

/**
 * Enter/exit envelope. `enter` rises over `enterSec` from `inSec`,
 * `exit` rises over `exitSec` from `outSec`, `p` is enter minus exit.
 */
export const useInOut = ({
	inSec,
	outSec,
	enterSec = 0.45,
	exitSec = 0.35,
	enterEasing = EASE.expoOut,
	exitEasing = EASE.expoIn,
}: {
	inSec: number;
	outSec?: number;
	enterSec?: number;
	exitSec?: number;
	enterEasing?: (n: number) => number;
	exitEasing?: (n: number) => number;
}) => {
	const {sec} = useClock();
	const enter = ramp(sec, inSec, inSec + enterSec, enterEasing);
	const exit =
		outSec === undefined ? 0 : ramp(sec, outSec, outSec + exitSec, exitEasing);
	return {enter, exit, p: Math.max(0, enter - exit), sec};
};

/* ------------------------------------------------------------------ *
 * Mask-wipe reveal
 * ------------------------------------------------------------------ */

export type WipeDirection = 'right' | 'left' | 'up' | 'down';

const ANGLE: Record<WipeDirection, number> = {
	right: 90,
	left: 270,
	up: 0,
	down: 180,
};

export const wipeMask = (
	progress: number,
	direction: WipeDirection = 'right',
	feather = 14,
) => {
	const edge = progress * (100 + feather * 2) - feather;
	return `linear-gradient(${ANGLE[direction]}deg, #000 ${edge}%, rgba(0,0,0,0) ${
		edge + feather
	}%)`;
};

/**
 * The house reveal: a mask wipe plus a compound transform. Type slides a
 * few px along the wipe axis and settles from 0.985 scale, so nothing
 * ever arrives on opacity alone.
 */
export const MaskReveal: React.FC<{
	readonly startSec: number;
	readonly durationSec?: number;
	readonly direction?: WipeDirection;
	readonly feather?: number;
	readonly travel?: number;
	readonly scaleFrom?: number;
	readonly outSec?: number;
	readonly outDurationSec?: number;
	readonly easing?: (n: number) => number;
	readonly style?: React.CSSProperties;
	readonly children: React.ReactNode;
}> = ({
	startSec,
	durationSec = 0.5,
	direction = 'right',
	feather = 14,
	travel = 26,
	scaleFrom = 0.985,
	outSec,
	outDurationSec = 0.3,
	easing = EASE.expoOut,
	style,
	children,
}) => {
	const {sec} = useClock();
	const p = ramp(sec, startSec, startSec + durationSec, easing);
	const out =
		outSec === undefined ? 0 : ramp(sec, outSec, outSec + outDurationSec, EASE.expoIn);
	const visible = Math.max(0, p - out);

	const axis = direction === 'up' || direction === 'down' ? 'Y' : 'X';
	const sign = direction === 'right' || direction === 'down' ? -1 : 1;
	const offset = (1 - p) * travel * sign;
	const mask = wipeMask(visible, direction, feather);

	return (
		<div
			style={{
				...style,
				maskImage: mask,
				WebkitMaskImage: mask,
				translate: axis === 'X' ? `${offset}px 0px` : `0px ${offset}px`,
				scale: interpolate(p, [0, 1], [scaleFrom, 1]),
				opacity: out > 0 ? 1 - out : 1,
				willChange: 'mask-image, translate, scale',
			}}
		>
			{children}
		</div>
	);
};

/**
 * Overdamped spring entrance with a compound transform. For elements
 * that should arrive rather than be wiped in.
 */
export const Reveal: React.FC<{
	readonly startSec: number;
	readonly config?: SpringConfig;
	readonly durationSec?: number;
	readonly translate?: [number, number];
	readonly scaleFrom?: number;
	readonly rotateFrom?: number;
	readonly style?: React.CSSProperties;
	readonly children: React.ReactNode;
}> = ({
	startSec,
	config = SPRING.entrance,
	durationSec,
	translate = [0, 28],
	scaleFrom = 0.94,
	rotateFrom = 0,
	style,
	children,
}) => {
	const {frame, fps} = useClock();
	const s = springAt(frame, fps, startSec, config, durationSec);
	return (
		<div
			style={{
				...style,
				translate: `${(1 - s) * translate[0]}px ${(1 - s) * translate[1]}px`,
				scale: interpolate(s, [0, 1], [scaleFrom, 1]),
				rotate: `${(1 - s) * rotateFrom}deg`,
				opacity: interpolate(s, [0, 0.35], [0, 1], {
					extrapolateRight: 'clamp',
				}),
			}}
		>
			{children}
		</div>
	);
};

/**
 * A gold rule that draws in from a given origin — the accent under
 * "NOT A LEGAL FINDING" and under the wordmark.
 */
export const AccentLine: React.FC<{
	readonly startSec: number;
	readonly durationSec?: number;
	readonly color: string;
	readonly width: number;
	readonly thickness?: number;
	readonly origin?: 'left' | 'center';
	readonly style?: React.CSSProperties;
}> = ({
	startSec,
	durationSec = 0.45,
	color,
	width,
	thickness = 4,
	origin = 'left',
	style,
}) => {
	const {sec} = useClock();
	const p = ramp(sec, startSec, startSec + durationSec, EASE.expoOut);
	return (
		<div
			style={{
				height: thickness,
				width,
				background: color,
				borderRadius: thickness,
				scale: `${p} 1`,
				transformOrigin: origin === 'left' ? '0% 50%' : '50% 50%',
				...style,
			}}
		/>
	);
};

/**
 * A band of light crossing a piece of type.
 *
 * It brightens a masked duplicate of the children rather than painting a
 * lit rectangle over the scene — a screen-blended band lightens the
 * background as much as the letterforms, which reads as a grey box
 * instead of a highlight.
 */
export const Shine: React.FC<{
	readonly progress: number;
	readonly bandPct?: number;
	readonly angleDeg?: number;
	readonly brightness?: number;
	readonly children: React.ReactNode;
}> = ({progress, bandPct = 15, angleDeg = 100, brightness = 2.3, children}) => {
	const active = progress > 0 && progress < 1;
	return (
		<div style={{position: 'relative', display: 'inline-block'}}>
			{children}
			{active ? (
				(() => {
					const e = progress * (100 + bandPct * 4) - bandPct * 2;
					const mask = `linear-gradient(${angleDeg}deg, rgba(0,0,0,0) ${
						e - bandPct
					}%, #000 ${e}%, rgba(0,0,0,0) ${e + bandPct}%)`;
					return (
						<div
							style={{
								position: 'absolute',
								inset: 0,
								maskImage: mask,
								WebkitMaskImage: mask,
								pointerEvents: 'none',
								opacity: Math.sin(progress * Math.PI),
							}}
						>
							<div style={{filter: `brightness(${brightness}) saturate(0.55)`}}>
								{children}
							</div>
						</div>
					);
				})()
			) : null}
		</div>
	);
};

/**
 * Motion-blur trail, but only while it is earning its keep. Outside the
 * active window the children render once instead of `layers` times.
 */
export const MaybeTrail: React.FC<{
	readonly active: boolean;
	readonly layers?: number;
	readonly lagInFrames?: number;
	readonly trailOpacity?: number;
	readonly children: React.ReactNode;
}> = ({active, layers = 4, lagInFrames = 1.4, trailOpacity = 0.45, children}) => {
	if (!active) return <>{children}</>;
	return (
		<Trail layers={layers} lagInFrames={lagInFrames} trailOpacity={trailOpacity}>
			{children}
		</Trail>
	);
};

/** True when `sec` sits inside [from, to]. */
export const within = (sec: number, from: number, to: number) =>
	sec >= from && sec <= to;

/* ------------------------------------------------------------------ *
 * Deterministic helpers
 * ------------------------------------------------------------------ */

/** Deterministic float in [min, max) for a stable seed. */
export const rnd = (seed: string | number, min: number, max: number) =>
	min + random(seed) * (max - min);

/** Stable list of n items with deterministic per-item randomness. */
export const spread = <T,>(n: number, fn: (i: number, r: (k: string) => number) => T): T[] =>
	Array.from({length: n}, (_, i) => fn(i, (k) => random(`${k}-${i}`)));

/* ------------------------------------------------------------------ *
 * Camera impulse — a one-frame punch that decays instead of popping
 * ------------------------------------------------------------------ */

export const punch = (
	frame: number,
	fps: number,
	atSec: number,
	amount = 0.02,
	decayFrames = 5,
) => {
	const f = frame - atSec * fps;
	if (f < 0 || f > decayFrames) return 0;
	return (
		amount *
		interpolate(f, [0, decayFrames], [1, 0], {
			extrapolateRight: 'clamp',
			easing: Easing.out(Easing.quad),
		})
	);
};
