/* ------------------------------------------------------------------ *
 * Stamp.tsx — "40% AT FAULT".
 *
 * The one shot of stampRed in the spot. It slams on in beat 1, loses
 * its authority in beat 2 (struck through, desaturated toward steel,
 * dropped and tilted), then shatters.
 *
 * `useStampState()` is the shared registration point: StrikeThrough and
 * Shards read the same geometry and the same drop/tilt, so nothing can
 * drift out of alignment.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, interpolate, interpolateColors, random} from 'remotion';
import {EASE, FONT, rgba, SPRING, shapeShadow} from '../theme';
import {
	MaybeTrail,
	ramp,
	springAt,
	useClock,
	useSpot,
	within,
} from '../overlays/lib';
import {LEAD, t} from '../timing/beats';

/* ------------------------------------------------------------------ *
 * Shatter geometry — declared here rather than in Shards.tsx so the
 * dependency runs one way (Shards → Stamp) with no import cycle.
 * ------------------------------------------------------------------ */

export const SHARD_COLS = 5;
export const SHARD_ROWS = 2;
export const SHARD_COUNT = SHARD_COLS * SHARD_ROWS;
export const SHARD_FALL_SEC = 0.5;

/** Frames of delay before shard `i` lets go — column-major, 2-frame steps. */
export const shardDelayFrames = (i: number) =>
	(i % SHARD_COLS) * 2 + Math.floor(i / SHARD_COLS);

/** First shard letting go to last shard gone. */
export const shardTotalSec = (fps: number) =>
	SHARD_FALL_SEC + shardDelayFrames(SHARD_COUNT - 1) / fps;

/* ------------------------------------------------------------------ *
 * Shared state
 * ------------------------------------------------------------------ */

export type StampState = ReturnType<typeof useStampState>;

export const useStampState = () => {
	const {sec, frame, fps} = useClock();
	const {layout, palette} = useSpot();
	const lead = LEAD / fps;
	const s = layout.stamp;

	const hitPct = t.forty - lead;
	const hitFault = t.fault - lead;
	const strikeAt = t.opening - lead;
	const shatterAt = t.not - lead;

	/** Impact springs — the two deliberate overshoots of the spot. */
	const pctIn = springAt(frame, fps, hitPct, SPRING.stampImpact, 0.75);
	const faultIn = springAt(frame, fps, hitFault, SPRING.stampImpactSmall, 0.5);

	/** The strike-through crossing takes 0.35s, expo-out. */
	const strike = ramp(sec, strikeAt, strikeAt + 0.35, EASE.expoOut);

	/** Shatter: shards fall and fade over 0.5s, 2-frame staggers. */
	const shatter = ramp(sec, shatterAt, shatterAt + shardTotalSec(fps), EASE.linear);

	/**
	 * The "%" flickers brighter for 6 frames on the word "percent", then
	 * settles. The oscillation is enveloped so it decays to zero at the
	 * end of the window — without that it can be caught mid-peak and pop.
	 */
	const pctFlickerAt = t.percent - lead;
	const flickerWindow = 6 / fps;
	const flickerP = (sec - pctFlickerAt) / flickerWindow;
	const flicker = within(sec, pctFlickerAt, pctFlickerAt + flickerWindow)
		? (1 - flickerP) *
			(0.35 + 0.65 * Math.abs(Math.sin((sec - pctFlickerAt) * fps * 1.35)))
		: 0;

	return {
		sec,
		frame,
		fps,
		lead,
		hitPct,
		hitFault,
		strikeAt,
		shatterAt,
		pctIn,
		faultIn,
		strike,
		shatter,
		flicker,
		/** Geometry of the "40% AT FAULT" unit. */
		cx: s.cx,
		cy: s.cy,
		blockW: s.blockW,
		blockH: s.blockH,
		pctSize: s.pct,
		faultSize: s.fault,
		/** −7°, tilting 2° further as it loses weight. */
		rotate: -7 - strike * 2,
		/** Drops 12px when struck. */
		dropY: strike * 12,
		/** Red desaturating toward steel. */
		color: interpolateColors(strike, [0, 1], [palette.stampRed, palette.steel]),
	};
};

