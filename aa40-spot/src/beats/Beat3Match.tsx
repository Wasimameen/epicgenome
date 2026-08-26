/* ------------------------------------------------------------------ *
 * Beat 3 — "The match"  (~7.4 → ~11.8s)  ·  warm, energetic
 *
 * The wordmark reveals in the upper third on "Awesome Attorneys". YOU
 * and ATTORNEY connect on "matches"; the middlemen disappear on
 * "directly". The sun finishes rising on "Phoenix" and a chip names the
 * match on "injury attorney".
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useVideoConfig} from 'remotion';
import {Horizon} from '../parts/Horizon';
import {MatchGraph} from '../parts/MatchGraph';
import {Wordmark} from '../parts/Wordmark';
import {useSpot} from '../overlays/lib';
import {LEAD, t} from '../timing/beats';

export const Beat3Match: React.FC = () => {
	const {fps} = useVideoConfig();
	const {layout} = useSpot();
	const lead = LEAD / fps;
	const w = layout.wordmark;

	return (
		<AbsoluteFill>
			<Horizon />

			<div
				style={{
					position: 'absolute',
					top: w.cy,
					left: 0,
					width: layout.width,
					display: 'flex',
					justifyContent: 'center',
					translate: '0px -50%',
				}}
			>
				<Wordmark startSec={t.awesome - lead} size={w.size} stacked={w.stacked} />
			</div>

			<MatchGraph />
		</AbsoluteFill>
	);
};
