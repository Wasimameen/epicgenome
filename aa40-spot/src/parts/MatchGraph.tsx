/* ------------------------------------------------------------------ *
 * MatchGraph.tsx — the whole proposition in one move.
 *
 * YOU and ATTORNEY slide in from opposite edges. The line between them
 * bends through two faint middlemen. On "directly" the middlemen shrink
 * to nothing and the line snaps straight and bright. No text explains
 * it; the move is the argument.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, interpolate, interpolateColors} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import {EASE, FONT, rgba, SPRING, shapeShadow, typeShadow} from '../theme';
import {MaskReveal, ramp, springAt, useClock, useSpot} from '../overlays/lib';
import {LEAD, t} from '../timing/beats';

/** Shared with Soundtrack so the connect chime lands on the same frame. */
export const matchTiming = (fps: number) => {
	const lead = LEAD / fps;
	const nodesIn = t.matches - lead;
	return {
		lead,
		nodesIn,
		lineIn: nodesIn + 0.18,
		lineDur: 0.4,
		pulseStart: nodesIn + 0.42,
		/** Pulse lands, rings flash, check-ring draws, chime fires. */
		arrival: t.directly - lead - 0.06,
		directly: t.directly - lead,
		chip: t.injury - lead,
	};
};

/** Cubic bezier point, used to walk the pulse along the connection. */
const bezier = (
	p0: [number, number],
	p1: [number, number],
	p2: [number, number],
	p3: [number, number],
	u: number,
): [number, number] => {
	const v = 1 - u;
	const a = v * v * v;
	const b = 3 * v * v * u;
	const c = 3 * v * u * u;
	const d = u * u * u;
	return [
		a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
		a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
	];
};

const Node: React.FC<{
	readonly x: number;
	readonly y: number;
	readonly r: number;
	readonly label: string;
	readonly enter: number;
	readonly from: number;
	readonly flash: number;
}> = ({x, y, r, label, enter, from, flash}) => {
	const {palette: c, layout, mode} = useSpot();
	const ring = interpolateColors(flash, [0, 1], [c.white, c.gold]);
	return (
		<div
			style={{
				position: 'absolute',
				left: x - r,
				top: y - r,
				width: r * 2,
				height: r * 2,
				translate: `${(1 - enter) * from}px 0px`,
				scale: interpolate(enter, [0, 1], [0.82, 1]),
				opacity: interpolate(enter, [0, 0.25], [0, 1], {extrapolateRight: 'clamp'}),
			}}
		>
			<div
				style={{
					width: r * 2,
					height: r * 2,
					borderRadius: '50%',
					border: `${Math.max(3, r * 0.085)}px solid ${ring}`,
					background: c.ink,
					boxShadow:
						flash > 0.01
							? `0 0 ${r * 1.1 * flash}px ${rgba(c.gold, 0.85 * flash)}`
							: undefined,
					filter: mode === 'overlay' ? shapeShadow('overlay') : undefined,
				}}
			/>
			<div
				style={{
					position: 'absolute',
					top: r * 2 + r * 0.42,
					left: '50%',
					translate: '-50% 0',
					fontFamily: FONT.brand,
					fontWeight: 600,
					fontSize: layout.labelSize * 0.94,
					letterSpacing: '0.14em',
					color: c.white,
					textShadow: typeShadow(mode),
					whiteSpace: 'nowrap',
				}}
			>
				{label}
			</div>
		</div>
	);
};

