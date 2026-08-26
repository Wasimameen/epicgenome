/* ------------------------------------------------------------------ *
 * Beat 4 — CTA  (~12.0 → ~15.4s)  ·  decisive
 *
 * Two slams and then nothing else moves — the type carries it. On the
 * URL the stack lifts and shrinks to make room, the address wipes in
 * under a shimmer, and the pill arrives. The last 2.6s is the end card,
 * and the last half second is completely still so the platform's
 * thumbnail frame is clean.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, interpolate, useVideoConfig} from 'remotion';
import {fitText} from '@remotion/layout-utils';
import {EASE, FONT, SPRING, typeShadow} from '../theme';
import {
	MaskReveal,
	ramp,
	Shine,
	springAt,
	useClock,
	useSpot,
	wipeMask,
} from '../overlays/lib';
import {Pill} from '../parts/Pill';
import {Wordmark} from '../parts/Wordmark';
import {Disclaimer} from '../parts/Disclaimer';
import {LEAD, t} from '../timing/beats';

/** Shared with Soundtrack so the shimmer and the slams stay in sync. */
export const ctaTiming = (fps: number) => {
	const lead = LEAD / fps;
	return {
		slam1: t.getMatched - lead,
		slam2: t.getPaid - lead,
		urlAt: t.url - lead,
		liftDur: 0.5,
		ctaOut: t.end - 0.95,
		endMark: t.end - 0.6,
		disclaimerAt: t.end - 0.25,
	};
};

const SlamLine: React.FC<{
	readonly text: string;
	readonly period: boolean;
	readonly color: string;
	readonly periodColor: string;
	readonly fontSize: number;
	readonly startSec: number;
	readonly outSec: number;
}> = ({text, period, color, periodColor, fontSize, startSec, outSec}) => {
	const {sec, frame, fps} = useClock();
	const {mode} = useSpot();

	const s = springAt(frame, fps, startSec, SPRING.ctaSlam, 0.55);
	const out = ramp(sec, outSec, outSec + 0.35, EASE.expoIn);
	if (s <= 0.0001) return null;

	const mask = wipeMask(Math.min(1, Math.max(0, s)) - out, 'up', 10);

	return (
		<div
			style={{
				maskImage: mask,
				WebkitMaskImage: mask,
				translate: `0px ${(1 - s) * fontSize * 0.42 + out * fontSize * 0.3}px`,
				scale: `${interpolate(s, [0, 1], [1.09, 1])} ${interpolate(s, [0, 1], [1.14, 1])}`,
				transformOrigin: '0% 100%',
				opacity: 1 - out,
				fontFamily: FONT.brand,
				fontWeight: 800,
				fontSize,
				lineHeight: 1.06,
				letterSpacing: '-0.02em',
				color,
				textShadow: typeShadow(mode),
				whiteSpace: 'nowrap',
			}}
		>
			{text}
			{period ? <span style={{color: periodColor}}>.</span> : null}
		</div>
	);
};

export const Beat4CTA: React.FC = () => {
	const {sec} = useClock();
	const {fps} = useVideoConfig();
	const {palette: c, layout, mode} = useSpot();
	const T = ctaTiming(fps);
	const cta = layout.cta;

	/* One size for both lines, capped by the brief and by the safe width. */
	const withinWidth = layout.width - cta.x - layout.safe.sideCam;
	const fitted = fitText({
		text: 'GET MATCHED.',
		withinWidth,
		fontFamily: FONT.brand,
		fontWeight: 800,
		letterSpacing: '-0.02em',
	});
	const ctaSize = Math.min(cta.size, fitted.fontSize);

	const urlFit = fitText({
		text: 'AwesomeAttorneys.com',
		withinWidth: layout.width - layout.safe.sideCam * 2,
		fontFamily: FONT.brand,
		fontWeight: 700,
		letterSpacing: '0em',
	});
	const urlSize = Math.min(layout.url.size, urlFit.fontSize);

	/* The stack eases up and shrinks to 70% to make room for the URL. */
	const lift = ramp(sec, T.urlAt, T.urlAt + T.liftDur, EASE.expoOut);
	const stackScale = interpolate(lift, [0, 1], [1, 0.7]);
	const stackY = -lift * cta.lift;

	/* A shimmer rises across the URL as it lands. */
	const shimmer = ramp(sec, T.urlAt + 0.1, T.urlAt + 0.85, EASE.standard);

	return (
		<AbsoluteFill>
			{/* GET MATCHED. / GET PAID. */}
			<div
				style={{
					position: 'absolute',
					left: cta.x,
					top: cta.line1Y,
					translate: `0px ${stackY}px`,
					scale: stackScale,
					transformOrigin: '0% 0%',
					display: 'flex',
					flexDirection: 'column',
					gap: ctaSize * (cta.gap - 1),
				}}
			>
				<SlamLine
					text="GET MATCHED"
					period
					color={c.white}
					periodColor={c.gold}
					fontSize={ctaSize}
					startSec={T.slam1}
					outSec={T.ctaOut}
				/>
				<SlamLine
					text="GET PAID"
					period
					color={c.gold}
					periodColor={c.gold}
					fontSize={ctaSize}
					startSec={T.slam2}
					outSec={T.ctaOut}
				/>
			</div>

			{/* End-card wordmark, centred above the URL. */}
			{sec >= T.endMark - 0.02 ? (
				<div
					style={{
						position: 'absolute',
						top: layout.endWordmark.cy,
						left: 0,
						width: layout.width,
						display: 'flex',
						justifyContent: 'center',
						translate: '0px -50%',
					}}
				>
					<Wordmark
						startSec={T.endMark}
						size={layout.endWordmark.size}
						stacked={layout.endWordmark.stacked}
						scan={false}
					/>
				</div>
			) : null}

			{/* AwesomeAttorneys.com */}
			{sec >= T.urlAt + 0.08 ? (
				<div
					style={{
						position: 'absolute',
						top: layout.url.y,
						left: 0,
						width: layout.width,
						display: 'flex',
						justifyContent: 'center',
					}}
				>
					<MaskReveal
						startSec={T.urlAt + 0.1}
						durationSec={0.5}
						direction="right"
						feather={16}
						travel={26}
					>
						<Shine progress={shimmer} bandPct={14} brightness={2.4}>
							<div
								style={{
									fontFamily: FONT.brand,
									fontWeight: 700,
									fontSize: urlSize,
									letterSpacing: '0em',
									whiteSpace: 'nowrap',
									textShadow: typeShadow(mode),
								}}
							>
								<span style={{color: c.white}}>Awesome</span>
								<span style={{color: c.gold}}>Attorneys</span>
								<span style={{color: c.white}}>.com</span>
							</div>
						</Shine>
					</MaskReveal>
				</div>
			) : null}

			<Pill startSec={T.urlAt + 0.5} label="Get Matched" />
			<Disclaimer startSec={T.disclaimerAt} />
		</AbsoluteFill>
	);
};
