/* ------------------------------------------------------------------ *
 * StrikeThrough.tsx — the turn of the whole spot.
 *
 * A gold line cuts across "40% AT FAULT" left to right in 0.35s,
 * expo-out, with a motion-blur trail. It registers to the stamp through
 * the shared `useStampState()`, so it stays on the type as the stamp
 * drops and tilts underneath it.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {EASE, rgba, shapeShadow} from '../theme';
import {MaybeTrail, ramp, useSpot, within} from '../overlays/lib';
import type {StampState} from './Stamp';

export const StrikeThrough: React.FC<{readonly state: StampState}> = ({state}) => {
	const {palette: c, mode} = useSpot();
	const {sec, strikeAt, strike, shatterAt, cx, cy, blockW, blockH, rotate, dropY} =
		state;

	if (strike <= 0) return null;

	const w = blockW * 1.1;
	const thickness = Math.max(8, blockH * 0.038);

	// It goes with the stamp it struck — quickly, ahead of the shards, so
	// there is never a gold line hanging over an empty space.
	const alpha = 1 - ramp(sec, shatterAt, shatterAt + 0.28, EASE.expoIn);
	if (alpha <= 0) return null;

	return (
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
				<MaybeTrail
					active={within(sec, strikeAt, strikeAt + 0.4)}
					layers={4}
					lagInFrames={1.2}
					trailOpacity={0.55}
				>
					<div
						style={{
							position: 'absolute',
							left: (blockW - w) / 2,
							// Sits on the "40%" line, where the eye is.
							top: blockH * 0.34 - thickness / 2,
							width: w * strike,
							height: thickness,
							borderRadius: thickness,
							background: `linear-gradient(90deg, ${rgba(c.gold, 0.55)} 0%, ${
								c.gold
							} 18%, ${c.sand} 62%, ${c.gold} 100%)`,
							boxShadow: `0 0 ${thickness * 2.6}px ${rgba(c.gold, 0.55 * alpha)}`,
							filter: mode === 'overlay' ? shapeShadow('overlay') : undefined,
							opacity: alpha,
						}}
					/>
				</MaybeTrail>

				{/* The leading tip is hotter than the line behind it. */}
				{strike < 1 ? (
					<div
						style={{
							position: 'absolute',
							left: (blockW - w) / 2 + w * strike - thickness * 0.9,
							top: blockH * 0.34 - thickness * 1.1,
							width: thickness * 1.8,
							height: thickness * 2.2,
							borderRadius: '50%',
							background: `radial-gradient(circle, ${rgba(c.sand, 0.9)} 0%, ${rgba(
								c.gold,
								0.35,
							)} 55%, rgba(0,0,0,0) 72%)`,
							opacity: interpolate(strike, [0, 0.12, 0.9, 1], [0, 1, 1, 0]),
						}}
					/>
				) : null}
			</div>
		</AbsoluteFill>
	);
};
