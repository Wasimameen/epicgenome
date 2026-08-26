/* ------------------------------------------------------------------ *
 * Camera.tsx — the spot is never static and never busy.
 *
 * A slow, continuous scale/translate drift over the whole scene, plus
 * the impact punches. One camera per mounted act, so a beat change that
 * is masked (the light sweep) or hard-cut can reset the framing without
 * a visible jump.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {EASE} from '../theme';
import {punch, useClock, useSpot} from '../overlays/lib';
import {beatWindows, LEAD, t, TOTAL_SEC} from '../timing/beats';

export type CameraAct = 'cold' | 'three' | 'four';

/** Lateral drift is a pure function of absolute time, so it never jumps. */
const lateralDrift = (sec: number, amount: number) => ({
	x: Math.sin(sec * 2 * Math.PI * 0.047) * amount,
	y: Math.cos(sec * 2 * Math.PI * 0.031) * amount * 0.5,
});

export const Camera: React.FC<{
	readonly act: CameraAct;
	readonly children: React.ReactNode;
}> = ({act, children}) => {
	const {sec, frame, fps} = useClock();
	const {layout} = useSpot();
	const w = beatWindows(fps);
	const lead = LEAD / fps;

	let scale = 1;

	if (act === 'cold') {
		// Beat 1: slow pull-out — deflation. Beat 2: reverses into a push.
		scale =
			sec < t.line2
				? interpolate(sec, [0, t.line2], [1.04, 1.0], {
						extrapolateLeft: 'clamp',
						extrapolateRight: 'clamp',
						easing: EASE.standard,
					})
				: interpolate(sec, [t.line2, w.two.end], [1.0, 1.06], {
						extrapolateLeft: 'clamp',
						extrapolateRight: 'clamp',
						easing: EASE.standard,
					});
	}

	if (act === 'three') {
		// Gentle continuous push, then the 3-frame 1.03 push on the way out.
		const push = interpolate(sec, [w.three.start, w.three.end], [1.0, 1.04], {
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
			easing: EASE.standard,
		});
		const cutPush = interpolate(
			sec,
			[w.three.end - 3 / fps, w.three.end],
			[1, 1.03],
			{extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.expoIn},
		);
		scale = push * cutPush;
	}

	if (act === 'four') {
		// Arrives at 0.97 on the hard cut, locks, then a slow push under
		// the URL.
		const arrive = interpolate(
			sec,
			[w.four.start, w.four.start + 6 / fps],
			[0.97, 1],
			{extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.expoOut},
		);
		const urlPush = interpolate(sec, [t.url - lead, t.end + 1.2], [1, 1.03], {
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
			easing: EASE.standard,
		});
		scale = arrive * urlPush;
	}

	// One-frame impacts that decay instead of popping.
	const impact =
		act === 'cold'
			? punch(frame, fps, t.forty - lead, 0.02)
			: act === 'four'
				? punch(frame, fps, t.getMatched - lead, 0.02) +
					punch(frame, fps, t.getPaid - lead, 0.02)
				: 0;

	/*
	 * The drift is continuous by design, but the last half second of the
	 * spot has to be dead still — it is the frame the platform grabs for
	 * the thumbnail. Ease the drift amplitude to zero before then rather
	 * than cutting it, so the camera settles instead of stopping.
	 */
	const settle = interpolate(sec, [TOTAL_SEC - 1.6, TOTAL_SEC - 0.6], [1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: EASE.expoOut,
	});
	const drift = lateralDrift(sec, (layout.tall ? 6 : 8) * settle);

	return (
		<AbsoluteFill
			style={{
				scale: scale + impact,
				translate: `${drift.x}px ${drift.y}px`,
				transformOrigin: '50% 50%',
			}}
		>
			{children}
		</AbsoluteFill>
	);
};
