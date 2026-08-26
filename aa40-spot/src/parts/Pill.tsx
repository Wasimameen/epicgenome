/* ------------------------------------------------------------------ *
 * Pill.tsx — the gold "Get Matched" button under the URL.
 *
 * Scales in with a soft glow on an overdamped spring, then breathes at
 * 0.6 Hz. It is the only thing still moving at the end of the spot, and
 * it stops before the final half second so the thumbnail frame is dead
 * still.
 * ------------------------------------------------------------------ */

import React from 'react';
import {interpolate} from 'remotion';
import {FONT, rgba, SPRING, shapeShadow} from '../theme';
import {springAt, useClock, useSpot} from '../overlays/lib';
import {TOTAL_SEC} from '../timing/beats';

export const Pill: React.FC<{
	readonly startSec: number;
	readonly label: string;
}> = ({startSec, label}) => {
	const {sec, frame, fps} = useClock();
	const {palette: c, layout, mode} = useSpot();
	const p = layout.pill;

	const enter = springAt(frame, fps, startSec, SPRING.entrance, 0.6);
	if (enter <= 0.0001) return null;

	// Breathing stops 0.6s before the end so the last half second is still.
	const stopAt = TOTAL_SEC - 0.6;
	const breathAmp = interpolate(sec, [stopAt - 0.5, stopAt], [1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const breathe = 1 + 0.012 * breathAmp * Math.sin((sec - startSec) * 2 * Math.PI * 0.6);
	const glow = 0.35 + 0.25 * breathAmp * (0.5 + 0.5 * Math.sin((sec - startSec) * 2 * Math.PI * 0.6));

	return (
		<div
			style={{
				position: 'absolute',
				top: p.y,
				left: '50%',
				translate: '-50% 0',
				scale: interpolate(enter, [0, 1], [0.86, 1]) * breathe,
				opacity: interpolate(enter, [0, 0.3], [0, 1], {extrapolateRight: 'clamp'}),
			}}
		>
			<div
				style={{
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'center',
					width: p.w,
					height: p.h,
					borderRadius: p.h / 2,
					background: `linear-gradient(180deg, ${c.sand} 0%, ${c.gold} 46%, #C89A3E 100%)`,
					color: c.ink,
					fontFamily: FONT.brand,
					fontWeight: 700,
					fontSize: p.size,
					letterSpacing: '0.01em',
					boxShadow:
						mode === 'full'
							? `0 0 ${p.h * 0.8}px ${rgba(c.gold, glow)}, 0 14px 40px rgba(0,0,0,0.45)`
							: `0 0 ${p.h * 0.5}px ${rgba(c.gold, glow * 0.7)}`,
					filter: mode === 'overlay' ? shapeShadow('overlay') : undefined,
				}}
			>
				{label}
			</div>
		</div>
	);
};
