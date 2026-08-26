/* ------------------------------------------------------------------ *
 * Wordmark.tsx — the brand.
 *
 * Uses assets-in/logo.svg|png when one is supplied. Otherwise builds the
 * typographic mark called for in §2: AWESOME in white, ATTORNEYS in
 * gold, tracked +0.16em. A single scan of light crosses it as it lands.
 * ------------------------------------------------------------------ */

import React from 'react';
import {Img, staticFile} from 'remotion';
import {ASSETS} from '../assets';
import {EASE, FONT, typeShadow} from '../theme';
import {MaskReveal, ramp, Shine, useClock, useSpot} from '../overlays/lib';

export const Wordmark: React.FC<{
	readonly startSec: number;
	readonly size: number;
	readonly scan?: boolean;
	readonly stacked?: boolean;
}> = ({startSec, size, scan = true, stacked = false}) => {
	const {sec} = useClock();
	const {palette: c, mode} = useSpot();

	const scanP = scan ? ramp(sec, startSec + 0.1, startSec + 0.72, EASE.standard) : 0;

	const inner = ASSETS.logo ? (
		<Img
			src={staticFile(ASSETS.logo)}
			style={{
				height: size * 1.5,
				width: 'auto',
				filter:
					mode === 'overlay'
						? 'drop-shadow(0 2px 6px rgba(0,0,0,0.6)) drop-shadow(0 10px 40px rgba(0,0,0,0.45))'
						: undefined,
			}}
		/>
	) : (
		<div
			style={{
				display: 'flex',
				flexDirection: stacked ? 'column' : 'row',
				alignItems: 'center',
				gap: stacked ? size * 0.1 : size * 0.34,
				fontFamily: FONT.brand,
				fontWeight: 800,
				fontSize: size,
				letterSpacing: '0.16em',
				lineHeight: 1.02,
				textShadow: typeShadow(mode),
				whiteSpace: 'nowrap',
			}}
		>
			<span style={{color: c.white}}>AWESOME</span>
			<span style={{color: c.gold}}>ATTORNEYS</span>
		</div>
	);

	return (
		<MaskReveal
			startSec={startSec}
			durationSec={0.55}
			direction="right"
			feather={18}
			travel={30}
		>
			{/* One scan of light across the mark itself. */}
			<Shine progress={scanP} bandPct={13} brightness={2.1}>
				{inner}
			</Shine>
		</MaskReveal>
	);
};
