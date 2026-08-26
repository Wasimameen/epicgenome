/* ------------------------------------------------------------------ *
 * Disclaimer.tsx — the required line, at the bottom safe edge.
 *
 * Sora 400, steel on ink. In overlay mode it gets its own scrim, since
 * steel-on-unknown-footage is the least legible thing in the spot.
 * ------------------------------------------------------------------ */

import React from 'react';
import {FONT, rgba, typeShadow} from '../theme';
import {MaskReveal, useSpot} from '../overlays/lib';

export const Disclaimer: React.FC<{readonly startSec: number}> = ({startSec}) => {
	const {palette: c, layout, mode, disclaimer} = useSpot();
	const d = layout.disclaimer;

	return (
		<div
			style={{
				position: 'absolute',
				top: d.y,
				left: 0,
				width: layout.width,
				display: 'flex',
				justifyContent: 'center',
			}}
		>
			<MaskReveal startSec={startSec} durationSec={0.5} direction="up" travel={12} feather={26}>
				<div
					style={{
						fontFamily: FONT.brand,
						fontWeight: 400,
						fontSize: d.size,
						letterSpacing: '0.01em',
						color: mode === 'overlay' ? '#9FB0C6' : c.steel,
						textAlign: 'center',
						textShadow: typeShadow(mode, 0.7),
						padding:
							mode === 'overlay' ? `${d.size * 0.34}px ${d.size * 0.7}px` : undefined,
						borderRadius: mode === 'overlay' ? d.size : undefined,
						background: mode === 'overlay' ? rgba('#050A12', 0.42) : undefined,
						maxWidth: layout.width - layout.safe.side * 2,
					}}
				>
					{disclaimer}
				</div>
			</MaskReveal>
		</div>
	);
};
