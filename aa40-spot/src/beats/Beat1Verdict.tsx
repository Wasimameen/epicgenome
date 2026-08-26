/* ------------------------------------------------------------------ *
 * Beat 1 — "The verdict that isn't"  (0 → ~3.4s)  ·  deflated, cold
 *
 * A claim form draws itself in, quiet. On "forty" a rubber stamp slams
 * onto it. The "%" flickers on "percent"; "AT FAULT" lands smaller and
 * quicker on "at fault". Then everything holds still and breathes.
 *
 * Beat 2 does not replace this scene — it transforms it — so beat 1 and
 * beat 2 live in one <Sequence> and this component stays mounted while
 * the stamp is struck through and shattered.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ClaimForm, FormLabel} from '../parts/ClaimForm';
import {Stamp, StampInkFilter, useStampState} from '../parts/Stamp';
import {useSpot} from '../overlays/lib';
import {LEAD, t} from '../timing/beats';
import {useVideoConfig} from 'remotion';

export const Beat1Verdict: React.FC = () => {
	const {palette: c, mode} = useSpot();
	const {fps} = useVideoConfig();
	const stamp = useStampState();
	const lead = LEAD / fps;

	return (
		<AbsoluteFill>
			{/* The ink filter def lives here, not inside <Stamp>, so it is
			    still mounted once the shards replace the intact stamp. */}
			{mode === 'full' ? <StampInkFilter /> : null}
			<ClaimForm />
			<FormLabel
				text="Claim Determination"
				color={c.steel}
				inSec={0.16}
				replacedAt={t.opening - lead + 0.08}
				direction="down"
			/>
			<Stamp state={stamp} />
		</AbsoluteFill>
	);
};
