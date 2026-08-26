/* ------------------------------------------------------------------ *
 * LightSweep.tsx — the reveal between the cold act and the warm one.
 *
 * A soft sand band, skewed −18°, crosses the frame left → right on
 * expo-in-out. Beat 3 is already in place behind it; the cold scene is
 * masked away along the same edge, so the sweep does the revealing
 * rather than covering a dissolve.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {EASE, rgba} from '../theme';
import {ramp, useClock, useSpot} from '../overlays/lib';

const SKEW = -18;

/** Gradient direction that matches the −18° skew of the band. */
export const SWEEP_ANGLE = 90 - SKEW;

/**
 * Where the band's centre is, as a percentage of frame width. The
 * cutout mask and the visible band both read from this, so the scene
 * disappears exactly under the light rather than ahead of it.
 */
export const sweepEdgePct = (progress: number) => progress * 132 - 16;

/**
 * The mask that removes the outgoing scene along the sweep edge. Applied
 * to the cold act: everything the band has already passed is gone.
 */
export const sweepCutoutMask = (progress: number) => {
	const edge = sweepEdgePct(progress);
	return `linear-gradient(${SWEEP_ANGLE}deg, rgba(0,0,0,0) ${edge - 5}%, #000 ${
		edge + 7
	}%)`;
};

/**
 * The exact inverse: visible only where the cold act has already been
 * wiped away.
 *
 * Beat 2's gold rule and beat 3's horizon are the same line, but they
 * live under different cameras and so sit a couple of dozen pixels
 * apart on screen. Revealing the horizon strictly behind the sweep edge
 * means only ever one of them is on any given column of pixels — the
 * rule hands over to the horizon under the band instead of doubling.
 */
export const sweepRevealMask = (progress: number) => {
	const edge = sweepEdgePct(progress);
	return `linear-gradient(${SWEEP_ANGLE}deg, #000 ${edge - 5}%, rgba(0,0,0,0) ${
		edge + 7
	}%)`;
};

export const LightSweep: React.FC<{
	readonly startSec: number;
	readonly endSec: number;
}> = ({startSec, endSec}) => {
	const {sec} = useClock();
	const {palette: c, layout} = useSpot();
	const p = ramp(sec, startSec, endSec, EASE.expoInOut);

	if (sec < startSec - 0.02 || sec > endSec + 0.12) return null;

	const bandW = layout.width * 0.42;
	// The band is centred on the same edge the cutout mask uses.
	const x = (sweepEdgePct(p) / 100) * layout.width - bandW / 2;

	return (
		<AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden'}}>
			<div
				style={{
					position: 'absolute',
					left: x,
					top: -layout.height * 0.3,
					width: bandW,
					height: layout.height * 1.6,
					rotate: `${SKEW}deg`,
					background: `linear-gradient(90deg, rgba(0,0,0,0) 0%, ${rgba(
						c.sand,
						0.16,
					)} 26%, ${rgba(c.sand, 0.4)} 52%, ${rgba(c.gold, 0.2)} 74%, rgba(0,0,0,0) 100%)`,
					filter: 'blur(14px)',
					mixBlendMode: 'screen',
					opacity: interpolate(p, [0, 0.1, 0.86, 1], [0, 1, 1, 0], {
						extrapolateRight: 'clamp',
					}),
				}}
			/>
		</AbsoluteFill>
	);
};