export const MatchGraph: React.FC = () => {
	const {sec, frame, fps} = useClock();
	const {palette: c, layout, mode} = useSpot();
	const m = layout.match;
	const T = matchTiming(fps);

	const cx = layout.width / 2;
	const cy = m.cy;
	const youX = cx - m.spread;
	const attX = cx + m.spread;

	/* Nodes arrive from far off-frame, overdamped. */
	const enter = springAt(frame, fps, T.nodesIn, SPRING.entrance, 0.62);

	/* Connection draws, then straightens on "directly". */
	const draw = ramp(sec, T.lineIn, T.lineIn + T.lineDur, EASE.expoOut);
	const straight = ramp(sec, T.directly, T.directly + 0.4, EASE.expoOut);

	/* Pulse travels and lands. */
	const travel = ramp(sec, T.pulseStart, T.arrival, EASE.standard);
	const flash = interpolate(
		sec,
		[T.arrival, T.arrival + 0.12, T.arrival + 0.6],
		[0, 1, 0.25],
		{extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
	);
	const check = ramp(sec, T.arrival, T.arrival + 0.42, EASE.expoOut);

	/* Middlemen: present from the start of the beat, gone on "directly". */
	const midOut = ramp(sec, T.directly, T.directly + 0.32, EASE.expoIn);
	const midR = m.nodeR * 0.5 * (1 - midOut);

	const x0 = youX + m.nodeR;
	const x1 = attX - m.nodeR;
	const bend = (1 - straight) * m.nodeR * 0.62;
	const c1: [number, number] = [x0 + (x1 - x0) * 0.3, cy + bend];
	const c2: [number, number] = [x0 + (x1 - x0) * 0.7, cy - bend];
	const p0: [number, number] = [x0, cy];
	const p3: [number, number] = [x1, cy];

	const path = `M ${p0[0]} ${p0[1]} C ${c1[0]} ${c1[1]}, ${c2[0]} ${c2[1]}, ${p3[0]} ${p3[1]}`;
	const [px, py] = bezier(p0, c1, c2, p3, travel);

	const midXs = [x0 + (x1 - x0) * 0.33, x0 + (x1 - x0) * 0.67];
	const midYs = [cy + bend * 0.72, cy - bend * 0.72];

	/* Chip: measured, not estimated, then right-clamped so it can never
	   leave the safe area however wide the string turns out to be. */
	const chipText = 'PHOENIX INJURY ATTORNEY';
	const chipPadX = layout.labelSize * 0.8;
	const chipMaxW = layout.width - layout.safe.sideCam * 2;
	let chipFont = layout.labelSize * 0.86;
	let chipW =
		measureText({
			text: chipText,
			fontFamily: FONT.brand,
			fontSize: chipFont,
			fontWeight: 600,
			letterSpacing: '0.14em',
		}).width +
		chipPadX * 2;
	if (chipW > chipMaxW) {
		chipFont *= chipMaxW / chipW;
		chipW = chipMaxW;
	}
	const chipCx = Math.min(attX, layout.width - layout.safe.sideCam - chipW / 2);

	if (enter <= 0.0001 && draw <= 0) return null;

	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<svg
				width={layout.width}
				height={layout.height}
				viewBox={`0 0 ${layout.width} ${layout.height}`}
				style={{position: 'absolute', inset: 0}}
			>
				{/* Faint middlemen — unlabeled, and briefly on the path. */}
				{midOut < 1
					? midXs.map((mx, i) => (
							<circle
								key={i}
								cx={mx}
								cy={midYs[i]}
								r={midR}
								fill="none"
								stroke={c.steel}
								strokeWidth={Math.max(2, m.nodeR * 0.06)}
								opacity={0.3 * (1 - midOut) * enter}
							/>
						))
					: null}

				{/* The connection */}
				<path
					d={path}
					fill="none"
					stroke={c.gold}
					strokeWidth={interpolate(straight, [0, 1], [3.5, 5.5])}
					strokeLinecap="round"
					pathLength={1}
					strokeDasharray={1}
					strokeDashoffset={1 - draw}
					opacity={interpolate(straight, [0, 1], [0.6, 1])}
					style={
						// The overlay contact shadow is already on the whole SVG.
						mode === 'full'
							? {filter: `drop-shadow(0 0 ${10 + straight * 12}px ${rgba(c.gold, 0.5)})`}
							: undefined
					}
				/>

				{/* Check-ring around the ATTORNEY node */}
				{check > 0 ? (
					<>
						<circle
							cx={attX}
							cy={cy}
							r={m.nodeR * 1.32}
							fill="none"
							stroke={c.gold}
							strokeWidth={Math.max(3, m.nodeR * 0.08)}
							pathLength={1}
							strokeDasharray={1}
							strokeDashoffset={1 - check}
							strokeLinecap="round"
							transform={`rotate(-90 ${attX} ${cy})`}
						/>
						<path
							d={`M ${attX - m.nodeR * 0.38} ${cy + m.nodeR * 0.02} L ${
								attX - m.nodeR * 0.1
							} ${cy + m.nodeR * 0.3} L ${attX + m.nodeR * 0.42} ${cy - m.nodeR * 0.34}`}
							fill="none"
							stroke={c.gold}
							strokeWidth={Math.max(4, m.nodeR * 0.11)}
							strokeLinecap="round"
							strokeLinejoin="round"
							pathLength={1}
							strokeDasharray={1}
							strokeDashoffset={1 - ramp(sec, T.arrival + 0.1, T.arrival + 0.4, EASE.expoOut)}
						/>
					</>
				) : null}

				{/* Travelling pulse */}
				{travel > 0 && travel < 1 ? (
					<circle
						cx={px}
						cy={py}
						r={Math.max(6, m.nodeR * 0.2)}
						fill={c.sand}
						opacity={interpolate(travel, [0, 0.08, 0.9, 1], [0, 1, 1, 0])}
						style={{filter: `drop-shadow(0 0 18px ${rgba(c.gold, 0.9)})`}}
					/>
				) : null}
			</svg>

			<Node
				x={youX}
				y={cy}
				r={m.nodeR}
				label="YOU"
				enter={enter}
				from={-(youX + m.nodeR * 2 + layout.width * 0.2)}
				flash={flash}
			/>
			<Node
				x={attX}
				y={cy}
				r={m.nodeR}
				label="ATTORNEY"
				enter={enter}
				from={layout.width - attX + m.nodeR * 2 + layout.width * 0.2}
				flash={flash}
			/>

			{/* Chip under the ATTORNEY node */}
			{sec >= T.chip - 0.02 ? (
				<>
					<div
						style={{
							position: 'absolute',
							left: attX - 1,
							top: cy + m.nodeR * 1.5,
							width: 2,
							height: Math.max(0, m.chipY - (cy + m.nodeR * 1.5)),
							background: rgba(c.gold, 0.45),
							scale: `1 ${ramp(sec, T.chip, T.chip + 0.3, EASE.expoOut)}`,
							transformOrigin: '50% 0%',
						}}
					/>
					<div
						style={{
							position: 'absolute',
							top: m.chipY,
							left: chipCx,
							translate: '-50% 0',
						}}
					>
						<MaskReveal startSec={T.chip} durationSec={0.45} direction="right" travel={20}>
							<div
								style={{
									boxSizing: 'border-box',
									width: chipW,
									display: 'inline-flex',
									alignItems: 'center',
									justifyContent: 'center',
									padding: `${chipFont * 0.44}px ${chipPadX}px`,
									border: `2px solid ${c.gold}`,
									borderRadius: 999,
									background: rgba(c.ink, mode === 'full' ? 0.55 : 0.72),
									fontFamily: FONT.brand,
									fontWeight: 600,
									fontSize: chipFont,
									letterSpacing: '0.14em',
									color: c.sand,
									textShadow: typeShadow(mode),
									whiteSpace: 'nowrap',
								}}
							>
								{chipText}
							</div>
						</MaskReveal>
					</div>
				</>
			) : null}
		</AbsoluteFill>
	);
};
