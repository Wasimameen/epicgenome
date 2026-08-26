/* ------------------------------------------------------------------ *
 * ClaimForm.tsx — the abstract claim form of beats 1 and 2.
 *
 * Not a document: a rounded slate card, thin steel field rows and three
 * redacted bars, drawn on top-to-bottom with strokeDashoffset in
 * 4-frame staggers. In beat 2 the steel dims by 40% as the argument
 * moves off it and onto the type.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {EASE, FONT, rgba, shapeShadow, typeShadow} from '../theme';
import {AccentLine, MaskReveal, ramp, useClock, useSpot} from '../overlays/lib';
import {t} from '../timing/beats';

const ROWS = 6;
const ROW_STAGGER_FRAMES = 4;
const DRAW_START = 0.1;

export const ClaimForm: React.FC = () => {
	const {sec, fps} = useClock();
	const {palette: c, layout, mode} = useSpot();
	const f = layout.form;

	const x0 = f.cx - f.w / 2;
	const y0 = f.cy - f.h / 2;
	const pad = f.w * 0.07;
	const innerW = f.w - pad * 2;

	/* Card outline draws itself in first. */
	const perimeter = 2 * (f.w + f.h) - 8 * f.r + 2 * Math.PI * f.r;
	const card = ramp(sec, 0.04, 0.5, EASE.expoOut);

	/* Beat 2 dims the steel by 40%. */
	const dim = interpolate(sec, [t.line2, t.line2 + 0.6], [1, 0.6], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: EASE.standard,
	});

	/* Rows: label stub + value line, 4-frame staggers, top to bottom. */
	const rows = Array.from({length: ROWS}, (_, i) => {
		const y = y0 + (0.2 + i * 0.088) * f.h;
		const start = DRAW_START + (i * ROW_STAGGER_FRAMES) / fps;
		const p = ramp(sec, start, start + 0.24, EASE.expoOut);
		const labelW = innerW * (0.2 + ((i * 37) % 11) / 90);
		const valueW = innerW * (0.42 + ((i * 53) % 17) / 60);
		return {y, p, labelW, valueW};
	});

	/* Three redacted bars near the foot of the form. */
	const bars = Array.from({length: 3}, (_, i) => {
		const y = y0 + (0.79 + i * 0.058) * f.h;
		const start = 0.62 + (i * ROW_STAGGER_FRAMES) / fps;
		const p = ramp(sec, start, start + 0.3, EASE.expoOut);
		const w = innerW * [0.62, 0.44, 0.53][i];
		return {y, p, w};
	});

	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<svg
				width={layout.width}
				height={layout.height}
				viewBox={`0 0 ${layout.width} ${layout.height}`}
				style={{
					position: 'absolute',
					inset: 0,
					// Thin steel line-work over unknown footage needs its own
					// contact shadow, exactly as the type does.
					filter: mode === 'overlay' ? shapeShadow('overlay') : undefined,
				}}
			>
				{/* Card body — fills in behind the drawn outline. */}
				{mode === 'full' ? (
					<rect
						x={x0}
						y={y0}
						width={f.w}
						height={f.h}
						rx={f.r}
						fill={rgba(c.slate, 0.62)}
						opacity={ramp(sec, 0.1, 0.62, EASE.standard)}
					/>
				) : null}

				{/* A cool highlight along the top edge so the card has a light source. */}
				<rect
					x={x0}
					y={y0}
					width={f.w}
					height={f.h}
					rx={f.r}
					fill="url(#aa40-card-sheen)"
					opacity={ramp(sec, 0.12, 0.66, EASE.standard) * (mode === 'full' ? 1 : 0)}
				/>

				<defs>
					<linearGradient id="aa40-card-sheen" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stopColor={rgba('#7E93AE', 0.16)} />
						<stop offset="42%" stopColor="rgba(0,0,0,0)" />
					</linearGradient>
				</defs>

				{/* Outline */}
				<rect
					x={x0}
					y={y0}
					width={f.w}
					height={f.h}
					rx={f.r}
					fill="none"
					stroke={rgba(c.steel, 0.85 * dim)}
					strokeWidth={2}
					strokeDasharray={perimeter}
					strokeDashoffset={perimeter * (1 - card)}
					strokeLinecap="round"
				/>

				<g opacity={dim}>
					{/* Header rule */}
					<line
						x1={x0 + pad}
						y1={y0 + f.h * 0.125}
						x2={x0 + f.w - pad}
						y2={y0 + f.h * 0.125}
						stroke={rgba(c.steel, 0.45)}
						strokeWidth={1.5}
						strokeDasharray={innerW}
						strokeDashoffset={innerW * (1 - ramp(sec, 0.18, 0.46, EASE.expoOut))}
					/>

					{/* Field rows */}
					{rows.map((r, i) => (
						<g key={i}>
							<line
								x1={x0 + pad}
								y1={r.y}
								x2={x0 + pad + r.labelW}
								y2={r.y}
								stroke={rgba(c.steel, 0.9)}
								strokeWidth={3}
								strokeLinecap="round"
								strokeDasharray={r.labelW}
								strokeDashoffset={r.labelW * (1 - r.p)}
							/>
							<line
								x1={x0 + pad + innerW * 0.34}
								y1={r.y}
								x2={x0 + pad + innerW * 0.34 + r.valueW}
								y2={r.y}
								stroke={rgba(c.steel, 0.4)}
								strokeWidth={1.5}
								strokeLinecap="round"
								strokeDasharray={r.valueW}
								strokeDashoffset={r.valueW * (1 - r.p)}
							/>
						</g>
					))}

					{/* Redacted bars */}
					{bars.map((b, i) => (
						<rect
							key={i}
							x={x0 + pad}
							y={b.y}
							width={b.w * b.p}
							height={f.h * 0.026}
							rx={f.h * 0.013}
							fill={rgba(c.steel, 0.5)}
						/>
					))}
				</g>
			</svg>
		</AbsoluteFill>
	);
};

