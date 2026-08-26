/* ------------------------------------------------------------------ *
 * Horizon.tsx — a stylised Phoenix horizon: two flat ridges and a sun.
 *
 * No buildings, no clip-art. A long Camelback-style ridge behind one
 * distinct peak, a coral → gold sun disc with a sand bloom, and the
 * thin gold line beat 2 already drew under the form — the two sit on
 * exactly the same y, so beat 3 continues the line rather than drawing
 * a new one.
 *
 * The sky gradient lives in Background (full mode only). These fills
 * are foreground shapes, so they survive into overlay mode.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {EASE, rgba, SPRING} from '../theme';
import {ramp, springAt, useClock, useSpot} from '../overlays/lib';
import {sweepRevealMask} from './LightSweep';
import {beatWindows, LEAD, t} from '../timing/beats';

/** A flat, geometric ridge: peaks at fractions of the width. */
const ridgePath = (
	W: number,
	H: number,
	line: number,
	rise: number,
	profile: [number, number][],
) => {
	const pts = profile
		.map(([fx, fy]) => `L ${(fx * W).toFixed(1)} ${(line - fy * rise).toFixed(1)}`)
		.join(' ');
	return `M ${-W * 0.05} ${line + 20} ${pts} L ${W * 1.05} ${line + 20} L ${
		W * 1.05
	} ${H} L ${-W * 0.05} ${H} Z`;
};

/** Long low ridge with a run of shallow summits. */
const BACK_PROFILE: [number, number][] = [
	[0.0, 0.18],
	[0.11, 0.62],
	[0.22, 0.34],
	[0.33, 0.5],
	[0.46, 1.0],
	[0.55, 0.74],
	[0.68, 0.86],
	[0.8, 0.42],
	[0.92, 0.58],
	[1.0, 0.3],
];

/** Camelback: a long flat ridge with one distinct peak to its left. */
const FRONT_PROFILE: [number, number][] = [
	[0.0, 0.1],
	[0.08, 0.3],
	[0.17, 1.0],
	[0.25, 0.52],
	[0.36, 0.66],
	[0.5, 0.62],
	[0.62, 0.7],
	[0.74, 0.44],
	[0.86, 0.56],
	[1.0, 0.22],
];

export const Horizon: React.FC = () => {
	const {sec, frame, fps} = useClock();
	const {palette: c, layout, mode} = useSpot();
	const h = layout.horizon;
	const w = beatWindows(fps);
	const lead = LEAD / fps;

	const W = layout.width;
	const H = layout.height;
	const line = layout.ruleY;

	/* The sun rises 40px across the beat and completes on "Phoenix". */
	const rise = interpolate(sec, [w.three.start, t.phoenix - lead + 0.35], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: EASE.standard,
	});
	const sunCy = line - h.sunLift - rise * 40;

	/* Ridges rise into place as the scene arrives. */
	const arrive = ramp(sec, w.three.start, w.three.start + 0.8, EASE.expoOut);

	/* The horizon line IS beat 2's rule. It is revealed strictly behind
	   the sweep edge so the two never appear as a double line. */
	const sweepP = ramp(sec, w.sweep.start, w.sweep.end, EASE.expoInOut);
	const lineMask = sec < w.sweep.end ? sweepRevealMask(sweepP) : undefined;

	/* The ridge brightens on "Phoenix". */
	const ridgeLift = ramp(sec, t.phoenix - lead, t.phoenix - lead + 0.5, EASE.standard);

	/* Location pin drops on "Phoenix" with a short settle. */
	const pin = springAt(frame, fps, t.phoenix - lead, SPRING.settle, 0.42);
	const pinX = W * (layout.tall ? 0.3 : 0.36);
	const pinSize = layout.tall ? 46 : 40;

	const back = ridgePath(W, H, line, h.backPeak * arrive, BACK_PROFILE);
	const front = ridgePath(W, H, line, h.frontPeak * arrive, FRONT_PROFILE);

	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<svg
				width={W}
				height={H}
				viewBox={`0 0 ${W} ${H}`}
				style={{
					position: 'absolute',
					inset: 0,
					filter: mode === 'overlay' ? 'drop-shadow(0 -2px 10px rgba(0,0,0,0.5))' : undefined,
				}}
			>
				<defs>
					<radialGradient id="aa40-sun" cx="50%" cy="50%" r="50%">
						<stop offset="0%" stopColor={c.sand} />
						<stop offset="30%" stopColor={c.gold} />
						<stop offset="72%" stopColor={c.coral} />
						<stop offset="100%" stopColor={c.coral} />
					</radialGradient>
					<radialGradient id="aa40-bloom" cx="50%" cy="50%" r="50%">
						<stop offset="0%" stopColor={rgba(c.sand, 0.42)} />
						<stop offset="34%" stopColor={rgba(c.coral, 0.22)} />
						<stop offset="100%" stopColor="rgba(0,0,0,0)" />
					</radialGradient>
					<linearGradient id="aa40-ridge-back" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stopColor="#2E4A6B" />
						<stop offset="100%" stopColor="#182B44" />
					</linearGradient>
					<linearGradient id="aa40-ridge-front" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stopColor="#101F33" />
						<stop offset="100%" stopColor="#060C15" />
					</linearGradient>
				</defs>

				{/* Bloom — needs a sky to sit in, so full mode only. */}
				{mode === 'full' ? (
					<circle
						cx={h.sunCx}
						cy={sunCy}
						r={h.sunR * 2.8}
						fill="url(#aa40-bloom)"
						opacity={arrive}
					/>
				) : null}

				{/* Sun disc */}
				<circle cx={h.sunCx} cy={sunCy} r={h.sunR} fill="url(#aa40-sun)" opacity={arrive} />

				{/* Back ridge */}
				<path d={back} fill="url(#aa40-ridge-back)" opacity={0.92 * arrive} />

				{/* Front ridge */}
				<path d={front} fill="url(#aa40-ridge-front)" opacity={arrive} />

				{/* Rim light along the front ridge, brightening on "Phoenix" */}
				<path
					d={front}
					fill="none"
					stroke={rgba(c.gold, 0.3 + 0.45 * ridgeLift)}
					strokeWidth={2.5}
					opacity={arrive}
				/>
			</svg>

			{/* The horizon line itself — beat 2's rule, continued. Outside
			    the SVG so it can carry the sweep-reveal mask. */}
			<div
				style={{
					position: 'absolute',
					left: 0,
					top: line - 1.5,
					width: W,
					height: 3,
					background: c.gold,
					opacity: 0.55 + 0.45 * ridgeLift,
					maskImage: lineMask,
					WebkitMaskImage: lineMask,
				}}
			/>

			{/* Location pin — no city text; the chip already names Phoenix. */}
			{pin > 0.001 ? (
				<div
					style={{
						position: 'absolute',
						left: pinX - pinSize / 2,
						top: line - pinSize * 1.5,
						translate: `0px ${(1 - pin) * -110}px`,
						scale: interpolate(pin, [0, 1], [0.7, 1]),
						opacity: interpolate(pin, [0, 0.3], [0, 1], {extrapolateRight: 'clamp'}),
					}}
				>
					<svg viewBox="0 0 24 36" width={pinSize} height={pinSize * 1.5}>
						<path
							d="M12 0C5.7 0 0.6 5.1 0.6 11.4 0.6 20 12 36 12 36s11.4-16 11.4-24.6C23.4 5.1 18.3 0 12 0z"
							fill={c.gold}
						/>
						<circle cx="12" cy="11.4" r="4.4" fill={c.ink} />
					</svg>
				</div>
			) : null}

		</AbsoluteFill>
	);
};
