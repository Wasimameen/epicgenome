/* ------------------------------------------------------------------ *
 * Texture.tsx — full mode only.
 *
 * Vignette, film grain and a 1px scan of light across the type at the
 * moments that need to feel lit. All three need a background to blend
 * against, so overlay mode drops them entirely.
 *
 * The grain seed advances every 2 frames and is derived from
 * useCurrentFrame(), so it is deterministic across renders.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {EASE, rgba} from '../theme';
import {useClock, useSpot} from '../overlays/lib';
import {LEAD, t} from '../timing/beats';

/** A small tiled turbulence patch is far cheaper than a full-frame filter. */
const GRAIN_TILE = 300;

const grainUrl = (seed: number) => {
	const svg =
		`<svg xmlns="http://www.w3.org/2000/svg" width="${GRAIN_TILE}" height="${GRAIN_TILE}">` +
		`<filter id="g" x="0" y="0" width="100%" height="100%">` +
		`<feTurbulence type="fractalNoise" baseFrequency="0.82" numOctaves="2" seed="${seed}" stitchTiles="stitch"/>` +
		`<feColorMatrix type="saturate" values="0"/>` +
		`</filter>` +
		`<rect width="${GRAIN_TILE}" height="${GRAIN_TILE}" filter="url(#g)"/>` +
		`</svg>`;
	return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}")`;
};

/** Moments where a scan of light crosses the type. */
const scanAt = (sec: number, lead: number) => {
	const moments = [t.fault - lead + 0.14, t.finding - lead, t.matched - lead, t.paid - lead];
	const dur = 0.5;
	let best = 0;
	let pos = -1;
	for (const m of moments) {
		if (sec >= m && sec <= m + dur) {
			const p = (sec - m) / dur;
			best = Math.sin(p * Math.PI);
			pos = EASE.expoOut(p);
		}
	}
	return {intensity: best, pos};
};

export const Texture: React.FC = () => {
	const {sec, frame, fps} = useClock();
	const {palette: c, layout} = useSpot();
	const lead = LEAD / fps;

	// Beat 1 sits in the heaviest vignette in the spot.
	const vignette = interpolate(sec, [t.line2, t.line2 + 0.8], [0.6, 0.5], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: EASE.standard,
	});

	const scan = scanAt(sec, lead);

	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			{/*
			 * Vignette, measured from the frame CORNER rather than from an
			 * ellipse sized to the frame. An ellipse puts its falloff right
			 * where the left edge of "GET MATCHED." sits, which reads as a
			 * dimmed first word rather than as a vignette. Holding it
			 * transparent to 74% of the corner distance keeps the whole safe
			 * area clean and still lands full strength in the corners.
			 */}
			<AbsoluteFill
				style={{
					background: `radial-gradient(farthest-corner at 50% 47%, rgba(0,0,0,0) 0%, rgba(0,0,0,0) 74%, rgba(0,0,0,${(
						vignette * 0.35
					).toFixed(3)}) 88%, rgba(0,0,0,${vignette.toFixed(3)}) 100%)`,
				}}
			/>

			{/* 1px scan of light across the type */}
			{scan.pos >= 0 ? (
				<AbsoluteFill
					style={{
						top: interpolate(scan.pos, [0, 1], [layout.bandTop - 60, layout.bandBottom + 60]),
						height: 3,
						background: `linear-gradient(90deg, rgba(0,0,0,0) 0%, ${rgba(
							c.sand,
							0.55,
						)} 22%, ${rgba(c.white, 0.85)} 50%, ${rgba(c.sand, 0.55)} 78%, rgba(0,0,0,0) 100%)`,
						filter: 'blur(1.2px)',
						opacity: scan.intensity * 0.5,
						mixBlendMode: 'screen',
					}}
				/>
			) : null}

			{/* Film grain — seed advances every 2 frames */}
			<AbsoluteFill
				style={{
					backgroundImage: grainUrl(Math.floor(frame / 2) % 977),
					backgroundRepeat: 'repeat',
					backgroundSize: `${GRAIN_TILE}px ${GRAIN_TILE}px`,
					opacity: 0.05,
					mixBlendMode: 'overlay',
				}}
			/>
		</AbsoluteFill>
	);
};