/* ------------------------------------------------------------------ *
 * Ink texture — feTurbulence + feDisplacementMap so the stamp reads as
 * rubber on paper, not as vector type.
 * ------------------------------------------------------------------ */

/** One shared id — the filter def lives in Beat1Verdict so it stays
 *  mounted after the intact stamp is replaced by its shards. */
export const STAMP_INK_ID = 'aa40-stamp-ink';

export const StampInkFilter: React.FC<{readonly id?: string}> = ({
	id = STAMP_INK_ID,
}) => (
	<svg
		width={0}
		height={0}
		style={{position: 'absolute', width: 0, height: 0}}
		aria-hidden
	>
		<defs>
			<filter
				id={id}
				x="-18%"
				y="-18%"
				width="136%"
				height="136%"
				colorInterpolationFilters="sRGB"
			>
				<feTurbulence
					type="fractalNoise"
					baseFrequency="0.055"
					numOctaves={3}
					seed={7}
					result="warp"
				/>
				<feDisplacementMap
					in="SourceGraphic"
					in2="warp"
					scale={7}
					xChannelSelector="R"
					yChannelSelector="G"
					result="disp"
				/>
				<feTurbulence
					type="fractalNoise"
					baseFrequency="0.42"
					numOctaves={2}
					seed={13}
					result="speck"
				/>
				<feColorMatrix
					in="speck"
					type="matrix"
					values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -0.9 1.34"
					result="speckA"
				/>
				<feComposite in="disp" in2="speckA" operator="in" />
			</filter>
		</defs>
	</svg>
);

/* ------------------------------------------------------------------ *
 * Impact particles — 26 flecks of ink, deterministic
 * ------------------------------------------------------------------ */

const Particles: React.FC<{readonly state: StampState}> = ({state}) => {
	const {palette: c} = useSpot();
	const {sec, hitPct, blockW, blockH} = state;
	const life = 0.85;
	if (sec < hitPct || sec > hitPct + life) return null;
	const p = (sec - hitPct) / life;

	return (
		<>
			{Array.from({length: 26}, (_, i) => {
				const ang = random(`ang-${i}`) * Math.PI * 2;
				const dist = 0.34 * blockW * (0.35 + random(`d-${i}`) * 0.75);
				const size = 3 + random(`s-${i}`) * 7;
				const delay = random(`t-${i}`) * 0.06;
				const lp = Math.max(0, Math.min(1, (p * life - delay) / (life - delay)));
				const travel = EASE.expoOut(lp);
				const settle = 1 - Math.pow(1 - lp, 2);
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: blockW / 2 + Math.cos(ang) * dist * travel - size / 2,
							top:
								blockH / 2 +
								Math.sin(ang) * dist * 0.62 * travel +
								settle * 26 * random(`g-${i}`) -
								size / 2,
							width: size,
							height: size * (0.5 + random(`r-${i}`) * 0.8),
							borderRadius: random(`b-${i}`) > 0.5 ? '50%' : 2,
							background: c.stampRed,
							opacity: interpolate(lp, [0, 0.18, 0.7, 1], [0, 0.95, 0.7, 0], {
								extrapolateRight: 'clamp',
							}),
							rotate: `${random(`rot-${i}`) * 90}deg`,
						}}
					/>
				);
			})}
		</>
	);
};

/* ------------------------------------------------------------------ *
 * The stamp itself
 * ------------------------------------------------------------------ */

