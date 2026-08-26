/* ------------------------------------------------------------------ *
 * Shards.tsx — the struck stamp loses its structure.
 *
 * Ten clip-path polygons over copies of the stamp block. Each falls
 * 30–60px and fades over 0.5s with 2-frame staggers, so the shape comes
 * apart rather than dissolving.
 *
 * The staggers run left to right, not top to bottom: a row-major order
 * reads as "the top half vanished", a column-major one reads as the
 * whole word crumbling from the end the strike-through came in from.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, interpolate, random} from 'remotion';
import {EASE} from '../theme';
import {useSpot} from '../overlays/lib';
import {
	SHARD_COLS as COLS,
	SHARD_COUNT as COUNT,
	SHARD_FALL_SEC as FALL_SEC,
	SHARD_ROWS as ROWS,
	shardDelayFrames,
	shardTotalSec,
	STAMP_INK_ID,
	StampBlock,
	type StampState,
} from './Stamp';

/**
 * Jittered grid cell as a clip-path polygon, in percentages. Interior
 * edges are jittered and every cell is over-extended, so the union
 * always covers the block with no seams showing through.
 */
const cellPolygon = (i: number) => {
	const cx = i % COLS;
	const cy = Math.floor(i / COLS);
	const x0 = (cx / COLS) * 100;
	const x1 = ((cx + 1) / COLS) * 100;
	const y0 = (cy / ROWS) * 100;
	const y1 = ((cy + 1) / ROWS) * 100;

	const j = (k: string, amt: number) => (random(`${k}-${i}`) - 0.5) * amt;
	const edgeX = (v: number, k: string) => (v <= 0 ? -6 : v >= 100 ? 106 : v + j(k, 8));
	const edgeY = (v: number, k: string) => (v <= 0 ? -6 : v >= 100 ? 106 : v + j(k, 14));

	const lx = edgeX(x0, 'lx');
	const rx = edgeX(x1, 'rx');
	const ty = edgeY(y0, 'ty');
	const by = edgeY(y1, 'by');
	const tSkew = j('ts', 7);
	const bSkew = j('bs', 7);

	return `polygon(${lx}% ${ty}%, ${rx}% ${ty + tSkew}%, ${rx}% ${by + bSkew}%, ${lx}% ${by}%)`;
};

export const Shards: React.FC<{readonly state: StampState}> = ({state}) => {
	const {mode} = useSpot();
	const {sec, fps, shatterAt, shatter, cx, cy, blockW, blockH, rotate, dropY} =
		state;

	if (shatter <= 0) return null;
	if (sec > shatterAt + shardTotalSec(fps) + 0.15) return null;

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
					// Same rubber-ink texture as the intact stamp, applied once
					// to the whole set rather than ten times.
					filter: mode === 'full' ? `url(#${STAMP_INK_ID})` : undefined,
				}}
			>
				{Array.from({length: COUNT}, (_, i) => {
					const delay = shardDelayFrames(i) / fps;
					const p = Math.max(0, Math.min(1, (sec - shatterAt - delay) / FALL_SEC));
					const fall = p <= 0 ? 0 : EASE.standard(p) * (32 + random(`fall-${i}`) * 30);
					const tip = p <= 0 ? 0 : (random(`tip-${i}`) - 0.5) * 26 * p;
					return (
						<div
							key={i}
							style={{
								position: 'absolute',
								inset: 0,
								clipPath: cellPolygon(i),
								translate: `${(random(`dx-${i}`) - 0.5) * 26 * p}px ${fall}px`,
								rotate: `${tip}deg`,
								opacity:
									p <= 0
										? 1
										: interpolate(p, [0, 0.58, 1], [1, 0.86, 0], {
												extrapolateRight: 'clamp',
											}),
								filter: mode === 'full' && p > 0 ? `blur(${p * 1.8}px)` : undefined,
							}}
						>
							<StampBlock state={state} flat />
						</div>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};