/* ------------------------------------------------------------------ *
 * The small-caps slot above the form. Beat 1 states the adjuster's
 * verdict; beat 2 renames it twice.
 * ------------------------------------------------------------------ */

/**
 * `replacedAt` is when the NEXT label takes this slot. This one wipes
 * out just before that instant, so the two are never on screen together
 * — the swap reads as one move rather than a crossfade.
 */
export const LABEL_SWAP_OUT = 0.2;

export const FormLabel: React.FC<{
	readonly text: string;
	readonly color: string;
	readonly inSec: number;
	readonly replacedAt?: number;
	readonly direction?: 'up' | 'down';
	readonly underline?: boolean;
	readonly underlineColor?: string;
}> = ({
	text,
	color,
	inSec,
	replacedAt,
	direction = 'up',
	underline = false,
	underlineColor,
}) => {
	const {sec} = useClock();
	const {layout, mode, palette} = useSpot();

	const outSec = replacedAt === undefined ? undefined : replacedAt - LABEL_SWAP_OUT;

	// Nothing rendered before it is due or after it has left.
	if (sec < inSec - 0.02) return null;
	if (outSec !== undefined && sec > outSec + LABEL_SWAP_OUT) return null;

	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<div
				style={{
					position: 'absolute',
					top: layout.labelY,
					left: 0,
					width: layout.width,
					display: 'flex',
					flexDirection: 'column',
					alignItems: 'center',
				}}
			>
				<MaskReveal
					startSec={inSec}
					durationSec={0.42}
					direction={direction}
					outSec={outSec}
					outDurationSec={LABEL_SWAP_OUT}
					travel={18}
					feather={22}
				>
					<div
						style={{
							fontFamily: FONT.brand,
							fontWeight: 600,
							fontSize: layout.labelSize,
							letterSpacing: '0.14em',
							textTransform: 'uppercase',
							color,
							textShadow: typeShadow(mode),
							whiteSpace: 'nowrap',
						}}
					>
						{text}
					</div>
				</MaskReveal>
				{underline ? (
					<AccentLine
						startSec={inSec + 0.18}
						durationSec={0.44}
						color={underlineColor ?? palette.gold}
						width={Math.min(
							layout.labelSize * text.length * 0.62,
							layout.width - layout.safe.sideCam * 2,
						)}
						thickness={3}
						origin="center"
						style={{marginTop: layout.labelSize * 0.46}}
					/>
				) : null}
			</div>
		</AbsoluteFill>
	);
};