/** The "40%" + "AT FAULT" unit, unpositioned — reused by Shards. */
export const StampBlock: React.FC<{
	readonly state: StampState;
	readonly flat?: boolean;
	readonly colorOverride?: string;
}> = ({state, flat = false, colorOverride}) => {
	const {mode} = useSpot();
	const {pctIn, faultIn, pctSize, faultSize, blockW, blockH, flicker} = state;
	const color = colorOverride ?? state.color;

	const pctScale = flat ? 1 : interpolate(pctIn, [0, 1], [1.6, 1]);
	const faultScale = flat ? 1 : interpolate(faultIn, [0, 1], [1.45, 1]);
	const pctVisible = flat ? 1 : pctIn > 0.001 ? 1 : 0;
	const faultVisible = flat ? 1 : faultIn > 0.001 ? 1 : 0;

	return (
		<div
			style={{
				width: blockW,
				height: blockH,
				display: 'flex',
				flexDirection: 'column',
				alignItems: 'center',
				justifyContent: 'center',
				fontFamily: FONT.stamp,
				color,
				filter: mode === 'overlay' ? shapeShadow('overlay') : undefined,
			}}
		>
			<div
				style={{
					fontSize: pctSize,
					lineHeight: 0.82,
					letterSpacing: '0.02em',
					scale: pctScale,
					translate: `0px ${flat ? 0 : (1 - pctIn) * -34}px`,
					opacity: pctVisible,
				}}
			>
				40
				{/* The "%" alone flickers on the word "percent". */}
				<span
					style={{
						textShadow:
							flicker > 0 ? `0 0 ${18 * flicker}px ${rgba(color, 0.9)}` : undefined,
						filter: flicker > 0 ? `brightness(${1 + flicker * 0.5})` : undefined,
					}}
				>
					%
				</span>
			</div>
			<div
				style={{
					fontSize: faultSize,
					lineHeight: 1,
					letterSpacing: '0.06em',
					marginTop: faultSize * 0.14,
					scale: faultScale,
					translate: `0px ${flat ? 0 : (1 - faultIn) * -18}px`,
					opacity: faultVisible,
				}}
			>
				AT FAULT
			</div>
		</div>
	);
};

export const Stamp: React.FC<{readonly state: StampState}> = ({state}) => {
	const {mode, palette} = useSpot();
	const {sec, hitPct, cx, cy, blockW, blockH, rotate, dropY, shatter, strike} = state;

	// Once the shards take over, the intact stamp is gone.
	if (shatter > 0) return null;

	const trailing = within(sec, hitPct - 0.1, hitPct + 0.34);

	// The strike-through crosses at blockW * 1.1, offset by 5% on the left.
	const edge = strike * 110 - 5;
	const red = palette.stampRed;
	const steel = palette.steel;
	const drainMask =
		strike <= 0
			? undefined
			: `linear-gradient(90deg, rgba(0,0,0,0) ${edge - 3}%, #000 ${edge + 5}%)`;

	return (
		<>
			<AbsoluteFill style={{pointerEvents: 'none'}}>
				<div
					style={{
						position: 'absolute',
						left: cx - blockW / 2,
						top: cy - blockH / 2,
						width: blockW,
						height: blockH,
						rotate: `${rotate}deg`,
						translate: `0px ${dropY}px`,
						transformOrigin: '50% 50%',
					}}
				>
					<MaybeTrail active={trailing} layers={3} lagInFrames={1.3} trailOpacity={0.4}>
						<div
							style={{
								position: 'relative',
								filter: mode === 'full' ? `url(#${STAMP_INK_ID})` : undefined,
							}}
						>
							{/* Two stacked copies. The steel one is underneath; the
							    red one on top is masked away behind the strike-through,
							    so the colour drains as the line passes rather than
							    fading everywhere at once. */}
							<StampBlock state={state} colorOverride={steel} />
							<div
								style={{
									position: 'absolute',
									inset: 0,
									maskImage: drainMask,
									WebkitMaskImage: drainMask,
								}}
							>
								<StampBlock state={state} colorOverride={red} />
							</div>
						</div>
					</MaybeTrail>
					<Particles state={state} />
				</div>
			</AbsoluteFill>
		</>
	);
};
