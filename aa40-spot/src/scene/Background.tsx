/* ------------------------------------------------------------------ *
 * Background.tsx — full mode only.
 *
 * One continuous ground for the whole spot, so the cold → warm turn is
 * a drift rather than a swap. Beats 1–2 are ink with an overhead light
 * and a slate haze; on "not" a warm edge enters from the top-right and
 * the gradient drifts to navy → ink with a gold rim; the CTA hard-cuts
 * back to ink keeping only that rim at 8%.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, interpolate, interpolateColors} from 'remotion';
import {EASE, rgba} from '../theme';
import {useClock, useSpot} from '../overlays/lib';
import {beatWindows, LEAD, t} from '../timing/beats';

export const Background: React.FC = () => {
	const {sec, fps} = useClock();
	const {palette: c, layout} = useSpot();
	const w = beatWindows(fps);
	const lead = LEAD / fps;

	/** 0 = cold, 1 = warm. The turn starts on "not". */
	const warmth = interpolate(sec, [t.not - lead, t.not - lead + 1.2], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: EASE.standard,
	});

	/** The CTA is a hard cut back to ink — no dissolve. */
	const cta = sec >= w.four.start ? 1 : 0;

	/** Sun-driven warming of the sky through beat 3. */
	const sunRise = interpolate(sec, [w.three.start, t.phoenix - lead + 0.3], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: EASE.standard,
	});

	/** 0.4 Hz breathing of the overhead light in the cold act. */
	const breathe = 0.88 + 0.12 * Math.sin(sec * 2 * Math.PI * 0.4);

	const skyTop = interpolateColors(sunRise, [0, 1], [c.navy, '#1A3A5C']);

	return (
		<AbsoluteFill style={{backgroundColor: c.ink}}>
			{/* Warm sky — navy → ink. Enters with the reframe, gone at the cut. */}
			<AbsoluteFill
				style={{
					background: `linear-gradient(180deg, ${skyTop} 0%, ${c.navy} 32%, ${c.ink} 78%)`,
					opacity: warmth * (1 - cta),
				}}
			/>

			{/* Cold overhead light, breathing. */}
			<AbsoluteFill
				style={{
					background: `radial-gradient(120% 62% at 50% -8%, ${rgba(
						'#3A4C64',
						0.55,
					)} 0%, ${rgba('#233145', 0.28)} 38%, rgba(0,0,0,0) 72%)`,
					opacity: (1 - warmth) * breathe,
				}}
			/>

			{/* Slate haze along the bottom — the cold beats sit in it. */}
			<AbsoluteFill
				style={{
					background: `linear-gradient(0deg, ${rgba(c.slate, 0.85)} 0%, ${rgba(
						c.slate,
						0.28,
					)} 18%, rgba(0,0,0,0) 42%)`,
					opacity: 1 - warmth,
				}}
			/>

			{/* The warm edge: a large gold radial entering from the top-right. */}
			<AbsoluteFill
				style={{
					background: `radial-gradient(80% 55% at ${interpolate(
						warmth,
						[0, 1],
						[118, 92],
					)}% ${interpolate(warmth, [0, 1], [-18, -4])}%, ${rgba(
						c.gold,
						1,
					)} 0%, ${rgba(c.gold, 0.35)} 38%, rgba(0,0,0,0) 70%)`,
					opacity: warmth * 0.12 * (1 - cta) + cta * 0.08,
				}}
			/>

			{/* CTA ground: ink, with a touch more weight at the bottom. */}
			<AbsoluteFill
				style={{
					background: `linear-gradient(180deg, rgba(0,0,0,0) 34%, ${rgba(
						'#050A12',
						0.75,
					)} 100%)`,
					opacity: cta * 0.9,
				}}
			/>

			{/* A whisper of lift under the type in the cold act, so the form
			    never sits on flat black. */}
			<AbsoluteFill
				style={{
					background: `radial-gradient(58% 34% at 50% ${
						(layout.form.cy / layout.height) * 100
					}%, ${rgba('#28384E', 0.4)} 0%, rgba(0,0,0,0) 74%)`,
					opacity: 1 - warmth,
				}}
			/>
		</AbsoluteFill>
	);
};
